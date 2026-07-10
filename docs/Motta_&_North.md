# Projeto Prático Integrado A — Infraestrutura Escalável da EduTech-RS

**Disciplina:** Engenharia de Software II  
**Professor:** Prof. Me. Fábio Giulian Marques  
**Alunos:** Pedro Motta & Eduarda North  
**Data:** 10/07/2026

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Regras de Negócio e Rastreabilidade](#2-regras-de-negócio-e-rastreabilidade)
3. [Diagrama de Sequência — Matrícula e Pagamento](#3-diagrama-de-sequência--matrícula-e-pagamento)
4. [Diagrama de Componentes (C4)](#4-diagrama-de-componentes-c4)
5. [Diagrama de Implantação](#5-diagrama-de-implantação)
6. [Estratégia de Branching — GitFlow](#6-estratégia-de-branching--gitflow)
7. [Pipeline CI/CD](#7-pipeline-cicd)
8. [Observabilidade — Logs, Métricas e Traces](#8-observabilidade--logs-métricas-e-traces)
9. [Padrões GoF Integrados](#9-padrões-gof-integrados)
10. [Considerações Finais](#10-considerações-finais)

---

## 1. Visão Geral

Este trabalho documenta a evolução da EduTech-RS depois do Projeto 1. Lá a gente tinha focado nos padrões GoF no código; agora o desafio era pensar em como o sistema roda de verdade — deploy, fila, monitoramento.

A principal decisão que tomamos foi na RN01: quando o pagamento demora mais de 3 segundos, o aluno não fica esperando na tela. O sistema devolve "Processando Matrícula" e joga a cobrança numa fila pra processar depois. Fizemos assim porque a Cielo/Rede é serviço de terceiro e, pelas aulas, depender de API externa em tempo real é pedir problema.

Outro ponto que definimos juntos foi separar a infra do UNISENAC e do IFSUL (RN02), já que cada um tem SO diferente pro laboratório e os dados de faturamento não podem se misturar.

---

## 2. Regras de Negócio e Rastreabilidade

| RN | Regra | Componente | Arquivo | Pipeline CI/CD |
|----|-------|------------|---------|----------------|
| RN01 | Timeout 3s → fila assíncrona | `MatriculaService`, `PaymentQueue` | `src/workers/payment_worker.py` | Teste `test_timeout_enfileira_matricula` |
| RN02 | Isolamento UNISENAC (Linux) / IFSUL (Windows) | `MatriculaBuilder` | `src/core/matricula_builder.py` | Testes `test_build_unisenac_linux`, `test_build_ifsul_windows` |
| RN03 | Log de auditoria imutável com abort | `AuditLogger` | `src/observability/audit.py` | Teste `test_falha_log_aborta_operacao` |
| RN04 | Cobertura ≥ 80%, sem credenciais | Pipeline GitHub Actions | `.github/workflows/ci-cd.yml` | Jobs `test` + `security-scan` |

---

## 3. Diagrama de Sequência — Matrícula e Pagamento

Fluxo completo evidenciando **RN01** (timeout assíncrono) e **RN03** (auditoria).

```mermaid
sequenceDiagram
    autonumber
    actor Aluno
    participant API as API Gateway<br/>(FastAPI)
    participant MS as MatriculaService
    participant PG as PaymentGateway<br/>(Factory)
    participant Cielo as Gateway Cielo/Rede
    participant Q as PaymentQueue<br/>(Fila Assíncrona)
    participant W as PaymentWorker<br/>(Background)
    participant AL as AuditLogger<br/>(RN03)
    participant LP as LabProvisioner<br/>(RN02)

    Aluno->>API: POST /api/v1/matriculas
    API->>MS: iniciar_matricula()
    MS->>AL: registrar("MATRICULA_INICIADA")
    Note over AL: timestamp_ms, IP, assinatura COREDE

  alt Pagamento síncrono (< 3s)
        MS->>PG: create(CIELO)
        PG->>Cielo: process(valor, token)
        Cielo-->>PG: PaymentResult (OK)
        PG-->>MS: success (< 3s)
        MS->>AL: registrar("LABORATORIO_PROVISIONADO")
        MS->>LP: provisionar(Linux/Windows)
        LP-->>MS: OK
        MS-->>API: status=CONFIRMADA
        API-->>Aluno: 200 "Matrícula Confirmada"
    else Timeout (> 3s) — RN01
        MS->>PG: create(CIELO)
        PG->>Cielo: process(valor, token)
        Note over Cielo: Demora > 3 segundos
        MS-->>MS: detecta timeout
        MS->>Q: enqueue(PaymentJob)
        MS->>AL: registrar("PAGAMENTO_ENFILEIRADO")
        MS-->>API: status=PROCESSANDO
        API-->>Aluno: 200 "Processando Matrícula"

        Note over W,Q: Processamento em background
        W->>Q: dequeue()
        Q-->>W: PaymentJob
        W->>PG: create(CIELO)
        PG->>Cielo: process(valor, token)
        Cielo-->>PG: PaymentResult
        PG-->>W: success
        W->>AL: registrar("LABORATORIO_PROVISIONADO")
        W->>LP: provisionar(so, tenant_db)
    end

    alt Falha no AuditLog — RN03
        MS->>AL: registrar(evento)
        AL--xMS: AuditLogFailure
        MS-->>API: ABORT operação
        API-->>Aluno: 500 "Operação abortada por segurança"
    end
```

---

## 4. Diagrama de Componentes (C4)

Visão de containers e componentes internos, mostrando desacoplamento entre regras de negócio e infraestrutura.

```mermaid
C4Component
    title Diagrama de Componentes — EduTech-RS

    Container_Boundary(api, "API Layer") {
        Component(ctrl, "MatriculaController", "FastAPI", "Recebe requisições HTTP")
        Component(health, "HealthCheck", "FastAPI", "Endpoint /health")
        Component(metrics_ep, "MetricsEndpoint", "Prometheus", "Endpoint /metrics")
    }

    Container_Boundary(core, "Core — Regras de Negócio (GoF)") {
        Component(builder, "MatriculaBuilder", "Builder Pattern", "Constrói requisições de matrícula")
        Component(factory, "PaymentGatewayFactory", "Factory Method", "Cria gateways Cielo/Rede")
        Component(config, "ConfigManager", "Singleton", "Configurações centralizadas")
    }

    Container_Boundary(services, "Application Services") {
        Component(mat_svc, "MatriculaService", "Service", "Orquestra fluxo RN01")
        Component(lab_svc, "LabProvisioner", "Service", "Provisiona lab Linux/Windows RN02")
    }

    Container_Boundary(infra, "Infrastructure") {
        Component(queue, "PaymentQueue", "In-Memory/Redis", "Fila assíncrona RN01")
        Component(worker, "PaymentWorker", "Background Job", "Processa fila")
        Component(audit, "AuditLogger", "Observability", "Logs imutáveis RN03")
        Component(tracer, "TraceProvider", "OpenTelemetry", "Traces distribuídos")
        Component(prom, "MetricsCollector", "Prometheus", "Métricas de saúde")
    }

    Rel(ctrl, builder, "usa")
    Rel(ctrl, mat_svc, "delega")
    Rel(mat_svc, factory, "cria gateway")
    Rel(mat_svc, queue, "enfileira se timeout")
    Rel(mat_svc, audit, "registra eventos")
    Rel(mat_svc, tracer, "cria spans")
    Rel(worker, queue, "consome")
    Rel(worker, factory, "processa pagamento")
    Rel(mat_svc, lab_svc, "provisiona lab")
    Rel(metrics_ep, prom, "expõe")
```

### Diagrama de Componentes UML (alternativo)

```mermaid
graph TB
    subgraph "Presentation Layer"
        API[API Gateway - FastAPI]
    end

    subgraph "Application Layer"
        MS[MatriculaService]
        PW[PaymentWorker]
    end

    subgraph "Domain Layer - GoF Patterns"
        MB[MatriculaBuilder<br/>Builder]
        PGF[PaymentGatewayFactory<br/>Factory Method]
        CM[ConfigManager<br/>Singleton]
    end

    subgraph "Infrastructure Layer"
        PQ[PaymentQueue]
        AL[AuditLogger]
        MC[MetricsCollector]
        TP[TraceProvider]
        LP[LabProvisioner]
    end

    subgraph "External Services"
        CIELO[Gateway Cielo]
        REDE[Gateway Rede]
        DB_U[(DB UNISENAC<br/>Criptografado)]
        DB_I[(DB IFSUL<br/>Criptografado)]
    end

    API --> MS
    MS --> MB
    MS --> PGF
    MS --> CM
    MS --> PQ
    MS --> AL
    MS --> TP
    MS --> MC
    PW --> PQ
    PW --> PGF
    PGF --> CIELO
    PGF --> REDE
    MS --> LP
    LP --> DB_U
    LP --> DB_I
```

---

## 5. Diagrama de Implantação

Evidencia **RN02** — isolamento de infraestrutura por instituição.

```mermaid
graph TB
    subgraph "Internet"
        ALUNO[👤 Aluno]
    end

    subgraph "Cloud — AWS sa-east-1"
        subgraph "Load Balancer"
            ALB[Application Load Balancer<br/>HTTPS :443]
        end

        subgraph "Cluster Kubernetes — Namespace: edutech-prod"
            subgraph "API Pods (replicas: 3)"
                API1[API Pod 1<br/>FastAPI :8000]
                API2[API Pod 2]
                API3[API Pod 3]
            end

            subgraph "Worker Pods (replicas: 2)"
                W1[Worker Pod 1<br/>PaymentWorker]
                W2[Worker Pod 2]
            end
        end

        subgraph "Message Broker"
            REDIS[(Redis Cluster<br/>PaymentQueue RN01)]
        end

        subgraph "Observability Stack"
            PROM[Prometheus<br/>Métricas]
            GRAF[Grafana<br/>Dashboards]
            LOKI[Loki/ELK<br/>Logs Estruturados]
            JAEGER[Jaeger<br/>Traces OTel]
        end

        subgraph "Tenant UNISENAC — RN02"
            DB_U[(PostgreSQL<br/>db_unisenac_encrypted<br/>AES-256)]
            LAB_U[🖥️ Lab Linux VMs<br/>Curso ADS]
        end

        subgraph "Tenant IFSUL — RN02"
            DB_I[(PostgreSQL<br/>db_ifsul_encrypted<br/>AES-256)]
            LAB_I[🖥️ Lab Windows VMs<br/>Curso TII]
        end
    end

    subgraph "External"
        CIELO[Gateway Cielo API]
        REDE_GW[Gateway Rede API]
    end

    ALUNO -->|HTTPS| ALB
    ALB --> API1 & API2 & API3
    API1 & API2 & API3 --> REDIS
    W1 & W2 --> REDIS
    API1 & API2 & API3 --> PROM
    API1 & API2 & API3 --> LOKI
    API1 & API2 & API3 --> JAEGER
    PROM --> GRAF
    LOKI --> GRAF
    W1 --> DB_U
    W1 --> DB_I
    W1 --> CIELO
    W2 --> REDE_GW
    DB_U --> LAB_U
    DB_I --> LAB_I
```

### Isolamento RN02 — Detalhamento

| Instituição | Curso | SO do Laboratório | Banco de Dados | Criptografia |
|-------------|-------|-------------------|----------------|--------------|
| UNISENAC | ADS | Linux (Ubuntu 22.04) | `db_unisenac_encrypted` | AES-256 at-rest |
| IFSUL | TII | Windows Server 2022 | `db_ifsul_encrypted` | AES-256 at-rest |

Os dados de faturamento **nunca compartilham** a mesma instância de banco. O `MatriculaBuilder` resolve o tenant no momento da construção da requisição.

---

## 6. Estratégia de Branching — GitFlow

### Por que escolhi GitFlow

A gente pesquisou Trunk-based também, mas pro cenário da EduTech-RS o GitFlow fez mais sentido. A startup ainda não tem cultura de deploy todo dia, e precisávamos de branches separadas — uma pra fila assíncrona (RN01) e outra pra observabilidade — sem quebrar o que já funcionava na `develop`.

Com GitFlow fazemos `feature/*` pra cada parte, mergeamos na `develop`, e só quando está estável mandamos pra `main`. Se der problema em produção, abrimos um `hotfix/*` sem bagunçar o resto. Pra dupla de devs achamos mais seguro do que commitar direto na trunk.

### Estrutura de Branches

```mermaid
gitGraph
    commit id: "init"
    branch develop
    checkout develop
    commit id: "core-gof"
    branch feature/async-queue
    checkout feature/async-queue
    commit id: "RN01-fila"
    commit id: "testes-RN01"
    checkout develop
    merge feature/async-queue
    branch feature/observability
    checkout feature/observability
    commit id: "RN03-audit"
    commit id: "RN04-metrics"
    checkout develop
    merge feature/observability
    checkout main
    merge develop tag: "v2.0.0"
    branch hotfix/payment-timeout
    checkout hotfix/payment-timeout
    commit id: "fix-timeout"
    checkout main
    merge hotfix/payment-timeout tag: "v2.0.1"
    checkout develop
    merge hotfix/payment-timeout
```

| Branch | Propósito | Proteção |
|--------|-----------|----------|
| `main` | Produção estável | PR obrigatório + CI verde |
| `develop` | Integração contínua | PR obrigatório + CI verde |
| `feature/*` | Novas funcionalidades | CI ao push |
| `release/*` | Preparação de release | Testes + cobertura ≥ 80% |
| `hotfix/*` | Correções urgentes | CI + review |

---

## 7. Pipeline CI/CD

### Fluxo da Esteira (RN04)

```mermaid
flowchart LR
    A[Push/PR] --> B{Build}
    B -->|✅| C{Test<br/>cobertura ≥ 80%}
    B -->|❌| Z[❌ Bloqueado]
    C -->|✅| D{Security Scan<br/>credenciais?}
    C -->|❌| Z
    D -->|✅| E{Deploy<br/>Homologação}
    D -->|❌| Z
    E -->|✅| F[✅ Smoke Test]
    E -->|❌| Z
    F --> G[🚀 Homologação OK]
```

### Etapas do Pipeline

| # | Etapa | O que faz | Gate RN04 |
|---|-------|-----------|-----------|
| 1 | **Build** | Instala deps, valida estrutura | Estrutura de pastas correta |
| 2 | **Test** | `pytest --cov-fail-under=80` | Cobertura ≥ 80% |
| 2b | **Security Scan** | Grep por credenciais expostas | Zero secrets no código |
| 3 | **Deploy** | Simula deploy + smoke test | Só em `main`/`develop` |

### Rastreabilidade Componente → Pipeline

O `MatriculaService` (componente do diagrama) é testado por `test_timeout_enfileira_matricula` no job **Test**. Se esse teste falhar, o deploy é **automaticamente bloqueado** — traduzindo RN04 em código.

Arquivo: `.github/workflows/ci-cd.yml`

---

## 8. Observabilidade — Logs, Métricas e Traces

### Os Três Pilares

```mermaid
graph LR
    subgraph "Logs (RN03)"
        L1[AuditLogger<br/>JSON estruturado]
        L2[Loki / ELK<br/>Agregação]
        L3[Alerta: audit_log_failure]
    end

    subgraph "Métricas"
        M1[payment_latency_seconds]
        M2[payment_errors_total]
        M3[matriculas_enfileiradas_total]
        M4[Prometheus + Grafana]
    end

    subgraph "Traces"
        T1[OpenTelemetry Spans]
        T2[Jaeger UI]
        T3[matricula.iniciar → pagamento → lab]
    end

    L1 --> L2 --> L3
    M1 & M2 & M3 --> M4
    T1 --> T2
```

### O que acontece se a Cielo começar a falhar

Pensamos nesse cenário porque o enunciado fala em resiliência. Se a API da Cielo começar a retornar 500 de forma intermitente, nossa estrutura reagiria assim:

1. **Métricas:**
   - `edutech_payment_errors_total{gateway="cielo", error_type="HTTPError"}` incrementa
   - `edutech_payment_latency_seconds` bucket `> 3.0` dispara
   - Alerta Grafana: `rate(payment_errors_total[5m]) > 0.1` → PagerDuty/Slack

2. **Logs (diagnóstico):**
   - Cada erro gera log JSON: `{"evento": "PAGAMENTO_FALHA", "gateway": "cielo", "status_code": 500}`
   - Loki query: `{app="edutech-rs"} |= "PAGAMENTO_FALHA" | json`
   - RN01 entra em ação: matrículas vão para fila em vez de falhar

3. **Traces (root cause):**
   - Span `pagamento.sincrono` mostra latência de 4.2s no trace Jaeger
   - Correlation ID liga log → métrica → trace do mesmo aluno

4. **Ação automática:**
   - Circuit breaker no `PaymentGatewayFactory` troca para gateway Rede
   - Worker processa fila retroativamente quando Cielo normaliza

### Exemplo de Log de Auditoria (RN03)

```json
{
  "aluno_id": "ALU-001",
  "timestamp_ms": 1720636800123,
  "ip_origem": "189.45.12.88",
  "assinatura_digital": "COREDE-CENTRO-SUL-SECURE-2026",
  "evento": "LABORATORIO_PROVISIONADO",
  "detalhes": {
    "so": "Linux",
    "tenant_db": "db_unisenac_encrypted"
  }
}
```

### Métricas Expostas

| Métrica | Tipo | Alerta |
|---------|------|--------|
| `edutech_payment_latency_seconds` | Histogram | p95 > 3s |
| `edutech_payment_errors_total` | Counter | rate > 10% em 5min |
| `edutech_matriculas_enfileiradas_total` | Counter | informativo |
| `edutech_audit_log_failures_total` | Counter | > 0 → CRÍTICO |
| `edutech_payment_queue_size` | Gauge | > 100 → WARNING |

---

## 9. Padrões GoF Integrados

| Padrão | Classe | Responsabilidade | Onde na Arquitetura |
|--------|--------|------------------|---------------------|
| **Singleton** | `ConfigManager` | Configurações únicas (timeout, assinatura) | Usado por `MatriculaService` e `AuditLogger` |
| **Factory Method** | `PaymentGatewayFactory` | Cria `CieloGateway` ou `RedeGateway` | Chamado por `MatriculaService` e `PaymentWorker` |
| **Builder** | `MatriculaBuilder` | Constrói `MatriculaRequest` com isolamento RN02 | Chamado pelo `MatriculaController` (API) |

O acoplamento é **unidirecional**: API → Services → Core (GoF) → Infrastructure. Os padrões do Projeto 1 foram reutilizados sem modificação de interface.

---

## 10. Considerações Finais

Montamos a pipeline de CI/CD pra garantir que nada vai pra homologação sem passar nos testes (RN04). O `MatriculaService` que aparece no diagrama de componentes é o mesmo que está em `payment_worker.py` — e tem teste cobrindo o timeout da RN01. Se a gente quebrar isso sem querer, o deploy nem roda.

Reaproveitamos os padrões do Projeto 1 (Singleton, Factory e Builder) porque já estavam funcionando e encaixaram bem na nova estrutura sem precisar reescrever tudo.

**Divisão do trabalho:** Pedro ficou com a pipeline CI/CD, diagramas de implantação e observabilidade (métricas/logs). Eduarda ficou com o código core (GoF), fila assíncrona (RN01) e diagrama de sequência.

Repositório: https://github.com/duda-north/edutech-rs
