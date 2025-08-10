from __future__ import annotations

import os
import re
from typing import List, Optional

import google.generativeai as genai

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
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.default_model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def _resolve_model(self, cfg: dict | None) -> str:
        cfg_model = (cfg or {}).get("model")
        model = (cfg_model or self.default_model).strip()
        return model

    async def fetch(self, input: FetchInput) -> RawEvidence:
        if not self.api_key:
            return {"raw_url": None, "raw": {"error": "missing_api_key", "request": input}}

        model_name = self._resolve_model(input.get("config"))
        prompt = input["query"]
        cfg = input.get("config") or {}
        use_search: bool = cfg.get("use_search", True)

        # Estratégias de ferramentas em ordem de tentativa
        tool_strategies: list[dict | None] = []
        if use_search:
            # 1) google_search_retrieval (pode não estar disponível em algumas versões)
            tool_strategies.append({"google_search_retrieval": {"dynamic_retrieval_config": {"mode": "MODE_DYNAMIC"}}})
            # 2) google_search (fallback)
            tool_strategies.append({"google_search": {}})
        # 3) sem tools
        tool_strategies.append(None)

        last_error: Optional[str] = None
        for tools in tool_strategies:
            try:
                if tools is None:
                    model = genai.GenerativeModel(model_name)
                    resp = model.generate_content(prompt)
                else:
                    model = genai.GenerativeModel(model_name, tools=[tools])
                    # tool_config apenas quando google_search_retrieval
                    if "google_search_retrieval" in tools:
                        resp = model.generate_content(
                            prompt,
                            tools=[tools],
                            tool_config={"google_search_retrieval": {"dynamic_retrieval_config": {"mode": "MODE_DYNAMIC"}}},
                        )
                    else:
                        resp = model.generate_content(prompt, tools=[tools])
                try:
                    data = resp.to_dict()  # type: ignore[attr-defined]
                except Exception:
                    data = {"text": getattr(resp, "text", ""), "raw": str(resp)}
                return {"raw_url": None, "raw": data}
            except Exception as e:
                msg = str(e)
                last_error = msg
                # Tenta próxima estratégia se erro de campo desconhecido/argumento inválido
                if "Unknown field" in msg or "INVALID_ARGUMENT" in msg or "not recognized" in msg:
                    continue
                # outros erros: retorna imediatamente
                return {"raw_url": None, "raw": {"error": "fetch_failed", "message": msg, "request": input}}

        # Se todas falharem
        return {"raw_url": None, "raw": {"error": "no_tool_worked", "message": last_error, "request": input}}

    async def parse(self, raw: RawEvidence) -> ParsedAnswer:
        data = raw.get("raw") or {}
        text = ""
        try:
            candidates = data.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    text = "".join(p.get("text") or "" for p in parts)
        except Exception:
            text = ""

        links: list[dict] = []
        try:
            cand0 = (data.get("candidates") or [{}])[0]
            gm = cand0.get("groundingMetadata", {})
            atts = gm.get("groundingAttributions", [])
            for a in atts:
                web = a.get("web") or {}
                uri = web.get("uri") or web.get("url")
                if uri:
                    uri = resolve_known_redirects(uri)
                    links.append({"url": uri, "title": web.get("title")})
            cite = cand0.get("citationMetadata", {})
            for part in cite.get("citationSources", []):
                if part.get("uri"):
                    uri = resolve_known_redirects(part.get("uri"))
                    links.append({"url": uri, "title": part.get("title")})
        except Exception:
            pass

        usage = (data.get("usageMetadata") or {})
        # normalizar contadores comuns se presentes
        norm_usage = {}
        if usage:
            # Gemini usa candidates[0].usageMetadata em alguns modelos
            try:
                cand0 = (data.get("candidates") or [{}])[0]
                um = cand0.get("usageMetadata") or {}
                if um:
                    norm_usage = {
                        "input_tokens": um.get("promptTokenCount") or um.get("inputTokenCount"),
                        "output_tokens": um.get("candidatesTokenCount") or um.get("outputTokenCount"),
                        "total_tokens": um.get("totalTokenCount"),
                    }
            except Exception:
                pass
        return {"text": text, "blocks": [], "links": links, "meta": {"engine": self.name, "model": data.get("model"), "raw_usage": norm_usage or usage}}

    async def extract_citations(self, parsed: ParsedAnswer) -> List[Citation]:
        citations: List[Citation] = []
        have = set()
        for link in parsed.get("links", []):
            url = link.get("url")
            if not url:
                continue
            have.add(url)
            citations.append(
                {
                    "domain": url,
                    "url": url,
                    "anchor": link.get("title") or None,
                    "position": None,
                    "type": "link",
                }
            )
        text = parsed.get("text") or ""
        for m in URL_RE.findall(text):
            m2 = resolve_known_redirects(m)
            if m2 in have:
                continue
            citations.append({"domain": m2, "url": m2, "anchor": None, "position": None, "type": "link"})
        return citations

    async def normalize(self, parsed: ParsedAnswer) -> ParsedAnswer:
        return parsed
