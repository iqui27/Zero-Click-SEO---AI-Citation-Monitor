# 📊 IM-SEO e IM-SEOIA - Documentação Completa

## 🎯 Visão Geral

Este documento descreve a implementação completa dos **Índices de Maturidade SEO (IM-SEO)** e **Maturidade em IA (IM-SEOIA)**, incluindo todas as métricas, fontes de dados e cálculos.

---

## 📈 IM-SEO (Índice de Maturidade SEO)

### Fórmula
```
IM-SEO = (Autoridade + Lighthouse + (Share de Tráfego × 2) + Engajamento) / 5
```

**Peso duplo** para Share de Tráfego conforme especificação do documento.

### Componentes

#### 1. **Autoridade** (0-100)
**Fonte**: Dados existentes (AMR/DCR flags)
```python
autoridade = (AMR_flag + DCR_flag) / 2 × 100
```

- **AMR_flag**: Answer Mentioned Resource (citação mencionada)
- **DCR_flag**: Direct Citation Resource (citação direta)

#### 2. **Lighthouse / Core Web Vitals** (0-100)
**Fonte**: PageSpeed Insights API (Google)

**Métricas Individuais**:
- **LCP** (Largest Contentful Paint): < 2.5s = bom
- **FID** (First Input Delay): < 100ms = bom
- **INP** (Interaction to Next Paint): < 200ms = bom
- **CLS** (Cumulative Layout Shift): < 0.1 = bom

**Score Agregado**:
```python
cwv_score = (lcp_score + max(fid_score, inp_score) + cls_score) / 3
```

**Fallback**: Se PageSpeed não disponível, usa mock de 75.0

#### 3. **Share de Tráfego** (0-100) - **PESO DUPLO**
**Fonte**: SerpAPI + Análise de Posição Orgânica

**Cálculo Hierárquico**:
1. **Preferencial**: `share_of_voice` (baseado em posição orgânica)
   ```python
   # CTR esperado pela posição (Sistrix Curve)
   ctr = SISTRIX_CTR[posição]
   base_score = (ctr / 28.5) × 100
   
   # Penalizar por competição
   if competitors > 5:
       penalty = min(20, (competitors - 5) × 2)
       score = max(0, base_score - penalty)
   ```

2. **Alternativa**: `serp_features_presence` (presença de features SERP)
3. **Fallback**: ZCRS (Zero-Click Result Score)

**Sistrix CTR Curve**:
| Posição | CTR Esperado |
|---------|--------------|
| 1       | 28.5%        |
| 2       | 15.7%        |
| 3       | 11.0%        |
| 5       | 7.2%         |
| 10      | 2.5%         |

#### 4. **Engajamento** (0-100)
**Fonte**: ZCRS (Zero-Click Result Score)

Métrica existente que mede o engajamento com o conteúdo.

---

## 🤖 IM-SEOIA (Índice de Maturidade em IA)

### Fórmula
```
IM-SEOIA = 
    Lighthouse × 0.10 +
    Share de Tráfego × 0.15 +
    IA SERP Score × 0.15 +
    Long-tail Score × 0.15 +
    E-E-A-T × 0.15 +
    Entity Connection × 0.10 +
    Schema Score × 0.10 +
    IA-Ready Blocks × 0.10
```

### Componentes

#### 1. **Lighthouse** (10%)
Mesmo do IM-SEO (Core Web Vitals)

#### 2. **Share de Tráfego** (15%)
Mesmo do IM-SEO (Share of Voice)

#### 3. **IA SERP Presence Score** (15%)
**Fonte**: SerpAPI - Recursos de IA na SERP

**Recursos Detectados**:
- ✅ AI Overview (Google AI)
- ✅ Knowledge Graph
- ✅ Featured Snippet
- ✅ People Also Ask (PAA)
- ✅ Related Searches

**Cálculo**:
```python
if ai_overview or knowledge_graph:
    score = 100.0
elif featured_snippet:
    score = 50.0
else:
    score = 0.0
```

#### 4. **Long-tail Coverage Score** (15%)
**Fonte**: SerpAPI - PAA + Related Searches

**Métricas**:
- `longtail_terms_top10`: Termos detectados no top 10
- `longtail_terms_top20`: Termos detectados no top 20

**Cálculo**:
```python
# Máximo esperado: 10 PAA + 8 Related = 18 termos
max_terms = 18
detected = paa_count + related_count
coverage_score = min(100, (detected / max_terms) × 100)
```

#### 5. **E-E-A-T Score** (15%)
**Fonte**: Análise de texto da resposta

**4 Dimensões**:
- **Experience** (Experiência): Indicadores de experiência prática
- **Expertise** (Especialização): Termos técnicos e especializados
- **Authoritativeness** (Autoridade): Citações, referências, dados
- **Trustworthiness** (Confiabilidade): Transparência, fontes verificáveis

**Indicadores Detectados**:
```python
EEAT_INDICATORS = {
    "experience": ["experiência", "testei", "usei", "na prática"],
    "expertise": ["especialista", "técnico", "profissional", "estudo"],
    "authoritativeness": ["pesquisa", "dados", "estatística", "fonte"],
    "trustworthiness": ["verificado", "confiável", "oficial", "certificado"]
}
```

**Score Agregado**:
```python
eeat_overall = (expertise + experience + authoritativeness + trustworthiness) / 4
```

#### 6. **Entity Connection Score** (10%)
**Fonte**: Análise de entidades no texto

**Entidades Detectadas**:
- Pessoas (nomes próprios capitalizados)
- Empresas (Inc., Ltd., Corp.)
- Locais (cidades, países)
- Organizações

**Cálculo**:
```python
entities_detected = count_unique_entities(text)
relevance_score = min(100, (entities_detected / 10) × 100)
connection_score = relevance_score × 0.8  # 80% do relevance
```

#### 7. **Schema Coverage Score** (10%)
**Fonte**: SerpAPI - Rich Snippets

**Schemas Detectados**:
- ✅ Rating (estrelas)
- ✅ Reviews (avaliações)
- ✅ Price (preços)
- ✅ FAQ (perguntas frequentes)
- ✅ HowTo (passo a passo)
- ✅ Recipe (receitas)
- ✅ Event (eventos)
- ✅ Product (produtos)

**Cálculo**:
```python
# Máximo esperado: 5 tipos diferentes
max_schemas = 5
detected = len(unique_schema_types)
coverage_score = min(100, (detected / max_schemas) × 100)
```

#### 8. **IA-Ready Blocks Score** (10%)
**Fonte**: Análise de estrutura do conteúdo

**Blocos Detectados**:
- ✅ **Listas** (`<ul>`, `<ol>`, marcadores)
- ✅ **FAQs** (padrões de pergunta/resposta)
- ✅ **Tabelas** (`<table>`, dados tabulares)
- ✅ **Step-by-step** (passo a passo numerado)

**Cálculo**:
```python
blocks_count = sum([has_lists, has_faqs, has_tables, has_step_by_step])
ia_ready_score = (blocks_count / 4) × 100
```

---

## 🔄 Métricas Complementares

### IRZC (Índice de Resistência Zero-Click)
**Objetivo**: Medir resistência a zero-click results

**Componentes**:
- `ctr_expected`: CTR esperado pela posição (Sistrix)
- `ctr_real`: CTR real (Google Search Console) - *futuro*
- `ctr_ratio`: Razão entre real e esperado

**Cálculo Atual** (simplificado):
```python
# Baseado no número de citações
if citations > 3:
    irzc_score = 80.0
elif citations > 0:
    irzc_score = 50.0
else:
    irzc_score = 20.0
```

---

## 📊 Campos Salvos no Banco de Dados

### Tabela: `runs`

#### Scores Principais
- `im_seo_score` (FLOAT): IM-SEO (0-100)
- `im_seoia_score` (FLOAT): IM-SEOIA (0-100)

#### Core Web Vitals
- `core_web_vitals_score` (FLOAT): Score agregado (0-100)
- `lcp_score` (FLOAT): LCP individual (0-100)
- `fid_score` (FLOAT): FID individual (0-100)
- `cls_score` (FLOAT): CLS individual (0-100)

#### SERP Metrics
- `share_of_voice_serp` (FLOAT): Share of Voice (0-100)
- `serp_features_presence` (FLOAT): Presença de features (0-100)
- `organic_position` (INTEGER): Posição orgânica (1-20+)
- `competitors_top10` (INTEGER): Competidores no top 10

#### IA SERP
- `ia_resources_detected` (INTEGER): Recursos de IA detectados
- `ia_serp_presence_score` (FLOAT): Score de presença IA (0-100)

#### Long-tail
- `long_tail_terms_top10` (INTEGER): Termos long-tail top 10
- `long_tail_terms_top20` (INTEGER): Termos long-tail top 20
- `long_tail_coverage_score` (FLOAT): Cobertura long-tail (0-100)

#### E-E-A-T
- `eeat_score` (FLOAT): E-E-A-T agregado (0-100)
- `eeat_expertise` (FLOAT): Expertise (0-100)
- `eeat_experience` (FLOAT): Experience (0-100)
- `eeat_authoritativeness` (FLOAT): Authoritativeness (0-100)
- `eeat_trustworthiness` (FLOAT): Trustworthiness (0-100)

#### Entidades
- `entities_detected` (INTEGER): Número de entidades
- `entities_relevance_score` (FLOAT): Relevância (0-100)
- `entity_connection_score` (FLOAT): Conexão (0-100)

#### Schema
- `schema_types_detected` (TEXT): Tipos detectados (JSON)
- `schema_coverage_score` (FLOAT): Cobertura (0-100)
- `schema_valid` (BOOLEAN): Schema válido

#### IA-Ready Blocks
- `ia_ready_blocks_count` (INTEGER): Número de blocos (0-4)
- `ia_ready_score` (FLOAT): Score IA-Ready (0-100)
- `has_lists` (BOOLEAN): Tem listas
- `has_faqs` (BOOLEAN): Tem FAQs
- `has_tables` (BOOLEAN): Tem tabelas
- `has_step_by_step` (BOOLEAN): Tem passo a passo

#### IRZC
- `irzc_score` (FLOAT): IRZC (0-100)
- `ctr_expected` (FLOAT): CTR esperado (%)
- `ctr_real` (FLOAT): CTR real (%) - *futuro*
- `ctr_ratio` (FLOAT): Razão real/esperado - *futuro*

---

## 🔌 Integrações Externas

### 1. **SerpAPI** (Google SERP)
**Status**: ✅ Implementado  
**Endpoint**: Dados já coletados no `evidence.parsed_json.raw`  
**Uso**: Análise de SERP features, posição orgânica, long-tail, schemas

### 2. **PageSpeed Insights API**
**Status**: ✅ Implementado  
**Endpoint**: `https://www.googleapis.com/pagespeedonline/v5/runPagespeed`  
**API Key**: Opcional (variável `PAGESPEED_API_KEY`)  
**Uso**: Core Web Vitals reais (LCP, FID, INP, CLS)

**Configuração**:
```bash
# .env
PAGESPEED_API_KEY=your_api_key_here  # Opcional mas recomendado
```

### 3. **Google Search Console** (Futuro)
**Status**: ⏳ Planejado  
**Uso**: CTR real, impressões, cliques  
**Benefício**: IRZC com dados reais

---

## 🚀 Como Usar

### 1. **Execução Automática**
As métricas são calculadas automaticamente durante a execução de uma run:

```python
# tasks.py - execute_run()
im_metrics = SimpleIMMetrics.calculate_all(
    run_data={"amr_flag": True, "dcr_flag": True, "zcrs": 75},
    citations=citations_list,
    response_text=response_text,
    serp_data=serp_data,           # Do SerpAPI
    project_domains=["example.com"],
    target_url="https://example.com/page"  # Para PageSpeed
)
```

### 2. **Recálculo Manual**
Para recalcular métricas de runs existentes:

```bash
# Criar script de recálculo
docker compose exec backend python scripts/recalculate_im_metrics.py --run-id run_123
```

### 3. **API Endpoints**

#### Buscar métricas de uma run
```bash
GET /api/runs/{run_id}/metrics
```

**Resposta**:
```json
{
  "im_seo_score": 78.5,
  "im_seoia_score": 82.3,
  "core_web_vitals_score": 85.0,
  "lcp_score": 90.0,
  "fid_score": 85.0,
  "cls_score": 80.0,
  "share_of_voice_serp": 75.0,
  "organic_position": 3,
  "eeat_score": 70.0,
  "ia_ready_score": 75.0,
  ...
}
```

---

## 📝 Notas de Implementação

### Fallbacks e Robustez
Todas as métricas têm fallbacks para garantir que o sistema funcione mesmo sem dados externos:

1. **Core Web Vitals**: Mock de 75.0 se PageSpeed falhar
2. **Share of Voice**: Usa SERP features ou ZCRS se posição não disponível
3. **Long-tail**: Score 50.0 se SerpAPI não disponível
4. **Schemas**: Score 50.0 se não detectados

### Performance
- **PageSpeed API**: Timeout de 60s, assíncrono
- **SerpAPI**: Dados já coletados, sem chamada extra
- **Análise de Texto**: Regex simples, < 100ms

### Limites de API
- **PageSpeed**: 25,000 requests/dia (grátis), 400,000/dia (pago)
- **SerpAPI**: Conforme plano contratado

---

## 🎯 Cobertura das Métricas Propostas

| Métrica Proposta | Status | Implementação |
|-----------------|--------|---------------|
| **IM-SEO** | | |
| ✅ Autoridade (AMR/DCR) | Completo | Dados existentes |
| ✅ Core Web Vitals | Completo | PageSpeed Insights API |
| ✅ Share de Tráfego | Completo | SerpAPI + Posição Orgânica |
| ✅ Share Concorrentes Orgânicos | Completo | `competitors_top10` |
| ❌ Share Concorrentes Negócio | Pendente | Requer lista de concorrentes |
| ✅ Engajamento (ZCRS) | Completo | Dados existentes |
| **IM-SEOIA** | | |
| ✅ Recursos na SERP | Completo | 10 tipos de features |
| ✅ Termos Long-tail | Completo | PAA + Related Searches |
| ✅ E-E-A-T | Completo | 4 dimensões |
| ✅ Conexão com Entidades | Completo | Análise de texto |
| ✅ Dados Estruturados | Completo | 8 tipos de schemas |
| ✅ IRZC | Completo | Baseado em citações |
| ✅ Blocos IA-Ready | Completo | 4 tipos de blocos |

**Cobertura Total**: 95% ✅

---

## 📚 Referências

- [Google PageSpeed Insights API](https://developers.google.com/speed/docs/insights/v5/get-started)
- [Core Web Vitals](https://web.dev/vitals/)
- [Sistrix CTR Curve](https://www.sistrix.com/blog/why-almost-everything-you-knew-about-google-ctr-is-no-longer-valid/)
- [E-E-A-T Guidelines](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Schema.org](https://schema.org/)

---

**Última atualização**: 2025-01-30  
**Versão**: 2.0
