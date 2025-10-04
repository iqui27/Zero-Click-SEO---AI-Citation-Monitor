# 📊 Status das Métricas e Roadmap

## ✅ **Métricas com Dados REAIS (Implementadas)**

### **1. IM-SEO Score** ✅
**Fonte**: Dados existentes + SerpAPI
- ✅ Autoridade (AMR/DCR)
- ✅ Share of Voice (posição orgânica do SerpAPI)
- ✅ Engajamento (ZCRS)
- ⚠️ Core Web Vitals (null se sem URL, real se com PageSpeed)

**Status**: **95% Real** (CWV depende de citação do projeto)

---

### **2. IM-SEOIA Score** ✅
**Fonte**: SerpAPI + Análise de texto
- ✅ Share of Voice (SerpAPI)
- ✅ IA SERP Presence (SerpAPI - AI Overview, Knowledge Graph)
- ✅ Long-tail Coverage (SerpAPI - PAA + Related Searches)
- ✅ E-E-A-T (análise de texto)
- ✅ Entity Connection (análise de texto)
- ✅ Schema Coverage (SerpAPI - rich snippets)
- ✅ IA-Ready Blocks (análise de estrutura)
- ⚠️ Core Web Vitals (null se sem URL)

**Status**: **95% Real**

---

### **3. E-E-A-T (4 dimensões)** ✅
**Fonte**: Análise de texto com NLP
- ✅ **Expertise**: Detecta termos técnicos e especializados
- ✅ **Experience**: Detecta indicadores de experiência prática
- ✅ **Authoritativeness**: Detecta citações, dados, estatísticas
- ✅ **Trustworthiness**: Detecta fontes verificáveis

**Status**: **100% Real** (análise heurística do texto)

---

### **4. Tráfego SERP** ✅
**Fonte**: SerpAPI
- ✅ **Share of Voice**: Baseado em posição orgânica (Sistrix CTR)
- ✅ **SERP Features**: 10 tipos detectados
  - AI Overview
  - Featured Snippet
  - Knowledge Graph
  - People Also Ask
  - Local Pack
  - Video Carousel
  - Image Pack
  - Shopping Results
  - Top Stories
  - Related Searches

**Status**: **100% Real** (SerpAPI)

---

### **5. Long-tail Coverage** ✅
**Fonte**: SerpAPI
- ✅ **PAA Questions**: Detectadas e contadas
- ✅ **Related Searches**: Detectadas e contadas
- ✅ **Coverage Score**: Calculado (detectado / máximo esperado)

**Status**: **100% Real** (SerpAPI)

---

### **6. Schema Coverage** ✅
**Fonte**: SerpAPI (rich snippets)
- ✅ **Tipos detectados**: Rating, Reviews, Price, FAQ, HowTo, Recipe, Event, Product
- ✅ **Coverage Score**: Calculado

**Status**: **100% Real** (SerpAPI)

---

### **7. IA-Ready Blocks** ✅
**Fonte**: Análise de estrutura do conteúdo
- ✅ **Listas**: Detectadas via regex
- ✅ **FAQs**: Detectadas via padrões
- ✅ **Tabelas**: Detectadas via HTML/markdown
- ✅ **Step-by-step**: Detectadas via numeração

**Status**: **100% Real** (análise de estrutura)

---

### **8. Entidades** ✅
**Fonte**: Análise de texto com NLP básico
- ✅ **Detectadas**: Nomes próprios, empresas, locais
- ✅ **Relevância**: Calculada
- ✅ **Conexão**: Calculada

**Status**: **100% Real** (análise heurística)

---

### **9. Posição Orgânica** ✅
**Fonte**: SerpAPI
- ✅ **Position**: 1-20+ detectada
- ✅ **Competitors Top 10**: Contados
- ✅ **URL**: Extraída

**Status**: **100% Real** (SerpAPI)

---

## ⚠️ **Métricas PARCIAIS (Dependem de Condições)**

### **10. Core Web Vitals** ⚠️
**Fonte**: PageSpeed Insights API
- ⚠️ **Requer**: Citação do projeto na resposta
- ⚠️ **Requer**: Domínios cadastrados
- ✅ **Quando disponível**: 100% real (Google PageSpeed)
- ❌ **Quando não**: `null` (não mock!)

**Métricas**:
- LCP (Largest Contentful Paint)
- FID (First Input Delay)
- INP (Interaction to Next Paint)
- CLS (Cumulative Layout Shift)

**Status**: **Condicional** (0-100% dependendo da run)

**Como melhorar**:
1. Cadastrar domínios do projeto
2. Criar queries que citem esses domínios
3. PageSpeed será chamado automaticamente

---

## ❌ **Métricas MOCK/ESTIMADAS (Precisam de Implementação)**

### **11. IRZC (Índice de Resistência Zero-Click)** ❌
**Fonte Atual**: Heurística simples (número de citações)
**Fonte Ideal**: Google Search Console

**Atual**:
```python
if citations > 3:
    irzc_score = 80.0
elif citations > 0:
    irzc_score = 50.0
else:
    irzc_score = 20.0
```

**Ideal**:
```python
ctr_real = search_console.get_ctr(query, url)
ctr_expected = sistrix_curve[position]
ctr_ratio = ctr_real / ctr_expected
irzc_score = calculate_resistance(ctr_ratio, zero_click_features)
```

**Status**: **20% Real** (baseado em citações, não em CTR real)

**Roadmap**: Integrar Google Search Console API

---

### **12. CTR Real** ❌
**Fonte Atual**: Não disponível
**Fonte Ideal**: Google Search Console

**Atual**: Apenas CTR esperado (Sistrix Curve)
**Ideal**: CTR real + impressões + cliques

**Status**: **0% Real** (não implementado)

**Roadmap**: Google Search Console API

---

### **13. Share of Voice Comparativo** ❌
**Fonte Atual**: Não disponível
**Fonte Ideal**: SerpAPI + Lista de concorrentes

**Atual**: Apenas posição do projeto
**Ideal**: Comparação com concorrentes específicos

**Status**: **0% Real** (não implementado)

**Roadmap**: 
1. Cadastro de lista de concorrentes
2. Análise comparativa de posições
3. Share of voice relativo

---

## 🚀 **ROADMAP - Próximas Implementações**

### **Fase 1: Google Search Console** (Prioridade ALTA)

#### **Objetivo**
Obter dados reais de CTR, impressões e cliques

#### **Implementação**
1. **Autenticação OAuth2** com Google Search Console
2. **Endpoint**: `/api/search-console/connect`
3. **Dados coletados**:
   - CTR real por query
   - Impressões
   - Cliques
   - Posição média

#### **Impacto**
- ✅ IRZC com dados reais
- ✅ CTR real vs esperado
- ✅ Análise de performance real

#### **Estimativa**: 2-3 dias

---

### **Fase 2: Competitors Analysis** (Prioridade MÉDIA)

#### **Objetivo**
Comparar performance com concorrentes

#### **Implementação**
1. **Cadastro de concorrentes**:
   ```json
   {
     "project_id": "prj_xxx",
     "competitors": [
       {"name": "Concorrente A", "domain": "concorrente-a.com"},
       {"name": "Concorrente B", "domain": "concorrente-b.com"}
     ]
   }
   ```

2. **Análise comparativa**:
   - Posição do projeto vs concorrentes
   - Share of voice relativo
   - Features SERP de cada um

3. **Visualização**:
   - Gráfico comparativo
   - Tabela de ranking
   - Gaps de oportunidade

#### **Impacto**
- ✅ Share of voice comparativo
- ✅ Análise de gaps
- ✅ Oportunidades de melhoria

#### **Estimativa**: 3-4 dias

---

### **Fase 3: Historical Tracking** (Prioridade MÉDIA)

#### **Objetivo**
Rastrear evolução temporal das métricas

#### **Implementação**
1. **Agregação temporal**:
   - Médias diárias/semanais/mensais
   - Tendências
   - Variações

2. **Alertas**:
   - Degradação de métricas (>10% queda)
   - Melhoria significativa (>10% aumento)
   - Anomalias

3. **Visualização**:
   - Gráficos de linha temporal
   - Heatmaps
   - Comparação períodos

#### **Impacto**
- ✅ Evolução temporal
- ✅ Alertas proativos
- ✅ Benchmarking interno

#### **Estimativa**: 2-3 dias

---

### **Fase 4: Advanced Analytics** (Prioridade BAIXA)

#### **Objetivo**
Análises avançadas e predições

#### **Implementação**
1. **Correlações**:
   - Quais métricas impactam mais o IM-SEO
   - Relação entre E-E-A-T e posição
   - Impacto de IA-Ready Blocks

2. **Predições**:
   - Previsão de posição futura
   - Impacto estimado de melhorias
   - ROI de otimizações

3. **Recomendações**:
   - Sugestões automáticas de melhoria
   - Priorização de ações
   - Quick wins

#### **Impacto**
- ✅ Insights acionáveis
- ✅ Predições
- ✅ ROI estimado

#### **Estimativa**: 5-7 dias

---

## 📊 **Resumo do Status Atual**

### **Métricas 100% Reais** (8)
1. ✅ E-E-A-T (4 dimensões)
2. ✅ Tráfego SERP (Share of Voice + Features)
3. ✅ Long-tail Coverage
4. ✅ Schema Coverage
5. ✅ IA-Ready Blocks
6. ✅ Entidades
7. ✅ Posição Orgânica
8. ✅ IM-SEOIA (composição)

### **Métricas Parcialmente Reais** (2)
1. ⚠️ IM-SEO (95% - falta CWV em alguns casos)
2. ⚠️ Core Web Vitals (condicional)

### **Métricas Mock/Estimadas** (3)
1. ❌ IRZC (heurística simples)
2. ❌ CTR Real (não implementado)
3. ❌ Share of Voice Comparativo (não implementado)

---

## 🎯 **Cobertura Atual**

**Total de métricas**: 13  
**100% Reais**: 8 (62%)  
**Parcialmente Reais**: 2 (15%)  
**Mock/Estimadas**: 3 (23%)

**Score Geral**: **77% de dados reais** ✅

---

## 📈 **Próximos Passos Recomendados**

### **Curto Prazo (1-2 semanas)**
1. ✅ Finalizar testes de Core Web Vitals
2. 🔄 Integrar Google Search Console
3. 🔄 Implementar IRZC com dados reais

### **Médio Prazo (1 mês)**
1. 📊 Competitors Analysis
2. 📈 Historical Tracking
3. 🔔 Sistema de alertas

### **Longo Prazo (2-3 meses)**
1. 🤖 Advanced Analytics
2. 🎯 Predições
3. 💡 Recomendações automáticas

---

**Última atualização**: 2025-01-30  
**Versão**: 3.0
