from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Default to SQLite for local/dev. In Docker Compose, DATABASE_URL is provided.
    database_url: str = "sqlite:///./app.db"
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
