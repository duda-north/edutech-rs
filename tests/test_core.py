"""Testes unitários — cobertura mínima 80% (RN04)."""
from unittest.mock import patch

import pytest

from src.core.config import ConfigManager
from src.core.matricula_builder import (
    Curso,
    Instituicao,
    MatriculaBuilder,
    StatusMatricula,
)
from src.core.payment_factory import GatewayType, PaymentGatewayFactory
from src.observability.audit import AuditLogFailure, AuditLogger
from src.workers.payment_worker import MatriculaService, PaymentJob, PaymentQueue


@pytest.fixture(autouse=True)
def reset_singleton():
    ConfigManager.reset_for_tests()
    yield
    ConfigManager.reset_for_tests()


class TestSingleton:
    def test_config_manager_singleton(self):
        a = ConfigManager()
        b = ConfigManager()
        assert a is b
        assert a.audit_signature == "COREDE-CENTRO-SUL-SECURE-2026"


class TestFactoryMethod:
    def test_cria_gateway_cielo(self):
        gw = PaymentGatewayFactory.create(GatewayType.CIELO)
        result = gw.process(100.0, "tok_123")
        assert result.success
        assert "CIELO" in result.transaction_id

    def test_cria_gateway_rede(self):
        gw = PaymentGatewayFactory.create(GatewayType.REDE)
        result = gw.process(50.0, "tok_456")
        assert result.success
        assert "REDE" in result.transaction_id

    def test_cria_gateway_slow(self):
        gw = PaymentGatewayFactory.create(GatewayType.SLOW)
        with patch("src.core.payment_factory.time.sleep"):
            result = gw.process(100.0, "tok_slow")
        assert not result.success
        assert result.latency_ms == 4000


class TestBuilder:
    def test_build_unisenac_linux(self):
        m = (
            MatriculaBuilder()
            .com_aluno("ALU-001")
            .com_instituicao(Instituicao.UNISENAC)
            .com_curso(Curso.ADS)
            .com_valor(299.90)
            .com_pagamento("tok")
            .com_ip("192.168.1.1")
            .build()
        )
        assert m.laboratorio_so == "Linux"
        assert m.tenant_db == "db_unisenac_encrypted"

    def test_build_ifsul_windows(self):
        m = (
            MatriculaBuilder()
            .com_aluno("ALU-002")
            .com_instituicao(Instituicao.IFSUL)
            .com_curso(Curso.TII)
            .com_valor(399.90)
            .com_pagamento("tok")
            .build()
        )
        assert m.laboratorio_so == "Windows"
        assert m.tenant_db == "db_ifsul_encrypted"

    def test_build_campos_obrigatorios(self):
        with pytest.raises(ValueError):
            MatriculaBuilder().com_aluno("ALU").build()


class TestRN01Async:
    def test_timeout_enfileira_matricula(self):
        queue = PaymentQueue()
        audit = AuditLogger()
        service = MatriculaService(queue=queue, audit=audit)
        matricula = (
            MatriculaBuilder()
            .com_aluno("ALU-TIMEOUT")
            .com_instituicao(Instituicao.UNISENAC)
            .com_curso(Curso.ADS)
            .com_valor(100)
            .com_pagamento("tok")
            .com_ip("10.0.0.1")
            .build()
        )
        with patch("src.core.payment_factory.time.sleep"):
            with patch(
                "src.workers.payment_worker.time.perf_counter",
                side_effect=[0.0, 4.5],
            ):
                resultado = service.iniciar_matricula(
                    matricula, gateway=GatewayType.SLOW
                )
        assert resultado.status == StatusMatricula.PROCESSANDO
        assert queue.size() == 1

    def test_worker_processa_fila(self):
        queue = PaymentQueue()
        audit = AuditLogger()
        service = MatriculaService(queue=queue, audit=audit)
        matricula = (
            MatriculaBuilder()
            .com_aluno("ALU-WORKER")
            .com_instituicao(Instituicao.IFSUL)
            .com_curso(Curso.TII)
            .com_valor(100)
            .com_pagamento("tok")
            .build()
        )
        queue.enqueue(PaymentJob(matricula=matricula))
        count = service.processar_fila()
        assert count == 1
        assert queue.size() == 0


class TestRN03Audit:
    def test_log_contem_campos_obrigatorios(self):
        storage = []
        logger = AuditLogger(storage=storage)
        entry = logger.registrar("ALU-001", "1.2.3.4", "TESTE", {"x": 1})
        assert entry.aluno_id == "ALU-001"
        assert entry.ip_origem == "1.2.3.4"
        assert entry.assinatura_digital == "COREDE-CENTRO-SUL-SECURE-2026"
        assert entry.timestamp_ms > 0

    def test_falha_log_aborta_operacao(self):
        logger = AuditLogger(fail_next=True)
        with pytest.raises(AuditLogFailure):
            logger.registrar("ALU", "1.1.1.1", "FALHA")

    def test_provisionamento_aborta_se_log_falhar(self):
        audit = AuditLogger(fail_next=True)
        service = MatriculaService(audit=audit)
        matricula = (
            MatriculaBuilder()
            .com_aluno("ALU-AUDIT")
            .com_instituicao(Instituicao.UNISENAC)
            .com_curso(Curso.ADS)
            .com_valor(100)
            .com_pagamento("tok")
            .build()
        )
        with pytest.raises(AuditLogFailure):
            service._provisionar_laboratorio(matricula)


class TestAPI:
    def test_health_endpoint(self):
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_criar_matricula(self):
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        resp = client.post(
            "/api/v1/matriculas",
            json={
                "aluno_id": "ALU-API",
                "instituicao": "UNISENAC",
                "curso": "ADS",
                "valor": 299.90,
                "card_token": "tok_test",
                "gateway": "cielo",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["aluno_id"] == "ALU-API"
        assert data["laboratorio_so"] == "Linux"
