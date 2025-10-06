# 📊 Documentação Completa de Indicadores - SEO Analyzer

**Data:** 2025-10-06  
**Versão:** 1.0

---

## 🎯 ÍNDICES COMPOSTOS

### 1. IM-SEO Score (0-100)
**Fórmula:** `(Autoridade + Lighthouse + Share de Tráfego + Engajamento) / 4`

**Componentes:**
- **Autoridade:** AMR/DCR flags (interno)
- **Lighthouse:** Core Web Vitals Score (requer PAGESPEED_API_KEY)
- **Share de Tráfego:** ZCRS ou Share of Voice SERP
- **Engajamento:** ZCRS (interno)

**Campo:** `im_seo_score`

---

### 2. IM-SEOIA Score (0-100)
**Fórmula:** Média ponderada de 7 componentes

**Componentes:**
1. **Performance** (Core Web Vitals)
2. **Traffic** (Share of Voice)
3. **IA SERP** (Presença em features)
4. **Long Tail** (Cobertura de termos)
5. **E-E-A-T** (Expertise, Experience, Authoritativeness, Trust)
6. **Entidades** (Detecção e relevância)
7. **IA-Ready** (Blocos estruturados)

**Campo:** `im_seoia_score`

---

## 📈 MÉTRICAS DE POSICIONAMENTO IA

### 3. Brand Positioning
**Valores:** `protagonista` | `competidor` | `ausente`

**Algoritmo:**
```python
if brand_mentions == 0 AND not has_target_citation:
    return "ausente"
elif competitor_mentions > 0 OR total_citations > 3:
    return "competidor"
else:
    return "protagonista"
```

**Fatores:**
- Menções da marca no texto (ex: "Banco do Brasil", "BB")
- Citações de domínio alvo (ex: bb.com.br)
- Palavras competitivas ("alternativas", "outras opções")
- Quantidade total de citações

**Campo:** `brand_positioning`  
**Arquivo:** `response_classifier.py:403-437`

---

### 4. Competitive Mentions (Marcas em Destaque)
**Tipo:** Integer (0 a N)

**Algoritmo:**
```python
competitor_keywords = [
    "itaú", "bradesco", "caixa", "santander", "nubank",
    "inter", "c6", "original", "safra", "votorantim",
    "btg", "pan", "neon", "picpay", "99pay"
]

mentions = 0
for competitor in competitor_keywords:
    if competitor.lower() in response:
        mentions += 1
```

**Interpretação:**
- **0** = Sem competição
- **1-2** = Competição moderada
- **3+** = Cenário altamente competitivo

**Campo:** `competitive_mentions`  
**Arquivo:** `advanced_metrics.py:219-229`

---

### 5. Financial Value Score
**Escala:** 0.0 a 10.0

**Algoritmo:**
```python
# 1. Valores base por produto
product_values = {
    "emprestimo": 9.5,
    "previdencia": 8.5,
    "conta_corrente": 8.0,
    "seguros": 7.5,
    "cartao_credito": 7.0,
    "investimentos": 6.0
}

# 2. Multiplicadores por intenção
intent_multipliers = {
    "transactional": 1.5,   # Quer contratar
    "commercial": 1.2,      # Comparando
    "navigational": 0.8,
    "informational": 0.6    # Só pesquisando
}

# 3. Cálculo final
final_value = base_value × multiplicador
return min(10.0, final_value)
```

**Exemplo:**
- Consulta: "como abrir conta corrente no BB"
- Produto: conta_corrente (8.0)
- Intenção: transactional (×1.5)
- **Score:** 8.0 × 1.5 = **10.0**

**Campo:** `financial_value_score`  
**Arquivo:** `advanced_metrics.py:231-254`

---

### 6. Content Gap Detection
**Tipo:** Boolean

**Algoritmo:**
```python
competitor_mentioned = algum concorrente está no texto?
bb_mentioned = "banco do brasil" ou "bb" no texto?
bb_domain_cited = "bb.com.br" nas citações?

return competitor_mentioned AND NOT (bb_mentioned OR bb_domain_cited)
```

**Uso:** Identifica oportunidades onde concorrentes são citados mas sua marca está ausente.

**Campo:** `content_gap_detected`  
**Arquivo:** `advanced_metrics.py:256-280`

---

## 🎭 CLASSIFICAÇÃO DE RESPOSTA

### 7. Response Type
**Valores:** `direta` | `explicativa` | `instrucional` | `comparativa` | `consultiva` | `navegacional`

**Descrição:**
- **direta:** Informação objetiva e concisa
- **explicativa:** Define ou explica conceitos
- **instrucional:** Apresenta passo a passo
- **comparativa:** Compara produtos/serviços
- **consultiva:** Oferece opinião/recomendação
- **navegacional:** Direciona para links específicos

**Campo:** `response_type`

---

### 8. Sufficiency Level
**Valores:** `total` | `parcial` | `insuficiente`

**Descrição:**
- **total:** Esgota completamente a dúvida
- **parcial:** Útil mas incentiva clique adicional
- **insuficiente:** Genérica, força busca adicional

**Campo:** `sufficiency_level`

---

### 9. Actionability Type
**Valores:** `transacional` | `informativa`

**Descrição:**
- **transacional:** Leva a ação direta (clique, contato, compra)
- **informativa:** Apenas informa

**Campo:** `actionability_type`

---

### 10. Trust Source
**Valores:** `citada` | `generica`

**Descrição:**
- **citada:** Inclui citações e links confiáveis
- **generica:** Sem fontes ou conhecimento geral

**Campo:** `trust_source`

---

### 11. Question Type
**Valores:** `marca` | `produto` | `informacao` | `comparacao`

**Descrição:**
- **marca:** Consulta focada na marca/instituição
- **produto:** Menciona produtos/serviços específicos
- **informacao:** Busca informação geral
- **comparacao:** Compara opções ou pede diferenças

**Campo:** `question_type`

---

### 12. Funnel Stage
**Valores:** `reconhecimento` | `consideracao` | `conversao`

**Descrição:**
- **reconhecimento:** Descoberta/educação sem ação imediata
- **consideracao:** Avalia alternativas ou compara ofertas
- **conversao:** Intenção de ação/transação imediata

**Campo:** `funnel_stage`

---

### 13. User Intent
**Valores:** `informational` | `transactional` | `navigational` | `commercial`

**Descrição:**
- **informational:** Busca informações/conceitos
- **transactional:** Quer realizar ação/compra
- **navigational:** Busca site/página específica
- **commercial:** Pesquisa produtos/comparação

**Campo:** `user_intent`

---

### 14. Conversion Potential
**Valores:** `alto` | `medio` | `baixo`

**Algoritmo:**
```python
intent_scores = {
    "transactional": 0.9,
    "commercial": 0.7,
    "navigational": 0.5,
    "informational": 0.3
}

combined_score = (intent_score × 0.4) + 
                 (satisfaction × 0.3) + 
                 (financial_value/10 × 0.3)

if combined_score >= 0.7: return "alto"
elif combined_score >= 0.4: return "medio"
else: return "baixo"
```

**Campo:** `conversion_potential`

---

### 15. Satisfaction Score
**Escala:** 0.0 a 1.0

**Algoritmo:**
```python
base_score = 0.5

# Fatores positivos
if len(response) > 200: base_score += 0.2
if len(citations) > 1: base_score += 0.2
if high_quality_indicators: base_score += 0.1 a 0.2

# Fatores negativos
if low_quality_indicators: base_score -= 0.15 a 0.3

return max(0.0, min(1.0, base_score))
```

**Indicadores de Alta Qualidade:**
- "passo a passo", "detalhadamente", "completo"
- "todas as informações", "requisitos", "documentos"

**Indicadores de Baixa Qualidade:**
- "consulte", "verifique", "mais informações"
- "entre em contato", "procure"

**Campo:** `satisfaction_score`

---

### 16. Classification Confidence
**Escala:** 0.0 a 1.0

**Algoritmo:**
```python
base_confidence = 0.7
text_length_factor = min(len(text) / 500, 1.0) × 0.1

# Ajustes por clareza
if response_type in ["instrucional", "navegacional"]: +0.1
if brand_positioning in ["ausente", "protagonista"]: +0.1
if trust_source == "citada": +0.05

return min(base_confidence + adjustments, 1.0)
```

**Campo:** `classification_confidence`

---

## 🏆 E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness)

### 17. E-E-A-T Score Geral
**Escala:** 0-100

**Fórmula:** Média dos 4 componentes

**Campo:** `eeat_score`

---

### 18. Expertise (Especialização)
**Escala:** 0-100

**Método:** Análise de palavras-chave e padrões de especialização no texto

**Campo:** `eeat_expertise`

---

### 19. Experience (Experiência)
**Escala:** 0-100

**Método:** Detecção de indicadores de experiência prática

**Campo:** `eeat_experience`

---

### 20. Authoritativeness (Autoridade)
**Escala:** 0-100

**Método:** Análise de padrões de autoridade e fontes

**Campo:** `eeat_authoritativeness`

---

### 21. Trustworthiness (Confiabilidade)
**Escala:** 0-100

**Método:** Detecção de sinais de confiança e transparência

**Campo:** `eeat_trustworthiness`

---

## 🌐 CORE WEB VITALS (Performance)

### 22. Core Web Vitals Score
**Escala:** 0-100  
**API:** PAGESPEED_API_KEY ❌ (FALTANDO)

**Descrição:** Score geral de performance do site

**Campo:** `core_web_vitals_score`

---

### 23. LCP (Largest Contentful Paint)
**Unidade:** Segundos  
**API:** PAGESPEED_API_KEY ❌

**Descrição:** Tempo para renderizar o maior elemento visível

**Valores Ideais:**
- **Bom:** < 2.5s
- **Precisa melhorar:** 2.5s - 4.0s
- **Ruim:** > 4.0s

**Campo:** `lcp_score`

---

### 24. FID (First Input Delay)
**Unidade:** Milissegundos  
**API:** PAGESPEED_API_KEY ❌

**Descrição:** Tempo até primeira interação do usuário

**Valores Ideais:**
- **Bom:** < 100ms
- **Precisa melhorar:** 100ms - 300ms
- **Ruim:** > 300ms

**Campo:** `fid_score`

---

### 25. CLS (Cumulative Layout Shift)
**Unidade:** Score (sem unidade)  
**API:** PAGESPEED_API_KEY ❌

**Descrição:** Estabilidade visual durante carregamento

**Valores Ideais:**
- **Bom:** < 0.1
- **Precisa melhorar:** 0.1 - 0.25
- **Ruim:** > 0.25

**Campo:** `cls_score`

---

## 📊 TRÁFEGO E SERP

### 26. Share of Voice SERP
**Escala:** 0.0 a 1.0  
**API:** SERPAPI_KEY ✅

**Descrição:** Participação da marca nos resultados SERP baseado em posição orgânica

**Campo:** `share_of_voice_serp`

---

### 27. SERP Features Presence
**Tipo:** String (lista de features)  
**API:** SERPAPI_KEY ✅

**Descrição:** Features detectadas no SERP (Featured Snippet, People Also Ask, etc.)

**Campo:** `serp_features_presence`

---

### 28. IA Resources Detected
**Tipo:** Boolean/Count  
**API:** SERPAPI_KEY ✅

**Descrição:** Recursos de IA detectados no SERP

**Campo:** Derivado de `serp_features`

---

### 29. IA SERP Presence Score
**Escala:** 0-100  
**API:** SERPAPI_KEY ✅

**Descrição:** Score de presença em features de IA no SERP

**Campo:** Calculado a partir de `serp_features`

---

## 🎯 LONG TAIL

### 30. Long Tail Terms Top 10
**Tipo:** Integer  
**API:** SERPAPI_KEY ✅

**Descrição:** Quantidade de termos long-tail ranqueando no Top 10

**Campo:** Derivado de dados SERP

---

### 31. Long Tail Terms Top 20
**Tipo:** Integer  
**API:** SERPAPI_KEY ✅

**Descrição:** Quantidade de termos long-tail ranqueando no Top 20

**Campo:** Derivado de dados SERP

---

### 32. Long Tail Coverage Score
**Escala:** 0-100  
**API:** SERPAPI_KEY ✅

**Descrição:** Score de cobertura de termos long-tail

**Campo:** Calculado a partir de dados SERP

---

## 🤖 IA-READY BLOCKS

### 33. IA Ready Score
**Escala:** 0-100

**Descrição:** Score geral de preparação para IA baseado em blocos estruturados

**Campo:** `ia_ready_score`

---

### 34. IA Ready Blocks Count
**Tipo:** Integer

**Descrição:** Quantidade total de blocos estruturados detectados

**Campo:** `ia_ready_blocks_count`

---

### 35. Has Lists
**Tipo:** Boolean

**Descrição:** Presença de listas estruturadas

**Campo:** `has_lists`

---

### 36. Has FAQs
**Tipo:** Boolean

**Descrição:** Presença de FAQs (Perguntas Frequentes)

**Campo:** `has_faqs`

---

### 37. Has Tables
**Tipo:** Boolean

**Descrição:** Presença de tabelas

**Campo:** `has_tables`

---

### 38. Has Step-by-Step
**Tipo:** Boolean

**Descrição:** Presença de instruções passo a passo

**Campo:** `has_step_by_step`

---

## 🔗 ENTIDADES

### 39. Entities Detected
**Tipo:** Integer

**Descrição:** Quantidade de entidades detectadas no texto

**Campo:** `entities_detected`

---

### 40. Entities Relevance Score
**Escala:** 0.0 a 1.0

**Descrição:** Score de relevância das entidades detectadas

**Campo:** `entities_relevance_score`

---

### 41. Entity Connection Score
**Escala:** 0-100

**Descrição:** Score de conexão entre entidades

**Campo:** `entity_connection_score`

---

## 📋 DADOS ESTRUTURADOS (Schema)

### 42. Schema Types Detected
**Tipo:** String (lista)

**Descrição:** Tipos de schemas detectados (Organization, Product, FAQPage, etc.)

**Campo:** `schema_types_detected`

---

### 43. Schema Coverage Score
**Escala:** 0-100

**Descrição:** Score de cobertura de schemas

**Campo:** `schema_coverage_score`

---

### 44. Schema Valid
**Tipo:** Boolean

**Descrição:** Validação dos schemas detectados

**Campo:** `schema_valid`

---

## 📉 IRZC (Índice de Risco Zero-Click)

### 45. IRZC Score
**Escala:** 0-100

**Descrição:** Índice de risco de perda de tráfego por respostas zero-click

**Campo:** `irzc_score`

---

### 46. CTR Expected
**Escala:** 0.0 a 1.0

**Descrição:** CTR esperado baseado na posição SERP

**Fórmula:** Baseado em curvas de CTR por posição

**Campo:** `ctr_expected`

---

### 47. CTR Real
**Escala:** 0.0 a 1.0  
**Fonte:** Google Search Console (OAuth)

**Descrição:** CTR real medido

**Campo:** `ctr_real` (NULL - requer GSC)

---

### 48. CTR Ratio
**Escala:** 0.0+  
**Fonte:** Google Search Console (OAuth)

**Descrição:** Razão entre CTR real e esperado

**Fórmula:** `ctr_real / ctr_expected`

**Campo:** `ctr_ratio` (NULL - requer GSC)

---

## 📝 CITAÇÕES

### 49. Citations Count
**Tipo:** Integer

**Descrição:** Quantidade total de citações na resposta

**Campo:** `citations_count`

---

### 50. Our Citations Count
**Tipo:** Integer

**Descrição:** Quantidade de citações dos nossos domínios

**Campo:** `our_citations_count`

---

### 51. Citations Is Ours
**Tipo:** Boolean

**Descrição:** Indica se pelo menos uma citação é nossa

**Campo:** `citations_is_ours`

---

### 52. Unique Domains Count
**Tipo:** Integer

**Descrição:** Quantidade de domínios únicos citados

**Campo:** `unique_domains_count`

---

## 💰 CUSTOS E PERFORMANCE

### 53. Latency (ms)
**Unidade:** Milissegundos

**Descrição:** Tempo de resposta da API

**Campo:** `latency_ms`

---

### 54. Cost (USD)
**Unidade:** Dólares

**Descrição:** Custo da execução

**Campo:** `cost_usd`

---

### 55. Tokens Input
**Tipo:** Integer

**Descrição:** Quantidade de tokens de entrada

**Campo:** `tokens_input`

---

### 56. Tokens Output
**Tipo:** Integer

**Descrição:** Quantidade de tokens de saída

**Campo:** `tokens_output`

---

### 57. Tokens Total
**Tipo:** Integer

**Descrição:** Total de tokens (input + output)

**Campo:** `tokens_total`

---

## 🔄 CICLOS E EXECUÇÃO

### 58. Cycles Total
**Tipo:** Integer

**Descrição:** Quantidade total de ciclos executados

**Campo:** `cycles_total`

---

### 59. Cycle Delay Seconds
**Tipo:** Integer

**Descrição:** Delay entre ciclos em segundos

**Campo:** `cycle_delay_seconds`

---

## 📅 AGENDAMENTO

### 60. Schedule Date
**Tipo:** Date

**Descrição:** Data do agendamento

**Campo:** `schedule_date`

---

### 61. Schedule Slot
**Tipo:** String

**Descrição:** Slot de horário do agendamento

**Campo:** `schedule_slot`

---

### 62. Schedule Index Today
**Tipo:** Integer

**Descrição:** Índice da execução no dia

**Campo:** `schedule_index_today`

---

### 63. Schedule Total Today
**Tipo:** Integer

**Descrição:** Total de execuções agendadas no dia

**Campo:** `schedule_total_today`

---

### 64. Schedule Source
**Tipo:** String

**Descrição:** Origem do agendamento (manual, automático, etc.)

**Campo:** `schedule_source`

---

## 🎨 PERCEPÇÃO DE VALOR

### 65. Perceived Value Category
**Valores:** `inovacao` | `tradicao` | `custo` | `atendimento`

**Descrição:** Categoria de valor percebido predominante

**Campo:** `perceived_value_category`

---

### 66. Perception Scores (Semântico)
**Fonte:** Gemini Semantic Insights

**Componentes:**
- **inovador_bb:** Score de inovação (0-10)
- **seguranca_bb:** Score de segurança (0-10)
- **custo_bb:** Score de custo/preço (0-10)
- **atendimento_bb:** Score de atendimento (0-10)

**Algoritmo:**
```python
perception = semantic_insights.payload["perception"]
scores = {
    "inovador": map_category_to_score(perception, "inovacao"),
    "seguranca": map_category_to_score(perception, "tradicao"),
    "custo": map_category_to_score(perception, "custo"),
    "atendimento": map_category_to_score(perception, "atendimento")
}
```

**Campos:** Derivados de `semantic_insights`

---

## 📊 INSIGHTS SEMÂNTICOS (Gemini)

### 67. Semantic Summary
**Tipo:** String (JSON)

**Descrição:** Resumo semântico gerado pelo Gemini

**Componentes:**
- **headline:** Título do resumo
- **bullets:** Pontos principais
- **opportunities:** Oportunidades identificadas

**Campo:** `semantic_summary`

---

### 68. Semantic Entities
**Tipo:** Array (JSON)

**Descrição:** Entidades extraídas semanticamente

**Estrutura:**
```json
{
  "name": "Banco do Brasil",
  "category": "brand",
  "roles": ["brand"],
  "confidence": 0.92,
  "citations": ["https://www.bb.com.br"],
  "description": "..."
}
```

**Fonte:** `semantic_insights.payload["entities"]`

---

### 69. Semantic Relationships
**Tipo:** Array (JSON)

**Descrição:** Relacionamentos entre entidades

**Estrutura:**
```json
{
  "source": "Banco do Brasil",
  "target": "Conta Digital",
  "type": "brand_product",
  "weight": 0.76,
  "explanation": "..."
}
```

**Fonte:** `semantic_insights.payload["relationships"]`

---

### 70. Semantic Keywords
**Tipo:** Array (JSON)

**Descrição:** Palavras-chave extraídas semanticamente

**Estrutura:**
```json
{
  "token": "conta digital",
  "weight": 0.81,
  "brands": ["Banco do Brasil"],
  "products": ["Conta Digital"],
  "competitors": ["Nubank"],
  "context": "..."
}
```

**Fonte:** `semantic_insights.payload["keywords"]`

---

### 71. Semantic Competitors
**Tipo:** Array (JSON)

**Descrição:** Concorrentes identificados semanticamente

**Estrutura:**
```json
{
  "name": "Nubank",
  "mentions": 2,
  "keywords": ["cartão sem anuidade"]
}
```

**Fonte:** `semantic_insights.payload["competitors"]`

---

## 📈 MÉTRICAS AGREGADAS (Analytics)

### 72. Brand Presence Percentage
**Escala:** 0-100%

**Algoritmo:**
```python
mentioned_runs = runs onde brand_positioning in ["protagonista", "competidor"]
percentage = (mentioned_runs / total_runs) × 100
```

**Endpoint:** `/api/analytics/brand-presence`

---

### 73. Domain Presence Percentage
**Escala:** 0-100%

**Algoritmo:**
```python
cited_runs = runs com domínio alvo nas citações
percentage = (cited_runs / total_runs) × 100
```

**Endpoint:** `/api/analytics/brand-presence`

---

### 74. Content Gaps Detected
**Tipo:** Integer

**Descrição:** Quantidade de gaps de conteúdo detectados no período

**Endpoint:** `/api/analytics/competitive-share`

---

### 75. Gap Percentage
**Escala:** 0-100%

**Algoritmo:**
```python
gap_percentage = (runs_with_gaps / total_competitive_runs) × 100
```

**Endpoint:** `/api/analytics/competitive-share`

---

### 76. High Value Opportunities
**Tipo:** Integer

**Algoritmo:**
```python
opportunities = runs onde:
    financial_value_score >= 7.0 AND
    content_gap_detected == True
```

**Endpoint:** `/api/analytics/value-metrics`

---

## 🔍 METADADOS DE EXECUÇÃO

### 77. Status
**Valores:** `pending` | `running` | `completed` | `failed` | `cancelled`

**Campo:** `status`

---

### 78. Model Name
**Tipo:** String

**Descrição:** Nome do modelo de IA utilizado

**Campo:** `model_name`

---

### 79. Engine ID
**Tipo:** String

**Descrição:** ID do engine de execução

**Campo:** `engine_id`

---

### 80. Engine Name
**Tipo:** String

**Descrição:** Nome do engine

**Campo:** `engine_name`

---

### 81. Engine Region
**Tipo:** String

**Descrição:** Região do engine

**Campo:** `engine_region`

---

### 82. Engine Device
**Tipo:** String

**Descrição:** Dispositivo do engine (desktop, mobile)

**Campo:** `engine_device`

---

### 83. Started At
**Tipo:** Timestamp

**Descrição:** Data/hora de início da execução

**Campo:** `started_at`

---

### 84. Finished At
**Tipo:** Timestamp

**Descrição:** Data/hora de término da execução

**Campo:** `finished_at`

---

### 85. Response Text
**Tipo:** Text

**Descrição:** Texto completo da resposta gerada

**Campo:** `response_text`

---

### 86. Classification Version
**Tipo:** String

**Descrição:** Versão do classificador utilizado

**Campo:** `classification_version`

---

### 87. Semantic Insights Updated At
**Tipo:** Timestamp

**Descrição:** Data/hora da última atualização dos insights semânticos

**Campo:** `semantic_insights_updated_at`

---

## 📊 RESUMO ESTATÍSTICO

### Total de Indicadores: **87 métricas**

#### Por Categoria:
- **Índices Compostos:** 2
- **Posicionamento IA:** 6
- **Classificação de Resposta:** 10
- **E-E-A-T:** 5
- **Core Web Vitals:** 4
- **Tráfego e SERP:** 4
- **Long Tail:** 3
- **IA-Ready Blocks:** 6
- **Entidades:** 3
- **Dados Estruturados:** 3
- **IRZC:** 4
- **Citações:** 4
- **Custos e Performance:** 5
- **Ciclos e Execução:** 2
- **Agendamento:** 5
- **Percepção de Valor:** 2
- **Insights Semânticos:** 6
- **Métricas Agregadas:** 5
- **Metadados de Execução:** 8

#### Por Status:
- ✅ **Funcionando:** 69 métricas (79%)
- ⚠️ **Parciais:** 14 métricas (16%)
- ❌ **NULL (API faltando):** 4 métricas (5%)

#### APIs Necessárias:
- ✅ **PERPLEXITY_API_KEY** - Execução de prompts
- ✅ **OPENAI_API_KEY** - Classificação automática
- ✅ **GOOGLE_API_KEY** - Insights semânticos (Gemini)
- ✅ **SERPAPI_KEY** - Dados SERP
- ❌ **PAGESPEED_API_KEY** - Core Web Vitals (FALTANDO)

---

## 🚀 ENDPOINTS DE EXPORTAÇÃO

### 1. Export Completo
**Endpoint:** `GET /export/runs`  
**Formatos:** CSV, JSON, Excel  
**Inclui:** Todas as 87 métricas

### 2. Export Indicadores (AI Overview)
**Endpoint:** `GET /export/indicadores`  
**Formatos:** CSV, JSON, Excel  
**Foco:** E-E-A-T, Percepção, Entidades

### 3. Export Estrutura Web
**Endpoint:** `GET /export/estrutura-web`  
**Formatos:** CSV, JSON, Excel  
**Foco:** IA-Ready Blocks, Performance, URLs

### 4. Export Analytics
**Endpoint:** `GET /api/analytics/*`  
**Formato:** JSON  
**Foco:** Métricas agregadas e insights

---

## 📝 NOTAS IMPORTANTES

1. **Core Web Vitals** requer configuração da PAGESPEED_API_KEY
2. **CTR Real** requer integração com Google Search Console (OAuth)
3. **Insights Semânticos** são opcionais e requerem GOOGLE_API_KEY
4. **Long Tail** pode retornar 0 mesmo com API configurada se SERP não tiver dados
5. **Schemas** retorna NULL se o site não usa dados estruturados (comportamento esperado)

---

**Última atualização:** 2025-10-06  
**Versão do Sistema:** 1.1  
**Classificador:** v1.1
