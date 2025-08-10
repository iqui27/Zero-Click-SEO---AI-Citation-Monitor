from __future__ import annotations

import os
import re
from typing import List

from openai import OpenAI

from app.services.adapters.base import EngineAdapter, FetchInput, RawEvidence, ParsedAnswer, Citation


URL_RE = re.compile(r"https?://[\w\-\.\?\,\'\/\+&%\$#_=:\(\)\*]+", re.IGNORECASE)


class OpenAIAdapter:
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    async def fetch(self, input: FetchInput) -> RawEvidence:
        if not self.client:
            return {"raw_url": None, "raw": {"error": "missing_api_key", "request": input}}
        system = (
            (input.get("config") or {}).get("system")
            or "Responda concisamente e liste as fontes no final com URLs completas (http)."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": input["query"]},
        ]
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return {"raw_url": None, "raw": resp.model_dump()}

    async def parse(self, raw: RawEvidence) -> ParsedAnswer:
        data = raw.get("raw") or {}
        choices = data.get("choices") or []
        content = ""
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content") or ""
        # Extrair possíveis URLs do texto
        links = []
        for m in URL_RE.findall(content or ""):
            links.append({"url": m})
        usage = data.get("usage") or {}
        return {"text": content, "blocks": [], "links": links, "meta": {"engine": self.name, "model": data.get("model"), "raw_usage": usage}}

    async def extract_citations(self, parsed: ParsedAnswer) -> List[Citation]:
        citations: List[Citation] = []
        for link in parsed.get("links", []):
            url = link.get("url")
            if not url:
                continue
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
