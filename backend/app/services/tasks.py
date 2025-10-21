from __future__ import annotations

from datetime import datetime, date
import json
import time
import os
import asyncio
import logging
from typing import Any

from celery import Celery, Task
from celery.exceptions import SoftTimeLimitExceeded, Retry
from celery.signals import task_prerun, task_postrun, task_failure, task_retry
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import (
    Run,
    Evidence,
    Citation,
    Domain,
    Engine,
    RunEvent,
    Insight,
    Project,
    RunSemanticInsight,
    PromptVersion,
    SerpFeature,
)
from app.services.insights import generate_basic_insights
from app.services.kpis import compute_run_report
from app.services.normalization import normalize_domain, normalize_url_for_dedupe
from app.services.engine_runner import run_engine
from app.services.engine_registry import apply_overrides, get_engine_base_config
from app.services.costs import compute_cost_usd, estimate_usage_from_text, get_default_pricing
from app.services.gemini_semantic import GeminiSemanticService
from app.services.geo_metrics import calculate_all_geo_metrics
from app.services.gemini_integration import GeminiClassificationIntegrator
from app.services.semantic_payload import store_insight_payload, load_insight_payload
from app.services.evidence_payload import store_evidence_payload, load_evidence_payload
from app.services.geo_dashboard import compute_geo_dashboard
from app.services.geo_daily_metrics import (
    recompute_geo_daily_metrics,
    DEFAULT_WINDOWS,
    DEFAULT_BRAND_PRESENCE,
)

logger = logging.getLogger(__name__)

# Initialize Celery with optimized configuration
celery = Celery(
    "seo_monitor",
    broker=settings.get_celery_broker_url(),
    backend=settings.get_celery_result_backend(),
)

# Celery configuration
celery.conf.update(
    # Task execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_default_queue="runs",
    task_default_exchange="runs",
    task_default_routing_key="runs",

    # Worker optimization
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    worker_max_tasks_per_child=settings.celery_worker_max_tasks_per_child,
    worker_disable_rate_limits=True,

    # Result backend
    result_backend_transport_options={
        "master_name": "mymaster",
        "socket_keepalive": True,
        "socket_connect_timeout": 5,
    },
    result_expires=3600 * 24,  # 24 hours

    # Task retry policy
    task_acks_late=True,  # Acknowledge tasks after execution
    task_reject_on_worker_lost=True,

    # Broker connection
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,

    # Redis broker options
    broker_transport_options={
        "visibility_timeout": 3600,  # 1 hour
        "max_connections": settings.redis_max_connections,
        "socket_keepalive": True,
        "socket_connect_timeout": 5,
    },
)

# Task time limits from settings
_SOFT_TL = settings.celery_task_soft_time_limit
_HARD_TL = settings.celery_task_time_limit


# Custom base task with logging
class LoggingTask(Task):
    """Base task class with automatic logging"""

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {self.name}[{task_id}] succeeded", extra={
            "task_id": task_id,
            "task_name": self.name,
            "args": args,
        })

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {self.name}[{task_id}] failed: {exc}", extra={
            "task_id": task_id,
            "task_name": self.name,
            "args": args,
            "error": str(exc),
        }, exc_info=True)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(f"Task {self.name}[{task_id}] retrying: {exc}", extra={
            "task_id": task_id,
            "task_name": self.name,
            "args": args,
            "error": str(exc),
        })


# Celery signals for monitoring
@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    logger.debug(f"Task {task.name}[{task_id}] starting")


@task_postrun.connect
def task_postrun_handler(task_id, task, *args, **kwargs):
    logger.debug(f"Task {task.name}[{task_id}] completed")


@task_failure.connect
def task_failure_handler(task_id, exception, *args, **kwargs):
    logger.error(f"Task {task_id} failed: {exception}")


@task_retry.connect
def task_retry_handler(task_id, *args, **kwargs):
    logger.warning(f"Task {task_id} retrying")


def _log(db: Session, run_id: str, step: str, status: str, message: str | None = None) -> None:
    db.add(RunEvent(run_id=run_id, version=step, status=status, message=message))
    db.commit()


def _finalize_run(db: Session, run: Run, message: str | None = None) -> None:
    if run.status == "failed":
        return
    already_completed = run.status == "completed"
    run.status = "completed"
    if run.finished_at is None:
        run.finished_at = datetime.utcnow()
    db.commit()
    if not already_completed and run.project_id:
        metric_dt = (run.finished_at or run.started_at or datetime.utcnow()).date()
        try:
            refresh_geo_daily_metrics_task.delay(run.project_id, metric_dt.isoformat())
            logger.info(
                "Queued geo_daily_metrics refresh",
                extra={
                    "project_id": run.project_id,
                    "metric_date": metric_dt.isoformat(),
                },
            )
        except Exception as exc:
            logger.warning(
                "Failed to enqueue geo_daily_metrics refresh",
                extra={
                    "project_id": run.project_id,
                    "metric_date": metric_dt.isoformat(),
                    "error": str(exc),
                },
            )
    if not already_completed or message:
        _log(db, run.id, "completed", "ok", message)


def _persist_serp_feature_details(db: Session, run_id: str, serp_metrics: dict[str, Any]) -> None:
    print(f"[SERP_PERSIST] Iniciando persistência para run {run_id}")
    print(f"[SERP_PERSIST] serp_metrics is None? {serp_metrics is None}")
    print(f"[SERP_PERSIST] serp_metrics empty? {not serp_metrics}")
    
    if not serp_metrics:
        print(f"[SERP_PERSIST] ABORTANDO: serp_metrics vazio")
        return

    features = serp_metrics.get("serp_features") or {}
    print(f"[SERP_PERSIST] Features: {features}")
    
    feature = db.query(SerpFeature).filter(SerpFeature.run_id == run_id).one_or_none()
    if not feature:
        feature = SerpFeature(run_id=run_id)
        db.add(feature)
        print(f"[SERP_PERSIST] Criou novo SerpFeature")

    feature.has_featured_snippet = bool(features.get("featured_snippet"))
    feature.has_paa = bool(features.get("people_also_ask"))
    feature.has_knowledge_panel = bool(features.get("knowledge_graph"))
    feature.has_ai_overview = bool(features.get("ai_overview"))
    feature.has_local_pack = bool(features.get("local_pack"))
    feature.has_video_carousel = bool(features.get("video_carousel"))
    feature.has_image_pack = bool(features.get("image_pack"))

    paa_items = serp_metrics.get("paa_items") or []
    if paa_items:
        feature.paa_questions = json.dumps([item.get("question") for item in paa_items if item.get("question")], ensure_ascii=False)[:8000]
        feature.paa_items = json.dumps(paa_items, ensure_ascii=False)[:16000]
    else:
        feature.paa_questions = None
        feature.paa_items = None

    knowledge_panel = serp_metrics.get("knowledge_panel")
    feature.knowledge_panel_json = (
        json.dumps(knowledge_panel, ensure_ascii=False)[:16000] if knowledge_panel else None
    )

    ai_overview = serp_metrics.get("ai_overview")
    feature.ai_overview_json = (
        json.dumps(ai_overview, ensure_ascii=False)[:20000] if ai_overview else None
    )

    featured_snippet = serp_metrics.get("featured_snippet")
    feature.featured_snippet_content = (
        json.dumps(featured_snippet, ensure_ascii=False)[:8000] if featured_snippet else None
    )

    feature.organic_position = serp_metrics.get("organic_position")
    feature.competitors_in_top10 = serp_metrics.get("competitors_top10") or 0

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

        base_cfg = get_engine_base_config(engine)
        cfg_eff = apply_overrides(base_cfg, run.engine_override_json)
        name_lower = (engine.name or "").lower()

        # Forçar país/region BR em todas as runs, conforme política do projeto
        fetch_input = {
            "query": prompt_text,
            "language": "pt-BR",
            "region": "BR",
            "device": (engine.device or "desktop"),
            "config": cfg_eff,
        }

        # Logar opções efetivas usadas no fetch para auditoria/debug
        try:
            cfg_used = {
                "model": cfg_eff.get("model"),
                # valores efetivos (sem null) após merge de defaults
                "web_search": cfg_eff.get("web_search"),
                "use_search": cfg_eff.get("use_search"),
                "force_search": cfg_eff.get("force_search"),
                "search_context_size": cfg_eff.get("search_context_size"),
                "reasoning_effort": cfg_eff.get("reasoning_effort"),
                "max_output_tokens": cfg_eff.get("max_output_tokens"),
                "web_search_force": cfg_eff.get("web_search_force"),
                "user_location": cfg_eff.get("user_location"),
                # Contexto efetivo
                "language": fetch_input.get("language"),
                "region": fetch_input.get("region"),
                "device": fetch_input.get("device"),
            }
            _log(db, run.id, "opts", "ok", json.dumps(cfg_used, ensure_ascii=False)[:4000])
        except Exception:
            pass

        total_cycles = max(1, int(cycles or 1))
        aggregated_extracted: list[dict[str, Any]] = []
        seen_citation_keys: set[str] = set()
        semantic_pending = False
        project_domains = {normalize_domain(d.domain) for d in db.query(Domain).filter(Domain.project_id == run.project_id).all()}
        t0_all = time.perf_counter()
        last_raw: dict[str, Any] | None = None
        last_parsed: dict[str, Any] | None = None
        # Per-cycle timeout (sec): Engine config wins, else env RUN_CYCLE_TIMEOUT_SECONDS, else default 180s
        timeout_cfg = None
        timeout_cfg = cfg_eff.get("timeout_seconds")
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
            
            model_for_log = cfg_eff.get("model")
            _log(db, run.id, "fetch", "started", f"Engine: {engine.name} model={model_for_log} (cycle {i+1}/{total_cycles})")
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

            # Registrar métricas de uso e ferramentas quando disponíveis
            try:
                meta_obj = parsed.get("meta") if isinstance(parsed, dict) else None
                usage_log: dict[str, Any] = {}
                if isinstance(meta_obj, dict):
                    raw_usage = meta_obj.get("raw_usage")
                    if isinstance(raw_usage, dict):
                        usage_log["usage"] = raw_usage
                    for key in ("web_search_calls", "web_search_used", "search_context_size"):
                        if key in meta_obj:
                            usage_log[key] = meta_obj.get(key)

                tool_types: set[str] = set()
                tool_call_count = 0
                raw_payload = raw.get("raw") if isinstance(raw, dict) else None
                response_dict = raw_payload.get("response") if isinstance(raw_payload, dict) else None
                if isinstance(response_dict, dict):
                    output_items = response_dict.get("output")
                    if isinstance(output_items, list):
                        for item in output_items:
                            if not isinstance(item, dict):
                                continue
                            item_type = item.get("type")
                            if isinstance(item_type, str) and item_type.endswith("_call"):
                                tool_call_count += 1
                                tool_types.add(item_type)
                if tool_call_count:
                    usage_log["tool_calls"] = tool_call_count
                    usage_log["tool_types"] = sorted(tool_types)

                if usage_log:
                    _log(db, run.id, "usage", "ok", json.dumps(usage_log, ensure_ascii=False)[:4000])
            except Exception:
                pass

            # stream simples do texto (chunk)
            if parsed.get("text"):
                _log(db, run.id, "chunk", "ok", (parsed.get("text") or "")[:4000])

            # persist evidence (JSON-safe + resilient)
            _log(db, run.id, "persist", "started")
            t_persist0 = time.perf_counter()
            def _make_json_safe(obj: Any):
                import json as _json
                try:
                    _json.dumps(obj, ensure_ascii=False, default=str)
                    return obj
                except Exception:
                    pass
                # strip problematic internals
                try:
                    if isinstance(obj, dict):
                        return {k: _make_json_safe(v) for k, v in obj.items() if k not in ("__obj", "__obj_fallback")}  # type: ignore[dict-item]
                    if isinstance(obj, list):
                        return [_make_json_safe(x) for x in obj]
                except Exception:
                    return str(obj)
                try:
                    return str(obj)
                except Exception:
                    return None
            raw_safe = _make_json_safe(raw.get("raw"))
            parsed_safe = _make_json_safe({
                "text": parsed.get("text"),
                "links": parsed.get("links"),
                "meta": parsed.get("meta"),
            })
            try:
                response_text_value = None
                if isinstance(parsed_safe, dict):
                    response_text_value = parsed_safe.get("text")
                text_trimmed = (response_text_value or "")
                text_trimmed = text_trimmed if isinstance(text_trimmed, str) else str(text_trimmed)
                links_value = None
                if isinstance(parsed_safe, dict) and isinstance(parsed_safe.get("links"), list):
                    links_value = parsed_safe.get("links")
                meta_value = None
                if isinstance(parsed_safe, dict) and isinstance(parsed_safe.get("meta"), dict):
                    meta_value = parsed_safe.get("meta")

                payload = {"raw": raw_safe, "parsed": parsed_safe}

                ev = Evidence(
                    run_id=run.id,
                    raw_url=raw.get("raw_url"),
                    screenshot_url=None,
                    content_hash=None,
                    response_text=text_trimmed or None,
                    response_links_json=links_value,
                    response_meta_json=meta_value,
                    has_text=bool((text_trimmed or "").strip()),
                )

                store_evidence_payload(ev, payload)

                db.add(ev)
                db.commit()
                t_persist1 = time.perf_counter()
                _log(db, run.id, "persist", "ok", f"{int((t_persist1 - t_persist0)*1000)} ms")
            except Exception as e:
                try:
                    db.rollback()
                except Exception:
                    pass
                _log(db, run.id, "persist", "fail", (str(e) or "persist_exception")[:4000])

            # extract citations
            _log(db, run.id, "extract", "started")
            t_extract0 = time.perf_counter()
            unique_before_cycle = len(aggregated_extracted)
            processed_links_cycle = 0
            for c in extracted:
                raw_url = c.get("url") or c.get("domain") or ""
                if not raw_url:
                    continue
                processed_links_cycle += 1

                normalized_url = normalize_url_for_dedupe(raw_url)
                domain_norm = normalize_domain(raw_url or c.get("domain") or "")
                if not domain_norm and normalized_url:
                    domain_norm = normalize_domain(normalized_url)
                if not normalized_url and raw_url:
                    normalized_url = raw_url.strip()

                key_base = normalized_url or domain_norm
                if not key_base:
                    key_base = (c.get("anchor") or raw_url or "").strip()
                if not key_base:
                    continue

                if key_base in seen_citation_keys:
                    continue
                seen_citation_keys.add(key_base)

                position_raw = c.get("position")
                if isinstance(position_raw, (int, float)):
                    position_value_int = int(position_raw)
                elif isinstance(position_raw, str):
                    try:
                        position_value_int = int(position_raw.strip())
                    except ValueError:
                        position_value_int = len(seen_citation_keys)
                else:
                    position_value_int = len(seen_citation_keys)
                position_value = str(position_value_int)

                is_ours = bool(domain_norm and domain_norm in project_domains)

                aggregated_extracted.append(
                    {
                        "url": raw_url,
                        "domain": domain_norm,
                        "type": c.get("type"),
                        "anchor": c.get("anchor"),
                        "position": position_value_int,
                        "is_ours": is_ours,
                    }
                )

                db.add(
                    Citation(
                        run_id=run.id,
                        domain=domain_norm,
                        url=raw_url,
                        anchor=c.get("anchor"),
                        position=position_value,
                        type=c.get("type"),
                        is_ours=is_ours,
                    )
                )
            db.commit()
            t_extract1 = time.perf_counter()
            unique_after_cycle = len(aggregated_extracted)
            unique_added = max(0, unique_after_cycle - unique_before_cycle)
            _log(
                db,
                run.id,
                "extract",
                "ok",
                f"{unique_added}/{processed_links_cycle or len(extracted)} unique citations in {int((t_extract1 - t_extract0)*1000)} ms",
            )

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
            extracted_domains = [c["domain"] for c in aggregated_extracted if c.get("domain")]
            our_citations_count = sum(1 for item in aggregated_extracted if item.get("is_ours"))
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
            
            # Log web_search_calls para tracking
            web_search_calls = (meta or {}).get("web_search_calls", 0)
            web_search_used = (meta or {}).get("web_search_used", False)
            search_context_size = (meta or {}).get("search_context_size")
            
            if web_search_calls > 0 or web_search_used:
                import json
                ws_info = {
                    "web_search_calls": web_search_calls,
                    "web_search_used": web_search_used,
                    "search_context_size": search_context_size,
                    "model": model_name,
                }
                _log(db, run.id, "web_search", "ok", json.dumps(ws_info))
        except Exception:
            pass

        # KPI (AMR/DCR/ZCRS) – calcular e persistir ao final da run para alimentar os painéis
        try:
            _ = compute_run_report(db, run.id)
        except Exception:
            pass

        # === VERIFICAR TIPO DE ENGINE: SERP vs LLM ===
        engine = db.get(Engine, run.engine_id) if run.engine_id else None
        engine_name = engine.name.lower() if engine else ""
        is_llm = any(llm in engine_name for llm in ["chatgpt", "gemini", "perplexity", "claude", "gpt", "openai"])
        
        print(f"[ENGINE_TYPE] Run {run.id} - Engine: {engine_name} - Is LLM: {is_llm}")
        
        # Para LLMs: pular IM-SEO e ir direto para semantic insights (que inclui GEO)
        if is_llm:
            print(f"[DEBUG] Pulando IM-SEO metrics - run é LLM (métricas GEO serão calculadas em semantic insights)")
            
            # Salvar response_text se disponível
            response_text = (last_parsed or {}).get("text") if last_parsed else None
            print(f"[DEBUG] response_text length: {len(response_text) if response_text else 0}, last_parsed exists: {last_parsed is not None}")
            if response_text:
                run.response_text = response_text[:50000]
                db.commit()
                print(f"[DEBUG] response_text saved to run: {len(run.response_text)} chars")
            
            # Enfileirar semantic insights (que inclui GEO)
            if settings.semantic_insights_enabled and response_text:
                try:
                    process_semantic_insights.delay(run.id)
                    _log(db, run.id, "semantic_insights", "queued", "Gemini semantic insights + GEO metrics enqueued")
                except Exception as queue_err:
                    print(f"[SEMANTIC] Falha ao enfileirar insights para run {run.id}: {queue_err}")
                    _log(db, run.id, "semantic_insights", "fail", f"queue error: {queue_err}")
            else:
                _log(db, run.id, "semantic_insights", "skip", "No response_text or semantic insights disabled")
            
            # Pular para buscar dados do Search Console (não calcular IM metrics)
        else:
            # === CÁLCULO DE MÉTRICAS IM-SEO / IM-SEOIA (APENAS PARA SERP) ===
            print(f"[DEBUG] Iniciando cálculo de métricas IM-SEO para run SERP {run.id}")
            try:
                from app.services.im_metrics_simple import SimpleIMMetrics
                
                _log(db, run.id, "im_metrics", "started", "Calculating IM-SEO and IM-SEOIA metrics")
                print(f"[DEBUG] Log de im_metrics.started enviado")
                
                # Preparar dados para cálculo
                response_text = (last_parsed or {}).get("text") if last_parsed else None
                print(f"[DEBUG] response_text length: {len(response_text) if response_text else 0}")
                
                # Salvar response_text na run para análises futuras
                if response_text:
                    run.response_text = response_text[:50000]  # Limitar tamanho
                
                # Classificar etapa do funil
                try:
                    from app.services.funnel_classifier import FunnelClassifier
                    prompt_version = db.get(PromptVersion, run.prompt_version_id)
                    prompt_text = prompt_version.text if prompt_version else ""
                    
                    funnel_stage, confidence = FunnelClassifier.classify_with_confidence(
                        prompt_text=prompt_text,
                        response_text=response_text
                    )
                    run.funnel_stage = funnel_stage
                    print(f"[FUNNEL] Classificado como '{funnel_stage}' (confiança: {confidence:.2f})")
                except Exception as e:
                    print(f"[FUNNEL] Erro ao classificar: {e}")
                
                # Buscar citações da run
                citations_list = db.query(Citation).filter(Citation.run_id == run.id).all()
                citations_data = [
                    {
                        "domain": c.domain,
                        "url": c.url,
                        "is_ours": c.is_ours,
                    }
                    for c in citations_list
                ]
                
                # Preparar dados da run
                run_data = {
                    "amr_flag": run.amr_flag,
                    "dcr_flag": run.dcr_flag,
                    "zcrs": run.zcrs,
                }
                
                # Buscar dados do SerpAPI se disponíveis
                serp_data = None
                project_domains = []
                target_url = None
                try:
                    # Buscar evidence para extrair dados SERP
                    evidence = db.query(Evidence).filter(Evidence.run_id == run.id).first()
                    if evidence:
                        serp_data = load_evidence_payload(evidence)

                    # Buscar domínios do projeto
                    project = db.query(Project).filter(Project.id == run.project_id).first()
                    if project:
                        domains_list = db.query(Domain).filter(Domain.project_id == project.id).all()
                        project_domains = [d.domain for d in domains_list]
                    
                    # Tentar extrair URL alvo das citações (primeira citação nossa)
                    for cit in citations_data:
                        if cit.get("is_ours"):
                            target_url = cit.get("url")
                            break
                    
                    # Se não houver citação nossa, usar domínio primário do projeto como fallback
                    if not target_url and project_domains:
                        primary_domain = db.query(Domain).filter(
                            Domain.project_id == project.id,
                            Domain.is_primary == True
                        ).first()
                        if primary_domain:
                            target_url = f"https://{primary_domain.domain}"
                            print(f"[IM_METRICS] Usando domínio primário como fallback: {target_url}")
                        elif project_domains:
                            # Se não tiver primário, usar o primeiro domínio
                            target_url = f"https://{project_domains[0]}"
                            print(f"[IM_METRICS] Usando primeiro domínio como fallback: {target_url}")
                except Exception as e:
                    print(f"[IM_METRICS] Erro ao buscar dados SERP: {e}")
                
                # Calcular todas as métricas (com SerpAPI e PageSpeed se disponíveis)
                print(f"[DEBUG] Chamando SimpleIMMetrics.calculate_all...")
                im_metrics = SimpleIMMetrics.calculate_all(
                    run_data, 
                    citations_data, 
                    response_text,
                    serp_data=serp_data,
                    project_domains=project_domains,
                    target_url=target_url
                )
                print(f"[DEBUG] Métricas calculadas: IM-SEO={im_metrics.get('im_seo_score')}, IM-SEOIA={im_metrics.get('im_seoia_score')}")
                
                # Atualizar run com métricas calculadas
                run.im_seo_score = im_metrics["im_seo_score"]
                run.im_seoia_score = im_metrics["im_seoia_score"]
                run.core_web_vitals_score = im_metrics["core_web_vitals_score"]
                run.lcp_score = im_metrics.get("lcp_score")
                run.fid_score = im_metrics.get("fid_score")
                run.cls_score = im_metrics.get("cls_score")
                run.share_of_voice_serp = im_metrics["share_of_voice_serp"]
                
                # E-E-A-T
                eeat = im_metrics["eeat"]
                run.eeat_score = eeat["overall"]
                run.eeat_expertise = eeat["expertise"]
                run.eeat_experience = eeat["experience"]
                run.eeat_authoritativeness = eeat["authoritativeness"]
                run.eeat_trustworthiness = eeat["trustworthiness"]
                
                # IA-Ready Blocks
                ia_ready = im_metrics["ia_ready"]
                run.ia_ready_score = ia_ready["score"]
                run.ia_ready_blocks_count = ia_ready["blocks_count"]
                run.has_lists = ia_ready["has_lists"]
                run.has_faqs = ia_ready["has_faqs"]
                run.has_tables = ia_ready["has_tables"]
                run.has_step_by_step = ia_ready["has_step_by_step"]
                
                # IRZC
                irzc = im_metrics["irzc"]
                run.irzc_score = irzc["score"]
                run.ctr_expected = irzc["ctr_expected"]
                
                # Entidades
                entities = im_metrics["entities"]
                run.entities_detected = entities["detected"]
                run.entities_relevance_score = entities["relevance_score"]
                run.entity_connection_score = entities["connection_score"]
                
                # Métricas do SerpAPI (se disponíveis)
                run.serp_features_presence = im_metrics.get("serp_features_presence")
                run.ia_resources_detected = im_metrics.get("ia_resources_detected")
                run.ia_serp_presence_score = im_metrics.get("ia_serp_presence_score")
                run.long_tail_terms_top10 = im_metrics.get("longtail_terms_top10")
                run.long_tail_terms_top20 = im_metrics.get("longtail_terms_top20")
                run.long_tail_coverage_score = im_metrics.get("longtail_coverage_score")
                run.schema_types_detected = im_metrics.get("schema_types_detected")
                run.schema_coverage_score = im_metrics.get("schema_coverage_score")
                
                # Posição orgânica e competidores
                run.organic_position = im_metrics.get("organic_position")
                run.competitors_in_top10 = im_metrics.get("competitors_top10") or 0

                # Persistir SERP features detalhadas
                serp_metrics_data = im_metrics.get("serp_metrics") or {}
                print(f"[DEBUG] serp_metrics keys: {list(serp_metrics_data.keys())}")
                print(f"[DEBUG] PAA items: {len(serp_metrics_data.get('paa_items', []))}")
                _persist_serp_feature_details(db, run.id, serp_metrics_data)

                db.commit()
                print(f"[DEBUG] Métricas salvas no banco com sucesso!")
                
                _log(db, run.id, "im_metrics", "ok", f"IM-SEO: {run.im_seo_score}, IM-SEOIA: {run.im_seoia_score}")

                if settings.semantic_insights_enabled:
                    try:
                        process_semantic_insights.delay(run.id)
                        semantic_pending = True
                        _log(db, run.id, "semantic_insights", "queued", "Gemini semantic insights enqueued")
                    except Exception as queue_err:
                        print(f"[SEMANTIC] Falha ao enfileirar insights para run {run.id}: {queue_err}")
                        _log(db, run.id, "semantic_insights", "fail", f"queue error: {queue_err}")
            except Exception as e:
                print(f"[DEBUG] ERRO no cálculo de métricas: {e}")
                import traceback
                traceback.print_exc()
                _log(db, run.id, "im_metrics", "fail", f"IM metrics calculation error: {str(e)}")
        
        # === BUSCAR DADOS DO GOOGLE SEARCH CONSOLE ===
        try:
            from app.services.search_console import SearchConsoleService
            
            # Buscar projeto
            project = db.query(Project).filter(Project.id == run.project_id).first()
            
            # Verificar se Search Console está conectado
            if project and project.search_console_token and project.search_console_site_url:
                # Buscar query/prompt text
                prompt_version = db.get(PromptVersion, run.prompt_version_id)
                query_text = prompt_version.text if prompt_version else ""
                
                _log(db, run.id, "search_console", "started", "Fetching data from Google Search Console")
                print(f"[SEARCH_CONSOLE] Buscando dados para query: {query_text}")
                
                # Buscar dados (últimos 7 dias)
                import asyncio
                gsc_data = asyncio.run(SearchConsoleService.get_query_data(
                    credentials_json=project.search_console_token,
                    site_url=project.search_console_site_url,
                    query=query_text
                ))
                
                if gsc_data.get("has_data"):
                    # Atualizar run com dados reais
                    run.ctr_real = gsc_data['ctr'] * 100  # Converter para %
                    
                    # Calcular CTR ratio se temos CTR esperado
                    if run.ctr_expected and run.ctr_real:
                        run.ctr_ratio = run.ctr_real / run.ctr_expected
                        
                        # Recalcular IRZC com dados reais
                        run.irzc_score = SearchConsoleService.calculate_irzc_with_real_data(
                            ctr_ratio=run.ctr_ratio,
                            zero_click_features=run.ia_resources_detected or 0
                        )
                    
                    db.commit()
                    _log(db, run.id, "search_console", "ok", f"CTR Real: {run.ctr_real:.2f}%, Clicks: {gsc_data['clicks']}, Impressions: {gsc_data['impressions']}")
                    print(f"[SEARCH_CONSOLE] ✅ Dados obtidos - CTR: {run.ctr_real:.2f}%, IRZC: {run.irzc_score}")
                else:
                    _log(db, run.id, "search_console", "no_data", "No data found for this query in Search Console")
                    print(f"[SEARCH_CONSOLE] ⚠️ Sem dados para esta query")
            else:
                print(f"[SEARCH_CONSOLE] Search Console não conectado para este projeto")
                
        except Exception as e:
            print(f"[SEARCH_CONSOLE] Erro ao buscar dados: {e}")
            import traceback
            traceback.print_exc()
            _log(db, run.id, "search_console", "fail", f"Error: {str(e)}")

        try:
            for ins in generate_basic_insights(db, run):
                db.add(ins)
        except Exception:
            pass

        if semantic_pending:
            run.status = "post_processing"
            run.finished_at = None
            db.commit()
            _log(db, run.id, "post_processing", "ok", "Waiting for semantic insights")
        else:
            _finalize_run(db, run)
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


@celery.task(name="tasks.process_semantic_insights", queue="runs", soft_time_limit=600, time_limit=900)
def process_semantic_insights(run_id: str) -> None:
    """Gera insights semânticos via Gemini para uma run já processada."""
    if not settings.semantic_insights_enabled:
        return

    db: Session = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if not run:
            return

        response_text = (run.response_text or "").strip()
        if not response_text:
            print(f"[SEMANTIC] Run {run_id} sem response_text. Abortando insights.")
            return

        prompt_version = db.get(PromptVersion, run.prompt_version_id)
        question_text = (prompt_version.text if prompt_version else "").strip()

        citations = db.query(Citation).filter(Citation.run_id == run_id).all()
        citations_payload = [
            {
                "domain": cite.domain,
                "url": cite.url,
                "is_ours": cite.is_ours,
            }
            for cite in citations
        ]

        project = db.get(Project, run.project_id)
        project_name = project.name if project else None

        # Fallback: se project_name for None/vazio, tentar usar um nome genérico
        # Isso garante que GEO metrics sejam calculadas mesmo com dados incompletos
        if not project_name and project:
            project_name = f"Project_{run.project_id[:8]}"  # Fallback genérico
            print(f"[SEMANTIC] ⚠️ Project name is None, using fallback: {project_name}")

        _log(db, run.id, "semantic_insights", "started", "Gemini semantic analysis")

        service = GeminiSemanticService()
        payload = service.analyze(
            question=question_text or "",
            response_text=response_text,
            citations=citations_payload,
            project_name=project_name,
        )

        insight = db.get(RunSemanticInsight, run_id)
        if insight is None:
            insight = RunSemanticInsight(run_id=run_id)
            db.add(insight)
        store_insight_payload(insight, payload)
        insight.updated_at = datetime.utcnow()

        perception = payload.get("perception") or {}
        primary_category = perception.get("primary_category") or perception.get("category")
        if primary_category:
            run.perceived_value_category = primary_category

        summary = payload.get("summary") or {}
        headline = summary.get("headline") or summary.get("title")
        bullets = summary.get("bullets") or summary.get("opportunities") or []
        # Construir resumo curto (limitar 2000 chars)
        pieces = []
        if headline:
            pieces.append(headline.strip())
        if bullets:
            try:
                bullets_text = "; ".join(str(b).strip() for b in bullets if str(b).strip())
            except Exception:
                bullets_text = ""
            if bullets_text:
                pieces.append(bullets_text)
        summary_text = " — ".join(pieces)
        if summary_text:
            run.semantic_summary = summary_text[:2000]

        entities_count = len(payload.get("entities", []))
        relationships = payload.get("relationships", [])
        avg_weight = 0.0
        if relationships:
            weights = [rel.get("weight") or 0.0 for rel in relationships]
            avg_weight = sum(weights) / max(len(weights), 1)
        if entities_count > 0:
            run.entities_detected = entities_count
            avg_conf = sum((entity.get("confidence") or 0.0) for entity in payload.get("entities", [])) / entities_count
            run.entities_relevance_score = round(avg_conf, 3)
        if avg_weight:
            run.entity_connection_score = round(avg_weight * 100, 2)

        # === MÉTRICAS GEO (Generative Engine Optimization) ===
        # IMPORTANTE: Só calcular para runs de LLMs (ChatGPT, Gemini, Perplexity)
        # NÃO calcular para SERP tradicional
        engine = db.get(Engine, run.engine_id) if run.engine_id else None
        engine_name = engine.name.lower() if engine else ""
        is_llm = any(llm in engine_name for llm in ["chatgpt", "gemini", "perplexity", "claude", "gpt", "openai"])

        # Calcular GEO para LLMs com response_text (project_name opcional com fallback)
        if is_llm and response_text:
            try:
                # Garantir que temos um project_name válido
                geo_project_name = project_name or (f"Project_{run.project_id[:8]}" if run.project_id else "Unknown")
                print(f"[GEO] Calculando métricas GEO para run {run_id} (project: {geo_project_name})")

                # Preparar citations para GEO
                citations_for_geo = [
                    {
                        "domain": cite.domain,
                        "url": cite.url,
                        "anchor": cite.anchor,
                        "position": cite.position,
                        "is_ours": cite.is_ours,
                    }
                    for cite in citations
                ]
                
                # Buscar variantes de domínio (se existirem)
                # TODO: Implementar query para DomainVariant quando tabela estiver criada
                domain_variants_map = {}  # Placeholder
                
                # Buscar competitors do payload Gemini
                competitors_from_gemini = payload.get("competitors", [])
                
                # Detectar nome da marca a partir dos domínios ou usar nome do projeto
                # Ex: bb.com.br -> "Banco do Brasil" ou "BB"
                brand_name = geo_project_name  # Usar o nome seguro com fallback
                brand_variations = []

                if project and hasattr(project, 'domains') and project.domains:
                    # Tentar inferir nome da marca a partir do domínio principal
                    main_domain = project.domains[0].domain if project.domains else None
                    if main_domain:
                        domain_lower = main_domain.lower()
                        # Mapeamento de domínios conhecidos para nomes de marca
                        brand_map = {
                            "bb.com.br": ("Banco do Brasil", ["BB", "Banco do Brasil", "bancodobrasil"]),
                            "nubank.com.br": ("Nubank", ["Nu", "Nubank"]),
                            "itau.com.br": ("Itaú", ["Itau", "Itaú"]),
                            "bradesco.com.br": ("Bradesco", ["Bradesco"]),
                            "santander.com.br": ("Santander", ["Santander"]),
                        }

                        if domain_lower in brand_map:
                            brand_name, brand_variations = brand_map[domain_lower]

                # Calcular todas as métricas GEO
                geo_metrics = calculate_all_geo_metrics(
                    response_text=response_text,
                    project_name=brand_name,
                    citations=citations_for_geo,
                    competitors_from_gemini=competitors_from_gemini,
                    project_domains=[d.domain for d in project.domains] if project and project.domains else [],
                    brand_variations=brand_variations if brand_variations else None,
                    domain_variants_map=domain_variants_map,
                )
                
                # Atualizar campos GEO no Run
                run.brand_mention_count = geo_metrics.get("brand_mention_count")
                run.brand_first_mention_position = geo_metrics.get("brand_first_mention_position")
                run.brand_mention_density = geo_metrics.get("brand_mention_density")
                run.brand_prominence_score = geo_metrics.get("brand_prominence_score")
                
                run.citation_quality_score = geo_metrics.get("citation_quality_score")
                run.first_citation_position = geo_metrics.get("first_citation_position")
                run.citation_rate_observed = geo_metrics.get("citation_rate_observed")
                run.citation_rate_corrected = geo_metrics.get("citation_rate_corrected")
                
                run.competitor_mention_ratio = geo_metrics.get("competitor_mention_ratio")
                run.share_of_voice_llm = geo_metrics.get("share_of_voice_llm")
                run.cocitation_competitors = geo_metrics.get("cocitation_competitors")
                
                run.conversational_trigger_count = geo_metrics.get("conversational_trigger_count")
                run.engagement_score = geo_metrics.get("engagement_score")
                
                # Advanced Metrics (Phase 2+)
                run.zero_click_presence = geo_metrics.get("zero_click_presence")
                run.authority_score = geo_metrics.get("authority_score")
                run.relevance_score = geo_metrics.get("relevance_score")
                run.clarity_score = geo_metrics.get("clarity_score")
                run.conversion_potential = geo_metrics.get("conversion_potential")
                run.conversion_potential_score = geo_metrics.get("conversion_potential_score")
                run.product_category = geo_metrics.get("product_category")
                
                print(f"[GEO] Métricas calculadas: prominence={geo_metrics.get('brand_prominence_score')}, sov={geo_metrics.get('share_of_voice_llm')}, product={geo_metrics.get('product_category')}")
                _log(db, run.id, "geo_metrics", "ok", f"prominence={geo_metrics.get('brand_prominence_score')}, sov={geo_metrics.get('share_of_voice_llm')}, zero_click={geo_metrics.get('zero_click_presence')}")
                
            except Exception as geo_exc:
                print(f"[GEO] Erro ao calcular métricas GEO para run {run_id}: {geo_exc}")
                import traceback
                traceback.print_exc()
                _log(db, run.id, "geo_metrics", "fail", str(geo_exc))
                # Não falhar o processo todo se GEO falhar

        # Classificação Zero-Click com Gemini (após GEO)
        try:
            print(f"[CLASSIFICATION] Iniciando classificação Zero-Click para run {run_id}")
            _log(db, run.id, "classification", "started", "Gemini Zero-Click classification")

            integrator = GeminiClassificationIntegrator(db=db)
            classification_result = integrator.classify_and_update_run_with_gemini(run_id, response_text)

            if classification_result:
                print(f"[CLASSIFICATION] Run {run_id} classificada: {classification_result.response_type.value}/{classification_result.brand_positioning.value} (confiança: {classification_result.confidence:.2f})")
                _log(db, run.id, "classification", "ok", f"type={classification_result.response_type.value}, positioning={classification_result.brand_positioning.value}, confidence={classification_result.confidence:.2f}")
            else:
                print(f"[CLASSIFICATION] Falha ao classificar run {run_id}")
                _log(db, run.id, "classification", "fail", "Classification returned None")

        except Exception as class_exc:
            print(f"[CLASSIFICATION] Erro ao classificar run {run_id}: {class_exc}")
            import traceback
            traceback.print_exc()
            _log(db, run.id, "classification", "fail", str(class_exc))
            # Não falhar o processo todo se classificação falhar

        # === CLASSIFICAÇÃO GEO COM GEMINI (funnel, question_type, product_category) ===
        try:
            from app.services.geo_classifier import classify_run_with_gemini

            print(f"[GEO_CLASSIFIER] Iniciando classificação GEO para run {run_id}")
            _log(db, run.id, "geo_classifier", "started", "Gemini GEO classification")

            classification = classify_run_with_gemini(run, db)

            if classification:
                run.funnel_stage = classification.get("funnel_stage")
                run.question_type = classification.get("question_type")

                # Se product_category não foi calculado pelo GEO metrics, usar do classificador
                if not run.product_category:
                    run.product_category = classification.get("product_category")

                db.commit()

                print(f"[GEO_CLASSIFIER] Run {run_id} classificada: funnel={run.funnel_stage}, type={run.question_type}, category={run.product_category}")
                _log(db, run.id, "geo_classifier", "ok", f"funnel={run.funnel_stage}, type={run.question_type}, category={run.product_category}")
            else:
                _log(db, run.id, "geo_classifier", "skip", "No classification returned")

        except Exception as clf_exc:
            print(f"[GEO_CLASSIFIER] Erro ao classificar run {run_id}: {clf_exc}")
            import traceback
            traceback.print_exc()
            _log(db, run.id, "geo_classifier", "fail", str(clf_exc))
            # Não falhar o processo todo se classificação falhar

        # === ANÁLISE SEMÂNTICA GEO COM GEMINI (semantic_scores) ===
        try:
            from app.services.geo_semantic_analyzer import analyze_semantic_scores

            print(f"[GEO_SEMANTIC] Iniciando análise semântica GEO para run {run_id}")
            _log(db, run.id, "geo_semantic", "started", "Gemini semantic quality analysis")

            semantic_scores = analyze_semantic_scores(run, db)

            if semantic_scores and any(v is not None for v in semantic_scores.values()):
                # Armazenar scores no RunSemanticInsight (adicionar ao payload existente)
                insight = db.get(RunSemanticInsight, run_id)
                if insight is None:
                    insight = RunSemanticInsight(run_id=run_id)
                    db.add(insight)

                existing_payload = load_insight_payload(insight)
                existing_payload["semantic_scores"] = semantic_scores
                store_insight_payload(insight, existing_payload)
                insight.updated_at = datetime.utcnow()

                db.commit()

                print(f"[GEO_SEMANTIC] Run {run_id} analisada: authority={semantic_scores.get('authority')}, relevance={semantic_scores.get('relevance')}")
                _log(db, run.id, "geo_semantic", "ok", f"authority={semantic_scores.get('authority')}, relevance={semantic_scores.get('relevance')}, clarity={semantic_scores.get('clarity')}")
            else:
                _log(db, run.id, "geo_semantic", "skip", "No semantic scores returned")

        except Exception as sem_exc:
            print(f"[GEO_SEMANTIC] Erro ao analisar semanticamente run {run_id}: {sem_exc}")
            import traceback
            traceback.print_exc()
            _log(db, run.id, "geo_semantic", "fail", str(sem_exc))
            # Não falhar o processo todo se análise semântica falhar

        # Refresh run object para garantir que temos a versão mais recente
        # Isso é importante porque GeminiClassificationIntegrator pode ter atualizado o run
        try:
            db.refresh(run)
            print(f"[DEBUG] Run object refreshed before commit")
        except Exception as refresh_exc:
            print(f"[DEBUG] Could not refresh run object: {refresh_exc}")

        db.commit()
        print(f"[DEBUG] Final commit completed for run {run_id}")
        _log(db, run.id, "semantic_insights", "ok", f"entities={entities_count}, perception={primary_category}")
        _finalize_run(db, run, "Semantic insights completed")

    except Exception as exc:
        db.rollback()
        print(f"[SEMANTIC] Erro ao gerar insights para run {run_id}: {exc}")
        _log(db, run_id, "semantic_insights", "fail", str(exc))
        run = db.get(Run, run_id)
        if run:
            _finalize_run(db, run, "Semantic insights failed")
    finally:
        db.close()


@celery.task(name="compute_geo_dashboard_task", soft_time_limit=600, time_limit=720)
def compute_geo_dashboard_task(
    project_id: str,
    prompt_id: str | None = None,
    prompt_version_id: str | None = None,
    subproject_id: str | None = None,
    date_from_str: str | None = None,
    date_to_str: str | None = None,
    bank_ids: list[str] | None = None,
    llm_model: str | None = None,
    prompt_category: str | None = None,
    prompt_text: str | None = None,
    brand_presence: str | None = None,
    web_structure_page: int = 1,
    web_structure_page_size: int = 30,
    force_materialized: bool = True,
) -> dict:
    """
    Task Celery para processar GEO Dashboard em background.
    Timeout de 5 minutos (soft) e 6 minutos (hard).
    """
    from datetime import date as date_type
    
    db = SessionLocal()
    
    try:
        print(f"[GEO-TASK] Iniciando processamento para projeto {project_id}")
        
        # Parse dates
        date_from = date_type.fromisoformat(date_from_str) if date_from_str else None
        date_to = date_type.fromisoformat(date_to_str) if date_to_str else None
        
        # Compute dashboard
        result = compute_geo_dashboard(
            db=db,
            project_id=project_id,
            prompt_id=prompt_id,
            prompt_version_id=prompt_version_id,
            subproject_id=subproject_id,
            date_from=date_from,
            date_to=date_to,
            bank_ids=bank_ids,
            llm_model=llm_model,
            prompt_category=prompt_category,
            prompt_text=prompt_text,
            brand_presence=brand_presence,
            force_materialized=force_materialized,
            web_structure_page=web_structure_page,
            web_structure_page_size=web_structure_page_size,
        )
        
        print(f"[GEO-TASK] Processamento concluído para projeto {project_id}")
        
        # Converter para dict serializável
        return {
            "status": "completed",
            "data": result.dict() if hasattr(result, 'dict') else result,
            "project_id": project_id,
        }
        
    except SoftTimeLimitExceeded:
        print(f"[GEO-TASK] Timeout ao processar projeto {project_id}")
        return {
            "status": "timeout",
            "error": "Processamento excedeu o tempo limite de 5 minutos",
            "project_id": project_id,
        }
    except Exception as exc:
        print(f"[GEO-TASK] Erro ao processar projeto {project_id}: {exc}")
        return {
            "status": "error",
            "error": str(exc),
            "project_id": project_id,
        }
    finally:
        db.close()


@celery.task(name="tasks.refresh_geo_daily_metrics", queue="runs", soft_time_limit=600, time_limit=720)
def refresh_geo_daily_metrics_task(
    project_id: str,
    metric_date_str: str,
    windows: list[int] | None = None,
    brand_presences: list[str] | None = None,
) -> dict:
    """
    Materializa as métricas agregadas do GEO Dashboard para um projeto/data.
    """
    db = SessionLocal()
    try:
        metric_date = date.fromisoformat(metric_date_str)
    except ValueError:
        return {
            "status": "error",
            "error": f"Invalid metric_date '{metric_date_str}' - expected YYYY-MM-DD",
        }

    try:
        result = recompute_geo_daily_metrics(
            db=db,
            project_id=project_id,
            metric_date=metric_date,
            windows=windows or DEFAULT_WINDOWS,
            brand_presences=brand_presences or DEFAULT_BRAND_PRESENCE,
        )
        return {
            "status": "completed",
            "project_id": project_id,
            "metric_date": metric_date.isoformat(),
            "metadata": result,
        }
    except Exception as exc:
        logger.error(
            "Failed to recompute geo_daily_metrics",
            extra={
                "project_id": project_id,
                "metric_date": metric_date_str,
                "error": str(exc),
            },
            exc_info=True,
        )
        return {
            "status": "error",
            "error": str(exc),
            "project_id": project_id,
            "metric_date": metric_date_str,
        }
    finally:
        db.close()
