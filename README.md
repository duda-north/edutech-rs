# EduTech-RS

## GitFlow

| Branch | Função |
|--------|--------|
| `main` | Produção |
| `develop` | Integração |
| `feature/*` | Nova funcionalidade |
| `release/*` | Preparar versão |
| `hotfix/*` | Correção urgente |

Fluxo: `feature/*` → `develop` → `main`

## Rodar

```bash
pip install -r requirements.txt
pytest
uvicorn src.api.main:app --reload
```

## CI/CD

`.github/workflows/ci-cd.yml` — Build → Test → Deploy

## Observabilidade

- Logs: `src/observability/audit.py`
- Métricas: `src/observability/metrics.py` + `GET /metrics`
- Traces: `src/observability/tracing.py`

Prometheus + Grafana (opcional):

```bash
docker compose up -d
```
