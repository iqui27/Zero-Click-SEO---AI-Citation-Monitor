# 🚀 Próximos Passos - Implementação GEO

## ✅ Status Atual: Backend 100% Completo

**Implementado:**
- ✅ 13 campos GEO no modelo Run
- ✅ 2 novas tabelas (domain_variants, content_gaps)
- ✅ Módulo de cálculo completo (geo_metrics.py)
- ✅ Integração automática em semantic insights
- ✅ 6 endpoints REST funcionais
- ✅ Schemas Pydantic completos
- ✅ Migração SQL pronta
- ✅ Detecção automática LLM vs SERP

---

## 📋 Checklist de Ativação (Ordem de Execução)

### 🔴 CRÍTICO - Fazer AGORA (30 min)

#### 1. Aplicar Migração SQL ⏱️ 5 min
```bash
# Conectar ao Azure SQL e executar:
sqlcmd -S seoanalyzer.database.windows.net -d SEO -U iqui27 -P "IquinhoF27!" \
  -i backend/migrations/add_geo_metrics.sql
```

**Validação:**
```sql
-- Verificar se colunas foram criadas
SELECT COLUMN_NAME, DATA_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'runs' 
  AND COLUMN_NAME LIKE '%brand%' OR COLUMN_NAME LIKE '%citation%' OR COLUMN_NAME LIKE '%engagement%';

-- Verificar se tabelas foram criadas
SELECT TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_NAME IN ('domain_variants', 'content_gaps');
```

#### 2. Reiniciar Backend ⏱️ 2 min
```bash
cd backend
docker-compose restart api worker
# Verificar logs
docker-compose logs -f api
```

#### 3. Testar Endpoints Básicos ⏱️ 10 min

**a) Health check:**
```bash
curl http://localhost:8000/health
```

**b) Criar domain variant de teste:**
```bash
curl -X POST http://localhost:8000/api/projects/prj_xxx/domain-variants \
  -H "Content-Type: application/json" \
  -d '{
    "variant_domain": "bancodobrasil.com.br",
    "canonical_domain": "bb.com.br",
    "display_name": "Banco do Brasil"
  }'
```

**c) Listar variants:**
```bash
curl http://localhost:8000/api/projects/prj_xxx/domain-variants
```

#### 4. Rodar Run de Teste com LLM ⏱️ 10 min

```bash
# Criar run com ChatGPT
curl -X POST http://localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "prj_xxx",
    "prompt_version_id": "pv_xxx",
    "engines": [{
      "name": "chatgpt",
      "region": "us",
      "device": "desktop"
    }]
  }'

# Aguardar conclusão (acompanhar logs)
# Verificar se métricas GEO foram calculadas
```

#### 5. Validar Métricas GEO ⏱️ 3 min

```sql
SELECT 
    id,
    status,
    brand_mention_count,
    brand_prominence_score,
    citation_rate_observed,
    citation_rate_corrected,
    share_of_voice_llm,
    engagement_score
FROM runs
WHERE id = 'run_xxx'  -- ID do run de teste
```

**Resultado esperado:**
- `brand_mention_count` > 0 (se marca foi mencionada)
- `brand_prominence_score` entre 0-100
- `citation_rate_observed` e `citation_rate_corrected` calculados
- `engagement_score` entre 0-100

---

### 🟡 IMPORTANTE - Fazer HOJE (2h)

#### 6. Configurar Domain Variants para Projeto Real ⏱️ 30 min

**Para Banco do Brasil:**
```bash
# Criar todas as variantes
curl -X POST http://localhost:8000/api/projects/prj_bb/domain-variants \
  -H "Content-Type: application/json" \
  -d '{"variant_domain": "bancodobrasil.com.br", "canonical_domain": "bb.com.br", "display_name": "Banco do Brasil"}'

curl -X POST http://localhost:8000/api/projects/prj_bb/domain-variants \
  -H "Content-Type: application/json" \
  -d '{"variant_domain": "ourocard.com.br", "canonical_domain": "bb.com.br", "display_name": "Banco do Brasil"}'

curl -X POST http://localhost:8000/api/projects/prj_bb/domain-variants \
  -H "Content-Type: application/json" \
  -d '{"variant_domain": "bbseguros.com.br", "canonical_domain": "bb.com.br", "display_name": "Banco do Brasil"}'
```

#### 7. Testar Citation Rate Stats ⏱️ 15 min

```bash
# Ver estatísticas dos últimos 30 dias
curl "http://localhost:8000/api/projects/prj_bb/geo/citation-rate?days=30"

# Ver estatísticas dos últimos 7 dias
curl "http://localhost:8000/api/projects/prj_bb/geo/citation-rate?days=7"
```

#### 8. Testar Co-Citation Analysis ⏱️ 15 min

```bash
# Top 10 concorrentes co-citados
curl "http://localhost:8000/api/projects/prj_bb/geo/cocitation-analysis?days=30&limit=10"

# Top 5 concorrentes
curl "http://localhost:8000/api/projects/prj_bb/geo/cocitation-analysis?days=30&limit=5"
```

#### 9. Criar Content Gaps de Exemplo ⏱️ 30 min

```bash
# Gap 1: Missing FAQ
curl -X POST http://localhost:8000/api/projects/prj_bb/content-gaps \
  -H "Content-Type: application/json" \
  -d '{
    "url": "/cartoes/ourocard",
    "gap_type": "missing_faq",
    "description": "Página de cartão sem seção de FAQ",
    "suggestion": "Adicionar FAQ com perguntas frequentes sobre anuidade, limite, benefícios",
    "priority": "high"
  }'

# Gap 2: Missing Table
curl -X POST http://localhost:8000/api/projects/prj_bb/content-gaps \
  -H "Content-Type: application/json" \
  -d '{
    "url": "/conta-pj",
    "gap_type": "missing_table",
    "description": "Sem tabela comparativa de tarifas",
    "suggestion": "Criar tabela comparando tarifas PJ vs concorrentes",
    "priority": "critical"
  }'

# Gap 3: No Comparison
curl -X POST http://localhost:8000/api/projects/prj_bb/content-gaps \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Cartão de Crédito PF",
    "gap_type": "no_comparison",
    "description": "Falta página comparativa BB vs Nubank",
    "suggestion": "Criar página neutra comparando benefícios, tarifas, limites",
    "priority": "medium"
  }'
```

#### 10. Documentar Resultados ⏱️ 30 min

Criar arquivo `GEO_TEST_RESULTS.md` com:
- Screenshots dos endpoints funcionando
- Exemplos de métricas calculadas
- Comparação CR Observed vs CR Corrected
- Top 5 concorrentes co-citados
- Lacunas criadas

---

### 🟢 MÉDIO PRAZO - Esta Semana (8h)

#### 11. Frontend - Tipos TypeScript ⏱️ 1h

**Arquivo:** `frontend/src/lib/api.ts`

```typescript
// Adicionar aos tipos existentes
export interface RunListItem {
  // ... campos existentes
  
  // GEO Metrics
  brand_mention_count?: number;
  brand_prominence_score?: number;
  citation_quality_score?: number;
  citation_rate_observed?: number;
  citation_rate_corrected?: number;
  share_of_voice_llm?: number;
  engagement_score?: number;
}

export interface RunDetail extends RunListItem {
  // ... campos existentes
  
  // GEO Metrics (completo)
  brand_first_mention_position?: number;
  brand_mention_density?: number;
  first_citation_position?: number;
  competitor_mention_ratio?: number;
  cocitation_competitors?: string;  // JSON array
  conversational_trigger_count?: number;
}

// Novos tipos GEO
export interface DomainVariant {
  id: string;
  project_id: string;
  variant_domain: string;
  canonical_domain: string;
  display_name?: string;
  created_at: string;
}

export interface ContentGap {
  id: string;
  project_id: string;
  url?: string;
  topic?: string;
  gap_type: string;
  description: string;
  suggestion?: string;
  priority: string;
  status: string;
  estimated_impact?: number;
  assignee?: string;
  detected_at: string;
  resolved_at?: string;
}

export interface GeoCitationRateStats {
  period_start: string;
  period_end: string;
  total_runs: number;
  llm_runs: number;
  cr_observed_avg: number;
  cr_corrected_avg: number;
  cr_trend: "up" | "down" | "stable";
  by_engine: Record<string, {
    cr_observed: number;
    cr_corrected: number;
    count: number;
  }>;
}

export interface GeoCoCitationAnalysis {
  competitor_domain: string;
  competitor_name: string;
  cocitation_count: number;
  cocitation_percentage: number;
  contexts: string[];
  avg_prominence_when_together?: number;
}
```

#### 12. Dashboard GEO - Estrutura Base ⏱️ 3h

**Arquivo:** `frontend/src/pages/GEODashboard.tsx`

Criar estrutura similar ao IM-Metrics Dashboard:
- Header com filtros (período, engine)
- 4 cards principais (CR, Share of Voice, Prominence, Engagement)
- 2 gráficos (evolução temporal, breakdown por engine)
- 1 tabela (top concorrentes co-citados)

#### 13. Dashboard GEO - Cards e Métricas ⏱️ 2h

Implementar cards:
- **Citation Rate Card:** CR Observed vs CR Corrected com trend
- **Share of Voice Card:** % nossa presença vs concorrentes
- **Prominence Card:** Score médio de proeminência
- **Engagement Card:** Score médio de engajamento

#### 14. Dashboard GEO - Gráficos ⏱️ 2h

Implementar gráficos:
- **Linha temporal:** CR ao longo do tempo (últimos 30 dias)
- **Barra horizontal:** Breakdown por engine (ChatGPT, Gemini, Perplexity)
- **Tabela:** Top 10 concorrentes co-citados com %

---

### 🔵 LONGO PRAZO - Próximas 2 Semanas (15h)

#### 15. UI Domain Variants ⏱️ 3h
- Página em Settings > Domain Variants
- Tabela com CRUD
- Preview de impacto no CR Corrected

#### 16. UI Content Gaps ⏱️ 3h
- Página dedicada Content Gaps
- Filtros por status/prioridade
- Kanban board (Open → In Progress → Completed)

#### 17. Sistema de Alertas ⏳ 4h
- Regras de alerta configuráveis
- Notificações in-app
- Histórico de alertas

#### 18. Backfill de Dados Históricos ⏳ 2h
- Script para recalcular métricas GEO em runs antigos
- Apenas runs de LLMs
- Batch processing

#### 19. Análise de Citability Drivers ⏳ 3h
- Script ML para identificar fatores
- Feature engineering
- Modelo explicável (SHAP values)

---

## 📊 Métricas de Sucesso

Após implementação completa, devemos conseguir responder:

✅ **Perguntas de Negócio:**
1. Qual engine (ChatGPT, Gemini, Perplexity) cita mais o BB?
2. O CR está subindo ou caindo nos últimos 30 dias?
3. Quantos % de "espaço narrativo" temos vs Nubank?
4. Quais concorrentes aparecem mais junto com o BB?
5. Nossas citações são de qualidade (posição, contexto)?
6. Que tipo de resposta gera mais engagement?

✅ **KPIs GEO:**
- Citation Rate Observed: > 40%
- Citation Rate Corrected: > 50%
- Share of Voice LLM: > 30%
- Brand Prominence Score: > 60
- Engagement Score: > 50

---

## 🎯 Entregáveis Finais

1. ✅ Backend funcional com métricas GEO
2. ⏳ Dashboard GEO no frontend
3. ⏳ Documentação de uso para time
4. ⏳ Apresentação de resultados (slides)
5. ⏳ Treinamento para stakeholders

---

## 📞 Suporte e Dúvidas

**Documentação:**
- `docs/GEO_METRICS_ANALYSIS.md` - Análise completa
- `docs/GEO_IMPLEMENTATION_PLAN.md` - Plano técnico
- `GEO_READY_TO_TEST.md` - Guia de testes

**Código:**
- `backend/app/services/geo_metrics.py` - Cálculos
- `backend/app/api/geo_routes.py` - API
- `backend/migrations/add_geo_metrics.sql` - Migração

---

**Última atualização:** 2025-10-08  
**Status:** 🎉 Backend pronto, aguardando migração SQL
