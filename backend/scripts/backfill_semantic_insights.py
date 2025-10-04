"""Backfill de insights semânticos com Gemini para runs existentes."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import Run
from app.services.tasks import process_semantic_insights


def backfill_semantic_insights(
    *,
    project_id: str | None = None,
    days: int | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> None:
    """Enfileira tarefas de insights semânticos para runs já processadas."""

    if not settings.semantic_insights_enabled:
        raise RuntimeError("SEMANTIC_INSIGHTS_ENABLED está desativado no ambiente atual")

    db = SessionLocal()
    try:
        query = db.query(Run).filter(Run.status == "completed")

        if project_id:
            query = query.filter(Run.project_id == project_id)

        if days is not None:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Run.finished_at >= cutoff)

        query = query.order_by(Run.finished_at.desc())

        if limit is not None:
            query = query.limit(limit)

        runs = query.all()

        print(f"[BACKFILL] Runs selecionadas: {len(runs)}")

        for run in runs:
            if dry_run:
                print(f"[DRY-RUN] {run.id} ({run.finished_at})")
                continue

            print(f"[BACKFILL] Enfileirando run {run.id}")
            process_semantic_insights.delay(run.id)

    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reprocessa insights semânticos para runs antigas")
    parser.add_argument("--project", dest="project_id", help="Filtrar por projeto")
    parser.add_argument("--days", type=int, help="Janela em dias a partir de hoje")
    parser.add_argument("--limit", type=int, help="Limitar número de runs")
    parser.add_argument("--dry-run", action="store_true", help="Somente listar runs sem enfileirar")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    backfill_semantic_insights(
        project_id=args.project_id,
        days=args.days,
        limit=args.limit,
        dry_run=args.dry_run,
    )
