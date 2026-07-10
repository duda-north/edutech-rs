"""RN01 — Fila assíncrona de processamento de pagamentos."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from src.core.config import ConfigManager
from src.core.matricula_builder import MatriculaRequest, StatusMatricula
from src.core.payment_factory import GatewayType, PaymentGatewayFactory
from src.observability.audit import AuditLogger, AuditLogFailure
from src.observability.metrics import (
    MATRICULAS_ENFILEIRADAS,
    PAYMENT_ERRORS,
    PAYMENT_LATENCY,
    QUEUE_SIZE,
)
from src.observability.tracing import trace_span


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PaymentJob:
    matricula: MatriculaRequest
    gateway: GatewayType = GatewayType.CIELO
    status: JobStatus = JobStatus.PENDING
    resultado: Optional[str] = None


@dataclass
class PaymentQueue:
    """Fila em memória (produção: Redis/RabbitMQ)."""

    jobs: list[PaymentJob] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def enqueue(self, job: PaymentJob) -> None:
        with self._lock:
            self.jobs.append(job)
            QUEUE_SIZE.set(len(self.jobs))

    def dequeue(self) -> Optional[PaymentJob]:
        with self._lock:
            if not self.jobs:
                QUEUE_SIZE.set(0)
                return None
            job = self.jobs.pop(0)
            QUEUE_SIZE.set(len(self.jobs))
            return job

    def size(self) -> int:
        with self._lock:
            return len(self.jobs)


class MatriculaService:
    """Orquestra matrícula com timeout assíncrono (RN01)."""

    def __init__(
        self,
        queue: PaymentQueue | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self._queue = queue or PaymentQueue()
        self._audit = audit or AuditLogger()
        self._config = ConfigManager()

    def iniciar_matricula(
        self,
        matricula: MatriculaRequest,
        gateway: GatewayType = GatewayType.CIELO,
        process_sync: Callable | None = None,
    ) -> MatriculaRequest:
        with trace_span("matricula.iniciar", {"aluno_id": matricula.aluno_id}):
            self._audit.registrar(
                aluno_id=matricula.aluno_id,
                ip_origem=matricula.ip_origem,
                evento="MATRICULA_INICIADA",
                detalhes={
                    "instituicao": matricula.instituicao.value,
                    "curso": matricula.curso.value,
                    "laboratorio_so": matricula.laboratorio_so,
                },
            )

            if process_sync:
                with trace_span("pagamento.sincrono", {"gateway": gateway.value}):
                    result = process_sync()
            else:
                result = self._tentar_pagamento_sincrono(matricula, gateway)

            if result == "timeout":
                job = PaymentJob(matricula=matricula, gateway=gateway)
                self._queue.enqueue(job)
                MATRICULAS_ENFILEIRADAS.labels(
                    instituicao=matricula.instituicao.value
                ).inc()
                matricula.status = StatusMatricula.PROCESSANDO
                self._audit.registrar(
                    aluno_id=matricula.aluno_id,
                    ip_origem=matricula.ip_origem,
                    evento="PAGAMENTO_ENFILEIRADO",
                    detalhes={"motivo": "timeout_3s", "gateway": gateway.value},
                )
            elif result == "success":
                matricula.status = StatusMatricula.CONFIRMADA
                self._provisionar_laboratorio(matricula)
            else:
                matricula.status = StatusMatricula.FALHA

            return matricula

    def _tentar_pagamento_sincrono(
        self, matricula: MatriculaRequest, gateway: GatewayType
    ) -> str:
        with trace_span("pagamento.sincrono", {"gateway": gateway.value}):
            payment_gateway = PaymentGatewayFactory.create(gateway)
            start = time.perf_counter()
            try:
                result = payment_gateway.process(
                    matricula.valor, matricula.card_token
                )
                elapsed = time.perf_counter() - start
                PAYMENT_LATENCY.labels(
                    gateway=gateway.value,
                    status="success" if result.success else "error",
                ).observe(elapsed)

                if elapsed > self._config.payment_timeout_seconds:
                    return "timeout"
                return "success" if result.success else "error"
            except Exception as exc:
                PAYMENT_ERRORS.labels(
                    gateway=gateway.value, error_type=type(exc).__name__
                ).inc()
                return "error"

    def _provisionar_laboratorio(self, matricula: MatriculaRequest) -> None:
        with trace_span(
            "laboratorio.provisionar",
            {"so": matricula.laboratorio_so or "unknown"},
        ):
            try:
                self._audit.registrar(
                    aluno_id=matricula.aluno_id,
                    ip_origem=matricula.ip_origem,
                    evento="LABORATORIO_PROVISIONADO",
                    detalhes={
                        "so": matricula.laboratorio_so,
                        "tenant_db": matricula.tenant_db,
                    },
                )
            except AuditLogFailure:
                matricula.status = StatusMatricula.FALHA
                raise

    def processar_fila(self) -> int:
        """Worker em background processa jobs pendentes."""
        processed = 0
        while True:
            job = self._queue.dequeue()
            if job is None:
                break
            job.status = JobStatus.PROCESSING
            with trace_span("pagamento.assincrono", {"job": job.matricula.aluno_id}):
                result = self._tentar_pagamento_sincrono(job.matricula, job.gateway)
                if result == "success":
                    job.status = JobStatus.COMPLETED
                    job.matricula.status = StatusMatricula.CONFIRMADA
                    self._provisionar_laboratorio(job.matricula)
                else:
                    job.status = JobStatus.FAILED
                    job.matricula.status = StatusMatricula.PAGAMENTO_PENDENTE
                processed += 1
        return processed
