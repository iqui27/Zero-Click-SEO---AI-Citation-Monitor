from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, MutableMapping, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.models import Engine

logger = logging.getLogger(__name__)

_META_PREFIX = "_"

ConfigDict = Dict[str, Any]
EngineCache = MutableMapping[Tuple[str, str, str, str, str], Tuple[Engine, Optional[ConfigDict]]]


def _coerce_to_dict(config: Any) -> ConfigDict:
    if not config:
        return {}
    if isinstance(config, dict):
        return dict(config)
    if isinstance(config, str):
        try:
            parsed = json.loads(config)
            if isinstance(parsed, dict):
                return dict(parsed)
        except Exception:
            logger.debug("Failed to parse engine config JSON string", exc_info=True)
    return {}


def _strip_meta(config: ConfigDict) -> ConfigDict:
    return {k: v for k, v in config.items() if not k.startswith(_META_PREFIX)}


def _is_positive_int(value: Any) -> bool:
    try:
        ivalue = int(value)
        return ivalue > 0
    except Exception:
        return False


def normalize_config(name: Optional[str], config: Any) -> ConfigDict:
    data = _strip_meta(_coerce_to_dict(config))
    key = (name or "").strip().lower()

    if key in ("openai", "gpt"):
        if data.get("web_search") is None:
            data["web_search"] = True
        if data.get("use_search") is None and "web_search" in data:
            try:
                data["use_search"] = bool(data.get("web_search"))
            except Exception:
                data["use_search"] = True
        if not data.get("search_context_size"):
            data["search_context_size"] = "low"
        if data.get("reasoning_effort") is None:
            data["reasoning_effort"] = "low"
        if data.get("web_search") and not data.get("web_search_tool_choice"):
            data["web_search_tool_choice"] = "auto"
        if not _is_positive_int(data.get("max_output_tokens")):
            data["max_output_tokens"] = 8192
        # Ajuste para GPT-5 / O5: maior limite de tokens e reasoning médio por padrão
        model_value = str(data.get("model") or "").strip().lower()
        if model_value.startswith("gpt-5") or model_value.startswith("o5"):
            if not _is_positive_int(data.get("max_output_tokens")) or data.get("max_output_tokens") == 8192:
                data["max_output_tokens"] = 12000
            data.setdefault("reasoning_effort", "medium")
    elif key in ("gemini", "google_gemini"):
        if data.get("use_search") is None:
            data["use_search"] = True
        if data.get("force_search") is None:
            data["force_search"] = True
        if not _is_positive_int(data.get("max_output_tokens")):
            data["max_output_tokens"] = 9000
        # Configurar parâmetros de grounding dinâmico quando não especificado
        if "dynamic_retrieval" not in data:
            data["dynamic_retrieval"] = {"mode": "MODE_DYNAMIC", "dynamic_threshold": 0.7}
    elif key in ("perplexity", "pplx"):
        if not data.get("model"):
            data["model"] = "sonar-pro"

    # Drop explicit None values for stability
    data = {k: v for k, v in data.items() if v is not None}
    return data


def compute_config_hash(config: ConfigDict) -> str:
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _merge_canonical_with_meta(canonical: ConfigDict, source_config: Any, *, mark_main: bool = False) -> ConfigDict:
    stored = dict(canonical)
    source_dict = _coerce_to_dict(source_config)
    for key, value in source_dict.items():
        if key.startswith(_META_PREFIX):
            stored[key] = value
    if mark_main:
        stored.setdefault("_main", True)
    return stored


def diff_configs(base: ConfigDict, desired: ConfigDict) -> Optional[ConfigDict]:
    diff: ConfigDict = {}
    for key, value in desired.items():
        if base.get(key) != value:
            diff[key] = value
    return diff or None


def apply_overrides(base: ConfigDict, overrides: Optional[ConfigDict]) -> ConfigDict:
    if not overrides:
        return dict(base)
    result = dict(base)
    for key, value in overrides.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = value
    return result


def get_engine_base_config(engine: Engine) -> ConfigDict:
    return normalize_config(engine.name, engine.config_json)


def ensure_engine(
    db: Session,
    *,
    project_id: str,
    name: Optional[str],
    region: Optional[str],
    device: Optional[str],
    requested_config: Any,
    cache: Optional[EngineCache] = None,
) -> Tuple[Engine, Optional[ConfigDict]]:
    """Return a canonical Engine for the supplied configuration.

    Creates or upgrades an Engine row when necessary and returns
    any per-run overrides required to match the requested config.
    """
    name_clean = (name or "").strip()
    region_clean = (region or "").strip() or None
    device_clean = (device or "").strip() or None

    requested_canonical = normalize_config(name_clean, requested_config)
    config_hash = compute_config_hash(requested_canonical)

    cache_key = (
        project_id,
        name_clean,
        region_clean or "",
        device_clean or "",
        config_hash,
    )
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    stmt = select(Engine).where(
        and_(
            Engine.project_id == project_id,
            Engine.name == name_clean,
            Engine.region.is_(region_clean) if region_clean is None else Engine.region == region_clean,
            Engine.device.is_(device_clean) if device_clean is None else Engine.device == device_clean,
            Engine.config_hash == config_hash,
        )
    )
    engine = db.execute(stmt).scalars().first()

    if engine is None:
        fallback_stmt = select(Engine).where(
            and_(
                Engine.project_id == project_id,
                Engine.name == name_clean,
                Engine.region.is_(region_clean) if region_clean is None else Engine.region == region_clean,
                Engine.device.is_(device_clean) if device_clean is None else Engine.device == device_clean,
            )
        )
        for candidate in db.execute(fallback_stmt).scalars():
            candidate_canonical = normalize_config(name_clean, candidate.config_json)
            candidate_hash = candidate.config_hash or compute_config_hash(candidate_canonical)
            if candidate_hash == config_hash:
                candidate.config_json = _merge_canonical_with_meta(
                    requested_canonical,
                    candidate.config_json,
                    mark_main="_main" in _coerce_to_dict(candidate.config_json) or True,
                )
                candidate.config_hash = config_hash
                db.commit()
                db.refresh(candidate)
                engine = candidate
                break

        if engine is None:
            stored_config = _merge_canonical_with_meta(requested_canonical, None, mark_main=True)
            engine = Engine(
                project_id=project_id,
                name=name_clean,
                region=region_clean,
                device=device_clean,
                config_json=stored_config,
                config_hash=config_hash,
            )
            db.add(engine)
            db.commit()
            db.refresh(engine)
    else:
        canonical_existing = normalize_config(name_clean, engine.config_json)
        if engine.config_hash != config_hash or canonical_existing != requested_canonical:
            engine.config_json = _merge_canonical_with_meta(
                requested_canonical,
                engine.config_json,
                mark_main="_main" in _coerce_to_dict(engine.config_json),
            )
            engine.config_hash = config_hash
            db.commit()
            db.refresh(engine)

    effective_engine = normalize_config(name_clean, engine.config_json)
    overrides = diff_configs(effective_engine, requested_canonical)

    result = (engine, overrides)
    if cache is not None:
        cache[cache_key] = result
    return result
