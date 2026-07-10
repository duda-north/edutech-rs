# GUIA DE ENTREGA — Passo a Passo para Hoje

Siga esta ordem. Tempo estimado: **1h30**.

---

## PASSO 1 — Personalizar o documento (5 min)

1. Abra `docs/PROJETO_ARQUITETURAL.md`
2. Substitua `_[PREENCHA SEU NOME]_` pelo seu nome completo
3. Salve o arquivo

---

## PASSO 2 — Subir para o GitHub (15 min)

### 2.1 Criar repositório no GitHub

1. Acesse https://github.com/new
2. Nome: `edutech-rs` (ou `edutech-rs-infra`)
3. Deixe **público** (professor precisa ver commits)
4. **NÃO** marque "Add README" (já temos um)
5. Clique em **Create repository**

### 2.2 Enviar o código

Abra o PowerShell na pasta do projeto e execute:

```powershell
cd "C:\Users\Eduarda North\edutech-rs"
git remote add origin https://github.com/SEU_USUARIO/edutech-rs.git
git push -u origin main
git push origin develop
git push origin feature/async-queue
git push origin feature/observability
git push --tags
```

> Troque `SEU_USUARIO` pelo seu username do GitHub.

### 2.3 Verificar a pipeline CI/CD

1. No GitHub, vá em **Actions**
2. A pipeline deve rodar automaticamente ao fazer push
3. Aguarde ficar verde (✅) — isso prova RN04 funcionando
4. Se falhar, clique no job e veja o erro

### 2.4 Colocar o link no documento

1. Copie a URL do repositório (ex: `https://github.com/seunome/edutech-rs`)
2. Abra `docs/PROJETO_ARQUITETURAL.md`
3. Substitua `_[INSIRA O LINK DO SEU REPOSITÓRIO GITHUB AQUI]_` pelo link
4. Salve e faça commit:

```powershell
git add docs/PROJETO_ARQUITETURAL.md
git commit -m "docs: adiciona link do repositorio e nome do aluno"
git push
```

---

## PASSO 3 — Gerar o PDF (20 min)

### Opção A — VS Code / Cursor (mais fácil)

1. Instale a extensão **"Markdown PDF"** (yzane.markdown-pdf)
2. Abra `docs/PROJETO_ARQUITETURAL.md`
3. Clique direito → **Markdown PDF: Export (pdf)**
4. O PDF será gerado na mesma pasta

### Opção B — Site online (sem instalar nada)

1. Acesse https://www.markdowntopdf.com/
2. Cole o conteúdo de `docs/PROJETO_ARQUITETURAL.md`
3. Baixe o PDF

### Opção C — Pandoc (se tiver instalado)

```powershell
pandoc docs/PROJETO_ARQUITETURAL.md -o Seu_Nome.pdf --pdf-engine=wkhtmltopdf
```

### Renomear o arquivo (OBRIGATÓRIO)

- Individual: `Seu_Nome.pdf` (ex: `Silva.pdf`)
- Dupla: `Sobrenome1_&_Sobrenome2.pdf`

---

## PASSO 4 — Estudar para a banca oral (30 min)

Leia a **Seção 10** do documento. Decore estas 4 respostas:

### 1. "Como o componente se reflete no Build?"

> O `MatriculaService` é testado pelo `test_timeout_enfileira_matricula` no job **Test** da pipeline. Se quebrar, o deploy é bloqueado automaticamente (RN04).

### 2. "Por que GitFlow?"

> A startup tem releases quinzenais e precisa de hotfix sem afetar develop. Trunk-based exigiria feature flags maduras — over-engineering para o estágio atual.

### 3. "Cielo falhando com 500 — como alerta Ops?"

> Três pilares: (1) Métrica `payment_errors_total` dispara alerta Grafana em < 1 min; (2) Log JSON com evento `PAGAMENTO_FALHA` no Loki; (3) Trace Jaeger mostra latência. RN01 protege o aluno enfileirando a matrícula.

### 4. "Por que sacrificar resposta síncrona?" (RN01)

> Disponibilidade > consistência imediata (CAP). O aluno não fica 30s com tela travada. Nenhuma matrícula é perdida porque vai para fila persistente.

---

## PASSO 5 — Entregar no AVA (5 min)

1. Acesse o AVA da disciplina
2. Faça upload do PDF com o nome correto
3. Se pedirem link do repositório, cole a URL do GitHub

---

## Checklist Final

- [ ] Nome preenchido no documento
- [ ] Repositório no GitHub com histórico de commits visível
- [ ] Pipeline CI/CD verde (Actions tab)
- [ ] Branches visíveis: main, develop, feature/*
- [ ] PDF gerado com nome correto
- [ ] Diagramas renderizados no PDF (sequência, componentes, implantação)
- [ ] Seção de observabilidade presente
- [ ] Seção GitFlow presente
- [ ] Estudou respostas da banca oral

---

## Estrutura do Projeto (referência rápida)

```
edutech-rs/
├── .github/workflows/ci-cd.yml    ← Pipeline CI/CD (RN04)
├── docs/PROJETO_ARQUITETURAL.md   ← Documento principal (vira PDF)
├── src/
│   ├── core/                      ← GoF: Singleton, Factory, Builder
│   ├── api/main.py                ← API FastAPI
│   ├── workers/payment_worker.py  ← RN01: fila assíncrona
│   └── observability/             ← RN03: logs, métricas, traces
└── tests/test_core.py             ← Testes (cobertura ≥ 80%)
```

Boa sorte na defesa! 🚀
