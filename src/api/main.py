"""API REST da EduTech-RS."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field

from src.core.matricula_builder import (
    Curso,
    Instituicao,
    MatriculaBuilder,
    StatusMatricula,
)
from src.core.payment_factory import GatewayType
from src.observability.audit import AuditLogFailure
from src.observability.tracing import trace_span
from src.workers.payment_worker import MatriculaService, PaymentQueue

app = FastAPI(
    title="EduTech-RS API",
    description="Infraestrutura Escalável — Engenharia de Software II",
    version="2.0.0",
)

_queue = PaymentQueue()
_service = MatriculaService(queue=_queue)


class MatriculaInput(BaseModel):
    aluno_id: str = Field(..., examples=["ALU-001"])
    instituicao: Instituicao
    curso: Curso
    valor: float = Field(..., gt=0)
    card_token: str
    gateway: GatewayType = GatewayType.CIELO


class MatriculaOutput(BaseModel):
    aluno_id: str
    status: StatusMatricula
    laboratorio_so: str | None
    tenant_db: str | None
    mensagem: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "edutech-rs"}


@app.post("/api/v1/matriculas", response_model=MatriculaOutput)
def criar_matricula(payload: MatriculaInput, request: Request):
    with trace_span("api.criar_matricula", {"aluno_id": payload.aluno_id}):
        try:
            matricula = (
                MatriculaBuilder()
                .com_aluno(payload.aluno_id)
                .com_instituicao(payload.instituicao)
                .com_curso(payload.curso)
                .com_valor(payload.valor)
                .com_pagamento(payload.card_token)
                .com_ip(request.client.host if request.client else "0.0.0.0")
                .build()
            )
            resultado = _service.iniciar_matricula(matricula, payload.gateway)

            mensagem = (
                "Sua matrícula está sendo processada. Você receberá confirmação em breve."
                if resultado.status == StatusMatricula.PROCESSANDO
                else "Matrícula processada com sucesso."
            )

            return MatriculaOutput(
                aluno_id=resultado.aluno_id,
                status=resultado.status,
                laboratorio_so=resultado.laboratorio_so,
                tenant_db=resultado.tenant_db,
                mensagem=mensagem,
            )
        except AuditLogFailure as exc:
            raise HTTPException(
                status_code=500,
                detail="Operação abortada: falha na gravação do log de auditoria (RN03)",
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/worker/processar-fila")
def processar_fila():
    """Endpoint para simular worker em background."""
    count = _service.processar_fila()
    return {"processados": count, "fila_restante": _queue.size()}


@app.get("/metrics")
def metrics():
    return PlainTextResponse(
        generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
