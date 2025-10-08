from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Float,
    JSON,
    UniqueConstraint,
    Index,
    Integer,
    VARCHAR,
    Text,
)
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.mssql import VARCHAR as MSSQL_VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


class FixedVarchar(TypeDecorator):
    """Custom type that forces fixed-length VARCHAR for SQL Server compatibility."""
    impl = VARCHAR
    cache_ok = True
    
    def __init__(self, length):
        self.length = length
        super().__init__(length)
    
    def load_dialect_impl(self, dialect):
        if dialect.name == 'mssql':
            return dialect.type_descriptor(MSSQL_VARCHAR(self.length))
        return dialect.type_descriptor(VARCHAR(self.length))


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("prj"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Google Search Console Integration
    search_console_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    search_console_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    search_console_site_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    domains: Mapped[list[Domain]] = relationship(back_populates="project", cascade="all, delete-orphan")
    prompts: Mapped[list[Prompt]] = relationship(back_populates="project", cascade="all, delete-orphan")
    engines: Mapped[list[Engine]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("dom"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    domain: Mapped[str] = mapped_column(FixedVarchar(255), nullable=False)
    pattern_regex: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    project: Mapped[Project] = relationship(back_populates="domains")

    __table_args__ = (
        UniqueConstraint("project_id", "domain", name="uq_project_domain"),
    )


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("pmt"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    intent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    persona: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    variables_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    project: Mapped[Project] = relationship(back_populates="prompts")
    versions: Mapped[list[PromptVersion]] = relationship(back_populates="prompt", cascade="all, delete-orphan")


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("pv"))
    prompt_id: Mapped[str] = mapped_column(ForeignKey("prompts.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    prompt: Mapped[Prompt] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("prompt_id", "version", name="uq_prompt_version"),
    )


class Engine(Base):
    __tablename__ = "engines"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("eng"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    project: Mapped[Project] = relationship(back_populates="engines")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("run"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    prompt_version_id: Mapped[str] = mapped_column(ForeignKey("prompt_versions.id"))
    engine_id: Mapped[str] = mapped_column(ForeignKey("engines.id"))
    subproject_id: Mapped[Optional[str]] = mapped_column(ForeignKey("subprojects.id"), nullable=True)
    monitor_id: Mapped[Optional[str]] = mapped_column(ForeignKey("monitors.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="queued")
    cycles_total: Mapped[int] = mapped_column(Integer, default=1)
    cycle_delay_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    zcrs: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    amr_flag: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    dcr_flag: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Métricas e observabilidade
    tokens_input: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    citations_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    our_citations_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unique_domains_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    config_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Agendamento/Monitor metadata
    schedule_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    schedule_slot: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # "HH:MM"
    schedule_index_today: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    schedule_total_today: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    schedule_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # monitor|monitor_now|manual

    # Classificação Zero-Click da Resposta
    response_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # direta|explicativa|instrucional|comparativa|consultiva|navegacional
    sufficiency_level: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # total|parcial|insuficiente
    actionability_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # transacional|informativa
    trust_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # citada|generica
    brand_positioning: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # protagonista|competidor|ausente
    question_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # marca|produto|informacao|comparacao
    funnel_stage: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # reconhecimento|consideracao|conversao
    classification_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0-1.0
    classified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    classification_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # versão do sistema de classificação
    perceived_value_category: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # inovacao|tradicao|custo|atendimento

    # Métricas Avançadas Zero-Click
    user_intent: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # informational|transactional|navigational|commercial
    satisfaction_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0-1.0 score combinado
    competitive_mentions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # número de concorrentes mencionados
    financial_value_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # valor estimado da consulta
    content_gap_detected: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)  # gap de conteúdo identificado
    conversion_potential: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # alto|medio|baixo

    # === MÉTRICAS IM-SEO ===
    # Performance (Core Web Vitals)
    lcp_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Largest Contentful Paint (seconds)
    fid_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # First Input Delay (ms)
    cls_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Cumulative Layout Shift
    core_web_vitals_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100

    # Tráfego
    share_of_voice_serp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # % SoV em SERP
    serp_features_presence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # % termos com features

    # IA - Recursos de SERP
    ia_resources_detected: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ia_serp_presence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100

    # IA - Long Tail
    long_tail_terms_top10: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    long_tail_terms_top20: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    long_tail_coverage_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100

    # IA - E-E-A-T
    eeat_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    eeat_expertise: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eeat_experience: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eeat_authoritativeness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eeat_trustworthiness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # IA - Conexão com Entidades
    entities_detected: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    entities_relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-1
    entity_connection_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100

    # IA - Dados Estruturados
    schema_types_detected: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array: ["Article", "FAQ"]
    schema_coverage_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    schema_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # IA - Blocos IA-Ready
    ia_ready_blocks_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ia_ready_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    has_lists: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    has_faqs: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    has_tables: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    has_step_by_step: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)

    # IA - IRZC (Índice de Risco de Zero Click)
    irzc_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    ctr_expected: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # CTR benchmark
    ctr_real: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # CTR real (se disponível)
    ctr_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # real/expected

    # === ÍNDICES COMPOSTOS ===
    im_seo_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    im_seoia_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100

    # Texto completo da resposta (para análise)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    semantic_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    citations: Mapped[list["Citation"]] = relationship("Citation", back_populates="run")
    entities: Mapped[list["Entity"]] = relationship("Entity", back_populates="run")
    serp_features: Mapped[list["SerpFeature"]] = relationship("SerpFeature", back_populates="run")
    semantic_insights: Mapped[Optional["RunSemanticInsight"]] = relationship(
        "RunSemanticInsight", back_populates="run", cascade="all, delete-orphan", uselist=False
    )


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("evd"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    raw_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    parsed_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    screenshot_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("ctt"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    domain: Mapped[str] = mapped_column(FixedVarchar(255))
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    anchor: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # top|middle|bottom
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # link|mention|logo
    is_ours: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_citations_run_id_domain", "run_id", "domain"),
    )

    run: Mapped[Run] = relationship("Run", back_populates="citations")


class Reason(Base):
    __tablename__ = "reasons"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("rsn"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String)
    label: Mapped[str] = mapped_column(String)
    confidence: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # low|medium|high


class CompetitorScore(Base):
    __tablename__ = "competitor_scores"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("cmp"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    domain: Mapped[str] = mapped_column(FixedVarchar(255))
    sov: Mapped[float] = mapped_column(Float)
    period_start: Mapped[datetime] = mapped_column(DateTime)
    period_end: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_comp_scores_project_domain", "project_id", "domain"),
    )


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("ins"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="NO ACTION"))
    run_id: Mapped[Optional[str]] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    impact: Mapped[Optional[int]] = mapped_column(nullable=True)
    effort: Mapped[Optional[int]] = mapped_column(nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    assignee: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("evt"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    version: Mapped[str] = mapped_column(VARCHAR(50))  # queued|fetch|parse|extract|persist|completed|error
    status: Mapped[str] = mapped_column(String)  # started|ok|fail
    message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_run_events_run_id_created", "run_id", "created_at"),
    )


class SubProject(Base):
    __tablename__ = "subprojects"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("spj"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(FixedVarchar(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_subproject_name"),
    )


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("ptm"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    subproject_id: Mapped[Optional[str]] = mapped_column(ForeignKey("subprojects.id"), nullable=True)
    category: Mapped[str] = mapped_column(FixedVarchar(100), nullable=False)  # ex.: Abertura de conta PF
    name: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    intent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    persona: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_prompt_templates_project_category", "project_id", "category"),
    )


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("mon"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    subproject_id: Mapped[Optional[str]] = mapped_column(ForeignKey("subprojects.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    schedule_cron: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    engines_json: Mapped[dict] = mapped_column(JSON)  # { engines: [ { name, region, device, config_json } ] }
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MonitorTemplate(Base):
    __tablename__ = "monitor_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    monitor_id: Mapped[str] = mapped_column(ForeignKey("monitors.id", ondelete="CASCADE"))
    template_id: Mapped[str] = mapped_column(ForeignKey("prompt_templates.id", ondelete="NO ACTION"))

    __table_args__ = (
        UniqueConstraint("monitor_id", "template_id", name="uq_monitor_template"),
    )


class MonitorHistory(Base):
    __tablename__ = "monitor_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    monitor_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="NO ACTION"))
    subproject_id: Mapped[str | None] = mapped_column(ForeignKey("subprojects.id", ondelete="NO ACTION"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    runs_total: Mapped[int] = mapped_column(Integer, default=0)
    runs_completed: Mapped[int] = mapped_column(Integer, default=0)
    runs_failed: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("monitor_id", name="uq_monitor_history_monitor_id"),
        Index("ix_monitor_history_project", "project_id"),
    )


class MonitorHistoryRun(Base):
    __tablename__ = "monitor_history_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    history_monitor_id: Mapped[str] = mapped_column(
        VARCHAR(50), ForeignKey("monitor_history.monitor_id", ondelete="CASCADE")
    )
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))

    __table_args__ = (
        Index("ix_monitor_history_runs_hist", "history_monitor_id"),
        Index("ix_monitor_history_runs_run", "run_id"),
        UniqueConstraint("history_monitor_id", "run_id", name="uq_monitor_history_run"),
    )


class SerpFeature(Base):
    """Modelo para SERP Features detectadas em uma run."""
    __tablename__ = "serp_features"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("sf"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))

    # Tipos de features detectadas
    has_featured_snippet: Mapped[bool] = mapped_column(Boolean, default=False)
    has_paa: Mapped[bool] = mapped_column(Boolean, default=False)  # People Also Ask
    has_knowledge_panel: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ai_overview: Mapped[bool] = mapped_column(Boolean, default=False)
    has_local_pack: Mapped[bool] = mapped_column(Boolean, default=False)
    has_video_carousel: Mapped[bool] = mapped_column(Boolean, default=False)
    has_image_pack: Mapped[bool] = mapped_column(Boolean, default=False)

    # Dados estruturados
    featured_snippet_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    paa_questions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array de strings
    paa_items: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array de objetos com posição/snippet
    knowledge_panel_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_overview_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Posições
    organic_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    competitors_in_top10: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_serp_features_run_id", "run_id"),
    )

    run: Mapped[Run] = relationship("Run", back_populates="serp_features")


class Entity(Base):
    """Modelo para Entidades detectadas no conteúdo de uma run."""
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("ent"))
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))

    name: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String)  # PERSON, ORGANIZATION, LOCATION, etc.
    salience_score: Mapped[float] = mapped_column(Float)  # 0-1 do Google NLP

    # Contexto
    mentions_count: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_entities_run_id", "run_id"),
    )

    run: Mapped[Run] = relationship("Run", back_populates="entities")


class RunSemanticInsight(Base):
    """Resultados estruturados de insights semânticos gerados pelo Gemini."""

    __tablename__ = "run_semantic_insights"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    run: Mapped[Run] = relationship("Run", back_populates="semantic_insights")


class UrlMetadata(Base):
    """Cached metadata from crawled URLs."""

    __tablename__ = "url_metadata"

    id: Mapped[str] = mapped_column(VARCHAR(50), primary_key=True, default=lambda: gen_id("umd"))
    url: Mapped[str] = mapped_column(String, unique=True, index=True)
    domain: Mapped[str] = mapped_column(FixedVarchar(255), index=True)
    
    # HTML metadata
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    meta_keywords: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    meta_robots: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Open Graph tags (stored as JSON)
    og_tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Special files for LLMs/AI
    llms_txt: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_txt: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    robots_txt_full: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # AI Ready detection
    has_structured_data: Mapped[bool] = mapped_column(Boolean, default=False)
    has_faq_schema: Mapped[bool] = mapped_column(Boolean, default=False)
    has_lists: Mapped[bool] = mapped_column(Boolean, default=False)
    has_tables: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Crawl status
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|success|error
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    http_status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_url_metadata_domain_status", "domain", "status"),
    )
