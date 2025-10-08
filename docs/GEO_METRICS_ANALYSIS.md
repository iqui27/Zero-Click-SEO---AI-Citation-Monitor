# Análise de Métricas GEO (Generative Engine Optimization)

**Data:** 2025-10-08  
**Foco:** OpenAI ChatGPT, Google Gemini, Perplexity  
**Escopo:** Análise de respostas de LLM (excluindo SERP)

---

## 1. Contexto: O que é GEO?

**GEO (Generative Engine Optimization)** é a otimização de marca e conteúdo para aparecer em respostas geradas por LLMs. É o "novo SEO" para uma era onde usuários obtêm respostas diretas de IAs sem clicar em links.

### Diferenças críticas vs SEO tradicional:
- **Não há "ranking" fixo** → Há **prominence** (proeminência narrativa)
- **Não há CTR tradicional** → Há **zero-click presence** (presença sem clique)
- **Backlinks → AI Citations** (citações em respostas de IA)
- **Share of Voice → Brand Mentions in LLMs**

### ⚠️ IMPORTANTE: Separação SERP vs LLM

**LLMs não devem popular métricas de SERP tradicionais.** Os indicadores são completamente diferentes:

| SERP (Google Search) | LLM (ChatGPT/Gemini/Perplexity) |
|---------------------|----------------------------------|
| Position (1-100) | Prominence Score (narrativa) |
| CTR (click-through) | Zero-Click Presence Rate |
| Impressions | Brand Mentions |
| Featured Snippets | First Citation Position |
| Core Web Vitals | Citation Quality Score |

**Tabelas separadas:**
- Métricas SERP → `serp_features`, campos IM-SEO no `runs`
- Métricas GEO → novos campos específicos GEO no `runs`

---

## 2. Métricas de GEO por Categoria

### 2.1 CORE METRICS (Essenciais)

#### ✅ Brand Mentions in AI Responses
**O que é:** Frequência com que a marca é mencionada em respostas de LLMs.  
**Por que importa:** Equivalente ao Share of Voice. Presença = mindshare, mesmo sem clique.  
**Como medir:** Contar ocorrências do nome da marca/produto no `response_text`.

**Status atual:** ❌ Não implementado  
**Campo necessário:** `brand_mention_count` (int)

---

#### ✅ AI Citation Count and Quality
**O que é:** Número e qualidade de citações (links/referências) para domínios do projeto.  
**Por que importa:** Citations são os "backlinks" do GEO. Trazem autoridade e tráfego.  
**Como medir:** Contagem + análise contextual (posição, anchor text, contexto).

**Status atual:** ✅ Parcialmente implementado  
- `our_citations_count` → contagem básica
- `citations_count` → total

**Faltam:**
- `citation_quality_score` (0-100) → média ponderada por posição + contexto
- `first_citation_position` (int) → posição da primeira citação nossa

---

#### ✅ AI Prominence Index (Positioning Score)
**O que é:** Onde sua marca aparece na narrativa? Primeira mencionada vs enterrada no fim?  
**Por que importa:** Ser o primeiro = maior confiança e influência.  
**Como medir:** Posição da primeira menção + densidade de menções + contexto semântico.

**Status atual:** ✅ Parcial via `brand_positioning` (protagonista|competidor|ausente)  
**Faltam:**
- `brand_first_mention_position` (int) → caractere ou % do texto onde aparece
- `brand_prominence_score` (0-100) → score composto
- `brand_mention_density` (float) → menções por 1000 caracteres

---

#### ✅ Zero-Click Presence Rate
**O que é:** % de respostas onde a marca aparece, independente de citação/link.  
**Por que importa:** Na era zero-click, presença = valor, mesmo sem tráfego imediato.  
**Como medir:** Agregado no nível de projeto/monitor.

**Status atual:** ❌ Não implementado (requer agregação)  
**Campo necessário:** Cálculo em analytics: `(runs com menção / total runs) * 100`

---

### 2.2 COMPETITIVE INTELLIGENCE

#### ✅ Competitor Mention Ratio
**O que é:** Nossa presença vs concorrentes na mesma resposta.  
**Por que importa:** Contexto competitivo. Sozinho = melhor. Com 10 concorrentes = diluído.  
**Como medir:** `our_mentions / (our_mentions + competitor_mentions)`

**Status atual:** ✅ Parcial via `competitive_mentions` (int)  
**Faltam:**
- `competitor_mention_ratio` (float 0-1)
- `share_of_voice_llm` (float 0-100) → % de "espaço narrativo"

---

#### ✅ Competitor Prominence Comparison
**O que é:** Somos mencionados antes ou depois dos concorrentes?  
**Por que importa:** Ordem = percepção de liderança.  
**Como medir:** Comparar `first_mention_position` vs concorrentes extraídos.

**Status atual:** ❌ Não implementado  
**Depende de:** Extração estruturada de competitors do `response_text`

---

### 2.3 ENGAGEMENT & CONVERSION POTENTIAL

#### ✅ Conversational Engagement Rate (CER)
**O que é:** A resposta incentiva follow-up? Tem CTAs implícitos?  
**Por que importa:** Mede "interesse" gerado, não apenas visibilidade.  
**Como medir:** Detectar padrões linguísticos: "saiba mais", "visite", perguntas abertas, etc.

**Status atual:** ❌ Não implementado  
**Campo necessário:** `conversational_trigger_count` (int) + `engagement_score` (0-100)

---

#### ✅ Conversion Potential Score
**O que é:** Quão provável é que a resposta leve a uma ação?  
**Por que importa:** Nem toda menção vale igual. "Melhor opção" > "também existe".  
**Como medir:** NLP para detectar linguagem de recomendação forte vs neutra.

**Status atual:** ✅ Implementado via `conversion_potential` (alto|medio|baixo)  
**Melhorias:** Transformar em score 0-100 + justificativa textual

---

### 2.4 SEMANTIC QUALITY

#### ✅ Perceived Value Category
**O que é:** Como a marca é posicionada? Inovação, tradição, custo, atendimento?  
**Por que importa:** Percepção de marca molda decisões de compra.  
**Como medir:** Análise semântica via LLM (já implementado via Gemini).

**Status atual:** ✅ Implementado via `perceived_value_category`

---

#### ✅ Semantic Summary Quality
**O que é:** Qualidade do resumo extraído da resposta.  
**Por que importa:** Base para análise rápida e dashboards.

**Status atual:** ✅ Implementado via `semantic_summary`

---

#### ✅ Entity Detection & Relevance
**O que é:** Quais entidades (pessoas, produtos, locais) são associadas à marca?  
**Por que importa:** Conexões semânticas fortalecem autoridade.

**Status atual:** ✅ Implementado via `entities_detected` + tabela `entities`

---

### 2.5 CONTENT FITNESS

#### ✅ Semantic Content Fitness (SCF) Score
**O que é:** Quão "AI-friendly" é o conteúdo citado? Estruturado, claro, factual?  
**Por que importa:** Conteúdo otimizado = mais chance de ser citado corretamente.  
**Como medir:** Análise dos domínios citados (schema, listas, FAQs, etc).

**Status atual:** ✅ Parcialmente via `ia_ready_score` + flags (has_lists, has_faqs, etc)  
**Limitação:** Requer crawl de URLs citadas (tabela `url_metadata`)

---

## 3. Métricas FALTANDO (Prioridade Alta)

### 3.1 Para adicionar ao modelo `Run`:

```python
# GEO - Brand Presence
brand_mention_count: int = 0  # quantas vezes marca aparece
brand_first_mention_position: int | None = None  # caractere ou % onde aparece
brand_mention_density: float | None = None  # menções por 1000 chars
brand_prominence_score: float | None = None  # 0-100

# GEO - Citation Quality
citation_quality_score: float | None = None  # 0-100
first_citation_position: int | None = None  # posição da 1ª citação nossa

# GEO - Competitive
competitor_mention_ratio: float | None = None  # 0-1
share_of_voice_llm: float | None = None  # 0-100

# GEO - Engagement
conversational_trigger_count: int = 0
engagement_score: float | None = None  # 0-100
```

---

## 4. Dados que JÁ TEMOS (Aproveitáveis)

### ✅ Campos existentes reutilizáveis:
- `response_text` → análise textual completa
- `our_citations_count` / `citations_count` → base para ratios
- `competitive_mentions` → contexto competitivo
- `brand_positioning` → protagonista|competidor|ausente
- `perceived_value_category` → inovação|tradição|custo|atendimento
- `semantic_summary` → resumo já processado
- `entities_detected` → contagem de entidades
- `conversion_potential` → alto|medio|baixo

### ✅ Tabelas relacionadas:
- `citations` → domínio, URL, anchor, posição, is_ours
- `run_semantic_insights` → payload JSON completo do Gemini
- `entities` → entidades detectadas com salience
- `url_metadata` → metadata de URLs citadas (crawled)

---

## 5. Funcionalidades Requeridas (Banco do Brasil)

### 5.1 Monitoramento de Citações (Citation Rate)
**Objetivo:** Analisar milhares de interações de LLMs e calcular métricas de citação.

**Métricas:**
- **Citation Rate (CR) Observado** → `(our_citations / total_responses) * 100`
- **Citation Rate (CR) Corrigido** → Ajustado para variantes de domínio
  - Ex: `bb.com.br`, `bancodobrasil.com.br`, `ourocard.com.br` → todos = "Banco do Brasil"
- **Segmentação por:**
  - Produto (Cartões, Conta PF/PJ, Crédito PF)
  - Funil (Reconhecimento, Consideração, Conversão)
  - Tipo de pergunta (marca, comparação, reputação)

**Implementação:**
- Novo campo: `citation_rate_observed` (float)
- Novo campo: `citation_rate_corrected` (float)
- Agregação: endpoint `/api/projects/{id}/geo/citation-rate`

---

### 5.2 Acompanhamento de Domínio (Domain Consolidation)
**Objetivo:** Consolidar todas as menções, incluindo variantes de domínio.

**Lógica:**
- Mapear domínios variantes → entidade única
- Exemplo BB: `bb.com.br`, `bancodobrasil.com.br`, `ourocard.com.br` → "Banco do Brasil"
- Evitar subestimar presença

**Implementação:**
- Nova tabela: `domain_variants` (domain_variant → canonical_domain)
- Função: `consolidate_domain_mentions()`
- UI: Gerenciamento de variantes em Configurações do Projeto

---

### 5.3 Dashboards Interativos e Alertas Inteligentes
**Objetivo:** Monitorar tendências e alertar sobre quedas/subidas.

**Alertas:**
- ⚠️ CR cai > 10% em 7 dias
- ⚠️ Dependência de perguntas com marca > 70%
- ⚠️ Concorrente lidera em tema específico
- ✅ CR cresce > 15% em 30 dias

**Dashboard GEO (baseado em IM-Metrics):**
- Cards: CR Observed, CR Corrected, Share of Voice, Prominence Score
- Gráficos: Evolução temporal, Breakdown por funil/produto
- Tabela: Top concorrentes por co-citação

---

### 5.4 Análise de Co-Citação e Concorrência
**Objetivo:** Identificar quais concorrentes aparecem junto com BB.

**Métricas:**
- **Co-Citation Frequency** → Quantas vezes competitor X aparece com BB
- **Co-Citation Context** → Em quais contextos (comparação, reputação, etc)
- **Competitor Dominance** → Temas onde concorrente lidera

**Implementação:**
- Novo campo: `cocitation_competitors` (JSON array)
- Endpoint: `/api/projects/{id}/geo/cocitation-analysis`

---

### 5.5 Drivers de Citabilidade e Previsões
**Objetivo:** Identificar fatores que aumentam chance de citação.

**Análise:**
- Modelos explicáveis (regressão logística / XGBoost)
- Fatores: funil, tipo de pergunta, qualidade de conteúdo, structured data
- Simulação: "Se melhorar FAQs, CR sobe X%"

**Implementação:**
- Script: `scripts/analyze_citability_drivers.py`
- Endpoint: `/api/projects/{id}/geo/citability-drivers`
- UI: Página "Previsões GEO"

---

### 5.6 Integração com Rotinas de Conteúdo
**Objetivo:** Destacar lacunas e orientar criação de conteúdo.

**Lacunas detectadas:**
- ❌ Páginas sem tabelas de tarifas
- ❌ FAQs desatualizadas (> 90 dias sem atualização)
- ❌ Ausência de TL;DR (sumário executivo)
- ❌ Falta de páginas comparativas neutras

**Sugestões automáticas:**
- ✅ "Criar FAQ para Cartão de Crédito PF"
- ✅ "Adicionar tabela de tarifas em /conta-pj"
- ✅ "Criar página comparativa: BB vs Nubank"

**Implementação:**
- Nova tabela: `content_gaps` (url, gap_type, priority, status)
- Endpoint: `/api/projects/{id}/content-gaps`
- UI: Página "Lacunas de Conteúdo"

---

## 6. Implementação Recomendada (ATUALIZADA)

### Fase 1: Campos e Estrutura Base (3h)
1. ✅ Adicionar campos GEO ao modelo `Run`
2. ✅ Criar função `calculate_brand_presence_metrics()`
3. ✅ Criar módulo `geo_metrics.py`
4. ⏳ Migração de banco
5. ⏳ Integrar em `process_semantic_insights()`

### Fase 2: Citation Rate & Domain Consolidation (4h)
1. Criar tabela `domain_variants`
2. Implementar `calculate_citation_rate()`
3. UI para gerenciar variantes de domínio
4. Endpoint de agregação

### Fase 3: Dashboard GEO (6h)
1. Criar `GEODashboard.tsx` (baseado em IM-Metrics)
2. Cards: CR, Share of Voice, Prominence, Engagement
3. Gráficos de evolução temporal
4. Breakdown por produto/funil/tipo

### Fase 4: Alertas Inteligentes (3h)
1. Sistema de regras de alerta
2. Notificações in-app
3. Email/Slack opcional
4. Histórico de alertas

### Fase 5: Co-Citação & Competitive (4h)
1. Análise de co-citação
2. Tabela de concorrentes
3. Contexto de aparição
4. Gráfico de share comparado

### Fase 6: Citability Drivers (6h)
1. Script de análise ML
2. Feature engineering
3. Modelo explicável
4. Simulador de impacto
5. UI de previsões

### Fase 7: Content Gaps (5h)
1. Detector de lacunas (crawl + análise)
2. Priorização automática
3. UI de gestão de gaps
4. Integração com workflow de conteúdo

**Total estimado:** ~31 horas

---

## 6. Ferramentas Externas (Referência)

Mercado atual usa:
- **Semrush Enterprise AIO** → tracking multi-LLM
- **Profound.ai** → citation tracking + brand mentions
- **Otterly.AI** → keyword → prompt monitoring
- **Ziptie.dev** → unlinked mentions
- **Peec AI** → prompt testing

**Nossa vantagem:** Integração full-stack + dados históricos + análise semântica via Gemini.

---

## 7. Próximos Passos

1. ✅ Validar esta análise com stakeholders
2. ⏳ Criar migração de banco para novos campos
3. ⏳ Implementar cálculos de métricas GEO
4. ⏳ Atualizar frontend para exibir métricas
5. ⏳ Criar dashboard GEO dedicado
6. ⏳ Documentar metodologia de cálculo

---

## 8. Referências

- [Backlinko: Generative Engine Optimization](https://backlinko.com/generative-engine-optimization-geo)
- [RevenueZen: GEO KPIs](https://revenuezen.com/geo-kpis-to-measure-success/)
- [Backlinko: LLM Tracking Tools](https://backlinko.com/llm-tracking-tools)
- [GetPassionFruit: GEO Guide](https://www.getpassionfruit.com/blog/generative-engine-optimization-guide-for-chatgpt-perplexity-gemini-claude-copilot)
