from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from app.models.models import Citation, Run
from app.schemas.schemas import RunReport, CitationOut
from app.services.normalization import normalize_domain, normalize_url_for_dedupe


def compute_amr(citations: List[Citation], our_domains: set[str]) -> float:
    # AMR: existe menção (link ou textual) a pelo menos um domínio nosso
    has_mention = any(c.domain in our_domains for c in citations)
    return 1.0 if has_mention else 0.0


def compute_dcr(citations: List[Citation], our_domains: set[str]) -> float:
    has_link = any(c.domain in our_domains and (c.type or "").lower() == "link" for c in citations)
    return 1.0 if has_link else 0.0


def compute_zcrs(citations: List[Citation]) -> float:
    # Heurística simplificada para MVP
    links_useful = sum(1 for c in citations if (c.type or "").lower() == "link")
    mentions = len(citations)
    pos_weight = 1.0
    score = 100 - (20 * links_useful + 10 * mentions + 5 * pos_weight)
    return max(0.0, min(100.0, float(score)))


def compute_run_report(db: Session, run_id: str) -> RunReport:
    run = db.get(Run, run_id)
    citations_raw = db.query(Citation).filter(Citation.run_id == run_id).all()

    # Dedup por URL normalizada
    unique: dict[str, Citation] = {}
    for c in citations_raw:
        url_norm = normalize_url_for_dedupe(c.url or c.domain or "")
        dom_norm = normalize_domain(url_norm)
        key = f"{dom_norm}|{(c.anchor or '').strip()}|{(c.type or '').strip()}"
        if key not in unique:
            # sobrescrever campos normalizados em memória (não persistente)
            c.url = url_norm
            c.domain = dom_norm
            unique[key] = c
    citations = list(unique.values())

    # Descobrir domínios do projeto
    from app.models.models import Domain, Project, Engine, PromptVersion, Prompt

    engine = db.get(Engine, run.engine_id)
    project = db.get(Project, run.project_id)
    domains = db.query(Domain).filter(Domain.project_id == project.id).all()
    our_domains = {d.domain for d in domains}

    amr = compute_amr(citations, our_domains)
    dcr = compute_dcr(citations, our_domains)
    zcrs = compute_zcrs(citations)

    run.amr_flag = amr == 1.0
    run.dcr_flag = dcr == 1.0
    run.zcrs = zcrs
    db.commit()

    return RunReport(
        id=run.id,
        amr=amr,
        dcr=dcr,
        zcrs=zcrs,
        citations=[
            CitationOut(
                domain=c.domain,
                url=c.url,
                anchor=c.anchor,
                position=c.position,
                type=c.type,
                is_ours=c.is_ours,
            )
            for c in citations
        ],
        reasons=[],
    )
