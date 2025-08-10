from __future__ import annotations

from typing import Protocol, TypedDict, List


class FetchInput(TypedDict):
    query: str
    language: str
    region: str
    device: str
    config: dict


class RawEvidence(TypedDict):
    raw_url: str | None
    raw: dict | str


class ParsedAnswer(TypedDict):
    text: str
    blocks: list[dict]
    links: list[dict]
    meta: dict


class Citation(TypedDict):
    domain: str
    url: str | None
    anchor: str | None
    position: str | None
    type: str | None


class EngineAdapter(Protocol):
    name: str

    async def fetch(self, input: FetchInput) -> RawEvidence:  # pragma: no cover
        ...

    async def parse(self, raw: RawEvidence) -> ParsedAnswer:  # pragma: no cover
        ...

    async def extract_citations(self, parsed: ParsedAnswer) -> List[Citation]:  # pragma: no cover
        ...

    async def normalize(self, parsed: ParsedAnswer) -> ParsedAnswer:  # pragma: no cover
        ...
