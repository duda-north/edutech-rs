"""Métricas Prometheus — RN03/RN04 observabilidade."""
from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge

# Tempo de resposta da API de pagamento (RN04 cenário de desastre)
PAYMENT_LATENCY = Histogram(
    "edutech_payment_latency_seconds",
    "Latência do gateway de pagamento",
    buckets=[0.1, 0.5, 1.0, 3.0, 5.0, 10.0],
    labelnames=["gateway", "status"],
)

PAYMENT_ERRORS = Counter(
    "edutech_payment_errors_total",
    "Total de erros no gateway de pagamento",
    labelnames=["gateway", "error_type"],
)

MATRICULAS_ENFILEIRADAS = Counter(
    "edutech_matriculas_enfileiradas_total",
    "Matrículas enviadas para fila assíncrona (RN01)",
    labelnames=["instituicao"],
)

AUDIT_LOG_FAILURES = Counter(
    "edutech_audit_log_failures_total",
    "Falhas na gravação de logs de auditoria (RN03)",
)

QUEUE_SIZE = Gauge(
    "edutech_payment_queue_size",
    "Tamanho atual da fila de pagamentos",
)

DEPLOY_BLOCKED = Counter(
    "edutech_deploy_blocked_total",
    "Deploys bloqueados por qualidade (RN04)",
    labelnames=["reason"],
)
