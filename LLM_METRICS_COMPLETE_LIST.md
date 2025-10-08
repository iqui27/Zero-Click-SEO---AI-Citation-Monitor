# 📊 Métricas e Colunas Salvas para Runs de LLM

**Data:** 2025-10-08  
**Engines LLM:** OpenAI, ChatGPT, Gemini, Perplexity, Claude

---

## ✅ Colunas Populadas para LLMs

### 1. **Informações Básicas do Run**
```python
# Sempre populado
id                    # VARCHAR - ID único do run
project_id            # VARCHAR - ID do projeto
prompt_version_id     # VARCHAR - ID da versão do prompt
engine_id             # VARCHAR - ID do engine (OpenAI, Gemini, etc)
subproject_id         # VARCHAR - ID do subprojeto (opcional)
monitor_id            # VARCHAR - ID do monitor (opcional)
status                # VARCHAR - "queued" → "running" → "completed"
started_at            # DATETIME - Início da execução
finished_at           # DATETIME - Fim da execução
```

### 2. **Custos e Performance**
```python
# Populado pelo engine runner
tokens_input          # INT - Tokens de entrada
tokens_output         # INT - Tokens de saída
tokens_total          # INT - Total de tokens
cost_usd              # FLOAT - Custo em USD
latency_ms            # INT - Latência em milissegundos
cycles_total          # INT - Número de ciclos executados
cycle_delay_seconds   # INT - Delay entre ciclos (se aplicável)
model_name            # VARCHAR - Nome do modelo (ex: "gpt-4o-mini")
```

### 3. **Citações**
```python
# Populado pelo engine runner
citations_count       # INT - Total de citações encontradas
our_citations_count   # INT - Citações dos nossos domínios
unique_domains_count  # INT - Domínios únicos citados
```

### 4. **Classificação Zero-Click** (Gemini Classifier)
```python
# Populado por classify_run_async()
response_type         # VARCHAR - "DIRETA", "COMPARATIVA", "INSTRUCIONAL", etc
sufficiency_level     # VARCHAR - "COMPLETA", "PARCIAL", "INSUFICIENTE"
actionability_type    # VARCHAR - "IMEDIATA", "PLANEJAMENTO", "PESQUISA"
trust_source          # VARCHAR - "ALTA", "MEDIA", "BAIXA"
brand_positioning     # VARCHAR - "LIDER", "COMPETIDOR", "NAO_MENCIONADO"
question_type         # VARCHAR - "INFORMACIONAL", "TRANSACIONAL", etc
funnel_stage          # VARCHAR - "consciencia", "consideracao", "decisao"
classification_confidence  # FLOAT - Confiança da classificação (0-1)
classified_at         # DATETIME - Quando foi classificado
classification_version    # VARCHAR - Versão do classificador
```

### 5. **Análise Semântica** (Gemini Semantic)
```python
# Populado por process_semantic_insights()
perceived_value_category  # VARCHAR - "custo", "qualidade", "conveniencia", etc
semantic_summary          # TEXT - Resumo semântico (até 2000 chars)
response_text             # TEXT - Texto completo da resposta (até 50000 chars)

# Entidades
entities_detected         # INT - Número de entidades detectadas
entities_relevance_score  # FLOAT - Score médio de relevância (0-1)
entity_connection_score   # FLOAT - Score de conexão entre entidades (0-100)
```

### 6. **🎯 MÉTRICAS GEO (Generative Engine Optimization)**

#### 6.1 Brand Presence
```python
brand_mention_count           # INT - Quantas vezes a marca aparece
brand_first_mention_position  # INT - Posição em caracteres da primeira menção
brand_mention_density         # FLOAT - Menções por 1000 caracteres
brand_prominence_score        # FLOAT - Score de proeminência (0-100)
                              # Fórmula: posição (40%) + densidade (30%) + primeiro parágrafo (30%)
```

#### 6.2 Citation Quality & Rate
```python
citation_quality_score    # FLOAT - Qualidade das citações (0-100)
                          # Fórmula: posição (40%) + anchor (20%) + contexto (30%) + domínio (10%)
first_citation_position   # INT - Posição ordinal da primeira citação (1-N)
citation_rate_observed    # FLOAT - % de citações observadas (simples)
citation_rate_corrected   # FLOAT - % ajustado por variantes de domínio
```

#### 6.3 Competitive Intelligence
```python
competitor_mention_ratio  # FLOAT - Ratio de menções (0-1)
                          # Fórmula: nossa_mencoes / (nossa_mencoes + concorrentes_mencoes)
share_of_voice_llm        # FLOAT - Share of Voice em % (0-100)
                          # Fórmula: (nossa_mencoes / total_mencoes) * 100
cocitation_competitors    # TEXT - JSON array de concorrentes co-citados
                          # Exemplo: ["nubank.com.br", "itau.com.br"]
```

#### 6.4 Engagement
```python
conversational_trigger_count  # INT - Número de triggers detectados
                              # Triggers: CTAs, perguntas abertas, links, benefícios
engagement_score              # FLOAT - Score de engajamento (0-100)
                              # 0-2 triggers=30, 3-4=60, 5+=100
```

---

## ❌ Colunas que FICAM NULL para LLMs

### Métricas IM-SEO (SERP Tradicional)
```python
# Estas métricas são APENAS para Google Search
im_seo_score              # NULL - Índice IM-SEO
im_seoia_score            # NULL - Índice IM-SEOIA

# Core Web Vitals (PageSpeed)
core_web_vitals_score    # NULL
lcp_score                # NULL - Largest Contentful Paint
fid_score                # NULL - First Input Delay
cls_score                # NULL - Cumulative Layout Shift

# Tráfego SERP
share_of_voice_serp      # NULL - Share of Voice em SERP
serp_features_presence   # NULL - Presença em features SERP
organic_position         # NULL - Posição orgânica (1-100)
competitors_in_top10     # NULL - Concorrentes no top 10

# IA SERP
ia_resources_detected    # NULL - Recursos de IA detectados
ia_serp_presence_score   # NULL - Score de presença IA SERP

# Long Tail
long_tail_terms_top10    # NULL
long_tail_terms_top20    # NULL
long_tail_coverage_score # NULL

# E-E-A-T (calculado de forma diferente para LLM)
eeat_score               # NULL (ou calculado pelo Gemini)
eeat_expertise           # NULL
eeat_experience          # NULL
eeat_authoritativeness   # NULL
eeat_trustworthiness     # NULL

# Schema.org
schema_types_detected    # NULL
schema_coverage_score    # NULL
schema_valid             # NULL

# IA-Ready Blocks (estrutura HTML)
ia_ready_blocks_count    # NULL
ia_ready_score           # NULL
has_lists                # NULL
has_faqs                 # NULL
has_tables               # NULL
has_step_by_step         # NULL

# IRZC (Índice de Risco Zero-Click)
irzc_score               # NULL
ctr_expected             # NULL
ctr_real                 # NULL
ctr_ratio                # NULL
```

---

## 📊 Resumo por Categoria

### ✅ Sempre Populado (LLM e SERP)
- Informações básicas (id, status, timestamps)
- Custos e performance (tokens, cost_usd, latency_ms)
- Citações (citations_count, our_citations_count)
- Classificação Zero-Click (response_type, brand_positioning, funnel_stage)
- Análise semântica básica (perceived_value_category, semantic_summary)

### ✅ Apenas para LLM (13 campos GEO)
- Brand Presence (4 campos)
- Citation Quality & Rate (4 campos)
- Competitive Intelligence (3 campos)
- Engagement (2 campos)

### ❌ Apenas para SERP (32+ campos IM-SEO)
- IM-SEO/IM-SEOIA scores
- Core Web Vitals
- Métricas de tráfego SERP
- Long tail
- E-E-A-T detalhado
- Schema.org
- IA-Ready Blocks
- IRZC

---

## 🔍 Exemplo de Run LLM Completo

```json
{
  "id": "run_abc123",
  "engine": "openai",
  "status": "completed",
  
  // Custos
  "tokens_total": 8500,
  "cost_usd": 0.042,
  "latency_ms": 3200,
  
  // Classificação
  "response_type": "COMPARATIVA",
  "brand_positioning": "COMPETIDOR",
  "funnel_stage": "consideracao",
  
  // Semântica
  "perceived_value_category": "custo",
  "entities_detected": 10,
  "response_text": "Resumo executivo — melhores bancos...",
  
  // GEO - Brand Presence
  "brand_mention_count": 3,
  "brand_prominence_score": 65.5,
  "brand_mention_density": 0.45,
  
  // GEO - Citation
  "citation_quality_score": 78.2,
  "citation_rate_observed": 42.5,
  "citation_rate_corrected": 48.3,
  
  // GEO - Competitive
  "share_of_voice_llm": 35.7,
  "competitor_mention_ratio": 0.42,
  "cocitation_competitors": "[\"nubank.com.br\",\"itau.com.br\"]",
  
  // GEO - Engagement
  "conversational_trigger_count": 5,
  "engagement_score": 75.0,
  
  // IM-SEO (NULL para LLM)
  "im_seo_score": null,
  "im_seoia_score": null,
  "core_web_vitals_score": null,
  "organic_position": null
}
```

---

## 🎯 Total de Campos por Tipo

| Categoria | Campos | Status LLM |
|-----------|--------|------------|
| **Básicos** | 10 | ✅ Populado |
| **Custos/Performance** | 8 | ✅ Populado |
| **Citações** | 3 | ✅ Populado |
| **Classificação Zero-Click** | 10 | ✅ Populado |
| **Semântica** | 5 | ✅ Populado |
| **GEO (LLM)** | **13** | ✅ **Populado** |
| **IM-SEO (SERP)** | 32+ | ❌ NULL |
| **TOTAL POPULADO** | **49 campos** | |
| **TOTAL NULL** | **32+ campos** | |

---

## 📝 Observações Importantes

1. **Separação Total:** LLM e SERP têm métricas completamente diferentes
2. **Sem Overlap:** Campos GEO nunca são populados para SERP, campos IM-SEO nunca para LLM
3. **Classificação Compartilhada:** Zero-Click classification funciona para ambos
4. **Response Text:** Salvo para ambos (análise textual)
5. **Citações:** Conceito diferente - SERP = backlinks, LLM = menções na resposta

---

**Última atualização:** 2025-10-08 18:05  
**Versão:** GEO v1.0 - Implementação completa
