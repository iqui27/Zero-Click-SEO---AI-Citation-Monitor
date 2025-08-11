
from __future__ import annotations

import os
import re
from typing import List, Optional, Dict, Any

from openai import OpenAI

from app.services.adapters.base import EngineAdapter, FetchInput, RawEvidence, ParsedAnswer, Citation


URL_RE = re.compile(r"https?://[\w\-\.\?\,\'\/\+&%\$#_=:\(\)\*]+", re.IGNORECASE)


class OpenAIAdapter:
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        # Keep env override but allow per-request override in fetch()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    async def fetch(self, input: FetchInput) -> RawEvidence:
        """Call OpenAI Responses API, optionally with web_search_preview."""
        if not self.client:
            return {"raw_url": None, "raw": {"error": "missing_api_key", "request": input}}

        cfg: Dict[str, Any] = (input.get("config") or {})

        # Use `instructions` (system prompt) per Responses API best-practice
        system = cfg.get("system") or (
            "Responda concisamente e liste as fontes no final com URLs completas (http)."
        )

        # Allow model + token limit override via config
        model = cfg.get("model") or self.model
        max_output_tokens = int(cfg.get("max_output_tokens") or 1000)

        # Optional web search tool
        use_web_search = cfg.get("web_search", True)
        web_search_options = cfg.get("web_search_options")  # e.g., {"recency_days": 30, ...}
        tools: List[Dict[str, Any]] = []
        if use_web_search:
            tool: Dict[str, Any] = {"type": "web_search_preview"}
            if isinstance(web_search_options, dict) and web_search_options:
                tool["web_search_options"] = web_search_options
            tools.append(tool)

        # Build request payload for Responses API
        kwargs: Dict[str, Any] = {
            "model": model,
            "instructions": system,
            "input": [
                {"role": "user", "content": input["query"]},
            ],
            "max_output_tokens": max_output_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        resp = self.client.responses.create(**kwargs)

        # Store both the full structured response and a plain text field for easy parsing
        raw_payload: Dict[str, Any] = {
            "response": resp.model_dump(),
            "output_text": getattr(resp, "output_text", None),
            "model": model,
        }
        return {"raw_url": None, "raw": raw_payload}

    async def parse(self, raw: RawEvidence) -> ParsedAnswer:
        data: Dict[str, Any] = raw.get("raw") or {}

        # Prefer the SDK-provided output_text; fallback to reconstruct from response dict
        content: str = data.get("output_text") or ""
        if not content:
            content = self._extract_text_from_response_dict(data.get("response") or {})

        # Extract possible URLs from the text
        links: List[Dict[str, str]] = []
        for m in URL_RE.findall(content or ""):
            links.append({"url": m})

        usage: Dict[str, Any] = {}
        response_dict: Dict[str, Any] = data.get("response") or {}
        usage = (response_dict.get("usage") or {}) if isinstance(response_dict, dict) else {}

        return {
            "text": content,
            "blocks": [],
            "links": links,
            "meta": {
                "engine": self.name,
                "model": data.get("model") or (response_dict.get("model") if isinstance(response_dict, dict) else None),
                "raw_usage": usage,
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

    # -------------------- helpers --------------------
    def _extract_text_from_response_dict(self, response_dict: Dict[str, Any]) -> str:
        """Best-effort text extraction for Responses API dicts (when output_text is absent)."""
        if not isinstance(response_dict, dict):
            return ""

        # New Responses format usually has a top-level "output" list with assistant messages
        output = response_dict.get("output")
        if isinstance(output, list):
            parts: List[str] = []
            for item in output:
                # Expecting items with structure like {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "..."}, ...]}
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "message":
                    content_list = item.get("content")
                    if isinstance(content_list, list):
                        for c in content_list:
                            if isinstance(c, dict):
                                # The SDK uses various keys; prefer "text" if present
                                text_val = c.get("text") or c.get("content")
                                if isinstance(text_val, str):
                                    parts.append(text_val)
            if parts:
                return "\n".join(parts).strip()

        # Fallbacks: some beta responses may store a string under "content"
        content = response_dict.get("content")
        if isinstance(content, str):
            return content

        # Legacy compatibility: try to mimic Chat Completions-style shape if present
        choices = response_dict.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0] or {}
            msg = first.get("message") or {}
            if isinstance(msg, dict):
                txt = msg.get("content")
                if isinstance(txt, str):
                    return txt
        return ""
