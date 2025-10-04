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
from app.services.normalization import normalize_domain
from app.services.engine_runner import run_engine
from app.services.costs import compute_cost_usd, estimate_usage_from_text, get_default_pricing
from app.services.gemini_semantic import GeminiSemanticService

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


def _persist_serp_feature_details(db: Session, run_id: str, serp_metrics: dict[str, Any]) -> None:
    if not serp_metrics:
        return

    features = serp_metrics.get("serp_features") or {}
    feature = db.query(SerpFeature).filter(SerpFeature.run_id == run_id).one_or_none()
    if not feature:
        feature = SerpFeature(run_id=run_id)
        db.add(feature)

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

        # Construir config EFETIVO por engine (evita nulls e reflete defaults reais)
        cfg_raw = dict(engine.config_json or {})
        name_lower = (engine.name or "").lower()
        cfg_eff = dict(cfg_raw)
        try:
            if name_lower in ("openai", "gpt"):
                # defaults para OpenAI Responses/Chat (aplicar também quando vier None ou vazio)
                if cfg_eff.get("web_search") is None:
                    cfg_eff["web_search"] = True
                if cfg_eff.get("use_search") is None:
                    # espelhar web_search para ter um campo comum nas UIs
                    try:
                        cfg_eff["use_search"] = bool(cfg_eff.get("web_search"))
                    except Exception:
                        cfg_eff["use_search"] = True
                if not cfg_eff.get("search_context_size"):
                    cfg_eff["search_context_size"] = "low"
                if cfg_eff.get("reasoning_effort") is None:
                    cfg_eff["reasoning_effort"] = "low"
                try:
                    mot = cfg_eff.get("max_output_tokens")
                    mot_i = int(mot) if mot is not None else None
                except Exception:
                    mot_i = None
                if mot_i is None or mot_i <= 0:
                    cfg_eff["max_output_tokens"] = 8192
            elif name_lower in ("gemini", "google_gemini"):
                if cfg_eff.get("use_search") is None:
                    cfg_eff["use_search"] = True
                # Default: enable force_search unless explicitly set by user/config
                if cfg_eff.get("force_search") is None:
                    cfg_eff["force_search"] = True
                try:
                    mot = cfg_eff.get("max_output_tokens")
                    mot_i = int(mot) if mot is not None else None
                except Exception:
                    mot_i = None
                if mot_i is None or mot_i <= 0:
                    cfg_eff["max_output_tokens"] = 9000
            elif name_lower in ("perplexity", "pplx"):
                # Defaults: model seguro e citações
                if not cfg_eff.get("model"):
                    cfg_eff["model"] = "sonar-pro"
        except Exception:
            pass

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
            cfg = dict(cfg_eff)
            cfg_used = {
                "model": cfg.get("model"),
                # valores efetivos (sem null) após merge de defaults
                "web_search": cfg.get("web_search"),
                "use_search": cfg.get("use_search"),
                "force_search": cfg.get("force_search"),
                "search_context_size": cfg.get("search_context_size"),
                "reasoning_effort": cfg.get("reasoning_effort"),
                "max_output_tokens": cfg.get("max_output_tokens"),
                "web_search_force": cfg.get("web_search_force"),
                "user_location": cfg.get("user_location"),
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
            
            try:
                model_for_log = (engine.config_json or {}).get("model")
            except Exception:
                model_for_log = None
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
                ev = Evidence(
                    run_id=run.id,
                    raw_url=raw.get("raw_url"),
                    parsed_json={"raw": raw_safe, "parsed": parsed_safe},
                    screenshot_url=None,
                    content_hash=None,
                )
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

        # Classificação Zero-Click da resposta
        try:
            from app.services.classification_integration import classify_run_async
            response_text = (last_parsed or {}).get("text") if last_parsed else None
            if response_text:
                classification_result = classify_run_async(run.id, response_text)
                if classification_result:
                    _log(db, run.id, "classify", "ok", f"Classified as {classification_result.response_type}/{classification_result.brand_positioning}")
                else:
                    _log(db, run.id, "classify", "fail", "Classification failed")
            else:
                _log(db, run.id, "classify", "skip", "No response text found")
        except Exception as e:
            _log(db, run.id, "classify", "fail", f"Classification error: {str(e)}")

        # === CÁLCULO DE MÉTRICAS IM-SEO / IM-SEOIA ===
        print(f"[DEBUG] Iniciando cálculo de métricas IM para run {run.id}")
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
                if evidence and evidence.parsed_json:
                    serp_data = evidence.parsed_json.get("raw", {})
                
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

            _persist_serp_feature_details(db, run.id, im_metrics.get("serp_metrics") or {})

            db.commit()
            print(f"[DEBUG] Métricas salvas no banco com sucesso!")
            
            _log(db, run.id, "im_metrics", "ok", f"IM-SEO: {run.im_seo_score}, IM-SEOIA: {run.im_seoia_score}")

            if settings.semantic_insights_enabled:
                try:
                    process_semantic_insights.delay(run.id)
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
            from app.models.models import PromptVersion
            
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

        _log(db, run.id, "semantic_insights", "started", "Gemini semantic analysis")

        service = GeminiSemanticService()
        payload = service.analyze(
            question=question_text or "",
            response_text=response_text,
            citations=citations_payload,
            project_name=project_name,
        )

        insight = db.get(RunSemanticInsight, run_id)
        if insight:
            insight.payload = payload
            insight.updated_at = datetime.utcnow()
        else:
            insight = RunSemanticInsight(run_id=run_id, payload=payload)
            db.add(insight)

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

        db.commit()
        _log(db, run.id, "semantic_insights", "ok", f"entities={entities_count}, perception={primary_category}")

    except Exception as exc:
        db.rollback()
        print(f"[SEMANTIC] Erro ao gerar insights para run {run_id}: {exc}")
        _log(db, run_id, "semantic_insights", "fail", str(exc))
    finally:
        db.close()
