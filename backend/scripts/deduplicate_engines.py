#!/usr/bin/env python3
"""Deduplicate Engine rows and migrate runs to canonical engines.

This script groups engines by `(project_id, name, region, device, config_hash)`
using the normalization helpers in `app.services.engine_registry`. Runs pointing
at duplicate engines are rewired to the canonical engine and any configuration
differences are persisted in `Run.engine_override_json`.

Usage:
    python backend/scripts/deduplicate_engines.py [--dry-run] [--project PROJECT_ID]
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.models import Engine, Run
from app.services.engine_registry import (
    apply_overrides,
    compute_config_hash,
    diff_configs,
    normalize_config,
)

Key = Tuple[str, str, str, str, str]


def _key_for_engine(engine: Engine, config_hash: str) -> Key:
    return (
        engine.project_id,
        (engine.name or "").strip(),
        (engine.region or "").strip(),
        (engine.device or "").strip(),
        config_hash,
    )


def _ensure_hash(session: Session, engine: Engine) -> str:
    canonical = normalize_config(engine.name, engine.config_json)
    cfg_hash = engine.config_hash or compute_config_hash(canonical)
    if engine.config_hash != cfg_hash:
        engine.config_hash = cfg_hash
        session.add(engine)
    return cfg_hash


def _repoint_runs(
    session: Session,
    runs: Iterable[Run],
    canonical_engine: Engine,
    canonical_cfg: Dict,
    duplicate_cfg: Dict,
    dry_run: bool,
) -> Tuple[int, int]:
    override_delta = diff_configs(canonical_cfg, duplicate_cfg) or {}
    updated_runs = 0
    overrides_written = 0

    for run in runs:
        merged_override = dict(run.engine_override_json or {})
        if override_delta:
            # duplicate config defines the target behaviour; overrides take precedence
            merged_override.update(override_delta)
        merged_override = {k: v for k, v in merged_override.items() if v is not None}

        if dry_run:
            print(
                f"DRY-RUN: would move run {run.id} -> engine {canonical_engine.id}"
                + (f" with overrides {merged_override}" if merged_override else "")
            )
            continue

        run.engine_id = canonical_engine.id
        run.engine_override_json = merged_override or None
        session.add(run)
        updated_runs += 1
        if merged_override:
            overrides_written += 1

    return updated_runs, overrides_written


def deduplicate_engines(project_id: Optional[str], dry_run: bool) -> None:
    session = SessionLocal()
    removed = 0
    reassigned_runs = 0
    overrides = 0
    try:
        engines_stmt = select(Engine)
        if project_id:
            engines_stmt = engines_stmt.where(Engine.project_id == project_id)
        engines = session.execute(engines_stmt).scalars().all()

        groups: Dict[Key, Engine] = {}
        duplicates: Dict[Key, List[Engine]] = defaultdict(list)

        for engine in engines:
            cfg_hash = _ensure_hash(session, engine)
            key = _key_for_engine(engine, cfg_hash)
            if key not in groups:
                groups[key] = engine
            else:
                duplicates[key].append(engine)

        if not dry_run:
            session.commit()

        if not duplicates:
            print("No duplicate engines detected. Nothing to do.")
            return

        for key, dup_list in duplicates.items():
            canonical = groups[key]
            canonical_cfg = normalize_config(canonical.name, canonical.config_json)
            if dup_list:
                print(
                    f"Processing {len(dup_list)} duplicate(s) for engine {canonical.id}"
                    f" [project={canonical.project_id} name={canonical.name} region={canonical.region} device={canonical.device}]"
                )
            for dup in dup_list:
                duplicate_cfg = normalize_config(dup.name, dup.config_json)
                runs_stmt = select(Run).where(Run.engine_id == dup.id)
                runs = session.execute(runs_stmt).scalars().all()
                updated, overrides_written = _repoint_runs(
                    session,
                    runs,
                    canonical,
                    canonical_cfg,
                    duplicate_cfg,
                    dry_run,
                )
                reassigned_runs += updated
                overrides += overrides_written

                if dry_run:
                    continue

                session.delete(dup)
                removed += 1
                session.commit()

        print("=== Deduplication summary ===")
        print(f"Canonical groups: {len(groups)}")
        print(f"Duplicate engines removed: {removed}")
        print(f"Runs reassigned: {reassigned_runs}")
        print(f"Runs with overrides set: {overrides}")
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Deduplicate engines and migrate runs to canonical entries.")
    parser.add_argument("--project", dest="project_id", help="Limit to a single project id", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing to the database")

    args = parser.parse_args()
    deduplicate_engines(args.project_id, args.dry_run)


if __name__ == "__main__":
    main()
