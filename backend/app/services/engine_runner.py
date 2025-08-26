from __future__ import annotations

import asyncio
from billiard import Process, Queue
import queue as _queue
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


def _proc_entry(name: str, fetch_input: FetchInput, out_q: Queue) -> None:
    """Child process entrypoint. Builds adapter and runs it in its own event loop.

    Sends ("ok", (raw, parsed, citations)) or ("err", message) via out_q.
    """
    try:
        adapter = get_adapter(name)
        res = asyncio.run(_run_adapter(adapter, fetch_input))
        out_q.put(("ok", res))
    except Exception as e:  # pragma: no cover - defensive in child
        try:
            out_q.put(("err", str(e)))
        except Exception:
            pass


def run_engine(name: str, fetch_input: FetchInput, timeout_seconds: float | None = None) -> Tuple[RawEvidence, ParsedAnswer, List[Citation]]:
    """Run the engine adapter.

    When a timeout is provided, execute in a separate subprocess and enforce a hard
    timeout by terminating the child on expiry. This avoids hangs caused by
    non-cancellable blocking SDK calls within threads.
    """
    # Fast path (no external timeout required): run in-process
    if not timeout_seconds or timeout_seconds <= 0:
        adapter = get_adapter(name)
        return asyncio.run(_run_adapter(adapter, fetch_input))

    # Timed path: use subprocess watchdog (billiard under Celery)
    out_q: Queue = Queue(maxsize=1)
    p = Process(target=_proc_entry, args=(name, fetch_input, out_q))
    p.start()
    try:
        try:
            status, payload = out_q.get(timeout=float(timeout_seconds))
        except _queue.Empty:
            raise asyncio.TimeoutError(f"Adapter timed out after {timeout_seconds}s")
        if status == "ok":
            # Ensure child exits
            p.join(timeout=1.0)
            raw, parsed, citations = payload
            return raw, parsed, citations
        else:
            # Child reported an error
            p.join(timeout=1.0)
            raise RuntimeError(str(payload))
    finally:
        if p.is_alive():
            try:
                p.terminate()
            except Exception:
                pass
            try:
                p.join(timeout=2.0)
            except Exception:
                pass
