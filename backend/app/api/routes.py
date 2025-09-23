from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, text, literal_column, and_, or_, Date, select, case
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta
from croniter import croniter
import asyncio
import threading
import io
import csv
import os

from app.db.session import SessionLocal
from app.core.config import settings
from app.models.models import Project, Domain, Prompt, PromptVersion, Engine, Run, Citation, Reason, Evidence, RunEvent, SubProject, PromptTemplate, Monitor, MonitorTemplate, MonitorHistory, MonitorHistoryRun, Insight
from app.schemas.schemas import (
    ProjectCreate,
    ProjectOut,
    DomainCreate,
    DomainOut,
    PromptCreate,
    PromptOut,
    PromptVersionCreate,
    PromptVersionOut,
    EngineCreate,
    EngineOut,
    RunCreate,
    RunOut,
    RunListItem,
    RunDetailOut,
    RunReport,
    CitationOut,
    EvidenceOut,
    OverviewAnalytics,
    RunsBySubprojectGroup,
    GroupedRunWithEvidences,
)
from app.services.tasks import enqueue_run
from app.services.scheduler import stop_scheduler, start_scheduler
from app.services.kpis import compute_run_report
from app.services.engine_runner import run_engine
from app.services.insights import generate_basic_insights, generate_subproject_insights as svc_generate_subproject_insights
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.sql import case
from typing import Any, Dict, List

# LLM (OpenAI) para geração de insights agregados
try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore
import os
from pathlib import Path

api_router = APIRouter()


# Dependency

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@api_router.post("/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        name=payload.name,
        country=payload.country,
        language=payload.language,
        timezone=payload.timezone,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectOut(id=project.id, **payload.dict())


@api_router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    return [ProjectOut(id=p.id, name=p.name, country=p.country, language=p.language, timezone=p.timezone) for p in projects]


@api_router.patch("/projects/{project_id}")
def update_project(project_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    # Campos permitidos para atualização
    for field in ["name", "country", "language", "timezone"]:
        if field in payload and payload[field] is not None:
            setattr(project, field, payload[field])
    db.commit()
    db.refresh(project)
    return ProjectOut(id=project.id, name=project.name, country=project.country, language=project.language, timezone=project.timezone)


@api_router.delete("/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    # Pausar scheduler para evitar criação concorrente de runs durante a deleção
    try:
        stop_scheduler()
    except Exception:
        pass
    # Remover Insights vinculados ao projeto para evitar restrição de FK (NO ACTION)
    db.query(Insight).filter(Insight.project_id == project_id).delete(synchronize_session=False)
    # 1) Apagar monitores e vínculos de templates do projeto (e desassociar runs deles)
    mon_ids = [mid for (mid,) in db.query(Monitor.id).filter(Monitor.project_id == project_id).all()]
    if mon_ids:
        # Desativar monitores imediatamente para evitar novos disparos
        db.query(Monitor).filter(Monitor.id.in_(mon_ids)).update({Monitor.active: False}, synchronize_session=False)
        db.commit()
        try:
            db.query(Run).filter(Run.project_id == project_id).update({Run.monitor_id: None}, synchronize_session=False)
        except Exception:
            pass
        db.query(MonitorTemplate).filter(MonitorTemplate.monitor_id.in_(mon_ids)).delete(synchronize_session=False)
        db.query(Monitor).filter(Monitor.id.in_(mon_ids)).delete(synchronize_session=False)
        db.commit()
    # 2) Coletar IDs de runs do projeto e apagar dependências + runs
    # (após remover monitores, não haverá novas runs sendo criadas por scheduler)
    # Tentar repetidamente esvaziar todas as runs (tratando condições de corrida)
    for _ in range(5):
        run_ids = [rid for (rid,) in db.query(Run.id).filter(Run.project_id == project_id).all()]
        if not run_ids:
            break
        # Apagar dependências de runs (defensivo para SQL Server quando FKs não estão com CASCADE)
        db.query(Evidence).filter(Evidence.run_id.in_(run_ids)).delete(synchronize_session=False)
        db.query(Citation).filter(Citation.run_id.in_(run_ids)).delete(synchronize_session=False)
        db.query(Reason).filter(Reason.run_id.in_(run_ids)).delete(synchronize_session=False)
        db.query(RunEvent).filter(RunEvent.run_id.in_(run_ids)).delete(synchronize_session=False)
        # Zerar vínculos de insights com runs (caso existam)
        try:
            db.query(Insight).filter(Insight.run_id.in_(run_ids)).update({Insight.run_id: None}, synchronize_session=False)
        except Exception:
            pass
        # Por fim, apagar as runs
        db.query(Run).filter(Run.id.in_(run_ids)).delete(synchronize_session=False)
        db.commit()

    # Apagar engines do projeto: garantir que não existam runs referenciando-os
    eng_ids = [eid for (eid,) in db.query(Engine.id).filter(Engine.project_id == project_id).all()]
    if eng_ids:
        # Se, por alguma razão, restaram runs, apague-as agora por engine_id
        db.query(Run).filter(Run.engine_id.in_(eng_ids)).delete(synchronize_session=False)
        db.commit()
        db.query(Engine).filter(Engine.id.in_(eng_ids)).delete(synchronize_session=False)

    # Apagar prompts/prompt_versions ligados ao projeto (defensivo)
    pr_ids = [pid for (pid,) in db.query(Prompt.id).filter(Prompt.project_id == project_id).all()]
    if pr_ids:
        db.query(PromptVersion).filter(PromptVersion.prompt_id.in_(pr_ids)).delete(synchronize_session=False)
        db.query(Prompt).filter(Prompt.id.in_(pr_ids)).delete(synchronize_session=False)

    # Apagar domínios e subprojetos (defensivo, caso FKs não estejam com CASCADE)
    db.query(Domain).filter(Domain.project_id == project_id).delete(synchronize_session=False)
    db.query(SubProject).filter(SubProject.project_id == project_id).delete(synchronize_session=False)

    db.commit()
    # Por fim, apagar o projeto
    db.delete(project)
    db.commit()
    # Tentar religar o scheduler em background
    try:
        def _restart_scheduler_bg():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start_scheduler())
        threading.Thread(target=_restart_scheduler_bg, daemon=True).start()
    except Exception:
        pass
    return {"ok": True}


@api_router.post("/monitors/{monitor_id}/stop")
def stop_monitor(monitor_id: str, db: Session = Depends(get_db)):
    mon = db.get(Monitor, monitor_id)
    if not mon:
        raise HTTPException(status_code=404, detail="Monitor não encontrado")
    # Desativar
    mon.active = False
    db.commit()
    # Cancelar runs ainda não iniciadas (queued)
    now = datetime.utcnow()
    queued = (
        db.query(Run)
        .filter(Run.monitor_id == monitor_id, Run.status == "queued")
        .all()
    )
    for r in queued:
        r.status = "failed"
        r.error_code = "user_cancelled"
        r.finished_at = now
        db.add(RunEvent(run_id=r.id, version="error", status="fail", message="Stopped by user"))
    db.commit()
    return {"ok": True, "queued_cancelled": len(queued)}


@api_router.get("/monitors/{monitor_id}/stats")
def monitor_stats(monitor_id: str, days: int = 7, db: Session = Depends(get_db)):
    days = max(1, min(int(days or 7), 90))
    since = datetime.utcnow() - timedelta(days=days)
    # Resumo por dia
    date_col = func.cast(Run.started_at, Date)
    rows = (
        db.query(
            date_col.label("date"),
            func.count(Run.id).label("total"),
            func.sum(case((Run.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Run.status == "failed", 1), else_=0)).label("failed"),
        )
        .filter(Run.monitor_id == monitor_id, Run.started_at >= since)
        .group_by(date_col)
        .order_by(date_col.desc())
        .all()
    )
    # Totais gerais
    total = db.query(func.count(Run.id)).filter(Run.monitor_id == monitor_id, Run.started_at >= since).scalar() or 0
    completed = db.query(func.count(Run.id)).filter(Run.monitor_id == monitor_id, Run.started_at >= since, Run.status == "completed").scalar() or 0
    failed = db.query(func.count(Run.id)).filter(Run.monitor_id == monitor_id, Run.started_at >= since, Run.status == "failed").scalar() or 0
    return {
        "since": since.isoformat(),
        "totals": {"total": int(total), "completed": int(completed), "failed": int(failed)},
        "by_day": [
            {"date": str(r.date), "total": int(r.total or 0), "completed": int(r.completed or 0), "failed": int(r.failed or 0)}
            for r in rows
        ],
    }


@api_router.delete("/monitors/{monitor_id}/runs")
def delete_monitor_runs(monitor_id: str, db: Session = Depends(get_db)):
    mon = db.get(Monitor, monitor_id)
    if not mon:
        raise HTTPException(status_code=404, detail="Monitor não encontrado")
    run_ids = [rid for (rid,) in db.query(Run.id).filter(Run.monitor_id == monitor_id).all()]
    if not run_ids:
        return {"deleted": 0}
    # apagar dependências
    db.query(Evidence).filter(Evidence.run_id.in_(run_ids)).delete(synchronize_session=False)
    db.query(Citation).filter(Citation.run_id.in_(run_ids)).delete(synchronize_session=False)
    db.query(Reason).filter(Reason.run_id.in_(run_ids)).delete(synchronize_session=False)
    db.query(RunEvent).filter(RunEvent.run_id.in_(run_ids)).delete(synchronize_session=False)
    # apagar runs
    db.query(Run).filter(Run.id.in_(run_ids)).delete(synchronize_session=False)
    db.commit()
    return {"deleted": len(run_ids)}

@api_router.post("/projects/{project_id}/domains", response_model=DomainOut)
def add_domain(project_id: str, payload: DomainCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    domain = Domain(project_id=project_id, domain=payload.domain, pattern_regex=payload.pattern_regex, is_primary=payload.is_primary)
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return DomainOut(id=domain.id, project_id=project_id, **payload.dict())


@api_router.get("/projects/{project_id}/domains")
def list_domains(project_id: str, db: Session = Depends(get_db)):
    domains = db.query(Domain).filter(Domain.project_id == project_id).all()
    return [
        {
            "id": d.id,
            "domain": d.domain,
            "pattern_regex": d.pattern_regex,
            "is_primary": d.is_primary,
        }
        for d in domains
    ]


@api_router.get("/monitors/{monitor_id}/export.csv")
def export_monitor_runs_csv(monitor_id: str, db: Session = Depends(get_db)):
    """Exporta CSV com runs do monitor incluindo resposta (texto) e citações.
    Somente inclui runs que possuem resposta não vazia (parsed.text).
    """
    # Subconsulta: existe Evidence com parsed.text não nulo/não vazio?
    txt = func.json_value(Evidence.parsed_json, '$.parsed.text')
    subq = (
        select(1)
        .select_from(Evidence)
        .where(Evidence.run_id == Run.id)
        .where(txt.isnot(None))
        .where(func.ltrim(func.rtrim(txt)) != '')
    )

    rows = (
        db.query(
            Run.id,
            Run.project_id,
            Run.subproject_id,
            SubProject.name.label("subproject_name"),
            Run.started_at,
            Run.finished_at,
            Run.status,
            Run.zcrs,
            Run.amr_flag,
            Run.dcr_flag,
            Run.tokens_total,
            Run.cost_usd,
            Run.model_name,
            Engine.name.label("engine"),
            PromptVersion.id.label("prompt_version_id"),
            PromptVersion.text.label("prompt_text"),
            Prompt.id.label("prompt_id"),
            Prompt.name.label("prompt_name"),
        )
        .join(Engine, Engine.id == Run.engine_id)
        .outerjoin(PromptVersion, PromptVersion.id == Run.prompt_version_id)
        .outerjoin(Prompt, Prompt.id == PromptVersion.prompt_id)
        .outerjoin(SubProject, SubProject.id == Run.subproject_id)
        .filter(Run.monitor_id == monitor_id)
        .filter(subq.exists())
        .order_by(
            case((Run.started_at.is_(None), 1), else_=0).asc(),
            Run.started_at.asc(),
            Run.id.asc(),
        )
        .all()
    )

    run_ids = [r.id for r in rows]

    # Mapear evidência com texto por run (prioriza a mais recente com texto)
    ev_map: dict[str, Evidence] = {}
    if run_ids:
        evs = (
            db.query(Evidence)
            .filter(Evidence.run_id.in_(run_ids))
            .order_by(Evidence.id.desc())
            .all()
        )
        for ev in evs:
            if ev.run_id in ev_map:
                continue
            try:
                parsed = (ev.parsed_json or {}).get("parsed") if isinstance(ev.parsed_json, dict) else {}
                text_val = (parsed or {}).get("text") if isinstance(parsed, dict) else None
                if (text_val or "").strip():
                    ev_map[ev.run_id] = ev
            except Exception:
                continue

    # Coletar citações por run
    cits_by_run: dict[str, list[tuple[str | None, str | None, bool]] ] = {}
    if run_ids:
        cits = (
            db.query(Citation.run_id, Citation.domain, Citation.url, Citation.is_ours)
            .filter(Citation.run_id.in_(run_ids))
            .all()
        )
        for rid, dom, url, is_ours in cits:
            cits_by_run.setdefault(rid, []).append((dom, url, bool(is_ours)))

    # Mapear AI Overview por run (último link explícito; para google_serp usar o próprio run_id)
    ai_map: dict[str, str] = {}
    if run_ids:
        ev_ai = (
            db.query(RunEvent.run_id, RunEvent.message, RunEvent.created_at)
            .filter(RunEvent.run_id.in_(run_ids), RunEvent.version == "ai_overview_link")
            .order_by(RunEvent.run_id.asc(), RunEvent.created_at.desc())
            .all()
        )
        for rid, msg, _ in ev_ai:
            if rid not in ai_map and (msg or "").strip():
                ai_map[rid] = (msg or "").strip()
        for r in rows:
            try:
                if (getattr(r, "engine", "") or "").lower() == "google_serp" and r.id not in ai_map:
                    ai_map[r.id] = r.id
            except Exception:
                continue

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "run_id",
        "monitor_id",
        "project_id",
        "subproject_id",
        "tema",
        "engine",
        "status",
        "started_at",
        "finished_at",
        "model",
        "tokens_total",
        "cost_usd",
        "zcrs",
        "amr",
        "dcr",
        "prompt_id",
        "prompt_name",
        "prompt_version_id",
        "prompt_text",
        "ai_overview_run_id",
        "categoria",
        "response_text",
        "citations_domains",
        "citations_urls",
        "citations_is_ours",
    ])

    # Preparar mapa de categoria por (project_id, template_name) inferindo do prompt_name (remove prefixo 'Run: ')
    def _norm_name(n: str | None) -> str | None:
        if not n:
            return None
        s = n.strip()
        if s.lower().startswith("run: "):
            s = s[5:].strip()
        return s

    proj_to_names: dict[str, set[str]] = {}
    for r in rows:
        pn = getattr(r, "prompt_name", None)
        nn = _norm_name(pn)
        if nn:
            proj_to_names.setdefault(r.project_id, set()).add(nn)
    cat_map: dict[tuple[str, str], str] = {}
    for pid, names in proj_to_names.items():
        if not names:
            continue
        for tpl in db.query(PromptTemplate).filter(
            PromptTemplate.project_id == pid,
            PromptTemplate.name.in_(list(names))
        ).all():
            cat_map[(tpl.project_id, tpl.name)] = tpl.category

    for r in rows:
        rid = r.id
        # Extrair texto de resposta da evidência mais recente
        ev = ev_map.get(rid)
        parsed = (ev.parsed_json or {}).get("parsed") if ev and isinstance(ev.parsed_json, dict) else {}
        text_val = (parsed or {}).get("text") if isinstance(parsed, dict) else None
        text_str = (text_val or "").strip()
        if not text_str:
            # Defesa extra (deveria ter sido filtrado pela subconsulta)
            continue

        # Agregar citações
        cits = cits_by_run.get(rid, [])
        doms = [d or "" for (d, _u, _ours) in cits if d]
        urls = [u or "" for (_d, u, _ours) in cits if u]

        pn = getattr(r, "prompt_name", None)
        nn = _norm_name(pn)
        category = cat_map.get((r.project_id, nn or ""), "") if nn else ""
        writer.writerow([
            rid,
            str(monitor_id),
            r.project_id,
            r.subproject_id or "",
            getattr(r, "subproject_name", None) or "",
            getattr(r, "engine", None) or "",
            r.status or "",
            r.started_at.isoformat() if r.started_at else "",
            r.finished_at.isoformat() if r.finished_at else "",
            getattr(r, "model_name", None) or "",
            int(r.tokens_total) if getattr(r, "tokens_total", None) is not None else "",
            float(r.cost_usd) if getattr(r, "cost_usd", None) is not None else "",
            r.zcrs if r.zcrs is not None else "",
            (1 if r.amr_flag else 0) if r.amr_flag is not None else "",
            (1 if r.dcr_flag else 0) if r.dcr_flag is not None else "",
            getattr(r, "prompt_id", None) or "",
            pn or "",
            getattr(r, "prompt_version_id", None) or "",
            getattr(r, "prompt_text", None) or "",
            ai_map.get(rid, ""),
            category,
            text_str,
            " ".join(doms),
            " ".join(urls),
        ])

    buf.seek(0)
    headers = {"Content-Disposition": f"attachment; filename=monitor_{monitor_id}_responses_citations.csv"}
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)


@api_router.get("/runs/count")
def count_runs(
    db: Session = Depends(get_db),
    project_id: str | None = None,
    subproject_id: str | None = None,
    engine: str | None = None,
    status: str | None = None,
    schedule_source: str | None = None,
    monitor_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    has_text: bool | None = None,
):
    q = db.query(func.count(Run.id))
    q = q.select_from(Run)
    # Join with Engine only if filtering by engine name to avoid duplicates
    if engine:
        q = q.join(Engine, Engine.id == Run.engine_id)
        q = q.filter(Engine.name == engine)

    if project_id:
        q = q.filter(Run.project_id == project_id)
    if subproject_id:
        q = q.filter(Run.subproject_id == subproject_id)
    if status:
        q = q.filter(Run.status == status)
    if schedule_source:
        q = q.filter(Run.schedule_source == schedule_source)
    if monitor_id:
        q = q.filter(Run.monitor_id == monitor_id)
    if date_from:
        q = q.filter(Run.started_at >= text(":df")).params(df=date_from)
    if date_to:
        q = q.filter(Run.started_at <= text(":dt")).params(dt=date_to)
    if has_text:
        txt = func.json_value(Evidence.parsed_json, '$.text')
        subq = (
            select(1)
            .select_from(Evidence)
            .where(Evidence.run_id == Run.id)
            .where(txt.isnot(None))
            .where(func.ltrim(func.rtrim(txt)) != '')
        )
        q = q.filter(subq.exists())

    total = q.scalar() or 0
    return {"count": int(total)}


@api_router.delete("/domains/{domain_id}")
def delete_domain(domain_id: str, db: Session = Depends(get_db)):
    d = db.get(Domain, domain_id)
    if not d:
        raise HTTPException(status_code=404, detail="Domínio não encontrado")
    db.delete(d)
    db.commit()
    return {"ok": True}


def _stream_runs_full_csv(db: Session, run_ids: list[str], filename: str) -> StreamingResponse:
    if not run_ids:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "run_id","project_id","subproject_id","engine","model","status","started_at","finished_at","cycles_total","zcrs",
            "tokens_input","tokens_output","tokens_total","cost_usd","latency_ms","citations_count","our_citations_count","unique_domains_count","error_code",
            "schedule_date","schedule_slot","schedule_index_today","schedule_total_today","schedule_source",
            "prompt_id","prompt_name","prompt_version_id","prompt_text","ai_overview_run_id","response_text","screenshot_url",
            "cit_domain","cit_url","cit_anchor","cit_position","cit_type","cit_is_ours","citations_is_ours",
        ])
        buf.seek(0)
        headers = {"Content-Disposition": f"attachment; filename={filename}"}
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)

    # Core run info with joins
    rows = (
        db.query(
            Run.id,
            Run.project_id,
            Run.subproject_id,
            SubProject.name.label("subproject_name"),
            Run.status,
            Run.started_at,
            Run.finished_at,
            Run.cycles_total,
            Run.zcrs,
            Run.tokens_input,
            Run.tokens_output,
            Run.tokens_total,
            Run.cost_usd,
            Run.latency_ms,
            Run.citations_count,
            Run.our_citations_count,
            Run.unique_domains_count,
            Run.model_name,
            Run.error_code,
            Run.schedule_date,
            Run.schedule_slot,
            Run.schedule_index_today,
            Run.schedule_total_today,
            Run.schedule_source,
            PromptVersion.id.label("prompt_version_id"),
            PromptVersion.text.label("prompt_text"),
            Prompt.id.label("prompt_id"),
            Prompt.name.label("prompt_name"),
            Engine.name.label("engine"),
        )
        .join(Engine, Engine.id == Run.engine_id)
        .outerjoin(PromptVersion, PromptVersion.id == Run.prompt_version_id)
        .outerjoin(Prompt, Prompt.id == PromptVersion.prompt_id)
        .outerjoin(SubProject, SubProject.id == Run.subproject_id)
        .filter(Run.id.in_(run_ids))
        .order_by(
            case((Run.started_at.is_(None), 1), else_=0).asc(),
            Run.started_at.asc(),
            Run.id.asc(),
        )
        .all()
    )

    # Evidence maps (response text and screenshot_url)
    ev_text: dict[str, str] = {}
    ev_shot: dict[str, str] = {}
    evs = (
        db.query(Evidence)
        .filter(Evidence.run_id.in_(run_ids))
        .order_by(Evidence.id.desc())
        .all()
    )
    for ev in evs:
        rid = ev.run_id
        if rid not in ev_text:
            try:
                parsed = (ev.parsed_json or {}).get("parsed") if isinstance(ev.parsed_json, dict) else {}
                text_val = (parsed or {}).get("text") if isinstance(parsed, dict) else None
                if (text_val or "").strip():
                    ev_text[rid] = str(text_val).strip()
            except Exception:
                pass
        if rid not in ev_shot and (ev.screenshot_url or "").strip():
            ev_shot[rid] = ev.screenshot_url or ""

    # Citations by run
    cit_rows = (
        db.query(Citation.run_id, Citation.domain, Citation.url, Citation.anchor, Citation.position, Citation.type, Citation.is_ours)
        .filter(Citation.run_id.in_(run_ids))
        .order_by(Citation.run_id.asc(), Citation.id.asc())
        .all()
    )
    cits_by_run: dict[str, list[tuple[str | None, str | None, str | None, str | None, str | None, bool]] ] = {}
    for rid, dom, url, anchor, position, ctype, is_ours in cit_rows:
        cits_by_run.setdefault(rid, []).append((dom, url, anchor, position, ctype, bool(is_ours)))

    # Aggregate boolean per run: any citation is ours?
    any_ours_by_run: dict[str, bool] = {rid: any(flag for (_d, _u, _a, _p, _t, flag) in lst) for rid, lst in cits_by_run.items()}

    # AI Overview mapping (explicit link or self if google_serp)
    ai_map: dict[str, str] = {}
    if run_ids:
        ev_ai = (
            db.query(RunEvent.run_id, RunEvent.message, RunEvent.created_at)
            .filter(RunEvent.run_id.in_(run_ids), RunEvent.version == "ai_overview_link")
            .order_by(RunEvent.run_id.asc(), RunEvent.created_at.desc())
            .all()
        )
        for rid, msg, _ in ev_ai:
            if rid not in ai_map and (msg or "").strip():
                ai_map[rid] = (msg or "").strip()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "run_id","project_id","subproject_id","engine","model","status","started_at","finished_at","cycles_total","zcrs",
        "tokens_input","tokens_output","tokens_total","cost_usd","latency_ms","citations_count","our_citations_count","unique_domains_count","error_code",
        "schedule_date","schedule_slot","schedule_index_today","schedule_total_today","schedule_source",
        "prompt_id","prompt_name","prompt_version_id","prompt_text","ai_overview_run_id","tema","categoria","response_text","screenshot_url",
        "cit_domain","cit_url","cit_anchor","cit_position","cit_type","cit_is_ours","citations_is_ours",
    ])
    # Build category map from PromptTemplate by normalizing Prompt.name (strip 'Run: ')
    def _norm_name(n: str | None) -> str | None:
        if not n:
            return None
        s = n.strip()
        if s.lower().startswith("run: "):
            s = s[5:].strip()
        return s
    proj_to_names: dict[str, set[str]] = {}
    for r in rows:
        pn = getattr(r, "prompt_name", None)
        nn = _norm_name(pn)
        if nn:
            proj_to_names.setdefault(r.project_id, set()).add(nn)
    cat_map: dict[tuple[str, str], str] = {}
    for pid, names in proj_to_names.items():
        if not names:
            continue
        for tpl in db.query(PromptTemplate).filter(
            PromptTemplate.project_id == pid,
            PromptTemplate.name.in_(list(names))
        ).all():
            cat_map[(tpl.project_id, tpl.name)] = tpl.category
    for r in rows:
        rid = r.id
        # default ai_overview: explicit link; for google_serp runs, fallback to own run_id
        ai_overview_id = ai_map.get(rid, "")
        try:
            if not ai_overview_id and (getattr(r, "engine", "") or "").lower() == "google_serp":
                ai_overview_id = rid
        except Exception:
            ai_overview_id = ai_overview_id or ""

        base = [
            r.id,
            r.project_id,
            r.subproject_id,
            getattr(r, "engine", None) or "",
            r.model_name or "",
            r.status or "",
            r.started_at.isoformat() if r.started_at else "",
            r.finished_at.isoformat() if r.finished_at else "",
            r.cycles_total or "",
            r.zcrs if r.zcrs is not None else "",
            r.tokens_input if r.tokens_input is not None else "",
            r.tokens_output if r.tokens_output is not None else "",
            r.tokens_total if r.tokens_total is not None else "",
            float(r.cost_usd) if r.cost_usd is not None else "",
            r.latency_ms if r.latency_ms is not None else "",
            r.citations_count if r.citations_count is not None else "",
            r.our_citations_count if r.our_citations_count is not None else "",
            r.unique_domains_count if r.unique_domains_count is not None else "",
            r.error_code or "",
            r.schedule_date.isoformat() if r.schedule_date else "",
            r.schedule_slot or "",
            r.schedule_index_today if r.schedule_index_today is not None else "",
            r.schedule_total_today if r.schedule_total_today is not None else "",
            r.schedule_source or "",
            getattr(r, "prompt_id", None) or "",
            getattr(r, "prompt_name", None) or "",
            getattr(r, "prompt_version_id", None) or "",
            getattr(r, "prompt_text", None) or "",
            ai_overview_id,
            getattr(r, "subproject_name", None) or "",
            (cat_map.get((r.project_id, _norm_name(getattr(r, "prompt_name", None)) or ""), "") if getattr(r, "prompt_name", None) else ""),
            ev_text.get(rid, ""),
            ev_shot.get(rid, ""),
        ]
        cits = cits_by_run.get(rid, [])
        any_ours = any_ours_by_run.get(rid, False)
        if not cits:
            writer.writerow(base + ["", "", "", "", "", "", "true" if any_ours else "false"])  # no citations
        else:
            for (dom, url, anchor, pos, ctype, is_ours) in cits:
                writer.writerow(base + [dom or "", url or "", anchor or "", pos or "", ctype or "", 1 if is_ours else 0, "true" if any_ours else "false"]) 

    buf.seek(0)
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)


@api_router.get("/monitors/{monitor_id}/export_full.csv")
def export_monitor_runs_full_csv(monitor_id: str, db: Session = Depends(get_db)):
    run_ids = [rid for (rid,) in db.query(Run.id).filter(Run.monitor_id == monitor_id).all()]
    return _stream_runs_full_csv(db, run_ids, f"monitor_{monitor_id}_runs_full.csv")


@api_router.get("/monitors/history/{monitor_id}/export_full.csv")
def export_deleted_monitor_runs_full_csv(monitor_id: str, db: Session = Depends(get_db)):
    # Lookup explicit mapping
    rid_map = [rid for (rid,) in db.query(MonitorHistoryRun.run_id).filter(MonitorHistoryRun.history_monitor_id == monitor_id).all()]
    if not rid_map:
        # Fallback: infer by project/subproject if available
        h = db.query(MonitorHistory).filter(MonitorHistory.monitor_id == monitor_id).first()
        if not h:
            raise HTTPException(status_code=404, detail="Monitor (histórico) não encontrado")
        q = (
            db.query(Run.id)
            .outerjoin(Monitor, Monitor.id == Run.monitor_id)
            .filter(Monitor.id.is_(None))
            .filter(Run.project_id == h.project_id)
        )
        q = q.filter(or_(Run.schedule_source == "monitor", Run.schedule_source == "monitor_now"))
        if h.subproject_id:
            q = q.filter(Run.subproject_id == h.subproject_id)
        rid_map = [rid for (rid,) in q.all()]
    return _stream_runs_full_csv(db, rid_map, f"deleted_monitor_{monitor_id}_runs_full.csv")


@api_router.get("/monitors/history/inferred_export_full.csv")
def export_inferred_monitor_runs_full_csv(project_id: str, subproject_id: str | None = None, db: Session = Depends(get_db)):
    q = (
        db.query(Run.id)
        .outerjoin(Monitor, Monitor.id == Run.monitor_id)
        .filter(Monitor.id.is_(None))
        .filter(Run.project_id == project_id)
        .filter(
            or_(
                Run.schedule_source == "monitor",
                Run.schedule_source == "monitor_now",
                and_(Run.schedule_source.is_(None), Run.schedule_slot.isnot(None)),
            )
        )
    )
    if subproject_id:
        q = q.filter(Run.subproject_id == subproject_id)
    ids = [rid for (rid,) in q.all()]
    sp_suffix = subproject_id or "none"
    return _stream_runs_full_csv(db, ids, f"inferred_pre_snapshot_{project_id}_{sp_suffix}_runs_full.csv")


@api_router.get("/monitors/history")
def monitors_history(project_id: str | None = None, db: Session = Depends(get_db)):
    """Lista monitores ativos (com contagem ao vivo) e monitores deletados (via MonitorHistory).
    Campos: monitor_id, name, status (active|deleted), runs_total, runs_completed, runs_failed, deleted_at?, project_id
    """
    out: list[dict] = []
    # Active monitors with live counts
    mons_q = db.query(Monitor)
    if project_id:
        mons_q = mons_q.filter(Monitor.project_id == project_id)
    mons = mons_q.all()
    active_ids = [m.id for m in mons]
    counts_map: dict[str, dict] = {}
    if active_ids:
        agg = (
            db.query(
                Run.monitor_id.label("mid"),
                func.count(Run.id).label("total"),
                func.sum(case((Run.status == "completed", 1), else_=0)).label("completed"),
                func.sum(case((Run.status == "failed", 1), else_=0)).label("failed"),
            )
            .filter(Run.monitor_id.in_(active_ids))
            .group_by(Run.monitor_id)
            .all()
        )
        for row in agg:
            counts_map[row.mid] = {
                "total": int(row.total or 0),
                "completed": int(row.completed or 0),
                "failed": int(row.failed or 0),
            }
    for m in mons:
        c = counts_map.get(m.id, {"total": 0, "completed": 0, "failed": 0})
        out.append({
            "monitor_id": m.id,
            "project_id": m.project_id,
            "subproject_id": m.subproject_id,
            "name": m.name,
            "status": "active",
            "runs_total": c["total"],
            "runs_completed": c["completed"],
            "runs_failed": c["failed"],
            "deleted_at": None,
            "inferred": False,
        })
    # Deleted monitors from history
    hist_q = db.query(MonitorHistory)
    if project_id:
        hist_q = hist_q.filter(MonitorHistory.project_id == project_id)
    for h in hist_q.order_by(MonitorHistory.deleted_at.desc()).all():
        out.append({
            "monitor_id": h.monitor_id,
            "project_id": h.project_id,
            "subproject_id": h.subproject_id,
            "name": h.name,
            "status": "deleted",
            "runs_total": int(h.runs_total or 0),
            "runs_completed": int(h.runs_completed or 0),
            "runs_failed": int(h.runs_failed or 0),
            "deleted_at": h.deleted_at,
            "inferred": False,
        })
    # Backfill for orphan runs (pre-snapshot): runs with monitor_id NULL but schedule_source from monitor
    orphan_q = (
        db.query(
            Run.project_id.label("pid"),
            Run.subproject_id.label("spid"),
            func.count(Run.id).label("total"),
            func.sum(case((Run.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Run.status == "failed", 1), else_=0)).label("failed"),
        )
        .outerjoin(Monitor, Monitor.id == Run.monitor_id)
        .filter(Monitor.id.is_(None))
        .filter(
            or_(
                Run.schedule_source == "monitor",
                Run.schedule_source == "monitor_now",
                and_(Run.schedule_source.is_(None), Run.schedule_slot.isnot(None)),
            )
        )
    )
    if project_id:
        orphan_q = orphan_q.filter(Run.project_id == project_id)
    orphan_rows = orphan_q.group_by(Run.project_id, Run.subproject_id).all()
    # Map subproject_id -> name
    sp_names: dict[str | None, str] = {}
    sp_ids = [r.spid for r in orphan_rows if r.spid]
    if sp_ids:
        for sp in db.query(SubProject).filter(SubProject.id.in_(sp_ids)).all():
            sp_names[sp.id] = sp.name
    for r in orphan_rows:
        spid = getattr(r, "spid", None)
        pid = getattr(r, "pid", None)
        name = sp_names.get(spid) if spid else None
        label = f"Pré-snapshot (Tema: {name})" if name else "Pré-snapshot (Tema: —)"
        out.append({
            "monitor_id": f"inferred_pre_snapshot_{pid or 'p'}_{spid or 'none'}",
            "project_id": pid,
            "subproject_id": spid,
            "name": label,
            "status": "deleted",
            "runs_total": int(getattr(r, "total", 0) or 0),
            "runs_completed": int(getattr(r, "completed", 0) or 0),
            "runs_failed": int(getattr(r, "failed", 0) or 0),
            "deleted_at": None,
            "inferred": True,
        })
    # Sort by status (deleted last) and name for stability
    out.sort(key=lambda x: (0 if x["status"] == "active" else 1, (x["name"] or "~").lower()))
    return out


@api_router.get("/monitors/history.csv")
def monitors_history_csv(project_id: str | None = None, db: Session = Depends(get_db)):
    items = monitors_history(project_id=project_id, db=db)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["monitor_id", "project_id", "name", "status", "runs_total", "runs_completed", "runs_failed", "deleted_at"])
    for it in items:
        writer.writerow([
            it.get("monitor_id", ""),
            it.get("project_id", ""),
            it.get("name", ""),
            it.get("status", ""),
            it.get("runs_total", 0),
            it.get("runs_completed", 0),
            it.get("runs_failed", 0),
            (it.get("deleted_at").isoformat() if it.get("deleted_at") else ""),
        ])
    buf.seek(0)
    headers = {"Content-Disposition": "attachment; filename=monitors_history.csv"}
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)


@api_router.post("/projects/{project_id}/prompts", response_model=PromptOut)
def create_prompt(project_id: str, payload: PromptCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    prompt = Prompt(
        project_id=project_id,
        name=payload.name,
        text=payload.text,
        intent=payload.intent,
        persona=payload.persona,
        variables_json=payload.variables or None,
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    # create first version
    pv = PromptVersion(prompt_id=prompt.id, version=1, text=payload.text)
    db.add(pv)
    db.commit()

    return PromptOut(
        id=prompt.id,
        project_id=project_id,
        name=prompt.name,
        text=prompt.text,
        intent=prompt.intent,
        persona=prompt.persona,
        active=prompt.active,
    )


@api_router.get("/prompts/{prompt_id}/versions/latest", response_model=PromptVersionOut)
def get_latest_prompt_version(prompt_id: str, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt não encontrado")
    v = (
        db.query(PromptVersion)
        .filter(PromptVersion.prompt_id == prompt_id)
        .order_by(PromptVersion.version.desc())
        .first()
    )
    if not v:
        raise HTTPException(status_code=404, detail="Nenhuma versão encontrada")
    return PromptVersionOut(id=v.id, prompt_id=v.prompt_id, version=v.version, text=v.text, created_at=v.created_at)


@api_router.get("/prompts/{prompt_id}/versions", response_model=list[PromptVersionOut])
def list_prompt_versions(prompt_id: str, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt não encontrado")
    versions = (
        db.query(PromptVersion)
        .filter(PromptVersion.prompt_id == prompt_id)
        .order_by(PromptVersion.version.asc())
        .all()
    )
    return [
        PromptVersionOut(
            id=v.id,
            prompt_id=v.prompt_id,
            version=v.version,
            text=v.text,
            created_at=v.created_at,
        )
        for v in versions
    ]


@api_router.post("/prompts/{prompt_id}/versions", response_model=PromptVersionOut)
def create_prompt_version(prompt_id: str, payload: PromptVersionCreate, db: Session = Depends(get_db)):
    prompt = db.get(Prompt, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt não encontrado")
    last = (
        db.query(PromptVersion)
        .filter(PromptVersion.prompt_id == prompt_id)
        .order_by(PromptVersion.version.desc())
        .first()
    )
    next_version = 1 if not last else last.version + 1
    pv = PromptVersion(prompt_id=prompt_id, version=next_version, text=payload.text)
    db.add(pv)
    db.commit()
    db.refresh(pv)
    return PromptVersionOut(id=pv.id, prompt_id=prompt_id, version=pv.version, text=pv.text, created_at=pv.created_at)


@api_router.post("/runs", response_model=list[RunOut])
def create_runs(payload: RunCreate, db: Session = Depends(get_db)):
    pv = db.get(PromptVersion, payload.prompt_version_id)
    if not pv:
        raise HTTPException(status_code=404, detail="Prompt version não encontrada")

    created_runs: list[RunOut] = []
    for engine_payload in payload.engines:
        engine = (
            db.query(Engine)
            .filter(
                Engine.project_id == payload.project_id,
                Engine.name == engine_payload.name,
                Engine.region == engine_payload.region,
                Engine.device == engine_payload.device,
            )
            .first()
        )
        # Se não existir engine, cria com o config_json enviado
        if not engine:
            engine = Engine(
                project_id=payload.project_id,
                name=engine_payload.name,
                region=engine_payload.region,
                device=engine_payload.device,
                config_json=engine_payload.config_json,
            )
            db.add(engine)
            db.commit()
            db.refresh(engine)
        else:
            # Se já existe, mas o config_json da requisição difere,
            # criamos uma nova engine "variável" para esta run com o config novo.
            req_cfg = engine_payload.config_json or None
            cur_cfg = engine.config_json or None
            if req_cfg is not None and req_cfg != cur_cfg:
                # marcar como efêmera para não poluir a listagem de engines do projeto
                tmp_cfg = dict(req_cfg)
                try:
                    tmp_cfg.setdefault("_ephemeral", True)
                    tmp_cfg.pop("_main", None)
                except Exception:
                    tmp_cfg = req_cfg
                engine = Engine(
                    project_id=payload.project_id,
                    name=engine_payload.name,
                    region=engine_payload.region,
                    device=engine_payload.device,
                    config_json=tmp_cfg,
                )
                db.add(engine)
                db.commit()
                db.refresh(engine)

        run = Run(
            project_id=payload.project_id,
            prompt_version_id=payload.prompt_version_id,
            engine_id=engine.id,
            subproject_id=payload.subproject_id,
            status="queued",
            schedule_source="manual",
        )
        # refletir número de ciclos solicitado
        try:
            run.cycles_total = max(1, int(payload.cycles or 1))
        except Exception:
            run.cycles_total = 1
        # adicionar delay entre ciclos se especificado
        print(f"[DEBUG] payload.cycle_delay_seconds: {payload.cycle_delay_seconds}")
        if payload.cycle_delay_seconds is not None:
            run.cycle_delay_seconds = max(0, int(payload.cycle_delay_seconds))
            print(f"[DEBUG] Set run.cycle_delay_seconds to: {run.cycle_delay_seconds}")
        else:
            print(f"[DEBUG] cycle_delay_seconds is None, not setting")
        db.add(run)
        db.commit()
        db.refresh(run)

        enqueue_run(run.id, cycles=payload.cycles)

        created_runs.append(
            RunOut(
                id=run.id,
                status=run.status,
                zcrs=run.zcrs,
                amr_flag=run.amr_flag,
                dcr_flag=run.dcr_flag,
                tokens_input=run.tokens_input,
                tokens_output=run.tokens_output,
                tokens_total=run.tokens_total,
                cost_usd=run.cost_usd,
                latency_ms=run.latency_ms,
                cycles_total=run.cycles_total,
            )
        )

    return created_runs


@api_router.post("/projects/{project_id}/engines", response_model=EngineOut)
def create_engine(project_id: str, payload: EngineCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    # As engines criadas via Settings são consideradas "principais" por padrão
    cfg = payload.config_json or {}
    try:
        if isinstance(cfg, dict):
            cfg.setdefault("_main", True)
    except Exception:
        pass
    # If creating a Gemini engine and api_key is absent, pull from env/settings to avoid worker restarts
    try:
        nm = (payload.name or "").strip().lower()
        if nm in ("gemini", "google_gemini") and isinstance(cfg, dict) and not cfg.get("api_key"):
            gk = (
                os.getenv("GOOGLE_API_KEY")
                or os.getenv("GEMINI_API_KEY")
                or getattr(settings, "google_api_key", None)
                or getattr(settings, "gemini_api_key", None)
            )
            if gk:
                cfg["api_key"] = gk
    except Exception:
        pass
    e = Engine(
        project_id=project_id,
        name=payload.name,
        region=payload.region,
        device=payload.device,
        config_json=cfg,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return EngineOut(id=e.id, project_id=project_id, name=e.name, region=e.region, device=e.device, config_json=e.config_json)


@api_router.get("/runs/{run_id}/report", response_model=RunReport)
def get_run_report(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrado")

    report = compute_run_report(db, run_id)
    return report
@api_router.get("/insights")
def list_insights(project_id: str, db: Session = Depends(get_db)):
    items = db.query(Insight).filter(Insight.project_id == project_id).order_by(Insight.id.desc()).all()
    return [
        {
            "id": i.id,
            "project_id": i.project_id,
            "run_id": i.run_id,
            "title": i.title,
            "description": i.description,
            "impact": i.impact,
            "effort": i.effort,
            "status": i.status,
            "assignee": i.assignee,
        }
        for i in items
    ]

@api_router.post("/runs/{run_id}/insights")
def generate_insights_for_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrado")
    insights = generate_basic_insights(db, run)
    for ins in insights:
        db.add(ins)
    db.commit()
    return {"created": len(insights)}


@api_router.get("/runs/{run_id}/evidences", response_model=list[EvidenceOut])
def list_run_evidences(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrado")
    evs = db.query(Evidence).filter(Evidence.run_id == run_id).all()
    return [EvidenceOut(id=e.id, run_id=e.run_id, parsed_json=e.parsed_json) for e in evs]


@api_router.get("/runs", response_model=list[RunListItem])
def list_runs(
    db: Session = Depends(get_db),
    project_id: str | None = None,
    subproject_id: str | None = None,
    engine: str | None = None,
    status: str | None = None,
    schedule_source: str | None = None,
    monitor_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 100,
    order_by: str | None = None,
    order_dir: str | None = None,
    has_text: bool | None = None,
):
    """
    Lista runs com otimizações de performance:
    - Índices específicos para filtros mais comuns
    - Remoção de JOINs custosos desnecessários
    - Cache de subqueries
    - Limit de page_size para evitar queries massivas
    """
    # Query otimizada - removendo JOINs custosos desnecessários
    q = (
        db.query(
            Run.id,
            Engine.name.label("engine"),
            Run.status,
            Run.started_at,
            Run.finished_at,
            Run.zcrs,
            Run.amr_flag,
            Run.dcr_flag,
            Run.cost_usd,
            Run.tokens_total,
            Run.cycles_total,
            Run.cycle_delay_seconds,
            Run.monitor_id,
            Run.schedule_date,
            Run.schedule_slot,
            Run.schedule_index_today,
            Run.schedule_total_today,
            Run.schedule_source,
            # Campos de classificação Zero-Click
            Run.response_type,
            Run.sufficiency_level,
            Run.actionability_type,
            Run.trust_source,
            Run.brand_positioning,
            Run.classification_confidence,
            # Usando subquery mais eficiente para template_name
            literal_column("'-'").label("template_name"),
            literal_column("NULL").label("template_category"),
            func.coalesce(SubProject.name, literal_column("'-'")).label("subproject_name"),
            Monitor.name.label("monitor_name"),
        )
        .join(Engine, Engine.id == Run.engine_id)
        .outerjoin(SubProject, SubProject.id == Run.subproject_id)
        .outerjoin(Monitor, Monitor.id == Run.monitor_id)
    )
    if project_id:
        q = q.filter(Run.project_id == project_id)
    if subproject_id:
        q = q.filter(Run.subproject_id == subproject_id)
    if engine:
        q = q.filter(Engine.name == engine)
    if status:
        q = q.filter(Run.status == status)
    if schedule_source:
        q = q.filter(Run.schedule_source == schedule_source)
    if monitor_id:
        q = q.filter(Run.monitor_id == monitor_id)
    if date_from:
        q = q.filter(Run.started_at >= text(":df")).params(df=date_from)
    if date_to:
        q = q.filter(Run.started_at <= text(":dt")).params(dt=date_to)
    # Optional: only runs that have any evidence with parsed_json.text not empty
    # Otimizado para reduzir overhead da subquery
    if has_text:
        # Usar EXISTS mais simples e rápido
        evidence_subq = (
            db.query(Evidence.run_id)
            .filter(Evidence.run_id == Run.id)
            .filter(Evidence.parsed_json.isnot(None))
            .exists()
        )
        q = q.filter(evidence_subq)
    # paginação
    page = max(1, int(page or 1))
    page_size = max(10, min(int(page_size or 100), 200))
    # ordenação dinâmica
    sort_mapping = {
        "started_at": Run.started_at,
        "finished_at": Run.finished_at,
        "cost_usd": Run.cost_usd,
        "tokens_total": Run.tokens_total,
        "zcrs": Run.zcrs,
        "status": Run.status,
        # atenção: ordenar por string agregadas exige repetir a expressão
        "engine": Engine.name,
    }
    sort_col = sort_mapping.get((order_by or "started_at").lower(), Run.started_at)
    dir_is_asc = (order_dir or "desc").lower() == "asc"
    # Emular NULLS LAST em SQL Server via CASE
    nulls_last = case((sort_col.is_(None), 1), else_=0)
    if dir_is_asc:
        q = q.order_by(nulls_last.asc(), sort_col.asc(), Run.id.asc())
    else:
        q = q.order_by(nulls_last.asc(), sort_col.desc(), Run.id.desc())

    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return [
        RunListItem(
            id=r.id,
            engine=r.engine,
            status=r.status,
            started_at=r.started_at,
            finished_at=r.finished_at,
            zcrs=r.zcrs,
            amr_flag=r.amr_flag,
            dcr_flag=r.dcr_flag,
            template_name=getattr(r, "template_name", None),
            template_category=getattr(r, "template_category", None),
            subproject_name=getattr(r, "subproject_name", None),
            cost_usd=getattr(r, "cost_usd", None),
            tokens_total=getattr(r, "tokens_total", None),
            cycles_total=getattr(r, "cycles_total", None),
            cycle_delay_seconds=getattr(r, "cycle_delay_seconds", None),
            monitor_id=getattr(r, "monitor_id", None),
            schedule_date=getattr(r, "schedule_date", None),
            schedule_slot=getattr(r, "schedule_slot", None),
            schedule_index_today=getattr(r, "schedule_index_today", None),
            schedule_total_today=getattr(r, "schedule_total_today", None),
            schedule_source=getattr(r, "schedule_source", None),
            monitor_name=getattr(r, "monitor_name", None),
            # Campos de classificação Zero-Click
            response_type=getattr(r, "response_type", None),
            sufficiency_level=getattr(r, "sufficiency_level", None),
            actionability_type=getattr(r, "actionability_type", None),
            trust_source=getattr(r, "trust_source", None),
            brand_positioning=getattr(r, "brand_positioning", None),
            classification_confidence=getattr(r, "classification_confidence", None),
        )
        for r in rows
    ]

# Workaround: forçar registro explícito do GET /runs
api_router.add_api_route("/runs", list_runs, methods=["GET"], response_model=list[RunListItem])


@api_router.get("/runs/grouped", response_model=list[RunsBySubprojectGroup])
def list_runs_grouped_by_subproject(
    db: Session = Depends(get_db),
    project_id: str | None = None,
    subproject_id: str | None = None,
    engine: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit_per_group: int = 5,
    max_total: int = 200,
):
    """
    Lista runs agrupadas por subprojeto (tema), incluindo evidências embutidas.
    Otimizado para UI de comparação lado-a-lado.
    """
    # Query base com joins necessários para enriquecer dados do run
    q = (
        db.query(
            Run.id,
            Run.subproject_id,
            Run.status,
            Run.started_at,
            Run.finished_at,
            Engine.name.label("engine"),
            func.coalesce(SubProject.name, literal_column("'-'")) .label("subproject_name"),
            PromptVersion.text.label("prompt_text"),
        )
        .join(Engine, Engine.id == Run.engine_id)
        .outerjoin(PromptVersion, PromptVersion.id == Run.prompt_version_id)
        .outerjoin(SubProject, SubProject.id == Run.subproject_id)
    )
    if project_id:
        q = q.filter(Run.project_id == project_id)
    if subproject_id:
        q = q.filter(Run.subproject_id == subproject_id)
    if engine:
        q = q.filter(Engine.name == engine)
    if status:
        q = q.filter(Run.status == status)
    if date_from:
        q = q.filter(Run.started_at >= text(":df")).params(df=date_from)
    if date_to:
        q = q.filter(Run.started_at <= text(":dt")).params(dt=date_to)

    # Emular NULLS LAST em SQL Server via CASE
    q = q.order_by(
        case((Run.started_at.is_(None), 1), else_=0).asc(),
        Run.started_at.desc(),
        Run.id.desc(),
    )
    rows = q.limit(max_total).all()

    # Agrupar limitando quantidade por grupo em memória
    groups: dict[str | None, dict] = {}
    for r in rows:
        spid = getattr(r, "subproject_id", None)
        spname = getattr(r, "subproject_name", "—")
        g = groups.get(spid)
        if not g:
            g = {"subproject_id": spid, "subproject_name": spname, "runs": []}
            groups[spid] = g
        if len(g["runs"]) >= max(1, int(limit_per_group or 1)):
            continue
        g["runs"].append(
            {
                "id": r.id,
                "engine": r.engine,
                "status": r.status,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "prompt_text": getattr(r, "prompt_text", None),
            }
        )

    # Buscar evidências em lote
    run_ids: list[str] = []
    for g in groups.values():
        run_ids.extend([rr["id"] for rr in g["runs"]])
    evidences_by_run: dict[str, list[Evidence]] = {}
    if run_ids:
        evs = db.query(Evidence).filter(Evidence.run_id.in_(run_ids)).all()
        for e in evs:
            evidences_by_run.setdefault(e.run_id, []).append(e)

    # Montar resposta tipada
    out: list[RunsBySubprojectGroup] = []
    # Ordenar grupos por nome de subprojeto para output estável
    for spid, g in sorted(groups.items(), key=lambda kv: (str(kv[1]["subproject_name"]) or "~")):
        runs_out: list[GroupedRunWithEvidences] = []
        for rr in g["runs"]:
            ev_list = [
                EvidenceOut(id=e.id, run_id=e.run_id, parsed_json=e.parsed_json)
                for e in evidences_by_run.get(rr["id"], [])
            ]
            runs_out.append(
                GroupedRunWithEvidences(
                    id=rr["id"],
                    engine=rr["engine"],
                    status=rr["status"],
                    started_at=rr["started_at"],
                    finished_at=rr["finished_at"],
                    prompt_text=rr.get("prompt_text"),
                    evidences=ev_list,
                )
            )
        out.append(
            RunsBySubprojectGroup(
                subproject_id=g["subproject_id"],
                subproject_name=g["subproject_name"],
                runs=runs_out,
            )
        )
    return out


@api_router.get("/runs/export.csv")
def export_runs_csv(
    db: Session = Depends(get_db),
    project_id: str | None = None,
    subproject_id: str | None = None,
    engine: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    order_by: str | None = None,
    order_dir: str | None = None,
):
    # Reuso da query do list_runs com mais colunas
    q = (
        db.query(
            Run.id,
            Engine.name.label("engine"),
            Run.status,
            Run.started_at,
            Run.finished_at,
            Run.model_name,
            Run.cost_usd,
            Run.tokens_input,
            Run.tokens_output,
            Run.tokens_total,
            Run.latency_ms,
        )
        .join(Engine, Engine.id == Run.engine_id)
    )
    if project_id:
        q = q.filter(Run.project_id == project_id)
    if subproject_id:
        q = q.filter(Run.subproject_id == subproject_id)
    if engine:
        q = q.filter(Engine.name == engine)
    if status:
        q = q.filter(Run.status == status)
    if date_from:
        q = q.filter(Run.started_at >= text(":df")).params(df=date_from)
    if date_to:
        q = q.filter(Run.started_at <= text(":dt")).params(dt=date_to)

    sort_mapping = {
        "started_at": Run.started_at,
        "finished_at": Run.finished_at,
        "cost_usd": Run.cost_usd,
        "tokens_total": Run.tokens_total,
        "status": Run.status,
        "engine": Engine.name,
    }
    sort_col = sort_mapping.get((order_by or "started_at").lower(), Run.started_at)
    dir_is_asc = (order_dir or "desc").lower() == "asc"
    # Emular NULLS LAST em SQL Server via CASE
    nulls_last = case((sort_col.is_(None), 1), else_=0)
    if dir_is_asc:
        q = q.order_by(nulls_last.asc(), sort_col.asc(), Run.id.asc())
    else:
        q = q.order_by(nulls_last.asc(), sort_col.desc(), Run.id.desc())

    rows = q.all()
    # Map AI Overview links for these runs
    run_ids = [r.id for r in rows]
    ai_map: dict[str, str] = {}
    if run_ids:
        ev_ai = (
            db.query(RunEvent.run_id, RunEvent.message, RunEvent.created_at)
            .filter(RunEvent.run_id.in_(run_ids), RunEvent.version == "ai_overview_link")
            .order_by(RunEvent.run_id.asc(), RunEvent.created_at.desc())
            .all()
        )
        for rid, msg, _ in ev_ai:
            if rid not in ai_map and (msg or "").strip():
                ai_map[rid] = (msg or "").strip()
    # Citations map (domains, urls, is_ours per run)
    run_to_domains: dict[str, list[str]] = {}
    run_to_urls: dict[str, list[str]] = {}
    run_to_ours: dict[str, list[str]] = {}
    if run_ids:
        cit_rows = (
            db.query(Citation.run_id, Citation.domain, Citation.url, Citation.is_ours)
            .filter(Citation.run_id.in_(run_ids))
            .order_by(Citation.run_id.asc())
            .all()
        )
        for rid, dom, url, is_ours in cit_rows:
            run_to_domains.setdefault(rid, []).append(dom or "")
            run_to_urls.setdefault(rid, []).append(url or "")
            run_to_ours.setdefault(rid, []).append("1" if bool(is_ours) else "0")
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id",
        "engine",
        "status",
        "started_at",
        "finished_at",
        "model_name",
        "ai_overview_run_id",
        "tokens_input",
        "tokens_output",
        "tokens_total",
        "latency_ms",
        "cost_usd",
        "citations_domains",
        "citations_urls",
        "citations_is_ours",
    ])
    for r in rows:
        # Determine AI Overview run id: explicit link, else own id for google_serp
        ai_overview_id = ai_map.get(r.id, "")
        try:
            if not ai_overview_id and (r.engine or "").lower() == "google_serp":
                ai_overview_id = r.id
        except Exception:
            ai_overview_id = ai_overview_id or ""
        writer.writerow([
            r.id,
            r.engine,
            r.status,
            r.started_at.isoformat() if r.started_at else "",
            r.finished_at.isoformat() if r.finished_at else "",
            r.model_name or "",
            ai_overview_id,
            r.tokens_input if r.tokens_input is not None else "",
            r.tokens_output if r.tokens_output is not None else "",
            r.tokens_total if r.tokens_total is not None else "",
            r.latency_ms if r.latency_ms is not None else "",
            f"{float(r.cost_usd):.6f}" if r.cost_usd is not None else "",
            " ".join(run_to_domains.get(r.id, [])),
            " ".join(run_to_urls.get(r.id, [])),
            " ".join(run_to_ours.get(r.id, [])),
        ])
    buf.seek(0)
    headers = {"Content-Disposition": "attachment; filename=runs_export.csv"}
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)


@api_router.get("/analytics/overview", response_model=OverviewAnalytics)
def analytics_overview(db: Session = Depends(get_db)):
    total_runs = db.query(func.count(Run.id)).scalar() or 0
    # média de boolean como 0/1 via CASE
    amr_avg = (
        db.query(func.avg(case((Run.amr_flag == 1, 1), else_=0))).scalar() or 0.0
    )
    dcr_avg = (
        db.query(func.avg(case((Run.dcr_flag == 1, 1), else_=0))).scalar() or 0.0
    )
    zcrs_avg = db.query(func.avg(Run.zcrs)).scalar() or 0.0
    return OverviewAnalytics(total_runs=total_runs, amr_avg=float(amr_avg), dcr_avg=float(dcr_avg), zcrs_avg=float(zcrs_avg))


@api_router.get("/runs/{run_id}", response_model=RunDetailOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrado")
    engine = db.get(Engine, run.engine_id)
    # recuperar prompt text
    pv = db.get(PromptVersion, run.prompt_version_id)
    prompt_text = pv.text if pv else None
    return RunDetailOut(
        id=run.id,
        project_id=run.project_id,
        prompt_version_id=run.prompt_version_id,
        engine=EngineCreate(name=engine.name, region=engine.region, device=engine.device, config_json=engine.config_json),
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        subproject_id=run.subproject_id,
        prompt_text=prompt_text,
        model_name=run.model_name,
        tokens_input=run.tokens_input,
        tokens_output=run.tokens_output,
        tokens_total=run.tokens_total,
        cost_usd=run.cost_usd,
        latency_ms=run.latency_ms,
        cycles_total=run.cycles_total,
        cycle_delay_seconds=run.cycle_delay_seconds,
        monitor_id=run.monitor_id,
        schedule_date=run.schedule_date,
        schedule_slot=run.schedule_slot,
        schedule_index_today=run.schedule_index_today,
        schedule_total_today=run.schedule_total_today,
        schedule_source=run.schedule_source,
    )


@api_router.delete("/runs/{run_id}")
def delete_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrada")
    db.delete(run)
    db.commit()
    return {"ok": True}


@api_router.get("/runs/{run_id}/events")
def list_run_events(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrado")
    evs = db.query(RunEvent).filter(RunEvent.run_id == run_id).order_by(RunEvent.created_at.asc()).all()
    return [
        {
            "step": e.version,
            "status": e.status,
            "message": e.message,
            "created_at": e.created_at.isoformat(),
        }
        for e in evs
    ]


@api_router.post("/runs/{run_id}/link-ai-overview")
def link_ai_overview(run_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    src = db.get(Run, run_id)
    if not src:
        raise HTTPException(status_code=404, detail="Run não encontrado")
    target_id = (payload or {}).get("target_run_id")
    if not target_id:
        raise HTTPException(status_code=400, detail="target_run_id requerido")
    tgt = db.get(Run, target_id)
    if not tgt:
        raise HTTPException(status_code=404, detail="Run alvo não encontrado")
    # Registrar como evento para manter histórico e evitar migração de schema
    ev = RunEvent(run_id=run_id, version="ai_overview_link", status="ok", message=target_id)
    db.add(ev)
    db.commit()
    return {"ok": True, "linked_run_id": target_id}


@api_router.get("/runs/{run_id}/ai-overview-source")
def get_ai_overview_source(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrado")
    engine = db.get(Engine, run.engine_id)
    if engine and (engine.name or "").lower() == "google_serp":
        return {"run_id": run_id}
    ev = (
        db.query(RunEvent)
        .filter(RunEvent.run_id == run_id, RunEvent.version == "ai_overview_link")
        .order_by(RunEvent.created_at.desc())
        .first()
    )
    return {"run_id": (ev.message if ev else None)}

@api_router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str):
    async def event_generator():
        last_ts = None
        # Envia backlog inicial
        db = SessionLocal()
        try:
            events = (
                db.query(RunEvent)
                .filter(RunEvent.run_id == run_id)
                .order_by(RunEvent.created_at.asc())
                .all()
            )
            if events:
                last_ts = events[-1].created_at
                for e in events:
                    yield format_sse(e)
        finally:
            db.close()
        # Loop de streaming com heartbeat
        while True:
            db = SessionLocal()
            try:
                q = db.query(RunEvent).filter(RunEvent.run_id == run_id)
                if last_ts is not None:
                    q = q.filter(RunEvent.created_at > last_ts)
                new_events = q.order_by(RunEvent.created_at.asc()).all()
                if new_events:
                    last_ts = new_events[-1].created_at
                    for e in new_events:
                        yield format_sse(e)
                else:
                    # heartbeat para manter conexão viva e forçar flush nos proxies
                    yield ": keep-alive\n\n"
                await asyncio.sleep(1)
            finally:
                db.close()

    def json_escape(s: str | None) -> str:
        if s is None:
            return 'null'
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

    def format_sse(e: RunEvent) -> str:
        return (
            "data: {" +
            f"\"step\":\"{e.version}\",\"status\":\"{e.status}\",\"message\":{json_escape(e.message)},\"created_at\":\"{e.created_at.isoformat()}\"" +
            "}\n\n"
        )

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)


# Analytics de custos/tokens por período
@api_router.get("/analytics/costs")
def analytics_costs(
    db: Session = Depends(get_db),
    project_id: str | None = None,
    subproject_id: str | None = None,
    engine: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    q = db.query(Run, Engine.name.label("engine"))
    q = q.join(Engine, Engine.id == Run.engine_id)
    if project_id:
        q = q.filter(Run.project_id == project_id)
    if subproject_id:
        q = q.filter(Run.subproject_id == subproject_id)
    if engine:
        q = q.filter(Engine.name == engine)
    if date_from:
        q = q.filter(Run.started_at >= text(":df")).params(df=date_from)
    if date_to:
        q = q.filter(Run.started_at <= text(":dt")).params(dt=date_to)

    rows = q.all()
    total_cost = float(sum((r.cost_usd or 0.0) for (r, _eng) in rows))
    total_tokens = int(sum((r.tokens_total or 0) for (r, _eng) in rows))
    count = len(rows)
    # série por dia e por engine
    # Build dynamic SQL for SQL Server compatibility
    where_conditions = ["r.started_at IS NOT NULL"]
    params = {}
    
    if project_id:
        where_conditions.append("r.project_id = :project_id")
        params["project_id"] = project_id
    if subproject_id:
        where_conditions.append("r.subproject_id = :subproject_id") 
        params["subproject_id"] = subproject_id
    if engine:
        where_conditions.append("e.name = :engine")
        params["engine"] = engine
    if date_from:
        where_conditions.append("r.started_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where_conditions.append("r.started_at <= :date_to")
        params["date_to"] = date_to
        
    where_clause = " AND ".join(where_conditions)
    
    series_sql = text(f"""
        SELECT 
            CAST(r.started_at AS DATE) as day,
            e.name as engine,
            SUM(COALESCE(r.cost_usd, 0.0)) as cost_usd,
            SUM(COALESCE(r.tokens_total, 0)) as tokens
        FROM runs r
        JOIN engines e ON e.id = r.engine_id
        WHERE {where_clause}
        GROUP BY CAST(r.started_at AS DATE), e.name
        ORDER BY day
    """)
    series_rows = db.execute(series_sql, params).fetchall()
    series_out = [
        {"day": d.isoformat(), "engine": eng, "cost_usd": float(c or 0), "tokens": int(t or 0)}
        for (d, eng, c, t) in series_rows
    ]

    return {
        "total_cost_usd": total_cost,
        "total_tokens": total_tokens,
        "runs": count,
        "avg_cost_per_run": (total_cost / count) if count else 0.0,
        "series": series_out,
    }

@api_router.post("/projects/{project_id}/subprojects")
def create_subproject(project_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    sp = SubProject(project_id=project_id, name=payload.get("name"), description=payload.get("description"))
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return {"id": sp.id, "project_id": sp.project_id, "name": sp.name, "description": sp.description}


@api_router.delete("/subprojects/{subproject_id}")
def delete_subproject(subproject_id: str, db: Session = Depends(get_db)):
    sp = db.get(SubProject, subproject_id)
    if not sp:
        raise HTTPException(status_code=404, detail="Subprojeto não encontrado")
    # Anular referências para respeitar FKs que não possuem ondelete=CASCADE
    db.query(Run).filter(Run.subproject_id == subproject_id).update({Run.subproject_id: None}, synchronize_session=False)
    db.query(PromptTemplate).filter(PromptTemplate.subproject_id == subproject_id).update({PromptTemplate.subproject_id: None}, synchronize_session=False)
    db.query(Monitor).filter(Monitor.subproject_id == subproject_id).update({Monitor.subproject_id: None}, synchronize_session=False)
    db.delete(sp)
    db.commit()
    return {"ok": True}


@api_router.get("/projects/{project_id}/subprojects")
def list_subprojects(project_id: str, db: Session = Depends(get_db)):
    sps = db.query(SubProject).filter(SubProject.project_id == project_id).all()
    return [{"id": s.id, "name": s.name, "description": s.description} for s in sps]


@api_router.patch("/subprojects/{subproject_id}")
def update_subproject(subproject_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    sp = db.get(SubProject, subproject_id)
    if not sp:
        raise HTTPException(status_code=404, detail="Subprojeto não encontrado")
    for field in ["name", "description"]:
        if field in payload and payload[field] is not None:
            setattr(sp, field, payload[field])
    db.commit()
    db.refresh(sp)
    return {"id": sp.id, "project_id": sp.project_id, "name": sp.name, "description": sp.description}


@api_router.post("/subprojects")
def create_subproject_q(payload: dict = Body(...), db: Session = Depends(get_db)):
    pid = payload.get("project_id")
    if not pid:
        raise HTTPException(status_code=400, detail="project_id requerido")
    sp = SubProject(project_id=pid, name=payload.get("name"), description=payload.get("description"))
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return {"id": sp.id, "project_id": sp.project_id, "name": sp.name, "description": sp.description}


@api_router.get("/subprojects")
def list_subprojects_q(project_id: str, db: Session = Depends(get_db)):
    sps = db.query(SubProject).filter(SubProject.project_id == project_id).all()
    return [{"id": s.id, "name": s.name, "description": s.description} for s in sps]


@api_router.post("/projects/{project_id}/templates")
def create_template(project_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    t = PromptTemplate(
        project_id=project_id,
        category=payload.get("category") or "Geral",
        name=payload.get("name"),
        text=payload.get("text"),
        intent=payload.get("intent"),
        persona=payload.get("persona"),
        subproject_id=payload.get("subproject_id"),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "category": t.category, "name": t.name, "subproject_id": t.subproject_id}


@api_router.get("/projects/{project_id}/templates")
def list_templates(
    project_id: str,
    category: str | None = None,
    subproject_id: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(PromptTemplate).filter(PromptTemplate.project_id == project_id)
    if category:
        q = q.filter(PromptTemplate.category == category)
    if subproject_id:
        q = q.filter(PromptTemplate.subproject_id == subproject_id)
    items = q.order_by(PromptTemplate.category.asc(), PromptTemplate.name.asc()).all()
    return [
        {
            "id": t.id,
            "category": t.category,
            "name": t.name,
            "text": t.text,
            "intent": t.intent,
            "persona": t.persona,
            "subproject_id": t.subproject_id,
        }
        for t in items
    ]


@api_router.patch("/templates/{template_id}")
def update_template(template_id: str, payload: dict, db: Session = Depends(get_db)):
    t = db.get(PromptTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    for k in ["category", "name", "text", "intent", "persona", "subproject_id"]:
        if k in payload and payload[k] is not None:
            setattr(t, k, payload[k])
    db.commit()
    db.refresh(t)
    return {"id": t.id, "category": t.category, "name": t.name, "subproject_id": t.subproject_id}


@api_router.delete("/templates/{template_id}")
def delete_template(template_id: str, db: Session = Depends(get_db)):
    t = db.get(PromptTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    db.delete(t)
    db.commit()
    return {"ok": True}


@api_router.get("/analytics/subprojects/{subproject_id}/overview")
def subproject_overview(subproject_id: str, db: Session = Depends(get_db)):
    # KPIs médios para runs do subprojeto
    runs = db.query(Run).filter(Run.subproject_id == subproject_id).all()
    total = len(runs)
    if total == 0:
        return {"total_runs": 0, "amr_avg": 0.0, "dcr_avg": 0.0, "zcrs_avg": 0.0}
    amr_avg = sum(1.0 if r.amr_flag else 0.0 for r in runs if r.amr_flag is not None) / max(1, total)
    dcr_avg = sum(1.0 if r.dcr_flag else 0.0 for r in runs if r.dcr_flag is not None) / max(1, total)
    zcrs_vals = [r.zcrs for r in runs if r.zcrs is not None]
    zcrs_avg = (sum(zcrs_vals) / len(zcrs_vals)) if zcrs_vals else 0.0
    return {"total_runs": total, "amr_avg": amr_avg, "dcr_avg": dcr_avg, "zcrs_avg": zcrs_avg}


@api_router.get("/analytics/subprojects/{subproject_id}/top-domains")
def subproject_top_domains(subproject_id: str, limit: int = 10, db: Session = Depends(get_db)):
    rows = (
        db.query(Citation.domain, func.count(Citation.id))
        .join(Run, Run.id == Citation.run_id)
        .filter(Run.subproject_id == subproject_id)
        .group_by(Citation.domain)
        .order_by(func.count(Citation.id).desc())
        .limit(limit)
        .all()
    )
    return [{"domain": d or "", "count": int(c)} for d, c in rows]


@api_router.get("/analytics/subprojects/{subproject_id}/series")
def subproject_series(subproject_id: str, db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            """
            SELECT
              CAST(runs.started_at AS DATE) AS day,
              AVG(CASE WHEN runs.amr_flag = 1 THEN 1 ELSE 0 END) AS amr_avg,
              AVG(CASE WHEN runs.dcr_flag = 1 THEN 1 ELSE 0 END) AS dcr_avg,
              AVG(runs.zcrs) AS zcrs_avg
            FROM runs
            WHERE runs.subproject_id = :sp AND runs.started_at IS NOT NULL
            GROUP BY CAST(runs.started_at AS DATE)
            ORDER BY day ASC
            """
        ),
        {"sp": subproject_id},
    ).fetchall()
    return [
        {"day": r[0].isoformat(), "amr_avg": float(r[1] or 0), "dcr_avg": float(r[2] or 0), "zcrs_avg": float(r[3] or 0)}
        for r in rows
    ]


@api_router.get("/analytics/performance-by-engine")
def performance_by_engine(subproject_id: str | None = None, db: Session = Depends(get_db)):
    base_sql = """
        SELECT e.name as engine,
               AVG(CASE WHEN r.amr_flag = 1 THEN 1 ELSE 0 END) AS amr_avg,
               AVG(CASE WHEN r.dcr_flag = 1 THEN 1 ELSE 0 END) AS dcr_avg,
               AVG(r.zcrs) AS zcrs_avg,
               COUNT(1) AS runs
        FROM runs r
        JOIN engines e ON e.id = r.engine_id
        {where}
        GROUP BY e.name
        ORDER BY runs DESC
    """
    where = "WHERE r.started_at IS NOT NULL"
    params: dict = {}
    if subproject_id:
        where += " AND r.subproject_id = :sp"
        params["sp"] = subproject_id
    sql = text(base_sql.format(where=where))
    rows = db.execute(sql, params).fetchall()
    return [
        {
            "engine": r[0],
            "amr_avg": float(r[1] or 0),
            "dcr_avg": float(r[2] or 0),
            "zcrs_avg": float(r[3] or 0),
            "runs": int(r[4] or 0),
        }
        for r in rows
    ]


@api_router.post("/projects/{project_id}/monitors")
def create_monitor(project_id: str, payload: dict, db: Session = Depends(get_db)):
    mon = Monitor(
        project_id=project_id,
        subproject_id=payload.get("subproject_id"),
        name=payload.get("name"),
        schedule_cron=payload.get("schedule_cron"),
        engines_json=payload.get("engines_json") or {"engines": []},
        active=True,
    )
    db.add(mon)
    db.commit()
    db.refresh(mon)
    return {"id": mon.id, "name": mon.name}


@api_router.get("/projects/{project_id}/monitors")
def list_monitors(project_id: str, db: Session = Depends(get_db)):
    mons = db.query(Monitor).filter(Monitor.project_id == project_id).all()
    def _schedule_info(sched: str | None) -> dict | None:
        if not sched:
            return None
        try:
            tz_br = timezone(timedelta(hours=-3))  # Brasília UTC-3 (sem DST)
            now_utc = datetime.now(timezone.utc)
            now_br = now_utc.astimezone(tz_br)
            # Parse optional options after ';'
            cron_part = sched
            until_date = None
            if ";" in sched:
                parts = [p.strip() for p in sched.split(";")]
                cron_part = parts[0].strip()
                for opt in parts[1:]:
                    if not opt:
                        continue
                    kv = [x.strip() for x in opt.split("=", 1)]
                    if len(kv) == 2 and kv[0].lower() == "until":
                        try:
                            y, m, d = [int(x) for x in kv[1].split("-")]
                            # store as ISO date string for UI
                            until_date = f"{y:04d}-{m:02d}-{d:02d}"
                        except Exception:
                            until_date = None
            exprs = [e.strip() for e in cron_part.split("|") if e.strip()]
            if not exprs:
                return {"tz": "UTC-3", "tz_label": "Brasília (UTC-3)"}
            # Collect next occurrences across all expressions (global next)
            upcoming: list[datetime] = []
            for ex in exprs:
                try:
                    it = croniter(ex, now_utc)
                    # Pull a few next occurrences from this expression
                    for _ in range(5):
                        dt = it.get_next(datetime)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        upcoming.append(dt)
                except Exception:
                    continue
            if not upcoming:
                return {"tz": "UTC-3", "tz_label": "Brasília (UTC-3)"}
            # Merge, sort and unique by minute
            upcoming.sort()
            uniq: list[datetime] = []
            seen = set()
            for dt in upcoming:
                k = dt.replace(second=0, microsecond=0)
                if k not in seen:
                    seen.add(k)
                    uniq.append(dt)
            uniq = uniq[:5]
            # Convert to Brasília and format
            def _fmt(dt_utc: datetime) -> str:
                dt_br = dt_utc.astimezone(tz_br)
                return f"{dt_br.hour:02d}:{dt_br.minute:02d} {dt_br.day:02d}/{dt_br.month:02d}"
            next_runs_br = [_fmt(x) for x in uniq]
            next_run_br = next_runs_br[0] if next_runs_br else None

            # Build today's schedule in Brasília timezone
            today_br = now_br.date()
            day_start_br = datetime(today_br.year, today_br.month, today_br.day, 0, 0, tzinfo=tz_br)
            day_end_br = day_start_br + timedelta(days=1)
            day_start_utc = day_start_br.astimezone(timezone.utc)
            day_end_utc = day_end_br.astimezone(timezone.utc)
            times_today_utc: list[datetime] = []
            for ex in exprs:
                try:
                    it_day = croniter(ex, day_start_utc)
                    # advance until first >= start
                    t = it_day.get_next(datetime)
                    # accumulate occurrences within day window
                    guard = 0
                    while t <= day_end_utc and guard < 100:
                        times_today_utc.append(t if t.tzinfo else t.replace(tzinfo=timezone.utc))
                        t = it_day.get_next(datetime)
                        guard += 1
                except Exception:
                    continue
            # Deduplicate by minute and sort
            times_today_utc.sort()
            seen2 = set(); uniq_today_utc: list[datetime] = []
            for dt in times_today_utc:
                k = dt.replace(second=0, microsecond=0)
                if k not in seen2:
                    seen2.add(k); uniq_today_utc.append(dt)
            daily_slots_br = [dt.astimezone(tz_br).strftime("%H:%M") for dt in uniq_today_utc]
            total_today = len(daily_slots_br)
            next_index_today = None
            if next_run_br:
                try:
                    # Extract HH:MM from next_run_br string
                    hhmm = next_run_br.split()[0]
                    if hhmm in daily_slots_br:
                        next_index_today = daily_slots_br.index(hhmm) + 1
                except Exception:
                    next_index_today = None
            return {
                "tz": "UTC-3",
                "tz_label": "Brasília (UTC-3)",
                "next_run_br": next_run_br,
                "next_runs_br": next_runs_br,
                "until": until_date,
                "daily_slots_br": daily_slots_br,
                "next_index_today": next_index_today,
                "total_today": total_today,
            }
        except Exception:
            return {"tz": "UTC-3", "tz_label": "Brasília (UTC-3)"}

    return [
        {
            "id": m.id,
            "name": m.name,
            "subproject_id": m.subproject_id,
            "schedule_cron": m.schedule_cron,
            "schedule_info": _schedule_info(m.schedule_cron),
            "engines_json": m.engines_json,
            "active": m.active,
        }
        for m in mons
    ]


@api_router.post("/monitors/{monitor_id}/templates/{template_id}")
def add_template_to_monitor(monitor_id: str, template_id: str, db: Session = Depends(get_db)):
    mt = MonitorTemplate(monitor_id=monitor_id, template_id=template_id)
    db.add(mt)
    db.commit()
    return {"ok": True}


@api_router.post("/monitors/{monitor_id}/run")
def run_monitor_now(monitor_id: str, db: Session = Depends(get_db)):
    mon = db.get(Monitor, monitor_id)
    if not mon:
        raise HTTPException(status_code=404, detail="Monitor não encontrado")
    # listar templates
    mts = db.query(MonitorTemplate).filter(MonitorTemplate.monitor_id == monitor_id).all()
    if not mts:
        raise HTTPException(status_code=400, detail="Nenhum template associado")
    # criar runs por template e engines
    created = []
    for mt in mts:
        tpl = db.get(PromptTemplate, mt.template_id)
        if not tpl:
            continue
        # criar prompt a partir do template
        prompt = Prompt(
            project_id=mon.project_id,
            name=f"Run: {tpl.name}",
            text=tpl.text,
            intent=tpl.intent,
            persona=tpl.persona,
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)
        pv = PromptVersion(prompt_id=prompt.id, version=1, text=tpl.text)
        db.add(pv)
        db.commit()
        db.refresh(pv)
        # engines
        for e in (mon.engines_json.get("engines") or []):
            engine = (
                db.query(Engine)
                .filter(
                    Engine.project_id == mon.project_id,
                    Engine.name == e.get("name"),
                    Engine.region == e.get("region"),
                    Engine.device == e.get("device"),
                )
                .first()
            )
            if not engine:
                cfg_json = dict(e.get("config_json") or {})
                # Default Gemini tokens if not set
                try:
                    if str(e.get("name") or "").lower() == "gemini" and "max_output_tokens" not in cfg_json:
                        cfg_json["max_output_tokens"] = 9000
                    if str(e.get("name") or "").lower() == "gemini" and cfg_json.get("use_search") is None:
                        cfg_json["use_search"] = True
                except Exception:
                    pass
                engine = Engine(
                    project_id=mon.project_id,
                    name=e.get("name"),
                    region=e.get("region"),
                    device=e.get("device"),
                    config_json=cfg_json,
                )
                db.add(engine)
                db.commit()
                db.refresh(engine)
            else:
                # If exists, MERGE requested config over current one to preserve credentials (e.g., api_key)
                req_cfg = dict(e.get("config_json") or {})
                cur_cfg = dict(engine.config_json or {})
                merged_cfg = dict(cur_cfg)
                try:
                    merged_cfg.update(req_cfg)
                except Exception:
                    pass
                # Ephemeral mark and clean flags
                try:
                    merged_cfg.setdefault("_ephemeral", True)
                    merged_cfg.pop("_main", None)
                except Exception:
                    pass
                # Defaults for Gemini
                try:
                    if str(e.get("name") or "").lower() == "gemini":
                        merged_cfg.setdefault("use_search", True)
                        merged_cfg.setdefault("max_output_tokens", 9000)
                except Exception:
                    pass
                # Only create a temp engine if merged differs from current
                if merged_cfg != cur_cfg:
                    engine = Engine(
                        project_id=mon.project_id,
                        name=e.get("name"),
                        region=e.get("region"),
                        device=e.get("device"),
                        config_json=merged_cfg,
                    )
                    db.add(engine)
                    db.commit()
                    db.refresh(engine)
            # schedule metadata (run-now)
            from datetime import datetime, timezone
            now_utc = datetime.now(timezone.utc)
            slot = f"{now_utc.hour:02d}:{now_utc.minute:02d}"
            run = Run(
                project_id=mon.project_id,
                prompt_version_id=pv.id,
                engine_id=engine.id,
                subproject_id=(tpl.subproject_id or mon.subproject_id),
                monitor_id=mon.id,
                status="queued",
                schedule_source="monitor_now",
                schedule_date=now_utc.replace(hour=0, minute=0, second=0, microsecond=0),
                schedule_slot=slot,
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            enqueue_run(run.id, cycles=1)
            created.append(run.id)
    return {"queued_runs": created}


@api_router.get("/monitors/{monitor_id}/templates")
def list_monitor_templates(monitor_id: str, db: Session = Depends(get_db)):
    mts = db.query(MonitorTemplate).filter(MonitorTemplate.monitor_id == monitor_id).all()
    return [{"id": mt.id, "template_id": mt.template_id} for mt in mts]


@api_router.delete("/monitors/{monitor_id}/templates/{template_id}")
def remove_template_from_monitor(monitor_id: str, template_id: str, db: Session = Depends(get_db)):
    mt = (
        db.query(MonitorTemplate)
        .filter(MonitorTemplate.monitor_id == monitor_id, MonitorTemplate.template_id == template_id)
        .first()
    )
    if not mt:
        raise HTTPException(status_code=404, detail="Associação não encontrada")
    db.delete(mt)
    db.commit()
    return {"ok": True}


@api_router.delete("/monitors/{monitor_id}")
def delete_monitor(monitor_id: str, db: Session = Depends(get_db)):
    mon = db.get(Monitor, monitor_id)
    if not mon:
        raise HTTPException(status_code=404, detail="Monitor não encontrado")
    # Snapshot: before desassociar runs, compute totals and persist into MonitorHistory
    try:
        run_rows = db.query(Run.id, Run.subproject_id).filter(Run.monitor_id == monitor_id).all()
        total = len(run_rows)
        completed = db.query(func.count(Run.id)).filter(Run.monitor_id == monitor_id, Run.status == "completed").scalar() or 0
        failed = db.query(func.count(Run.id)).filter(Run.monitor_id == monitor_id, Run.status == "failed").scalar() or 0
        # Predominant subproject among runs
        sp_counts: dict[str | None, int] = {}
        for _rid, spid in run_rows:
            sp_counts[spid] = sp_counts.get(spid, 0) + 1
        predominant_sp: str | None = None
        if sp_counts:
            predominant_sp = max(sp_counts.items(), key=lambda kv: kv[1])[0]
        # Insert or update history (idempotent by monitor_id)
        existing = (
            db.query(MonitorHistory)
            .filter(MonitorHistory.monitor_id == monitor_id)
            .first()
        )
        if existing:
            existing.project_id = mon.project_id
            existing.name = mon.name
            existing.subproject_id = predominant_sp
            existing.runs_total = int(total)
            existing.runs_completed = int(completed)
            existing.runs_failed = int(failed)
        else:
            hist = MonitorHistory(
                monitor_id=monitor_id,
                project_id=mon.project_id,
                subproject_id=predominant_sp,
                name=mon.name,
                runs_total=int(total),
                runs_completed=int(completed),
                runs_failed=int(failed),
            )
            db.add(hist)
        db.commit()
        # Snapshot run mapping for precise exports
        try:
            if run_rows:
                values = []
                for rid, _sp in run_rows:
                    values.append(MonitorHistoryRun(history_monitor_id=monitor_id, run_id=rid))
                db.bulk_save_objects(values)
                db.commit()
        except Exception:
            db.rollback()
    except Exception:
        # Non-blocking snapshot
        try:
            db.rollback()
        except Exception:
            pass
    # Desassociar runs para evitar bloqueio de FK
    try:
        db.query(Run).filter(Run.monitor_id == monitor_id).update({Run.monitor_id: None}, synchronize_session=False)
    except Exception:
        pass
    # Remover vínculos de templates (FK CASCADE já cobre, mas fazermos explicitamente por segurança)
    db.query(MonitorTemplate).filter(MonitorTemplate.monitor_id == monitor_id).delete(synchronize_session=False)
    db.delete(mon)
    db.commit()
    return {"ok": True}


@api_router.get("/monitors/{monitor_id}/runs")
def list_runs_by_monitor(monitor_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(
            Run.id,
            Run.status,
            Run.started_at,
            Run.finished_at,
            Run.zcrs,
            Run.cycles_total,
            Run.cost_usd,
            Engine.name.label("engine"),
            Prompt.id.label("prompt_id"),
            Prompt.name.label("prompt_name"),
            Run.schedule_date,
            Run.schedule_slot,
            Run.schedule_source,
        )
        .join(Engine, Engine.id == Run.engine_id)
        .outerjoin(PromptVersion, PromptVersion.id == Run.prompt_version_id)
        .outerjoin(Prompt, Prompt.id == PromptVersion.prompt_id)
        .filter(Run.monitor_id == monitor_id)
        .order_by(
            case((Run.started_at.is_(None), 1), else_=0).asc(),
            Run.started_at.desc(),
            Run.id.desc(),
        )
        .all()
    )
    return [
        {
            "id": r.id,
            "status": r.status,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "zcrs": r.zcrs,
            "cycles_total": r.cycles_total,
            "cost_usd": r.cost_usd,
            "engine": getattr(r, "engine", None),
            "prompt_id": getattr(r, "prompt_id", None),
            "prompt_name": getattr(r, "prompt_name", None),
            "schedule_date": getattr(r, "schedule_date", None),
            "schedule_slot": getattr(r, "schedule_slot", None),
            "schedule_source": getattr(r, "schedule_source", None),
        }
        for r in rows
    ]


@api_router.get("/projects/{project_id}/engines")
def list_engines(project_id: str, db: Session = Depends(get_db)):
    """Lista apenas engines principais para o projeto.

    Regras:
    - Oculta engines efêmeras (config_json._ephemeral == true).
    - Deduplica por "name", escolhendo a melhor candidata por prioridade:
      1) config_json._main == true
      2) region == 'BR' e device == 'desktop'
      3) primeira ocorrência
    """
    engs = db.query(Engine).filter(Engine.project_id == project_id).all()
    # agrupar por nome com heurística de escolha
    best_by_name: dict[str, Engine] = {}

    def is_ephemeral(cfg: dict | None) -> bool:
        return bool(isinstance(cfg, dict) and cfg.get("_ephemeral"))
    def is_archived(cfg: dict | None) -> bool:
        return bool(isinstance(cfg, dict) and cfg.get("_archived"))

    def score(e: Engine) -> tuple[int, int]:
        cfg = e.config_json or {}
        # maior é melhor
        s_main = 1 if (isinstance(cfg, dict) and cfg.get("_main") is True) else 0
        s_brdesk = 1 if (str(e.region or "").upper() == "BR" and str(e.device or "").lower() == "desktop") else 0
        return (s_main, s_brdesk)

    for e in engs:
        if is_ephemeral(e.config_json) or is_archived(e.config_json):
            continue
        cur = best_by_name.get(e.name)
        if cur is None:
            best_by_name[e.name] = e
        else:
            if score(e) > score(cur):
                best_by_name[e.name] = e

    # Ordenar alfabeticamente por nome para estabilidade
    chosen = [best_by_name[k] for k in sorted(best_by_name.keys())]
    return [
        {
            "id": e.id,
            "name": e.name,
            "region": e.region,
            "device": e.device,
            "config_json": e.config_json,
        }
        for e in chosen
    ]


@api_router.delete("/engines/{engine_id}")
def delete_engine(engine_id: str, db: Session = Depends(get_db)):
    e = db.get(Engine, engine_id)
    if not e:
        raise HTTPException(status_code=404, detail="Engine não encontrada")
    runs_count = db.query(func.count(Run.id)).filter(Run.engine_id == engine_id).scalar() or 0
    if runs_count > 0:
        # Se há runs associadas, arquiva em vez de deletar para não quebrar FK
        cfg = e.config_json or {}
        if not isinstance(cfg, dict):
            cfg = {}
        cfg["_archived"] = True
        e.config_json = cfg
        db.commit()
        db.refresh(e)
        return {"archived": True, "runs": int(runs_count)}
    db.delete(e)
    db.commit()
    return {"deleted": True}


@api_router.patch("/engines/{engine_id}")
def update_engine(engine_id: str, payload: dict, db: Session = Depends(get_db)):
    e = db.get(Engine, engine_id)
    if not e:
        raise HTTPException(status_code=404, detail="Engine não encontrada")
    if "config_json" in payload:
        e.config_json = payload.get("config_json")
    if "region" in payload:
        e.region = payload.get("region")
    if "device" in payload:
        e.device = payload.get("device")
    db.commit()
    db.refresh(e)
    return {"id": e.id, "config_json": e.config_json, "region": e.region, "device": e.device}


@api_router.get("/utils/url-title")
def fetch_url_title(url: str):
    try:
        with httpx.Client(timeout=8.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = client.get(url)
            r.raise_for_status()
            html = r.text
        soup = BeautifulSoup(html, "lxml")
        og = soup.find("meta", attrs={"property": "og:title"})
        title = (og.get("content") if og else None) or (soup.title.string if soup.title else None) or url
        return {"title": title}
    except Exception:
        return {"title": url}


@api_router.patch("/monitors/{monitor_id}")
def update_monitor(monitor_id: str, payload: dict, db: Session = Depends(get_db)):
    mon = db.get(Monitor, monitor_id)
    if not mon:
        raise HTTPException(status_code=404, detail="Monitor não encontrado")
    if "name" in payload:
        mon.name = payload.get("name") or mon.name
    if "subproject_id" in payload:
        mon.subproject_id = payload.get("subproject_id")
    if "schedule_cron" in payload:
        mon.schedule_cron = payload.get("schedule_cron")
    if "engines_json" in payload:
        mon.engines_json = payload.get("engines_json") or mon.engines_json
    if "active" in payload:
        mon.active = bool(payload.get("active"))
    db.commit()
    db.refresh(mon)
    return {
        "id": mon.id,
        "name": mon.name,
        "subproject_id": mon.subproject_id,
        "schedule_cron": mon.schedule_cron,
        "engines_json": mon.engines_json,
        "active": mon.active,
    }


@api_router.get("/analytics/subprojects/{subproject_id}/export.csv")
def export_subproject_csv(subproject_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(Run.id, Run.started_at, Run.finished_at, Run.status, Run.zcrs, Run.amr_flag, Run.dcr_flag, Engine.name)
        .join(Engine, Engine.id == Run.engine_id)
        .filter(Run.subproject_id == subproject_id)
        .order_by(Run.started_at.asc().nullsfirst())
        .all()
    )
    # map run_id -> citations joined
    cits = (
        db.query(Citation.run_id, Citation.url, Citation.is_ours)
        .join(Run, Run.id == Citation.run_id)
        .filter(Run.subproject_id == subproject_id)
        .all()
    )
    run_to_urls: dict[str, list[str]] = {}
    run_to_ours: dict[str, list[str]] = {}
    for rid, url, is_ours in cits:
        run_to_urls.setdefault(rid, []).append(url or "")
        run_to_ours.setdefault(rid, []).append("1" if bool(is_ours) else "0")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["run_id", "started_at", "finished_at", "status", "engine", "zcrs", "amr", "dcr", "citations", "citations_is_ours"])
    for rid, started, finished, status, zcrs, amr, dcr, eng in rows:
        writer.writerow([
            rid,
            started.isoformat() if started else "",
            finished.isoformat() if finished else "",
            status,
            eng,
            zcrs if zcrs is not None else "",
            1 if amr else 0 if amr is not None else "",
            1 if dcr else 0 if dcr is not None else "",
            " ".join(run_to_urls.get(rid, [])),
            " ".join(run_to_ours.get(rid, [])),
        ])
    buf.seek(0)
    headers = {"Content-Disposition": f"attachment; filename=subproject_{subproject_id}.csv"}
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)


@api_router.post("/analytics/subprojects/{subproject_id}/generate-insights")
def generate_subproject_insights(subproject_id: str, db: Session = Depends(get_db)):
    """Gera um insight agregado do subprojeto usando um LLM (quando disponível).

    Retorna um payload com seções estruturadas: resumo, recomendações, ações, tópicos, keywords e wordcloud.
    """
    # Coleta de dados básicos do subprojeto
    runs = (
        db.query(
            Run.id,
            Run.status,
            Run.started_at,
            Run.finished_at,
            Run.zcrs,
            Run.cost_usd,
            Run.tokens_total,
            Run.amr_flag,
            Run.dcr_flag,
            Run.model_name,
            Engine.name.label("engine"),
            Engine.config_json.label("engine_config"),
            Run.project_id,
            PromptVersion.text.label("prompt_text"),
        )
        .join(Engine, Engine.id == Run.engine_id)
        .outerjoin(PromptVersion, PromptVersion.id == Run.prompt_version_id)
        .filter(Run.subproject_id == subproject_id)
        .order_by(Run.started_at.desc().nullslast())
        .limit(200)
        .all()
    )
    citations = (
        db.query(Citation.run_id, Citation.domain, Citation.url)
        .join(Run, Run.id == Citation.run_id)
        .filter(Run.subproject_id == subproject_id)
        .limit(1000)
        .all()
    )

    # Anexar evidências (resposta e links) e opts efetivos por run
    run_ids = [r.id for r in runs]
    ev_map: Dict[str, Dict[str, Any]] = {}
    if run_ids:
        ev_rows = (
            db.query(Evidence)
            .filter(Evidence.run_id.in_(run_ids))
            .order_by(Evidence.id.desc())
            .all()
        )
        for ev in ev_rows:
            if ev.run_id not in ev_map:
                ev_map[ev.run_id] = ev.parsed_json or {}
    opts_map: Dict[str, Any] = {}
    if run_ids:
        evt_rows = (
            db.query(RunEvent)
            .filter(RunEvent.run_id.in_(run_ids), RunEvent.version == "opts")
            .order_by(RunEvent.created_at.desc())
            .all()
        )
        import json as _json
        for e in evt_rows:
            if e.run_id in opts_map:
                continue
            try:
                opts_map[e.run_id] = _json.loads(e.message or "{}")
            except Exception:
                opts_map[e.run_id] = {"raw": (e.message or "")[:500]}

    def _subset_cfg(cfg: Dict[str, Any] | None) -> Dict[str, Any]:
        if not isinstance(cfg, dict):
            return {}
        keys = [
            "model",
            "web_search",
            "use_search",
            "search_context_size",
            "reasoning_effort",
            "max_output_tokens",
            "user_location",
            "web_search_force",
        ]
        return {k: cfg.get(k) for k in keys if k in cfg}

    def _trim(s: Any, n: int) -> Any:
        if isinstance(s, str) and len(s) > n:
            return s[:n] + "…"
        return s

    # Estruturar contexto enxuto para LLM
    runs_ctx: List[Dict[str, Any]] = []
    for r in runs:
        rid = r.id
        ev = ev_map.get(rid) or {}
        parsed = ev.get("parsed") or {}
        meta = parsed.get("meta") or {}
        text = parsed.get("text") or ""
        links = parsed.get("links") or []
        # compor config efetiva (engine.config + opts logados)
        engine_cfg = _subset_cfg(r.engine_config or {})
        if rid in opts_map and isinstance(opts_map[rid], dict):
            engine_cfg.update(_subset_cfg(opts_map[rid]))
        runs_ctx.append({
            "id": rid,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "zcrs": float(r.zcrs or 0),
            "cost_usd": float(r.cost_usd or 0),
            "tokens_total": int(r.tokens_total or 0),
            "engine": r.engine,
            "model": (r.model_name or meta.get("model") or meta.get("engine") or r.engine),
            "prompt": _trim(r.prompt_text or "", 3000),
            "response": _trim(text or "", 6000),
            "links": links,
            "amr_flag": bool(r.amr_flag) if r.amr_flag is not None else None,
            "dcr_flag": bool(r.dcr_flag) if r.dcr_flag is not None else None,
            "project_id": r.project_id,
            "engine_config": engine_cfg,
        })

    cits_ctx: List[Dict[str, Any]] = [
        {"run_id": rid, "domain": dom or "", "url": url or ""} for (rid, dom, url) in citations
    ]

    # Heurísticas por run (reuso de app.services.insights) para enriquecer o contexto do LLM
    heuristics_data: List[Dict[str, Any]] = []
    try:
        runs_full = (
            db.query(Run)
            .filter(Run.subproject_id == subproject_id)
            .order_by(Run.started_at.desc().nullslast())
            .limit(200)
            .all()
        )
        for r in runs_full:
            try:
                hs = generate_basic_insights(db, r)
                for h in hs:
                    heuristics_data.append({
                        "run_id": h.run_id,
                        "title": h.title,
                        "description": h.description,
                        "impact": h.impact,
                        "effort": h.effort,
                        "status": h.status,
                    })
            except Exception:
                # heurística é auxiliar: seguir sem bloquear
                continue
    except Exception:
        heuristics_data = []

    # Prompt de sistema para orientar estilo e seções
    system = (
        "Você é um analista sênior de SEO para Zero‑Click/AI Overviews. "
        "Escreva um insight executivo e prático, sem perguntas. Em português. "
        "Respeite a estrutura de saída JSON pedida."
    )
    user_prompt = {
        "task": "Gerar insights agregados sobre Zero‑Click para um subprojeto",
        "requirements": [
            "Resumo executivo (3-5 bullets)",
            "Principais recomendações priorizadas (impacto x esforço)",
            "Ações rápidas (quick wins)",
            "Tópicos recorrentes e lacunas (com base nas respostas/citações)",
            "Palavras‑chave sugeridas (lista)",
            "Esboço de nuvem de palavras (wordcloud: {token, weight})",
        ],
        "data": {
            "runs": runs_ctx,
            "citations": cits_ctx,
            "heuristics": heuristics_data,
        },
        "output_schema": {
            "summary": ["string"],
            "recommendations": [{"title": "string", "impact": "low|medium|high", "effort": "low|medium|high"}],
            "quick_wins": ["string"],
            "topics": ["string"],
            "keywords": ["string"],
            "wordcloud": [{"token": "string", "weight": "number"}]
        }
    }

    # Fallback caso não haja chave/SDK: retorna um esqueleto com heurísticas leves
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        # Heurística simples: top domínios e palavras básicas a partir de URLs
        from collections import Counter
        doms = [d or "" for (_rid, d, _u) in citations]
        top = Counter(doms).most_common(8)
        wc = [{"token": k[:24], "weight": int(v)} for k, v in top if k]
        return {
            "summary": [
                "Resumo indisponível (LLM não configurado).",
                f"Runs consideradas: {len(runs_ctx)}; Citações: {len(cits_ctx)}.",
            ],
            "recommendations": [],
            "quick_wins": ["Configure a chave OPENAI_API_KEY para insights completos."],
            "topics": [],
            "keywords": [],
            "wordcloud": wc,
        }

    # Chamada ao LLM (Responses API) com um formato enxuto
    try:
        import json
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # type: ignore
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {"type": "array", "items": {"type": "string"}},
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "title": {"type": "string"},
                            "impact": {"type": "string"},
                            "effort": {"type": "string"}
                        },
                        "required": ["title"],
                    }
                },
                "quick_wins": {"type": "array", "items": {"type": "string"}},
                "topics": {"type": "array", "items": {"type": "string"}},
                "keywords": {"type": "array", "items": {"type": "string"}},
                "wordcloud": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "token": {"type": "string"},
                            "weight": {"type": "number"}
                        },
                        "required": ["token", "weight"]
                    }
                }
            },
            "required": ["summary", "recommendations", "quick_wins", "topics", "keywords", "wordcloud"]
        }
        instructions = (
            system
            + "\n\nIMPORTANTE: Responda apenas com JSON válido (sem markdown e sem ```), obedecendo ao schema a seguir. "
            + json.dumps(schema, ensure_ascii=False)
        )
        resp = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5"),
            instructions=instructions,
            input=(
                "Analise os dados a seguir e gere APENAS o JSON final.\nDADOS:\n"
                + json.dumps(user_prompt, ensure_ascii=False)
            ),
            max_output_tokens=1024,
            reasoning={"effort": "low"},
        )
        text = getattr(resp, "output_text", None) or ""
        if not text:
            # Tentar extrair de output[].content[]
            try:
                d = resp.model_dump()  # type: ignore[attr-defined]
                out = d.get("output") or []
                parts: List[str] = []
                for it in out:
                    if isinstance(it, dict) and it.get("type") == "message":
                        for c in (it.get("content") or []):
                            t = c.get("text") or c.get("content")
                            if isinstance(t, str):
                                parts.append(t)
                if parts:
                    text = "\n".join(parts)
            except Exception:
                text = ""
        # Parsing robusto com saneamento
        import re as _re
        def _try_parse(txt: str):
            return json.loads(txt)
        def _sanitize(txt: str) -> str:
            s = (txt or "").strip()
            # remover fences ```json ... ```
            if s.startswith("```"):
                s = s[s.find("\n") + 1 :] if "\n" in s else s.replace("```", "")
                s = s.replace("```", "")
            # recortar bloco JSON principal
            if '{' in s and '}' in s:
                start = s.find('{')
                end = s.rfind('}')
                if end > start:
                    s = s[start:end+1]
            # normalizar aspas “ ” ‘ ’ -> "
            s = s.replace('“', '"').replace('”', '"').replace('’', '"').replace("‘", '"')
            # normalizar NaN/Infinity
            s = s.replace('NaN', '0').replace('Infinity', '0').replace('-Infinity', '0')
            # remover vírgulas à direita antes de } ou ]
            s = _re.sub(r",\s*([}\]])", r"\1", s)
            # remover comentários estilo //...
            s = _re.sub(r"^\s*//.*$", "", s, flags=_re.MULTILINE)
            return s
        def _parse_markdown(txt: str) -> dict:
            # Extrair seções por headings e listas
            s = (txt or "").replace('\r', '')
            lines = s.split('\n')
            current = None
            buckets: dict[str, list[str]] = {"summary": [], "recommendations": [], "quick_wins": [], "topics": [], "keywords": [], "wordcloud": []}
            def _norm(h: str) -> str:
                h = h.lower().strip()
                if 'resumo' in h: return 'summary'
                if 'recomenda' in h: return 'recommendations'
                if 'quick' in h or 'ações rápidas' in h: return 'quick_wins'
                if 'tópico' in h or 'lacuna' in h: return 'topics'
                if 'palavras' in h: return 'keywords'
                if 'wordcloud' in h or 'nuvem' in h: return 'wordcloud'
                return ''
            for ln in lines:
                if ln.lstrip().startswith('#'):
                    header = ln.lstrip('#').strip()
                    current = _norm(header)
                    continue
                if current:
                    stripped = ln.strip()
                    if stripped.startswith(('-', '*')) or _re.match(r"^\d+\.\s", stripped):
                        item = stripped.lstrip('-* ').strip()
                        buckets[current].append(item)
            # Construir estrutura destino
            import math
            out: dict[str, any] = {
                "summary": buckets["summary"],
                "recommendations": [],
                "quick_wins": buckets["quick_wins"],
                "topics": buckets["topics"],
                "keywords": buckets["keywords"],
                "wordcloud": []
            }
            # Recommendations: tentar extrair impacto/esforço
            for itm in buckets['recommendations']:
                impact = None
                effort = None
                m1 = _re.search(r"impacto\s*[:=-]\s*([a-zA-Z]+)", itm, flags=_re.IGNORECASE)
                m2 = _re.search(r"esforç[o|o]\s*[:=-]\s*([a-zA-Z]+)", itm, flags=_re.IGNORECASE)
                if m1: impact = m1.group(1).lower()
                if m2: effort = m2.group(1).lower()
                title = _re.sub(r"\(.*?\)|\[.*?\]|impacto.*$|esforço.*$", "", itm, flags=_re.IGNORECASE).strip(" -–—;:")
                out['recommendations'].append({"title": title or itm, **({"impact": impact} if impact else {}), **({"effort": effort} if effort else {})})
            # Wordcloud: token: peso | token (peso)
            for itm in buckets['wordcloud']:
                m = _re.search(r"^(.+?)[\s:（\(]+([0-9]+(?:\.[0-9]+)?)\)?$", itm.strip())
                if m:
                    token = m.group(1).strip().strip('-:').strip()
                    try:
                        weight = float(m.group(2))
                    except Exception:
                        weight = 1.0
                else:
                    token, weight = itm.strip(), 1.0
                if token:
                    out['wordcloud'].append({"token": token[:48], "weight": weight})
            return out
        data: dict = {}
        try:
            data = _try_parse(text)
        except Exception:
            s1 = _sanitize(text)
            try:
                data = _try_parse(s1)
            except Exception:
                # segunda passagem: remover quebras de linha entre chaves e vírgulas sobrando
                s2 = _re.sub(r",\s*(\n|\r)+\s*([}\]])", r"\2", s1)
                try:
                    data = _try_parse(s2)
                except Exception:
                    # fallback: parser de markdown estruturado
                    data = _parse_markdown(text)
        # Sanitizar campos esperados e enriquecer com heurísticas se vier vazio
        payload = {
            "summary": list(data.get("summary", []))[:10],
            "recommendations": data.get("recommendations", [])[:10],
            "quick_wins": list(data.get("quick_wins", []))[:10],
            "topics": list(data.get("topics", []))[:20],
            "keywords": list(data.get("keywords", []))[:30],
            "wordcloud": data.get("wordcloud", [])[:40],
        }

        def enrich_if_empty(p: Dict[str, Any]) -> Dict[str, Any]:
            from collections import Counter
            import re
            # agregados básicos
            total_runs = len(runs_ctx)
            avg_zcrs = round(sum(r.get("zcrs", 0) for r in runs_ctx) / total_runs, 1) if total_runs else 0.0
            total_cost = round(sum(r.get("cost_usd", 0.0) for r in runs_ctx), 4)
            total_tokens = int(sum(r.get("tokens_total", 0) for r in runs_ctx))
            amr_vals = [1 for r in runs_ctx if r.get("amr_flag") is True]
            dcr_vals = [1 for r in runs_ctx if r.get("dcr_flag") is True]
            amr_avg = round(len(amr_vals) / total_runs, 2) if total_runs else 0.0
            dcr_avg = round(len(dcr_vals) / total_runs, 2) if total_runs else 0.0

            # domains do projeto para separar concorrentes
            project_id = None
            for r in runs_ctx:
                if r.get("project_id"):
                    project_id = r["project_id"]
                    break
            project_domains = set()
            if project_id:
                for d in db.query(Domain).filter(Domain.project_id == project_id).all():
                    if d.domain:
                        project_domains.add(d.domain)

            # top domains e tokens
            dom_counter = Counter()
            token_counter = Counter()
            url_re = re.compile(r"https?://([^/]+)(/[^\s]*)?", re.IGNORECASE)
            word_re = re.compile(r"[A-Za-zÀ-ÿ0-9]{3,}")
            stop = set([
                "www","com","br","net","org","de","pt","http","https","html","htm","php","amp","blog","news","www2",
                "para","como","que","qual","mais","melhor","sobre","isso","isto","essa","esse","aquele","uma","um",
                "de","da","do","das","dos","e","a","o","os","as","em","no","na","nas","nos","por","com","ao","à","às","aos"
            ])
            for _rid, dom, url in citations:
                host = (dom or "").lower()
                if host:
                    dom_counter[host] += 1
                    for part in host.replace(".", " ").split():
                        w = part.strip()
                        if w and w not in stop and word_re.fullmatch(w):
                            token_counter[w] += 1
                u = (url or "")
                m = url_re.match(u)
                if m:
                    path = (m.group(2) or "").lower()
                    for w in word_re.findall(path):
                        if w not in stop:
                            token_counter[w] += 1

            top_tokens = [t for t, _c in token_counter.most_common(30)]
            top_wc = [{"token": t, "weight": float(c)} for t, c in token_counter.most_common(20)]
            top_competitor = None
            for d, _c in dom_counter.most_common():
                if d not in project_domains:
                    top_competitor = d
                    break

            # preencher se vazio
            if not p.get("summary"):
                p["summary"] = [
                    f"Runs analisadas: {total_runs}",
                    f"ZCRS médio: {avg_zcrs}",
                    f"Custo total: ${total_cost}",
                    f"Tokens totais: {total_tokens}",
                    f"AMR médio: {amr_avg} · DCR médio: {dcr_avg}",
                ]
            if not p.get("recommendations"):
                recs = []
                if avg_zcrs < 50:
                    recs.append({"title": "Aumentar relevância do conteúdo para elevar ZCRS", "impact": "high", "effort": "medium"})
                if amr_avg < 0.3:
                    recs.append({"title": "Melhorar match com intenção (AMR baixo)", "impact": "medium", "effort": "medium"})
                if top_competitor:
                    recs.append({"title": f"Criar/otimizar comparativos com {top_competitor}", "impact": "high", "effort": "low"})
                if total_tokens > 300000:
                    recs.append({"title": "Reduzir contexto e otimizar consultas (tokens altos)", "impact": "medium", "effort": "low"})
                # aproveitar heurísticas por run
                def _map_level(n: int | None) -> str | None:
                    if n is None:
                        return None
                    return {1: "low", 2: "medium", 3: "high"}.get(int(n), None)
                seen_titles: set[str] = set(r["title"] for r in recs)
                for h in heuristics_data[:10]:
                    title = (h.get("title") or "").strip()
                    if not title or title in seen_titles:
                        continue
                    recs.append({
                        "title": title,
                        **({"impact": _map_level(h.get("impact"))} if _map_level(h.get("impact")) else {}),
                        **({"effort": _map_level(h.get("effort"))} if _map_level(h.get("effort")) else {}),
                    })
                    seen_titles.add(title)
                p["recommendations"] = recs[:6]
            if not p.get("quick_wins"):
                q = [
                    "Adicionar seções FAQ/HowTo nas páginas foco",
                    "Garantir dados estruturados atualizados (FAQ/HowTo)",
                    "Revisar headings e entidades principais nas páginas Top",
                ]
                if top_competitor:
                    q.insert(0, f"Publicar página 'Nossa marca vs {top_competitor}'")
                # se heurística "Por que não citou?" apareceu, priorizar ação correspondente
                if any((h.get("title") or "").lower().startswith("por que não citou") for h in heuristics_data):
                    q.insert(0, "Investigar por que o domínio não foi citado e reforçar sinais E-E-A-T em páginas foco")
                p["quick_wins"] = q[:6]
            if not p.get("topics"):
                p["topics"] = top_tokens[:8]
            if not p.get("keywords"):
                p["keywords"] = top_tokens[:15]
            if not p.get("wordcloud"):
                p["wordcloud"] = top_wc
            return p

        return enrich_if_empty(payload)
    except Exception as e:
        return {
            "summary": [
                "Falha ao gerar via LLM.",
                str(e)[:200],
            ],
            "recommendations": [],
            "quick_wins": [],
            "topics": [],
            "keywords": [],
            "wordcloud": [],
        }

@api_router.get("/setup/status")
def setup_status() -> dict:
    has_env = os.path.exists(".env")
    keys = {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        # Aceita GOOGLE_API_KEY ou GEMINI_API_KEY
        "gemini": bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")),
        "perplexity": bool(os.getenv("PERPLEXITY_API_KEY")),
        "serpapi": bool(os.getenv("SERPAPI_KEY")),
    }
    sandbox = not any(keys.values())
    return {"has_env": has_env, "keys": keys, "sandbox": sandbox}


@api_router.post("/setup/save-keys")
def save_keys(payload: dict = Body(...), db: Session = Depends(get_db)) -> dict:
    """Persiste chaves em .env e atualiza o ambiente do processo para efeito imediato."""
    # Map de campos -> variáveis aceitas
    key_map: dict[str, list[str]] = {
        "openai_key": ["OPENAI_API_KEY"],
        "gemini_key": ["GOOGLE_API_KEY", "GEMINI_API_KEY"],
        "perplexity_key": ["PERPLEXITY_API_KEY"],
        "serpapi_key": ["SERPAPI_KEY"],
    }

    # Carregar .env existente (se houver)
    env_path = Path(".env")
    lines: list[str] = []
    if env_path.exists():
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            lines = []

    # Transformar em dict preservando ordem
    existing: dict[str, str] = {}
    order: list[str] = []
    for ln in lines:
        if not ln.strip() or ln.strip().startswith("#"):
            order.append(ln)
            continue
        if "=" in ln:
            k, v = ln.split("=", 1)
            existing[k.strip()] = v
            order.append(k.strip())
        else:
            order.append(ln)

    # Atualizar valores
    saved_vars: list[str] = []
    for field, env_vars in key_map.items():
        val = payload.get(field)
        if val is None:
            continue
        for var in env_vars:
            existing[var] = val
            os.environ[var] = val
            saved_vars.append(var)
            if var not in order:
                order.append(var)

    # Reconstruir conteúdo preservando comentários e ordem
    out_lines: list[str] = []
    for it in order:
        if not it:
            out_lines.append("")
        elif it.strip().startswith("#") or "=" not in it:
            # linha original de comentário ou desconhecida
            if it in existing:
                out_lines.append(f"{it}={existing[it]}")
            else:
                out_lines.append(it)
        else:
            # era uma KEY
            key = it.split("=", 1)[0].strip()
            out_lines.append(f"{key}={existing.get(key, '')}")

    # Acrescentar quaisquer chaves novas ausentes
    for k, v in existing.items():
        if not any(ln.startswith(f"{k}=") for ln in out_lines):
            out_lines.append(f"{k}={v}")

    try:
        env_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao salvar .env: {str(e)[:200]}")

    # If Gemini key provided, persist it into all Gemini engines missing api_key
    try:
        gkey = payload.get("gemini_key")
        if gkey:
            engines = db.query(Engine).filter(Engine.name.in_(["gemini", "google_gemini"])).all()
            updated = 0
            for eng in engines:
                cfgj = dict(eng.config_json or {})
                if not cfgj.get("api_key"):
                    cfgj["api_key"] = gkey
                    eng.config_json = cfgj
                    updated += 1
            if updated:
                db.commit()
    except Exception:
        # do not fail the request if engine update fails
        try:
            db.rollback()
        except Exception:
            pass
    return {"ok": True, "saved": saved_vars}


@api_router.post("/setup/test-connections")
def test_connections(payload: dict = Body(...)) -> dict:
    results = {}
    # OpenAI
    try:
        import os
        from openai import OpenAI  # type: ignore
        key = payload.get("openai_key") or os.getenv("OPENAI_API_KEY")
        ok = False
        if key:
            client = OpenAI(api_key=key)
            client.models.list()
            ok = True
        results["openai"] = {"ok": ok}
    except Exception as e:
        results["openai"] = {"ok": False, "error": str(e)[:200]}
    # Gemini (use google-genai SDK, same adaptador dos monitores)
    try:
        from google import genai as ggenai  # type: ignore
        key = (
            payload.get("gemini_key")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or getattr(settings, "google_api_key", None)
            or getattr(settings, "gemini_api_key", None)
        )
        ok = False
        if key:
            client = ggenai.Client(api_key=key)
            # Call a lightweight endpoint
            _ = client.models.list()
            ok = True
        results["gemini"] = {"ok": ok}
    except Exception as e:
        results["gemini"] = {"ok": False, "error": str(e)[:200]}
    # Perplexity
    try:
        import httpx
        key = payload.get("perplexity_key") or os.getenv("PERPLEXITY_API_KEY")
        ok = False
        if key:
            with httpx.Client(timeout=8.0) as c:
                r = c.get("https://api.perplexity.ai/models", headers={"Authorization": f"Bearer {key}"})
                ok = r.status_code < 500
        results["perplexity"] = {"ok": ok}
    except Exception as e:
        results["perplexity"] = {"ok": False, "error": str(e)[:200]}
    # SerpAPI
    try:
        import httpx
        key = payload.get("serpapi_key") or os.getenv("SERPAPI_KEY")
        ok = False
        if key:
            with httpx.Client(timeout=8.0) as c:
                r = c.get("https://serpapi.com/status.json", params={"api_key": key})
                ok = r.status_code == 200
        results["serpapi"] = {"ok": ok}
    except Exception as e:
        results["serpapi"] = {"ok": False, "error": str(e)[:200]}
    results["sandbox"] = not any(v.get("ok") for v in results.values())
    return results


@api_router.post("/setup/suggest-queries")
def suggest_queries(payload: dict = Body(...)) -> dict:
    site: str = (payload.get("site") or "").strip()
    base = site.replace("https://", "").replace("http://", "").strip("/")
    brand = base.split(".")[0] if base else "seu banco"
    intents = {
        "Informacional": [f"o que é pix {brand}", f"como funciona cartão {brand}", f"app {brand} limites pix"],
        "Comparativa": [f"{brand} vs nubank cartão", f"{brand} vs itau conta pj"],
        "Transacional": [f"abrir conta {brand}", f"cartão {brand} solicitar"],
        "Navegacional": [f"{brand} login", f"{brand} atendimento"],
    }
    queries = []
    for cat, qs in intents.items():
        for q in qs:
            queries.append({"text": q, "intent": cat})
    return {"queries": queries[:15]}


@api_router.post("/setup/smoke-test")
def smoke_test(payload: dict = Body(...), db: Session = Depends(get_db)) -> dict:
    project_id = payload.get("project_id")
    subproject_id = payload.get("subproject_id")
    queries: list[str] = payload.get("queries") or []
    engine_name: str = payload.get("engine") or "sandbox"
    # criar prompt+versão para cada query e enfileirar
    queued: list[str] = []
    for q in queries[:5]:
        p = Prompt(project_id=project_id, name=f"Smoke: {q}", text=q, intent=None, persona=None)
        db.add(p); db.commit(); db.refresh(p)
        pv = PromptVersion(prompt_id=p.id, version=1, text=q)
        db.add(pv); db.commit(); db.refresh(pv)
        engine = db.query(Engine).filter(Engine.project_id==project_id, Engine.name==engine_name).first()
        if not engine:
            engine = Engine(project_id=project_id, name=engine_name, region="BR", device="desktop", config_json={})
            db.add(engine); db.commit(); db.refresh(engine)
        run = Run(project_id=project_id, prompt_version_id=pv.id, engine_id=engine.id, subproject_id=subproject_id, status="queued")
        db.add(run); db.commit(); db.refresh(run)
        enqueue_run(run.id, cycles=1)
        queued.append(run.id)
    return {"queued_runs": queued}


@api_router.post("/sandbox/test")
def sandbox_test(payload: dict = Body(...)) -> dict:
    """Execute a single adapter end-to-end without touching DB.

    Body params:
    - engine: one of [openai, gemini, perplexity, google_serp, sandbox]
    - prompt (or query): text
    - model: optional, forwarded into config.model
    - config: optional dict with engine-specific settings
    - language, region, device: optional context
    - timeout_seconds: optional float
    """
    import time
    engine_name: str = (payload.get("engine") or "openai").strip()
    prompt: str = (payload.get("prompt") or payload.get("query") or "").strip()
    cfg: dict = dict(payload.get("config") or {})
    if payload.get("model") and not cfg.get("model"):
        cfg["model"] = payload.get("model")
    language = (payload.get("language") or "pt-BR").strip() or "pt-BR"
    region = (payload.get("region") or "BR").strip() or "BR"
    device = (payload.get("device") or "desktop").strip() or "desktop"
    try:
        timeout_seconds = float(payload.get("timeout_seconds") or 30)
    except Exception:
        timeout_seconds = 30.0

    fetch_input = {
        "query": prompt,
        "language": language,
        "region": region,
        "device": device,
        "config": cfg,
    }

    t0 = time.perf_counter()
    try:
        raw, parsed, citations = run_engine(engine_name, fetch_input, timeout_seconds=timeout_seconds)
        t1 = time.perf_counter()
    except Exception as e:
        return {
            "ok": False,
            "engine": engine_name,
            "model": cfg.get("model"),
            "error": str(e),
        }

    # Raw preview helpers
    raw_payload = raw.get("raw") if isinstance(raw, dict) else raw
    # If adapter reported an error in raw, surface it clearly as failure
    if isinstance(raw_payload, dict) and raw_payload.get("error"):
        err = str(raw_payload.get("error"))
        msg = str(raw_payload.get("message") or "")
        req = raw_payload.get("request") if isinstance(raw_payload.get("request"), dict) else None
        return {
            "ok": False,
            "engine": engine_name,
            "model": cfg.get("model"),
            "error": f"{err}: {msg}".strip(": "),
            "request": req,
        }
    raw_keys = list(raw_payload.keys())[:12] if isinstance(raw_payload, dict) else []
    output_types = []
    try:
        rd = raw_payload.get("response") or raw_payload
        out = rd.get("output") or []
        for item in out[:8]:
            if isinstance(item, dict) and item.get("type"):
                output_types.append(item.get("type"))
    except Exception:
        pass

    full_text = parsed.get("text") or ""
    text_preview = full_text[:800]
    truncated = len(full_text) > len(text_preview)
    meta = parsed.get("meta") or {}
    # Usage and max tokens for diagnostics
    usage = meta.get("raw_usage") or {}
    cfg_max_tokens = cfg.get("max_output_tokens")
    return {
        "ok": True,
        "engine": engine_name,
        "model": cfg.get("model"),
        "timing_ms": int((t1 - t0) * 1000),
        "text_preview": text_preview,
        "text": full_text,
        "truncated": truncated,
        "links": parsed.get("links", [])[:10],
        "web_search_used": bool(meta.get("web_search_used")),
        "web_search_calls": int(meta.get("web_search_calls") or 0),
        "usage": usage,
        "config_max_output_tokens": cfg_max_tokens,
        "raw_keys": raw_keys,
        "output_types": output_types,
    }


@api_router.get("/sandbox/openai/models")
def sandbox_openai_models(org: str | None = None, project: str | None = None) -> dict:
    """List available models for the current OpenAI API key.

    Optional query params:
    - org: Organization ID to scope the request
    - project: Project ID to scope the request
    """
    if OpenAI is None:
        return {"ok": False, "error": "openai_client_unavailable"}
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"ok": False, "error": "missing_api_key"}
    used_org = org or os.getenv("OPENAI_ORG_ID") or os.getenv("OPENAI_ORGANIZATION")
    used_project = project or os.getenv("OPENAI_PROJECT_ID") or os.getenv("OPENAI_PROJECT")
    try:
        client = OpenAI(api_key=api_key, organization=used_org, project=used_project) if (used_org or used_project) else OpenAI(api_key=api_key)
        lst = client.models.list()
        # Defensive extraction across SDK versions
        data = getattr(lst, "data", []) or []
        ids: list[str] = []
        for m in data:
            mid = getattr(m, "id", None) or (m.get("id") if isinstance(m, dict) else None)
            if mid:
                ids.append(str(mid))
        return {"ok": True, "ids": ids, "count": len(ids), "organization": used_org, "project": used_project}
    except Exception as e:
        return {"ok": False, "error": str(e), "organization": used_org, "project": used_project}


@api_router.get("/projects/{project_id}/stats")
def project_stats(project_id: str, db: Session = Depends(get_db)):
    sp_count = db.query(func.count(SubProject.id)).filter(SubProject.project_id == project_id).scalar() or 0
    run_count = db.query(func.count(Run.id)).filter(Run.project_id == project_id).scalar() or 0
    return {"subprojects": int(sp_count), "runs": int(run_count)}


# ============================================================================
# CLASSIFICATION ENDPOINTS
# ============================================================================

@api_router.post("/runs/{run_id}/classify")
def classify_run(run_id: str, db: Session = Depends(get_db)):
    """Classifica uma run específica usando o sistema Zero-Click"""
    from app.services.classification_integration import classify_run_async

    # Verificar se a run existe
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrada")

    # Executar classificação
    result = classify_run_async(run_id)

    if result is None:
        raise HTTPException(status_code=400, detail="Falha ao classificar a run")

    return {
        "run_id": run_id,
        "classification": {
            "response_type": result.response_type.value,
            "sufficiency_level": result.sufficiency_level.value,
            "actionability_type": result.actionability_type.value,
            "trust_source": result.trust_source.value,
            "brand_positioning": result.brand_positioning.value,
            "confidence": result.confidence,
            "reasoning": result.reasoning
        },
        "classified_at": datetime.utcnow().isoformat(),
        "version": "1.0"
    }


@api_router.post("/projects/{project_id}/classify/batch")
def classify_project_runs(
    project_id: str,
    force_update: bool = False,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """Classifica todas as runs de um projeto em lote"""
    from app.services.classification_integration import retroactively_classify_all_runs

    # Verificar se o projeto existe
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Executar classificação em lote
    results = retroactively_classify_all_runs(
        project_id=project_id,
        force_update=force_update,
        limit=limit
    )

    # Estatísticas do processamento
    total_processed = len(results)
    successful = sum(1 for r in results.values() if r is not None)
    failed = total_processed - successful

    return {
        "project_id": project_id,
        "total_processed": total_processed,
        "successful": successful,
        "failed": failed,
        "force_update": force_update,
        "limit": limit,
        "processed_at": datetime.utcnow().isoformat()
    }


@api_router.get("/projects/{project_id}/classification/stats")
def get_classification_stats(project_id: str, db: Session = Depends(get_db)):
    """Retorna estatísticas de classificação para um projeto"""

    # Verificar se o projeto existe
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Estatísticas gerais
    total_runs = db.query(func.count(Run.id)).filter(
        Run.project_id == project_id,
        Run.status == "completed"
    ).scalar() or 0

    classified_runs = db.query(func.count(Run.id)).filter(
        Run.project_id == project_id,
        Run.status == "completed",
        Run.response_type.isnot(None)
    ).scalar() or 0

    # Distribuição por tipo de resposta
    response_type_stats = db.query(
        Run.response_type,
        func.count(Run.id).label('count')
    ).filter(
        Run.project_id == project_id,
        Run.response_type.isnot(None)
    ).group_by(Run.response_type).all()

    # Distribuição por posicionamento da marca
    brand_positioning_stats = db.query(
        Run.brand_positioning,
        func.count(Run.id).label('count')
    ).filter(
        Run.project_id == project_id,
        Run.brand_positioning.isnot(None)
    ).group_by(Run.brand_positioning).all()

    # Distribuição por nível de suficiência
    sufficiency_stats = db.query(
        Run.sufficiency_level,
        func.count(Run.id).label('count')
    ).filter(
        Run.project_id == project_id,
        Run.sufficiency_level.isnot(None)
    ).group_by(Run.sufficiency_level).all()

    # Confiança média das classificações
    avg_confidence = db.query(
        func.avg(Run.classification_confidence)
    ).filter(
        Run.project_id == project_id,
        Run.classification_confidence.isnot(None)
    ).scalar() or 0.0

    return {
        "project_id": project_id,
        "overview": {
            "total_runs": total_runs,
            "classified_runs": classified_runs,
            "unclassified_runs": total_runs - classified_runs,
            "classification_coverage": round(classified_runs / total_runs * 100, 1) if total_runs > 0 else 0,
            "avg_confidence": round(float(avg_confidence), 2)
        },
        "response_types": {
            row.response_type: row.count for row in response_type_stats
        },
        "brand_positioning": {
            row.brand_positioning: row.count for row in brand_positioning_stats
        },
        "sufficiency_levels": {
            row.sufficiency_level: row.count for row in sufficiency_stats
        }
    }


@api_router.get("/classification/unprocessed")
def get_unprocessed_runs(
    project_id: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Retorna lista de runs que ainda não foram classificadas"""
    from app.services.classification_integration import ClassificationIntegrator

    with ClassificationIntegrator(db) as integrator:
        unclassified_ids = integrator.get_unclassified_runs(project_id, limit)

    return {
        "unclassified_runs": unclassified_ids,
        "count": len(unclassified_ids),
        "project_id": project_id,
        "limit": limit
    }


# ============================================================================
# ADVANCED ANALYTICS ENDPOINTS
# ============================================================================

@api_router.get("/projects/{project_id}/analytics/brand-presence")
def get_brand_presence_analytics(
    project_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Métricas de presença da marca (% consultas com BB, evolução temporal)"""
    from app.services.advanced_analytics import AdvancedAnalyticsService

    # Verificar se o projeto existe
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    analytics = AdvancedAnalyticsService(db)
    return analytics.get_brand_presence_metrics(project_id, days)


@api_router.get("/projects/{project_id}/analytics/competitive-share")
def get_competitive_share_analytics(
    project_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Análise de share competitivo e gaps de conteúdo"""
    from app.services.advanced_analytics import AdvancedAnalyticsService

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    analytics = AdvancedAnalyticsService(db)
    return analytics.get_competitive_share_analysis(project_id, days)


@api_router.get("/projects/{project_id}/analytics/satisfaction-quality")
def get_satisfaction_quality_analytics(
    project_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Métricas de satisfação e qualidade por LLM"""
    from app.services.advanced_analytics import AdvancedAnalyticsService

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    analytics = AdvancedAnalyticsService(db)
    return analytics.get_satisfaction_and_quality_metrics(project_id, days)


@api_router.get("/projects/{project_id}/analytics/conversion-value")
def get_conversion_value_analytics(
    project_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Métricas de valor financeiro e potencial de conversão"""
    from app.services.advanced_analytics import AdvancedAnalyticsService

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    analytics = AdvancedAnalyticsService(db)
    return analytics.get_conversion_and_value_metrics(project_id, days)


@api_router.get("/projects/{project_id}/analytics/comprehensive-dashboard")
def get_comprehensive_dashboard(
    project_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Dashboard completo com todas as métricas avançadas integradas"""
    from app.services.advanced_analytics import AdvancedAnalyticsService

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    analytics = AdvancedAnalyticsService(db)
    return analytics.get_comprehensive_dashboard(project_id, days)


@api_router.get("/projects/{project_id}/analytics/content-gaps")
def get_content_gap_opportunities(
    project_id: str,
    days: int = 30,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Lista de oportunidades onde concorrentes aparecem mas BB está ausente"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Buscar runs com gaps de conteúdo
    gap_runs = db.query(
        Run.id,
        Run.prompt_version_id,
        Run.competitive_mentions,
        Run.financial_value_score,
        Run.user_intent,
        Run.finished_at
    ).filter(
        Run.project_id == project_id,
        Run.status == "completed",
        Run.finished_at >= cutoff_date,
        Run.content_gap_detected == True,
        Run.financial_value_score >= 5.0  # Apenas gaps de valor médio/alto
    ).order_by(
        Run.financial_value_score.desc()
    ).limit(limit).all()

    gap_opportunities = []
    for run in gap_runs:
        # Buscar texto do prompt
        prompt_text = None
        try:
            prompt_version = db.query(PromptVersion).filter(
                PromptVersion.id == run.prompt_version_id
            ).first()
            if prompt_version:
                prompt_text = prompt_version.text[:200] + "..." if len(prompt_version.text) > 200 else prompt_version.text
        except:
            pass

        gap_opportunities.append({
            "run_id": run.id,
            "prompt_preview": prompt_text,
            "competitive_mentions": run.competitive_mentions,
            "financial_value": run.financial_value_score,
            "user_intent": run.user_intent,
            "date": run.finished_at.isoformat() if run.finished_at else None
        })

    return {
        "project_id": project_id,
        "period_days": days,
        "total_gaps_found": len(gap_opportunities),
        "opportunities": gap_opportunities
    }


# ============================================================================
# GEMINI-POWERED CLASSIFICATION ENDPOINTS
# ============================================================================

@api_router.post("/runs/{run_id}/classify/gemini")
def classify_run_with_gemini_endpoint(run_id: str, db: Session = Depends(get_db)):
    """Classifica uma run específica usando Gemini 2.0 Flash"""
    from app.services.gemini_integration import classify_run_with_gemini

    # Verificar se a run existe
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrada")

    # Executar classificação com Gemini
    result = classify_run_with_gemini(run_id)

    if result is None:
        raise HTTPException(status_code=400, detail="Falha ao classificar com Gemini")

    return {
        "run_id": run_id,
        "classification": {
            "response_type": result.response_type.value,
            "sufficiency_level": result.sufficiency_level.value,
            "actionability_type": result.actionability_type.value,
            "trust_source": result.trust_source.value,
            "brand_positioning": result.brand_positioning.value,
            "confidence": result.confidence
        },
        "advanced_metrics": {
            "user_intent": result.user_intent.value,
            "satisfaction_score": result.satisfaction_score,
            "competitive_mentions": result.competitive_mentions,
            "financial_value_score": result.financial_value_score,
            "content_gap_detected": result.content_gap_detected,
            "conversion_potential": result.conversion_potential.value
        },
        "ai_insights": {
            "strategic_insights": result.strategic_insights,
            "optimization_suggestions": result.optimization_suggestions,
            "reasoning": result.reasoning
        },
        "classified_at": datetime.utcnow().isoformat(),
        "version": "2.0-gemini"
    }


@api_router.post("/projects/{project_id}/classify/gemini/batch")
def batch_classify_with_gemini_endpoint(
    project_id: str,
    limit: int = 500,
    db: Session = Depends(get_db)
):
    """Classifica runs de um projeto em lote usando Gemini 2.0 Flash"""
    from app.services.gemini_integration import batch_classify_with_gemini_service

    # Verificar se o projeto existe
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Executar classificação em lote com Gemini
    results = batch_classify_with_gemini_service(project_id=project_id, limit=limit)

    # Estatísticas do processamento
    total_processed = len(results)
    successful = sum(1 for r in results.values() if r is not None)
    failed = total_processed - successful

    # Análise de insights
    strategic_insights = []
    optimization_suggestions = []

    for result in results.values():
        if result:
            strategic_insights.extend(result.strategic_insights)
            optimization_suggestions.extend(result.optimization_suggestions)

    # Remover duplicatas e pegar top insights
    unique_insights = list(set(strategic_insights))[:10]
    unique_suggestions = list(set(optimization_suggestions))[:10]

    return {
        "project_id": project_id,
        "processing_summary": {
            "total_processed": total_processed,
            "successful": successful,
            "failed": failed,
            "success_rate": round(successful / total_processed * 100, 1) if total_processed > 0 else 0,
            "limit": limit
        },
        "aggregated_insights": {
            "strategic_insights": unique_insights,
            "optimization_suggestions": unique_suggestions
        },
        "processed_at": datetime.utcnow().isoformat(),
        "version": "2.0-gemini"
    }


@api_router.get("/projects/{project_id}/insights/gemini")
def get_gemini_insights_summary(
    project_id: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Obtém resumo de insights estratégicos gerados pelo Gemini"""
    from app.services.gemini_integration import get_gemini_insights_for_project

    # Verificar se o projeto existe
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    insights = get_gemini_insights_for_project(project_id, days)
    return insights


@api_router.get("/projects/{project_id}/classification/gemini-status")
def get_gemini_classification_status(project_id: str, db: Session = Depends(get_db)):
    """Verifica status das classificações com Gemini para um projeto"""

    # Verificar se o projeto existe
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Contar runs por versão de classificação
    total_runs = db.query(func.count(Run.id)).filter(
        Run.project_id == project_id,
        Run.status == "completed"
    ).scalar() or 0

    gemini_classified = db.query(func.count(Run.id)).filter(
        Run.project_id == project_id,
        Run.status == "completed",
        Run.classification_version == "2.0-gemini"
    ).scalar() or 0

    basic_classified = db.query(func.count(Run.id)).filter(
        Run.project_id == project_id,
        Run.status == "completed",
        Run.classification_version == "1.0"
    ).scalar() or 0

    unclassified = db.query(func.count(Run.id)).filter(
        Run.project_id == project_id,
        Run.status == "completed",
        Run.response_type.is_(None)
    ).scalar() or 0

    # Qualidade média das classificações Gemini
    gemini_avg_confidence = db.query(
        func.avg(Run.classification_confidence)
    ).filter(
        Run.project_id == project_id,
        Run.classification_version == "2.0-gemini",
        Run.classification_confidence.isnot(None)
    ).scalar() or 0.0

    return {
        "project_id": project_id,
        "classification_status": {
            "total_completed_runs": total_runs,
            "gemini_classified": gemini_classified,
            "basic_classified": basic_classified,
            "unclassified": unclassified,
            "gemini_coverage": round(gemini_classified / total_runs * 100, 1) if total_runs > 0 else 0,
            "gemini_avg_confidence": round(float(gemini_avg_confidence), 2)
        },
        "recommendations": {
            "should_upgrade_to_gemini": basic_classified > 0,
            "needs_initial_classification": unclassified > 0,
            "upgrade_candidates": basic_classified,
            "new_classification_needed": unclassified
        }
    }


@api_router.post("/classification/migrate-to-gemini")
def migrate_existing_classifications_to_gemini(
    project_id: str = None,
    limit: int = 200,
    db: Session = Depends(get_db)
):
    """Migra classificações básicas existentes para análise avançada do Gemini"""
    from app.services.gemini_integration import batch_classify_with_gemini_service

    # Buscar runs com classificação básica que podem ser upgradeadas
    query = db.query(Run.id).filter(
        Run.status == "completed",
        Run.classification_version == "1.0",  # Apenas básicas
        Run.response_type.isnot(None)  # Já classificadas
    )

    if project_id:
        # Verificar se o projeto existe
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Projeto não encontrado")
        query = query.filter(Run.project_id == project_id)

    migration_candidates = [row[0] for row in query.limit(limit).all()]

    if not migration_candidates:
        return {
            "message": "Nenhuma classificação básica encontrada para migração",
            "project_id": project_id,
            "candidates_found": 0
        }

    # Executar migração
    print(f"[GEMINI_MIGRATION] Migrando {len(migration_candidates)} runs para Gemini")
    results = batch_classify_with_gemini_service(project_id=project_id, limit=limit)

    successful_migrations = sum(1 for r in results.values() if r is not None)

    return {
        "migration_summary": {
            "candidates_found": len(migration_candidates),
            "processed": len(results),
            "successful_migrations": successful_migrations,
            "migration_rate": round(successful_migrations / len(migration_candidates) * 100, 1) if migration_candidates else 0
        },
        "project_id": project_id,
        "limit": limit,
        "completed_at": datetime.utcnow().isoformat()
    }
