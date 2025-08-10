from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.api.routes import api_router

app = FastAPI(title="Zero-Click SEO & AI Citation Monitor", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    # Cria tabelas e tenta aplicar colunas novas em bancos existentes (sem Alembic)
    Base.metadata.create_all(bind=engine)
    # Migração leve: adicionar colunas de métricas na tabela runs, se não existirem (Postgres)
    try:
        with engine.begin() as conn:  # transaction
            stmts = [
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS tokens_input INTEGER",
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS tokens_output INTEGER",
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS tokens_total INTEGER",
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS cost_usd DOUBLE PRECISION",
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS latency_ms INTEGER",
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS citations_count INTEGER",
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS our_citations_count INTEGER",
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS unique_domains_count INTEGER",
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS model_name VARCHAR(255)",
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS error_code VARCHAR(255)",
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS config_hash VARCHAR(255)",
                # insights.run_id para relacionar insight com run
                "ALTER TABLE insights ADD COLUMN IF NOT EXISTS run_id VARCHAR(255)",
                "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name='insights' AND column_name='run_id') THEN BEGIN EXCEPTION WHEN others THEN END; END IF; END $$;",
            ]
            for sql in stmts:
                conn.execute(text(sql))
    except Exception:
        # tolerar ambiente que não suporte IF NOT EXISTS
        pass


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")
