from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, text, literal_column
from fastapi.responses import StreamingResponse
import asyncio
import io
import csv
import os

from app.db.session import SessionLocal
from app.models.models import Project, Domain, Prompt, PromptVersion, Engine, Run, Citation, Reason, Evidence, RunEvent, SubProject, PromptTemplate, Monitor, MonitorTemplate
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
)
from app.services.tasks import enqueue_run
from app.services.kpis import compute_run_report
from app.services.insights import generate_basic_insights
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.sql import case

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


@api_router.delete("/domains/{domain_id}")
def delete_domain(domain_id: str, db: Session = Depends(get_db)):
    d = db.get(Domain, domain_id)
    if not d:
        raise HTTPException(status_code=404, detail="Domínio não encontrado")
    db.delete(d)
    db.commit()
    return {"ok": True}


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
                engine = Engine(
                    project_id=payload.project_id,
                    name=engine_payload.name,
                    region=engine_payload.region,
                    device=engine_payload.device,
                    config_json=req_cfg,
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
        )
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
            )
        )

    return created_runs


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
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 100,
    order_by: str | None = None,
    order_dir: str | None = None,
):
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
            func.coalesce(Prompt.name, literal_column("'—'")) .label("template_name"),
            func.coalesce(SubProject.name, literal_column("'—'")) .label("subproject_name"),
        )
        .join(Engine, Engine.id == Run.engine_id)
        .outerjoin(PromptVersion, PromptVersion.id == Run.prompt_version_id)
        .outerjoin(Prompt, Prompt.id == PromptVersion.prompt_id)
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
    if dir_is_asc:
        q = q.order_by(sort_col.asc().nullslast(), Run.id.asc())
    else:
        q = q.order_by(sort_col.desc().nullslast(), Run.id.desc())

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
            subproject_name=getattr(r, "subproject_name", None),
            cost_usd=getattr(r, "cost_usd", None),
            tokens_total=getattr(r, "tokens_total", None),
        )
        for r in rows
    ]

# Workaround: forçar registro explícito do GET /runs
api_router.add_api_route("/runs", list_runs, methods=["GET"], response_model=list[RunListItem])


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
    if dir_is_asc:
        q = q.order_by(sort_col.asc().nullslast(), Run.id.asc())
    else:
        q = q.order_by(sort_col.desc().nullslast(), Run.id.desc())

    rows = q.all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id",
        "engine",
        "status",
        "started_at",
        "finished_at",
        "model_name",
        "tokens_input",
        "tokens_output",
        "tokens_total",
        "latency_ms",
        "cost_usd",
    ])
    for r in rows:
        writer.writerow([
            r.id,
            r.engine,
            r.status,
            r.started_at.isoformat() if r.started_at else "",
            r.finished_at.isoformat() if r.finished_at else "",
            r.model_name or "",
            r.tokens_input if r.tokens_input is not None else "",
            r.tokens_output if r.tokens_output is not None else "",
            r.tokens_total if r.tokens_total is not None else "",
            r.latency_ms if r.latency_ms is not None else "",
            f"{float(r.cost_usd):.6f}" if r.cost_usd is not None else "",
        ])
    buf.seek(0)
    headers = {"Content-Disposition": "attachment; filename=runs_export.csv"}
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)


@api_router.get("/analytics/overview", response_model=OverviewAnalytics)
def analytics_overview(db: Session = Depends(get_db)):
    total_runs = db.query(func.count(Run.id)).scalar() or 0
    # média de boolean como 0/1 via CASE
    amr_avg = (
        db.query(func.avg(case((Run.amr_flag.is_(True), 1), else_=0))).scalar() or 0.0
    )
    dcr_avg = (
        db.query(func.avg(case((Run.dcr_flag.is_(True), 1), else_=0))).scalar() or 0.0
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
    )


@api_router.get("/runs/{run_id}/events")
def list_run_events(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run não encontrado")
    evs = db.query(RunEvent).filter(RunEvent.run_id == run_id).order_by(RunEvent.created_at.asc()).all()
    return [
        {
            "step": e.step,
            "status": e.status,
            "message": e.message,
            "created_at": e.created_at.isoformat(),
        }
        for e in evs
    ]


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
            f"\"step\":\"{e.step}\",\"status\":\"{e.status}\",\"message\":{json_escape(e.message)},\"created_at\":\"{e.created_at.isoformat()}\"" +
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
    series = (
        db.query(
            func.date_trunc('day', Run.started_at).label('day'),
            Engine.name.label('engine'),
            func.sum(func.coalesce(Run.cost_usd, 0.0)).label('cost_usd'),
            func.sum(func.coalesce(Run.tokens_total, 0)).label('tokens')
        )
        .join(Engine, Engine.id == Run.engine_id)
        .filter(Run.started_at.isnot(None))
    )
    if project_id:
        series = series.filter(Run.project_id == project_id)
    if subproject_id:
        series = series.filter(Run.subproject_id == subproject_id)
    if engine:
        series = series.filter(Engine.name == engine)
    if date_from:
        series = series.filter(Run.started_at >= text(":df")).params(df=date_from)
    if date_to:
        series = series.filter(Run.started_at <= text(":dt")).params(dt=date_to)
    series = series.group_by('day', Engine.name).order_by('day').all()
    series_out = [
        {"day": d.isoformat(), "engine": eng, "cost_usd": float(c or 0), "tokens": int(t or 0)}
        for (d, eng, c, t) in series
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


@api_router.get("/projects/{project_id}/subprojects")
def list_subprojects(project_id: str, db: Session = Depends(get_db)):
    sps = db.query(SubProject).filter(SubProject.project_id == project_id).all()
    return [{"id": s.id, "name": s.name, "description": s.description} for s in sps]


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
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "category": t.category, "name": t.name}


@api_router.get("/projects/{project_id}/templates")
def list_templates(project_id: str, category: str | None = None, db: Session = Depends(get_db)):
    q = db.query(PromptTemplate).filter(PromptTemplate.project_id == project_id)
    if category:
        q = q.filter(PromptTemplate.category == category)
    items = q.order_by(PromptTemplate.category.asc(), PromptTemplate.name.asc()).all()
    return [
        {
            "id": t.id,
            "category": t.category,
            "name": t.name,
            "text": t.text,
            "intent": t.intent,
            "persona": t.persona,
        }
        for t in items
    ]


@api_router.patch("/templates/{template_id}")
def update_template(template_id: str, payload: dict, db: Session = Depends(get_db)):
    t = db.get(PromptTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    for k in ["category", "name", "text", "intent", "persona"]:
        if k in payload and payload[k] is not None:
            setattr(t, k, payload[k])
    db.commit()
    db.refresh(t)
    return {"id": t.id, "category": t.category, "name": t.name}


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
              date_trunc('day', runs.started_at) AS day,
              AVG(CASE WHEN runs.amr_flag IS TRUE THEN 1 ELSE 0 END) AS amr_avg,
              AVG(CASE WHEN runs.dcr_flag IS TRUE THEN 1 ELSE 0 END) AS dcr_avg,
              AVG(runs.zcrs) AS zcrs_avg
            FROM runs
            WHERE runs.subproject_id = :sp AND runs.started_at IS NOT NULL
            GROUP BY day
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
               AVG(CASE WHEN r.amr_flag IS TRUE THEN 1 ELSE 0 END) AS amr_avg,
               AVG(CASE WHEN r.dcr_flag IS TRUE THEN 1 ELSE 0 END) AS dcr_avg,
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
    return [
        {
            "id": m.id,
            "name": m.name,
            "subproject_id": m.subproject_id,
            "schedule_cron": m.schedule_cron,
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
                engine = Engine(
                    project_id=mon.project_id,
                    name=e.get("name"),
                    region=e.get("region"),
                    device=e.get("device"),
                    config_json=e.get("config_json"),
                )
                db.add(engine)
                db.commit()
                db.refresh(engine)
            run = Run(
                project_id=mon.project_id,
                prompt_version_id=pv.id,
                engine_id=engine.id,
                subproject_id=mon.subproject_id,
                monitor_id=mon.id,
                status="queued",
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


@api_router.get("/monitors/{monitor_id}/runs")
def list_runs_by_monitor(monitor_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(Run.id, Run.status, Run.started_at, Run.finished_at, Run.zcrs)
        .filter(Run.monitor_id == monitor_id)
        .order_by(Run.started_at.desc().nullslast(), Run.id.desc())
        .all()
    )
    return [
        {"id": r.id, "status": r.status, "started_at": r.started_at, "finished_at": r.finished_at, "zcrs": r.zcrs}
        for r in rows
    ]


@api_router.get("/projects/{project_id}/engines")
def list_engines(project_id: str, db: Session = Depends(get_db)):
    engs = db.query(Engine).filter(Engine.project_id == project_id).all()
    return [
        {
            "id": e.id,
            "name": e.name,
            "region": e.region,
            "device": e.device,
            "config_json": e.config_json,
        }
        for e in engs
    ]


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
        db.query(Citation.run_id, Citation.url)
        .join(Run, Run.id == Citation.run_id)
        .filter(Run.subproject_id == subproject_id)
        .all()
    )
    run_to_urls: dict[str, list[str]] = {}
    for rid, url in cits:
        run_to_urls.setdefault(rid, []).append(url or "")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["run_id", "started_at", "finished_at", "status", "engine", "zcrs", "amr", "dcr", "citations"])
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
        ])
    buf.seek(0)
    headers = {"Content-Disposition": f"attachment; filename=subproject_{subproject_id}.csv"}
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)


@api_router.get("/setup/status")
def setup_status() -> dict:
    has_env = os.path.exists(".env")
    keys = {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "gemini": bool(os.getenv("GOOGLE_API_KEY")),
        "perplexity": bool(os.getenv("PERPLEXITY_API_KEY")),
        "serpapi": bool(os.getenv("SERPAPI_KEY")),
    }
    sandbox = not any(keys.values())
    return {"has_env": has_env, "keys": keys, "sandbox": sandbox}


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
    # Gemini
    try:
        import google.generativeai as genai  # type: ignore
        key = payload.get("gemini_key") or os.getenv("GOOGLE_API_KEY")
        ok = False
        if key:
            genai.configure(api_key=key)
            _ = genai.list_models()
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


@api_router.get("/projects/{project_id}/stats")
def project_stats(project_id: str, db: Session = Depends(get_db)):
    sp_count = db.query(func.count(SubProject.id)).filter(SubProject.project_id == project_id).scalar() or 0
    run_count = db.query(func.count(Run.id)).filter(Run.project_id == project_id).scalar() or 0
    return {"subprojects": int(sp_count), "runs": int(run_count)}
