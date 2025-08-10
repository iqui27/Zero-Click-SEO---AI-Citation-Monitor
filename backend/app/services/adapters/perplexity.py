from __future__ import annotations

import os
from typing import List

import httpx

from app.services.adapters.base import EngineAdapter, FetchInput, RawEvidence, ParsedAnswer, Citation


class PerplexityAdapter:
    name = "perplexity"

    def __init__(self, api_key: str | None = None, timeout_seconds: float = 30.0) -> None:
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://api.perplexity.ai"

    async def fetch(self, input: FetchInput) -> RawEvidence:
        if not self.api_key:
            return {"raw_url": None, "raw": {"error": "missing_api_key", "request": input}}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        model = (input.get("config", {}) or {}).get("model", "sonar-pro")
        user_query = input["query"]
        system = "Responda concisamente e liste as fontes com URLs completas ao final."
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_query},
        ]
        payload = {"model": model, "messages": messages}
        url = f"{self.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            data = resp.json()
            return {"raw_url": None, "raw": data}

    async def parse(self, raw: RawEvidence) -> ParsedAnswer:
        data = raw.get("raw") or {}
        choices = data.get("choices") or []
        content = ""
        if choices:
            msg = choices[0].get("message") or {}
            content = msg.get("content") or ""
        citations = data.get("citations") or []
        search_results = data.get("search_results") or []

        links: list[dict] = []
        for u in citations:
            if isinstance(u, str):
                links.append({"url": u})
        for r in search_results:
            u = r.get("url")
            if u:
                links.append({"url": u, "title": r.get("title")})

        return {"text": content, "blocks": [], "links": links, "meta": {"engine": self.name, "raw_usage": data.get("usage"), "model": data.get("model")}}

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
