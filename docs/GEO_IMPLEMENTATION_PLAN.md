# Plano de Implementação: Métricas GEO

## 1. Campos Novos no Modelo `Run`

```python
# GEO - Brand Presence
brand_mention_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
brand_first_mention_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # caractere onde aparece
brand_mention_density: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # menções / 1000 chars
brand_prominence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100

# GEO - Citation Quality
citation_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
first_citation_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # posição ordinal (1-N)

# GEO - Competitive
competitor_mention_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-1
share_of_voice_llm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100

# GEO - Engagement
conversational_trigger_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
engagement_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
```

---

## 2. Funções de Cálculo

### 2.1 Brand Presence Metrics

```python
def calculate_brand_presence_metrics(
    response_text: str,
    project_name: str,
    project_domains: List[str]
) -> Dict[str, Any]:
    """
    Calcula métricas de presença de marca na resposta.
    
    Returns:
        {
            "brand_mention_count": int,
            "brand_first_mention_position": int | None,  # posição em chars
            "brand_mention_density": float,  # menções por 1000 chars
            "brand_prominence_score": float  # 0-100
        }
    """
```

**Lógica:**
1. Normalizar nomes (case-insensitive, variações)
2. Contar ocorrências exatas + fuzzy match (90% similarity)
3. Encontrar primeira posição (em caracteres)
4. Densidade = (count / len(text)) * 1000
5. Prominence score:
   - Primeira posição nos primeiros 20% do texto: +40 pts
   - Densidade alta (>2 por 1000 chars): +30 pts
   - Mencionado no primeiro parágrafo: +30 pts

---

### 2.2 Citation Quality Score

```python
def calculate_citation_quality_score(
    citations: List[Citation],
    response_text: str
) -> Dict[str, Any]:
    """
    Calcula qualidade das citações "nossas".
    
    Returns:
        {
            "citation_quality_score": float,  # 0-100
            "first_citation_position": int | None  # posição ordinal
        }
    """
```

**Lógica:**
- Filtrar `is_ours=True`
- Para cada citação:
  - **Posição (40%):** Primeira citação = 40, última = 10
  - **Anchor text (20%):** Descritivo = 20, genérico = 5
  - **Contexto (30%):** Citação com contexto positivo/recomendação = 30
  - **Domínio (10%):** Domínio primário = 10, secundário = 5
- Média ponderada

---

### 2.3 Competitive Metrics

```python
def calculate_competitive_metrics(
    response_text: str,
    project_name: str,
    competitors_from_gemini: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calcula métricas competitivas.
    
    Returns:
        {
            "competitor_mention_ratio": float,  # 0-1
            "share_of_voice_llm": float  # 0-100
        }
    """
```

**Lógica:**
1. Contar menções de cada competitor no `response_text`
2. `competitor_mention_ratio = our_count / (our_count + sum(comp_counts))`
3. `share_of_voice_llm = competitor_mention_ratio * 100`

---

### 2.4 Engagement Score

```python
def calculate_engagement_metrics(
    response_text: str
) -> Dict[str, Any]:
    """
    Detecta gatilhos conversacionais e calcula score de engajamento.
    
    Returns:
        {
            "conversational_trigger_count": int,
            "engagement_score": float  # 0-100
        }
    """
```

**Triggers detectados:**
- CTAs explícitos: "visite", "saiba mais", "conheça", "experimente", "compare"
- Perguntas abertas: "você pode", "considere", "que tal"
- Indicadores de continuação: "além disso", "também é importante", "vale lembrar"
- Links/URLs presentes
- Menções de benefícios específicos

**Score:**
- 0 triggers = 0
- 1-2 triggers = 30
- 3-4 triggers = 60
- 5+ triggers = 100

---

## 3. Integração no Fluxo

### Local: `backend/app/services/tasks.py`

**Função:** `process_semantic_insights()`

**Após linha 820 (onde já temos semantic_summary):**

```python
# GEO Metrics - Brand Presence
if project_name and response_text:
    brand_metrics = calculate_brand_presence_metrics(
        response_text=response_text,
        project_name=project_name,
        project_domains=[d.domain for d in run.project.domains]
    )
    run.brand_mention_count = brand_metrics.get("brand_mention_count")
    run.brand_first_mention_position = brand_metrics.get("brand_first_mention_position")
    run.brand_mention_density = brand_metrics.get("brand_mention_density")
    run.brand_prominence_score = brand_metrics.get("brand_prominence_score")

# GEO Metrics - Citation Quality
if citations:
    citation_metrics = calculate_citation_quality_score(
        citations=citations,
        response_text=response_text
    )
    run.citation_quality_score = citation_metrics.get("citation_quality_score")
    run.first_citation_position = citation_metrics.get("first_citation_position")

# GEO Metrics - Competitive
competitors = payload.get("competitors", [])
if competitors and response_text and project_name:
    comp_metrics = calculate_competitive_metrics(
        response_text=response_text,
        project_name=project_name,
        competitors_from_gemini=competitors
    )
    run.competitor_mention_ratio = comp_metrics.get("competitor_mention_ratio")
    run.share_of_voice_llm = comp_metrics.get("share_of_voice_llm")

# GEO Metrics - Engagement
if response_text:
    engagement = calculate_engagement_metrics(response_text=response_text)
    run.conversational_trigger_count = engagement.get("conversational_trigger_count")
    run.engagement_score = engagement.get("engagement_score")
```

---

## 4. Migração de Banco

### Arquivo: `backend/migrations/add_geo_metrics.sql`

```sql
-- GEO Metrics for LLM Analysis
ALTER TABLE runs ADD COLUMN brand_mention_count INT NULL;
ALTER TABLE runs ADD COLUMN brand_first_mention_position INT NULL;
ALTER TABLE runs ADD COLUMN brand_mention_density FLOAT NULL;
ALTER TABLE runs ADD COLUMN brand_prominence_score FLOAT NULL;

ALTER TABLE runs ADD COLUMN citation_quality_score FLOAT NULL;
ALTER TABLE runs ADD COLUMN first_citation_position INT NULL;

ALTER TABLE runs ADD COLUMN competitor_mention_ratio FLOAT NULL;
ALTER TABLE runs ADD COLUMN share_of_voice_llm FLOAT NULL;

ALTER TABLE runs ADD COLUMN conversational_trigger_count INT NULL;
ALTER TABLE runs ADD COLUMN engagement_score FLOAT NULL;
```

---

## 5. Frontend: Schemas & API

### `backend/app/schemas/schemas.py`

Adicionar aos schemas `RunOut`, `RunListItem`, `RunDetailOut`:

```python
# GEO Metrics
brand_mention_count: Optional[int] = None
brand_prominence_score: Optional[float] = None
citation_quality_score: Optional[float] = None
share_of_voice_llm: Optional[float] = None
engagement_score: Optional[float] = None
```

### Frontend: `frontend/src/lib/api.ts`

Adicionar aos tipos `RunListItem` e `RunDetail`:

```typescript
// GEO Metrics
brand_mention_count?: number;
brand_prominence_score?: number;
citation_quality_score?: number;
share_of_voice_llm?: number;
engagement_score?: number;
```

---

## 6. Dashboard GEO

### Novo componente: `frontend/src/pages/GEODashboard.tsx`

**Cards principais:**
1. **Brand Visibility Score** (média de prominence)
2. **Share of Voice** (média de share_of_voice_llm)
3. **Citation Quality** (média de citation_quality_score)
4. **Engagement Rate** (média de engagement_score)

**Gráficos:**
- Evolução temporal de todas as métricas
- Comparação por engine (ChatGPT vs Gemini vs Perplexity)
- Top prompts por prominence
- Competitive landscape (nossa presença vs concorrentes)

---

## 7. Backfill de Dados Históricos

### Script: `scripts/backfill_geo_metrics.py`

Processar runs existentes que já têm:
- `response_text` preenchido
- `semantic_insights` calculado
- `citations` relacionadas

---

## 8. Testes

### Casos de teste:
1. Resposta sem mencionar marca → scores = 0
2. Resposta com marca no início → high prominence
3. Resposta com 10 competidores → low share of voice
4. Resposta com CTAs → high engagement
5. Citação de domínio primário na posição 1 → high quality

---

## 9. Documentação para Usuário

### Adicionar seção ao manual:
**"Entendendo suas Métricas GEO"**

- O que é Brand Prominence
- Como interpretar Share of Voice
- Quando se preocupar com Citation Quality
- Como melhorar Engagement Score

---

## 10. Cronograma Estimado

| Fase | Tarefa | Tempo | Status |
|------|--------|-------|--------|
| 1 | Análise e documentação | 2h | ✅ Done |
| 2 | Migração de banco + modelos | 1h | ⏳ Next |
| 3 | Funções de cálculo | 4h | ⏳ |
| 4 | Integração em tasks.py | 1h | ⏳ |
| 5 | Schemas + API | 1h | ⏳ |
| 6 | Frontend (cards + tipos) | 2h | ⏳ |
| 7 | Dashboard GEO | 4h | ⏳ |
| 8 | Backfill script | 2h | ⏳ |
| 9 | Testes | 2h | ⏳ |
| 10 | Documentação | 1h | ⏳ |
| **TOTAL** | | **20h** | |

---

## 11. Métricas de Sucesso

Após implementação, devemos conseguir responder:

1. ✅ Qual engine cita mais nossa marca? (ChatGPT vs Gemini vs Perplexity)
2. ✅ Estamos perdendo share of voice para quais competidores?
3. ✅ Quais prompts geram maior prominence?
4. ✅ Nossa citação quality está melhorando ao longo do tempo?
5. ✅ Que tipo de resposta gera mais engagement?
6. ✅ Estamos ausentes em quantos % das respostas do nosso segmento?
