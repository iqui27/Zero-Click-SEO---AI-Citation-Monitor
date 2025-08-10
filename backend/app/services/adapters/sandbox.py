from __future__ import annotations

import random
from typing import List

from app.services.adapters.base import EngineAdapter, FetchInput, RawEvidence, ParsedAnswer, Citation


EXAMPLE_SOURCES = [
    {"url": "https://pt.wikipedia.org/wiki/PIX", "anchor": "Wikipedia - Pix"},
    {"url": "https://www.bcb.gov.br/estabilidadefinanceira/pix", "anchor": "Banco Central do Brasil - Pix"},
    {"url": "https://www.bb.com.br/site/pix/", "anchor": "Banco do Brasil - Pix"},
    {"url": "https://www.gov.br", "anchor": "Portal Gov.br"},
]


class SandboxAdapter:
    name = "sandbox"

    async def fetch(self, input: FetchInput) -> RawEvidence:
        query = input.get("query") or ""
        return {
            "raw_url": None,
            "raw": {
                "query": query,
                "note": "sandbox_mode",
            },
        }

    async def parse(self, raw: RawEvidence) -> ParsedAnswer:
        query = (raw.get("raw") or {}).get("query") or ""
        snippet = (
            f"Resposta simulada para: {query}\n\n" \
            f"- O Pix é gratuito para PF em geral\n" \
            f"- Para PJ há tarifas em recebimentos\n" \
            f"- Limites personalizáveis no app\n\n" \
            f"Fontes: ver links abaixo"
        )
        # Embaralhar 2-3 fontes
        sources = random.sample(EXAMPLE_SOURCES, k=3)
        links = [{"url": s["url"], "anchor": s["anchor"]} for s in sources]
        return {"text": snippet, "blocks": [], "links": links, "meta": {"engine": self.name}}

    async def extract_citations(self, parsed: ParsedAnswer) -> List[Citation]:
        cites: List[Citation] = []
        for idx, link in enumerate(parsed.get("links") or []):
            cites.append(
                {
                    "domain": link.get("url") or "",
                    "url": link.get("url"),
                    "anchor": link.get("anchor"),
                    "position": str(idx + 1),
                    "type": "link",
                }
            )
        return cites

    async def normalize(self, parsed: ParsedAnswer) -> ParsedAnswer:
        return parsed
