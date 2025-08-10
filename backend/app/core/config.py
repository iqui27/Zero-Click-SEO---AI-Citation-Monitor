from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://seo:seo@localhost:5432/seo_analyzer"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "devsecret"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
