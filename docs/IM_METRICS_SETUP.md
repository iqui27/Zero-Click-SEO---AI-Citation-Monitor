# 🚀 IM Metrics - Guia de Configuração Rápida

## ⚙️ Configuração Inicial

### 1. Variáveis de Ambiente

Adicione ao seu `.env`:

```bash
# PageSpeed Insights API (Opcional mas recomendado)
PAGESPEED_API_KEY=your_google_api_key_here
```

**Como obter API Key do PageSpeed**:
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie/selecione um projeto
3. Ative a API: **PageSpeed Insights API**
4. Crie credenciais: **API Key**
5. Copie a chave e adicione ao `.env`

**Limites**:
- **Sem API Key**: 25,000 requests/dia
- **Com API Key**: 400,000 requests/dia

### 2. Rebuild dos Containers

```bash
docker compose up -d --build backend worker
```

---

## 🧪 Testando as Métricas

### 1. Criar Nova Run (Google SERP)

```bash
# Via API
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "engine_id": 1,
    "query": "seu termo de busca"
  }'
```

### 2. Verificar Métricas Calculadas

```bash
# Buscar métricas da run
curl http://localhost:8000/api/runs/{run_id}/metrics | jq

# Exemplo de resposta
{
  "im_seo_score": 78.5,
  "im_seoia_score": 82.3,
  "core_web_vitals_score": 85.0,
  "lcp_score": 90.0,
  "fid_score": 85.0,
  "cls_score": 80.0,
  "share_of_voice_serp": 75.0,
  "organic_position": 3,
  "competitors_top10": 8,
  "serp_features_presence": 70.0,
  "ia_serp_presence_score": 100.0,
  "longtail_terms_top10": 5,
  "longtail_coverage_score": 65.0,
  "eeat_score": 70.0,
  "schema_coverage_score": 60.0,
  "ia_ready_score": 75.0
}
```

### 3. Verificar Logs

```bash
# Logs do backend
docker compose logs -f backend

# Procurar por:
[IM_METRICS] Erro ao analisar SerpAPI: ...
[IM_METRICS] Erro ao buscar Core Web Vitals: ...
[PAGESPEED] Timeout ao analisar ...
```

---

## 📊 O Que Cada Métrica Significa

### IM-SEO Score (0-100)
**Fórmula**: `(Autoridade + Lighthouse + Share×2 + Engajamento) / 5`

- **< 50**: ❌ Precisa melhorar urgentemente
- **50-70**: ⚠️ Razoável, mas pode melhorar
- **70-85**: ✅ Bom desempenho
- **> 85**: 🏆 Excelente!

### IM-SEOIA Score (0-100)
**Fórmula**: Média ponderada de 8 componentes

- **< 50**: ❌ Não otimizado para IA
- **50-70**: ⚠️ Parcialmente otimizado
- **70-85**: ✅ Bem otimizado
- **> 85**: 🏆 Totalmente otimizado para IA!

### Core Web Vitals Score (0-100)
- **< 50**: ❌ Performance ruim
- **50-75**: ⚠️ Precisa melhorar
- **75-90**: ✅ Boa performance
- **> 90**: 🏆 Performance excelente!

### Share of Voice (0-100)
Baseado na posição orgânica e CTR esperado:
- **Posição 1**: ~100 pontos
- **Posição 3**: ~75 pontos
- **Posição 5**: ~50 pontos
- **Posição 10**: ~25 pontos

### Organic Position (1-20+)
- **1-3**: 🏆 Top positions
- **4-10**: ✅ Primeira página
- **11-20**: ⚠️ Segunda página
- **> 20**: ❌ Precisa melhorar

---

## 🔧 Troubleshooting

### PageSpeed API Não Funciona

**Sintoma**: `core_web_vitals_score` sempre 75.0 (mock)

**Soluções**:
1. Verificar se `PAGESPEED_API_KEY` está configurada
2. Verificar se a URL alvo é acessível publicamente
3. Verificar logs: `[PAGESPEED] Erro...`
4. Testar manualmente:
   ```bash
   curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://example.com&key=YOUR_KEY"
   ```

### SerpAPI Não Retorna Dados

**Sintoma**: `serp_features_presence`, `organic_position` são `null`

**Soluções**:
1. Verificar se a run é do tipo **Google SERP**
2. Verificar se `evidence.parsed_json.raw` existe
3. Verificar logs: `[IM_METRICS] Erro ao analisar SerpAPI`
4. Verificar estrutura dos dados:
   ```bash
   # No banco
   SELECT parsed_json FROM evidence WHERE run_id = 'run_xxx';
   ```

### Métricas Não Aparecem no Frontend

**Sintoma**: Dashboard vazio ou campos `null`

**Soluções**:
1. Verificar se a run foi executada **após** a implementação
2. Runs antigas não têm as novas métricas (recalcular)
3. Verificar endpoint: `GET /api/runs/{run_id}/metrics`
4. Verificar console do navegador para erros

---

## 🔄 Recalcular Métricas de Runs Antigas

### Opção 1: Via SQL (Rápido)

```sql
-- Marcar runs para recálculo
UPDATE runs 
SET status = 'pending'
WHERE engine_id = 1  -- Google SERP
  AND created_at > '2025-01-01'
  AND im_seo_score IS NULL;
```

### Opção 2: Via Script Python (Recomendado)

Criar `scripts/recalculate_im_metrics.py`:

```python
#!/usr/bin/env python3
"""Recalcula métricas IM para runs existentes."""

import sys
sys.path.insert(0, '/app')

from app.db.session import SessionLocal
from app.models.models import Run, Evidence, Citation, Domain, Project
from app.services.im_metrics_simple import SimpleIMMetrics

def recalculate_run(run_id: str):
    db = SessionLocal()
    try:
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            print(f"Run {run_id} não encontrada")
            return
        
        # Buscar dados necessários
        citations = db.query(Citation).filter(Citation.run_id == run.id).all()
        citations_data = [{"domain": c.domain, "url": c.url, "is_ours": c.is_ours} for c in citations]
        
        evidence = db.query(Evidence).filter(Evidence.run_id == run.id).first()
        serp_data = evidence.parsed_json.get("raw", {}) if evidence and evidence.parsed_json else None
        
        project = db.query(Project).filter(Project.id == run.project_id).first()
        domains = db.query(Domain).filter(Domain.project_id == project.id).all() if project else []
        project_domains = [d.domain for d in domains]
        
        # URL alvo
        target_url = None
        for cit in citations_data:
            if cit.get("is_ours"):
                target_url = cit.get("url")
                break
        
        # Calcular métricas
        run_data = {"amr_flag": run.amr_flag, "dcr_flag": run.dcr_flag, "zcrs": run.zcrs}
        im_metrics = SimpleIMMetrics.calculate_all(
            run_data, citations_data, run.response_text,
            serp_data=serp_data, project_domains=project_domains, target_url=target_url
        )
        
        # Atualizar run
        run.im_seo_score = im_metrics["im_seo_score"]
        run.im_seoia_score = im_metrics["im_seoia_score"]
        run.core_web_vitals_score = im_metrics["core_web_vitals_score"]
        run.lcp_score = im_metrics.get("lcp_score")
        run.fid_score = im_metrics.get("fid_score")
        run.cls_score = im_metrics.get("cls_score")
        # ... (adicionar todos os campos)
        
        db.commit()
        print(f"✅ Run {run_id}: IM-SEO={run.im_seo_score}, IM-SEOIA={run.im_seoia_score}")
        
    except Exception as e:
        print(f"❌ Erro ao recalcular {run_id}: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", help="ID da run")
    parser.add_argument("--all", action="store_true", help="Recalcular todas")
    parser.add_argument("--limit", type=int, default=10, help="Limite de runs")
    args = parser.parse_args()
    
    if args.run_id:
        recalculate_run(args.run_id)
    elif args.all:
        db = SessionLocal()
        runs = db.query(Run).filter(Run.engine_id == 1).limit(args.limit).all()
        db.close()
        for run in runs:
            recalculate_run(run.id)
```

**Executar**:
```bash
# Recalcular uma run específica
docker compose exec backend python scripts/recalculate_im_metrics.py --run-id run_123

# Recalcular últimas 10 runs
docker compose exec backend python scripts/recalculate_im_metrics.py --all --limit 10
```

---

## 📈 Monitoramento

### Verificar Taxa de Sucesso

```sql
-- Runs com métricas calculadas
SELECT 
    COUNT(*) as total,
    COUNT(im_seo_score) as with_im_seo,
    COUNT(core_web_vitals_score) as with_cwv,
    COUNT(organic_position) as with_position,
    ROUND(COUNT(im_seo_score) * 100.0 / COUNT(*), 2) as success_rate
FROM runs
WHERE engine_id = 1  -- Google SERP
  AND created_at > NOW() - INTERVAL '7 days';
```

### Verificar Médias

```sql
-- Médias das métricas
SELECT 
    ROUND(AVG(im_seo_score), 2) as avg_im_seo,
    ROUND(AVG(im_seoia_score), 2) as avg_im_seoia,
    ROUND(AVG(core_web_vitals_score), 2) as avg_cwv,
    ROUND(AVG(organic_position), 2) as avg_position
FROM runs
WHERE im_seo_score IS NOT NULL
  AND created_at > NOW() - INTERVAL '7 days';
```

---

## 🎯 Próximos Passos

### Fase 2 (Opcional)
1. **Google Search Console Integration**
   - CTR real
   - Impressões
   - Cliques
   - IRZC com dados reais

2. **Competitors Analysis**
   - Lista de concorrentes de negócio
   - Share of voice comparativo
   - Análise de gaps

3. **Historical Tracking**
   - Evolução temporal das métricas
   - Alertas de degradação
   - Benchmarking

---

## 📞 Suporte

**Documentação Completa**: `docs/IM_METRICS_COMPLETE.md`

**Logs Úteis**:
```bash
# Backend
docker compose logs -f backend | grep IM_METRICS

# Worker (Celery)
docker compose logs -f worker | grep IM_METRICS

# PageSpeed
docker compose logs -f backend | grep PAGESPEED
```

**Verificar Health**:
```bash
curl http://localhost:8000/health
```
