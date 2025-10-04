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
    perceived_value_category: Optional[str] = None
    semantic_summary: Optional[str] = None


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


class RunDetailOut(BaseModel):
    model_config = {"from_attributes": True}
    
    id: str
    project_id: str
    prompt_version_id: str
    engine: EngineCreate
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    subproject_id: Optional[str] = None
    # prompt
    prompt_text: Optional[str] = None
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
