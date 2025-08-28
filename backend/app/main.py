from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import asyncio
import threading

from app.core.config import settings
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.api.routes import api_router
from app.services.scheduler import start_scheduler

app = FastAPI(title="Zero-Click SEO & AI Citation Monitor", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    # Cria tabelas e tenta aplicar colunas novas em bancos existentes (sem Alembic)
    Base.metadata.create_all(bind=engine)
    # Migração leve (apenas Postgres): adicionar colunas de métricas, se não existirem
    try:
        if engine.dialect.name == "postgresql":
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
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS cycle_delay_seconds INTEGER",
                    # insights.run_id para relacionar insight com run
                    "ALTER TABLE insights ADD COLUMN IF NOT EXISTS run_id VARCHAR(255)",
                    "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name='insights' AND column_name='run_id') THEN BEGIN EXCEPTION WHEN others THEN END; END IF; END $$;",
                ]
                for sql in stmts:
                    conn.execute(text(sql))
        elif engine.dialect.name == "mssql":
            # Migração leve (Azure SQL): adicionar colunas ausentes da tabela runs
            print("[MIGRATION] Starting SQL Server migration...")
            def _exec_safe(sql: str, description: str = "") -> None:
                try:
                    print(f"[MIGRATION] Executing: {description}")
                    with engine.begin() as _conn:
                        _conn.execute(text(sql))
                    print(f"[MIGRATION] Success: {description}")
                except Exception as e:
                    print(f"[MIGRATION] Failed: {description} - {e}")

            # Adicionar cycles_total primeiro
            _exec_safe("""
                IF NOT EXISTS (
                    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'runs' AND COLUMN_NAME = 'cycles_total'
                )
                BEGIN
                    ALTER TABLE dbo.runs ADD cycles_total INT NULL;
                END
            """, "Add runs.cycles_total column")
            
            # Backfill cycles_total em transação separada
            _exec_safe("""
                UPDATE dbo.runs SET cycles_total = 1 WHERE cycles_total IS NULL;
            """, "Backfill runs.cycles_total with default value")

            # Lista de outras colunas que devem existir na tabela runs
            runs_columns = [
                ("tokens_input", "INT"),
                ("tokens_output", "INT"),
                ("tokens_total", "INT"),
                ("cost_usd", "FLOAT"),
                ("latency_ms", "INT"),
                ("citations_count", "INT"),
                ("our_citations_count", "INT"),
                ("unique_domains_count", "INT"),
                ("model_name", "VARCHAR(255)"),
                ("error_code", "VARCHAR(255)"),
                ("config_hash", "VARCHAR(255)"),
                ("cycle_delay_seconds", "INT"),
            ]

            # Adicionar cada coluna se não existir
            for col_name, col_type in runs_columns:
                _exec_safe(f"""
                    IF NOT EXISTS (
                        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'runs' AND COLUMN_NAME = '{col_name}'
                    )
                    BEGIN
                        ALTER TABLE dbo.runs ADD {col_name} {col_type} NULL;
                    END
                """, f"Add runs.{col_name} column")

            # Adicionar prompt_templates.subproject_id, se não existir
            _exec_safe("""
                IF NOT EXISTS (
                    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'prompt_templates' AND COLUMN_NAME = 'subproject_id'
                )
                BEGIN
                    ALTER TABLE dbo.prompt_templates ADD subproject_id VARCHAR(50) NULL;
                END
            """, "Add prompt_templates.subproject_id column")

            # Adicionar FK, se não existir
            _exec_safe("""
                IF NOT EXISTS (
                    SELECT 1 FROM sys.foreign_keys WHERE name = N'fk_prompt_templates_subproject'
                )
                BEGIN
                    ALTER TABLE dbo.prompt_templates 
                    ADD CONSTRAINT fk_prompt_templates_subproject FOREIGN KEY (subproject_id) REFERENCES dbo.subprojects(id);
                END
            """, "Add FK constraint for prompt_templates.subproject_id")

            # Adicionar insights.run_id, se não existir
            _exec_safe("""
                IF NOT EXISTS (
                    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'insights' AND COLUMN_NAME = 'run_id'
                )
                BEGIN
                    ALTER TABLE dbo.insights ADD run_id VARCHAR(50) NULL;
                END
            """, "Add insights.run_id column")
            
            print("[MIGRATION] SQL Server migration completed.")
    except Exception:
        # tolerar ambiente que não suporte IF NOT EXISTS
        pass
    
    # Start the monitor scheduler in a background thread
    def run_scheduler():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_scheduler())
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("[SCHEDULER] Monitor scheduler started in background thread")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")
