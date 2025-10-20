from __future__ import annotations

import json
import os
from typing import Any, Dict

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import RunSemanticInsight
from app.services.semantic_payload import store_insight_payload, load_insight_payload


def migrate_batch(db: Session, batch_size: int = 100) -> int:
    migrated = 0
    query = select(RunSemanticInsight).where(RunSemanticInsight.payload.isnot(None)).limit(batch_size)
    results = db.execute(query).scalars().all()
    for insight in results:
        payload = load_insight_payload(insight)
        if not payload:
            continue
        store_insight_payload(insight, payload)
        migrated += 1
    if migrated:
        db.commit()
    return migrated


def main() -> None:
    if not settings.azure_blob_connection_string:
        raise RuntimeError("Azure Blob connection string not configured")

    total_migrated = 0
    with SessionLocal() as db:
        while True:
            migrated = migrate_batch(db)
            if not migrated:
                break
            total_migrated += migrated
            print(f"Migrated {migrated} semantic payload(s) in this batch")

    print(f"Total migrated: {total_migrated}")


if __name__ == "__main__":
    main()
