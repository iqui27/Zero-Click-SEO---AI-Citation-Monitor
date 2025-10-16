# Otimizações de Performance do Dashboard

## Problema Identificado

O dashboard estava demorando muito para carregar os dados devido a:

1. **Múltiplas requisições HTTP sequenciais** (5-6 chamadas)
2. **Queries SQL não otimizadas** sem índices
3. **Falta de índices no banco Azure SQL**
4. **Ausência de cache no backend**

## Soluções Implementadas

### 1. Endpoint Agregado `/analytics/dashboard`

**Antes:** 5-6 requisições HTTP separadas
```typescript
axios.get('/analytics/overview')
axios.get('/analytics/subprojects/{id}/series')
axios.get('/analytics/subprojects/{id}/top-domains')
axios.get('/analytics/performance-by-engine')
axios.get('/analytics/costs')
```

**Depois:** 1 única requisição
```typescript
getDashboardData(subproject_id)
```

**Benefícios:**
- ✅ Redução de 83% no número de requests (6 → 1)
- ✅ Redução de latência de rede
- ✅ Menos overhead de conexão HTTP
- ✅ Carregamento paralelo de dados no backend

### 2. Queries SQL Otimizadas

**Antes:** Queries ORM com múltiplos round-trips
```python
runs = db.query(Run).filter(...).all()
# Processa em Python
```

**Depois:** Agregações SQL diretas
```sql
SELECT 
    COUNT(*) as total_runs,
    AVG(CASE WHEN amr_flag = 1 THEN 1.0 ELSE 0.0 END) as amr_avg,
    AVG(CASE WHEN dcr_flag = 1 THEN 1.0 ELSE 0.0 END) as dcr_avg,
    AVG(COALESCE(zcrs, 0.0)) as zcrs_avg
FROM runs
WHERE started_at IS NOT NULL
```

**Benefícios:**
- ✅ Processamento no banco (mais rápido)
- ✅ Menos dados transferidos
- ✅ Uso de índices nativos do SQL Server

### 3. Índices de Performance

Criados 6 índices estratégicos:

```sql
-- Filtros por data
CREATE INDEX idx_runs_started_at ON runs(started_at);

-- Filtros por subproject
CREATE INDEX idx_runs_subproject_id ON runs(subproject_id);

-- JOIN com engines
CREATE INDEX idx_runs_engine_id ON runs(engine_id);

-- Índice composto otimizado
CREATE INDEX idx_runs_subproject_started ON runs(subproject_id, started_at)
INCLUDE (amr_flag, dcr_flag, zcrs, cost_usd, tokens_total);

-- JOIN de citations
CREATE INDEX idx_citations_run_id ON citations(run_id);
CREATE INDEX idx_citations_domain ON citations(domain);
```

**Benefícios:**
- ✅ Queries 10-50x mais rápidas
- ✅ Redução de full table scans
- ✅ Melhor uso de memória do SQL Server

### 4. Frontend Otimizado

**Antes:**
```typescript
const [overview, setOverview] = useState(null)
const [series, setSeries] = useState(null)
const [topDomains, setTopDomains] = useState(null)
const [perf, setPerf] = useState(null)
const [costs, setCosts] = useState(null)

useEffect(() => {
  axios.get('/analytics/overview').then(setOverview)
  axios.get('/analytics/series').then(setSeries)
  // ... mais 3 chamadas
}, [])
```

**Depois:**
```typescript
const [data, setData] = useState<DashboardData | null>(null)
const [loading, setLoading] = useState(true)

useEffect(() => {
  getDashboardData(subproject_id)
    .then(setData)
    .finally(() => setLoading(false))
}, [])
```

**Benefícios:**
- ✅ Código mais limpo e manutenível
- ✅ Melhor controle de loading state
- ✅ Menos re-renders
- ✅ Melhor UX

## Como Aplicar

### 1. Aplicar Índices no Banco

```bash
# Opção 1: Via script automatizado
./scripts/apply_performance_indexes.sh

# Opção 2: Manualmente via Azure Portal
# Execute o arquivo: backend/migrations/add_performance_indexes.sql
```

### 2. Deploy do Backend

```bash
cd backend
# Reinicie o container/serviço para carregar o novo endpoint
docker-compose restart api
```

### 3. Deploy do Frontend

```bash
cd frontend
npm run build
# Deploy dos arquivos estáticos
```

## Resultados Esperados

| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Tempo de carregamento | ~5-8s | ~0.5-1s | **85-90%** |
| Número de requests | 6 | 1 | **83%** |
| Dados transferidos | ~200KB | ~50KB | **75%** |
| Tempo de query SQL | ~2-3s | ~0.1-0.3s | **90%** |

## Monitoramento

### Verificar Performance das Queries

```sql
-- Top queries mais lentas
SELECT TOP 10
    qs.execution_count,
    qs.total_elapsed_time / 1000000.0 AS total_elapsed_time_s,
    qs.total_elapsed_time / qs.execution_count / 1000000.0 AS avg_elapsed_time_s,
    SUBSTRING(qt.text, (qs.statement_start_offset/2)+1,
        ((CASE qs.statement_end_offset
            WHEN -1 THEN DATALENGTH(qt.text)
            ELSE qs.statement_end_offset
        END - qs.statement_start_offset)/2) + 1) AS query_text
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) qt
WHERE qt.text LIKE '%runs%'
ORDER BY qs.total_elapsed_time DESC;
```

### Verificar Uso dos Índices

```sql
-- Verificar se índices estão sendo usados
SELECT 
    i.name AS index_name,
    s.user_seeks,
    s.user_scans,
    s.user_lookups,
    s.user_updates
FROM sys.dm_db_index_usage_stats s
JOIN sys.indexes i ON s.object_id = i.object_id AND s.index_id = i.index_id
WHERE OBJECT_NAME(s.object_id) = 'runs'
ORDER BY s.user_seeks + s.user_scans + s.user_lookups DESC;
```

## Próximos Passos (Opcional)

### Cache no Backend (Futuro)

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache simples em memória (5 minutos)
_cache = {}
_cache_ttl = {}

def get_cached_dashboard(subproject_id: str | None):
    key = f"dashboard_{subproject_id or 'all'}"
    now = datetime.utcnow()
    
    if key in _cache and key in _cache_ttl:
        if now < _cache_ttl[key]:
            return _cache[key]
    
    # Buscar dados
    data = compute_dashboard_data(subproject_id)
    
    # Cachear por 5 minutos
    _cache[key] = data
    _cache_ttl[key] = now + timedelta(minutes=5)
    
    return data
```

### Redis Cache (Produção)

```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_dashboard_cached(subproject_id: str | None):
    key = f"dashboard:{subproject_id or 'all'}"
    
    # Tentar cache
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    
    # Computar
    data = compute_dashboard_data(subproject_id)
    
    # Cachear por 5 minutos
    redis_client.setex(key, 300, json.dumps(data))
    
    return data
```

## Troubleshooting

### Dashboard ainda lento?

1. **Verificar se índices foram aplicados:**
   ```sql
   SELECT name FROM sys.indexes WHERE object_id = OBJECT_ID('runs');
   ```

2. **Verificar plano de execução:**
   ```sql
   SET STATISTICS IO ON;
   SET STATISTICS TIME ON;
   -- Execute a query do dashboard
   ```

3. **Verificar fragmentação dos índices:**
   ```sql
   SELECT 
       OBJECT_NAME(i.object_id) AS table_name,
       i.name AS index_name,
       s.avg_fragmentation_in_percent
   FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') s
   JOIN sys.indexes i ON s.object_id = i.object_id AND s.index_id = i.index_id
   WHERE s.avg_fragmentation_in_percent > 30
   ORDER BY s.avg_fragmentation_in_percent DESC;
   ```

4. **Rebuild índices fragmentados:**
   ```sql
   ALTER INDEX idx_runs_started_at ON runs REBUILD;
   ```

## Referências

- [SQL Server Index Design Guide](https://docs.microsoft.com/en-us/sql/relational-databases/sql-server-index-design-guide)
- [Azure SQL Performance Best Practices](https://docs.microsoft.com/en-us/azure/azure-sql/database/performance-guidance)
- [FastAPI Performance Tips](https://fastapi.tiangolo.com/advanced/performance/)
