from __future__ import annotations

from datetime import datetime
import json
import time
from typing import Any

from celery import Celery
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import Run, Evidence, Citation, Domain, Engine, RunEvent, Insight
from app.services.insights import generate_basic_insights
from app.services.kpis import compute_run_report
from app.services.normalization import normalize_domain
from app.services.engine_runner import run_engine
from app.services.costs import compute_cost_usd, estimate_usage_from_text, get_default_pricing

celery = Celery(
    "seo_monitor",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


def _log(db: Session, run_id: str, step: str, status: str, message: str | None = None) -> None:
    db.add(RunEvent(run_id=run_id, step=step, status=status, message=message))
    db.commit()


def enqueue_run(run_id: str, cycles: int = 1) -> None:
    celery.send_task("tasks.execute_run", args=[run_id, cycles], queue="runs")


@celery.task(name="tasks.execute_run")
def execute_run(run_id: str, cycles: int = 1) -> None:
    db: Session = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if not run:
            return
        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()
        _log(db, run.id, "queued", "ok", "Run started")

        engine = db.get(Engine, run.engine_id)
        query_text = db.execute(
            text(
                """
                SELECT pv.text, p.variables_json
                FROM prompt_versions pv
                JOIN prompts p ON pv.prompt_id = p.id
                WHERE pv.id = :pvid
                """
            ),
            {"pvid": run.prompt_version_id},
        ).mappings().first()
        prompt_text = query_text["text"] if query_text else ""

        fetch_input = {
            "query": prompt_text,
            "language": "pt-BR",
            "region": engine.region or "BR",
            "device": engine.device or "desktop",
            "config": engine.config_json or {},
        }

        # Logar opções efetivas usadas no fetch para auditoria/debug
        try:
            cfg = (engine.config_json or {})

            # Calcular web_search efetivo respeitando defaults por engine
            def compute_effective_web_search(engine_name: str, cfg_dict: dict) -> bool:
                name = (engine_name or "").lower()
                if name == "gemini":
                    # Gemini: default é True, a não ser que use_search === False
                    if "use_search" in cfg_dict:
                        return bool(cfg_dict.get("use_search"))
                    if "web_search" in cfg_dict:
                        return bool(cfg_dict.get("web_search"))
                    return True
                # Demais engines: considerar apenas web_search explícito (default False)
                if "web_search" in cfg_dict:
                    return bool(cfg_dict.get("web_search"))
                return False

            cfg_used = {
                "model": cfg.get("model"),
                # Mantém compatibilidade, mas agora reflete o default correto por engine
                "web_search": compute_effective_web_search(engine.name, cfg),
                # Reporta também o campo específico do Gemini quando presente
                "use_search": cfg.get("use_search"),
                "search_context_size": cfg.get("search_context_size"),
                "reasoning_effort": cfg.get("reasoning_effort"),
                "max_output_tokens": cfg.get("max_output_tokens"),
                "web_search_force": cfg.get("web_search_force"),
                "user_location": cfg.get("user_location"),
            }
            _log(db, run.id, "opts", "ok", json.dumps(cfg_used, ensure_ascii=False)[:4000])
        except Exception:
            pass

        total_cycles = max(1, int(cycles or 1))
        aggregated_extracted: list[dict[str, Any]] = []
        project_domains = {normalize_domain(d.domain) for d in db.query(Domain).filter(Domain.project_id == run.project_id).all()}
        t0_all = time.perf_counter()
        last_raw: dict[str, Any] | None = None
        last_parsed: dict[str, Any] | None = None
        for i in range(total_cycles):
            _log(db, run.id, "fetch", "started", f"Engine: {engine.name} (cycle {i+1}/{total_cycles})")
            raw, parsed, extracted = run_engine(engine.name, fetch_input)
            _log(db, run.id, "fetch", "ok")

            last_raw, last_parsed = raw, parsed

            # stream simples do texto (chunk)
            if parsed.get("text"):
                _log(db, run.id, "chunk", "ok", (parsed.get("text") or "")[:4000])

            # persist evidence
            _log(db, run.id, "persist", "started")
            ev = Evidence(
                run_id=run.id,
                raw_url=raw.get("raw_url"),
                parsed_json={
                    "raw": raw.get("raw"),
                    "parsed": {"text": parsed.get("text"), "links": parsed.get("links"), "meta": parsed.get("meta")},
                },
                screenshot_url=None,
                content_hash=None,
            )
            db.add(ev)
            db.commit()
            _log(db, run.id, "persist", "ok")

            # extract citations
            _log(db, run.id, "extract", "started")
            for c in extracted:
                aggregated_extracted.append(c)
                domain_norm = normalize_domain(c.get("url") or c.get("domain") or "")
                is_ours = domain_norm in project_domains
                db.add(
                    Citation(
                        run_id=run.id,
                        domain=domain_norm,
                        url=c.get("url"),
                        anchor=c.get("anchor"),
                        position=c.get("position"),
                        type=c.get("type"),
                        is_ours=is_ours,
                    )
                )
            db.commit()
            _log(db, run.id, "extract", "ok")

        t1_all = time.perf_counter()

        # métricas finais
        try:
            meta = (last_parsed or {}).get("meta") if last_parsed else {}
            usage = (meta or {}).get("raw_usage") or (meta or {}).get("usage")
            if not usage:
                usage = estimate_usage_from_text((last_parsed or {}).get("text"))
            tokens_input = None
            tokens_output = None
            tokens_total = None
            # Definição do modelo usada (prioriza o configurado na Engine)
            model_name = (engine.config_json or {}).get("model") or (meta or {}).get("model") or (meta or {}).get("engine") or engine.name
            if isinstance(usage, dict):
                # Preferir tokens faturáveis calculados por costs._extract_tokens (com desconto de cache)
                from app.services.costs import _extract_tokens as _extract_tokens_internal
                ti, to, tt = _extract_tokens_internal(usage)
                tokens_input = ti
                tokens_output = to
                if tokens_input is not None and tokens_output is not None:
                    tokens_total = int(tokens_input) + int(tokens_output)
            if tokens_total is None and tokens_input is not None:
                tokens_total = int(tokens_input) + int(tokens_output or 0)

            citations_count = len(aggregated_extracted)
            extracted_domains = [normalize_domain(c.get("url") or c.get("domain") or "") for c in aggregated_extracted]
            our_citations_count = sum(1 for d in extracted_domains if d and d in project_domains)
            unique_domains_count = len({d for d in extracted_domains if d})
            # Pricing: mesclar defaults por (engine, model) com config_json
            base_cfg = dict(engine.config_json or {})
            default_pricing_cfg = get_default_pricing(engine.name, str(model_name or "")) or {}
            # merge raso: se usuário definiu pricing em config_json, mantém; senão aplica default
            if default_pricing_cfg and not base_cfg.get("pricing"):
                base_cfg.update(default_pricing_cfg)
            cost_usd = compute_cost_usd(base_cfg, usage if isinstance(usage, dict) else None)

            run.tokens_input = int(tokens_input) if tokens_input is not None else None
            run.tokens_output = int(tokens_output) if tokens_output is not None else None
            run.tokens_total = int(tokens_total) if tokens_total is not None else None
            run.model_name = str(model_name) if model_name else None
            run.latency_ms = int((t1_all - t0_all) * 1000)
            run.citations_count = citations_count
            run.our_citations_count = our_citations_count
            run.unique_domains_count = unique_domains_count
            run.cost_usd = cost_usd
        except Exception:
            pass

        # KPI (AMR/DCR/ZCRS) – calcular e persistir ao final da run para alimentar os painéis
        try:
            _ = compute_run_report(db, run.id)
        except Exception:
            pass

        run.status = "completed"
        run.finished_at = datetime.utcnow()
        try:
            for ins in generate_basic_insights(db, run):
                db.add(ins)
            db.commit()
        except Exception:
            pass
        db.commit()
        _log(db, run.id, "completed", "ok")
    except Exception as e:
        _log(db, run_id, "error", "fail", str(e))
        try:
            run = db.get(Run, run_id)
            if run:
                run.status = "failed"
                run.finished_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
