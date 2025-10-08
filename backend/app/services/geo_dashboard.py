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
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, desc, text
from collections import Counter, defaultdict
import json
import re
from urllib.parse import urlparse

from app.models.models import (
    Run,
    Citation,
    Entity,
    Evidence,
    SerpFeature,
    Project,
    Domain,
    PromptTemplate,
    SubProject,
    RunSemanticInsight,
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
) -> Dict[str, Any]:
    """
    Compute aggregated GEO dashboard data with filtering.

    Args:
        db: Database session
        project_id: Project ID (required)
        prompt_id: Optional filter by prompt
        prompt_version_id: Optional filter by prompt version
        subproject_id: Optional filter by subproject (produto)
        date_from: Optional start date filter
        date_to: Optional end date filter
        bank_ids: Optional list of bank domains/names to compare

    Returns:
        Dictionary with all dashboard sections
    """

    # Build base query with filters
    query = db.query(Run).filter(
        Run.project_id == project_id,
        Run.status == "completed"
    )

    if prompt_version_id:
        query = query.filter(Run.prompt_version_id == prompt_version_id)

    if subproject_id:
        query = query.filter(Run.subproject_id == subproject_id)

    if date_from:
        query = query.filter(func.date(Run.started_at) >= date_from)

    if date_to:
        query = query.filter(func.date(Run.started_at) <= date_to)

    runs = query.all()

    if not runs:
        return _empty_dashboard()

    run_ids = [r.id for r in runs]

    # Get project domains for "our" detection
    domains = db.query(Domain).filter(Domain.project_id == project_id).all()
    our_domains = {normalize_domain(d.domain) for d in domains if d.domain}

    # Aggregate data
    kpis = _compute_kpis(runs, our_domains, bank_ids)
    radar = _compute_radar(runs, bank_ids)
    positioning = _compute_positioning(db, run_ids, bank_ids)
    keywords_entities = _compute_keywords_entities(db, run_ids)
    panorama = _compute_panorama(runs, db, run_ids, bank_ids)
    web_structure = _compute_web_structure(db, run_ids, bank_ids)
    alerts = _compute_alerts(runs)
    swot = _compute_swot(runs)
    raw_samples = _get_raw_samples(db, run_ids, limit=10)

    return {
        "project_id": project_id,
        "filters_applied": {
            "prompt_id": prompt_id,
            "prompt_version_id": prompt_version_id,
            "subproject_id": subproject_id,
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "bank_ids": bank_ids,
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


def _compute_kpis(runs: List[Run], our_domains: set, bank_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Compute hero KPI metrics."""

    # Perception label mapping
    PERCEPTION_LABELS = {
        "inovacao": "Inovação & tecnologia",
        "tradicao": "Tradição & segurança",
        "custo": "Baixo custo",
        "atendimento": "Atendimento & relacionamento",
    }

    # Count AI Overview rankings (where brand is mentioned in AI Overview)
    ai_overview_count = sum(1 for r in runs if r.ia_resources_detected and r.ia_resources_detected > 0)

    # Count URL rankings (DCR flag) - Note: DCR is calculated at run time, so we use the flag
    url_ranking_count = sum(1 for r in runs if r.dcr_flag)

    # Total mentions
    total_mentions = sum(r.citations_count or 0 for r in runs)

    # Average EEAT score
    eeat_scores = [r.eeat_score for r in runs if r.eeat_score is not None]
    avg_eeat = sum(eeat_scores) / len(eeat_scores) if eeat_scores else 0

    # Most common perception
    perceptions = [r.perceived_value_category for r in runs if r.perceived_value_category]
    perception_counts = Counter(perceptions)
    top_perception_code = perception_counts.most_common(1)[0][0] if perception_counts else None
    top_perception = PERCEPTION_LABELS.get(top_perception_code, top_perception_code or "N/A")

    return [
        {"label": "Ranking AI Overview", "value": ai_overview_count, "total": len(runs), "unit": "runs"},
        {"label": "Ranking URLs", "value": url_ranking_count, "total": len(runs), "unit": "runs"},
        {"label": "Menções", "value": total_mentions, "unit": "total"},
        {"label": "E-E-A-T Médio", "value": round(avg_eeat, 1), "unit": "score"},
        {"label": "Percepção Principal", "value": top_perception, "unit": "category"},
    ]


def _compute_radar(runs: List[Run], bank_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Compute radar chart dimensions for selected banks."""

    # For MVP: aggregate all runs (single bank view)
    # TODO: Split by bank_ids when bank detection is implemented

    im_seo_scores = [r.im_seo_score for r in runs if r.im_seo_score is not None]
    im_seoia_scores = [r.im_seoia_score for r in runs if r.im_seoia_score is not None]
    irzc_scores = [r.irzc_score for r in runs if r.irzc_score is not None]
    eeat_scores = [r.eeat_score for r in runs if r.eeat_score is not None]
    cwv_scores = [r.core_web_vitals_score for r in runs if r.core_web_vitals_score is not None]
    ia_ready_scores = [r.ia_ready_score for r in runs if r.ia_ready_score is not None]

    return [
        {
            "bank": "Agregado",  # TODO: Split by actual banks
            "dimensions": [
                {"name": "IM-SEO", "value": sum(im_seo_scores) / len(im_seo_scores) if im_seo_scores else 0},
                {"name": "IM-SEO/IA", "value": sum(im_seoia_scores) / len(im_seoia_scores) if im_seoia_scores else 0},
                {"name": "IRZC", "value": sum(irzc_scores) / len(irzc_scores) if irzc_scores else 0},
                {"name": "E-E-A-T", "value": sum(eeat_scores) / len(eeat_scores) if eeat_scores else 0},
                {"name": "Core Web Vitals", "value": sum(cwv_scores) / len(cwv_scores) if cwv_scores else 0},
                {"name": "IA Ready", "value": sum(ia_ready_scores) / len(ia_ready_scores) if ia_ready_scores else 0},
            ]
        }
    ]


def _compute_positioning(db: Session, run_ids: List[str], bank_ids: Optional[List[str]]) -> Dict[str, Any]:
    """Compute brand ranking and perception breakdown."""

    # Get all citations from runs
    citations = db.query(Citation).filter(Citation.run_id.in_(run_ids)).all()

    # Count mentions by domain
    domain_counts = Counter(c.domain for c in citations if c.domain)

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
    }


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


def _compute_panorama(runs: List[Run], db: Session, run_ids: List[str], bank_ids: Optional[List[str]]) -> Dict[str, Any]:
    """Compute panorama cards and comparison chart."""

    # Calculate deltas
    im_seo_scores = [r.im_seo_score for r in runs if r.im_seo_score is not None]
    im_seoia_scores = [r.im_seoia_score for r in runs if r.im_seoia_score is not None]

    avg_im_seo = sum(im_seo_scores) / len(im_seo_scores) if im_seo_scores else 0
    avg_im_seoia = sum(im_seoia_scores) / len(im_seoia_scores) if im_seoia_scores else 0
    delta = avg_im_seoia - avg_im_seo

    # Count AI Overview, PAA, KP occurrences
    serp_features = db.query(SerpFeature).filter(SerpFeature.run_id.in_(run_ids)).all()

    ai_overview_count = sum(1 for sf in serp_features if sf.has_ai_overview)
    paa_count = sum(1 for sf in serp_features if sf.has_paa)
    kp_count = sum(1 for sf in serp_features if sf.has_knowledge_panel)

    cards = [
        {"label": "IM-SEO/IA vs IM-SEO", "value": round(delta, 2), "delta": round(delta, 2), "supporting": f"IM-SEO: {round(avg_im_seo, 1)}, IM-SEO/IA: {round(avg_im_seoia, 1)}"},
        {"label": "Total Runs", "value": len(runs)},
        {"label": "AI Overview", "value": ai_overview_count},
        {"label": "PAA", "value": paa_count},
        {"label": "Knowledge Panel", "value": kp_count},
    ]

    # Chart data (placeholder - should be per bank)
    chart = [
        {
            "bank": "Agregado",
            "ai_overview_count": ai_overview_count,
            "paa_count": paa_count,
            "kp_count": kp_count,
        }
    ]

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
        url_metadata_list = db.query(UrlMetadata).filter(
            UrlMetadata.url.in_(citation_urls),
            UrlMetadata.status == "success"
        ).all()
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
    """Generate SWOT analysis from aggregated metrics."""

    # Calculate averages
    avg_eeat = sum(r.eeat_score for r in runs if r.eeat_score) / len([r for r in runs if r.eeat_score]) if any(r.eeat_score for r in runs) else 0
    avg_ia_ready = sum(r.ia_ready_score for r in runs if r.ia_ready_score) / len([r for r in runs if r.ia_ready_score]) if any(r.ia_ready_score for r in runs) else 0
    dcr_rate = sum(1 for r in runs if r.dcr_flag) / len(runs) if runs else 0

    strengths = []
    weaknesses = []
    opportunities = []
    threats = []

    # Strengths
    if avg_eeat > 70:
        strengths.append(f"E-E-A-T forte (média {round(avg_eeat, 1)})")
    if dcr_rate > 0.5:
        strengths.append(f"Alta presença em citações ({round(dcr_rate*100, 1)}% DCR)")
    if avg_ia_ready > 70:
        strengths.append(f"Conteúdo bem estruturado para IA (score {round(avg_ia_ready, 1)})")

    # Weaknesses
    if avg_eeat < 50:
        weaknesses.append(f"E-E-A-T necessita melhorias (média {round(avg_eeat, 1)})")
    if dcr_rate < 0.3:
        weaknesses.append(f"Baixa presença em citações ({round(dcr_rate*100, 1)}% DCR)")

    # Opportunities
    if avg_ia_ready < 60:
        opportunities.append("Potencial de otimização para blocos IA-Ready")

    high_irzc = sum(1 for r in runs if r.irzc_score and r.irzc_score > 70) / len(runs) if runs else 0
    if high_irzc > 0.3:
        opportunities.append(f"Otimização para reduzir zero-click ({round(high_irzc*100, 1)}% alto IRZC)")

    # Threats
    if avg_eeat < 40:
        threats.append("Risco de perda de visibilidade por baixo E-E-A-T")

    return {
        "strengths": strengths or ["Análise em andamento"],
        "weaknesses": weaknesses or ["Nenhuma fraqueza crítica detectada"],
        "opportunities": opportunities or ["Análise em andamento"],
        "threats": threats or ["Nenhuma ameaça crítica detectada"],
    }


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
