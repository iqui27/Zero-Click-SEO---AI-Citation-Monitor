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
    monitor_id: Mapped[Optional[str]] = mapped_column(ForeignKey("monitors.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="queued")
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
