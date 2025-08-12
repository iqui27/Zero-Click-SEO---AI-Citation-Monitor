from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://seo:seo@localhost:5432/seo_analyzer"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "devsecret"
    # Chaves opcionais (aceitas para evitar erro de extras no .env)
    openai_api_key: str | None = None
    google_api_key: str | None = None
    gemini_api_key: str | None = None
    perplexity_api_key: str | None = None
    serpapi_key: str | None = None

    # Permitir variáveis extras do .env (ex.: SERPAPI_KEY, OPENAI_API_KEY)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )


settings = Settings()
