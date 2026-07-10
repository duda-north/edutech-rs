# EduTech-RS — Infraestrutura Escalável

Projeto Prático Integrado — Engenharia de Software II  
**Disciplina:** ES II | **Professor:** Prof. Me. Fábio Giulian Marques

## Sobre

Sistema de matrículas e pagamentos da startup **EduTech-RS**, com arquitetura escalável, CI/CD automatizado e observabilidade completa.

## Regras de Negócio Implementadas

| RN | Descrição | Implementação |
|----|-----------|---------------|
| RN01 | Processamento assíncrono (timeout 3s) | `src/workers/payment_worker.py` |
| RN02 | Isolamento UNISENAC/IFSUL | `src/core/matricula_builder.py` |
| RN03 | Logs de auditoria imutáveis | `src/observability/audit.py` |
| RN04 | Deploy seguro (cobertura ≥ 80%) | `.github/workflows/ci-cd.yml` |

## Padrões GoF (Projeto 1)

- **Singleton:** `ConfigManager` — `src/core/config.py`
- **Factory Method:** `PaymentGatewayFactory` — `src/core/payment_factory.py`
- **Builder:** `MatriculaBuilder` — `src/core/matricula_builder.py`

## Como Executar

```bash
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```

## Testes

```bash
pytest
```

## Documentação Completa

Ver `docs/PROJETO_ARQUITETURAL.md` — documento principal para exportar em PDF.

## Estratégia de Branching

**GitFlow** — detalhado na documentação arquitetural.

## Stack

- Python 3.12 + FastAPI
- Prometheus (métricas)
- OpenTelemetry (traces)
- GitHub Actions (CI/CD)
