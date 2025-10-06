# Mapeamento de Campos - Exportações GEO (SERP, Indicadores, Estrutura Web)

## Fonte de Dados Disponíveis

### Run (backend/app/models/models.py)
- `id`, `prompt_version_id`, `project_id`, `subproject_id`
- `response_text`: Texto completo da resposta
- `im_seo_score`, `im_seoia_score`, `eeat_score`, `irzc_score`
- `eeat_expertise`, `eeat_experience`, `eeat_authoritativeness`, `eeat_trustworthiness`
- `entities_detected`, `ia_ready_blocks_count`, `has_lists`, `has_faqs`, `has_tables`, `has_step_by_step`
- `core_web_vitals_score`, `lcp_score`, `fid_score`, `cls_score`
- `latency_ms`

### SerpFeature (backend/app/models/models.py)
- `ai_overview_json`: JSON com `summary`, `text_blocks`, `references`, `follow_up_questions`
- `has_ai_overview`, `has_paa`, `has_knowledge_panel`
- `paa_questions`: String (JSON array) com perguntas PAA
- `knowledge_panel_json`: String (JSON) com dados do Knowledge Panel
- `organic_position`, `competitors_in_top10`

### Citation (backend/app/models/models.py)
- `domain`, `url`, `is_ours`, `position`

### RunSemanticInsight (backend/app/models/models.py)
- `payload`: JSON com `entities`, `keywords`, `perception`, `summary`, `competitors`, `wordcloud`

### Prompt (via PromptVersion → Prompt)
- `text`: Texto da pergunta

---

## Tabela 1: SERP - AI Overview

| Campo | Descrição | Fonte | Regra de Cálculo |
|-------|-----------|-------|------------------|
| **run_id** | ID da execução | `Run.id` | Direto |
| **prompt** | Texto da pergunta | `Prompt.text` (via `Run.prompt_version_id`) | Direto |
| **produto** | Produto/Categoria | `SubProject.name` ou `Run.subproject_id` | Direto ou mapear de metadados |
| **relevancia** | Nível de relevância | `Run` + análise semântica | Classificar baseado em `im_seo_score` e `funnel_stage`: <br>- >= 80: "Alta"<br>- >= 60: "Média-Alta"<br>- >= 40: "Média"<br>- < 40: "Consultiva/Reputacional" |
| **pergunta_bb** | BB mencionado na pergunta? | `Prompt.text` | Verificar se contém "banco do brasil", "bb", "banco brasil" (case-insensitive) → "Sim"/"Não" |
| **funil** | Etapa do funil | `Run.funnel_stage` | Mapear: <br>- "reconhecimento" → "Reconhecimento"<br>- "consideracao" → "Consideração"<br>- "conversao" → "Conversão"<br>- null → "Não classificado" |
| **resposta** | Texto completo da resposta | `SerpFeature.ai_overview_json` | Concatenar `summary` + snippets de `text_blocks` |
| **tem_url** | Resposta tem URLs? | `SerpFeature.ai_overview_json['references']` | len(references) > 0 → "Sim"/"Não" |
| **url_bb** | Resposta tem URL do BB? | `SerpFeature.ai_overview_json['references']` + `Citation.is_ours` | Verificar se algum `reference.domain` contém "bb.com.br" → "Sim"/"Não" |
| **posicao_url_bb** | Melhor posição da URL do BB | `SerpFeature.ai_overview_json['references']` | Index (1-based) da primeira `reference` com domain contendo "bb.com.br", ou null |
| **citation_bb** | Sequência binária de posições | `SerpFeature.ai_overview_json['references']` | String binária (ex: "01001"): 1 se BB, 0 se não, para cada posição |
| **ranking_url** | JSON ranking completo URLs | `SerpFeature.ai_overview_json['references']` | JSON array: `[{"position": 1, "domain": "x", "url": "y", "is_bb": true/false}, ...]` |
| **nome_bb** | Nome BB mencionado no texto? | `SerpFeature.ai_overview_json['summary']` + `text_blocks` | Verificar menções "banco do brasil", "bb" no texto → "Sim"/"Não" |
| **posicao_bb** | Posição da 1ª menção ao BB | `SerpFeature.ai_overview_json['summary']` + `text_blocks` | Index (caracteres ou palavra) da primeira menção, ou null |
| **ranking_txt** | JSON ranking bancos citados | Análise de texto + `RunSemanticInsight.payload['competitors']` | JSON array: `[{"name": "Banco do Brasil", "mentions": 5, "position": 1}, ...]` |
| **tem_paa** | PAA apareceu? | `SerpFeature.has_paa` | Direto → "Sim"/"Não" |
| **bb_paa** | BB citado no PAA? | `SerpFeature.paa_questions` (JSON) | Parse JSON, verificar menções BB → "Sim"/"Não" |
| **posicao_bb_paa** | Posição BB no PAA | `SerpFeature.paa_questions` (JSON) | Index da primeira pergunta que menciona BB, ou null |
| **tem_kp** | Knowledge Panel apareceu? | `SerpFeature.has_knowledge_panel` | Direto → "Sim"/"Não" |
| **bb_kp** | BB citado no KP? | `SerpFeature.knowledge_panel_json` | Parse JSON, verificar se é sobre BB → "Sim"/"Não" |

---

## Tabela 2: Indicadores - AI Overview

| Campo | Descrição | Fonte | Regra de Cálculo |
|-------|-----------|-------|------------------|
| **run_id** | ID da execução | `Run.id` | Direto |
| **prompt** | Texto da pergunta | `Prompt.text` | Direto |
| **produto** | Produto/Categoria | `SubProject.name` | Direto |
| **nome_bb** | BB mencionado? | Análise texto | Verificar menções no texto → "Sim"/"Não" |
| **score_eeat_bb** | Score EEAT agregado | `Run.eeat_score` | Direto (0-100) |
| **experiencia_bb** | Componente Experiência | `Run.eeat_experience` | Direto (0-100) |
| **expertise_bb** | Componente Expertise | `Run.eeat_expertise` | Direto (0-100) |
| **autoridade_bb** | Componente Autoridade | `Run.eeat_authoritativeness` | Direto (0-100) |
| **confiabilidade_bb** | Componente Confiabilidade | `Run.eeat_trustworthiness` | Direto (0-100) |
| **ranking_eeat** | JSON ranking EEAT bancos | `RunSemanticInsight.payload['competitors']` + scores EEAT | JSON: `[{"bank": "BB", "score": 52.5}, ...]` |
| **inovador_bb** | Nota Inovação | `RunSemanticInsight.payload['perception']` | Se `primary_category == 'inovacao'` → 5, senão verificar `secondary_categories` → 0-5 |
| **seguranca_bb** | Nota Tradição/Segurança | `RunSemanticInsight.payload['perception']` | Se categoria inclui "tradicao" → 0-5 |
| **custo_bb** | Nota Baixo Custo | `RunSemanticInsight.payload['perception']` | Se categoria inclui "custo" → 0-5 |
| **atendimento_bb** | Nota Atendimento | `RunSemanticInsight.payload['perception']` | Se categoria inclui "atendimento" → 0-5 |
| **resultado_percepcao** | JSON notas completas | `RunSemanticInsight.payload['perception']` | JSON: `{"inovacao": 5, "seguranca": 3, "custo": 4, "atendimento": 2}` |
| **qt_total_entidades** | Total de entidades | `Run.entities_detected` ou `len(RunSemanticInsight.payload['entities'])` | Direto |
| **qt_entidades_bb** | Entidades vinculadas ao BB | `RunSemanticInsight.payload['entities']` | Contar entidades com `name` contendo "banco do brasil", "bb" |
| **conexoes_bancos** | JSON conexões banco→produto | `RunSemanticInsight.payload['relationships']` | Filtrar relacionamentos tipo "banco" → "produto": `[{"bank": "BB", "products": ["Conta", "Cartão"]}, ...]` |

---

## Tabela 3: Estrutura Web - AI Overview

| Campo | Descrição | Fonte | Regra de Cálculo |
|-------|-----------|-------|------------------|
| **run_id** | ID da execução | `Run.id` | Direto |
| **prompt** | Texto da pergunta | `Prompt.text` | Direto |
| **produto** | Produto/Categoria | `SubProject.name` | Direto |
| **url_bb** | URL BB citada? | `Citation.is_ours == True` | len([c for c in citations if c.is_ours]) > 0 → "Sim"/"Não" |
| **tem_titulo_bb** | Página tem <title>? | **Não disponível** | ❌ Campo não capturado. Retornar null ou coletar via scraping |
| **txt_titulo_bb** | Textos dos títulos | **Não disponível** | ❌ Requer scraping das URLs `is_ours` |
| **tem_descricao_bb** | Tem meta description? | **Não disponível** | ❌ Requer scraping |
| **txt_descricao_bb** | Textos das descriptions | **Não disponível** | ❌ Requer scraping |
| **tem_keywords** | Tem meta keywords? | **Não disponível** | ❌ Requer scraping |
| **txt_keywords** | Lista das keywords | **Não disponível** | ❌ Requer scraping |
| **tem_robots_bb** | Possui instruções robots? | **Não disponível** | ❌ Requer scraping |
| **txt_robots_bb** | Instruções robots | **Não disponível** | ❌ Requer scraping |
| **tem_ogtags_bb** | Possui Open Graph Tags? | **Não disponível** | ❌ Requer scraping |
| **ogtags_bb** | JSON OG tags | **Não disponível** | ❌ Requer scraping |
| **tem_aiblocks_bb** | Possui AI Ready Blocks? | `Run.ia_ready_blocks_count` | > 0 → "Sim"/"Não" |
| **qt_aiblocks_bb** | Quantidade de blocks | `Run.ia_ready_blocks_count` | Direto |
| **tipos_aiblocks_bb** | Tipos de blocks | `Run.has_lists`, `has_faqs`, `has_tables`, `has_step_by_step` | Lista: ex: ["listas", "FAQs", "tabelas"] |
| **ranking_web** | JSON ranking estrutura web | **Parcialmente disponível** | JSON baseado em `ia_ready_blocks_count`, mas sem dados completos de outros bancos |
| **latencia** | Latência da página BB | `Run.latency_ms` ou **não disponível** | Se disponível: direto. Senão, requer medição via PageSpeed/Lighthouse |
| **performance** | Indicador de performance | `Run.core_web_vitals_score` | Direto (0-100) |

---

## Campos Faltantes / Ações Necessárias

### 🔴 CRÍTICO - Dados não coletados atualmente

#### PAA e Knowledge Panel
- **Problema**: `SerpFeature.has_paa=False`, `paa_questions=None`, `knowledge_panel_json=None` em todos os runs
- **Solução**: Revisar serviço de ingestão SerpAPI para mapear campos `related_questions` e `knowledge_graph` corretamente
- **Arquivo**: Buscar por serviço que persiste `SerpFeature` (provavelmente em `backend/app/services/`)

#### Estrutura Web (Meta Tags, OG Tags, Robots)
- **Problema**: Nenhum campo de estrutura web está sendo coletado
- **Solução**: Implementar scraping das URLs `is_ours=True` para capturar:
  - `<title>`, `<meta name="description">`, `<meta name="keywords">`
  - `<meta name="robots">`, Open Graph tags
  - Dados de performance (latência, CWV)
- **Impacto**: Sem isso, Tabela 3 (Estrutura Web) ficará 80% vazia

### ⚠️ ALTA PRIORIDADE - Dados parcialmente disponíveis

#### Scores EEAT Detalhados
- **Status**: `Run.eeat_score` existe (agregado), mas subcomponentes (`eeat_expertise`, `eeat_experience`, etc.) podem estar null
- **Verificação**: Confirmar se esses campos estão sendo calculados e salvos corretamente
- **Alternativa**: Derivar de `RunSemanticInsight.payload` se disponível

#### Perception Categories (Inovação, Custo, etc.)
- **Status**: `RunSemanticInsight.payload['perception']` traz `primary_category` e `secondary_categories`
- **Solução**: Mapear categorias para notas 0-5 conforme regra:
  - Categoria primária: 5 pontos
  - Categoria secundária: 3 pontos
  - Não mencionada: 0 pontos

### ✅ BAIXA PRIORIDADE - Melhorias futuras

#### Ranking de Competidores (URLs, Texto, EEAT)
- **Status**: Dados parciais em `citations` e `semantic_insights.competitors`
- **Melhoria**: Enriquecer com análise cross-run para rankings mais precisos

---

## Próximos Passos

### 1. Corrigir Ingestão de Dados
- [ ] Revisar e corrigir coleta PAA (`SerpFeature.paa_questions`)
- [ ] Revisar e corrigir coleta Knowledge Panel (`SerpFeature.knowledge_panel_json`)
- [ ] Implementar scraping de meta tags para URLs `is_ours=True`
- [ ] Garantir que scores EEAT detalhados são salvos em `Run`

### 2. Implementar Endpoints de Exportação
- [ ] Criar `/api/export/serp` (Tabela SERP)
- [ ] Criar `/api/export/indicadores` (Tabela Indicadores)
- [ ] Criar `/api/export/estrutura-web` (Tabela Estrutura Web)
- [ ] Manter compatibilidade com `/api/export/csv`, `/api/export/json`, `/api/export/excel` atuais

### 3. Atualizar Frontend
- [ ] Adicionar seletor de tipo de exportação em `ExportDialog.tsx`
- [ ] Enviar todos os filtros (`prompt_id`, `run_id`, `subproject_id`) ao backend
- [ ] Exibir descrições dos novos tipos de exportação

### 4. Testes de Acurácia
- [ ] Gerar runs com dados completos (incluindo PAA/KP)
- [ ] Validar cada campo de cada tabela contra dados reais
- [ ] Testar exportação em CSV, JSON e Excel
- [ ] Documentar cobertura de dados (% de campos populados)

---

## Notas de Implementação

### Formato de Saída
- **CSV**: Uma linha por run, campos JSON como strings
- **JSON**: Estrutura aninhada com arrays
- **Excel**: Múltiplas sheets (Metadata + Data + Rankings)

### Tratamento de Dados Ausentes
- Campos string vazios: `""`
- Campos numéricos: `null`
- Campos booleanos (Sim/Não): `"Não"` quando ausente
- JSON rankings vazios: `[]`

### Performance
- Limit padrão: 200 runs
- Usar `selectinload` e `joinedload` para otimizar queries
- Implementar paginação se necessário para exports grandes
