
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
        # Prefer new Google GenAI SDK client (ai.google.dev). API key can come from arg or env.
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.default_model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        # Note: we will (re)build a client in fetch() if a per-run key is provided in config
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
        # Allow per-run key via config.api_key; fallback to adapter/env key
        cfg = input.get("config") or {}
        cfg_api_key = cfg.get("api_key") or cfg.get("GOOGLE_API_KEY") or cfg.get("GEMINI_API_KEY")
        eff_key = cfg_api_key or self.api_key
        if not eff_key:
            return {"raw_url": None, "raw": {"error": "missing_api_key", "request": input}}
        # Build a client with the effective key (do not mutate self.client permanently)
        client = genai.Client(api_key=eff_key)

        model_name = self._resolve_model(cfg)
        base_prompt = input["query"]

        # Strategies order can be influenced by config.force_search
        use_search: bool = cfg.get("use_search", True)
        force_search: bool = bool(cfg.get("force_search"))
        # Strengthen instruction to encourage tool usage and explicit citations
        if use_search:
            sys_hint = (
                "Você é um analista objetivo de busca na Web. Use a ferramenta Google Search para buscar informações em tempo real "
                "e inclua de 2 a 5 fontes no final, usando URLs completas começando com http. Evite citar sem link."
            )
            prompt = f"{sys_hint}\n\n{base_prompt}"
        else:
            prompt = base_prompt

        def _has_grounding(data: Dict[str, Any]) -> bool:
            try:
                cand0 = (data.get("candidates") or [{}])[0]
                gm = cand0.get("groundingMetadata", {}) or cand0.get("grounding_metadata", {})
                chunks = gm.get("groundingChunks", []) or gm.get("grounding_chunks", [])
                if chunks:
                    return True
                cite = cand0.get("citationMetadata", {}) or cand0.get("citation_metadata", {})
                srcs = cite.get("citationSources", []) or cite.get("citations", [])
                if srcs:
                    return True
            except Exception:
                pass
            return False

        def _config_for_strategy(strategy: str) -> types.GenerateContentConfig:
            if strategy == "google_search":
                return self._make_config_with_search(cfg, model_name)
            if strategy == "google_search_retrieval":
                # Build retrieval tool explicitly (no generation_config to avoid extra_forbidden)
                try:
                    dyn_cfg = (cfg or {}).get("dynamic_retrieval") or {}
                    # If force_search, require retrieval
                    if bool(cfg.get("force_search")):
                        mode_name = "MODE_REQUIRED"
                    else:
                        mode_name = str(dyn_cfg.get("mode") or "MODE_DYNAMIC")
                    mode = getattr(types.DynamicRetrievalConfigMode, mode_name, types.DynamicRetrievalConfigMode.MODE_DYNAMIC)
                    thr = dyn_cfg.get("dynamic_threshold")
                    if thr is not None:
                        drc = types.DynamicRetrievalConfig(mode=mode, dynamic_threshold=float(thr))
                    else:
                        drc = types.DynamicRetrievalConfig(mode=mode)
                    retrieval = types.GoogleSearchRetrieval(dynamic_retrieval_config=drc) if drc else types.GoogleSearchRetrieval()
                    tool = types.Tool(google_search_retrieval=retrieval)
                    return types.GenerateContentConfig(tools=[tool])
                except Exception:
                    # Fallback to empty config
                    return types.GenerateContentConfig()
            # none
            return types.GenerateContentConfig()

        # Build strategy order
        if not use_search:
            strategies = ["none"]
        else:
            strategies = ["google_search_retrieval", "google_search", "none"] if force_search else ["google_search", "google_search_retrieval", "none"]

        # Try strategies; if web search yields no grounding, attempt the alternate tool before returning
        errors: List[str] = []
        last_success: Dict[str, Any] | None = None
        tried: set[str] = set()
        for strategy in strategies:
            try:
                config = _config_for_strategy(strategy)

                def _gen_content(params: Dict[str, Any]):
                    return client.models.generate_content(**params)
                resp = await asyncio.to_thread(
                    _gen_content,
                    {
                        "model": model_name,
                        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                        "config": config,
                    },
                )
                # Try to extract a full structured dict (candidates + grounding)
                data: Dict[str, Any] = {}
                try:
                    if hasattr(resp, "model_dump"):
                        data = resp.model_dump()  # type: ignore[attr-defined]
                    elif hasattr(resp, "to_dict"):
                        data = resp.to_dict()  # type: ignore[attr-defined]
                    elif hasattr(resp, "dict"):
                        data = resp.dict()  # type: ignore[attr-defined]
                    else:
                        import json
                        to_json = getattr(resp, "model_dump_json", None) or getattr(resp, "to_json", None)
                        if callable(to_json):
                            data = json.loads(to_json())
                except Exception:
                    data = {}
                if not isinstance(data, dict) or not data:
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
                            return client.models.generate_content(**params)
                        resp2 = await asyncio.to_thread(
                            _gen_content2,
                            {
                                "model": model_name,
                                "contents": [{"role": "user", "parts": [{"text": "Forneça a resposta final agora em texto corrido com 3–5 fontes (URLs completas http) no final."}]}],
                                "config": config,
                            },
                        )
                        # Best-effort to dict
                        try:
                            if hasattr(resp2, "model_dump"):
                                d2 = resp2.model_dump()  # type: ignore[attr-defined]
                            elif hasattr(resp2, "to_dict"):
                                d2 = resp2.to_dict()  # type: ignore[attr-defined]
                            elif hasattr(resp2, "dict"):
                                d2 = resp2.dict()  # type: ignore[attr-defined]
                            else:
                                import json
                                to_json2 = getattr(resp2, "model_dump_json", None) or getattr(resp2, "to_json", None)
                                d2 = json.loads(to_json2()) if callable(to_json2) else {"text": getattr(resp2, "text", "")}
                        except Exception:
                            d2 = {"text": getattr(resp2, "text", "")}
                        # anexar ao payload para o parse ter alternativas
                        data["fallback"] = d2
                    except Exception:
                        pass
                # If search was enabled but no grounding detected, attempt alternate strategy if available
                if use_search and strategy != "none" and not _has_grounding(data):
                    last_success = data
                    tried.add(strategy)
                    # If we haven't tried the other search tool yet, continue loop to try it
                    if ("google_search_retrieval" in strategies and "google_search_retrieval" not in tried) or ("google_search" in strategies and "google_search" not in tried):
                        continue
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
                recoverable_markers = (
                    "Unknown field",
                    "INVALID_ARGUMENT",
                    "not recognized",
                    "unrecognized",
                    "extra inputs are not permitted",
                    "extra_forbidden",
                )
                if any(t in msg for t in recoverable_markers) or any(
                    t in lower for t in transient_markers
                ):
                    continue
                return {"raw_url": None, "raw": {"error": "fetch_failed", "message": msg, "request": input}}
        # If we had a successful non-grounded response, return it; otherwise surface errors
        if last_success is not None:
            return {"raw_url": None, "raw": last_success}
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
