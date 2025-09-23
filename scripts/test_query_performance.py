#!/usr/bin/env python3
"""
Script para testar performance das otimizações na query de listagem de runs
"""

import os
import sys
import time
import argparse
from pathlib import Path
from sqlalchemy import text

# Adicionar o diretório backend ao Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionLocal


def time_query(db, query_text: str, params: dict = None, description: str = "Query") -> float:
    """Executa uma query e mede o tempo de execução"""
    start_time = time.time()
    try:
        result = db.execute(text(query_text), params or {})
        rows = result.fetchall()
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"✅ {description}: {execution_time:.3f}s ({len(rows)} rows)")
        return execution_time
    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"❌ {description}: {execution_time:.3f}s (ERROR: {e})")
        return execution_time


def test_runs_listing_performance(project_id: str = None):
    """Testa a performance da query principal de listagem de runs"""

    print("=== 🚀 Teste de Performance - Listagem de Runs ===")
    print()

    db = SessionLocal()
    try:
        # Query original (custosa com JOINs)
        original_query = """
        SELECT runs.id AS runs_id, engines.name AS engine, runs.status AS runs_status,
               runs.started_at AS runs_started_at, runs.finished_at AS runs_finished_at,
               runs.zcrs AS runs_zcrs, runs.amr_flag AS runs_amr_flag, runs.dcr_flag AS runs_dcr_flag,
               runs.cost_usd AS runs_cost_usd, runs.tokens_total AS runs_tokens_total,
               runs.cycles_total AS runs_cycles_total, runs.cycle_delay_seconds AS runs_cycle_delay_seconds,
               runs.monitor_id AS runs_monitor_id, runs.schedule_date AS runs_schedule_date,
               runs.schedule_slot AS runs_schedule_slot, runs.schedule_index_today AS runs_schedule_index_today,
               runs.schedule_total_today AS runs_schedule_total_today, runs.schedule_source AS runs_schedule_source,
               coalesce(prompts.name, '-') AS template_name, prompt_templates.category AS template_category,
               coalesce(subprojects.name, '-') AS subproject_name, monitors.name AS monitor_name
        FROM runs
        JOIN engines ON engines.id = runs.engine_id
        LEFT OUTER JOIN prompt_versions ON prompt_versions.id = runs.prompt_version_id
        LEFT OUTER JOIN prompts ON prompts.id = prompt_versions.prompt_id
        LEFT OUTER JOIN prompt_templates ON prompt_templates.project_id = runs.project_id
            AND replace(replace(prompts.name, 'Template: ', ''), 'Run: ', '') = prompt_templates.name
            AND (prompt_templates.subproject_id = runs.subproject_id OR prompt_templates.subproject_id IS NULL AND runs.subproject_id IS NULL)
        LEFT OUTER JOIN subprojects ON subprojects.id = runs.subproject_id
        LEFT OUTER JOIN monitors ON monitors.id = runs.monitor_id
        WHERE runs.project_id = :project_id
        ORDER BY CASE WHEN (runs.started_at IS NULL) THEN 1 ELSE 0 END ASC, runs.started_at DESC, runs.id DESC
        OFFSET 0 ROWS FETCH FIRST 100 ROWS ONLY
        """

        # Query otimizada (sem JOINs custosos)
        optimized_query = """
        SELECT runs.id AS runs_id, engines.name AS engine, runs.status AS runs_status,
               runs.started_at AS runs_started_at, runs.finished_at AS runs_finished_at,
               runs.zcrs AS runs_zcrs, runs.amr_flag AS runs_amr_flag, runs.dcr_flag AS runs_dcr_flag,
               runs.cost_usd AS runs_cost_usd, runs.tokens_total AS runs_tokens_total,
               runs.cycles_total AS runs_cycles_total, runs.cycle_delay_seconds AS runs_cycle_delay_seconds,
               runs.monitor_id AS runs_monitor_id, runs.schedule_date AS runs_schedule_date,
               runs.schedule_slot AS runs_schedule_slot, runs.schedule_index_today AS runs_schedule_index_today,
               runs.schedule_total_today AS runs_schedule_total_today, runs.schedule_source AS runs_schedule_source,
               runs.response_type, runs.sufficiency_level, runs.actionability_type,
               runs.trust_source, runs.brand_positioning, runs.classification_confidence,
               '-' AS template_name, NULL AS template_category,
               coalesce(subprojects.name, '-') AS subproject_name, monitors.name AS monitor_name
        FROM runs
        JOIN engines ON engines.id = runs.engine_id
        LEFT OUTER JOIN subprojects ON subprojects.id = runs.subproject_id
        LEFT OUTER JOIN monitors ON monitors.id = runs.monitor_id
        WHERE runs.project_id = :project_id
        ORDER BY CASE WHEN (runs.started_at IS NULL) THEN 1 ELSE 0 END ASC, runs.started_at DESC, runs.id DESC
        OFFSET 0 ROWS FETCH FIRST 100 ROWS ONLY
        """

        # Query para contar total de runs
        count_query = "SELECT COUNT(*) FROM runs WHERE project_id = :project_id"

        # Obter um project_id se não fornecido
        if not project_id:
            result = db.execute(text("SELECT TOP 1 id FROM projects"))
            row = result.fetchone()
            if row:
                project_id = row[0]
                print(f"Usando project_id: {project_id}")
            else:
                print("❌ Nenhum projeto encontrado na base de dados")
                return

        params = {"project_id": project_id}

        print("📊 Executando testes de performance...")
        print()

        # Teste 1: Contar runs
        time_query(db, count_query, params, "COUNT de runs")

        print()
        print("🔥 Comparação de queries:")

        # Teste 2: Query original (custosa)
        original_time = time_query(db, original_query, params, "Query ORIGINAL (com JOINs custosos)")

        # Teste 3: Query otimizada
        optimized_time = time_query(db, optimized_query, params, "Query OTIMIZADA (sem JOINs custosos)")

        # Calcular melhoria
        if original_time > 0:
            improvement = ((original_time - optimized_time) / original_time) * 100
            print()
            print(f"📈 Melhoria de performance: {improvement:.1f}%")
            if improvement > 0:
                print(f"⚡ Query otimizada é {original_time/optimized_time:.1f}x mais rápida")
            else:
                print("⚠️  Query otimizada não mostrou melhoria significativa")

        print()
        print("🔍 Testando queries de filtros específicos...")

        # Teste 4: Filtro por status
        status_query = optimized_query.replace(
            "WHERE runs.project_id = :project_id",
            "WHERE runs.project_id = :project_id AND runs.status = 'completed'"
        )
        time_query(db, status_query, params, "Filtro por status = 'completed'")

        # Teste 5: Filtro por data (últimos 7 dias)
        date_query = optimized_query.replace(
            "WHERE runs.project_id = :project_id",
            "WHERE runs.project_id = :project_id AND runs.started_at >= DATEADD(day, -7, GETDATE())"
        )
        time_query(db, date_query, params, "Filtro por data (últimos 7 dias)")

        # Teste 6: Verificar se os índices estão sendo usados
        print()
        print("📋 Verificando índices disponíveis...")

        index_query = """
        SELECT i.name as index_name, t.name as table_name,
               STRING_AGG(c.name, ', ') as columns
        FROM sys.indexes i
        JOIN sys.tables t ON i.object_id = t.object_id
        JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        WHERE t.name IN ('runs', 'engines', 'subprojects', 'monitors')
        AND i.name LIKE 'ix_%'
        GROUP BY i.name, t.name
        ORDER BY t.name, i.name
        """

        result = db.execute(text(index_query))
        indexes = result.fetchall()

        if indexes:
            for idx in indexes:
                print(f"  📌 {idx.table_name}.{idx.index_name}: [{idx.columns}]")
        else:
            print("  ⚠️  Nenhum índice personalizado encontrado")

    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Teste de Performance das Queries Otimizadas')
    parser.add_argument(
        '--project-id',
        type=str,
        help='ID do projeto para testar (opcional)'
    )

    args = parser.parse_args()

    test_runs_listing_performance(args.project_id)


if __name__ == "__main__":
    main()