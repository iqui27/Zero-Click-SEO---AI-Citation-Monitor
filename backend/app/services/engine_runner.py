from __future__ import annotations

import asyncio
from typing import Tuple, List

from app.services.adapters.perplexity import PerplexityAdapter
from app.services.adapters.google_serp import GoogleSerpAdapter
from app.services.adapters.openai_adapter import OpenAIAdapter
from app.services.adapters.gemini import GeminiAdapter
from app.services.adapters.sandbox import SandboxAdapter
from app.services.adapters.base import FetchInput, ParsedAnswer, Citation, RawEvidence


def get_adapter(name: str):
    key = (name or "").strip().lower()
    if key in ("perplexity", "pplx"):
        return PerplexityAdapter()
    if key in ("google_serp", "google-ai", "google"):
        return GoogleSerpAdapter()
    if key in ("openai", "gpt"):
        return OpenAIAdapter()
    if key in ("gemini", "google_gemini"):
        return GeminiAdapter()
    if key in ("sandbox", "demo", "fixture"):
        return SandboxAdapter()
    raise ValueError(f"Engine não suportado: {name}")


async def _run_adapter(adapter, fetch_input: FetchInput) -> Tuple[RawEvidence, ParsedAnswer, List[Citation]]:
    raw = await adapter.fetch(fetch_input)
    parsed = await adapter.parse(raw)
    parsed = await adapter.normalize(parsed)
    citations = await adapter.extract_citations(parsed)
    return raw, parsed, citations


def run_engine(name: str, fetch_input: FetchInput) -> Tuple[RawEvidence, ParsedAnswer, List[Citation]]:
    adapter = get_adapter(name)
    return asyncio.run(_run_adapter(adapter, fetch_input))
