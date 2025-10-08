from __future__ import annotations

import os
import re
from typing import List, Dict, Any

import httpx

from app.services.adapters.base import EngineAdapter, FetchInput, RawEvidence, ParsedAnswer, Citation


class PerplexityAdapter:
    name = "perplexity"

    def __init__(self, api_key: str | None = None, timeout_seconds: float = 30.0) -> None:
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://api.perplexity.ai"

    async def fetch(self, input: FetchInput) -> RawEvidence:
        cfg = (input.get("config", {}) or {})
        # Allow per-run api_key override
        eff_key = cfg.get("api_key") or self.api_key or os.getenv("PERPLEXITY_API_KEY")
        if not eff_key:
            return {"raw_url": None, "raw": {"error": "missing_api_key", "request": input}}

        headers = {
            "Authorization": f"Bearer {eff_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        model = cfg.get("model", "sonar-pro")
        user_query = input["query"]
        system = "Responda concisamente e liste as fontes com URLs completas ao final."
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_query},
        ]
        payload: Dict[str, Any] = {"model": model, "messages": messages}
        # Optional tuning
        try:
            if cfg.get("temperature") is not None:
                payload["temperature"] = float(cfg.get("temperature"))
        except Exception:
            pass
        try:
            if cfg.get("top_p") is not None:
                payload["top_p"] = float(cfg.get("top_p"))
        except Exception:
            pass
        try:
            if cfg.get("max_tokens") is not None:
                payload["max_tokens"] = int(cfg.get("max_tokens"))
        except Exception:
            pass
        # Perplexity-specific search/citation parameters
        payload.setdefault("search_mode", cfg.get("search_mode") or "web")  # "web" | "academic"
        payload.setdefault("return_citations", True)
        if cfg.get("search_recency_filter") is not None:
            payload["search_recency_filter"] = cfg.get("search_recency_filter")
        if cfg.get("search_domain_filter") is not None:
            payload["search_domain_filter"] = cfg.get("search_domain_filter")
        if cfg.get("return_images") is not None:
            payload["return_images"] = bool(cfg.get("return_images"))
        if cfg.get("return_related_questions") is not None:
            payload["return_related_questions"] = bool(cfg.get("return_related_questions"))

        url = f"{self.base_url}/chat/completions"

        def _is_transient_status(code: int) -> bool:
            return code >= 500 or code in (408, 429)

        attempts = 0
        max_attempts = 3
        last_err: Dict[str, Any] | None = None
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            while attempts < max_attempts:
                attempts += 1
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                except httpx.TimeoutException as e:
                    last_err = {"error": "timeout", "message": str(e)}
                    if attempts < max_attempts:
                        try:
                            # simple backoff: 0.4s, 0.8s
                            import asyncio as _a
                            await _a.sleep(0.4 * attempts)
                        except Exception:
                            pass
                        continue
                    break
                except httpx.HTTPError as e:
                    last_err = {"error": "http_error", "message": str(e)}
                    break

                # Non-2xx: return structured error; retry on transient
                if resp.status_code < 200 or resp.status_code >= 300:
                    body_preview = None
                    try:
                        txt = resp.text
                        body_preview = txt[:500] if txt else None
                    except Exception:
                        body_preview = None
                    err_obj = {
                        "error": "bad_status",
                        "status": resp.status_code,
                        "body": body_preview,
                    }
                    last_err = err_obj
                    if _is_transient_status(resp.status_code) and attempts < max_attempts:
                        try:
                            import asyncio as _a
                            await _a.sleep(0.4 * attempts)
                        except Exception:
                            pass
                        continue
                    break

                # Try JSON parse safely
                try:
                    data = resp.json()
                except Exception as e:
                    # Not JSON (HTML/empty). Return structured error with preview
                    body_preview = None
                    try:
                        txt = resp.text
                        body_preview = txt[:500] if txt else None
                    except Exception:
                        body_preview = None
                    last_err = {"error": "invalid_json", "message": str(e), "status": resp.status_code, "body": body_preview}
                    # Retry only if transient status
                    if _is_transient_status(resp.status_code) and attempts < max_attempts:
                        try:
                            import asyncio as _a
                            await _a.sleep(0.4 * attempts)
                        except Exception:
                            pass
                        continue
                    break

                # Fallback: alguns modelos podem não retornar 'choices' ou conteúdo textual; tentar 'sonar-pro'
                try:
                    choices = data.get("choices") or []
                    content_empty = True
                    if choices:
                        msg = (choices[0] or {}).get("message") or {}
                        c = msg.get("content")
                        content_empty = (not c) or (isinstance(c, str) and not c.strip()) or (isinstance(c, list) and not any(bool(x) for x in c))
                    if (not choices or content_empty) and str(model).lower() != "sonar-pro":
                        payload2 = dict(payload)
                        payload2["model"] = "sonar-pro"
                        resp2 = await client.post(url, headers=headers, json=payload2)
                        try:
                            data2 = resp2.json()
                        except Exception as e2:
                            data2 = {"error": "invalid_json", "message": str(e2), "status": resp2.status_code, "body": (resp2.text[:500] if hasattr(resp2, 'text') else None)}
                        return {"raw_url": None, "raw": {"primary": data, "fallback": data2, "model": payload.get("model"), "model_fallback": "sonar-pro"}}
                except Exception:
                    pass
                return {"raw_url": None, "raw": data}

        # If we exit loop with error
        return {"raw_url": url, "raw": last_err or {"error": "unknown"}}

    async def parse(self, raw: RawEvidence) -> ParsedAnswer:
        data: Dict[str, Any] = raw.get("raw") or {}
        # Unwrap possible fallback wrapper
        if ("primary" in data) or ("fallback" in data):
            try:
                fb = data.get("fallback") or {}
                pr = data.get("primary") or {}
                use = fb if (fb.get("choices") or []) else pr
                if isinstance(use, dict) and use:
                    data = use
            except Exception:
                pass
        choices = data.get("choices") or []
        content = ""
        if choices:
            try:
                msg = choices[0].get("message") or {}
                c = msg.get("content")
                if isinstance(c, str):
                    content = c
                elif isinstance(c, list):
                    parts: list[str] = []
                    for seg in c:
                        if isinstance(seg, str):
                            if seg.strip():
                                parts.append(seg)
                        elif isinstance(seg, dict):
                            # Common shapes: {type: 'text', text: '...'}
                            t = seg.get("text") or seg.get("content") or ""
                            if isinstance(t, str) and t.strip():
                                parts.append(t)
                    content = "\n".join(parts).strip()
            except Exception:
                pass
        if not content:
            # Fallbacks sometimes seen in API variants
            content = data.get("answer") or data.get("output_text") or ""

        # Citations and search results
        links: list[dict] = []
        for key in ("citations", "source_urls", "sources", "urls"):
            for u in (data.get(key) or []):
                if isinstance(u, str):
                    links.append({"url": u})
        for r in (data.get("search_results") or []):
            u = r.get("url")
            if u:
                links.append({"url": u, "title": r.get("title")})

        # Fallback: extract URLs from text
        if content:
            for m in re.findall(r"https?://[^\s)]+", content):
                if all(x.get("url") != m for x in links):
                    links.append({"url": m})

        return {
            "text": content,
            "blocks": [],
            "links": links,
            "meta": {"engine": self.name, "raw_usage": data.get("usage"), "model": data.get("model")},
        }

    async def extract_citations(self, parsed: ParsedAnswer) -> List[Citation]:
        citations: List[Citation] = []
        position_counter = 0
        for link in parsed.get("links", []):
            url = link.get("url")
            if not url:
                continue
            link_position = link.get("position")
            if isinstance(link_position, (int, float)):
                position_value = str(int(link_position))
            elif isinstance(link_position, str) and link_position.strip().isdigit():
                position_value = link_position.strip()
            else:
                position_counter += 1
                position_value = str(position_counter)
            citations.append(
                {
                    "domain": url,
                    "url": url,
                    "anchor": link.get("title") or None,
                    "position": position_value,
                    "type": "link",
                }
            )
        return citations

    async def normalize(self, parsed: ParsedAnswer) -> ParsedAnswer:
        return parsed
