"""
Analytics API Routes - Métricas agregadas e dashboard.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from collections import Counter, defaultdict

from app.db.session import SessionLocal
from app.models.models import Run, Project, Engine, SubProject, Prompt, PromptVersion, RunSemanticInsight

router = APIRouter(tags=["analytics"])


def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/im-overview")
def get_im_overview(
    project_id: Optional[str] = None,
    engine_ids: Optional[str] = None,  # Comma-separated IDs
    days: int = Query(30, ge=1, le=365),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    im_seo_min: Optional[float] = None,
    im_seo_max: Optional[float] = None,
    im_seoia_min: Optional[float] = None,
    im_seoia_max: Optional[float] = None,
    subproject_id: Optional[str] = None,
    prompt_id: Optional[str] = None,
    run_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna visão geral das métricas IM-SEO/IM-SEOIA.
    
    Inclui:
    - Médias de todas as métricas
    - Tendências (comparação com período anterior)
    - Distribuição de scores
    """
    # Data de corte
    if start_date and end_date:
        cutoff_date = datetime.fromisoformat(start_date)
        end_date_obj = datetime.fromisoformat(end_date)
    else:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        end_date_obj = datetime.utcnow()
    
    # Query base
    query = db.query(Run).filter(
        Run.status == "completed",
        Run.started_at >= cutoff_date,
        Run.started_at <= end_date_obj
    )
    
    # Filtros
    engine_id_list: List[str] = []

    if project_id:
        query = query.filter(Run.project_id == project_id)

    if engine_ids:
        engine_id_list = [engine_id.strip() for engine_id in engine_ids.split(',') if engine_id.strip()]
        if engine_id_list:
            query = query.filter(Run.engine_id.in_(engine_id_list))
    
    if im_seo_min is not None:
        query = query.filter(Run.im_seo_score >= im_seo_min)
    if im_seo_max is not None:
        query = query.filter(Run.im_seo_score <= im_seo_max)
    
    if im_seoia_min is not None:
        query = query.filter(Run.im_seoia_score >= im_seoia_min)
    if im_seoia_max is not None:
        query = query.filter(Run.im_seoia_score <= im_seoia_max)

    if subproject_id:
        query = query.filter(Run.subproject_id == subproject_id)

    if prompt_id:
        query = query.join(PromptVersion, Run.prompt_version_id == PromptVersion.id)
        query = query.filter(PromptVersion.prompt_id == prompt_id)

    if run_id:
        query = query.filter(Run.id == run_id)
    
    runs = query.all()
    
    if not runs:
        return {
            "total_runs": 0,
            "metrics": {},
            "trends": {},
            "distribution": {},
            "multidimensional": {"dimensions": []},
            "index_comparison": {"series": [], "delta": None},
            "insights": [],
            "semantic": _empty_semantic_snapshot(),
        }
    
    # Calcular médias
    def safe_avg(values):
        filtered = [v for v in values if v is not None]
        return round(sum(filtered) / len(filtered), 2) if filtered else None
    
    metrics = {
        "im_seo": {
            "average": safe_avg([r.im_seo_score for r in runs]),
            "min": min([r.im_seo_score for r in runs if r.im_seo_score is not None], default=None),
            "max": max([r.im_seo_score for r in runs if r.im_seo_score is not None], default=None),
        },
        "im_seoia": {
            "average": safe_avg([r.im_seoia_score for r in runs]),
            "min": min([r.im_seoia_score for r in runs if r.im_seoia_score is not None], default=None),
            "max": max([r.im_seoia_score for r in runs if r.im_seoia_score is not None], default=None),
        },
        "eeat": {
            "average": safe_avg([r.eeat_score for r in runs]),
            "min": min([r.eeat_score for r in runs if r.eeat_score is not None], default=None),
            "max": max([r.eeat_score for r in runs if r.eeat_score is not None], default=None),
            "expertise": safe_avg([r.eeat_expertise for r in runs]),
            "experience": safe_avg([r.eeat_experience for r in runs]),
            "authoritativeness": safe_avg([r.eeat_authoritativeness for r in runs]),
            "trustworthiness": safe_avg([r.eeat_trustworthiness for r in runs]),
        },
        "core_web_vitals": {
            "average": safe_avg([r.core_web_vitals_score for r in runs]),
            "lcp": safe_avg([r.lcp_score for r in runs]),
            "fid": safe_avg([r.fid_score for r in runs]),
            "cls": safe_avg([r.cls_score for r in runs]),
        },
        "irzc": {
            "average": safe_avg([r.irzc_score for r in runs]),
            "min": min([r.irzc_score for r in runs if r.irzc_score is not None], default=None),
            "max": max([r.irzc_score for r in runs if r.irzc_score is not None], default=None),
            "ctr_real_avg": safe_avg([r.ctr_real for r in runs]),
            "ctr_expected_avg": safe_avg([r.ctr_expected for r in runs]),
        },
        "serp": {
            "share_of_voice_avg": safe_avg([r.share_of_voice_serp for r in runs]),
            "serp_features_avg": safe_avg([r.serp_features_presence for r in runs]),
            "organic_position_avg": safe_avg([getattr(r, 'organic_position', None) for r in runs]),
        },
        "ia_ready": {
            "average": safe_avg([r.ia_ready_score for r in runs]),
            "blocks_avg": safe_avg([r.ia_ready_blocks_count for r in runs]),
            "has_lists_pct": len([r for r in runs if r.has_lists]) / len(runs) * 100,
            "has_faqs_pct": len([r for r in runs if r.has_faqs]) / len(runs) * 100,
            "has_tables_pct": len([r for r in runs if r.has_tables]) / len(runs) * 100,
        }
    }
    
    # Calcular tendências (comparar com período anterior)
    previous_cutoff = cutoff_date - timedelta(days=days)
    previous_runs = db.query(Run).filter(
        Run.status == "completed",
        Run.started_at >= previous_cutoff,
        Run.started_at < cutoff_date
    )
    
    if project_id:
        previous_runs = previous_runs.filter(Run.project_id == project_id)

    if engine_id_list:
        previous_runs = previous_runs.filter(Run.engine_id.in_(engine_id_list))

    if im_seo_min is not None:
        previous_runs = previous_runs.filter(Run.im_seo_score >= im_seo_min)
    if im_seo_max is not None:
        previous_runs = previous_runs.filter(Run.im_seo_score <= im_seo_max)

    if im_seoia_min is not None:
        previous_runs = previous_runs.filter(Run.im_seoia_score >= im_seoia_min)
    if im_seoia_max is not None:
        previous_runs = previous_runs.filter(Run.im_seoia_score <= im_seoia_max)

    if subproject_id:
        previous_runs = previous_runs.filter(Run.subproject_id == subproject_id)

    if prompt_id:
        previous_runs = previous_runs.join(PromptVersion, Run.prompt_version_id == PromptVersion.id)
        previous_runs = previous_runs.filter(PromptVersion.prompt_id == prompt_id)

    if run_id:
        previous_runs = previous_runs.filter(Run.id == run_id)

    previous_runs = previous_runs.all()
    
    def calc_trend(current, previous_list):
        if not previous_list:
            return None
        prev_avg = safe_avg(previous_list)
        if prev_avg is None or current is None:
            return None
        return round(((current - prev_avg) / prev_avg) * 100, 2)
    
    trends = {
        "im_seo": calc_trend(
            metrics["im_seo"]["average"],
            [r.im_seo_score for r in previous_runs]
        ),
        "im_seoia": calc_trend(
            metrics["im_seoia"]["average"],
            [r.im_seoia_score for r in previous_runs]
        ),
        "eeat": calc_trend(
            metrics["eeat"]["average"],
            [r.eeat_score for r in previous_runs]
        ),
        "irzc": calc_trend(
            metrics["irzc"]["average"],
            [r.irzc_score for r in previous_runs]
        ),
    }
    
    # Distribuição de scores
    def get_distribution(scores, ranges):
        distribution = {}
        for label, (min_val, max_val) in ranges.items():
            count = len([s for s in scores if s is not None and min_val <= s < max_val])
            distribution[label] = count
        return distribution
    
    im_seo_scores = [r.im_seo_score for r in runs if r.im_seo_score is not None]
    
    distribution = {
        "im_seo": get_distribution(im_seo_scores, {
            "excellent (80-100)": (80, 101),
            "good (60-79)": (60, 80),
            "fair (40-59)": (40, 60),
            "poor (0-39)": (0, 40),
        })
    }
    
    def normalize(value: Optional[float]) -> float:
        return round(float(value), 2) if value is not None else 0.0

    multidimensional = {
        "dimensions": [
            {"label": "IM-SEO", "value": normalize(metrics["im_seo"].get("average"))},
            {"label": "IM-SEOIA", "value": normalize(metrics["im_seoia"].get("average"))},
            {"label": "E-E-A-T", "value": normalize(metrics["eeat"].get("average"))},
            {"label": "Core Web Vitals", "value": normalize(metrics["core_web_vitals"].get("average"))},
            {"label": "IA Ready", "value": normalize(metrics["ia_ready"].get("average"))},
            {"label": "IRZC", "value": normalize(metrics["irzc"].get("average"))},
        ]
    }

    index_comparison = {
        "series": [
            {"label": "IM-SEO", "value": metrics["im_seo"].get("average")},
            {"label": "IM-SEOIA", "value": metrics["im_seoia"].get("average")},
            {"label": "E-E-A-T", "value": metrics["eeat"].get("average")},
        ],
        "delta": None,
    }

    if metrics["im_seo"].get("average") is not None and metrics["im_seoia"].get("average") is not None:
        index_comparison["delta"] = round(metrics["im_seoia"]["average"] - metrics["im_seo"]["average"], 2)

    insights: List[dict] = []

    def add_insight(title: str, description: str, severity: str = "info") -> None:
        insights.append(
            {
                "title": title,
                "description": description,
                "severity": severity,
            }
        )

    def fmt(value: Optional[float]) -> str:
        return f"{value:.1f}" if value is not None else "N/A"

    im_seo_avg = metrics["im_seo"].get("average")
    im_seoia_avg = metrics["im_seoia"].get("average")
    eeat_avg = metrics["eeat"].get("average")
    cwv_avg = metrics["core_web_vitals"].get("average")
    irzc_avg = metrics["irzc"].get("average")
    ia_ready_avg = metrics["ia_ready"].get("average")
    sov_avg = metrics["serp"].get("share_of_voice_avg")
    serp_features_avg = metrics["serp"].get("serp_features_avg")

    # IM-SEO status
    if im_seo_avg is not None:
        if im_seo_avg < 50:
            add_insight(
                "IM-SEO crítico",
                (
                    f"Score médio em {fmt(im_seo_avg)}. Reforce conteúdo pilar, backlinks e experiência "
                    "técnica para alcançar patamar competitivo."
                ),
                severity="high",
            )
        elif im_seo_avg < 60:
            add_insight(
                "IM-SEO abaixo do ideal",
                (
                    f"Score médio em {fmt(im_seo_avg)}. Priorize ajustes de autoridade (AMR/DCR) "
                    "e performance (Core Web Vitals)."
                ),
                severity="medium",
            )
        elif im_seo_avg >= 80:
            add_insight(
                "IM-SEO em nível de excelência",
                f"Score médio em {fmt(im_seo_avg)}. Mantenha rotinas de monitoramento para sustentar o desempenho.",
                severity="positive",
            )

    # IM-SEO trends
    if trends.get("im_seo") is not None:
        if trends["im_seo"] < -5:
            add_insight(
                "Queda recente em IM-SEO",
                (
                    f"Variação de {fmt(trends['im_seo'])}% em relação ao período anterior. "
                    "Investigue conteúdos que perderam posição e revise sinais de autoridade."
                ),
                severity="medium",
            )
        elif trends["im_seo"] > 7:
            add_insight(
                "IM-SEO acelerando",
                f"Crescimento de {fmt(trends['im_seo'])}% versus o período anterior. Aproveite o momentum para ampliar conteúdos vencedores.",
                severity="positive",
            )

    # IM-SEOIA status e tendências
    if im_seoia_avg is not None:
        if im_seoia_avg < 60:
            add_insight(
                "IM-SEOIA precisa evoluir",
                (
                    f"Score médio em {fmt(im_seoia_avg)}. Inclua blocos estruturados (listas, FAQs) e dados "
                    "de suporte para respostas generativas."
                ),
                severity="medium",
            )
        elif im_seoia_avg >= 78:
            add_insight(
                "Forte preparo para IA",
                f"IM-SEOIA em {fmt(im_seoia_avg)}. Continue estruturando conteúdos para experiências generativas.",
                severity="positive",
            )

    if trends.get("im_seoia") is not None:
        if trends["im_seoia"] > 5:
            add_insight(
                "IM-SEOIA em ascensão",
                "Mantenha iniciativas de IA – evolução positiva recente detectada.",
                severity="positive",
            )
        elif trends["im_seoia"] < -5:
            add_insight(
                "IM-SEOIA perdeu tração",
                (
                    f"Variação negativa de {fmt(trends['im_seoia'])}% frente ao período anterior. "
                    "Revise prompts, blocos de destaque e cobertura temática."
                ),
                severity="medium",
            )

    # E-E-A-T
    if eeat_avg is not None and eeat_avg < 60:
        add_insight(
            "E-E-A-T precisa de reforço",
            (
                f"Score médio em {fmt(eeat_avg)}. Reforce sinais de experiência, especialistas e evidências "
                "(estudos, depoimentos, dados proprietários)."
            ),
            severity="high",
        )
    elif eeat_avg is not None and eeat_avg >= 80:
        add_insight(
            "Autoridade consolidada",
            "E-E-A-T acima de 80. Explore esse diferencial em novas páginas e assets.",
            severity="positive",
        )

    # Core Web Vitals
    if cwv_avg is not None and cwv_avg < 70:
        add_insight(
            "Core Web Vitals fora da meta",
            (
                f"Score médio em {fmt(cwv_avg)}. Priorize melhorias em LCP, CLS e FID para destravar ganhos de posicionamento."
            ),
            severity="medium",
        )
    elif cwv_avg is not None and cwv_avg >= 85:
        add_insight(
            "Performance Web exemplar",
            "Core Web Vitals em patamar excelente. Utilize este benchmark para outras propriedades digitais.",
            severity="positive",
        )

    # Zero-click risk
    if irzc_avg is not None:
        if irzc_avg > 75:
            add_insight(
                "Risco Zero-Click crítico",
                f"Índice em {fmt(irzc_avg)}. Reavalie SERP intent, snippets e CTAs para recuperar cliques orgânicos.",
                severity="high",
            )
        elif irzc_avg > 60:
            add_insight(
                "Risco Zero-Click elevado",
                f"Índice em {fmt(irzc_avg)}. Ajuste meta descriptions e estruturas ricas para capturar o clique.",
                severity="medium",
            )
        else:
            add_insight(
                "Risco Zero-Click controlado",
                f"IRZC em {fmt(irzc_avg)}. Continue monitorando concorrentes e features SERP.",
                severity="positive",
            )

    # IA Ready
    if ia_ready_avg is not None:
        if ia_ready_avg < 55:
            add_insight(
                "Potencial IA-Ready",
                (
                    f"Score médio em {fmt(ia_ready_avg)}. Adicione listas, FAQs e dados estruturados para respostas generativas."
                ),
                severity="medium",
            )
        elif ia_ready_avg >= 75:
            add_insight(
                "Conteúdo preparado para IA",
                f"IA-Ready em {fmt(ia_ready_avg)}. Escale padrões estruturados para clusters adjacentes.",
                severity="positive",
            )

    # SERP share of voice e features
    if sov_avg is not None:
        if sov_avg < 30:
            add_insight(
                "Share of Voice limitado",
                (
                    f"Participação média em {fmt(sov_avg)}%. Reforce páginas prioritárias e melhore snippets para ganhar visibilidade."
                ),
                severity="medium",
            )
        elif sov_avg >= 60:
            add_insight(
                "Alta presença em SERP",
                f"Share of Voice em {fmt(sov_avg)}%. Amplie esforços para proteger posições estratégicas.",
                severity="positive",
            )

    if serp_features_avg is not None and serp_features_avg < 20:
        add_insight(
            "Poucas SERP Features",
            (
                f"Apenas {fmt(serp_features_avg)}% das SERPs exibem features conquistadas. Estruture conteúdo para rich results (FAQ, HowTo, Reviews)."
            ),
            severity="medium",
        )
    elif serp_features_avg is not None and serp_features_avg >= 55:
        add_insight(
            "Bom domínio de SERP Features",
            f"Features presentes em {fmt(serp_features_avg)}% das SERPs. Expanda para queries long tail.",
            severity="positive",
        )

    semantic = _build_semantic_snapshot(runs, db)

    return {
        "total_runs": len(runs),
        "period_days": days,
        "metrics": metrics,
        "trends": trends,
        "distribution": distribution,
        "multidimensional": multidimensional,
        "index_comparison": index_comparison,
        "insights": insights,
        "semantic": semantic,
    }


@router.get("/semantic-insights")
def get_semantic_insights(
    project_id: Optional[str] = None,
    engine_ids: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    im_seo_min: Optional[float] = None,
    im_seo_max: Optional[float] = None,
    im_seoia_min: Optional[float] = None,
    im_seoia_max: Optional[float] = None,
    subproject_id: Optional[str] = None,
    prompt_id: Optional[str] = None,
    run_id: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retorna snapshot agregado das entidades, keywords e percepção."""
    overview = get_im_overview(
        project_id=project_id,
        engine_ids=engine_ids,
        days=days,
        start_date=start_date,
        end_date=end_date,
        im_seo_min=im_seo_min,
        im_seo_max=im_seo_max,
        im_seoia_min=im_seoia_min,
        im_seoia_max=im_seoia_max,
        subproject_id=subproject_id,
        prompt_id=prompt_id,
        run_id=run_id,
        db=db,
    )
    return overview.get("semantic", _empty_semantic_snapshot())


def _empty_semantic_snapshot() -> Dict[str, Any]:
    return {
        "perception_distribution": [],
        "brand_ranking": [],
        "top_keywords": [],
        "competitors": [],
        "runs_analyzed": 0,
    }


def _build_semantic_snapshot(runs: List[Run], db: Session) -> Dict[str, Any]:
    if not runs:
        return _empty_semantic_snapshot()

    run_ids = [run.id for run in runs]
    total_runs = len(runs)

    perception_counts = Counter(
        run.perceived_value_category for run in runs if run.perceived_value_category
    )
    perception_distribution = [
        {
            "category": category,
            "count": count,
            "percentage": round((count / total_runs) * 100, 1),
        }
        for category, count in perception_counts.most_common()
    ]

    insights = (
        db.query(RunSemanticInsight)
        .filter(RunSemanticInsight.run_id.in_(run_ids))
        .all()
    )

    if not insights:
        snapshot = _empty_semantic_snapshot()
        snapshot["perception_distribution"] = perception_distribution
        snapshot["runs_analyzed"] = 0
        return snapshot

    brand_scores: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"score": 0.0, "mentions": 0})
    competitor_scores: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"score": 0.0, "mentions": 0})
    keyword_scores: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"weight": 0.0, "mentions": 0, "brands": set(), "competitors": set()}
    )

    for insight in insights:
        payload = insight.payload or {}

        for entity in payload.get("entities", []) or []:
            name = entity.get("name")
            if not name:
                continue
            roles = entity.get("roles") or []
            confidence = float(entity.get("confidence") or 0.0)
            category = (entity.get("category") or "").lower()

            if "brand" in [r.lower() for r in roles] or category == "brand":
                data = brand_scores[name]
                data["score"] += confidence if confidence > 0 else 0.5
                data["mentions"] += 1
            if "competitor" in [r.lower() for r in roles] or category == "competitor":
                data = competitor_scores[name]
                data["score"] += confidence if confidence > 0 else 0.5
                data["mentions"] += 1

        for keyword in payload.get("keywords", []) or []:
            token = keyword.get("token") or keyword.get("keyword")
            if not token:
                continue
            entry = keyword_scores[token]
            weight = float(keyword.get("weight") or keyword.get("score") or 0.0)
            if weight <= 0:
                weight = 0.3
            entry["weight"] += weight
            entry["mentions"] += 1
            for brand in keyword.get("brands") or []:
                entry["brands"].add(brand)
            for competitor in keyword.get("competitors") or []:
                entry["competitors"].add(competitor)

        for competitor in payload.get("competitors", []) or []:
            name = competitor.get("name")
            if not name:
                continue
            mentions = competitor.get("mentions") or 1
            score_add = float(competitor.get("score") or mentions)
            data = competitor_scores[name]
            data["mentions"] += mentions
            data["score"] += score_add

    brand_ranking = [
        {
            "name": name,
            "score": round(data["score"], 2),
            "mentions": data["mentions"],
        }
        for name, data in brand_scores.items()
    ]
    brand_ranking.sort(key=lambda item: item["score"], reverse=True)

    competitors = [
        {
            "name": name,
            "score": round(data["score"], 2),
            "mentions": data["mentions"],
        }
        for name, data in competitor_scores.items()
    ]
    competitors.sort(key=lambda item: item["score"], reverse=True)

    top_keywords = [
        {
            "token": token,
            "weight": round(data["weight"], 2),
            "mentions": data["mentions"],
            "brands": sorted(data["brands"]),
            "competitors": sorted(data["competitors"]),
        }
        for token, data in keyword_scores.items()
    ]
    top_keywords.sort(key=lambda item: item["weight"], reverse=True)

    return {
        "perception_distribution": perception_distribution,
        "brand_ranking": brand_ranking[:15],
        "top_keywords": top_keywords[:25],
        "competitors": competitors[:15],
        "runs_analyzed": len(insights),
    }


@router.get("/timeseries")
def get_timeseries(
    project_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    granularity: str = Query("day", regex="^(day|week|month)$"),
    db: Session = Depends(get_db)
):
    """
    Retorna série temporal das métricas para gráficos.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(Run).filter(
        Run.status == "completed",
        Run.started_at >= cutoff_date
    )
    
    if project_id:
        query = query.filter(Run.project_id == project_id)
    
    runs = query.order_by(Run.started_at.asc()).all()
    
    # Agrupar por período
    from collections import defaultdict
    grouped = defaultdict(list)
    
    for run in runs:
        if granularity == "day":
            key = run.started_at.date().isoformat()
        elif granularity == "week":
            key = run.started_at.strftime("%Y-W%U")
        else:  # month
            key = run.started_at.strftime("%Y-%m")
        
        grouped[key].append(run)
    
    # Calcular médias por período
    timeseries = []
    for period, period_runs in sorted(grouped.items()):
        def safe_avg(values):
            filtered = [v for v in values if v is not None]
            return round(sum(filtered) / len(filtered), 2) if filtered else None
        
        timeseries.append({
            "period": period,
            "count": len(period_runs),
            "im_seo_score": safe_avg([r.im_seo_score for r in period_runs]),
            "im_seoia_score": safe_avg([r.im_seoia_score for r in period_runs]),
            "eeat_score": safe_avg([r.eeat_score for r in period_runs]),
            "core_web_vitals_score": safe_avg([r.core_web_vitals_score for r in period_runs]),
            "irzc_score": safe_avg([r.irzc_score for r in period_runs]),
            "share_of_voice_serp": safe_avg([r.share_of_voice_serp for r in period_runs]),
        })
    
    return {
        "granularity": granularity,
        "period_days": days,
        "data": timeseries
    }


@router.get("/im-filters")
def get_im_filters(
    project_id: Optional[str] = None,
    limit_runs: int = Query(200, ge=10, le=1000),
    db: Session = Depends(get_db)
):
    """Retorna opções de filtros avançados para o dashboard IM."""

    projects_query = db.query(Project.id, Project.name).order_by(Project.name.asc())
    if project_id:
        projects_query = projects_query.filter(Project.id == project_id)
    projects = [
        {"id": proj.id, "name": proj.name}
        for proj in projects_query.all()
    ]

    themes_query = db.query(SubProject.id, SubProject.name, SubProject.project_id).order_by(SubProject.name.asc())
    if project_id:
        themes_query = themes_query.filter(SubProject.project_id == project_id)
    themes = [
        {
            "id": theme.id,
            "name": theme.name,
            "project_id": theme.project_id,
        }
        for theme in themes_query.all()
    ]

    prompts_query = db.query(Prompt.id, Prompt.name, Prompt.text, Prompt.project_id, Prompt.intent).order_by(Prompt.name.asc())
    if project_id:
        prompts_query = prompts_query.filter(Prompt.project_id == project_id)
    
    # Agrupar prompts pelo texto para juntar prompts custom iguais
    prompts_by_text = {}
    for prompt in prompts_query.all():
        # Para prompts custom, usar o texto como chave de agrupamento
        if prompt.name and prompt.name.startswith("Prompt custom"):
            # Usar primeiros 100 chars do texto como preview
            text_preview = prompt.text[:100] if prompt.text else prompt.name
            group_key = f"custom_{prompt.text}"  # Agrupar pelo texto completo
            
            if group_key not in prompts_by_text:
                prompts_by_text[group_key] = {
                    "id": prompt.id,  # Usar ID do primeiro
                    "name": text_preview,  # Mostrar preview do texto
                    "text": prompt.text,  # Texto completo
                    "project_id": prompt.project_id,
                    "intent": prompt.intent,
                    "prompt_ids": [prompt.id],  # Lista de IDs agrupados
                    "is_custom": True,
                }
            else:
                # Adicionar ID ao grupo
                prompts_by_text[group_key]["prompt_ids"].append(prompt.id)
        else:
            # Prompts normais (templates) não agrupar
            prompts_by_text[f"template_{prompt.id}"] = {
                "id": prompt.id,
                "name": prompt.name,
                "text": prompt.text,
                "project_id": prompt.project_id,
                "intent": prompt.intent,
                "prompt_ids": [prompt.id],
                "is_custom": False,
            }
    
    prompts = list(prompts_by_text.values())

    engine_rows = db.query(Engine.id, Engine.project_id, Engine.name, Engine.region, Engine.device).order_by(Engine.name.asc()).all()
    if project_id:
        engine_rows = [row for row in engine_rows if row.project_id == project_id]

    engine_groups_map: dict[tuple[str | None, str | None, str | None], dict] = {}
    for row in engine_rows:
        key = (row.name, row.region, row.device)
        label_parts = [row.name]
        if row.region:
            label_parts.append(row.region)
        if row.device:
            label_parts.append(row.device.capitalize())
        label = " • ".join(label_parts)
        if key not in engine_groups_map:
            engine_groups_map[key] = {
                "key": "|".join(part or "" for part in key),
                "label": label,
                "name": row.name,
                "region": row.region,
                "device": row.device,
                "engine_ids": [row.id],
            }
        else:
            engine_groups_map[key]["engine_ids"].append(row.id)

    engine_groups = list(engine_groups_map.values())

    runs_query = (
        db.query(
            Run.id,
            Run.project_id,
            Run.subproject_id,
            Run.status,
            Run.started_at,
            Engine.name.label("engine_name"),
            Engine.region.label("engine_region"),
            Engine.device.label("engine_device"),
            PromptVersion.prompt_id.label("prompt_id"),
            Prompt.name.label("prompt_name"),
        )
        .join(Engine, Engine.id == Run.engine_id)
        .outerjoin(PromptVersion, PromptVersion.id == Run.prompt_version_id)
        .outerjoin(Prompt, Prompt.id == PromptVersion.prompt_id)
    )

    if project_id:
        runs_query = runs_query.filter(Run.project_id == project_id)

    runs_rows = (
        runs_query.order_by(Run.started_at.desc(), Run.id.desc())
        .limit(limit_runs)
        .all()
    )

    runs = []
    for row in runs_rows:
        engine_key = (row.engine_name, row.engine_region, row.engine_device)
        engine_group_key = "|".join(part or "" for part in engine_key)
        runs.append(
            {
                "id": row.id,
                "project_id": row.project_id,
                "subproject_id": row.subproject_id,
                "prompt_id": row.prompt_id,
                "prompt_name": row.prompt_name,
                "engine_name": row.engine_name,
                "engine_region": row.engine_region,
                "engine_device": row.engine_device,
                "status": row.status,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "engine_group_key": engine_group_key,
            }
        )

    return {
        "projects": projects,
        "themes": themes,
        "prompts": prompts,
        "runs": runs,
        "engine_groups": engine_groups,
    }


@router.get("/engines")
def get_engines(db: Session = Depends(get_db)):
    """
    Retorna lista de todas as engines disponíveis.
    """
    engines = db.query(Engine).all()
    return [{"id": e.id, "name": e.name} for e in engines]


@router.get("/projects")
def get_projects_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Retorna resumo de métricas por projeto.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    projects = db.query(Project).all()
    
    summary = []
    for project in projects:
        runs = db.query(Run).filter(
            Run.project_id == project.id,
            Run.status == "completed",
            Run.started_at >= cutoff_date
        ).all()
        
        if not runs:
            continue
        
        def safe_avg(values):
            filtered = [v for v in values if v is not None]
            return round(sum(filtered) / len(filtered), 2) if filtered else None
        
        summary.append({
            "project_id": project.id,
            "project_name": project.name,
            "total_runs": len(runs),
            "im_seo_avg": safe_avg([r.im_seo_score for r in runs]),
            "im_seoia_avg": safe_avg([r.im_seoia_score for r in runs]),
            "eeat_avg": safe_avg([r.eeat_score for r in runs]),
            "irzc_avg": safe_avg([r.irzc_score for r in runs]),
        })
    
    return {
        "period_days": days,
        "projects": summary
    }
