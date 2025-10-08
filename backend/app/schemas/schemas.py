from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str
    country: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None


class ProjectOut(ProjectCreate):
    id: str


class DomainCreate(BaseModel):
    domain: str
    pattern_regex: Optional[str] = None
    is_primary: bool = False


class DomainOut(DomainCreate):
    id: str
    project_id: str


class PromptCreate(BaseModel):
    name: str
    text: str
    intent: Optional[str] = None
    persona: Optional[str] = None
    variables: Optional[dict] = Field(default=None, alias="variables")


class PromptOut(BaseModel):
    id: str
    project_id: str
    name: str
    text: str
    intent: Optional[str]
    persona: Optional[str]
    active: bool


class PromptVersionCreate(BaseModel):
    text: str


class PromptVersionOut(BaseModel):
    id: str
    prompt_id: str
    version: int
    text: str
    created_at: datetime


class EngineCreate(BaseModel):
    name: str
    region: Optional[str] = None
    device: Optional[str] = None
    config_json: Optional[dict] = None


class EngineOut(EngineCreate):
    id: str
    project_id: str


class RunCreate(BaseModel):
    project_id: str
    prompt_version_id: str
    engines: List[EngineCreate]
    cycles: int = 1
    cycle_delay_seconds: Optional[int] = None
    schedule: Optional[str] = None
    subproject_id: Optional[str] = None


class RunOut(BaseModel):
    id: str
    status: str
    zcrs: Optional[float] = None
    amr_flag: Optional[bool] = None
    dcr_flag: Optional[bool] = None
    # novos campos (opc)
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    tokens_total: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[int] = None
    cycles_total: Optional[int] = None
    # Classificação Zero-Click
    response_type: Optional[str] = None
    sufficiency_level: Optional[str] = None
    actionability_type: Optional[str] = None
    trust_source: Optional[str] = None
    brand_positioning: Optional[str] = None
    question_type: Optional[str] = None
    funnel_stage: Optional[str] = None
    classification_confidence: Optional[float] = None
    classified_at: Optional[datetime] = None
    classification_version: Optional[str] = None
    perceived_value_category: Optional[str] = None
    semantic_summary: Optional[str] = None
    
    # === MÉTRICAS GEO (Generative Engine Optimization) ===
    # Exclusivo para LLMs (ChatGPT, Gemini, Perplexity)
    brand_mention_count: Optional[int] = None
    brand_prominence_score: Optional[float] = None
    citation_quality_score: Optional[float] = None
    citation_rate_observed: Optional[float] = None
    citation_rate_corrected: Optional[float] = None
    share_of_voice_llm: Optional[float] = None
    engagement_score: Optional[float] = None
    
    # GEO Advanced (Phase 2+)
    zero_click_presence: Optional[float] = None
    authority_score: Optional[float] = None
    relevance_score: Optional[float] = None
    clarity_score: Optional[float] = None
    conversion_potential_score: Optional[float] = None


class RunListItem(BaseModel):
    id: str
    engine: str
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    zcrs: Optional[float]
    amr_flag: Optional[bool]
    dcr_flag: Optional[bool]
    template_name: Optional[str] = None
    template_category: Optional[str] = None
    subproject_name: Optional[str] = None
    # síntese de custos
    cost_usd: Optional[float] = None
    tokens_total: Optional[int] = None
    cycles_total: Optional[int] = None
    cycle_delay_seconds: Optional[int] = None
    # monitor/schedule
    monitor_id: Optional[str] = None
    monitor_name: Optional[str] = None
    schedule_date: Optional[datetime] = None
    schedule_slot: Optional[str] = None
    schedule_index_today: Optional[int] = None
    schedule_total_today: Optional[int] = None
    schedule_source: Optional[str] = None
    # Classificação Zero-Click
    response_type: Optional[str] = None
    sufficiency_level: Optional[str] = None
    actionability_type: Optional[str] = None
    trust_source: Optional[str] = None
    brand_positioning: Optional[str] = None
    question_type: Optional[str] = None
    funnel_stage: Optional[str] = None
    classification_confidence: Optional[float] = None
    # Métricas Avançadas Zero-Click
    user_intent: Optional[str] = None
    satisfaction_score: Optional[float] = None
    competitive_mentions: Optional[int] = None
    financial_value_score: Optional[float] = None
    content_gap_detected: Optional[bool] = None
    conversion_potential: Optional[str] = None
    perceived_value_category: Optional[str] = None
    semantic_summary: Optional[str] = None
    
    # === MÉTRICAS GEO (Generative Engine Optimization) ===
    # Exclusivo para LLMs (ChatGPT, Gemini, Perplexity)
    brand_mention_count: Optional[int] = None
    brand_prominence_score: Optional[float] = None
    citation_quality_score: Optional[float] = None
    citation_rate_observed: Optional[float] = None
    citation_rate_corrected: Optional[float] = None
    share_of_voice_llm: Optional[float] = None
    engagement_score: Optional[float] = None
    
    # GEO Advanced (Phase 2+)
    zero_click_presence: Optional[float] = None
    authority_score: Optional[float] = None
    relevance_score: Optional[float] = None
    clarity_score: Optional[float] = None
    conversion_potential_score: Optional[float] = None


class RunDetailOut(BaseModel):
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "protected_namespaces": (),
    }
    
    id: str
    project_id: str
    prompt_version_id: str
    engine: EngineCreate
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    subproject_id: Optional[str] = None
    project_name: Optional[str] = None
    subproject_name: Optional[str] = None
    prompt_name: Optional[str] = None
    prompt_category: Optional[str] = None
    prompt_template_category: Optional[str] = None
    prompt_template_name: Optional[str] = None
    prompt_id: Optional[str] = None
    # prompt
    prompt_text: Optional[str] = None
    # response
    response_text: Optional[str] = None
    # observabilidade
    model_name: Optional[str] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    tokens_total: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[int] = None
    cycles_total: Optional[int] = None
    cycle_delay_seconds: Optional[int] = None
    # monitor/schedule
    monitor_id: Optional[str] = None
    schedule_date: Optional[datetime] = None
    schedule_slot: Optional[str] = None
    schedule_index_today: Optional[int] = None
    schedule_total_today: Optional[int] = None
    schedule_source: Optional[str] = None
    # Classificação Zero-Click
    response_type: Optional[str] = None
    sufficiency_level: Optional[str] = None
    actionability_type: Optional[str] = None
    trust_source: Optional[str] = None
    brand_positioning: Optional[str] = None
    question_type: Optional[str] = None
    funnel_stage: Optional[str] = None
    classification_confidence: Optional[float] = None
    classified_at: Optional[datetime] = None
    classification_version: Optional[str] = None
    # Métricas Avançadas Zero-Click
    user_intent: Optional[str] = None
    satisfaction_score: Optional[float] = None
    competitive_mentions: Optional[int] = None
    financial_value_score: Optional[float] = None
    content_gap_detected: Optional[bool] = None
    conversion_potential: Optional[str] = None
    
    # === MÉTRICAS IM-SEO / IM-SEOIA ===
    # Índices Compostos
    im_seo_score: Optional[float] = None
    im_seoia_score: Optional[float] = None
    
    # Performance (Core Web Vitals)
    lcp_score: Optional[float] = None
    fid_score: Optional[float] = None
    cls_score: Optional[float] = None
    core_web_vitals_score: Optional[float] = None
    
    # Tráfego
    share_of_voice_serp: Optional[float] = None
    serp_features_presence: Optional[float] = None
    
    # IA - Recursos de SERP
    ia_resources_detected: Optional[int] = None
    ia_serp_presence_score: Optional[float] = None
    
    # Long-tail
    long_tail_terms_top10: Optional[int] = None
    long_tail_terms_top20: Optional[int] = None
    long_tail_coverage_score: Optional[float] = None
    
    # E-E-A-T
    eeat_score: Optional[float] = None
    eeat_expertise: Optional[float] = None
    eeat_experience: Optional[float] = None
    eeat_authoritativeness: Optional[float] = None
    eeat_trustworthiness: Optional[float] = None
    
    # Entidades
    entities_detected: Optional[int] = None
    entities_relevance_score: Optional[float] = None
    entity_connection_score: Optional[float] = None
    
    # Schema
    schema_types_detected: Optional[str] = None
    schema_coverage_score: Optional[float] = None
    
    # IA-Ready Blocks
    ia_ready_score: Optional[float] = None
    ia_ready_blocks_count: Optional[int] = None
    has_lists: Optional[bool] = None
    has_faqs: Optional[bool] = None
    has_tables: Optional[bool] = None
    has_step_by_step: Optional[bool] = None
    
    # IRZC
    irzc_score: Optional[float] = None
    ctr_expected: Optional[float] = None
    ctr_real: Optional[float] = None
    ctr_ratio: Optional[float] = None
    
    # Posição Orgânica (do SerpAPI)
    organic_position: Optional[int] = None
    competitors_top10: Optional[int] = None
    
    # === MÉTRICAS GEO (Generative Engine Optimization) ===
    # IMPORTANTE: Exclusivo para LLMs (ChatGPT, Gemini, Perplexity)
    # NÃO deve ser populado para SERP tradicional
    
    # Brand Presence
    brand_mention_count: Optional[int] = None
    brand_first_mention_position: Optional[int] = None
    brand_mention_density: Optional[float] = None
    brand_prominence_score: Optional[float] = None
    
    # Citation Quality & Rate
    citation_quality_score: Optional[float] = None
    first_citation_position: Optional[int] = None
    citation_rate_observed: Optional[float] = None
    citation_rate_corrected: Optional[float] = None
    
    # Competitive Intelligence
    competitor_mention_ratio: Optional[float] = None
    share_of_voice_llm: Optional[float] = None
    cocitation_competitors: Optional[str] = None  # JSON array
    
    # Engagement
    conversational_trigger_count: Optional[int] = None
    engagement_score: Optional[float] = None
    
    # GEO Advanced (Phase 2+)
    zero_click_presence: Optional[float] = None
    authority_score: Optional[float] = None
    relevance_score: Optional[float] = None
    clarity_score: Optional[float] = None
    product_category: Optional[str] = None
    conversion_potential_score: Optional[float] = None


class RunSemanticInsightOut(BaseModel):
    run_id: str
    perceived_value_category: Optional[str] = None
    semantic_summary: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    updated_at: Optional[datetime] = None


class CitationOut(BaseModel):
    domain: str
    url: Optional[str]
    anchor: Optional[str]
    position: Optional[str]
    type: Optional[str]
    is_ours: bool


class RunReport(BaseModel):
    id: str
    amr: float
    dcr: float
    zcrs: float
    citations: List[CitationOut]
    reasons: List[dict]


class EvidenceOut(BaseModel):
    id: str
    run_id: str
    parsed_json: Any


class OverviewAnalytics(BaseModel):
    total_runs: int
    amr_avg: float
    dcr_avg: float
    zcrs_avg: float


# Grouped comparison schemas
class GroupedRunWithEvidences(BaseModel):
    id: str
    engine: str
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    prompt_text: Optional[str] = None
    evidences: List[EvidenceOut]


class RunsBySubprojectGroup(BaseModel):
    subproject_id: Optional[str]
    subproject_name: str
    runs: List[GroupedRunWithEvidences]


# === GEO Dashboard Schemas ===

class GeoKPI(BaseModel):
    """KPI metric for hero cards."""
    label: str
    value: Any
    total: Optional[int] = None
    unit: Optional[str] = None
    delta: Optional[float] = None
    trend: Optional[str] = None  # "up"|"down"|"stable"


class GeoRadarDimension(BaseModel):
    """Single dimension in radar chart."""
    name: str
    value: float


class GeoRadarSeries(BaseModel):
    """Radar chart series for a single bank/entity."""
    bank: str
    dimensions: List[GeoRadarDimension]


class GeoBrandRanking(BaseModel):
    """Brand ranking entry."""
    rank: int
    brand: str
    mentions: int
    sample_url: Optional[str] = None


class GeoPerceptionBreakdown(BaseModel):
    """Perception breakdown per dimension."""
    dimension: str
    bank_a: Optional[float] = None
    bank_b: Optional[float] = None


class GeoPositioning(BaseModel):
    """Positioning section data."""
    brand_ranking: List[GeoBrandRanking]
    perception_breakdown: List[GeoPerceptionBreakdown]


class GeoWordCloudItem(BaseModel):
    """Word cloud item."""
    text: str
    frequency: int
    weight: float


class GeoEntityItem(BaseModel):
    """Entity table item."""
    entity: str
    type: str
    mentions: int
    runs: int


class GeoKeywordsEntities(BaseModel):
    """Keywords and entities section."""
    word_cloud: List[GeoWordCloudItem]
    entities: List[GeoEntityItem]


class GeoPanoramaCard(BaseModel):
    """Panorama summary card."""
    label: str
    value: Any
    delta: Optional[float] = None
    supporting: Optional[str] = None


class GeoPanoramaChart(BaseModel):
    """Panorama comparison chart data."""
    bank: str
    ai_overview_count: int
    paa_count: int
    kp_count: int


class GeoPanorama(BaseModel):
    """Panorama section data."""
    cards: List[GeoPanoramaCard]
    chart: List[GeoPanoramaChart]


class GeoWebStructureItem(BaseModel):
    """Web structure checklist item."""
    domain: Optional[str] = None
    primary_url: Optional[str] = None
    url: Optional[str] = None  # Deprecated, use primary_url
    title: bool
    meta_description: bool
    keywords: bool
    robots: bool
    open_graph: bool
    ai_ready_blocks: bool
    details: Optional[Dict[str, Any]] = None
    matches_filter: Optional[bool] = None


# === SCHEMAS GEO (Generative Engine Optimization) ===

class DomainVariantCreate(BaseModel):
    """Criar variante de domínio."""
    variant_domain: str
    canonical_domain: str
    display_name: Optional[str] = None


class DomainVariantOut(BaseModel):
    """Retorno de variante de domínio."""
    id: str
    project_id: str
    variant_domain: str
    canonical_domain: str
    display_name: Optional[str] = None
    created_at: datetime


class ContentGapCreate(BaseModel):
    """Criar lacuna de conteúdo."""
    url: Optional[str] = None
    topic: Optional[str] = None
    gap_type: str  # missing_faq|outdated_content|no_comparison|missing_table|no_tldr
    description: str
    suggestion: Optional[str] = None
    priority: str = "medium"  # low|medium|high|critical
    assignee: Optional[str] = None


class ContentGapUpdate(BaseModel):
    """Atualizar lacuna de conteúdo."""
    status: Optional[str] = None  # open|in_progress|completed|dismissed
    priority: Optional[str] = None
    assignee: Optional[str] = None
    suggestion: Optional[str] = None


class ContentGapOut(BaseModel):
    """Retorno de lacuna de conteúdo."""
    id: str
    project_id: str
    url: Optional[str] = None
    topic: Optional[str] = None
    gap_type: str
    description: str
    suggestion: Optional[str] = None
    priority: str
    status: str
    estimated_impact: Optional[float] = None
    assignee: Optional[str] = None
    detected_at: datetime
    resolved_at: Optional[datetime] = None


class GeoCitationRateStats(BaseModel):
    """Estatísticas de Citation Rate agregadas."""
    period_start: datetime
    period_end: datetime
    total_runs: int
    llm_runs: int  # Apenas LLMs
    cr_observed_avg: float
    cr_corrected_avg: float
    cr_trend: str  # "up"|"down"|"stable"
    by_engine: Dict[str, Dict[str, float]]  # {"chatgpt": {"cr_obs": 45.2, "cr_corr": 52.1}}
    by_funnel: Optional[Dict[str, float]] = None
    by_product: Optional[Dict[str, float]] = None


class GeoCoCitationAnalysis(BaseModel):
    """Análise de co-citação com concorrentes."""
    competitor_domain: str
    competitor_name: str
    cocitation_count: int
    cocitation_percentage: float
    contexts: List[str]  # ["comparacao", "reputacao", "produto"]
    avg_prominence_when_together: Optional[float] = None


class GeoAlert(BaseModel):
    """Alert item (Crítico/Atenção/Oportunidade)."""
    severity: str  # "critico"|"atencao"|"oportunidade"
    title: str
    description: str
    supporting_runs: List[str]


class GeoSWOT(BaseModel):
    """SWOT analysis."""
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]


class GeoRawSample(BaseModel):
    """Raw analysis sample."""
    run_id: str
    started_at: Optional[str]
    engine: str
    status: str
    im_seo_score: Optional[float]
    eeat_score: Optional[float]
    citations_count: Optional[int]
    response_snippet: Optional[str]


class GeoDashboardFilters(BaseModel):
    """Filters applied to dashboard."""
    prompt_id: Optional[str] = None
    prompt_version_id: Optional[str] = None
    subproject_id: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    bank_ids: Optional[List[str]] = None


class GeoDashboardOut(BaseModel):
    """Complete GEO dashboard response."""
    project_id: Optional[str]
    filters_applied: GeoDashboardFilters
    total_runs: int
    kpis: List[GeoKPI]
    radar: List[GeoRadarSeries]
    positioning: GeoPositioning
    keywords_entities: GeoKeywordsEntities
    panorama: GeoPanorama
    web_structure: List[GeoWebStructureItem]
    alerts: List[GeoAlert]
    swot: GeoSWOT
    raw_samples: List[GeoRawSample]
