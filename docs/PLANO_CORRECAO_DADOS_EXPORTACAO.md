# Plano de Correção - Dados Faltantes para Exportação GEO

**Data:** 2025-10-06  
**Objetivo:** Corrigir 100% dos dados faltantes antes de implementar frontend de exportação

---

## 🔴 Problemas Críticos Identificados

### 1. PAA (People Also Ask) - NÃO COLETADO
**Status Atual:**
- `SerpFeature.has_paa = False`
- `SerpFeature.paa_questions = None`

**Impacto:**
- Tabela SERP: Colunas `tem_paa`, `bb_paa`, `posicao_bb_paa` ficam vazias

**Causa Raiz:**
- Pipeline de coleta SerpAPI não está mapeando campo `related_questions`

**Solução:**
1. Localizar serviço que persiste `SerpFeature` (provavelmente em `backend/app/services/`)
2. Adicionar mapeamento para `related_questions` da resposta SerpAPI
3. Persistir em `SerpFeature.paa_questions` (JSON string)
4. Atualizar `SerpFeature.has_paa = True` quando existir

---

### 2. Knowledge Panel - NÃO COLETADO
**Status Atual:**
- `SerpFeature.has_knowledge_panel = False`
- `SerpFeature.knowledge_panel_json = None`

**Impacto:**
- Tabela SERP: Colunas `tem_kp`, `bb_kp` ficam vazias

**Causa Raiz:**
- Pipeline não está mapeando `knowledge_graph` da SerpAPI

**Solução:**
1. No mesmo serviço de `SerpFeature`
2. Mapear campo `knowledge_graph` da resposta SerpAPI
3. Persistir em `SerpFeature.knowledge_panel_json` (JSON string)
4. Atualizar `SerpFeature.has_knowledge_panel = True` quando existir

---

### 3. URLs do BB no AI Overview References - INCONSISTÊNCIA
**Status Atual:**
- `Run.citations` tem 3 URLs BB (`is_ours=True`)
- AI Overview `references` tem 0 URLs BB

**Impacto:**
- Tabela SERP: Colunas `url_bb`, `posicao_url_bb`, `citation_bb`, `ranking_url` podem estar incorretas

**Causa Raiz:**
- Citations e AI Overview references vêm de fontes diferentes
- AI Overview references não incluem domínios `bb.com.br`

**Solução:**
1. Verificar se AI Overview da SerpAPI realmente traz references com BB
2. Se sim: Ajustar parsing para capturar corretamente
3. Se não: Usar `Run.citations` como fonte primária (já implementado no endpoint)
4. Documentar que `ranking_url` vem de citations quando AI Overview não tiver

---

### 4. Funnel Stage - NÃO CLASSIFICADO
**Status Atual:**
- `Run.funnel_stage = None`

**Impacto:**
- Tabela SERP: Coluna `funil` fica "Não classificado"

**Causa Raiz:**
- Sistema de classificação não está sendo executado ou não está salvando resultado

**Solução:**
1. Localizar onde `funnel_stage` deveria ser calculado
2. Opções:
   - a) Implementar classificação automática baseada em palavras-chave da pergunta
   - b) Usar análise do Gemini Semantic Service
   - c) Classificação manual via UI (futuro)
3. Persistir resultado em `Run.funnel_stage`

---

### 5. Brand Positioning - NÃO CLASSIFICADO
**Status Atual:**
- `Run.brand_positioning = None`

**Impacto:**
- Análise de posicionamento incompleta (não usado diretamente em exportação atual)

**Causa Raiz:**
- Sistema de análise de brand positioning não implementado ou não salvando

**Solução:**
1. Verificar se campo está sendo usado
2. Se sim: Implementar análise (protagonista/competidor/ausente)
3. Se não: Manter como enhancement futuro

---

### 6. Core Web Vitals - NÃO CALCULADO
**Status Atual:**
- `Run.core_web_vitals_score = None`
- `Run.lcp_score, fid_score, cls_score = None`
- Mas `Run.latency_ms = 5079` existe

**Impacto:**
- Tabela Estrutura Web: Coluna `performance` fica vazia

**Causa Raiz:**
- PageSpeed API não está sendo chamada OU resultado não está sendo salvo

**Solução:**
1. Verificar se `PAGESPEED_API_KEY` está configurada
2. Verificar serviço que calcula Core Web Vitals (provavelmente `backend/app/services/tasks.py`)
3. Garantir que está sendo chamado para URLs `is_ours=True`
4. Persistir scores em `Run`

---

### 7. Competitors - NÃO POPULADO
**Status Atual:**
- `RunSemanticInsight.payload['competitors'] = []`

**Impacto:**
- Tabela SERP: Coluna `ranking_txt` fica vazia
- Tabela Indicadores: `ranking_eeat` fica vazio

**Causa Raiz:**
- Gemini Semantic Service não está detectando/retornando competitors

**Solução:**
1. Verificar prompt do Gemini em `backend/app/services/gemini_semantic.py`
2. Garantir que pede análise de competitors/bancos mencionados
3. Validar parsing do JSON de resposta
4. Se necessário: Ajustar prompt para ser mais explícito

---

### 8. Meta Tags (Estrutura Web) - NÃO COLETADO
**Status Atual:**
- Todos campos de meta tags são `None`:
  - `tem_titulo_bb`, `txt_titulo_bb`
  - `tem_descricao_bb`, `txt_descricao_bb`
  - `tem_keywords`, `txt_keywords`
  - `tem_robots_bb`, `txt_robots_bb`
  - `tem_ogtags_bb`, `ogtags_bb`

**Impacto:**
- Tabela Estrutura Web: 12 de 18 colunas vazias (67% vazio)

**Causa Raiz:**
- Funcionalidade de scraping de meta tags NÃO EXISTE

**Solução:**
1. Criar novo serviço de scraping (ex: `backend/app/services/web_scraper.py`)
2. Para cada URL com `is_ours=True`:
   - Fazer request HTTP
   - Parse HTML (BeautifulSoup)
   - Extrair: title, meta description, meta keywords, meta robots, OG tags
3. Persistir em novo modelo `WebStructure` (ou expandir `Citation`)
4. Atualizar endpoint de exportação para buscar esses dados

---

## 📋 Plano de Execução

### Fase 1: Correções Críticas (Prioridade ALTA)
**Tempo estimado: 2-3 horas**

#### ✅ 1.1 Corrigir Coleta PAA e Knowledge Panel
- [ ] Localizar serviço de ingestão SerpAPI
- [ ] Adicionar mapeamento `related_questions` → `paa_questions`
- [ ] Adicionar mapeamento `knowledge_graph` → `knowledge_panel_json`
- [ ] Testar com nova run
- [ ] Validar que dados foram salvos

#### ✅ 1.2 Corrigir Core Web Vitals
- [ ] Verificar configuração `PAGESPEED_API_KEY`
- [ ] Localizar serviço de cálculo (tasks.py)
- [ ] Garantir chamada para URLs BB
- [ ] Testar com nova run
- [ ] Validar scores salvos

#### ✅ 1.3 Corrigir Competitors no Semantic Insights
- [ ] Revisar prompt Gemini
- [ ] Ajustar para pedir lista de bancos/competitors
- [ ] Validar parsing do JSON de resposta
- [ ] Testar com nova run
- [ ] Validar competitors populados

### Fase 2: Classificações (Prioridade MÉDIA)
**Tempo estimado: 1-2 horas**

#### ✅ 2.1 Implementar Funnel Stage
- [ ] Definir regras de classificação (palavras-chave ou Gemini)
- [ ] Implementar lógica
- [ ] Persistir em `Run.funnel_stage`
- [ ] Testar

#### ✅ 2.2 Implementar Brand Positioning (Opcional)
- [ ] Definir se é necessário agora
- [ ] Se sim: Implementar análise
- [ ] Se não: Documentar como enhancement futuro

### Fase 3: Scraping de Meta Tags (Prioridade BAIXA)
**Tempo estimado: 3-4 horas**

#### ✅ 3.1 Criar Serviço de Web Scraping
- [ ] Criar `backend/app/services/web_scraper.py`
- [ ] Implementar funções:
  - `scrape_meta_tags(url)` → dict com todas meta tags
  - `scrape_og_tags(url)` → dict com Open Graph tags
- [ ] Adicionar tratamento de erros (timeout, 404, etc)

#### ✅ 3.2 Criar Modelo para Estrutura Web
Opção A: Novo modelo
```python
class WebStructure(Base):
    __tablename__ = "web_structure"
    id: Mapped[str] = mapped_column(primary_key=True)
    url: Mapped[str]
    title: Mapped[Optional[str]]
    meta_description: Mapped[Optional[str]]
    meta_keywords: Mapped[Optional[str]]
    meta_robots: Mapped[Optional[str]]
    og_tags_json: Mapped[Optional[str]]  # JSON
    scraped_at: Mapped[datetime]
```

Opção B: Expandir Citation
- Adicionar campos de meta tags diretamente

#### ✅ 3.3 Integrar no Pipeline
- [ ] Chamar scraping após criar citations `is_ours=True`
- [ ] Salvar resultados
- [ ] Atualizar endpoint de exportação

### Fase 4: Validação Final
**Tempo estimado: 1 hora**

#### ✅ 4.1 Testes End-to-End
- [ ] Rodar 5 novas runs completas
- [ ] Verificar cada campo de cada tabela
- [ ] Calcular % de cobertura de dados
- [ ] Documentar gaps remanescentes

#### ✅ 4.2 Atualizar Documentação
- [ ] Atualizar `EXPORT_TABLES_MAPPING.md`
- [ ] Documentar campos 100% populados
- [ ] Documentar campos parciais/opcionais
- [ ] Criar guia de troubleshooting

---

## 🎯 Ordem de Execução Recomendada

### Dia 1 (4-5 horas)
1. ✅ Corrigir PAA e Knowledge Panel (1h)
2. ✅ Corrigir Core Web Vitals (1h)
3. ✅ Corrigir Competitors (1.5h)
4. ✅ Implementar Funnel Stage (1h)
5. ✅ Testar tudo com novas runs (0.5h)

### Dia 2 (3-4 horas) - Opcional
6. ✅ Criar serviço de scraping (2h)
7. ✅ Integrar no pipeline (1h)
8. ✅ Testes finais (1h)

---

## 📊 Métricas de Sucesso

### Antes (Estado Atual)
- **Tabela SERP**: 12/19 colunas (~63%)
- **Tabela Indicadores**: 15/18 colunas (~83%)
- **Tabela Estrutura Web**: 6/18 colunas (~33%)
- **Média Geral**: ~60% de dados

### Meta Após Fase 1
- **Tabela SERP**: 18/19 colunas (~95%)
- **Tabela Indicadores**: 17/18 colunas (~94%)
- **Tabela Estrutura Web**: 6/18 colunas (~33%)
- **Média Geral**: ~74% de dados

### Meta Após Fase 2
- **Tabela SERP**: 19/19 colunas (100%)
- **Tabela Indicadores**: 18/18 colunas (100%)
- **Tabela Estrutura Web**: 8/18 colunas (~44%)
- **Média Geral**: ~81% de dados

### Meta Após Fase 3 (Completo)
- **Tabela SERP**: 19/19 colunas (100%)
- **Tabela Indicadores**: 18/18 colunas (100%)
- **Tabela Estrutura Web**: 18/18 colunas (100%)
- **Média Geral**: 100% de dados ✅

---

## 🚀 Próximos Passos Imediatos

1. **AGORA**: Localizar serviço de ingestão SerpAPI
   ```bash
   grep -r "SerpFeature" backend/app/services/
   grep -r "serp" backend/app/services/
   ```

2. **DEPOIS**: Identificar onde `funnel_stage` deveria ser calculado
   ```bash
   grep -r "funnel_stage" backend/
   ```

3. **POR ÚLTIMO**: Verificar `PAGESPEED_API_KEY` e Core Web Vitals
   ```bash
   grep -r "core_web_vitals" backend/
   grep -r "PAGESPEED" backend/
   ```

---

## ⚠️ Riscos e Mitigações

### Risco 1: SerpAPI não retorna PAA/KP
**Mitigação**: Verificar documentação SerpAPI, ajustar parâmetros de request

### Risco 2: PageSpeed API com quota limitada
**Mitigação**: Implementar cache, limitar chamadas apenas para URLs BB

### Risco 3: Scraping bloqueado por rate limit
**Mitigação**: Implementar delays, user-agent rotativo, fallback para null

### Risco 4: Tempo de execução muito longo
**Mitigação**: Executar scraping async/background, não bloquear run

---

## 📝 Checklist de Validação

Antes de ir para frontend, validar:

- [ ] 5 runs consecutivas têm `has_paa` correto
- [ ] 5 runs consecutivas têm `has_knowledge_panel` correto
- [ ] 5 runs consecutivas têm `core_web_vitals_score` calculado
- [ ] 5 runs consecutivas têm `competitors` no semantic insights
- [ ] 5 runs consecutivas têm `funnel_stage` classificado
- [ ] Export SERP retorna dados 95%+ completos
- [ ] Export Indicadores retorna dados 95%+ completos
- [ ] Export Estrutura Web retorna dados mínimos (sem scraping OK)

---

**Status:** 🔴 Aguardando início da Fase 1  
**Próxima Ação:** Localizar serviço de ingestão SerpAPI
