"""
Rotas API para GEO (Generative Engine Optimization).
Endpoints para análise de presença de marca em LLMs (ChatGPT, Gemini, Perplexity).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.models import (
    Run,
    Project,
    Engine,
    DomainVariant,
    ContentGap,
    Citation,
)
from app.schemas.schemas import (
    DomainVariantCreate,
    DomainVariantOut,
    ContentGapCreate,
    ContentGapUpdate,
    ContentGapOut,
    GeoCitationRateStats,
    GeoCoCitationAnalysis,
)

router = APIRouter(prefix="/api/projects", tags=["GEO"])


# Dependency
def get_db():
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========================================
# DOMAIN VARIANTS (Consolidação de Domínios)
# ========================================

@router.get("/{project_id}/domain-variants", response_model=List[DomainVariantOut])
def list_domain_variants(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Lista todas as variantes de domínio configuradas para o projeto."""
    variants = db.query(DomainVariant).filter(
    ).order_by(DomainVariant.canonical_domain, DomainVariant.variant_domain).all()
    
    return variants


@router.post("/{project_id}/domain-variants/bulk")
def bulk_create_domain_variants(
    project_id: str,
    canonical_domain: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Popula variantes de domínio em massa para domínios conhecidos.
    
    Domínios suportados:
    - bb.com.br (Banco do Brasil)
    - nubank.com.br
    - itau.com.br
    - bradesco.com.br
    - santander.com.br
    - caixa.gov.br
    - bancointer.com.br
    - c6bank.com.br
    - pagbank.com.br
    """
    # Verificar se projeto existe
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Mapeamento de variantes
    variants_map = {
        "bb.com.br": [
            "bancodobrasil.com.br", "bb.com", "ourocard.com.br", "ourocard.com",
            "bbseguros.com.br", "atendimento.bb.com.br"
        ],
        "nubank.com.br": ["nu.com.br", "nubank.com", "nuconta.com.br", "nuinvest.com.br"],
        "itau.com.br": ["itau.com", "itaucard.com.br", "itauempresial.com.br"],
        "bradesco.com.br": ["bradesco.com", "bradescocard.com.br"],
        "santander.com.br": ["santander.com", "santandercard.com.br"],
        "caixa.gov.br": ["caixa.com.br", "caixaseguros.com.br"],
        "bancointer.com.br": ["inter.com.br", "inter.co"],
        "c6bank.com.br": ["c6bank.com", "c6.com.br"],
        "pagbank.com.br": ["pagseguro.com.br", "pagseguro.uol.com.br"],
    }
    
    if canonical_domain not in variants_map:
        raise HTTPException(
            status_code=400,
            detail=f"Domínio não suportado. Disponíveis: {', '.join(variants_map.keys())}"
        )
    
    variants = variants_map[canonical_domain]
    added = []
    skipped = []
    
    for variant_domain in variants:
        # Verificar se já existe
        existing = db.query(DomainVariant).filter(
            DomainVariant.project_id == project_id,
            DomainVariant.variant_domain == variant_domain,
        ).first()
        
        if existing:
            skipped.append(variant_domain)
            continue
        
        # Criar
        from app.models.models import gen_id
        domain_variant = DomainVariant(
            id=gen_id("dv"),
            project_id=project_id,
            variant_domain=variant_domain,
            canonical_domain=canonical_domain,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        db.add(domain_variant)
        added.append(variant_domain)
    
    db.commit()
    
    return {
        "canonical_domain": canonical_domain,
        "added_count": len(added),
        "skipped_count": len(skipped),
        "added": added,
        "skipped": skipped,
    }


@router.post("/{project_id}/domain-variants")
def create_domain_variant(
    project_id: str,
    variant: DomainVariantCreate,
    db: Session = Depends(get_db),
) -> DomainVariantOut:
    """Cria uma nova variante de domínio."""
    # Verificar se projeto existe
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verificar se variante já existe
    existing = db.query(DomainVariant).filter(
        DomainVariant.project_id == project_id,
        DomainVariant.variant_domain == variant.variant_domain
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Variant domain already exists")
    
    from app.models.models import gen_id
    domain_variant = DomainVariant(
        id=gen_id("dv"),
        project_id=project_id,
        variant_domain=variant.variant_domain,
        canonical_domain=variant.canonical_domain,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    
    db.add(domain_variant)
    db.commit()
    db.refresh(domain_variant)
    
    return domain_variant


@router.delete("/{project_id}/domain-variants/{variant_id}")
def delete_domain_variant(
    project_id: str,
    variant_id: str,
    db: Session = Depends(get_db)
):
    """Remove uma variante de domínio."""
    variant = db.get(DomainVariant, variant_id)
    
    if not variant or variant.project_id != project_id:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    db.delete(variant)
    db.commit()
    
    return {"status": "deleted", "id": variant_id}


# ========================================
# CONTENT GAPS (Lacunas de Conteúdo)
# ========================================

@router.get("/{project_id}/content-gaps", response_model=List[ContentGapOut])
def list_content_gaps(
    project_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    db: Session = Depends(get_db)
):
    """Lista lacunas de conteúdo detectadas."""
    query = db.query(ContentGap).filter(ContentGap.project_id == project_id)
    
    if status:
        query = query.filter(ContentGap.status == status)
    
    if priority:
        query = query.filter(ContentGap.priority == priority)
    
    gaps = query.order_by(
        # Ordenar por prioridade (critical > high > medium > low) e data
        ContentGap.priority.desc(),
        ContentGap.detected_at.desc()
    ).all()
    
    return gaps


@router.post("/{project_id}/content-gaps", response_model=ContentGapOut)
def create_content_gap(
    project_id: str,
    payload: ContentGapCreate,
    db: Session = Depends(get_db)
):
    """Cria uma nova lacuna de conteúdo."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    gap = ContentGap(
        project_id=project_id,
        url=payload.url,
        topic=payload.topic,
        gap_type=payload.gap_type,
        description=payload.description,
        suggestion=payload.suggestion,
        priority=payload.priority,
        assignee=payload.assignee,
    )
    
    db.add(gap)
    db.commit()
    db.refresh(gap)
    
    return gap


@router.patch("/{project_id}/content-gaps/{gap_id}", response_model=ContentGapOut)
def update_content_gap(
    project_id: str,
    gap_id: str,
    payload: ContentGapUpdate,
    db: Session = Depends(get_db)
):
    """Atualiza uma lacuna de conteúdo."""
    gap = db.get(ContentGap, gap_id)
    
    if not gap or gap.project_id != project_id:
        raise HTTPException(status_code=404, detail="Content gap not found")
    
    if payload.status is not None:
        gap.status = payload.status
        if payload.status == "completed":
            gap.resolved_at = datetime.utcnow()
    
    if payload.priority is not None:
        gap.priority = payload.priority
    
    if payload.assignee is not None:
        gap.assignee = payload.assignee
    
    if payload.suggestion is not None:
        gap.suggestion = payload.suggestion
    
    db.commit()
    db.refresh(gap)
    
    return gap


@router.delete("/{project_id}/content-gaps/{gap_id}")
def delete_content_gap(
    project_id: str,
    gap_id: str,
    db: Session = Depends(get_db)
):
    """Remove uma lacuna de conteúdo."""
    gap = db.get(ContentGap, gap_id)
    
    if not gap or gap.project_id != project_id:
        raise HTTPException(status_code=404, detail="Content gap not found")
    
    db.delete(gap)
    db.commit()
    
    return {"status": "deleted", "id": gap_id}


# ========================================
# CITATION RATE STATS (Estatísticas Agregadas)
# ========================================

@router.get("/{project_id}/geo/citation-rate", response_model=GeoCitationRateStats)
def get_citation_rate_stats(
    project_id: str,
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Calcula estatísticas de Citation Rate para o projeto.
    Apenas runs de LLMs (ChatGPT, Gemini, Perplexity).
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    period_start = datetime.utcnow() - timedelta(days=days)
    period_end = datetime.utcnow()
    
    # Buscar engines de LLM
    llm_engines = db.query(Engine).filter(
        Engine.project_id == project_id,
        or_(
            Engine.name.ilike("%chatgpt%"),
            Engine.name.ilike("%gpt%"),
            Engine.name.ilike("%gemini%"),
            Engine.name.ilike("%perplexity%"),
            Engine.name.ilike("%claude%"),
        )
    ).all()
    
    llm_engine_ids = [e.id for e in llm_engines]
    
    if not llm_engine_ids:
        # Sem engines de LLM configuradas
        return GeoCitationRateStats(
            period_start=period_start,
            period_end=period_end,
            total_runs=0,
            llm_runs=0,
            cr_observed_avg=0.0,
            cr_corrected_avg=0.0,
            cr_trend="stable",
            by_engine={},
        )
    
    # Buscar runs de LLM no período
    runs = db.query(Run).filter(
        Run.project_id == project_id,
        Run.engine_id.in_(llm_engine_ids),
        Run.started_at >= period_start,
        Run.started_at <= period_end,
        Run.status == "completed",
    ).all()
    
    total_runs = len(runs)
    llm_runs = total_runs
    
    if total_runs == 0:
        return GeoCitationRateStats(
            period_start=period_start,
            period_end=period_end,
            total_runs=0,
            llm_runs=0,
            cr_observed_avg=0.0,
            cr_corrected_avg=0.0,
            cr_trend="stable",
            by_engine={},
        )
    
    # Calcular médias
    cr_observed_values = [r.citation_rate_observed for r in runs if r.citation_rate_observed is not None]
    cr_corrected_values = [r.citation_rate_corrected for r in runs if r.citation_rate_corrected is not None]
    
    cr_observed_avg = sum(cr_observed_values) / len(cr_observed_values) if cr_observed_values else 0.0
    cr_corrected_avg = sum(cr_corrected_values) / len(cr_corrected_values) if cr_corrected_values else 0.0
    
    # Calcular tendência (comparar primeira metade vs segunda metade)
    mid_point = period_start + timedelta(days=days // 2)
    first_half = [r for r in runs if r.started_at < mid_point]
    second_half = [r for r in runs if r.started_at >= mid_point]
    
    first_half_avg = sum(r.citation_rate_corrected for r in first_half if r.citation_rate_corrected) / len(first_half) if first_half else 0
    second_half_avg = sum(r.citation_rate_corrected for r in second_half if r.citation_rate_corrected) / len(second_half) if second_half else 0
    
    if second_half_avg > first_half_avg * 1.1:
        trend = "up"
    elif second_half_avg < first_half_avg * 0.9:
        trend = "down"
    else:
        trend = "stable"
    
    # Breakdown por engine
    by_engine: Dict[str, Dict[str, float]] = {}
    for engine in llm_engines:
        engine_runs = [r for r in runs if r.engine_id == engine.id]
        if engine_runs:
            obs_vals = [r.citation_rate_observed for r in engine_runs if r.citation_rate_observed is not None]
            corr_vals = [r.citation_rate_corrected for r in engine_runs if r.citation_rate_corrected is not None]
            
            by_engine[engine.name] = {
                "cr_observed": round(sum(obs_vals) / len(obs_vals), 2) if obs_vals else 0.0,
                "cr_corrected": round(sum(corr_vals) / len(corr_vals), 2) if corr_vals else 0.0,
                "count": len(engine_runs),
            }
    
    return GeoCitationRateStats(
        period_start=period_start,
        period_end=period_end,
        total_runs=total_runs,
        llm_runs=llm_runs,
        cr_observed_avg=round(cr_observed_avg, 2),
        cr_corrected_avg=round(cr_corrected_avg, 2),
        cr_trend=trend,
        by_engine=by_engine,
    )


# ========================================
# CO-CITATION ANALYSIS (Análise Competitiva)
# ========================================

@router.get("/{project_id}/geo/cocitation-analysis", response_model=List[GeoCoCitationAnalysis])
def get_cocitation_analysis(
    project_id: str,
    days: int = Query(30, description="Number of days to analyze"),
    limit: int = Query(10, description="Top N competitors"),
    db: Session = Depends(get_db)
):
    """
    Analisa co-citação: quais concorrentes aparecem junto com nossa marca.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    period_start = datetime.utcnow() - timedelta(days=days)
    
    # Buscar runs de LLM com co-citação
    llm_engines = db.query(Engine).filter(
        Engine.project_id == project_id,
        or_(
            Engine.name.ilike("%chatgpt%"),
            Engine.name.ilike("%gpt%"),
            Engine.name.ilike("%gemini%"),
            Engine.name.ilike("%perplexity%"),
            Engine.name.ilike("%claude%"),
        )
    ).all()
    
    llm_engine_ids = [e.id for e in llm_engines]
    
    runs = db.query(Run).filter(
        Run.project_id == project_id,
        Run.engine_id.in_(llm_engine_ids),
        Run.started_at >= period_start,
        Run.status == "completed",
        Run.cocitation_competitors.isnot(None),
    ).all()
    
    # Agregar co-citações
    competitor_stats: Dict[str, Dict[str, Any]] = {}
    
    for run in runs:
        try:
            cocited = json.loads(run.cocitation_competitors or "[]")
            for domain in cocited:
                if domain not in competitor_stats:
                    competitor_stats[domain] = {
                        "count": 0,
                        "prominence_scores": [],
                    }
                competitor_stats[domain]["count"] += 1
                if run.brand_prominence_score:
                    competitor_stats[domain]["prominence_scores"].append(run.brand_prominence_score)
        except json.JSONDecodeError:
            continue
    
    # Converter para lista e ordenar
    total_cocitations = sum(stats["count"] for stats in competitor_stats.values())
    
    results: List[GeoCoCitationAnalysis] = []
    for domain, stats in sorted(competitor_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:limit]:
        avg_prominence = None
        if stats["prominence_scores"]:
            avg_prominence = round(sum(stats["prominence_scores"]) / len(stats["prominence_scores"]), 2)
        
        results.append(GeoCoCitationAnalysis(
            competitor_domain=domain,
            competitor_name=domain.split(".")[0].title(),  # Simplificado
            cocitation_count=stats["count"],
            cocitation_percentage=round((stats["count"] / total_cocitations) * 100, 2) if total_cocitations > 0 else 0.0,
            contexts=["geral"],  # TODO: Detectar contextos específicos
            avg_prominence_when_together=avg_prominence,
        ))
    
    return results


# ========================================
# AGGREGATION ENDPOINTS (Métricas por Segmento)
# ========================================

@router.get("/{project_id}/geo/stats-by-funnel")
def get_geo_stats_by_funnel(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retorna estatísticas GEO agregadas por estágio do funil.
    
    Returns:
        {
            "consciencia": {"runs": 10, "avg_citation_rate": 35.5, "avg_prominence": 65.2},
            "consideracao": {...},
            "decisao": {...}
        }
    """
    # Verificar se projeto existe
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Data de corte
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Query base: runs LLM do projeto
    base_query = db.query(Run).filter(
        Run.project_id == project_id,
        Run.started_at >= cutoff_date,
        Run.status == "completed",
    ).join(Engine).filter(
        or_(
            Engine.name.ilike("%openai%"),
            Engine.name.ilike("%chatgpt%"),
            Engine.name.ilike("%gemini%"),
            Engine.name.ilike("%perplexity%"),
            Engine.name.ilike("%claude%"),
        )
    )
    
    # Agrupar por funnel_stage
    stats_by_funnel: Dict[str, Dict[str, Any]] = {}
    
    for stage in ["consciencia", "consideracao", "decisao", "pos_compra"]:
        runs = base_query.filter(Run.funnel_stage == stage).all()
        
        if not runs:
            stats_by_funnel[stage] = {
                "runs_count": 0,
                "avg_citation_rate": None,
                "avg_prominence": None,
                "avg_engagement": None,
                "avg_conversion_potential": None,
            }
            continue
        
        # Calcular médias
        citation_rates = [r.citation_rate_observed for r in runs if r.citation_rate_observed is not None]
        prominences = [r.brand_prominence_score for r in runs if r.brand_prominence_score is not None]
        engagements = [r.engagement_score for r in runs if r.engagement_score is not None]
        conversions = [r.conversion_potential_score for r in runs if r.conversion_potential_score is not None]
        
        stats_by_funnel[stage] = {
            "runs_count": len(runs),
            "avg_citation_rate": round(sum(citation_rates) / len(citation_rates), 2) if citation_rates else None,
            "avg_prominence": round(sum(prominences) / len(prominences), 2) if prominences else None,
            "avg_engagement": round(sum(engagements) / len(engagements), 2) if engagements else None,
            "avg_conversion_potential": round(sum(conversions) / len(conversions), 2) if conversions else None,
        }
    
    return stats_by_funnel


@router.get("/{project_id}/geo/stats-by-question-type")
def get_geo_stats_by_question_type(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retorna estatísticas GEO agregadas por tipo de pergunta.
    
    Returns:
        {
            "informacional": {"runs": 15, "avg_citation_rate": 40.2, ...},
            "transacional": {...},
            "navegacional": {...}
        }
    """
    # Verificar se projeto existe
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Data de corte
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Query base: runs LLM do projeto
    base_query = db.query(Run).filter(
        Run.project_id == project_id,
        Run.started_at >= cutoff_date,
        Run.status == "completed",
    ).join(Engine).filter(
        or_(
            Engine.name.ilike("%openai%"),
            Engine.name.ilike("%chatgpt%"),
            Engine.name.ilike("%gemini%"),
            Engine.name.ilike("%perplexity%"),
            Engine.name.ilike("%claude%"),
        )
    )
    
    # Agrupar por question_type
    stats_by_type: Dict[str, Dict[str, Any]] = {}
    
    for qtype in ["informacional", "transacional", "navegacional", "comparativa"]:
        runs = base_query.filter(Run.question_type == qtype).all()
        
        if not runs:
            stats_by_type[qtype] = {
                "runs_count": 0,
                "avg_citation_rate": None,
                "avg_prominence": None,
                "avg_sov": None,
                "avg_conversion_potential": None,
            }
            continue
        
        # Calcular médias
        citation_rates = [r.citation_rate_observed for r in runs if r.citation_rate_observed is not None]
        prominences = [r.brand_prominence_score for r in runs if r.brand_prominence_score is not None]
        sovs = [r.share_of_voice_llm for r in runs if r.share_of_voice_llm is not None]
        conversions = [r.conversion_potential_score for r in runs if r.conversion_potential_score is not None]
        
        stats_by_type[qtype] = {
            "runs_count": len(runs),
            "avg_citation_rate": round(sum(citation_rates) / len(citation_rates), 2) if citation_rates else None,
            "avg_prominence": round(sum(prominences) / len(prominences), 2) if prominences else None,
            "avg_sov": round(sum(sovs) / len(sovs), 2) if sovs else None,
            "avg_conversion_potential": round(sum(conversions) / len(conversions), 2) if conversions else None,
        }
    
    return stats_by_type


@router.get("/{project_id}/geo/stats-by-product")
def get_geo_stats_by_product(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retorna estatísticas GEO agregadas por categoria de produto.
    
    Returns:
        {
            "cartoes": {"runs": 8, "avg_citation_rate": 42.5, ...},
            "credito": {...},
            "investimentos": {...}
        }
    """
    # Verificar se projeto existe
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Data de corte
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Query base: runs LLM do projeto
    base_query = db.query(Run).filter(
        Run.project_id == project_id,
        Run.started_at >= cutoff_date,
        Run.status == "completed",
    ).join(Engine).filter(
        or_(
            Engine.name.ilike("%openai%"),
            Engine.name.ilike("%chatgpt%"),
            Engine.name.ilike("%gemini%"),
            Engine.name.ilike("%perplexity%"),
            Engine.name.ilike("%claude%"),
        )
    )
    
    # Agrupar por product_category
    stats_by_product: Dict[str, Dict[str, Any]] = {}
    
    # Categorias possíveis
    categories = ["cartoes", "credito", "investimentos", "conta", "seguros", "empresarial", "digital", "multiproduto"]
    
    for category in categories:
        runs = base_query.filter(Run.product_category == category).all()
        
        if not runs:
            stats_by_product[category] = {
                "runs_count": 0,
                "avg_citation_rate": None,
                "avg_prominence": None,
                "avg_sov": None,
                "avg_engagement": None,
                "avg_conversion_potential": None,
            }
            continue
        
        # Calcular médias
        citation_rates = [r.citation_rate_observed for r in runs if r.citation_rate_observed is not None]
        prominences = [r.brand_prominence_score for r in runs if r.brand_prominence_score is not None]
        sovs = [r.share_of_voice_llm for r in runs if r.share_of_voice_llm is not None]
        engagements = [r.engagement_score for r in runs if r.engagement_score is not None]
        conversions = [r.conversion_potential_score for r in runs if r.conversion_potential_score is not None]
        
        stats_by_product[category] = {
            "runs_count": len(runs),
            "avg_citation_rate": round(sum(citation_rates) / len(citation_rates), 2) if citation_rates else None,
            "avg_prominence": round(sum(prominences) / len(prominences), 2) if prominences else None,
            "avg_sov": round(sum(sovs) / len(sovs), 2) if sovs else None,
            "avg_engagement": round(sum(engagements) / len(engagements), 2) if engagements else None,
            "avg_conversion_potential": round(sum(conversions) / len(conversions), 2) if conversions else None,
        }
    
    return stats_by_product
