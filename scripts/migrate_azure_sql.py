#!/usr/bin/env python3
"""
Migrate data from one Azure SQL (SQL Server) database to another using SQLAlchemy
and the project's ORM models.

Usage examples:

  # Using full URLs (recommended; make sure to URL-encode special chars in password)
  export SOURCE_DATABASE_URL="mssql+pyodbc://user:pass%402025%21@old-host:1433/olddb?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
  export TARGET_DATABASE_URL="mssql+pyodbc://usrMonumenta:Monu%402025%21@db-aigeo.database.windows.net:1433/db-ai-geo-hml?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
  python scripts/migrate_azure_sql.py

Notes:
- Do NOT commit secrets. Prefer exporting variables only in your shell session.
- The script will create the target schema (tables) if not present.
- It will copy rows table-by-table in FK-safe order, skipping IDs already present.
- For monitor_templates (integer identity PK), we skip copying the PK value and
  avoid duplicates using the (monitor_id, template_id) uniqueness.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Iterable, List, Tuple, Dict, Set

from sqlalchemy import create_engine, text, insert, select, MetaData, Table, Column
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, DBAPIError

# Import models and Base from the app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.db.base import Base
from app.models.models import (
    Project,
    Domain,
    Prompt,
    PromptVersion,
    Engine,
    SubProject,
    Monitor,
    PromptTemplate,
    Run,
    Evidence,
    Citation,
    Reason,
    RunEvent,
    Insight,
    CompetitorScore,
    MonitorTemplate,
)


def get_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f"ERROR: environment variable {name} is required", file=sys.stderr)
        sys.exit(2)
    return v


def make_engine(url: str):
    # Match app backend settings for MSSQL reliability
    connect_args: Dict[str, Any] = {}
    if url.startswith("mssql"):
        connect_args = {
            "timeout": 120,
            "login_timeout": 120,
            "autocommit": True,
        }
        return create_engine(
            url,
            pool_pre_ping=True,
            connect_args=connect_args,
            pool_timeout=60,
            pool_recycle=3600,
        )
    else:
        return create_engine(
            url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )


def fetch_existing_ids(sess: Session, model) -> Set[Any]:
    pk_col = model.__table__.c.get("id")
    if pk_col is None:
        return set()
    rows = sess.execute(select(pk_col)).all()
    return {r[0] for r in rows}


def chunked(iterable: Iterable[Any], size: int) -> Iterable[List[Any]]:
    batch: List[Any] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def row_to_dict(row_obj, model, skip_columns: Set[str] | None = None) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    skip_columns = skip_columns or set()
    for col in model.__table__.columns:
        if col.name in skip_columns:
            continue
        data[col.name] = getattr(row_obj, col.name)
    return data


def ensure_target_schema(engine):
    print("[SCHEMA] Creating target schema if missing...")
    try:
        Base.metadata.create_all(bind=engine)
        print("[SCHEMA] Done.")
        return
    except Exception as e:
        msg = str(e).lower()
        if "multiple cascade" not in msg and "1785" not in msg:
            raise
        print("[SCHEMA] Detected SQL Server multiple cascade paths issue. Falling back to create tables WITHOUT foreign keys...")

    # Fallback: clone metadata without foreign keys and create
    clone_md = MetaData()
    for src_table in Base.metadata.sorted_tables:
        new_cols = []
        for c in src_table.columns:
            # Recreate column without ForeignKey constraints
            new_col = Column(
                c.name,
                c.type,
                primary_key=c.primary_key,
                nullable=c.nullable,
                default=c.default,
                server_default=c.server_default,
                autoincrement=c.autoincrement,
            )
            new_cols.append(new_col)
        Table(src_table.name, clone_md, *new_cols)

    clone_md.create_all(bind=engine)
    print("[SCHEMA] Tables created without FKs. The application startup will manage additional constraints as needed.")


def copy_simple_table(src: Session, dst: Session, model, batch_size: int = 500) -> Tuple[int, int]:
    """Copy rows by primary key presence (assumes string PK named 'id')."""
    print(f"[COPY] {model.__tablename__} ...", flush=True)
    src_rows = src.query(model).all()
    if not src_rows:
        print(f"[COPY] {model.__tablename__}: nothing to copy")
        return (0, 0)

    inserted = 0
    skipped = 0
    table = model.__table__
    # SQL Server supports max 2100 parameters per statement. Keep under ~2000.
    cols_count = max(1, len(table.columns))
    max_rows = max(1, 2000 // cols_count)
    eff_batch = min(batch_size, max_rows)

    # Process in batches and de-duplicate against target per-batch
    def id_of(row: dict):
        return row.get("id")

    all_rows = [row_to_dict(r, model) for r in src_rows]

    for batch in chunked(all_rows, eff_batch):
        ids = [id_of(r) for r in batch if id_of(r) is not None]
        if ids:
            existing = set(x[0] for x in dst.execute(select(table.c.id).where(table.c.id.in_(ids))).all())
        else:
            existing = set()
        pending = [r for r in batch if id_of(r) not in existing]
        skipped += len(batch) - len(pending)
        if not pending:
            continue
        try:
            dst.execute(insert(table).values(pending))
            inserted += len(pending)
        except (IntegrityError, DBAPIError) as _:
            # Retry one-by-one to skip any race/duplicates
            for row in pending:
                try:
                    dst.execute(insert(table).values(row))
                    inserted += 1
                except Exception:
                    skipped += 1
    print(f"[COPY] {model.__tablename__}: inserted={inserted}, skipped={skipped}")
    return inserted, skipped


def copy_monitor_templates(src: Session, dst: Session, batch_size: int = 500) -> Tuple[int, int]:
    """Copy monitor_templates avoiding duplicate (monitor_id, template_id) and not forcing identity PK."""
    model = MonitorTemplate
    print(f"[COPY] {model.__tablename__} ...", flush=True)
    src_rows = src.query(model).all()
    if not src_rows:
        print(f"[COPY] {model.__tablename__}: nothing to copy")
        return (0, 0)

    # Fetch existing pairs
    tbl = model.__table__
    existing_pairs = set(dst.execute(select(tbl.c.monitor_id, tbl.c.template_id)).all())

    to_insert = []
    for r in src_rows:
        key = (r.monitor_id, r.template_id)
        if key in existing_pairs:
            continue
        # skip the identity PK column 'id', let SQL Server assign
        to_insert.append(row_to_dict(r, model, skip_columns={"id"}))

    inserted = 0
    skipped = len(src_rows) - len(to_insert)

    # Adjust batch size for SQL Server parameter limit (estimate by row keys)
    if to_insert:
        cols_count = max(1, len(to_insert[0].keys()))
        max_rows = max(1, 2000 // cols_count)
        eff_batch = min(batch_size, max_rows)
    else:
        eff_batch = batch_size

    for batch in chunked(to_insert, eff_batch):
        try:
            dst.execute(insert(tbl).values(batch))
            inserted += len(batch)
        except (IntegrityError, DBAPIError) as _:
            # Retry item by item
            for row in batch:
                try:
                    dst.execute(insert(tbl).values(row))
                    inserted += 1
                except Exception:
                    skipped += 1

    print(f"[COPY] {model.__tablename__}: inserted={inserted}, skipped={skipped}")
    return inserted, skipped


def main() -> None:
    source_url = get_env("SOURCE_DATABASE_URL")
    target_url = get_env("TARGET_DATABASE_URL")

    print("[INFO] Source:", source_url)
    print("[INFO] Target:", target_url)

    src_engine = make_engine(source_url)
    dst_engine = make_engine(target_url)

    ensure_target_schema(dst_engine)

    with Session(src_engine) as src_sess, Session(dst_engine) as dst_sess:
        # Copy in FK-safe order
        order = [
            Project,
            Domain,
            Engine,
            Prompt,
            PromptVersion,
            SubProject,
            Monitor,
            PromptTemplate,
            Run,
            Evidence,
            Citation,
            Reason,
            RunEvent,
            Insight,
            CompetitorScore,
        ]

        total_inserted = 0
        total_skipped = 0

        for model in order:
            try:
                ins, skp = copy_simple_table(src_sess, dst_sess, model)
                total_inserted += ins
                total_skipped += skp
                dst_sess.commit()
            except Exception as e:
                dst_sess.rollback()
                print(f"[ERROR] Failed copying {model.__tablename__}: {e}")
                raise

        # Handle the identity table with special rules
        try:
            ins, skp = copy_monitor_templates(src_sess, dst_sess)
            total_inserted += ins
            total_skipped += skp
            dst_sess.commit()
        except Exception as e:
            dst_sess.rollback()
            print(f"[ERROR] Failed copying monitor_templates: {e}")
            raise

    print("[DONE] Migration completed. inserted=", total_inserted, "skipped=", total_skipped)


if __name__ == "__main__":
    main()
