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
from app.api.search_console_routes import router as search_console_router
from app.api.analytics_routes import router as analytics_router
from app.api.export_routes import router as export_router
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
    # Migração leve: adicionar colunas de métricas, se não existirem
    try:
        if engine.dialect.name == "sqlite":
            # SQLite migrations - adicionar colunas IM-SEO/IM-SEOIA
            print("[MIGRATION] Starting SQLite migration for IM metrics...")
            with engine.begin() as conn:
                # Helper para adicionar coluna se não existir
                def add_column_if_not_exists(table: str, column: str, col_type: str):
                    try:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                        print(f"[MIGRATION] Added {table}.{column}")
                    except Exception as e:
                        if "duplicate column name" not in str(e).lower():
                            print(f"[MIGRATION] Warning adding {table}.{column}: {e}")
                
                # Adicionar colunas IM-SEO/IM-SEOIA
                im_columns = [
                    ("lcp_score", "FLOAT"),
                    ("fid_score", "FLOAT"),
                    ("cls_score", "FLOAT"),
                    ("core_web_vitals_score", "FLOAT"),
                    ("share_of_voice_serp", "FLOAT"),
                    ("serp_features_presence", "FLOAT"),
                    ("ia_resources_detected", "INTEGER"),
                    ("ia_serp_presence_score", "FLOAT"),
                    ("long_tail_terms_top10", "INTEGER"),
                    ("long_tail_terms_top20", "INTEGER"),
                    ("long_tail_coverage_score", "FLOAT"),
                    ("eeat_score", "FLOAT"),
                    ("eeat_expertise", "FLOAT"),
                    ("eeat_experience", "FLOAT"),
                    ("eeat_authoritativeness", "FLOAT"),
                    ("eeat_trustworthiness", "FLOAT"),
                    ("entities_detected", "INTEGER"),
                    ("entities_relevance_score", "FLOAT"),
                    ("entity_connection_score", "FLOAT"),
                    ("schema_types_detected", "TEXT"),
                    ("schema_coverage_score", "FLOAT"),
                    ("schema_valid", "BOOLEAN"),
                    ("ia_ready_blocks_count", "INTEGER"),
                    ("ia_ready_score", "FLOAT"),
                    ("has_lists", "BOOLEAN"),
                    ("has_faqs", "BOOLEAN"),
                    ("has_tables", "BOOLEAN"),
                    ("has_step_by_step", "BOOLEAN"),
                    ("irzc_score", "FLOAT"),
                    ("ctr_expected", "FLOAT"),
                    ("ctr_real", "FLOAT"),
                    ("ctr_ratio", "FLOAT"),
                    ("im_seo_score", "FLOAT"),
                    ("im_seoia_score", "FLOAT"),
                    ("response_text", "TEXT"),
                    ("perceived_value_category", "VARCHAR(50)"),
                    ("semantic_summary", "TEXT"),
                ]

                for col_name, col_type in im_columns:
                    add_column_if_not_exists("runs", col_name, col_type)

                serp_columns = [
                    ("paa_items", "TEXT"),
                    ("knowledge_panel_json", "TEXT"),
                    ("ai_overview_json", "TEXT"),
                ]

                for col_name, col_type in serp_columns:
                    add_column_if_not_exists("serp_features", col_name, col_type)
                
                # Adicionar colunas para arquivos especiais LLM/AI na tabela url_metadata
                url_metadata_columns = [
                    ("llms_txt", "TEXT"),
                    ("ai_txt", "TEXT"),
                    ("robots_txt_full", "TEXT"),
                ]
                for col_name, col_type in url_metadata_columns:
                    add_column_if_not_exists("url_metadata", col_name, col_type)

                print("[MIGRATION] SQLite migration completed for IM metrics.")
        
        elif engine.dialect.name == "postgresql":
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
                    # Classificação Zero-Click da Resposta
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS response_type VARCHAR(50)",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS sufficiency_level VARCHAR(50)",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS actionability_type VARCHAR(50)",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS trust_source VARCHAR(50)",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS brand_positioning VARCHAR(50)",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS question_type VARCHAR(50)",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS funnel_stage VARCHAR(50)",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS classification_confidence DOUBLE PRECISION",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS classified_at TIMESTAMP",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS classification_version VARCHAR(50)",
                    # Métricas Avançadas Zero-Click
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS user_intent VARCHAR(50)",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS satisfaction_score DOUBLE PRECISION",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS competitive_mentions INTEGER",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS financial_value_score DOUBLE PRECISION",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS content_gap_detected BOOLEAN",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS conversion_potential VARCHAR(50)",
                    # insights.run_id para relacionar insight com run
                    "ALTER TABLE insights ADD COLUMN IF NOT EXISTS run_id VARCHAR(255)",
                    "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage WHERE table_name='insights' AND column_name='run_id') THEN BEGIN EXCEPTION WHEN others THEN END; END IF; END $$;",
                    # citations.is_ours (booleano) para marcar se o domínio citado é nosso
                    "ALTER TABLE citations ADD COLUMN IF NOT EXISTS is_ours BOOLEAN",
                    "UPDATE citations SET is_ours = FALSE WHERE is_ours IS NULL",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS perceived_value_category VARCHAR(50)",
                    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS semantic_summary TEXT",
                    "ALTER TABLE serp_features ADD COLUMN IF NOT EXISTS paa_items TEXT",
                    "ALTER TABLE serp_features ADD COLUMN IF NOT EXISTS knowledge_panel_json TEXT",
                    "ALTER TABLE serp_features ADD COLUMN IF NOT EXISTS ai_overview_json TEXT",
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
                # Classificação Zero-Click da Resposta
                ("response_type", "VARCHAR(50)"),
                ("sufficiency_level", "VARCHAR(50)"),
                ("actionability_type", "VARCHAR(50)"),
                ("trust_source", "VARCHAR(50)"),
                ("brand_positioning", "VARCHAR(50)"),
                ("question_type", "VARCHAR(50)"),
                ("funnel_stage", "VARCHAR(50)"),
                ("classification_confidence", "FLOAT"),
                ("classified_at", "DATETIME"),
                ("classification_version", "VARCHAR(50)"),
                ("perceived_value_category", "VARCHAR(50)"),
                # Métricas Avançadas Zero-Click
                ("user_intent", "VARCHAR(50)"),
                ("satisfaction_score", "FLOAT"),
                ("competitive_mentions", "INT"),
                ("financial_value_score", "FLOAT"),
                ("content_gap_detected", "BIT"),
                ("conversion_potential", "VARCHAR(50)"),
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

            # Garantir FK runs.monitor_id -> monitors.id com ON DELETE SET NULL
            _exec_safe("""
                -- Drop FK existente (qualquer nome) entre runs.monitor_id e monitors.id
                DECLARE @fk NVARCHAR(128);
                SELECT TOP 1 @fk = fk.name
                FROM sys.foreign_keys fk
                JOIN sys.tables t ON fk.parent_object_id = t.object_id
                JOIN sys.tables rt ON fk.referenced_object_id = rt.object_id
                WHERE t.name = 'runs' AND rt.name = 'monitors';
                IF @fk IS NOT NULL
                BEGIN
                    DECLARE @sql NVARCHAR(MAX) = N'ALTER TABLE dbo.runs DROP CONSTRAINT ' + QUOTENAME(@fk) + ';';
                    EXEC sp_executesql @sql;
                END
            """, "Drop existing FK runs -> monitors if any")

            _exec_safe("""
                -- Garantir coluna nula e recriar FK com ON DELETE SET NULL
                IF EXISTS (
                    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'runs' AND COLUMN_NAME = 'monitor_id'
                )
                BEGIN
                    ALTER TABLE dbo.runs ALTER COLUMN monitor_id VARCHAR(50) NULL;
                END
                IF NOT EXISTS (
                    SELECT 1 FROM sys.foreign_keys WHERE name = N'fk_runs_monitor'
                )
                BEGIN
                    ALTER TABLE dbo.runs 
                    ADD CONSTRAINT fk_runs_monitor FOREIGN KEY (monitor_id)
                    REFERENCES dbo.monitors(id) ON DELETE SET NULL;
                END
            """, "Ensure FK runs.monitor_id ON DELETE SET NULL")

            # Adicionar colunas de metadados de agendamento em runs, se não existirem
            _exec_safe("""
                IF NOT EXISTS (
                    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'runs' AND COLUMN_NAME = 'schedule_date'
                ) BEGIN
                    ALTER TABLE dbo.runs ADD schedule_date DATETIME NULL;
                END
                IF NOT EXISTS (
                    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'runs' AND COLUMN_NAME = 'schedule_slot'
                ) BEGIN
                    ALTER TABLE dbo.runs ADD schedule_slot VARCHAR(20) NULL;
                END
                IF NOT EXISTS (
                    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'runs' AND COLUMN_NAME = 'schedule_index_today'
                ) BEGIN
                    ALTER TABLE dbo.runs ADD schedule_index_today INT NULL;
                END
                IF NOT EXISTS (
                    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'runs' AND COLUMN_NAME = 'schedule_total_today'
                ) BEGIN
                    ALTER TABLE dbo.runs ADD schedule_total_today INT NULL;
                END
                IF NOT EXISTS (
                    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'runs' AND COLUMN_NAME = 'schedule_source'
                ) BEGIN
                    ALTER TABLE dbo.runs ADD schedule_source VARCHAR(30) NULL;
                END
            """, "Add scheduling metadata columns to runs")
            
            # Adicionar citations.is_ours (booleano) se não existir e backfill para 0
            _exec_safe("""
                IF NOT EXISTS (
                    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'citations' AND COLUMN_NAME = 'is_ours'
                )
                BEGIN
                    ALTER TABLE dbo.citations ADD is_ours BIT NULL;
                    UPDATE dbo.citations SET is_ours = 0 WHERE is_ours IS NULL;
                END
            """, "Add citations.is_ours column and backfill false")

            # === MIGRATIONS IM-SEO / IM-SEOIA ===
            
            # Criar tabela serp_features
            _exec_safe("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='serp_features' and xtype='U')
                BEGIN
                    CREATE TABLE serp_features (
                        id VARCHAR(50) PRIMARY KEY,
                        run_id VARCHAR(50) NOT NULL,
                        has_featured_snippet BIT DEFAULT 0,
                        has_paa BIT DEFAULT 0,
                        has_knowledge_panel BIT DEFAULT 0,
                        has_ai_overview BIT DEFAULT 0,
                        has_local_pack BIT DEFAULT 0,
                        has_video_carousel BIT DEFAULT 0,
                        has_image_pack BIT DEFAULT 0,
                        featured_snippet_content NVARCHAR(MAX),
                        paa_questions NVARCHAR(MAX),
                        paa_items NVARCHAR(MAX),
                        knowledge_panel_json NVARCHAR(MAX),
                        ai_overview_json NVARCHAR(MAX),
                        organic_position INT,
                        competitors_in_top10 INT DEFAULT 0,
                        created_at DATETIME DEFAULT GETDATE(),
                        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
                    );
                    CREATE INDEX ix_serp_features_run_id ON serp_features(run_id);
                END
            """, "Create serp_features table")

            # Criar tabela entities
            _exec_safe("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='entities' and xtype='U')
                BEGIN
                    CREATE TABLE entities (
                        id VARCHAR(50) PRIMARY KEY,
                        run_id VARCHAR(50) NOT NULL,
                        name NVARCHAR(255) NOT NULL,
                        entity_type VARCHAR(50),
                        salience_score FLOAT,
                        mentions_count INT DEFAULT 1,
                        created_at DATETIME DEFAULT GETDATE(),
                        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
                    );
                    CREATE INDEX ix_entities_run_id ON entities(run_id);
                END
            """, "Create entities table")

            _exec_safe("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='run_semantic_insights' and xtype='U')
                BEGIN
                    CREATE TABLE run_semantic_insights (
                        run_id VARCHAR(50) PRIMARY KEY,
                        payload NVARCHAR(MAX) NOT NULL,
                        created_at DATETIME DEFAULT GETDATE(),
                        updated_at DATETIME DEFAULT GETDATE(),
                        FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
                    );
                END
            """, "Create run_semantic_insights table")

            # Adicionar campos de Performance (Core Web Vitals) em runs
            im_seo_columns = [
                ("lcp_score", "FLOAT"),
                ("fid_score", "FLOAT"),
                ("cls_score", "FLOAT"),
                ("core_web_vitals_score", "FLOAT"),
                ("share_of_voice_serp", "FLOAT"),
                ("serp_features_presence", "FLOAT"),
                ("ia_resources_detected", "INT"),
                ("ia_serp_presence_score", "FLOAT"),
                ("long_tail_terms_top10", "INT"),
                ("long_tail_terms_top20", "INT"),
                ("long_tail_coverage_score", "FLOAT"),
                ("eeat_score", "FLOAT"),
                ("eeat_expertise", "FLOAT"),
                ("eeat_experience", "FLOAT"),
                ("eeat_authoritativeness", "FLOAT"),
                ("eeat_trustworthiness", "FLOAT"),
                ("entities_detected", "INT"),
                ("entities_relevance_score", "FLOAT"),
                ("entity_connection_score", "FLOAT"),
                ("schema_types_detected", "NVARCHAR(MAX)"),
                ("schema_coverage_score", "FLOAT"),
                ("schema_valid", "BIT"),
                ("ia_ready_blocks_count", "INT"),
                ("ia_ready_score", "FLOAT"),
                ("has_lists", "BIT"),
                ("has_faqs", "BIT"),
                ("has_tables", "BIT"),
                ("has_step_by_step", "BIT"),
                ("irzc_score", "FLOAT"),
                ("ctr_expected", "FLOAT"),
                ("ctr_real", "FLOAT"),
                ("ctr_ratio", "FLOAT"),
                ("im_seo_score", "FLOAT"),
                ("im_seoia_score", "FLOAT"),
                ("response_text", "NVARCHAR(MAX)"),
                ("perceived_value_category", "VARCHAR(50)"),
                ("semantic_summary", "NVARCHAR(MAX)"),
            ]

            for col_name, col_type in im_seo_columns:
                _exec_safe(f"""
                    IF NOT EXISTS (
                        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'runs' AND COLUMN_NAME = '{col_name}'
                    )
                    BEGIN
                        ALTER TABLE dbo.runs ADD {col_name} {col_type} NULL;
                    END
                """, f"Add runs.{col_name} column for IM metrics")

            serp_feature_columns = [
                ("paa_items", "NVARCHAR(MAX)"),
                ("knowledge_panel_json", "NVARCHAR(MAX)"),
                ("ai_overview_json", "NVARCHAR(MAX)"),
            ]

            for col_name, col_type in serp_feature_columns:
                _exec_safe(f"""
                    IF NOT EXISTS (
                        SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'serp_features' AND COLUMN_NAME = '{col_name}'
                    )
                    BEGIN
                        ALTER TABLE dbo.serp_features ADD {col_name} {col_type} NULL;
                    END
                """, f"Add serp_features.{col_name} column")

            print("[MIGRATION] SQL Server migration completed (including IM-SEO/IM-SEOIA).")
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
app.include_router(search_console_router)
app.include_router(analytics_router, prefix="/api/analytics")
app.include_router(export_router, prefix="/api")
