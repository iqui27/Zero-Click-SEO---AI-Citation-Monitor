from __future__ import annotations

from datetime import date, datetime, timedelta
import time
from typing import Iterable, Optional, Tuple, Dict, Any, Set

from sqlalchemy import func, case, and_, or_, Date, cast
from sqlalchemy.orm import Session
from sqlalchemy.exc import DBAPIError

from app.models.models import (
    Run,
    GeoDailyMetric,
    PromptVersion,
    Engine,
)
from app.services.geo_dashboard import compute_geo_dashboard

DEFAULT_WINDOWS = (1, 7, 30)
DEFAULT_BRAND_PRESENCE = ("all", "with_brand", "without_brand")


def _normalize_model_name(model_name: Optional[str], engine_name: Optional[str]) -> Optional[str]:
    if model_name:
        base = model_name.strip().lower()
        if base:
            return base
    if engine_name:
        base = engine_name.strip().lower()
        if base:
            return base
    return None


def _date_expression(dialect_name: str):
    coalesced = func.coalesce(Run.started_at, Run.finished_at)
    if dialect_name == "mssql":
        return cast(coalesced, Date)
    return func.date(coalesced)


def _collect_scope_combinations(
    db: Session,
    project_id: str,
    start_date: date,
    end_date: date,
) -> Set[Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]]:
    dialect = db.bind.dialect.name
    date_expr = _date_expression(dialect)

    rows = (
        db.query(
            PromptVersion.prompt_id,
            Run.prompt_version_id,
            Run.subproject_id,
            Run.model_name,
            Engine.name.label("engine_name"),
        )
        .outerjoin(PromptVersion, Run.prompt_version_id == PromptVersion.id)
        .outerjoin(Engine, Run.engine_id == Engine.id)
        .filter(Run.project_id == project_id)
        .filter(Run.status == "completed")
        .filter(date_expr >= start_date)
        .filter(date_expr <= end_date)
        .distinct()
        .all()
    )

    scopes: Set[Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]] = set()
    scopes.add((None, None, None, None))

    for row in rows:
        llm_model = _normalize_model_name(row.model_name, row.engine_name)
        scopes.add((row.prompt_id, row.prompt_version_id, row.subproject_id, llm_model))

        # Também armazenar combinacoes sem prompt_version_id para suportar filtro por prompt_id
        if row.prompt_id:
            scopes.add((row.prompt_id, None, row.subproject_id, llm_model))

    return scopes


def _build_stats_query(
    db: Session,
    project_id: str,
    start_date: date,
    end_date: date,
    prompt_id: Optional[str],
    prompt_version_id: Optional[str],
    subproject_id: Optional[str],
    llm_model: Optional[str],
    brand_presence: str,
):
    dialect = db.bind.dialect.name
    date_expr = _date_expression(dialect)

    query = (
        db.query(
            func.count(Run.id).label("runs_total"),
            func.coalesce(func.sum(Run.brand_mention_count), 0).label("brand_mentions_total"),
            func.sum(case((Run.our_citations_count > 0, 1), else_=0)).label("runs_with_brand"),
            func.coalesce(func.sum(Run.brand_prominence_score), 0.0).label("brand_prominence_sum"),
            func.coalesce(func.sum(Run.zero_click_presence), 0.0).label("zero_click_sum"),
            func.coalesce(func.sum(Run.engagement_score), 0.0).label("engagement_sum"),
            func.coalesce(func.sum(Run.conversion_potential_score), 0.0).label("conversion_potential_sum"),
            func.coalesce(func.sum(Run.authority_score), 0.0).label("authority_sum"),
            func.coalesce(func.sum(Run.relevance_score), 0.0).label("relevance_sum"),
            func.coalesce(func.sum(Run.clarity_score), 0.0).label("clarity_sum"),
            func.coalesce(func.sum(Run.im_seo_score), 0.0).label("im_seo_sum"),
            func.coalesce(func.sum(Run.im_seoia_score), 0.0).label("im_seoia_sum"),
            func.coalesce(func.sum(Run.citation_rate_observed), 0.0).label("citation_rate_observed_sum"),
            func.coalesce(func.sum(Run.citation_rate_corrected), 0.0).label("citation_rate_corrected_sum"),
        )
        .filter(Run.project_id == project_id)
        .filter(Run.status == "completed")
        .filter(date_expr >= start_date)
        .filter(date_expr <= end_date)
    )

    if prompt_version_id:
        query = query.filter(Run.prompt_version_id == prompt_version_id)
    elif prompt_id:
        query = query.join(PromptVersion, Run.prompt_version_id == PromptVersion.id)
        query = query.filter(PromptVersion.prompt_id == prompt_id)

    if subproject_id:
        query = query.filter(Run.subproject_id == subproject_id)

    if llm_model:
        llm_model_norm = llm_model.strip().lower()
        query = query.outerjoin(Engine, Run.engine_id == Engine.id)
        query = query.filter(
            or_(
                func.lower(func.coalesce(Run.model_name, "")).like(f"%{llm_model_norm}%"),
                func.lower(func.coalesce(Engine.name, "")).like(f"%{llm_model_norm}%"),
            )
        )

    if brand_presence == "with_brand":
        query = query.filter(Run.our_citations_count > 0)
    elif brand_presence == "without_brand":
        query = query.filter(or_(Run.our_citations_count == 0, Run.our_citations_count.is_(None)))

    return query


def _persist_geo_metric(
    db: Session,
    *,
    project_id: str,
    metric_date: date,
    window_days: int,
    prompt_id: Optional[str],
    prompt_version_id: Optional[str],
    subproject_id: Optional[str],
    llm_model: Optional[str],
    brand_presence: str,
    stats,
    payload: Dict[str, Any],
    max_retries: int = 3,
) -> bool:
    """Insert or update a GeoDailyMetric row with basic deadlock retry."""

    def _build_query() -> Any:
        query = (
            db.query(GeoDailyMetric)
            .filter(
                GeoDailyMetric.project_id == project_id,
                GeoDailyMetric.metric_date == metric_date,
                GeoDailyMetric.window_days == window_days,
                GeoDailyMetric.brand_presence == brand_presence,
            )
        )

        if prompt_id:
            query = query.filter(GeoDailyMetric.prompt_id == prompt_id)
        else:
            query = query.filter(GeoDailyMetric.prompt_id.is_(None))

        if prompt_version_id:
            query = query.filter(GeoDailyMetric.prompt_version_id == prompt_version_id)
        else:
            query = query.filter(GeoDailyMetric.prompt_version_id.is_(None))

        if subproject_id:
            query = query.filter(GeoDailyMetric.subproject_id == subproject_id)
        else:
            query = query.filter(GeoDailyMetric.subproject_id.is_(None))

        if llm_model:
            query = query.filter(GeoDailyMetric.llm_model == llm_model)
        else:
            query = query.filter(GeoDailyMetric.llm_model.is_(None))

        return query

    for attempt in range(max_retries):
        try:
            record = _build_query().one_or_none()

            if not record:
                record = GeoDailyMetric(
                    project_id=project_id,
                    metric_date=metric_date,
                    window_days=window_days,
                    prompt_id=prompt_id,
                    prompt_version_id=prompt_version_id,
                    subproject_id=subproject_id,
                    llm_model=llm_model,
                    brand_presence=brand_presence,
                )
                db.add(record)

            record.runs_total = stats.runs_total or 0
            record.runs_with_brand = stats.runs_with_brand or 0
            record.brand_mentions_total = stats.brand_mentions_total or 0
            record.exclusive_mentions_total = payload.get("exclusive_citations_count", 0) or 0
            record.brand_prominence_sum = float(stats.brand_prominence_sum or 0.0)
            record.zero_click_sum = float(stats.zero_click_sum or 0.0)
            record.engagement_sum = float(stats.engagement_sum or 0.0)
            record.conversion_potential_sum = float(stats.conversion_potential_sum or 0.0)
            record.authority_sum = float(stats.authority_sum or 0.0)
            record.relevance_sum = float(stats.relevance_sum or 0.0)
            record.clarity_sum = float(stats.clarity_sum or 0.0)
            record.im_seo_sum = float(stats.im_seo_sum or 0.0)
            record.im_seoia_sum = float(stats.im_seoia_sum or 0.0)
            record.citation_rate_observed_sum = float(stats.citation_rate_observed_sum or 0.0)
            record.citation_rate_corrected_sum = float(stats.citation_rate_corrected_sum or 0.0)
            record.metrics_payload = payload
            record.llm_model = llm_model
            record.updated_at = datetime.utcnow()

            db.flush()
            db.commit()
            return True
        except DBAPIError as exc:
            db.rollback()
            orig = getattr(exc, "orig", None)
            if orig and getattr(orig, "args", None):
                message = " ".join(str(arg) for arg in orig.args)
            else:
                message = str(exc)
            if "1205" in message or "deadlock" in message.lower():
                backoff = 0.5 * (attempt + 1)
                time.sleep(backoff)
                continue
            raise

    return False


def recompute_geo_daily_metrics(
    db: Session,
    project_id: str,
    metric_date: date,
    windows: Iterable[int] = DEFAULT_WINDOWS,
    brand_presences: Iterable[str] = DEFAULT_BRAND_PRESENCE,
    limit_web_structure: int = 25,
) -> Dict[str, Any]:
    """
    Rebuild aggregated dashboard payloads for the given project and metric date.

    Returns metadata about processed scopes for observability.
    """
    processed = {
        "project_id": project_id,
        "metric_date": metric_date.isoformat(),
        "windows": [],
    }

    for window_days in windows:
        start_date = metric_date - timedelta(days=window_days - 1)
        scopes = _collect_scope_combinations(db, project_id, start_date, metric_date)

        window_meta = {
            "window_days": window_days,
            "scopes_processed": 0,
            "rows_upserted": 0,
        }

        for scope in scopes:
            prompt_id, prompt_version_id, subproject_id, llm_model_raw = scope
            normalized_llm = llm_model_raw.strip().lower() if llm_model_raw else None
            if normalized_llm:
                normalized_llm = normalized_llm[:64]

            for brand_presence in brand_presences:
                stats_query = _build_stats_query(
                    db=db,
                    project_id=project_id,
                    start_date=start_date,
                    end_date=metric_date,
                    prompt_id=prompt_id,
                    prompt_version_id=prompt_version_id,
                    subproject_id=subproject_id,
                    llm_model=normalized_llm,
                    brand_presence=brand_presence,
                )
                stats = stats_query.one()

                runs_total = stats.runs_total or 0

                if runs_total == 0:
                    # Evita armazenar linhas vazias para filtros específicos
                    continue

                payload = compute_geo_dashboard(
                    db=db,
                    project_id=project_id,
                    prompt_id=prompt_id,
                    prompt_version_id=prompt_version_id,
                    subproject_id=subproject_id,
                    date_from=start_date,
                    date_to=metric_date,
                    bank_ids=None,
                    llm_model=normalized_llm,
                    prompt_category=None,
                    prompt_text=None,
                    brand_presence=brand_presence,
                    force_materialized=False,
                    web_structure_page_size=limit_web_structure,
                )

                saved = _persist_geo_metric(
                    db=db,
                    project_id=project_id,
                    metric_date=metric_date,
                    window_days=window_days,
                    prompt_id=prompt_id,
                    prompt_version_id=prompt_version_id,
                    subproject_id=subproject_id,
                    llm_model=normalized_llm,
                    brand_presence=brand_presence,
                    stats=stats,
                    payload=payload,
                )
                if saved:
                    window_meta["rows_upserted"] += 1

            window_meta["scopes_processed"] += 1

        processed["windows"].append(window_meta)

    return processed
