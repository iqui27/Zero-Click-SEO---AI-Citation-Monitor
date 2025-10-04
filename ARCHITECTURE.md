# Arquitetura do Sistema - Zero-Click SEO Monitor

## Visão Geral

Este documento descreve a arquitetura técnica do sistema, padrões de design, fluxos de dados e decisões arquiteturais.

---

## Arquitetura de Alto Nível

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Browser    │  │  Mobile App  │  │  API Client  │         │
│  │   (React)    │  │   (Future)   │  │   (Future)   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                    HTTP/REST + SSE
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                      APPLICATION LAYER                            │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Backend                       │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │   │
│  │  │   API    │  │   SSE    │  │  WebSocket│             │   │
│  │  │ Endpoints│  │ Streaming│  │  (Future) │             │   │
│  │  └────┬─────┘  └────┬─────┘  └─────┬─────┘             │   │
│  │       │             │              │                     │   │
│  │  ┌────▼─────────────▼──────────────▼─────┐             │   │
│  │  │        Business Logic Layer           │             │   │
│  │  │  - Services                           │             │   │
│  │  │  - Validators                         │             │   │
│  │  │  - Orchestrators                      │             │   │
│  │  └────┬──────────────────────────────────┘             │   │
│  └───────┼──────────────────────────────────────────────────┘   │
│          │                                                       │
└──────────┼───────────────────────────────────────────────────────┘
           │
    ┌──────┴──────┬──────────────┬────────────────┐
    │             │              │                │
┌───▼────┐  ┌────▼─────┐  ┌─────▼──────┐  ┌─────▼──────┐
│Database│  │Task Queue│  │   Cache    │  │  External  │
│ Azure  │  │  Redis   │  │   Redis    │  │    APIs    │
│  SQL   │  │ +Celery  │  │            │  │  - Gemini  │
│        │  │          │  │            │  │  - OpenAI  │
│        │  │          │  │            │  │  - Perplexity│
└────────┘  └──────────┘  └────────────┘  └────────────┘
```

---

## Camadas da Aplicação

### 1. Presentation Layer (Frontend)

**Responsabilidades:**
- Renderização de UI
- Gerenciamento de estado local
- Comunicação com API
- Validação de inputs do usuário

**Tecnologias:**
- React 18 (Componentes funcionais + Hooks)
- TypeScript (Type safety)
- TailwindCSS (Styling)
- Axios (HTTP client)
- React Router (Navegação)

**Padrões:**
- **Component-based architecture**: Componentes reutilizáveis
- **Container/Presentational pattern**: Separação de lógica e UI
- **Custom hooks**: Lógica compartilhada (useRunStream, usePolling)

### 2. API Layer (Backend)

**Responsabilidades:**
- Exposição de endpoints REST
- Validação de requests
- Autenticação/Autorização (futuro)
- Rate limiting (futuro)
- Streaming SSE

**Tecnologias:**
- FastAPI (Framework assíncrono)
- Pydantic (Validação de dados)
- Uvicorn (ASGI server)

**Padrões:**
- **RESTful API**: Recursos bem definidos
- **OpenAPI/Swagger**: Documentação automática
- **Dependency Injection**: `Depends()` para DB sessions
- **Response models**: Pydantic schemas para serialização

### 3. Business Logic Layer

**Responsabilidades:**
- Regras de negócio
- Orquestração de serviços
- Cálculo de métricas
- Classificação de respostas
- Geração de insights

**Componentes:**

#### Services
- `tasks.py`: Orquestração de runs
- `kpis.py`: Cálculo de métricas (AMR, DCR, ZCRS)
- `insights.py`: Geração de insights com IA
- `scheduler.py`: Agendamento de monitors

#### Adapters (External Integrations)
- `gemini.py`: Integração Google Gemini
- `openai_adapter.py`: Integração OpenAI
- `perplexity.py`: Integração Perplexity
- `serp.py`: Scraping Google SERP

#### Classifiers
- `response_classifier.py`: Classificação baseada em regras
- `gemini_classifier.py`: Classificação com IA
- `advanced_metrics.py`: Métricas avançadas

**Padrões:**
- **Adapter pattern**: Abstração de APIs externas
- **Strategy pattern**: Diferentes estratégias de classificação
- **Factory pattern**: Criação de adapters baseado em engine
- **Observer pattern**: Eventos de run (SSE)

### 4. Data Access Layer

**Responsabilidades:**
- Persistência de dados
- Queries otimizadas
- Transações
- Migrações

**Tecnologias:**
- SQLAlchemy 2.0 (ORM)
- pyodbc (Driver Azure SQL)
- Alembic (Migrações - futuro)

**Padrões:**
- **Repository pattern**: Abstração de acesso a dados
- **Unit of Work**: Gerenciamento de transações
- **Active Record**: Modelos SQLAlchemy

### 5. Infrastructure Layer

**Responsabilidades:**
- Task queue
- Caching
- Scheduling
- Logging
- Monitoring

**Tecnologias:**
- Celery (Task queue)
- Redis (Message broker + Cache)
- Docker (Containerização)
- Nginx (Reverse proxy)

---

## Fluxos de Dados

### Fluxo 1: Criação e Execução de Run

```
┌─────────┐
│ User    │
│ (UI)    │
└────┬────┘
     │
     │ 1. POST /api/runs
     │    {project_id, prompt_version_id, engines, ...}
     │
     ▼
┌────────────────┐
│ FastAPI        │
│ routes.py      │
└────┬───────────┘
     │
     │ 2. Validate payload (Pydantic)
     │ 3. Create Run record (status=queued)
     │ 4. Save to DB
     │
     ▼
┌────────────────┐
│ Database       │
│ (Azure SQL)    │
└────┬───────────┘
     │
     │ 5. Return run_id
     │
     ▼
┌────────────────┐
│ tasks.py       │
│ enqueue_run()  │
└────┬───────────┘
     │
     │ 6. Push task to Redis queue
     │
     ▼
┌────────────────┐
│ Redis Queue    │
└────┬───────────┘
     │
     │ 7. Celery worker picks task
     │
     ▼
┌────────────────────────────────────────────────┐
│ Worker Process                                 │
│                                                │
│  1. Update run.status = 'running'             │
│  2. Emit RunEvent(type='started')             │
│  3. Execute adapter (Gemini/OpenAI/etc.)      │
│  4. Stream chunks → RunEvent(type='chunk')    │
│  5. Extract citations                         │
│  6. Calculate KPIs (AMR, DCR, ZCRS)           │
│  7. Classify response (Gemini classifier)     │
│  8. Generate insights                         │
│  9. Update run.status = 'completed'           │
│  10. Emit RunEvent(type='completed')          │
│                                                │
└────┬───────────────────────────────────────────┘
     │
     │ 11. Save all to DB
     │
     ▼
┌────────────────┐
│ Database       │
│ - Run          │
│ - Citations    │
│ - RunEvents    │
│ - Insights     │
└────────────────┘
```

### Fluxo 2: SSE Streaming (Real-time Updates)

```
┌─────────┐
│ Browser │
└────┬────┘
     │
     │ 1. EventSource('/api/runs/{run_id}/stream')
     │
     ▼
┌────────────────┐
│ FastAPI        │
│ SSE endpoint   │
└────┬───────────┘
     │
     │ 2. Query RunEvents WHERE run_id = ?
     │    ORDER BY version ASC
     │
     ▼
┌────────────────┐
│ Database       │
└────┬───────────┘
     │
     │ 3. Stream events as SSE
     │    data: {"event_type": "chunk", "data_json": {...}}
     │
     ▼
┌─────────┐
│ Browser │
│         │
│ eventSource.onmessage = (event) => {
│   const data = JSON.parse(event.data)
│   updateUI(data)
│ }
│         │
└─────────┘
```

### Fluxo 3: Monitor Scheduling

```
┌────────────────┐
│ Scheduler      │
│ (Background    │
│  Thread)       │
└────┬───────────┘
     │
     │ Every 60 seconds
     │
     ▼
┌────────────────────────────────────────────┐
│ 1. Query active monitors                   │
│    SELECT * FROM monitors WHERE active=true│
│                                            │
│ 2. For each monitor:                       │
│    - Parse schedule_cron                   │
│    - Check if should run now (croniter)    │
│                                            │
│ 3. If should run:                          │
│    - Get linked templates                  │
│    - Get configured engines                │
│    - Create runs for each template+engine  │
│    - Enqueue tasks                         │
│                                            │
│ 4. Save MonitorHistory record              │
│                                            │
└────┬───────────────────────────────────────┘
     │
     │ 5. Tasks execute normally
     │
     ▼
┌────────────────┐
│ Celery Workers │
└────────────────┘
```

---

## Padrões de Design

### 1. Adapter Pattern (External APIs)

**Problema:** Diferentes APIs de IA têm interfaces distintas.

**Solução:** Criar adapters que implementam interface comum.

```python
# Interface comum
class AIAdapter(Protocol):
    async def run(self, prompt: str, config: dict) -> dict:
        """
        Returns:
            {
                "response": str,
                "citations": List[dict],
                "tokens": dict,
                "model": str
            }
        """
        ...

# Implementações
class GeminiAdapter(AIAdapter):
    async def run(self, prompt: str, config: dict) -> dict:
        # Gemini-specific logic
        ...

class OpenAIAdapter(AIAdapter):
    async def run(self, prompt: str, config: dict) -> dict:
        # OpenAI-specific logic
        ...

# Factory
def get_adapter(engine_name: str) -> AIAdapter:
    if "gemini" in engine_name:
        return GeminiAdapter()
    elif "gpt" in engine_name:
        return OpenAIAdapter()
    # ...
```

### 2. Observer Pattern (Run Events)

**Problema:** Frontend precisa de updates em tempo real.

**Solução:** Sistema de eventos com SSE.

```python
# Publisher (Worker)
def emit_event(run_id: str, event_type: str, data: dict):
    event = RunEvent(
        run_id=run_id,
        event_type=event_type,
        data_json=data,
        version=get_next_version(run_id)
    )
    db.add(event)
    db.commit()

# Subscriber (SSE endpoint)
async def stream_events(run_id: str):
    last_version = 0
    while True:
        events = db.query(RunEvent)\
            .filter(RunEvent.run_id == run_id)\
            .filter(RunEvent.version > last_version)\
            .order_by(RunEvent.version)\
            .all()
        
        for event in events:
            yield f"data: {json.dumps(event.to_dict())}\n\n"
            last_version = event.version
        
        if is_terminal_state(run_id):
            break
        
        await asyncio.sleep(1)
```

### 3. Strategy Pattern (Classification)

**Problema:** Múltiplas estratégias de classificação.

**Solução:** Diferentes classifiers com interface comum.

```python
class Classifier(Protocol):
    def classify(self, run: Run) -> dict:
        ...

class RuleBasedClassifier(Classifier):
    def classify(self, run: Run) -> dict:
        # Regex, keywords, heuristics
        ...

class GeminiClassifier(Classifier):
    def classify(self, run: Run) -> dict:
        # AI-powered classification
        ...

# Context
class ClassificationService:
    def __init__(self, strategy: Classifier):
        self.strategy = strategy
    
    def classify_run(self, run: Run) -> dict:
        return self.strategy.classify(run)

# Usage
service = ClassificationService(GeminiClassifier())
result = service.classify_run(run)
```

### 4. Repository Pattern (Data Access)

**Problema:** Lógica de acesso a dados espalhada.

**Solução:** Centralizar queries em repositories.

```python
class RunRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, run_id: str) -> Run:
        return self.db.get(Run, run_id)
    
    def get_by_project(self, project_id: str, limit: int = 100) -> List[Run]:
        return self.db.query(Run)\
            .filter(Run.project_id == project_id)\
            .order_by(Run.started_at.desc())\
            .limit(limit)\
            .all()
    
    def get_pending(self) -> List[Run]:
        return self.db.query(Run)\
            .filter(Run.status == 'queued')\
            .all()

# Usage
repo = RunRepository(db)
runs = repo.get_by_project("prj_12345678")
```

### 5. Dependency Injection (FastAPI)

**Problema:** Gerenciamento de dependências (DB sessions, configs).

**Solução:** FastAPI `Depends()`.

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@api_router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run
```

---

## Decisões Arquiteturais

### 1. Por que Azure SQL em vez de PostgreSQL?

**Decisão:** Migrar de PostgreSQL para Azure SQL Server.

**Razões:**
- Integração com ecossistema Azure
- Managed service (backup, HA, scaling)
- Melhor suporte empresarial
- Compatibilidade com ferramentas Microsoft

**Trade-offs:**
- Custo mais alto
- Vendor lock-in
- Necessidade de pyodbc (mais complexo que psycopg2)

### 2. Por que Celery + Redis?

**Decisão:** Usar Celery para task queue.

**Razões:**
- Maduro e battle-tested
- Suporte a scheduling (Celery Beat)
- Retry logic built-in
- Monitoring tools (Flower)

**Alternativas consideradas:**
- RQ (Redis Queue): Mais simples, mas menos features
- AWS SQS: Vendor lock-in
- Kafka: Overkill para o caso de uso

### 3. Por que SSE em vez de WebSockets?

**Decisão:** Server-Sent Events para streaming.

**Razões:**
- Unidirecional (servidor → cliente) suficiente
- Mais simples que WebSockets
- Reconnect automático
- HTTP/2 multiplexing

**Trade-offs:**
- Não permite cliente → servidor (não necessário)
- Fallback para polling se SSE falhar

### 4. Por que SQLAlchemy ORM?

**Decisão:** Usar ORM em vez de SQL raw.

**Razões:**
- Type safety com Python
- Migrations (Alembic)
- Abstração de dialetos SQL
- Relationships automáticos

**Trade-offs:**
- Performance overhead (mínimo)
- Curva de aprendizado
- Queries complexas podem ser verbosas

### 5. Por que React em vez de Vue/Svelte?

**Decisão:** React para frontend.

**Razões:**
- Ecossistema maduro
- shadcn/ui (componentes prontos)
- TypeScript support excelente
- Comunidade grande

**Alternativas:**
- Vue: Mais simples, mas menos componentes prontos
- Svelte: Mais rápido, mas ecossistema menor

---

## Segurança

### 1. Autenticação (Futuro)

**Plano:**
- JWT (JSON Web Tokens)
- OAuth2 com Password Flow
- Refresh tokens

**Implementação:**
```python
# backend/app/core/security.py
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username
```

### 2. Rate Limiting (Futuro)

**Plano:**
- Limitar requests por IP/usuário
- Proteção contra DDoS

**Implementação:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/runs")
@limiter.limit("100/minute")
def list_runs(request: Request):
    ...
```

### 3. Input Validation

**Atual:**
- Pydantic schemas validam todos os inputs
- SQL injection prevenido por ORM

**Exemplo:**
```python
class RunCreate(BaseModel):
    project_id: str = Field(..., regex=r"^prj_[a-f0-9]{8}$")
    prompt_version_id: str = Field(..., regex=r"^pv_[a-f0-9]{8}$")
    engines: List[EngineConfig] = Field(..., min_items=1, max_items=10)
    cycles: int = Field(1, ge=1, le=10)
```

### 4. Secrets Management

**Atual:**
- `.env` file (não commitado)
- Environment variables

**Futuro:**
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault

---

## Performance e Escalabilidade

### 1. Database Optimization

**Índices:**
```python
class Run(Base):
    __table_args__ = (
        Index('idx_run_project_status', 'project_id', 'status'),
        Index('idx_run_started_at', 'started_at'),
        Index('idx_run_monitor', 'monitor_id'),
    )
```

**Query Optimization:**
```python
# ❌ N+1 problem
runs = db.query(Run).all()
for run in runs:
    citations = run.citations  # Lazy load (N queries)

# ✅ Eager loading
runs = db.query(Run).options(
    joinedload(Run.citations),
    joinedload(Run.events)
).all()
```

### 2. Caching Strategy

**Plano:**
```python
import redis
from functools import wraps

cache = redis.Redis(host='redis', port=6379, db=1)

def cached(ttl=300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            cached_value = cache.get(key)
            if cached_value:
                return json.loads(cached_value)
            
            result = await func(*args, **kwargs)
            cache.setex(key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

@cached(ttl=600)
async def get_analytics_overview(project_id: str):
    # Expensive query
    ...
```

### 3. Horizontal Scaling

**Worker Scaling:**
```bash
# Múltiplos workers
docker compose up --scale worker=5
```

**API Scaling:**
```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      replicas: 3
    
  nginx:
    # Load balancer
    depends_on:
      - api
```

### 4. Async Operations

**FastAPI async endpoints:**
```python
@api_router.get("/runs/{run_id}")
async def get_run(run_id: str, db: Session = Depends(get_db)):
    # Non-blocking I/O
    run = await db.execute(select(Run).where(Run.id == run_id))
    return run.scalar_one_or_none()
```

---

## Monitoramento e Observabilidade

### 1. Logging

**Estrutura:**
```python
import logging
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

# Usage
logger.info("run_started", run_id=run.id, engine=run.engine.name)
logger.error("adapter_failed", run_id=run.id, error=str(e))
```

### 2. Metrics (Futuro)

**Prometheus:**
```python
from prometheus_client import Counter, Histogram, Gauge

run_counter = Counter('runs_total', 'Total runs', ['engine', 'status'])
run_duration = Histogram('run_duration_seconds', 'Run duration', ['engine'])
active_runs = Gauge('active_runs', 'Currently active runs')

# Usage
run_counter.labels(engine='gemini', status='completed').inc()
run_duration.labels(engine='gemini').observe(duration)
```

### 3. Tracing (Futuro)

**OpenTelemetry:**
```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("process_run")
def process_run(run_id: str):
    with tracer.start_as_current_span("execute_adapter"):
        result = adapter.run(prompt)
    
    with tracer.start_as_current_span("calculate_kpis"):
        kpis = compute_kpis(result)
    
    return kpis
```

---

## Disaster Recovery

### 1. Backup Strategy

**Database:**
- Automated daily backups (Azure SQL)
- Point-in-time restore (35 days)
- Geo-replication (futuro)

**Scripts:**
```bash
# scripts/backup-database.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
az sql db export \
  --resource-group seo-analyzer \
  --server seoanalyzer \
  --name SEO \
  --storage-key $STORAGE_KEY \
  --storage-key-type StorageAccessKey \
  --storage-uri "https://backups.blob.core.windows.net/backups/backup_${DATE}.bacpac"
```

### 2. High Availability

**Plano:**
- Multi-region deployment
- Load balancer (Azure Traffic Manager)
- Database failover groups
- Redis Sentinel (HA)

### 3. Rollback Strategy

**Deployment:**
```bash
# Tag releases
git tag -a v1.2.3 -m "Release 1.2.3"
git push origin v1.2.3

# Rollback
git checkout v1.2.2
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Conclusão

Esta arquitetura foi projetada para:
- **Escalabilidade**: Horizontal scaling de workers e API
- **Manutenibilidade**: Código modular e bem documentado
- **Extensibilidade**: Fácil adicionar novos adapters/features
- **Resiliência**: Retry logic, fallbacks, error handling
- **Performance**: Caching, async I/O, query optimization

Para adicionar novas features, siga os padrões estabelecidos e consulte o **DEVELOPER_GUIDE.md**.

---

**Versão**: 1.0  
**Última atualização**: Janeiro 2025
