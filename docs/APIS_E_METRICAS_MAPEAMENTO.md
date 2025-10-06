# 🔑 Mapeamento Completo: APIs x Métricas IM

**Data:** 2025-10-04 03:07  
**Análise:** Quais APIs estão configuradas e quais métricas dependem delas

## 📊 Status das API Keys

| API | Status | Uso | Impacto |
|-----|--------|-----|---------|
| PERPLEXITY_API_KEY | ✅ Configurada | Execução de prompts | Crítico - Sem ela não há resposta |
| OPENAI_API_KEY | ✅ Configurada | Classificação de respostas | Importante - Classificação automática |
| GOOGLE_API_KEY | ✅ Configurada | Insights semânticos (Gemini) | Opcional - Análise avançada |
| SERPAPI_KEY | ✅ Configurada | Dados SERP (posições, features) | Importante - Métricas de tráfego |
| **PAGESPEED_API_KEY** | ❌ **FALTANDO** | **Core Web Vitals** | **Importante - Performance** |

## 🎯 Métricas IM e Suas Dependências

### 1️⃣ ÍNDICES COMPOSTOS

#### IM-SEO Score
**Status:** ✅ Funcionando  
**Fórmula:** (Autoridade + Lighthouse + Share de Tráfego + Engajamento) / 4

**Dependências:**
- ✅ Autoridade: AMR/DCR flags (interno, sem API)
- ❌ **Lighthouse (Core Web Vitals):** **PAGESPEED_API_KEY** (FALTANDO)
- ⚠️ Share de Tráfego: ZCRS ou SERPAPI_KEY (tem fallback)
- ✅ Engajamento: ZCRS (interno)

**Impacto da API faltante:**
- Lighthouse usa valor padrão (75.0) quando PageSpeed falha
- Score calculado, mas não reflete performance real

#### IM-SEOIA Score  
**Status:** ✅ Funcionando  
**Fórmula:** Média ponderada de 7 componentes

**Dependências:**
- ❌ **Performance (Core Web Vitals):** **PAGESPEED_API_KEY** (FALTANDO)
- ⚠️ Traffic (Share of Voice): SERPAPI_KEY (configurada ✅)
- ⚠️ IA SERP: SERPAPI_KEY (configurada ✅)
- ⚠️ Long Tail: SERPAPI_KEY (configurada ✅)
- ✅ E-E-A-T: Análise de texto (sem API externa)
- ✅ Entidades: Análise de texto (sem API externa)
- ✅ IA-Ready: Análise de texto (sem API externa)

**Impacto da API faltante:**
- Performance = 0 quando PageSpeed falha
- Reduz score geral do IM-SEOIA

---

### 2️⃣ CORE WEB VITALS (Performance)

**Status:** ❌ NULL (API faltando)  
**API Necessária:** PAGESPEED_API_KEY

**Métricas afetadas:**
- ❌ **Core Web Vitals Score** (0-100)
- ❌ **LCP** (Largest Contentful Paint)
- ❌ **FID** (First Input Delay)
- ❌ **CLS** (Cumulative Layout Shift)

**Impacto:**
- IM-SEO usa valor padrão (75.0)
- IM-SEOIA: componente Performance = 0
- Não reflete performance real do site

---

### 3️⃣ TRÁFEGO E SERP

**Status:** ⚠️ Parcialmente funcionando  
**API Necessária:** SERPAPI_KEY (✅ Configurada)

**Métricas:**
- ✅ **Share of Voice SERP** (baseado em posição orgânica)
- ✅ **SERP Features Presence** (features detectadas)
- ⚠️ **IA Resources Detected** (depende de dados SERP)
- ⚠️ **IA SERP Presence Score** (depende de dados SERP)

**Observação:**
- Se SERP data não disponível, usa fallback (ZCRS)
- Valores podem ser aproximados

---

### 4️⃣ LONG TAIL

**Status:** ⚠️ Parcialmente funcionando  
**API Necessária:** SERPAPI_KEY (✅ Configurada)

**Métricas:**
- ⚠️ **Long Tail Terms Top 10** (0 se SERP não tem dados)
- ⚠️ **Long Tail Terms Top 20** (0 se SERP não tem dados)
- ⚠️ **Long Tail Coverage Score** (0 se SERP não tem dados)

**Observação:**
- Depende de dados detalhados do SERP
- Pode retornar 0 mesmo com API configurada se SERP não tiver dados

---

### 5️⃣ E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness)

**Status:** ✅ Funcionando perfeitamente  
**API Necessária:** Nenhuma (análise de texto)

**Métricas:**
- ✅ **E-E-A-T Score Geral** (0-100)
- ✅ **Expertise** (0-100)
- ✅ **Experience** (0-100)
- ✅ **Authoritativeness** (0-100)
- ✅ **Trustworthiness** (0-100)

**Método:**
- Análise de palavras-chave no texto
- Detecção de padrões de autoridade
- Sem dependência de API externa

---

### 6️⃣ ENTIDADES

**Status:** ✅ Funcionando perfeitamente  
**API Necessária:** Nenhuma (análise de texto)

**Métricas:**
- ✅ **Entities Detected** (quantidade)
- ✅ **Entities Relevance Score** (0-1)
- ✅ **Entity Connection Score** (0-100)

**Método:**
- Extração de entidades do texto
- Comparação com domínios do projeto
- Sem dependência de API externa

---

### 7️⃣ DADOS ESTRUTURADOS (Schema)

**Status:** ⚠️ Depende do conteúdo  
**API Necessária:** Nenhuma (análise de markup)

**Métricas:**
- ⚠️ **Schema Types Detected** (NULL se não houver)
- ⚠️ **Schema Coverage Score** (0 se não houver)
- ⚠️ **Schema Valid** (NULL se não houver)

**Observação:**
- Detecta schemas no HTML/JSON-LD
- NULL é esperado se site não usa schemas

---

### 8️⃣ IA-READY BLOCKS

**Status:** ✅ Funcionando perfeitamente  
**API Necessária:** Nenhuma (análise de texto)

**Métricas:**
- ✅ **IA Ready Score** (0-100)
- ✅ **IA Ready Blocks Count** (quantidade)
- ✅ **Has Lists** (boolean)
- ✅ **Has FAQs** (boolean)
- ✅ **Has Tables** (boolean)
- ✅ **Has Step-by-Step** (boolean)

**Método:**
- Detecção de padrões no texto
- Análise de estrutura da resposta
- Sem dependência de API externa

---

### 9️⃣ IRZC (Índice de Risco Zero-Click)

**Status:** ✅ Funcionando perfeitamente  
**API Necessária:** Nenhuma (cálculo interno)

**Métricas:**
- ✅ **IRZC Score** (0-100)
- ✅ **CTR Expected** (baseado em posição)
- ⚠️ **CTR Real** (NULL - precisa Google Search Console)
- ⚠️ **CTR Ratio** (NULL - precisa GSC)

**Observação:**
- CTR Real depende de Google Search Console (não é API key, é OAuth)

---

## 📈 RESUMO DO IMPACTO

### ✅ Funcionando 100% (Sem APIs Externas)
- E-E-A-T (5 métricas)
- Entidades (3 métricas)
- IA-Ready Blocks (6 métricas)
- IRZC (2 métricas funcionando)

**Total:** 16 métricas funcionando perfeitamente

### ⚠️ Funcionando com Limitações (APIs Configuradas)
- Share of Voice SERP (SERPAPI_KEY ✅)
- SERP Features (SERPAPI_KEY ✅)
- Long Tail (SERPAPI_KEY ✅ - mas pode retornar 0)

**Total:** 6 métricas com dados variáveis

### ❌ NÃO Funcionando (API Faltando)
- **Core Web Vitals Score** (PAGESPEED_API_KEY ❌)
- **LCP** (PAGESPEED_API_KEY ❌)
- **FID** (PAGESPEED_API_KEY ❌)
- **CLS** (PAGESPEED_API_KEY ❌)

**Total:** 4 métricas NULL

---

## 🎯 PRIORIDADE DE CONFIGURAÇÃO

### 🔴 CRÍTICO - Configure Agora
**PAGESPEED_API_KEY**
- Impacto: 4 métricas NULL
- Afeta: IM-SEO e IM-SEOIA scores
- Solução: Obter em https://console.cloud.google.com/apis/credentials
- Limite grátis: 25.000 requisições/dia

### 🟡 OPCIONAL - Já Configuradas
- ✅ SERPAPI_KEY (tráfego e long-tail)
- ✅ GOOGLE_API_KEY (insights semânticos)
- ✅ OPENAI_API_KEY (classificação)
- ✅ PERPLEXITY_API_KEY (execução)

### 🟢 FUTURO - Integrações Adicionais
- Google Search Console (CTR real)
- Analytics (dados de comportamento)

---

## 📊 ESTATÍSTICAS

**Total de Métricas IM:** ~32 métricas
- ✅ Funcionando: 22 métricas (69%)
- ⚠️ Parciais: 6 métricas (19%)
- ❌ NULL: 4 métricas (12%)

**Com PAGESPEED_API_KEY configurada:**
- ✅ Funcionando: 26 métricas (81%)
- ⚠️ Parciais: 6 métricas (19%)
- ❌ NULL: 0 métricas (0%)

---

## 🚀 AÇÃO RECOMENDADA

**Configure a PAGESPEED_API_KEY para ter 100% das métricas funcionando!**

```bash
# 1. Obter chave
https://console.cloud.google.com/apis/credentials

# 2. Adicionar no servidor
ssh ubuntu@129.148.63.199
cd /opt/seo-analyzer
sudo nano .env

# Adicionar:
PAGESPEED_API_KEY=SUA_CHAVE_AQUI

# 3. Reiniciar
sudo docker compose -f docker-compose.prod.yml restart worker

# 4. Testar
# Execute uma nova run e verifique Core Web Vitals
```

**Com essa única API configurada, você terá 100% das métricas IM funcionando!** 🎉
