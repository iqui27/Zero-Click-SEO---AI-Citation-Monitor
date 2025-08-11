from __future__ import annotations


from typing import Any, Optional
import math

# --- Default pricing for our engines/models (USD per 1k tokens/calls) ---
# Sources (last checked 2025-08-11):
# OpenAI GPT-5 / GPT-4.1 pricing: https://openai.com/api/pricing/
# Gemini 2.5 pricing: https://ai.google.dev/gemini-api/docs/pricing
# Perplexity Sonar pricing: https://docs.perplexity.ai/getting-started/pricing
# SerpAPI on-demand & reserved pricing: https://serpapi.com/enterprise and
#   https://serpapi.com/blog/breakdown-of-serpapis-subscriptions/

from typing import Dict, Tuple

# Mapping key: (engine_name, model)
# Values follow the structure expected by `compute_cost_usd` under key "pricing".
DEFAULT_PRICING: Dict[Tuple[str, str], dict] = {
    # OpenAI — per 1M: GPT-5 Input $1.25 / Output $10.00  → per 1k: 0.00125 / 0.01
    # Web search tool call (per 1k calls): $10 (search content tokens billed at model rate)
    ("openai", "gpt-5"): {
        "pricing": {
            "input_per_1k_usd": 0.00125,
            "output_per_1k_usd": 0.01,
            # Not used by compute_cost_usd (informational for callers that count tool calls):
            "web_search_per_1k_calls_usd": 10.0,
        }
    },
    # OpenAI — GPT-4.1 per 1M: Input $2.00 / Output $8.00  → per 1k: 0.002 / 0.008
    # Web search tool call (per 1k calls): $25 (search content tokens included for 4.1)
    ("openai", "gpt-4.1"): {
        "pricing": {
            "input_per_1k_usd": 0.002,
            "output_per_1k_usd": 0.008,
            "web_search_per_1k_calls_usd": 25.0,
        }
    },
    # Google Gemini 2.5 Pro — per 1M: Input $1.25 / Output $10.00 (≤200k prompt) → per 1k: 0.00125 / 0.01
    # NOTE: For prompts >200k, prices are higher (Input $2.50 / Output $15.00).
    ("gemini", "gemini-2.5-pro"): {
        "pricing": {
            "input_per_1k_usd": 0.00125,
            "output_per_1k_usd": 0.01,
        }
    },
    # Google Gemini 2.5 Flash — per 1M: Input $0.30 / Output $2.50 → per 1k: 0.0003 / 0.0025
    ("gemini", "gemini-2.5-flash"): {
        "pricing": {
            "input_per_1k_usd": 0.0003,
            "output_per_1k_usd": 0.0025,
        }
    },
    # Perplexity Sonar Pro — per 1M: Input $3 / Output $15 → per 1k: 0.003 / 0.015
    # (Perplexity also charges a variable request fee based on search context size — not modeled here)
    ("perplexity", "sonar-pro"): {
        "pricing": {
            "input_per_1k_usd": 0.003,
            "output_per_1k_usd": 0.015,
        }
    },
    # Google SERP (SerpAPI) — per-call pricing (not token based)
    # On-demand: $7.50 / 1k searches → 0.0075 per call (default)
    # Reserved:  $2.75 / 1k searches → 0.00275 per call (set manually if you use reserved)
    ("google_serp", "serpapi"): {
        "pricing": {
            "per_call_usd": 0.0075,
            # "per_call_usd": 0.00275,  # use this if you’re on reserved searches
        }
    },
}


def get_default_pricing(engine_name: str, model: str) -> Optional[dict]:
    """Return a pricing dict for (engine_name, model) if known.

    The structure matches `{"pricing": {...}}` so it can be merged with
    an Engine.config_json. Names are case-insensitive.
    """
    key = (str(engine_name or "").lower(), str(model or "").lower())
    return DEFAULT_PRICING.get(key)


def _extract_tokens(usage: dict | None) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Extrai tokens considerando descontos de cache quando disponível.

    - input_tokens_details.cached_tokens: tokens de prompt cacheados (com desconto).
      Para efeitos de custo, consideramos os tokens faturáveis como
      input_billable = max(0, input_tokens - cached_tokens).
    """
    if not usage:
        return None, None, None
    # brutos
    ti_raw = usage.get("prompt_tokens") or usage.get("input_tokens") or usage.get("input")
    to = usage.get("completion_tokens") or usage.get("output_tokens") or usage.get("output")
    # cache (quando houver)
    cached = None
    try:
        details = usage.get("input_tokens_details") or {}
        cached = details.get("cached_tokens")
    except Exception:
        cached = None
    # faturável (se soubermos o cache)
    if ti_raw is not None:
        try:
            ti_billable = int(ti_raw) - int(cached or 0)
            ti = max(0, ti_billable)
        except Exception:
            ti = int(ti_raw)
    else:
        ti = None
    tt = usage.get("total_tokens")
    if tt is None and (ti is not None or to is not None):
        tt = (ti or 0) + (int(to) if to is not None else 0)
    return (
        int(ti) if ti is not None else None,
        int(to) if to is not None else None,
        int(tt) if tt is not None else None,
    )


def compute_cost_usd(engine_config: dict | None, usage: dict | None) -> Optional[float]:
    """
    Calcula custo estimado em USD com base no pricing configurado no Engine.config_json.
    Estrutura esperada em engine_config:
      {
        "pricing": {
           "input_per_1k_usd": 0.003,
           "output_per_1k_usd": 0.006,
           "total_per_1k_usd": 0.005,  # opcional, caso queira preço único
           "per_call_usd": 0.001       # opcional
        }
      }
    Caso não haja pricing configurado ou usage, retorna None.
    """
    pricing = (engine_config or {}).get("pricing") or {}
    if not pricing:
        return None
    ti, to, tt = _extract_tokens(usage)
    per_call = float(pricing.get("per_call_usd") or 0.0)
    total = per_call
    # Preço total baseado em tokens (se informado)
    if tt is not None and pricing.get("total_per_1k_usd") is not None:
        total += (float(tt) / 1000.0) * float(pricing.get("total_per_1k_usd"))
        return round(total, 6)
    # Preço separado input/output
    if ti is not None and pricing.get("input_per_1k_usd") is not None:
        total += (float(ti) / 1000.0) * float(pricing.get("input_per_1k_usd"))
    if to is not None and pricing.get("output_per_1k_usd") is not None:
        total += (float(to) / 1000.0) * float(pricing.get("output_per_1k_usd"))
    return round(total, 6) if total > 0 else None


def estimate_usage_from_text(text: str | None) -> dict | None:
    """
    Estima contagem de tokens a partir do tamanho do texto quando o provider não retorna usage.
    Heurística simples: ~4 caracteres por token. Considera apenas saída (completion/output).
    """
    if not text:
        return None
    # Remover espaços extras para uma estimativa um pouco mais estável
    compact = " ".join((text or "").split())
    approx_tokens = max(1, math.ceil(len(compact) / 4))
    return {
        "input_tokens": 0,
        "output_tokens": approx_tokens,
        "total_tokens": approx_tokens,
    }

