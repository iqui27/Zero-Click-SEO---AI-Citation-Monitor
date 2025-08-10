from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from app.models.models import Run, Citation, Insight, Domain


def generate_basic_insights(db: Session, run: Run) -> List[Insight]:
    """Gera insights heurísticos simples pós-run.
    - Se não houver citações do domínio alvo: sugerir FAQ/HowTo, atualizar conteúdos e comparativos
    - Se houver citações concorrentes recorrentes: sugerir página comparativa
    """
    insights: List[Insight] = []
    project_domains = {d.domain for d in db.query(Domain).filter(Domain.project_id == run.project_id).all()}
    citations = db.query(Citation).filter(Citation.run_id == run.id).all()
    our_hit = any(c.domain in project_domains for c in citations)

    if not our_hit:
        insights.append(Insight(
            project_id=run.project_id,
            run_id=run.id,
            title="Por que não citou?",
            description="Não encontramos citações ao seu domínio nesta resposta. Avalie adicionar FAQ/HowTo, atualizar conteúdo e páginas comparativas com concorrentes.",
            impact=3,
            effort=2,
            status="open",
        ))

    # Top concorrente desta run
    competitor_domains = [c.domain for c in citations if c.domain not in project_domains]
    if competitor_domains:
        top = competitor_domains[0]
        insights.append(Insight(
            project_id=run.project_id,
            run_id=run.id,
            title=f"Concorrente citado: {top}",
            description=f"Crie/otimize uma página comparativa com {top} e adicione dados estruturados (FAQ/HowTo).",
            impact=2,
            effort=2,
            status="open",
        ))

    return insights


