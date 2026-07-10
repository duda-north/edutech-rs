"""Builder — monta a requisição de matrícula."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Instituicao(str, Enum):
    UNISENAC = "UNISENAC"
    IFSUL = "IFSUL"


class Curso(str, Enum):
    ADS = "ADS"
    TII = "TII"


class StatusMatricula(str, Enum):
    PROCESSANDO = "Processando Matrícula"
    CONFIRMADA = "Matrícula Confirmada"
    PAGAMENTO_PENDENTE = "Pagamento Pendente"
    FALHA = "Falha na Matrícula"


@dataclass
class MatriculaRequest:
    aluno_id: str
    instituicao: Instituicao
    curso: Curso
    valor: float
    card_token: str
    ip_origem: str
    status: StatusMatricula = StatusMatricula.PROCESSANDO
    laboratorio_so: Optional[str] = None
    tenant_db: Optional[str] = None


class MatriculaBuilder:
    def __init__(self) -> None:
        self._aluno_id: Optional[str] = None
        self._instituicao: Optional[Instituicao] = None
        self._curso: Optional[Curso] = None
        self._valor: float = 0.0
        self._card_token: Optional[str] = None
        self._ip_origem: str = "0.0.0.0"

    def com_aluno(self, aluno_id: str) -> MatriculaBuilder:
        self._aluno_id = aluno_id
        return self

    def com_instituicao(self, instituicao: Instituicao) -> MatriculaBuilder:
        self._instituicao = instituicao
        return self

    def com_curso(self, curso: Curso) -> MatriculaBuilder:
        self._curso = curso
        return self

    def com_valor(self, valor: float) -> MatriculaBuilder:
        self._valor = valor
        return self

    def com_pagamento(self, card_token: str) -> MatriculaBuilder:
        self._card_token = card_token
        return self

    def com_ip(self, ip_origem: str) -> MatriculaBuilder:
        self._ip_origem = ip_origem
        return self

    def build(self) -> MatriculaRequest:
        if not all([self._aluno_id, self._instituicao, self._curso, self._card_token]):
            raise ValueError("Campos obrigatórios ausentes na matrícula")

        laboratorio_so, tenant_db = self._resolver_isolamento()

        return MatriculaRequest(
            aluno_id=self._aluno_id,
            instituicao=self._instituicao,
            curso=self._curso,
            valor=self._valor,
            card_token=self._card_token,
            ip_origem=self._ip_origem,
            laboratorio_so=laboratorio_so,
            tenant_db=tenant_db,
        )

    def _resolver_isolamento(self) -> tuple[str, str]:
        """RN02 — cada instituição tem SO e banco separado."""
        if self._instituicao == Instituicao.UNISENAC and self._curso == Curso.ADS:
            return "Linux", "db_unisenac_encrypted"
        if self._instituicao == Instituicao.IFSUL and self._curso == Curso.TII:
            return "Windows", "db_ifsul_encrypted"
        raise ValueError(
            f"Combinação inválida: {self._instituicao}/{self._curso}"
        )
