# Guia do Desenvolvedor - Zero-Click SEO & AI Citation Monitor

## 📋 Índice

1. [Visão Geral do Projeto](#visão-geral-do-projeto)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Stack Tecnológica](#stack-tecnológica)
4. [Estrutura do Projeto](#estrutura-do-projeto)
5. [Modelos de Dados](#modelos-de-dados)
6. [API Reference](#api-reference)
7. [Serviços e Integrações](#serviços-e-integrações)
8. [Frontend](#frontend)
9. [Fluxo de Desenvolvimento](#fluxo-de-desenvolvimento)
10. [Testes](#testes)
11. [Deploy e Infraestrutura](#deploy-e-infraestrutura)
12. [Troubleshooting](#troubleshooting)
13. [Boas Práticas](#boas-práticas)

---

## Visão Geral do Projeto

O **Zero-Click SEO & AI Citation Monitor** é uma plataforma de monitoramento e análise de citações em respostas de IA (AI Overviews, Bing Copilot, Perplexity, etc.) e SERP tradicional. O sistema permite:

- **Monitorar citações** de domínios específicos em respostas de IA
- **Calcular KPIs** como AMR (AI Mention Rate), DCR (Domain Citation Rate), ZCRS (Zero-Click Response Score)
- **Classificar respostas** usando IA (Gemini 2.5 Pro) para análise zero-click
- **Agendar execuções** periódicas com CRON
- **Gerar insights** automatizados sobre presença de marca e oportunidades
- **Exportar dados** em CSV para análise externa

### Objetivos do Sistema

1. **Visibilidade**: Rastrear onde e como marcas aparecem em respostas de IA
2. **Métricas**: Quantificar presença e relevância através de KPIs padronizados
3. **Insights**: Identificar oportunidades de otimização e gaps de conteúdo
4. **Automação**: Executar monitoramento contínuo sem intervenção manual

---

## Arquitetura do Sistema

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React + Vite + TypeScript + TailwindCSS + shadcn/ui       │
│  - Dashboard Analytics                                       │
│  - Run Management (SSE real-time)                           │
│  - Monitor Scheduling                                        │
│  - Template Management                                       │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTP/REST + SSE
┌──────────────────▼──────────────────────────────────────────┐
│                      BACKEND API                             │
│              FastAPI + SQLAlchemy                            │
│  - REST Endpoints                                            │
│  - SSE Streaming (Run Events)                               │
│  - Authentication & Authorization                            │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┬──────────────┐
        │                     │              │
┌───────▼────────┐  ┌────────▼──────┐  ┌───▼──────────┐
│   DATABASE     │  │  REDIS/CELERY │  │   ADAPTERS   │
│  Azure SQL     │  │  Task Queue   │  │  - Gemini    │
│  (pyodbc)      │  │  Scheduler    │  │  - OpenAI    │
└────────────────┘  └───────────────┘  │  - Perplexity│
                                        │  - SERP API  │
                                        │  - Playwright│
                                        └──────────────┘
```

### Fluxo de Execução de Run

```
1. User/Monitor → POST /api/runs (payload)
2. Backend → Enqueue task (Celery)
3. Worker → Pick task from Redis queue
4. Worker → Execute engine adapter (Gemini/OpenAI/Perplexity/SERP)
5. Worker → Stream events via SSE (RunEvent)
6. Worker → Extract citations, calculate KPIs
7. Worker → Classify response (Gemini classifier)
8. Worker → Save results to database
9. Frontend → Display real-time updates via SSE
```

---

## Stack Tecnológica

### Backend

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **Python** | 3.11+ | Linguagem principal |
| **FastAPI** | 0.111.0 | Framework web assíncrono |
| **SQLAlchemy** | 2.0.30 | ORM para banco de dados |
| **Pydantic** | 2.8.2 | Validação de dados e schemas |
| **Celery** | 5.4.0 | Task queue para jobs assíncronos |
| **Redis** | 5.0.7 | Message broker e cache |
| **pyodbc** | 5.1.0 | Driver para Azure SQL Server |
| **httpx** | 0.28.1 | Cliente HTTP assíncrono |
| **Playwright** | 1.46.0 | Browser automation para SERP |
| **OpenAI SDK** | 1.99.7 | Integração com GPT models |
| **Google GenAI** | 1.29.0 | Integração com Gemini |
| **croniter** | 2.0.1 | Parser de expressões CRON |

### Frontend

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **React** | 18.3+ | Framework UI |
| **TypeScript** | 5.5+ | Type safety |
| **Vite** | 5.4+ | Build tool e dev server |
| **TailwindCSS** | 3.4+ | Utility-first CSS |
| **shadcn/ui** | Latest | Componentes UI modernos |
| **Recharts** | 2.12+ | Gráficos e visualizações |
| **Axios** | 1.7+ | Cliente HTTP |
| **React Router** | 6.26+ | Roteamento SPA |
| **Lucide React** | Latest | Ícones |

### Infraestrutura

- **Database**: Azure SQL Server (via pyodbc)
- **Cache/Queue**: Redis
- **Container**: Docker + Docker Compose
- **Reverse Proxy**: Nginx (produção) / Caddy (alternativa)
- **Deploy**: Oracle Cloud Infrastructure (OCI)

---

## Estrutura do Projeto

```
SEO Analyzer/
├── backend/                    # Backend FastAPI
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py      # Todos os endpoints REST
│   │   ├── core/
│   │   │   ├── config.py      # Configurações (env vars)
│   │   │   └── security.py    # Auth/JWT (se houver)
│   │   ├── db/
│   │   │   ├── base.py        # Base SQLAlchemy
│   │   │   └── session.py     # Engine e SessionLocal
│   │   ├── models/
│   │   │   └── models.py      # Modelos SQLAlchemy
│   │   ├── schemas/
│   │   │   └── schemas.py     # Pydantic schemas
│   │   ├── services/
│   │   │   ├── adapters/      # Integrações externas
│   │   │   │   ├── gemini.py
│   │   │   │   ├── openai_adapter.py
│   │   │   │   ├── perplexity.py
│   │   │   │   └── serp.py
│   │   │   ├── tasks.py       # Celery tasks
│   │   │   ├── scheduler.py   # Monitor scheduler (CRON)
│   │   │   ├── kpis.py        # Cálculo de métricas
│   │   │   ├── insights.py    # Geração de insights
│   │   │   ├── classification_integration.py
│   │   │   ├── response_classifier.py
│   │   │   ├── gemini_classifier.py
│   │   │   └── advanced_metrics.py
│   │   └── main.py            # Entry point FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   └── celery_app.py          # Celery worker config
│
├── frontend/                   # Frontend React
│   ├── src/
│   │   ├── assets/            # Imagens, fonts
│   │   ├── components/        # Componentes React
│   │   │   ├── ui/            # shadcn/ui components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Projects.tsx
│   │   │   ├── Subprojects.tsx
│   │   │   ├── Templates.tsx
│   │   │   ├── Monitors.tsx
│   │   │   ├── Runs.tsx
│   │   │   └── RunDetail.tsx
│   │   ├── lib/
│   │   │   ├── api.ts         # Funções de API
│   │   │   └── utils.ts       # Helpers
│   │   ├── pages/             # Páginas principais
│   │   ├── App.tsx
│   │   └── main.tsx           # Entry point
│   ├── Dockerfile.frontend
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── scripts/                    # Scripts utilitários
│   ├── classify_existing_runs.py
│   ├── gemini_retroactive_analysis.py
│   ├── backfill_is_ours.py
│   └── backup-database.sh
│
├── deploy/                     # Configurações de deploy
│   ├── nginx.conf
│   └── ssl/
│
├── docs/                       # Documentação adicional
│   ├── README-UX.md
│   ├── CLOUDFLARE_DNS_SETUP.md
│   └── SUBDOMAIN_SETUP.md
│
├── docker-compose.yml          # Dev environment
├── docker-compose.prod.yml     # Production environment
├── .env                        # Environment variables (não commitar!)
├── .gitignore
├── README.md
├── DEVELOPMENT.md
├── DEVELOPER_GUIDE.md          # Este arquivo
└── ZERO_CLICK_CLASSIFICATION.md
```

---

## Modelos de Dados

### Entidades Principais

#### 1. Project
Representa um projeto/cliente que será monitorado.

```python
class Project(Base):
    id: str              # prj_xxxxxxxx
    name: str            # Nome do projeto
    country: str         # País (ex: "BR")
    language: str        # Idioma (ex: "pt-BR")
    timezone: str        # Timezone (ex: "America/Sao_Paulo")
    created_by: str      # Usuário criador
```

#### 2. Domain
Domínios-alvo que queremos rastrear nas citações.

```python
class Domain(Base):
    id: str              # dom_xxxxxxxx
    project_id: str      # FK → projects.id
    domain: str          # Ex: "bb.com.br"
    pattern_regex: str   # Regex opcional para match
    is_primary: bool     # Domínio principal?
```

#### 3. SubProject
Agrupamento lógico de runs (ex: "Conta Universitária", "Crédito Imobiliário").

```python
class SubProject(Base):
    id: str              # sub_xxxxxxxx
    project_id: str      # FK → projects.id
    name: str            # Nome do subprojeto
    description: str     # Descrição opcional
```

#### 4. PromptTemplate
Templates de prompts reutilizáveis por categoria.

```python
class PromptTemplate(Base):
    id: str              # tpl_xxxxxxxx
    project_id: str      # FK → projects.id
    subproject_id: str   # FK → subprojects.id (opcional)
    category: str        # Ex: "Abertura PF", "Seguro Auto"
    name: str            # Nome do template
    text: str            # Texto do prompt
    intent: str          # Intenção (informational, transactional, etc.)
    persona: str         # Persona do usuário
```

#### 5. Engine
Configuração de engines (modelos de IA ou SERP).

```python
class Engine(Base):
    id: str              # eng_xxxxxxxx
    project_id: str      # FK → projects.id
    name: str            # Ex: "gemini-2.0-flash", "gpt-4o", "google-serp"
    region: str          # Região (ex: "BR", "US")
    device: str          # Dispositivo (ex: "desktop", "mobile")
    config_json: dict    # Configurações adicionais (JSON)
```

#### 6. Monitor
Agendamento de execuções periódicas (CRON).

```python
class Monitor(Base):
    id: str              # mon_xxxxxxxx
    project_id: str      # FK → projects.id
    subproject_id: str   # FK → subprojects.id (opcional)
    name: str            # Nome do monitor
    schedule_cron: str   # Expressão CRON (ex: "0 2 * * *")
    engines_json: dict   # Lista de engines a executar
    active: bool         # Ativo/pausado
```

#### 7. Run
Execução individual de um prompt em uma engine.

```python
class Run(Base):
    id: str                     # run_xxxxxxxx
    project_id: str             # FK → projects.id
    prompt_version_id: str      # FK → prompt_versions.id
    engine_id: str              # FK → engines.id
    subproject_id: str          # FK → subprojects.id (opcional)
    monitor_id: str             # FK → monitors.id (opcional)
    status: str                 # queued, running, completed, error
    cycles_total: int           # Número de ciclos executados
    cycle_delay_seconds: int    # Delay entre ciclos
    started_at: datetime
    finished_at: datetime
    
    # Métricas básicas
    zcrs: float                 # Zero-Click Response Score
    amr_flag: bool              # AI Mention Rate (citou?)
    dcr_flag: bool              # Domain Citation Rate (citou domínio?)
    
    # Observabilidade
    tokens_input: int
    tokens_output: int
    tokens_total: int
    cost_usd: float
    latency_ms: int
    citations_count: int
    our_citations_count: int
    unique_domains_count: int
    model_name: str
    error_code: str
    
    # Classificação Zero-Click
    response_type: str          # direta, explicativa, instrucional, etc.
    sufficiency_level: str      # total, parcial, insuficiente
    actionability_type: str     # transacional, informativa
    trust_source: str           # citada, generica
    brand_positioning: str      # protagonista, competidor, ausente
    question_type: str          # marca, produto, informacao, comparacao
    funnel_stage: str           # reconhecimento, consideracao, conversao
    classification_confidence: float
    classified_at: datetime
    classification_version: str
    
    # Métricas avançadas
    user_intent: str            # informational, transactional, navigational, commercial
    satisfaction_score: float   # 0.0-1.0
    competitive_mentions: int
    financial_value_score: float # 0.0-10.0
    content_gap_detected: bool
    conversion_potential: str   # alto, medio, baixo
    
    # Metadados de agendamento
    schedule_date: datetime
    schedule_slot: str
    schedule_index_today: int
    schedule_total_today: int
    schedule_source: str        # manual, monitor, monitor_now
```

#### 8. Citation
Citações extraídas das respostas.

```python
class Citation(Base):
    id: str              # cit_xxxxxxxx
    run_id: str          # FK → runs.id
    url: str             # URL citada
    title: str           # Título da página
    snippet: str         # Snippet/descrição
    position: int        # Posição na resposta
    is_ours: bool        # É do nosso domínio?
```

#### 9. RunEvent
Eventos de execução (streaming SSE).

```python
class RunEvent(Base):
    id: str              # evt_xxxxxxxx
    run_id: str          # FK → runs.id
    version: int         # Versão do evento (sequencial)
    event_type: str      # started, progress, chunk, tool_call, completed, error
    data_json: dict      # Dados do evento (JSON)
    timestamp: datetime
```

#### 10. Insight
Insights gerados automaticamente (IA).

```python
class Insight(Base):
    id: str              # ins_xxxxxxxx
    project_id: str      # FK → projects.id
    run_id: str          # FK → runs.id (opcional)
    subproject_id: str   # FK → subprojects.id (opcional)
    insight_type: str    # opportunity, warning, trend, recommendation
    title: str
    description: str
    priority: str        # high, medium, low
    created_at: datetime
```

### Relacionamentos

```
Project (1) ──< (N) Domain
Project (1) ──< (N) SubProject
Project (1) ──< (N) PromptTemplate
Project (1) ──< (N) Engine
Project (1) ──< (N) Monitor
Project (1) ──< (N) Run

SubProject (1) ──< (N) PromptTemplate
SubProject (1) ──< (N) Monitor
SubProject (1) ──< (N) Run

Monitor (1) ──< (N) Run

Run (1) ──< (N) Citation
Run (1) ──< (N) RunEvent
Run (1) ──< (N) Insight
```

---

## API Reference

### Base URL
- **Development**: `http://localhost:8000/api`
- **Production**: `https://your-domain.com/api`

### Autenticação
Atualmente o sistema não possui autenticação. Para adicionar:
- Implementar JWT em `backend/app/core/security.py`
- Adicionar middleware de autenticação em `main.py`
- Proteger rotas com `Depends(get_current_user)`

### Endpoints Principais

#### Projects

```http
POST   /api/projects
GET    /api/projects
GET    /api/projects/{project_id}
PATCH  /api/projects/{project_id}
DELETE /api/projects/{project_id}
```

**Exemplo - Criar Projeto:**
```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Banco do Brasil",
    "country": "BR",
    "language": "pt-BR",
    "timezone": "America/Sao_Paulo"
  }'
```

#### Domains

```http
GET    /api/projects/{project_id}/domains
POST   /api/projects/{project_id}/domains
DELETE /api/domains/{domain_id}
```

**Exemplo - Adicionar Domínio:**
```bash
curl -X POST http://localhost:8000/api/projects/{project_id}/domains \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "bb.com.br",
    "is_primary": true
  }'
```

#### Subprojects

```http
GET    /api/projects/{project_id}/subprojects
POST   /api/projects/{project_id}/subprojects
PATCH  /api/subprojects/{subproject_id}
DELETE /api/subprojects/{subproject_id}
```

#### Templates

```http
GET    /api/projects/{project_id}/templates
POST   /api/projects/{project_id}/templates
PATCH  /api/templates/{template_id}
DELETE /api/templates/{template_id}
```

#### Engines

```http
GET    /api/projects/{project_id}/engines
PATCH  /api/projects/{project_id}/engines
```

#### Monitors

```http
GET    /api/projects/{project_id}/monitors
POST   /api/projects/{project_id}/monitors
PATCH  /api/monitors/{monitor_id}
DELETE /api/monitors/{monitor_id}
POST   /api/monitors/{monitor_id}/run              # Executar agora
POST   /api/monitors/{monitor_id}/templates/{template_id}
DELETE /api/monitors/{monitor_id}/templates/{template_id}
GET    /api/monitors/{monitor_id}/history
GET    /api/monitors/{monitor_id}/export.csv       # Export agregado
GET    /api/monitors/{monitor_id}/export_full.csv  # Export completo
```

**Exemplo - Criar Monitor:**
```bash
curl -X POST http://localhost:8000/api/projects/{project_id}/monitors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Monitor Diário - Conta Universitária",
    "subproject_id": "sub_12345678",
    "schedule_cron": "0 2 * * *",
    "engines_json": [
      {"name": "gemini-2.0-flash"},
      {"name": "gpt-4o"}
    ],
    "active": true
  }'
```

#### Runs

```http
POST   /api/runs
GET    /api/runs                    # Filtros: subproject_id, engine, status, limit
GET    /api/runs/{run_id}
DELETE /api/runs/{run_id}
GET    /api/runs/{run_id}/events
GET    /api/runs/{run_id}/stream    # SSE (Server-Sent Events)
GET    /api/runs/{run_id}/report
GET    /api/runs/{run_id}/evidences
```

**Exemplo - Criar Run:**
```bash
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "prj_12345678",
    "prompt_version_id": "pv_87654321",
    "engines": [
      {
        "name": "gemini-2.0-flash",
        "region": "BR",
        "device": "desktop",
        "config_json": {"use_search": true}
      }
    ],
    "cycles": 1,
    "subproject_id": "sub_12345678"
  }'
```

**Exemplo - SSE Stream (JavaScript):**
```javascript
const eventSource = new EventSource(`/api/runs/${runId}/stream`);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.event_type, data.data_json);
};

eventSource.onerror = () => {
  eventSource.close();
  // Fallback para polling
};
```

#### Analytics

```http
GET /api/analytics/overview
GET /api/analytics/subprojects/{subproject_id}/overview
GET /api/analytics/subprojects/{subproject_id}/series
GET /api/analytics/subprojects/{subproject_id}/top-domains
GET /api/analytics/subprojects/{subproject_id}/export.csv
```

#### Classification

```http
POST   /api/runs/{run_id}/classify                      # Classificação básica
POST   /api/runs/{run_id}/classify/gemini               # Classificação Gemini
POST   /api/projects/{project_id}/classify/batch        # Lote básico
POST   /api/projects/{project_id}/classify/gemini/batch # Lote Gemini
GET    /api/projects/{project_id}/classification/stats
GET    /api/projects/{project_id}/insights/gemini
GET    /api/classification/unprocessed
POST   /api/classification/migrate-to-gemini
```

#### Utilities

```http
GET /api/utils/url-title?url=https://example.com
```

---

## Serviços e Integrações

### 1. Adapters (Integrações Externas)

#### Gemini Adapter (`backend/app/services/adapters/gemini.py`)

```python
async def run_gemini(
    prompt: str,
    model: str = "gemini-2.0-flash-exp",
    use_search: bool = True,
    config: dict = None
) -> dict:
    """
    Executa prompt no Gemini com grounding opcional.
    
    Returns:
        {
            "response": str,
            "citations": [{"url": str, "title": str, ...}],
            "tokens": {"input": int, "output": int},
            "model": str
        }
    """
```

**Configuração:**
- `GOOGLE_API_KEY` ou `GEMINI_API_KEY` no `.env`
- Suporta `google_search` tool (grounding)
- Fallback automático se tool não disponível

#### OpenAI Adapter (`backend/app/services/adapters/openai_adapter.py`)

```python
async def run_openai(
    prompt: str,
    model: str = "gpt-4o",
    config: dict = None
) -> dict:
    """
    Executa prompt no OpenAI.
    Extrai URLs por regex (não tem grounding nativo).
    """
```

**Configuração:**
- `OPENAI_API_KEY` no `.env`
- `OPENAI_ORG_ID` (opcional): `org-cwSHSUpwENqGkjtok0zVm4cu`
- `OPENAI_PROJECT_ID` (opcional): `proj_5KNRTmP5Ojg4fqdEBloLhile`

#### Perplexity Adapter (`backend/app/services/adapters/perplexity.py`)

```python
async def run_perplexity(
    prompt: str,
    model: str = "sonar",
    config: dict = None
) -> dict:
    """
    Executa prompt no Perplexity.
    Retorna citations e search_results nativos.
    """
```

**Configuração:**
- `PERPLEXITY_API_KEY` no `.env`

#### SERP Adapter (`backend/app/services/adapters/serp.py`)

```python
async def run_google_serp(
    query: str,
    region: str = "BR",
    device: str = "desktop"
) -> dict:
    """
    Captura SERP do Google via Playwright (headless).
    Fallback para SerpAPI se Playwright falhar.
    """
```

**Configuração:**
- `SERPAPI_KEY` no `.env` (fallback)
- Playwright instalado automaticamente no container

### 2. Task Queue (Celery)

#### Configuração (`backend/celery_app.py`)

```python
from celery import Celery

celery_app = Celery(
    "seo_analyzer",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
```

#### Tasks Principais (`backend/app/services/tasks.py`)

```python
@celery_app.task
def enqueue_run(run_id: str):
    """
    Task principal: executa run completa.
    
    Fluxo:
    1. Busca Run no DB
    2. Executa adapter correspondente
    3. Stream eventos via RunEvent
    4. Extrai citações
    5. Calcula KPIs
    6. Classifica resposta (Gemini)
    7. Salva resultados
    """
```

**Executar Worker:**
```bash
# Dev
docker compose up worker

# Manual
cd backend
celery -A celery_app worker --loglevel=info
```

### 3. Scheduler (CRON Monitors)

#### Implementação (`backend/app/services/scheduler.py`)

```python
async def start_scheduler():
    """
    Loop infinito que verifica monitors ativos.
    Usa croniter para calcular próxima execução.
    """
    while True:
        monitors = db.query(Monitor).filter(Monitor.active == True).all()
        for monitor in monitors:
            if should_run(monitor.schedule_cron):
                await execute_monitor(monitor.id)
        await asyncio.sleep(60)  # Check a cada 1 minuto
```

**Expressões CRON Comuns:**
- `0 2 * * *` - Diário às 02:00
- `0 6 * * 1-5` - Dias úteis às 06:00
- `0 3 * * 0` - Semanal (domingo) às 03:00
- `*/30 * * * *` - A cada 30 minutos

### 4. KPIs e Métricas (`backend/app/services/kpis.py`)

```python
def compute_run_report(run: Run, citations: List[Citation], domains: List[Domain]) -> dict:
    """
    Calcula métricas:
    - AMR (AI Mention Rate): bool - citou algum domínio nosso?
    - DCR (Domain Citation Rate): bool - citou domínio específico?
    - ZCRS (Zero-Click Response Score): float 0-100
    - Citations count, unique domains, etc.
    """
```

**Fórmula ZCRS:**
```
ZCRS = (our_citations / total_citations) * 100
```

### 5. Classification System

#### Response Classifier (`backend/app/services/response_classifier.py`)

Classificação baseada em regras e padrões de texto.

```python
class ResponseClassifier:
    def classify(self, response_text: str, prompt_text: str, citations: List[Citation]) -> dict:
        """
        Retorna:
        {
            "response_type": str,
            "sufficiency_level": str,
            "actionability_type": str,
            "trust_source": str,
            "brand_positioning": str,
            "question_type": str,
            "funnel_stage": str,
            "confidence": float
        }
        """
```

#### Gemini Classifier (`backend/app/services/gemini_classifier.py`)

Classificação avançada usando Gemini 2.5 Pro.

```python
class GeminiZeroClickAnalyzer:
    async def analyze_run(self, run_id: str) -> dict:
        """
        Análise completa com IA:
        - Classificação básica
        - Métricas avançadas
        - Insights estratégicos
        - Oportunidades de otimização
        """
```

#### Advanced Metrics (`backend/app/services/advanced_metrics.py`)

```python
class AdvancedMetricsAnalyzer:
    def analyze(self, response: str, citations: List[Citation]) -> dict:
        """
        Calcula:
        - user_intent
        - satisfaction_score
        - competitive_mentions
        - financial_value_score
        - content_gap_detected
        - conversion_potential
        """
```

### 6. Insights Generation (`backend/app/services/insights.py`)

```python
async def generate_subproject_insights(
    project_id: str,
    subproject_id: str,
    days: int = 7
) -> dict:
    """
    Gera insights agregados usando OpenAI:
    - Tendências
    - Oportunidades
    - Alertas
    - Recomendações
    """
```

---

## Frontend

### Estrutura de Componentes

```
src/
├── components/
│   ├── ui/                    # shadcn/ui base components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── select.tsx
│   │   └── ...
│   ├── Dashboard.tsx          # Dashboard principal
│   ├── Projects.tsx           # Gestão de projetos
│   ├── Subprojects.tsx        # Gestão de subprojetos
│   ├── Templates.tsx          # Gestão de templates
│   ├── Monitors.tsx           # Gestão de monitors
│   ├── Runs.tsx               # Lista de runs
│   └── RunDetail.tsx          # Detalhe de run (SSE)
```

### API Client (`frontend/src/lib/api.ts`)

```typescript
import axios from 'axios'

export const http = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' }
})

// Funções principais
export const createProject = (data: ProjectCreate) => 
  http.post('/projects', data)

export const createRun = (data: CreateRunPayload) => 
  http.post('/runs', data)

export const deleteRun = (runId: string) => 
  http.delete(`/runs/${runId}`)

export const getRunDetail = (runId: string) => 
  http.get<RunDetail>(`/runs/${runId}`)

// ... mais funções
```

### SSE (Server-Sent Events)

```typescript
// Em RunDetail.tsx
useEffect(() => {
  const eventSource = new EventSource(`/api/runs/${runId}/stream`)
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    switch (data.event_type) {
      case 'started':
        setStatus('running')
        break
      case 'chunk':
        appendMarkdown(data.data_json.text)
        break
      case 'tool_call':
        updateToolbelt(data.data_json)
        break
      case 'completed':
        setStatus('completed')
        eventSource.close()
        break
      case 'error':
        setError(data.data_json.message)
        eventSource.close()
        break
    }
  }
  
  eventSource.onerror = () => {
    eventSource.close()
    // Fallback para polling
    startPolling()
  }
  
  return () => eventSource.close()
}, [runId])
```

### Componentes shadcn/ui

Instalados via CLI:
```bash
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add dialog
# etc.
```

Uso:
```tsx
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

<Card>
  <CardHeader>
    <CardTitle>Run Detail</CardTitle>
  </CardHeader>
  <CardContent>
    <Button onClick={handleDelete}>Delete</Button>
  </CardContent>
</Card>
```

### Roteamento

```typescript
// main.tsx
import { createBrowserRouter, RouterProvider } from 'react-router-dom'

const router = createBrowserRouter([
  { path: '/', element: <Dashboard /> },
  { path: '/projects', element: <Projects /> },
  { path: '/subprojects', element: <Subprojects /> },
  { path: '/templates', element: <Templates /> },
  { path: '/monitors', element: <Monitors /> },
  { path: '/runs', element: <Runs /> },
  { path: '/runs/:runId', element: <RunDetail /> },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <RouterProvider router={router} />
)
```

---

## Fluxo de Desenvolvimento

### 1. Setup Inicial

```bash
# Clone o repositório
git clone <repo-url>
cd "SEO Analyzer"

# Crie o .env
cp .env.example .env
# Edite .env com suas chaves de API

# Suba o ambiente de desenvolvimento
docker compose up -d --build

# Acesse:
# - Frontend: http://localhost:5173
# - Backend: http://localhost:8000/docs
```

### 2. Desenvolvimento Backend

```bash
# Logs do backend
docker compose logs -f backend

# Logs do worker
docker compose logs -f worker

# Acessar container
docker compose exec backend bash

# Executar migrations (se usar Alembic)
docker compose exec backend alembic upgrade head
```

**Hot Reload:**
- FastAPI com `--reload` ativo
- Mudanças em `backend/app/` recarregam automaticamente

### 3. Desenvolvimento Frontend

```bash
# Instalar dependências localmente (opcional)
cd frontend
npm install

# Dev server (já roda no Docker)
npm run dev

# Build para produção
npm run build

# Lint
npm run lint
```

**Hot Reload:**
- Vite com HMR ativo
- Mudanças em `frontend/src/` atualizam instantaneamente

### 4. Adicionar Nova Feature

#### Exemplo: Adicionar campo `priority` em Run

**1. Atualizar modelo (`backend/app/models/models.py`):**
```python
class Run(Base):
    # ... campos existentes
    priority: Mapped[Optional[str]] = mapped_column(String, nullable=True)
```

**2. Adicionar migração SQL (`backend/app/main.py`):**
```python
# Em on_startup()
stmts = [
    # ... migrações existentes
    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS priority VARCHAR(20)",
]
```

**3. Atualizar schema (`backend/app/schemas/schemas.py`):**
```python
class RunOut(BaseModel):
    # ... campos existentes
    priority: Optional[str] = None
```

**4. Atualizar API (`backend/app/api/routes.py`):**
```python
@api_router.patch("/runs/{run_id}/priority")
def update_run_priority(run_id: str, priority: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    run.priority = priority
    db.commit()
    return {"status": "ok"}
```

**5. Atualizar frontend (`frontend/src/lib/api.ts`):**
```typescript
export type RunListItem = {
  // ... campos existentes
  priority?: string
}

export const updateRunPriority = (runId: string, priority: string) =>
  http.patch(`/runs/${runId}/priority`, { priority })
```

**6. Atualizar UI (`frontend/src/components/Runs.tsx`):**
```tsx
<Badge variant={run.priority === 'high' ? 'destructive' : 'default'}>
  {run.priority || 'normal'}
</Badge>
```

**7. Testar:**
```bash
# Reiniciar backend
docker compose restart backend

# Verificar no Swagger
open http://localhost:8000/docs

# Testar no frontend
open http://localhost:5173/runs
```

### 5. Debugging

#### Backend
```bash
# Adicionar breakpoint (pdb)
import pdb; pdb.set_trace()

# Logs detalhados
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Frontend
```typescript
// Console logs
console.log('Debug:', data)

// React DevTools
// Instalar extensão no Chrome/Firefox
```

---

## Testes

### Backend Tests

```bash
# Instalar pytest
cd backend
pip install pytest pytest-asyncio

# Criar tests/
mkdir tests
touch tests/__init__.py
touch tests/test_kpis.py
```

**Exemplo de teste:**
```python
# tests/test_kpis.py
import pytest
from app.services.kpis import compute_run_report
from app.models.models import Run, Citation, Domain

def test_zcrs_calculation():
    run = Run(id="run_test")
    citations = [
        Citation(url="https://bb.com.br/page1", is_ours=True),
        Citation(url="https://competitor.com/page2", is_ours=False),
    ]
    domains = [Domain(domain="bb.com.br")]
    
    report = compute_run_report(run, citations, domains)
    
    assert report["zcrs"] == 50.0  # 1/2 = 50%
    assert report["amr_flag"] is True
```

**Executar testes:**
```bash
pytest tests/ -v
```

### Frontend Tests

```bash
cd frontend
npm install --save-dev vitest @testing-library/react

# Criar tests/
mkdir src/__tests__
touch src/__tests__/api.test.ts
```

**Exemplo de teste:**
```typescript
// src/__tests__/api.test.ts
import { describe, it, expect } from 'vitest'
import { http } from '../lib/api'

describe('API Client', () => {
  it('should have correct base URL', () => {
    expect(http.defaults.baseURL).toBe('/api')
  })
})
```

**Executar testes:**
```bash
npm test
```

### Integration Tests

```bash
# Criar docker-compose.test.yml
# Executar stack de teste
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## Deploy e Infraestrutura

### Ambiente de Produção

#### 1. Oracle Cloud Infrastructure (OCI)

**Configuração atual:**
- **IP Público**: `129.148.63.199`
- **Frontend**: Porta 80 (Nginx)
- **Backend**: Porta 8000 (interno)
- **Database**: Azure SQL Server (externo)

**Arquivos de deploy:**
- `docker-compose.prod.yml`
- `deploy/nginx.conf`
- `deploy/ssl/` (certificados Cloudflare)

#### 2. Azure SQL Server

**Connection String:**
```
DRIVER={ODBC Driver 18 for SQL Server};
SERVER=seoanalyzer.database.windows.net,1433;
DATABASE=SEO;
UID=iqui27;
PWD=<password>;
Encrypt=yes;
TrustServerCertificate=yes;
Connection Timeout=30;
```

**Configuração no `.env`:**
```bash
DATABASE_URL=mssql+pyodbc://iqui27:<password>@seoanalyzer.database.windows.net:1433/SEO?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes
```

**Firewall:**
- Adicionar IP do servidor OCI nas regras de firewall do Azure

#### 3. Deploy Steps

```bash
# 1. SSH no servidor OCI
ssh opc@129.148.63.199

# 2. Navegar para o diretório
cd /opt/seo-analyzer

# 3. Atualizar código (via git ou scp)
git pull origin main
# ou
scp -r . opc@129.148.63.199:/opt/seo-analyzer/

# 4. Atualizar .env com variáveis de produção
nano .env

# 5. Build e restart
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build

# 6. Verificar logs
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend

# 7. Health check
curl http://localhost:8000/health
curl http://localhost:5173
```

#### 4. Nginx Configuration

```nginx
# deploy/nginx.conf
server {
    listen 80;
    server_name 129.148.63.199;

    # Frontend
    location / {
        proxy_pass http://frontend:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # SSE (Server-Sent Events)
    location /api/runs/ {
        proxy_pass http://backend:8000;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

#### 5. SSL/TLS (Cloudflare)

```bash
# Certificados em deploy/ssl/
cloudflare-cert.pem
cloudflare-key.pem

# Configurar Nginx para HTTPS
listen 443 ssl;
ssl_certificate /etc/nginx/ssl/cloudflare-cert.pem;
ssl_certificate_key /etc/nginx/ssl/cloudflare-key.pem;
```

#### 6. Backup Database

```bash
# Script de backup (scripts/backup-database.sh)
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_${DATE}.sql"

# Backup via Azure CLI ou sqlcmd
sqlcmd -S seoanalyzer.database.windows.net \
  -U iqui27 -P <password> \
  -d SEO \
  -Q "BACKUP DATABASE SEO TO DISK = '/backups/${BACKUP_FILE}'"

echo "Backup saved: ${BACKUP_FILE}"
```

**Agendar backup (cron):**
```bash
# Editar crontab
crontab -e

# Adicionar linha (backup diário às 03:00)
0 3 * * * /opt/seo-analyzer/scripts/backup-database.sh
```

### Monitoramento

#### 1. Logs

```bash
# Backend logs
docker compose -f docker-compose.prod.yml logs -f backend

# Worker logs
docker compose -f docker-compose.prod.yml logs -f worker

# Nginx logs
docker compose -f docker-compose.prod.yml logs -f nginx
```

#### 2. Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/api/projects
```

#### 3. Métricas (Futuro)

- Integrar Prometheus + Grafana
- Adicionar OpenTelemetry
- Configurar alertas (email/Slack)

---

## Troubleshooting

### Problemas Comuns

#### 1. Backend não conecta ao Azure SQL

**Sintomas:**
- `pyodbc.OperationalError: HYT00 Login timeout expired`
- Backend não inicia

**Soluções:**
1. Verificar firewall do Azure SQL:
   ```bash
   # Adicionar IP do servidor nas regras de firewall
   ```
2. Testar conexão manualmente:
   ```bash
   docker run --rm -it mcr.microsoft.com/mssql-tools \
     /opt/mssql-tools/bin/sqlcmd \
     -S seoanalyzer.database.windows.net \
     -U iqui27 -P <password> \
     -Q "SELECT 1"
   ```
3. Verificar DNS:
   ```bash
   nslookup seoanalyzer.database.windows.net
   ```
4. Adicionar `extra_hosts` no `docker-compose.prod.yml`:
   ```yaml
   services:
     backend:
       extra_hosts:
         - "seoanalyzer.database.windows.net:191.234.142.161"
   ```

#### 2. SSE não funciona (Run Detail não atualiza)

**Sintomas:**
- Timeline não atualiza em tempo real
- Frontend cai em polling

**Soluções:**
1. Verificar Nginx config (proxy_buffering off):
   ```nginx
   location /api/runs/ {
       proxy_buffering off;
       proxy_cache off;
   }
   ```
2. Verificar CORS:
   ```python
   # backend/app/main.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
   )
   ```
3. Testar SSE diretamente:
   ```bash
   curl -N http://localhost:8000/api/runs/{run_id}/stream
   ```

#### 3. Frontend build falha

**Sintomas:**
- `ENOTEMPTY: directory not empty`
- `vite: not found`

**Soluções:**
1. Limpar node_modules:
   ```bash
   docker compose exec frontend rm -rf node_modules
   docker compose restart frontend
   ```
2. Force reinstall:
   ```bash
   docker compose exec frontend npm install --force
   ```

#### 4. Celery worker não processa tasks

**Sintomas:**
- Runs ficam em `queued` indefinidamente
- Worker logs não mostram atividade

**Soluções:**
1. Verificar Redis:
   ```bash
   docker compose exec redis redis-cli ping
   # Deve retornar: PONG
   ```
2. Verificar worker logs:
   ```bash
   docker compose logs -f worker
   ```
3. Reiniciar worker:
   ```bash
   docker compose restart worker
   ```
4. Limpar fila Redis:
   ```bash
   docker compose exec redis redis-cli FLUSHALL
   ```

#### 5. Playwright/Chromium não funciona

**Sintomas:**
- SERP adapter falha
- `Executable doesn't exist at /root/.cache/ms-playwright/...`

**Soluções:**
1. Instalar Playwright no container:
   ```bash
   docker compose exec backend playwright install chromium
   ```
2. Verificar Dockerfile:
   ```dockerfile
   RUN playwright install --with-deps chromium
   ```

#### 6. Classificação Gemini falha

**Sintomas:**
- `classification_confidence` é None
- Runs não são classificadas

**Soluções:**
1. Verificar API key:
   ```bash
   echo $GOOGLE_API_KEY
   ```
2. Testar API manualmente:
   ```python
   import google.generativeai as genai
   genai.configure(api_key="YOUR_KEY")
   model = genai.GenerativeModel("gemini-2.0-flash-exp")
   response = model.generate_content("Hello")
   print(response.text)
   ```
3. Verificar quota:
   - Acessar [Google AI Studio](https://aistudio.google.com/)
   - Verificar limites de uso

---

## Boas Práticas

### 1. Código

#### Backend (Python)
- **PEP 8**: Seguir convenções de estilo Python
- **Type hints**: Usar anotações de tipo
  ```python
  def process_run(run_id: str, db: Session) -> dict:
      ...
  ```
- **Docstrings**: Documentar funções complexas
  ```python
  def compute_zcrs(citations: List[Citation]) -> float:
      """
      Calcula Zero-Click Response Score.
      
      Args:
          citations: Lista de citações extraídas
          
      Returns:
          Score de 0.0 a 100.0
      """
  ```
- **Error handling**: Usar try/except apropriadamente
  ```python
  try:
      result = await adapter.run(prompt)
  except Exception as e:
      logger.error(f"Adapter failed: {e}")
      raise HTTPException(500, "Adapter error")
  ```

#### Frontend (TypeScript)
- **TypeScript strict**: Ativar modo strict
  ```json
  // tsconfig.json
  {
    "compilerOptions": {
      "strict": true
    }
  }
  ```
- **Componentes funcionais**: Preferir hooks
  ```tsx
  const RunCard: React.FC<{run: RunListItem}> = ({run}) => {
      const [loading, setLoading] = useState(false)
      // ...
  }
  ```
- **Destructuring**: Usar para props
  ```tsx
  const { id, status, engine } = run
  ```

### 2. Git

#### Commits
- **Conventional Commits**:
  ```
  feat: adicionar campo priority em Run
  fix: corrigir cálculo de ZCRS
  docs: atualizar DEVELOPER_GUIDE
  refactor: extrair lógica de classificação
  test: adicionar testes para KPIs
  ```

#### Branches
- `main` - Produção
- `develop` - Desenvolvimento
- `feature/nome-feature` - Features
- `fix/nome-bug` - Bug fixes

#### Pull Requests
- Descrever mudanças claramente
- Referenciar issues relacionadas
- Incluir screenshots (se UI)
- Aguardar code review

### 3. Segurança

#### Secrets
- **NUNCA** commitar `.env`
- Usar `.env.example` como template
- Rotacionar chaves periodicamente
- Usar secrets management (ex: AWS Secrets Manager)

#### API Keys
- Armazenar em variáveis de ambiente
- Não logar chaves completas
- Usar rate limiting
- Implementar autenticação JWT (futuro)

### 4. Performance

#### Backend
- **Queries otimizadas**: Usar eager loading
  ```python
  runs = db.query(Run).options(
      joinedload(Run.citations),
      joinedload(Run.events)
  ).all()
  ```
- **Índices**: Adicionar em colunas frequentemente consultadas
  ```python
  __table_args__ = (
      Index('idx_run_status', 'status'),
      Index('idx_run_project', 'project_id'),
  )
  ```
- **Caching**: Usar Redis para dados frequentes
- **Async**: Preferir operações assíncronas

#### Frontend
- **Lazy loading**: Carregar componentes sob demanda
  ```tsx
  const RunDetail = lazy(() => import('./components/RunDetail'))
  ```
- **Memoization**: Usar `useMemo` e `useCallback`
  ```tsx
  const filteredRuns = useMemo(() => 
      runs.filter(r => r.status === 'completed'),
      [runs]
  )
  ```
- **Debouncing**: Para inputs de busca
  ```tsx
  const debouncedSearch = useDebounce(searchTerm, 500)
  ```

### 5. Documentação

- **README.md**: Overview do projeto
- **DEVELOPMENT.md**: Setup de desenvolvimento
- **DEVELOPER_GUIDE.md**: Guia completo (este arquivo)
- **API docs**: Swagger/OpenAPI automático
- **Code comments**: Para lógica complexa
- **Changelog**: Manter histórico de versões

### 6. Testes

- **Cobertura**: Mínimo 70%
- **Unit tests**: Funções isoladas
- **Integration tests**: Fluxos completos
- **E2E tests**: Jornadas do usuário (futuro)
- **CI/CD**: Executar testes automaticamente

---

## Recursos Adicionais

### Documentação Externa

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/)
- [React Docs](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [TailwindCSS](https://tailwindcss.com/docs)
- [shadcn/ui](https://ui.shadcn.com/)
- [Celery Docs](https://docs.celeryq.dev/)
- [Playwright Docs](https://playwright.dev/)

### APIs de IA

- [Google Gemini API](https://ai.google.dev/docs)
- [OpenAI API](https://platform.openai.com/docs)
- [Perplexity API](https://docs.perplexity.ai/)
- [SerpAPI](https://serpapi.com/docs)

### Ferramentas

- **VS Code Extensions**:
  - Python
  - Pylance
  - ES7+ React/Redux/React-Native snippets
  - Prettier
  - ESLint
  - Docker
  - GitLens

- **Chrome Extensions**:
  - React Developer Tools
  - Redux DevTools (se usar Redux)

### Comunidade

- **Issues**: Reportar bugs e sugerir features
- **Discussions**: Perguntas e discussões
- **Wiki**: Documentação adicional

---

## Próximos Passos

### Roadmap Técnico

1. **Autenticação e Autorização**
   - Implementar JWT
   - Roles e permissões
   - Multi-tenancy

2. **Testes Automatizados**
   - Unit tests (backend)
   - Component tests (frontend)
   - E2E tests (Playwright)
   - CI/CD pipeline

3. **Monitoramento e Observabilidade**
   - Prometheus + Grafana
   - OpenTelemetry
   - Error tracking (Sentry)
   - Log aggregation (ELK)

4. **Performance**
   - Query optimization
   - Caching strategy (Redis)
   - CDN para frontend
   - Database indexing

5. **Features**
   - Alertas (email/Slack/webhook)
   - Relatórios PDF
   - API pública (webhooks)
   - Integração com ferramentas de marketing

6. **Infraestrutura**
   - Kubernetes (K8s)
   - Auto-scaling
   - Multi-region
   - Disaster recovery

---

## Contato e Suporte

- **Maintainer**: Equipe SEO Analyzer
- **Email**: [seu-email@exemplo.com]
- **Slack**: [#seo-analyzer]
- **Issues**: [GitHub Issues](https://github.com/seu-repo/issues)

---

**Versão**: 1.0  
**Última atualização**: Janeiro 2025  
**Licença**: [Sua Licença]
