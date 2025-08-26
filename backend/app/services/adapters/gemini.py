
from __future__ import annotations

import os
import re
from typing import List, Optional, Dict, Any
import asyncio

from google import genai
from google.genai import types

from app.services.adapters.base import EngineAdapter, FetchInput, RawEvidence, ParsedAnswer, Citation
from app.services.normalization import resolve_known_redirects


SUPPORTED_MODELS = {
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
}

URL_RE = re.compile(r"https?://[\w\-\.\?\,\'\/\+&%\$#_=:\(\)\*]+", re.IGNORECASE)


class GeminiAdapter:
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        # Prefer new Google GenAI SDK client (ai.google.dev). The API key can be passed or read from env.
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.default_model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.client: Optional[genai.Client] = genai.Client(api_key=self.api_key) if self.api_key else None

    def _resolve_model(self, cfg: dict | None) -> str:
        cfg_model = (cfg or {}).get("model")
        model = (cfg_model or self.default_model).strip()
        return model

    def _make_config_with_search(self, cfg: dict | None, model_name: str) -> types.GenerateContentConfig:
        """Build a GenerateContentConfig enabling Google Search grounding per current docs.

        Preferred tool: `google_search` (Gemini 2.x / 2.5 and current 1.5).
        Fallback for legacy 1.5 flows: `google_search_retrieval` with DynamicRetrievalConfig.
        """
        # Sempre habilitar web search por padrão. Só desliga se for explicitamente False.
        use_search: bool = (cfg or {}).get("use_search", True)
        if use_search is False:
            return types.GenerateContentConfig()

        # Primary (recommended): google_search
        try:
            tool = types.Tool(google_search=types.GoogleSearch())
            return types.GenerateContentConfig(tools=[tool])
        except Exception:
            # Very old SDKs may not recognize google_search; fall back below
            pass

        # Legacy fallback: google_search_retrieval (mainly for older 1.5 variants)
        dyn_cfg = (cfg or {}).get("dynamic_retrieval") or {}
        drc = None
        try:
            mode_name = str(dyn_cfg.get("mode") or "MODE_DYNAMIC")
            mode = getattr(types.DynamicRetrievalConfigMode, mode_name, types.DynamicRetrievalConfigMode.MODE_DYNAMIC)
            thr = dyn_cfg.get("dynamic_threshold")
            if thr is not None:
                drc = types.DynamicRetrievalConfig(mode=mode, dynamic_threshold=float(thr))
            else:
                drc = types.DynamicRetrievalConfig(mode=mode)
        except Exception:
            drc = None
        try:
            retrieval = types.GoogleSearchRetrieval(dynamic_retrieval_config=drc) if drc else types.GoogleSearchRetrieval()
            tool = types.Tool(google_search_retrieval=retrieval)
            return types.GenerateContentConfig(tools=[tool])
        except Exception:
            # No tools usable; return empty config
            return types.GenerateContentConfig()

    async def fetch(self, input: FetchInput) -> RawEvidence:
        if not self.client:
            return {"raw_url": None, "raw": {"error": "missing_api_key", "request": input}}

        model_name = self._resolve_model(input.get("config"))
        prompt = input["query"]
        cfg = input.get("config") or {}

        # Try with google_search (recommended). If SDK rejects the tool, fall back to legacy or no tools.
        errors: List[str] = []
        for strategy in ("google_search", "google_search_retrieval", "none"):
            try:
                if strategy == "google_search":
                    config = self._make_config_with_search(cfg, model_name)
                elif strategy == "google_search_retrieval":
                    # Force legacy tool by bypassing primary path
                    dyn_only = {"use_search": True, "dynamic_retrieval": (cfg.get("dynamic_retrieval") or {"mode": "MODE_DYNAMIC", "dynamic_threshold": 0.7})}
                    config = self._make_config_with_search(dyn_only, model_name)
                else:
                    config = types.GenerateContentConfig()

                def _gen_content(params: Dict[str, Any]):
                    return self.client.models.generate_content(**params)
                resp = await asyncio.to_thread(
                    _gen_content,
                    {
                        "model": model_name,
                        "contents": prompt,
                        "config": config,
                    },
                )
                try:
                    data = resp.to_dict()  # structured dict with candidates + groundingMetadata
                except Exception:
                    data = {"text": getattr(resp, "text", ""), "raw": str(resp)}
                # Se não extrairmos texto de imediato, tentar um minimal fallback pedindo saída textual
                try:
                    cand = (data.get("candidates") or [{}])[0]
                    parts = cand.get("content", {}).get("parts", [])
                    has_text = any((p.get("text") or "").strip() for p in parts)
                except Exception:
                    has_text = bool(data.get("text"))
                if not has_text:
                    try:
                        def _gen_content2(params: Dict[str, Any]):
                            return self.client.models.generate_content(**params)
                        resp2 = await asyncio.to_thread(
                            _gen_content2,
                            {
                                "model": model_name,
                                "contents": "Forneça a resposta final agora em texto corrido com 3–5 fontes (URLs completas http) no final.",
                                "config": config,
                            },
                        )
                        d2 = resp2.to_dict()
                        # anexar ao payload para o parse ter alternativas
                        data["fallback"] = d2
                    except Exception:
                        pass
                return {"raw_url": None, "raw": data}
            except Exception as e:
                msg = str(e)
                errors.append(f"{strategy}: {msg}")
                # Continue for tool/field issues OR transient/server errors (5xx/timeouts)
                lower = msg.lower()
                transient_markers = (
                    "internal server error",
                    "unavailable",
                    "deadline exceeded",
                    "timeout",
                    "temporarily",
                    "bad gateway",
                    "gateway timeout",
                    "503",
                    "502",
                    "500",
                )
                if any(t in msg for t in ("Unknown field", "INVALID_ARGUMENT", "not recognized", "unrecognized")) or any(
                    t in lower for t in transient_markers
                ):
                    continue
                return {"raw_url": None, "raw": {"error": "fetch_failed", "message": msg, "request": input}}

        return {"raw_url": None, "raw": {"error": "no_tool_worked", "message": "; ".join(errors), "request": input}}

    async def parse(self, raw: RawEvidence) -> ParsedAnswer:
        data: Dict[str, Any] = raw.get("raw") or {}

        # --- Extract plain text ---
        text = ""
        try:
            candidates = data.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = "".join(p.get("text") or "" for p in parts)
            # Fallback if present
            if not text and isinstance(data.get("text"), str):
                text = data.get("text") or ""
            # Fallback 2: tentar payload de fallback
            if not text and isinstance(data.get("fallback"), dict):
                fc = data.get("fallback") or {}
                c2 = (fc.get("candidates") or [{}])[0]
                p2 = c2.get("content", {}).get("parts", [])
                if p2:
                    text = "".join(x.get("text") or "" for x in p2)
        except Exception:
            text = data.get("text") or ""

        # --- Extract links from groundingMetadata (preferred) and citationMetadata (fallback) ---
        links: List[Dict[str, str]] = []
        try:
            cand0 = (data.get("candidates") or [{}])[0]
            gm = cand0.get("groundingMetadata", {}) or cand0.get("grounding_metadata", {})
            # Grounding chunks
            for ch in gm.get("groundingChunks", []) + gm.get("grounding_chunks", []):
                web = ch.get("web") or {}
                uri = web.get("uri") or web.get("url")
                if uri:
                    uri = resolve_known_redirects(uri)
                    links.append({"url": uri, "title": web.get("title")})
            # Legacy: citationMetadata
            cite = cand0.get("citationMetadata", {}) or cand0.get("citation_metadata", {})
            for part in cite.get("citationSources", []) + cite.get("citations", []):
                uri = part.get("uri") or part.get("url")
                if uri:
                    uri = resolve_known_redirects(uri)
                    links.append({"url": uri, "title": part.get("title")})
        except Exception:
            pass

        # Fallback: scrape URLs from text
        if text:
            have = {l["url"] for l in links}
            for m in URL_RE.findall(text):
                m2 = resolve_known_redirects(m)
                if m2 not in have:
                    links.append({"url": m2, "title": None})

        # --- Inferir uso de web search e contagem de chamadas ---
        web_used = False
        web_calls = 0
        try:
            cand0 = (data.get("candidates") or [{}])[0]
            gm = cand0.get("groundingMetadata", {}) or cand0.get("grounding_metadata", {})
            chunks = gm.get("groundingChunks", []) or []
            if chunks:
                web_used = True
                for ch in chunks:
                    web = ch.get("web") or {}
                    if web.get("uri") or web.get("url"):
                        web_calls += 1
            cite = cand0.get("citationMetadata", {}) or cand0.get("citation_metadata", {})
            srcs = cite.get("citationSources", []) or cite.get("citations", [])
            if srcs:
                web_used = True
        except Exception:
            pass

        # --- Normalize usage tokens if present ---
        norm_usage: Dict[str, Any] = {}
        try:
            cand0 = (data.get("candidates") or [{}])[0]
            um = cand0.get("usageMetadata") or cand0.get("usage_metadata") or {}
            if um:
                norm_usage = {
                    "input_tokens": um.get("promptTokenCount") or um.get("inputTokenCount") or um.get("prompt_tokens"),
                    "output_tokens": um.get("candidatesTokenCount") or um.get("outputTokenCount") or um.get("completion_tokens"),
                    "total_tokens": um.get("totalTokenCount") or um.get("total_tokens"),
                }
        except Exception:
            pass

        return {
            "text": text,
            "blocks": [],
            "links": links,
            "meta": {
                "engine": self.name,
                "model": data.get("model"),
                "raw_usage": norm_usage,
                # Sinalização para UI
                "web_search_used": bool(web_used),
                "web_search_calls": int(web_calls),
            },
        }

    async def extract_citations(self, parsed: ParsedAnswer) -> List[Citation]:
        citations: List[Citation] = []
        seen = set()
        for link in parsed.get("links", []):
            url = link.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            citations.append(
                {
                    "domain": url,
                    "url": url,
                    "anchor": link.get("title") or None,
                    "position": None,
                    "type": "link",
                }
            )
        return citations

    async def normalize(self, parsed: ParsedAnswer) -> ParsedAnswer:
        return parsed
