from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BeforeValidator
from typing import Annotated, Literal
import os
import json
import re


def parse_comma_separated_string(v):
    if isinstance(v, str):
        value = v.strip()
        if not value:
            return []
        if value[0] in {'"', "'"} and value[-1] == value[0]:
            value = value[1:-1].strip()
        if value.startswith('[') and value.endswith(']'):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except json.JSONDecodeError:
                pass
        parts = re.split(r"[\s,;]+", value)
        return [item.strip() for item in parts if item.strip()]
    return v


CommaSeparatedList = Annotated[list[str], BeforeValidator(parse_comma_separated_string)]


class Settings(BaseSettings):
    # Environment
    environment: Literal["development", "production", "staging"] = "development"
    debug: bool = True

    # Application
    app_name: str = "Zero-Click SEO & AI Citation Monitor"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"

    # Security
    secret_key: str = "devsecret"
    allowed_origins: CommaSeparatedList = ["*"]  # Override in production
    allowed_hosts: CommaSeparatedList = ["*"]

    # Database
    database_url: str = "sqlite:///./app.db"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 3600
    db_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # Celery
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    celery_task_time_limit: int = 1200
    celery_task_soft_time_limit: int = 900
    celery_worker_prefetch_multiplier: int = 4
    celery_worker_max_tasks_per_child: int = 1000

    # API Keys
    openai_api_key: str | None = None
    google_api_key: str | None = None
    gemini_api_key: str | None = None
    perplexity_api_key: str | None = None
    serpapi_key: str | None = None
    pagespeed_api_key: str | None = None

    # Azure Blob Storage
    azure_blob_connection_string: str | None = None
    azure_blob_container_semantic: str = "semantic-insights"
    azure_blob_container_evidence: str = "evidence-payloads"

    # Features
    semantic_insights_enabled: bool = True

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text

    # Performance
    enable_gzip: bool = True
    gzip_min_size: int = 1000

    # Rate Limiting (requests per minute)
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 10

    # Monitoring
    enable_metrics: bool = False
    sentry_dsn: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    def get_celery_broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    def get_celery_result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url


settings = Settings()

# Auto-configure based on environment
if settings.is_production:
    settings.debug = False
    settings.db_echo = False
    settings.log_level = os.getenv("LOG_LEVEL", "INFO")
    # In production, parse ALLOWED_ORIGINS from env
    origins_str = os.getenv("ALLOWED_ORIGINS", "")
    if origins_str:
        settings.allowed_origins = [o.strip() for o in origins_str.split(",") if o.strip()]
