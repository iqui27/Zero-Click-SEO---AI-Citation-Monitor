"""
GEO Dashboard Data Aggregation Service

Aggregates metrics across runs for the POC dashboard including:
- KPIs (ranking, mentions, EEAT, perception)
- Radar charts (IM-SEO, IRZC, EEAT, Web Vitals)
- Brand positioning/rankings
- Keywords & entities
- Panorama metrics
- Web structure checklist
- AI-generated insights and alerts
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Set
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, desc, text, Date
from collections import Counter, defaultdict
import json
import re
import statistics
from urllib.parse import urlparse

from app.models.models import (
    Run,
    Citation,
    Entity,
    Evidence,
    SerpFeature,
    Project,
    Domain,
    Prompt,
    PromptTemplate,
    SubProject,
    RunSemanticInsight,
    PromptVersion,
)
from app.services.normalization import normalize_domain


# Official bank domains for web structure filtering
OFFICIAL_BANK_DOMAINS: Set[str] = {
    "bb.com.br",
    "itau.com.br",
    "itauuniclass.com.br",
    "bancodobrasil.com.br",
    "bradesco.com.br",
    "caixa.gov.br",
    "santander.com.br",
    "btgpactual.com.br",
    "safra.com.br",
    "sicredi.com.br",
    "sicoob.com.br",
    "inter.com.br",
    "nubank.com.br",
    "pagbank.com.br",
    "mercadopago.com.br",
    "c6bank.com.br",
    "bancoob.com.br",
    "bancoob.com",
    "banrisul.com.br",
    "banco.votorantim.com.br",
    "citibank.com.br",
    "banestes.com.br",
    "magie.com.br",
    "willbank.com.br",
    "digio.com.br",
    "inter.co",
}


def _is_official_bank_domain(domain: str) -> bool:
    """Check if domain is an official bank domain."""
    domain = normalize_domain(domain)
    if domain in OFFICIAL_BANK_DOMAINS:
        return True

    for allowed in OFFICIAL_BANK_DOMAINS:
        if domain.endswith("." + allowed):
            return True

    return False


def _domain_matches(citation_domain: str, our_domains: set) -> bool:
    """
    Check if citation domain matches any of our domains (including subdomains).

    Examples:
        www45.bb.com.br matches bb.com.br
        subdomain.example.com matches example.com
    """
    citation_domain = citation_domain.lower().strip()

    # Direct match
    if citation_domain in our_domains:
        return True

    # Check if it's a subdomain of any of our domains
    for our_domain in our_domains:
        # Add dot to avoid partial matches (e.g., "notbb.com.br" shouldn't match "bb.com.br")
        if citation_domain.endswith('.' + our_domain):
            return True

    return False


def compute_geo_dashboard(
    db: Session,
    project_id: str,
    prompt_id: Optional[str] = None,
    prompt_version_id: Optional[str] = None,
    subproject_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    bank_ids: Optional[List[str]] = None,
    llm_model: Optional[str] = None,
    prompt_category: Optional[str] = None,
    prompt_text: Optional[str] = None,
    brand_presence: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute aggregated GEO dashboard data with filtering.

    Args:
        db: Database session
        project_id: Project ID (required)
        prompt_id: Optional filter by prompt template ID
        prompt_version_id: Optional filter by prompt version
        subproject_id: Optional filter by subproject (tema)
        date_from: Optional start date filter
        date_to: Optional end date filter
        bank_ids: Optional list of bank domains/names to compare
        llm_model: Optional filter by LLM model name
        prompt_category: Optional filter by prompt template category
        prompt_text: Optional filter by prompt text (partial match)
        brand_presence: Optional filter by brand citations ('with_brand', 'without_brand', 'all')

    Returns:
        Dictionary with all dashboard sections
    """

    # Build base query with filters
    query = db.query(Run).filter(
        Run.project_id == project_id,
        Run.status == "completed"
    )

    # Filter by prompt category or text
    # Note: PromptTemplate has category, but Run uses prompt_version_id which links to Prompt (not PromptTemplate)
    # We'll filter by PromptTemplate if category is provided, otherwise by Prompt for text search
    if prompt_category:
        # Join through PromptVersion -> PromptTemplate for category filter
        query = query.join(PromptVersion, Run.prompt_version_id == PromptVersion.id)
        query = query.join(Prompt, PromptVersion.prompt_id == Prompt.id)
        # Note: Prompt doesn't have category, but PromptTemplate does
        # For now, we'll search in Prompt.name or text
        query = query.filter(
            or_(
                Prompt.name.ilike(f"%{prompt_category}%"),
                Prompt.text.ilike(f"%{prompt_category}%")
            )
        )
    elif prompt_text or prompt_id:
        query = query.join(PromptVersion, Run.prompt_version_id == PromptVersion.id)
        query = query.join(Prompt, PromptVersion.prompt_id == Prompt.id)
        
        if prompt_id:
            query = query.filter(Prompt.id == prompt_id)
        
        if prompt_text:
            query = query.filter(
                or_(
                    Prompt.text.ilike(f"%{prompt_text}%"),
                    Prompt.name.ilike(f"%{prompt_text}%")
                )
            )
    elif prompt_version_id:
        query = query.filter(Run.prompt_version_id == prompt_version_id)

    if subproject_id:
        query = query.filter(Run.subproject_id == subproject_id)

    if date_from:
        # Use func.cast() - works on both SQLite and Azure SQL Server
        query = query.filter(func.cast(Run.started_at, Date) >= date_from)

    if date_to:
        # Use func.cast() - works on both SQLite and Azure SQL Server
        query = query.filter(func.cast(Run.started_at, Date) <= date_to)

    if llm_model:
        query = query.filter(Run.model_name.ilike(f"%{llm_model}%"))
    
    # Filter by brand presence
    if brand_presence == 'with_brand':
        query = query.filter(Run.our_citations_count > 0)
    elif brand_presence == 'without_brand':
        query = query.filter((Run.our_citations_count == 0) | (Run.our_citations_count.is_(None)))

    runs = query.all()

    if not runs:
        return _empty_dashboard()

    run_ids = [r.id for r in runs]

    # Get project info and domains for "our" detection
    project = db.query(Project).filter(Project.id == project_id).first()
    domains = db.query(Domain).filter(Domain.project_id == project_id).all()
    our_domains = {normalize_domain(d.domain) for d in domains if d.domain}
    our_label = project.name if project and project.name else "Nossa marca"

    # Aggregate data
    kpis = _compute_kpis(runs, our_domains, bank_ids)
    radar = _compute_radar(runs, bank_ids)
    positioning = _compute_positioning(db, run_ids, bank_ids, our_domains, our_label)
    keywords_entities = _compute_keywords_entities(db, run_ids)
    panorama = _compute_panorama(db, run_ids, runs)
    web_structure = _compute_web_structure(db, run_ids, bank_ids)
    alerts = _compute_alerts(runs)
    swot = _compute_swot(runs)
    raw_samples = _get_raw_samples(db, run_ids, limit=10)

    timeline, geo_summary = _compute_geo_timeline_and_summary(runs)
    cocitation_breakdown = _compute_cocitation_breakdown(db, run_ids, our_domains)
    context_insights = _compute_context_insights(runs)
    exclusive_citations_count = _compute_exclusive_citations(runs, our_domains)

    # Add semantic_scores to geo_summary from radar dimensions
    semantic_scores = _aggregate_semantic_scores(db, run_ids)
    if not semantic_scores and radar:
        # Fallback: use radar dimensions as semantic scores
        semantic_scores = {}
        for dimension in radar[0].get("dimensions", []):
            name = dimension.get("name", "").lower()
            value = dimension.get("value", 0)
            # Map dimension names to semantic score keys
            key_map = {
                "taxa de citação": "citation_rate",
                "engajamento": "engagement",
                "conversão": "conversion",
                "autoridade": "authority",
                "relevância": "relevance",
                "clareza": "clarity"
            }
            key = key_map.get(name, name.replace(" ", "_"))
            semantic_scores[key] = value
    
    if semantic_scores:
        geo_summary["semantic_scores"] = semantic_scores

    return {
        "project_id": project_id,
        "filters_applied": {
            "prompt_id": prompt_id,
            "prompt_version_id": prompt_version_id,
            "subproject_id": subproject_id,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "bank_ids": bank_ids,
            "llm_model": llm_model,
            "prompt_category": prompt_category,
            "prompt_text": prompt_text,
            "brand_presence": brand_presence,
        },
        "total_runs": len(runs),
        "kpis": kpis,
        "radar": radar,
        "positioning": positioning,
        "keywords_entities": keywords_entities,
        "panorama": panorama,
        "web_structure": web_structure,
        "alerts": alerts,
        "swot": swot,
        "raw_samples": raw_samples,
        "timeline": timeline,
        "geo_summary": geo_summary,
        "cocitation_breakdown": cocitation_breakdown,
        "context_insights": context_insights,
        "exclusive_citations_count": exclusive_citations_count,
    }


def _empty_dashboard() -> Dict[str, Any]:
    """Return empty dashboard structure when no data."""
    return {
        "project_id": None,
        "filters_applied": {},
        "total_runs": 0,
        "kpis": [],
        "radar": [],
        "positioning": {"brand_ranking": [], "perception_breakdown": []},
        "keywords_entities": {"word_cloud": [], "entities": []},
        "panorama": {"cards": [], "chart": []},
        "web_structure": [],
        "alerts": [],
        "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []},
        "raw_samples": [],
    }


def _trend_direction(current: Optional[float], previous: Optional[float]) -> str:
    if current is None and previous is None:
        return "neutral"
    if current is None:
        return "neutral"
    if previous in (None, 0):
        return "up" if current > 0 else "neutral"
    if current > previous:
        return "up"
    if current < previous:
        return "down"
    return "neutral"


def _compute_kpis(runs: List[Run], our_domains: set, bank_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Compute hero KPI metrics (últimos 7 dias vs período anterior)."""

    if not runs:
        return [
            {"label": "Menções de Marca", "value": 0, "unit": "total", "delta": None, "delta_unit": "percent"},
            {"label": "Taxa de Citação", "value": 0.0, "unit": "percent", "delta": None, "delta_unit": "points"},
            {"label": "Índice de Proeminência", "value": 0.0, "unit": "score", "delta": None, "delta_unit": "percent"},
            {"label": "Presença Zero-Click", "value": 0.0, "unit": "percent", "delta": None, "delta_unit": "points"},
        ]

    WINDOW_DAYS = 7

    def _resolve_date(run: Run) -> Optional[date]:
        ts = run.started_at or run.finished_at
        return ts.date() if ts else None

    sorted_runs = sorted(
        [r for r in runs if _resolve_date(r)],
        key=lambda r: (r.started_at or r.finished_at),
        reverse=True,
    )

    if not sorted_runs:
        return [
            {"label": "Menções de Marca", "value": 0, "unit": "total", "delta": None, "delta_unit": "percent"},
            {"label": "Taxa de Citação", "value": 0.0, "unit": "percent", "delta": None, "delta_unit": "points"},
            {"label": "Índice de Proeminência", "value": 0.0, "unit": "score", "delta": None, "delta_unit": "percent"},
            {"label": "Presença Zero-Click", "value": 0.0, "unit": "percent", "delta": None, "delta_unit": "points"},
        ]

    latest_date = _resolve_date(sorted_runs[0])
    current_start = latest_date - timedelta(days=WINDOW_DAYS - 1)
    previous_start = current_start - timedelta(days=WINDOW_DAYS)
    previous_end = current_start - timedelta(days=1)

    current_runs: List[Run] = []
    previous_runs: List[Run] = []

    for run in sorted_runs:
        run_date = _resolve_date(run)
        if not run_date:
            continue
        if run_date >= current_start:
            current_runs.append(run)
        elif previous_start <= run_date <= previous_end:
            previous_runs.append(run)

    def _aggregate(runs_bucket: List[Run]) -> Dict[str, Optional[float]]:
        if not runs_bucket:
            return {
                "brand_mentions": 0.0,
                "citation_rate": 0.0,
                "prominence_avg": 0.0,
                "zero_click": 0.0,
                "runs": 0,
            }

        total_runs = len(runs_bucket)
        brand_mentions = sum(run.brand_mention_count or 0 for run in runs_bucket)
        
        # Citation rate: percentage of runs with OUR brand citations
        # This is more accurate for brand presence analysis
        citation_rate = (sum(1 for run in runs_bucket if (run.our_citations_count or 0) > 0) / total_runs) * 100
        
        prominence_scores = [run.brand_prominence_score for run in runs_bucket if run.brand_prominence_score is not None]
        prominence_avg = sum(prominence_scores) / len(prominence_scores) if prominence_scores else 0.0
        # Use zero_click_presence (LLM metric) instead of ia_resources_detected (SERP metric)
        zero_click_scores = [run.zero_click_presence for run in runs_bucket if run.zero_click_presence is not None]
        zero_click = sum(zero_click_scores) / len(zero_click_scores) if zero_click_scores else 0.0

        return {
            "brand_mentions": float(brand_mentions),
            "citation_rate": round(citation_rate, 1),
            "prominence_avg": round(prominence_avg, 1),
            "zero_click": round(zero_click, 1),
            "runs": total_runs,
        }

    def _pct_change(current: float, previous: float) -> Optional[float]:
        if previous in (None, 0):
            return None
        return round(((current - previous) / previous) * 100, 1)

    def _point_change(current: float, previous: float) -> Optional[float]:
        if previous is None:
            return None
        return round(current - previous, 1)

    current_metrics = _aggregate(current_runs or sorted_runs)
    previous_metrics = _aggregate(previous_runs)

    return [
        {
            "label": "Menções de Marca",
            "value": current_metrics["brand_mentions"],
            "unit": "total",
            "delta": _pct_change(current_metrics["brand_mentions"], previous_metrics["brand_mentions"]),
            "trend_direction": _trend_direction(current_metrics["brand_mentions"], previous_metrics["brand_mentions"]),
            "delta_unit": "percent",
        },
        {
            "label": "Taxa de Citação",
            "value": current_metrics["citation_rate"],
            "unit": "percent",
            "delta": _point_change(current_metrics["citation_rate"], previous_metrics["citation_rate"]),
            "trend_direction": _trend_direction(current_metrics["citation_rate"], previous_metrics["citation_rate"]),
            "delta_unit": "points",
        },
        {
            "label": "Índice de Proeminência",
            "value": current_metrics["prominence_avg"],
            "unit": "score",
            "delta": _pct_change(current_metrics["prominence_avg"], previous_metrics["prominence_avg"]),
            "trend_direction": _trend_direction(current_metrics["prominence_avg"], previous_metrics["prominence_avg"]),
            "delta_unit": "percent",
        },
        {
            "label": "Presença Zero-Click",
            "value": current_metrics["zero_click"],
            "unit": "percent",
            "delta": _point_change(current_metrics["zero_click"], previous_metrics["zero_click"]),
            "trend_direction": _trend_direction(current_metrics["zero_click"], previous_metrics["zero_click"]),
            "delta_unit": "points",
        },
    ]


def _compute_radar(runs: List[Run], bank_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Compute radar chart dimensions for LLM responses - simplified for GEO Dashboard."""

    # GEO Dashboard metrics (LLM-focused, not SERP)
    citation_rates = [r.citation_rate_observed for r in runs if r.citation_rate_observed is not None]
    engagement_scores = [r.engagement_score for r in runs if r.engagement_score is not None]
    conversion_scores = [r.conversion_potential_score for r in runs if r.conversion_potential_score is not None]
    authority_scores = [r.authority_score for r in runs if r.authority_score is not None]
    relevance_scores = [r.relevance_score for r in runs if r.relevance_score is not None]
    clarity_scores = [r.clarity_score for r in runs if r.clarity_score is not None]

    return [
        {
            "bank": "Agregado",
            "dimensions": [
                {"name": "Taxa de Citação", "value": sum(citation_rates) / len(citation_rates) if citation_rates else 0},
                {"name": "Engajamento", "value": sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0},
                {"name": "Conversão", "value": sum(conversion_scores) / len(conversion_scores) if conversion_scores else 0},
                {"name": "Autoridade", "value": sum(authority_scores) / len(authority_scores) if authority_scores else 0},
                {"name": "Relevância", "value": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0},
                {"name": "Clareza", "value": sum(clarity_scores) / len(clarity_scores) if clarity_scores else 0},
            ]
        }
    ]


def _compute_positioning(
    db: Session,
    run_ids: List[str],
    bank_ids: Optional[List[str]],
    our_domains: Set[str],
    our_label: str,
) -> Dict[str, Any]:
    """Compute brand ranking, share of voice and perception breakdown."""

    # Get all citations from runs
    citations = db.query(Citation).filter(Citation.run_id.in_(run_ids)).all()

    # Count mentions by domain
    domain_counts = Counter(c.domain for c in citations if c.domain)

    total_mentions = sum(domain_counts.values()) or 0
    our_mentions = 0
    competitor_mentions: Dict[str, int] = {}

    for domain, count in domain_counts.items():
        if _domain_matches(domain, our_domains):
            our_mentions += count
        else:
            competitor_mentions[domain] = competitor_mentions.get(domain, 0) + count

    share_of_voice: Dict[str, float] = {}
    if total_mentions > 0:
        if our_mentions:
            label = our_label.strip() or "Nossa marca"
            share_of_voice[label] = round((our_mentions / total_mentions) * 100, 2)

        # Ordenar concorrentes por menções e limitar para manter visual limpo
        sorted_competitors = sorted(competitor_mentions.items(), key=lambda item: item[1], reverse=True)
        other_total = 0
        for domain, count in sorted_competitors[:6]:
            share_of_voice[domain] = round((count / total_mentions) * 100, 2)
        if len(sorted_competitors) > 6:
            other_total = sum(count for _, count in sorted_competitors[6:])
        if other_total:
            share_of_voice["Outros"] = round((other_total / total_mentions) * 100, 2)

    # Build ranking table
    brand_ranking = [
        {"rank": i + 1, "brand": domain, "mentions": count, "sample_url": next((c.url for c in citations if c.domain == domain and c.url), None)}
        for i, (domain, count) in enumerate(domain_counts.most_common(20))
    ]

    # Perception breakdown (placeholder - needs more sophisticated analysis)
    perception_breakdown = []

    return {
        "brand_ranking": brand_ranking,
        "perception_breakdown": perception_breakdown,
        "share_of_voice": share_of_voice,
        "total_mentions": total_mentions,
    }


def _compute_geo_timeline_and_summary(runs: List[Run]) -> tuple[list[Dict[str, Any]], Dict[str, Any]]:
    """Aggregate GEO timeline (daily) and summary metrics."""

    timeline_map: Dict[date, Dict[str, Any]] = defaultdict(lambda: {
        "mention_sum": 0,
        "mention_counts": 0,
        "first_sum": 0.0,
        "first_counts": 0,
        "density_sum": 0.0,
        "density_counts": 0,
        "engagement_sum": 0.0,
        "engagement_counts": 0,
        "conversion_sum": 0.0,
        "conversion_counts": 0,
        "citation_rate_observed_sum": 0.0,
        "citation_rate_observed_counts": 0,
        "citation_rate_corrected_sum": 0.0,
        "citation_rate_corrected_counts": 0,
    })

    density_values: List[float] = []
    first_values: List[float] = []
    trigger_values: List[float] = []
    engagement_values: List[float] = []
    conversion_scores: List[float] = []
    conversion_labels: List[str] = []
    competitor_ratios: List[float] = []
    runs_with_cocitation = 0
    perceived_value_categories: List[str] = []

    total_runs = len(runs)

    for run in runs:
        ts = run.started_at or run.finished_at
        if not ts:
            continue

        run_date = ts.date()

        if run.brand_mention_density is not None:
            density_values.append(run.brand_mention_density)
        if run.brand_first_mention_position is not None:
            first_values.append(run.brand_first_mention_position)
        if run.conversational_trigger_count is not None:
            trigger_values.append(float(run.conversational_trigger_count))
        if run.engagement_score is not None:
            engagement_values.append(run.engagement_score)
        if run.conversion_potential_score is not None:
            conversion_scores.append(run.conversion_potential_score)
        if run.conversion_potential:
            conversion_labels.append(run.conversion_potential)
        if run.competitor_mention_ratio is not None:
            competitor_ratios.append(run.competitor_mention_ratio)
        if run.perceived_value_category:
            perceived_value_categories.append(run.perceived_value_category)

        if run.cocitation_competitors:
            try:
                competitors_payload = json.loads(run.cocitation_competitors)
                if isinstance(competitors_payload, list) and competitors_payload:
                    runs_with_cocitation += 1
            except json.JSONDecodeError:
                pass

        if run_date is None:
            continue

        entry = timeline_map[run_date]

        if run.brand_mention_count is not None:
            entry["mention_sum"] += run.brand_mention_count
            entry["mention_counts"] += 1

        if run.brand_first_mention_position is not None:
            entry["first_sum"] += float(run.brand_first_mention_position)
            entry["first_counts"] += 1

        if run.brand_mention_density is not None:
            entry["density_sum"] += run.brand_mention_density
            entry["density_counts"] += 1

        if run.engagement_score is not None:
            entry["engagement_sum"] += run.engagement_score
            entry["engagement_counts"] += 1

        if run.conversion_potential_score is not None:
            entry["conversion_sum"] += run.conversion_potential_score
            entry["conversion_counts"] += 1

        if run.citation_rate_observed is not None:
            entry["citation_rate_observed_sum"] += run.citation_rate_observed
            entry["citation_rate_observed_counts"] += 1

        if run.citation_rate_corrected is not None:
            entry["citation_rate_corrected_sum"] += run.citation_rate_corrected
            entry["citation_rate_corrected_counts"] += 1

    timeline: List[Dict[str, Any]] = []
    for day in sorted(timeline_map.keys()):
        entry = timeline_map[day]
        # Calculate median for first mention position per day (more robust to outliers)
        day_first_positions = [r.brand_first_mention_position for r in runs if r.started_at and r.started_at.date() == day and r.brand_first_mention_position is not None]
        first_mention_median = round(statistics.median(day_first_positions), 2) if day_first_positions else None
        
        timeline.append({
            "date": day.isoformat(),
            "brand_mention_count": entry["mention_sum"],
            "brand_first_mention_position_avg": first_mention_median,
            "brand_mention_density_avg": _safe_avg(entry["density_sum"], entry["density_counts"]),
            "engagement_score_avg": _safe_avg(entry["engagement_sum"], entry["engagement_counts"]),
            "conversion_potential_score_avg": _safe_avg(entry["conversion_sum"], entry["conversion_counts"]),
            "citation_rate_observed_avg": _safe_avg(entry["citation_rate_observed_sum"], entry["citation_rate_observed_counts"]),
            "citation_rate_corrected_avg": _safe_avg(entry["citation_rate_corrected_sum"], entry["citation_rate_corrected_counts"]),
        })

    # Aggregate perceived value categories
    perceived_value_agg = []
    if perceived_value_categories:
        category_counts = Counter(perceived_value_categories)
        total_categorized = sum(category_counts.values())
        perceived_value_agg = [
            {
                "label": category,
                "value": count,
                "percentage": round((count / total_categorized) * 100, 1)
            }
            for category, count in category_counts.most_common()
        ]
        print(f"[DEBUG] perceived_value_categories: {perceived_value_agg}")
    
    geo_summary = {
        "total_runs": total_runs,
        "brand_mention_density_avg": _safe_avg(sum(density_values), len(density_values)),
        "brand_first_mention_position_avg": round(statistics.median(first_values), 2) if first_values else None,
        "conversational_trigger_avg": _safe_avg(sum(trigger_values), len(trigger_values)),
        "engagement_score_avg": _safe_avg(sum(engagement_values), len(engagement_values)),
        "conversion_potential_score_avg": _safe_avg(sum(conversion_scores), len(conversion_scores)),
        "top_conversion_potential": _most_common(conversion_labels),
        "competitor_mention_ratio_avg": _safe_avg(sum(competitor_ratios), len(competitor_ratios)),
        "cocitation_percentage": round((runs_with_cocitation / total_runs) * 100, 2) if total_runs else 0.0,
        "perceived_value_categories": perceived_value_agg if perceived_value_agg else None,
    }

    return timeline, geo_summary


def _safe_avg(sum_value: float, count: int) -> Optional[float]:
    if not count:
        return None
    return round(sum_value / count, 2)


def _most_common(values: List[str]) -> Optional[str]:
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _aggregate_semantic_scores(db: Session, run_ids: List[str]) -> Optional[Dict[str, float]]:
    """
    Aggregate semantic scores from RunSemanticInsight for all runs.

    Returns averaged scores for: authority, relevance, clarity, context, precision, freshness.
    """
    insights = db.query(RunSemanticInsight).filter(
        RunSemanticInsight.run_id.in_(run_ids)
    ).all()

    if not insights:
        return None

    # Collect all semantic scores
    scores_by_dimension: Dict[str, List[float]] = {
        "authority": [],
        "relevance": [],
        "clarity": [],
        "context": [],
        "precision": [],
        "freshness": [],
    }

    for insight in insights:
        payload = insight.payload or {}
        semantic_scores = payload.get("semantic_scores", {})

        if not semantic_scores:
            continue

        for dimension, score in semantic_scores.items():
            if dimension in scores_by_dimension and score is not None:
                scores_by_dimension[dimension].append(float(score))

    # Calculate averages
    aggregated_scores = {}
    for dimension, scores in scores_by_dimension.items():
        if scores:
            aggregated_scores[dimension] = round(sum(scores) / len(scores), 1)
        else:
            aggregated_scores[dimension] = 0

    # Only return if we have at least some scores
    if any(score > 0 for score in aggregated_scores.values()):
        return aggregated_scores

    return None


def _extract_keywords_from_text(text: str, top_n: int = 50) -> List[Dict[str, Any]]:
    """Extract meaningful keywords from text, removing stopwords and common words."""
    import re

    # Stopwords em português
    stopwords = {
        'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não',
        'uma', 'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi',
        'ao', 'ele', 'das', 'tem', 'à', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito',
        'há', 'nos', 'já', 'está', 'eu', 'também', 'só', 'pelo', 'pela', 'até', 'isso',
        'ela', 'entre', 'era', 'depois', 'sem', 'mesmo', 'aos', 'ter', 'seus', 'quem',
        'nas', 'me', 'esse', 'eles', 'estão', 'você', 'tinha', 'foram', 'essa', 'num',
        'nem', 'suas', 'meu', 'às', 'minha', 'têm', 'numa', 'pelos', 'elas', 'havia',
        'seja', 'qual', 'será', 'nós', 'tenho', 'lhe', 'deles', 'essas', 'esses', 'pelas',
        'este', 'fosse', 'dele', 'tu', 'te', 'vocês', 'vos', 'lhes', 'meus', 'minhas',
        'teu', 'tua', 'teus', 'tuas', 'nosso', 'nossa', 'nossos', 'nossas', 'dela', 'delas',
        'esta', 'estes', 'estas', 'aquele', 'aquela', 'aqueles', 'aquelas', 'isto', 'aquilo',
        'estou', 'está', 'estamos', 'estão', 'estive', 'esteve', 'estivemos', 'estiveram',
        'estava', 'estávamos', 'estavam', 'estivera', 'estivéramos', 'seja', 'sejamos',
        'sejam', 'fosse', 'fôssemos', 'fossem', 'for', 'formos', 'forem', 'sou', 'somos',
        'são', 'era', 'éramos', 'eram', 'fui', 'foi', 'fomos', 'foram', 'fora', 'fôramos',
        'ser', 'ter', 'sobre', 'pode', 'fazer', 'cada', 'ano', 'anos', 'dia', 'dias', 'vez',
        'vezes', 'ainda', 'onde', 'porque', 'então', 'assim', 'bem', 'toda', 'todo', 'todos',
        'todas', 'outro', 'outra', 'outros', 'outras', 'etc'
    }

    # Limpar e tokenizar
    text = text.lower()
    # Remover URLs, markdown, símbolos
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)

    # Extrair palavras (mínimo 3 caracteres)
    words = [w.strip() for w in text.split() if len(w.strip()) >= 3]

    # Remover stopwords
    words = [w for w in words if w not in stopwords]

    # Contar frequências
    word_counts = Counter(words)

    # Retornar top N
    return [
        {"text": word, "frequency": count, "weight": min(100, count * 3)}
        for word, count in word_counts.most_common(top_n)
    ]


def _compute_keywords_entities(db: Session, run_ids: List[str]) -> Dict[str, Any]:
    """Compute word cloud and entity mapping from Gemini semantic insights (preferred) or fallback."""
    from app.models.models import RunSemanticInsight

    # PRIORIDADE 1: Usar semantic insights do Gemini quando disponível
    semantic_insights = db.query(RunSemanticInsight).filter(
        RunSemanticInsight.run_id.in_(run_ids)
    ).all()

    if semantic_insights:
        # Agregar keywords e entities de todos os semantic insights
        all_keywords = []
        all_entities = []

        for insight in semantic_insights:
            payload = insight.payload or {}
            all_keywords.extend(payload.get("keywords", []))
            all_entities.extend(payload.get("entities", []))

        # Build word cloud from Gemini keywords
        keyword_counts = Counter()
        for kw in all_keywords:
            token = kw.get("token") or kw.get("keyword")
            if token:
                keyword_counts[token] += 1

        word_cloud = [
            {"text": word, "frequency": count, "weight": min(100, count * 5)}
            for word, count in keyword_counts.most_common(50)
        ]

        # Build entities from Gemini entities
        entity_by_name = defaultdict(lambda: {"mentions": 0, "categories": set(), "runs": set()})

        for ent in all_entities:
            name = ent.get("name")
            if name:
                entity_by_name[name]["mentions"] += 1
                category = ent.get("category") or ent.get("type")
                if category:
                    entity_by_name[name]["categories"].add(category)
                # Assumir que veio de um run_id (não temos no payload, mas podemos inferir)

        entity_table = [
            {
                "entity": name,
                "type": ", ".join(sorted(data["categories"])),
                "mentions": data["mentions"],
                "runs": len(semantic_insights),  # Aproximação
            }
            for name, data in sorted(entity_by_name.items(), key=lambda x: x[1]["mentions"], reverse=True)
        ][:30]

        # Se word cloud ficou vazio, usar fallback
        if not word_cloud:
            runs = db.query(Run).filter(Run.id.in_(run_ids)).all()
            all_text = " ".join([r.response_text for r in runs if r.response_text])
            word_cloud = _extract_keywords_from_text(all_text, top_n=50)

        return {
            "word_cloud": word_cloud,
            "entities": entity_table,
        }

    # PRIORIDADE 2: Usar tabela Entity se disponível
    entities = db.query(Entity).filter(Entity.run_id.in_(run_ids)).all()

    if entities:
        # Build word cloud from entity names
        entity_names = [e.name for e in entities]
        word_counts = Counter(entity_names)

        word_cloud = [
            {"text": word, "frequency": count, "weight": min(100, count * 10)}
            for word, count in word_counts.most_common(50)
        ]

        # Entity table
        entity_by_name = defaultdict(lambda: {"mentions": 0, "types": set(), "runs": set()})

        for e in entities:
            entity_by_name[e.name]["mentions"] += e.mentions_count
            entity_by_name[e.name]["types"].add(e.entity_type)
            entity_by_name[e.name]["runs"].add(e.run_id)

        entity_table = [
            {
                "entity": name,
                "type": ", ".join(data["types"]),
                "mentions": data["mentions"],
                "runs": len(data["runs"]),
            }
            for name, data in sorted(entity_by_name.items(), key=lambda x: x[1]["mentions"], reverse=True)
        ][:30]

        return {
            "word_cloud": word_cloud,
            "entities": entity_table,
        }

    # FALLBACK: Extrair manualmente do texto das runs
    runs = db.query(Run).filter(Run.id.in_(run_ids)).all()

    # Concatenate all response texts
    all_text = " ".join([r.response_text for r in runs if r.response_text])

    # Extract keywords
    word_cloud = _extract_keywords_from_text(all_text, top_n=50)

    # For entities, use domains as clean entity names
    citations = db.query(Citation).filter(Citation.run_id.in_(run_ids)).all()

    # Build entities from domains
    entity_by_domain = defaultdict(lambda: {"mentions": 0, "types": set(), "runs": set()})

    for c in citations:
        if c.domain:
            entity_by_domain[c.domain]["mentions"] += 1
            entity_by_domain[c.domain]["types"].add(c.type or "citation")
            entity_by_domain[c.domain]["runs"].add(c.run_id)

    entity_table = [
        {
            "entity": domain,
            "type": ", ".join(sorted(data["types"])),
            "mentions": data["mentions"],
            "runs": len(data["runs"]),
        }
        for domain, data in sorted(entity_by_domain.items(), key=lambda x: x[1]["mentions"], reverse=True)
    ][:30]

    return {
        "word_cloud": word_cloud,
        "entities": entity_table,
    }


def _compute_panorama(db: Session, run_ids: List[str], runs: List[Run]) -> Dict[str, Any]:
    """Compute panorama cards - LLM metrics only (no SERP features)."""

    # LLM-specific metrics
    avg_citation_rate = sum(r.citation_rate_observed or 0 for r in runs) / len(runs) if runs else 0
    avg_engagement = sum(r.engagement_score or 0 for r in runs) / len(runs) if runs else 0
    avg_conversion = sum(r.conversion_potential_score or 0 for r in runs) / len(runs) if runs else 0
    
    # Count citations
    total_citations = sum(r.citations_count or 0 for r in runs)
    our_citations = sum(r.our_citations_count or 0 for r in runs)

    cards = [
        {"label": "Total Runs", "value": len(runs)},
        {"label": "Taxa de Citação Média", "value": round(avg_citation_rate, 1), "unit": "%"},
        {"label": "Total de Citações", "value": total_citations},
        {"label": "Nossas Citações", "value": our_citations},
        {"label": "Engajamento Médio", "value": round(avg_engagement, 1)},
        {"label": "Conversão Média", "value": round(avg_conversion, 1)},
    ]

    # Chart data by LLM model
    chart = []
    models = {}
    for run in runs:
        model = run.model_name or "Unknown"
        if model not in models:
            models[model] = {"runs": 0, "citations": 0, "our_citations": 0}
        models[model]["runs"] += 1
        models[model]["citations"] += run.citations_count or 0
        models[model]["our_citations"] += run.our_citations_count or 0
    
    for model, data in models.items():
        chart.append({
            "model": model,
            "runs": data["runs"],
            "citations": data["citations"],
            "our_citations": data["our_citations"],
            "citation_rate": round((data["our_citations"] / data["citations"] * 100) if data["citations"] > 0 else 0, 1)
        })

    return {
        "cards": cards,
        "chart": chart,
    }


def _compute_web_structure(db: Session, run_ids: List[str], bank_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Compute web structure checklist from Citations, aggregating by official bank domains."""
    from app.models.models import UrlMetadata

    # Get citations (URLs from AI Overview responses)
    citations = db.query(Citation).filter(Citation.run_id.in_(run_ids)).all()
    
    # Get all crawled metadata for these URLs
    citation_urls = [c.url for c in citations if c.url]
    url_metadata_map = {}
    if citation_urls:
        # SQL Server has a limit of ~2100 parameters, so batch the queries
        batch_size = 2000
        url_metadata_list = []
        for i in range(0, len(citation_urls), batch_size):
            batch = citation_urls[i:i + batch_size]
            batch_results = db.query(UrlMetadata).filter(
                UrlMetadata.url.in_(batch),
                UrlMetadata.status == "success"
            ).all()
            url_metadata_list.extend(batch_results)
        url_metadata_map = {m.url: m for m in url_metadata_list}

    aggregated: Dict[str, Dict[str, Any]] = {}

    allowed_domains_input = {
        normalize_domain(d)
        for d in (bank_ids or [])
        if d
    }
    
    urls_processed = 0
    urls_filtered = 0

    for citation in citations:
        url = citation.url
        if not url:
            continue
        
        urls_processed += 1

        parsed_url = urlparse(url)
        if not parsed_url.netloc:
            continue

        normalized_domain = normalize_domain(parsed_url.netloc)

        # Filter only official bank domains (including optional bank_ids override)
        is_allowed = False
        if allowed_domains_input:
            for allowed in allowed_domains_input:
                if normalized_domain == allowed or normalized_domain.endswith("." + allowed):
                    is_allowed = True
                    break
        else:
            is_allowed = _is_official_bank_domain(normalized_domain)

        if not is_allowed:
            urls_filtered += 1
            if urls_filtered <= 5:  # Log first 5 filtered domains
                print(f"[DEBUG] Filtered domain: {normalized_domain}")
            continue

        # Check if we have crawled metadata for this URL
        url_metadata = url_metadata_map.get(url)
        
        # Extract metadata from crawled data or fallback to citation
        if url_metadata:
            title_text = url_metadata.title or citation.anchor or ""
            meta_desc_text = url_metadata.meta_description or ""
            keywords_text = url_metadata.meta_keywords or ""
            robots_text = url_metadata.meta_robots or ""
            og_tags = url_metadata.og_tags or {}
            
            # AI Ready detection from crawled data
            ai_ready_types = []
            if url_metadata.has_lists:
                ai_ready_types.append("Lista")
            if url_metadata.has_faq_schema:
                ai_ready_types.append("FAQ")
            if url_metadata.has_tables:
                ai_ready_types.append("Tabela")
            if url_metadata.has_structured_data:
                ai_ready_types.append("Schema.org")
        else:
            # Fallback to citation data only
            title_text = citation.anchor or ""
            meta_desc_text = ""
            keywords_text = ""
            robots_text = ""
            og_tags = {}
            ai_ready_types = []

        has_title = bool(title_text)
        has_meta_desc = bool(meta_desc_text)
        has_keywords = bool(keywords_text)
        has_robots = bool(robots_text)
        has_og = bool(og_tags)
        has_ai_ready = bool(ai_ready_types)

        # Create entry for this domain
        entry = aggregated.setdefault(
            normalized_domain,
            {
                "domain": normalized_domain,
                "primary_url": url,
                "title": False,
                "meta_description": False,
                "keywords": False,
                "robots": False,
                "open_graph": False,
                "ai_ready_blocks": False,
                "details": {
                    "title_text": None,
                    "meta_desc_text": None,
                    "keywords": [],
                    "robots": None,
                    "open_graph": {},
                    "ai_ready_types": [],
                    "sample_urls": set(),
                    "llms_txt": None,
                    "ai_txt": None,
                    "robots_txt_full": None,
                },
            },
        )

        # Update entry with metadata
        entry["title"] = entry["title"] or has_title
        entry["meta_description"] = entry["meta_description"] or has_meta_desc
        entry["keywords"] = entry["keywords"] or has_keywords
        entry["robots"] = entry["robots"] or has_robots
        entry["open_graph"] = entry["open_graph"] or has_og
        entry["ai_ready_blocks"] = entry["ai_ready_blocks"] or has_ai_ready
        
        details = entry["details"]
        details["sample_urls"].add(url)

        if has_title and not details["title_text"]:
            details["title_text"] = str(title_text)[:160]
        
        if has_meta_desc and not details["meta_desc_text"]:
            details["meta_desc_text"] = str(meta_desc_text)[:220]
        
        if has_keywords:
            keywords_list = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
            existing_keywords = set(details.get("keywords") or [])
            for kw in keywords_list:
                existing_keywords.add(kw)
            details["keywords"] = sorted(existing_keywords)
        
        if has_robots and not details["robots"]:
            details["robots"] = robots_text[:160]
        
        if has_og:
            stored_og = details.get("open_graph") or {}
            for key, value in og_tags.items():
                stored_og.setdefault(key, value)
            details["open_graph"] = stored_og
        
        if has_ai_ready:
            stored_types = set(details.get("ai_ready_types") or [])
            for tp in ai_ready_types:
                stored_types.add(tp)
            details["ai_ready_types"] = sorted(stored_types)
        
        # Store special files from crawled metadata
        if url_metadata:
            if url_metadata.llms_txt and not details["llms_txt"]:
                details["llms_txt"] = url_metadata.llms_txt
            if url_metadata.ai_txt and not details["ai_txt"]:
                details["ai_txt"] = url_metadata.ai_txt
            if url_metadata.robots_txt_full and not details["robots_txt_full"]:
                details["robots_txt_full"] = url_metadata.robots_txt_full

    # Prepare final list sorted by domain
    checklist = []
    
    # Debug: log aggregation results
    print(f"[DEBUG] _compute_web_structure: processed {urls_processed} URLs from {len(citations)} citations, filtered {urls_filtered}, aggregated {len(aggregated)} domains")
    
    for domain, data in aggregated.items():
        # Convert set of sample urls to sorted list and pick first as primary link reference
        sample_urls = sorted(data["details"].get("sample_urls", []))
        data["details"]["sample_urls"] = sample_urls
        if sample_urls:
            data["primary_url"] = sample_urls[0]

        og_dict = data["details"].get("open_graph") or {}
        data["details"]["open_graph_pairs"] = [
            {"property": key, "value": og_dict[key]}
            for key in sorted(og_dict.keys())
        ]

        # Indicar se domínio faz parte do conjunto filtrado manualmente
        data["matches_filter"] = bool(allowed_domains_input)

        checklist.append(data)

    checklist.sort(key=lambda item: item["domain"])
    
    print(f"[DEBUG] _compute_web_structure: returning {len(checklist)} items")
    if checklist:
        print(f"[DEBUG] First item keys: {list(checklist[0].keys())}")

    return checklist


def _compute_alerts(runs: List[Run]) -> List[Dict[str, Any]]:
    """Generate prioritized alerts (Crítico/Atenção/Oportunidade)."""

    alerts = []

    # Check for critical issues
    failed_runs = [r for r in runs if r.error_code]
    if len(failed_runs) > len(runs) * 0.1:  # More than 10% failed
        alerts.append({
            "severity": "critico",
            "title": "Alta Taxa de Falhas",
            "description": f"{len(failed_runs)} de {len(runs)} runs falharam ({round(len(failed_runs)/len(runs)*100, 1)}%)",
            "supporting_runs": [r.id for r in failed_runs[:5]],
        })

    # Check for attention items
    low_eeat_runs = [r for r in runs if r.eeat_score is not None and r.eeat_score < 50]
    if low_eeat_runs:
        alerts.append({
            "severity": "atencao",
            "title": "E-E-A-T Baixo Detectado",
            "description": f"{len(low_eeat_runs)} runs com score E-E-A-T abaixo de 50",
            "supporting_runs": [r.id for r in low_eeat_runs[:5]],
        })

    # Check for opportunities
    high_irzc_runs = [r for r in runs if r.irzc_score is not None and r.irzc_score > 70]
    if high_irzc_runs:
        alerts.append({
            "severity": "oportunidade",
            "title": "Alto Risco de Zero-Click",
            "description": f"{len(high_irzc_runs)} runs com IRZC > 70 - oportunidade de otimização",
            "supporting_runs": [r.id for r in high_irzc_runs[:5]],
        })

    # Good AI Ready presence
    good_ia_ready = [r for r in runs if r.ia_ready_score is not None and r.ia_ready_score > 80]
    if good_ia_ready:
        alerts.append({
            "severity": "oportunidade",
            "title": "Conteúdo IA-Ready Forte",
            "description": f"{len(good_ia_ready)} runs com score IA-Ready > 80",
            "supporting_runs": [r.id for r in good_ia_ready[:5]],
        })

    return alerts


def _compute_swot(runs: List[Run]) -> Dict[str, List[str]]:
    """Generate SWOT analysis from LLM metrics."""

    # Calculate LLM-specific averages
    avg_citation_rate = sum(r.citation_rate_observed or 0 for r in runs) / len(runs) if runs else 0
    avg_engagement = sum(r.engagement_score or 0 for r in runs) / len(runs) if runs else 0
    avg_conversion = sum(r.conversion_potential_score or 0 for r in runs) / len(runs) if runs else 0
    
    # Citation metrics
    total_citations = sum(r.citations_count or 0 for r in runs)
    our_citations = sum(r.our_citations_count or 0 for r in runs)
    citation_presence = (our_citations / total_citations * 100) if total_citations > 0 else 0

    strengths = []
    weaknesses = []
    opportunities = []
    threats = []

    # Strengths
    if avg_citation_rate >= 20:
        strengths.append(f"Boa taxa de citação ({round(avg_citation_rate, 1)}%)")
    if citation_presence >= 30:
        strengths.append(f"Presença forte nas citações ({round(citation_presence, 1)}%)")
    if avg_engagement >= 60:
        strengths.append(f"Alto engajamento nas respostas ({round(avg_engagement, 1)})")
    if avg_conversion >= 50:
        strengths.append(f"Bom potencial de conversão ({round(avg_conversion, 1)})")

    # Weaknesses
    if avg_citation_rate < 10:
        weaknesses.append(f"Taxa de citação baixa ({round(avg_citation_rate, 1)}%)")
    if citation_presence < 15:
        weaknesses.append(f"Presença fraca nas citações ({round(citation_presence, 1)}%)")
    if avg_engagement < 40:
        weaknesses.append(f"Engajamento baixo ({round(avg_engagement, 1)})")

    # Opportunities
    if avg_citation_rate < 30:
        opportunities.append("Potencial para aumentar presença em citações LLM")
    if avg_conversion < 60:
        opportunities.append("Oportunidade de otimizar conteúdo para conversão")

    # Threats
    if avg_citation_rate < 5:
        threats.append("Risco de invisibilidade em respostas de LLMs")
    if citation_presence < 10:
        threats.append("Competidores dominando as citações")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": threats,
    }


def _compute_cocitation_breakdown(db: Session, run_ids: List[str], our_domains: Set[str]) -> List[Dict[str, Any]]:
    """
    Compute co-citation breakdown by competitor.
    
    Returns list of competitors with their co-citation rates.
    """
    runs = db.query(Run).filter(Run.id.in_(run_ids)).all()
    
    competitor_cocitations: Dict[str, int] = Counter()
    total_runs_with_cocitation = 0
    
    for run in runs:
        if not run.cocitation_competitors:
            continue
            
        try:
            competitors = json.loads(run.cocitation_competitors)
            if isinstance(competitors, list) and competitors:
                total_runs_with_cocitation += 1
                for competitor in competitors:
                    if isinstance(competitor, dict):
                        name = competitor.get("name") or competitor.get("domain")
                    else:
                        name = str(competitor)
                    
                    if name:
                        competitor_cocitations[name] += 1
        except (json.JSONDecodeError, TypeError):
            continue
    
    # Calculate percentages and sort
    breakdown = []
    for competitor, count in competitor_cocitations.most_common(10):
        percentage = (count / len(run_ids)) * 100 if run_ids else 0
        breakdown.append({
            "name": competitor,
            "cocitation_count": count,
            "cocitation_rate": round(percentage, 1),
        })
    
    return breakdown


def _compute_context_insights(runs: List[Run]) -> Dict[str, Any]:
    """
    Generate context-based insights from runs.
    
    Analyzes performance by theme, category, and question type.
    """
    # Group by question type
    by_question_type: Dict[str, List[Run]] = defaultdict(list)
    for run in runs:
        qtype = run.question_type or "outros"
        by_question_type[qtype].append(run)
    
    # Group by product category
    by_category: Dict[str, List[Run]] = defaultdict(list)
    for run in runs:
        cat = run.product_category or "geral"
        by_category[cat].append(run)
    
    # Calculate performance by context
    context_performance = []
    
    for qtype, qtype_runs in by_question_type.items():
        if not qtype_runs:
            continue
            
        brand_mentions = sum(r.brand_mention_count or 0 for r in qtype_runs)
        avg_engagement = sum(r.engagement_score or 0 for r in qtype_runs if r.engagement_score) / len([r for r in qtype_runs if r.engagement_score]) if any(r.engagement_score for r in qtype_runs) else 0
        
        context_performance.append({
            "context": qtype,
            "type": "question_type",
            "runs_count": len(qtype_runs),
            "brand_mentions": brand_mentions,
            "avg_engagement": round(avg_engagement, 1),
        })
    
    for cat, cat_runs in by_category.items():
        if not cat_runs or cat == "geral":
            continue
            
        brand_mentions = sum(r.brand_mention_count or 0 for r in cat_runs)
        avg_engagement = sum(r.engagement_score or 0 for r in cat_runs if r.engagement_score) / len([r for r in cat_runs if r.engagement_score]) if any(r.engagement_score for r in cat_runs) else 0
        
        context_performance.append({
            "context": cat,
            "type": "category",
            "runs_count": len(cat_runs),
            "brand_mentions": brand_mentions,
            "avg_engagement": round(avg_engagement, 1),
        })
    
    # Sort by brand mentions descending
    context_performance.sort(key=lambda x: x["brand_mentions"], reverse=True)
    
    return {
        "performance_by_context": context_performance[:10],
        "total_contexts": len(by_question_type) + len([c for c in by_category.keys() if c != "geral"]),
    }


def _compute_exclusive_citations(runs: List[Run], our_domains: Set[str]) -> int:
    """
    Count runs where ONLY our brand was cited (no competitors).
    
    A run has exclusive citation if:
    - It has at least one citation from our domains
    - It has no co-citations with competitors
    """
    exclusive_count = 0
    
    for run in runs:
        # Check if run has our citations
        if not run.our_citations_count or run.our_citations_count == 0:
            continue
        
        # Check if run has co-citations
        has_cocitation = False
        if run.cocitation_competitors:
            try:
                competitors = json.loads(run.cocitation_competitors)
                if isinstance(competitors, list) and competitors:
                    has_cocitation = True
            except (json.JSONDecodeError, TypeError):
                pass
        
        # If has our citations but no co-citations, it's exclusive
        if not has_cocitation:
            exclusive_count += 1
    
    return exclusive_count


def _get_raw_samples(db: Session, run_ids: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """Get raw analysis samples for transparency."""

    runs = db.query(Run).filter(Run.id.in_(run_ids)).order_by(Run.started_at.desc()).limit(limit).all()

    samples = []
    for r in runs:
        samples.append({
            "run_id": r.id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "engine": r.engine_id,
            "status": r.status,
            "im_seo_score": r.im_seo_score,
            "eeat_score": r.eeat_score,
            "citations_count": r.citations_count,
            "response_snippet": r.response_text[:200] if r.response_text else None,
        })

    return samples
