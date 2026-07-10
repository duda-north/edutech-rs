"""RN03 — Logs de auditoria imutáveis com abort em falha."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Any

from src.core.config import ConfigManager


class AuditLogFailure(Exception):
    """Lançada quando a gravação do log de auditoria falha (RN03)."""


@dataclass(frozen=True)
class AuditLogEntry:
    aluno_id: str
    timestamp_ms: int
    ip_origem: str
    assinatura_digital: str
    evento: str
    detalhes: dict[str, Any]


class AuditLogger:
    def __init__(self, storage: list | None = None, fail_next: bool = False) -> None:
        self._storage = storage if storage is not None else []
        self._fail_next = fail_next
        self._config = ConfigManager()

    def registrar(
        self,
        aluno_id: str,
        ip_origem: str,
        evento: str,
        detalhes: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        if self._fail_next:
            self._fail_next = False
            raise AuditLogFailure("Falha simulada na gravação do log de auditoria")

        entry = AuditLogEntry(
            aluno_id=aluno_id,
            timestamp_ms=int(time.time() * 1000),
            ip_origem=ip_origem,
            assinatura_digital=self._config.audit_signature,
            evento=evento,
            detalhes=detalhes or {},
        )
        self._storage.append(entry)
        return entry

    def to_json(self, entry: AuditLogEntry) -> str:
        return json.dumps(asdict(entry), ensure_ascii=False)
