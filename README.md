# EduTech-RS — Infraestrutura Escalável

**Engenharia de Software II** — Prof. Fábio Giulian Marques  
**Pedro Motta & Eduarda North**

Sistema de matrículas da startup EduTech-RS com processamento assíncrono, CI/CD e observabilidade.

## Regras de negócio

| RN | O que faz |
|----|-----------|
| RN01 | Fila assíncrona quando pagamento demora +3s |
| RN02 | UNISENAC → Linux / IFSUL → Windows (dados isolados) |
| RN03 | Log de auditoria imutável |
| RN04 | Pipeline bloqueia deploy se testes < 80% |

## Padrões GoF (Projeto 1)

Singleton, Factory Method e Builder em `src/core/`.

## Estratégia de branching — GitFlow

A gente pesquisou Trunk-based também, mas pro nosso fluxo (dupla de devs, features separadas) o **GitFlow** fez mais sentido. Cada regra de negócio saiu numa `feature/*` e foi integrando na `develop` antes de ir pra `main`.

| Branch | Pra quê serve |
|--------|---------------|
| `main` | Produção estável |
| `develop` | Integração contínua |
| `feature/*` | Nova funcionalidade (ex: `feature/async-queue`, `feature/observability`) |
| `release/*` | Preparar versão |
| `hotfix/*` | Correção urgente em produção |

Fluxo: `feature/*` → `develop` → `main`. Se quebrar em prod, abre `hotfix/*` e mergeia de volta nas duas.

Diagrama completo e justificativa: [`docs/Motta_&_North.md`](docs/Motta_%26_North.md) (seção 6).

## Pipeline CI/CD

Arquivo: [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml)

A esteira roda em push/PR nas branches do GitFlow e tem três etapas:

1. **Build** — instala deps, valida estrutura (`src/api`, `src/core`, `src/workers`)
2. **Test** — `pytest` com cobertura mínima de 80% (RN04) + scan de credenciais expostas
3. **Deploy** — simula homologação e roda smoke test em `/health` e `/metrics` (só `main`/`develop`)

Se o `test_timeout_enfileira_matricula` falhar, por exemplo, o deploy nem chega a rodar.

## Observabilidade

Código em `src/observability/`:

| Pilar | Implementação |
|-------|---------------|
| **Logs** | `AuditLogger` — JSON com `aluno_id`, IP, timestamp, assinatura. Falhou o log → aborta a operação (RN03) |
| **Métricas** | Prometheus em `/metrics` — latência de pagamento, erros, fila assíncrona |
| **Traces** | OpenTelemetry — spans de `api.criar_matricula` até `laboratorio.provisionar` |

### Prometheus + Grafana (local)

Com a API rodando (`uvicorn src.api.main:app --reload`):

```bash
docker compose up -d
```

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin / admin)

No Grafana, adiciona Prometheus como data source (`http://prometheus:9090`) e consulta métricas tipo `edutech_payment_latency_seconds`.

## Rodar

```bash
pip install -r requirements.txt
pytest
uvicorn src.api.main:app --reload
```

Endpoints úteis:

- `GET /health` — health check
- `GET /metrics` — métricas Prometheus
- `POST /api/v1/matriculas` — criar matrícula

## Documentação (PDF)

`docs/Motta_&_North.md` → exportar como **`Motta_&_North.pdf`**

## Repo

https://github.com/duda-north/edutech-rs
