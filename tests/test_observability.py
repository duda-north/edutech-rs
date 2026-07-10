"""Testes de observabilidade — logs, métricas e traces."""
import json

import pytest
from fastapi.testclient import TestClient

from src.core.config import ConfigManager
from src.core.matricula_builder import Curso, Instituicao, MatriculaBuilder
from src.observability.audit import AuditLogger
from src.observability.tracing import get_exported_spans, reset_traces
from src.workers.payment_worker import MatriculaService, PaymentQueue


@pytest.fixture(autouse=True)
def reset_singleton():
    ConfigManager.reset_for_tests()
    yield
    ConfigManager.reset_for_tests()


@pytest.fixture(autouse=True)
def clean_traces():
    reset_traces()
    yield
    reset_traces()


class TestMetricas:
    def test_endpoint_metrics_retorna_prometheus(self):
        from src.api.main import app

        client = TestClient(app)
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        assert "edutech_payment_latency_seconds" in resp.text
        assert "edutech_payment_errors_total" in resp.text
        assert "edutech_matriculas_enfileiradas_total" in resp.text


class TestTraces:
    def test_fluxo_matricula_gera_spans(self):
        queue = PaymentQueue()
        service = MatriculaService(queue=queue)
        matricula = (
            MatriculaBuilder()
            .com_aluno("ALU-TRACE")
            .com_instituicao(Instituicao.UNISENAC)
            .com_curso(Curso.ADS)
            .com_valor(100)
            .com_pagamento("tok")
            .com_ip("10.0.0.1")
            .build()
        )
        service.iniciar_matricula(matricula, process_sync=lambda: "success")

        names = [s.name for s in get_exported_spans()]
        assert "matricula.iniciar" in names
        assert "pagamento.sincrono" in names
        assert "laboratorio.provisionar" in names

    def test_api_gera_span_criar_matricula(self):
        from src.api.main import app

        client = TestClient(app)
        client.post(
            "/api/v1/matriculas",
            json={
                "aluno_id": "ALU-API-TRACE",
                "instituicao": "UNISENAC",
                "curso": "ADS",
                "valor": 299.90,
                "card_token": "tok_test",
                "gateway": "cielo",
            },
        )

        names = [s.name for s in get_exported_spans()]
        assert "api.criar_matricula" in names


class TestAuditJSON:
    def test_log_serializa_json_estruturado(self):
        logger = AuditLogger()
        entry = logger.registrar(
            "ALU-001",
            "189.45.12.88",
            "MATRICULA_INICIADA",
            {"gateway": "cielo"},
        )
        data = json.loads(logger.to_json(entry))

        assert data["aluno_id"] == "ALU-001"
        assert data["ip_origem"] == "189.45.12.88"
        assert data["evento"] == "MATRICULA_INICIADA"
        assert data["assinatura_digital"] == "COREDE-CENTRO-SUL-SECURE-2026"
        assert data["detalhes"]["gateway"] == "cielo"
