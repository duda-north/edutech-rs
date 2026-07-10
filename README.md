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

## Rodar

```bash
pip install -r requirements.txt
pytest
uvicorn src.api.main:app --reload
```

## Documentação (PDF)

`docs/Motta_&_North.md` → exportar como **`Motta_&_North.pdf`**

## Repo

https://github.com/duda-north/edutech-rs
