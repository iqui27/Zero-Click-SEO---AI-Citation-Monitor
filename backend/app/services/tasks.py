from __future__ import annotations

from datetime import datetime
import json
import time
import os
import asyncio
from typing import Any

from celery import Celery
from celery.exceptions import SoftTimeLimitExceeded
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

# Global task time limits (soft/hard) via env, to avoid indefinite runs
_SOFT_TL = int(os.getenv("CELERY_SOFT_TIME_LIMIT", os.getenv("RUN_SOFT_TIME_LIMIT", "900")))  # 15 min default
_HARD_TL = int(os.getenv("CELERY_TIME_LIMIT", os.getenv("RUN_HARD_TIME_LIMIT", "1200")))     # 20 min default


def _log(db: Session, run_id: str, step: str, status: str, message: str | None = None) -> None:
    db.add(RunEvent(run_id=run_id, version=step, status=status, message=message))
    db.commit()


def enqueue_run(run_id: str, cycles: int = 1) -> None:
    celery.send_task("tasks.execute_run", args=[run_id, cycles], queue="runs")


@celery.task(name="tasks.execute_run", soft_time_limit=_SOFT_TL, time_limit=_HARD_TL)
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
        # Per-cycle timeout (sec): Engine config wins, else env RUN_CYCLE_TIMEOUT_SECONDS, else default 180s
        timeout_cfg = None
        try:
            timeout_cfg = (engine.config_json or {}).get("timeout_seconds")
        except Exception:
            timeout_cfg = None
        timeout_env = os.getenv("RUN_CYCLE_TIMEOUT_SECONDS") or os.getenv("RUN_TIMEOUT_SECONDS")
        try:
            timeout_seconds: float | None = float(timeout_cfg) if timeout_cfg is not None else (float(timeout_env) if timeout_env else 180.0)
        except Exception:
            timeout_seconds = 180.0

        aborted_due_timeout = False
        for i in range(total_cycles):
            # Apply cycle delay before each cycle (except the first one)
            if i > 0 and run.cycle_delay_seconds and run.cycle_delay_seconds > 0:
                delay_seconds = run.cycle_delay_seconds
                _log(db, run.id, "delay", "started", f"Waiting {delay_seconds}s before cycle {i+1}/{total_cycles}")
                time.sleep(delay_seconds)
                _log(db, run.id, "delay", "ok", f"Delay completed for cycle {i+1}")
            
            _log(db, run.id, "fetch", "started", f"Engine: {engine.name} (cycle {i+1}/{total_cycles})")
            t_fetch0 = time.perf_counter()
            try:
                raw, parsed, extracted = run_engine(engine.name, fetch_input, timeout_seconds=timeout_seconds)
                t_fetch1 = time.perf_counter()
                _log(db, run.id, "fetch", "ok", f"{int((t_fetch1 - t_fetch0)*1000)} ms")
            except Exception as e:
                # Distinguish timeout vs other failures
                if isinstance(e, asyncio.TimeoutError):
                    _log(db, run.id, "fetch", "timeout", f"> {timeout_seconds}s at cycle {i+1}/{total_cycles}")
                    aborted_due_timeout = True
                    break
                else:
                    _log(db, run.id, "fetch", "fail", str(e)[:4000])
                    raise

            last_raw, last_parsed = raw, parsed

            # stream simples do texto (chunk)
            if parsed.get("text"):
                _log(db, run.id, "chunk", "ok", (parsed.get("text") or "")[:4000])

            # persist evidence
            _log(db, run.id, "persist", "started")
            t_persist0 = time.perf_counter()
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
            t_persist1 = time.perf_counter()
            _log(db, run.id, "persist", "ok", f"{int((t_persist1 - t_persist0)*1000)} ms")

            # extract citations
            _log(db, run.id, "extract", "started")
            t_extract0 = time.perf_counter()
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
            t_extract1 = time.perf_counter()
            _log(db, run.id, "extract", "ok", f"{len(extracted)} items in {int((t_extract1 - t_extract0)*1000)} ms")

        if aborted_due_timeout:
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            db.commit()
            _log(db, run.id, "error", "fail", f"Run aborted due to timeout (> {timeout_seconds}s)")
            return

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
    except SoftTimeLimitExceeded as e:
        # Celery soft timeout triggered: log and mark failed, so the UI reflects termination
        try:
            _log(db, run_id, "error", "timeout", f"Soft time limit exceeded: {_SOFT_TL}s")
            run = db.get(Run, run_id)
            if run:
                run.status = "failed"
                run.finished_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
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
