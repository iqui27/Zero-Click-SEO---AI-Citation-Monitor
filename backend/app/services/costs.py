from __future__ import annotations

from typing import Any, Optional


def _extract_tokens(usage: dict | None) -> tuple[Optional[int], Optional[int], Optional[int]]:
    if not usage:
        return None, None, None
    ti = usage.get("prompt_tokens") or usage.get("input_tokens") or usage.get("input")
    to = usage.get("completion_tokens") or usage.get("output_tokens") or usage.get("output")
    tt = usage.get("total_tokens") or (None if ti is None and to is None else int(ti or 0) + int(to or 0))
    return (int(ti) if ti is not None else None, int(to) if to is not None else None, int(tt) if tt is not None else None)


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


