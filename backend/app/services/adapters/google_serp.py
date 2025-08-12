from __future__ import annotations

import os
from typing import List
from urllib.parse import urlencode, parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.adapters.base import EngineAdapter, FetchInput, RawEvidence, ParsedAnswer, Citation
from app.services.normalization import resolve_known_redirects


BLOCKED_HOSTS = {
    "google.com",
    "www.google.com",
    "policies.google.com",
    "accounts.google.com",
    "support.google.com",
    "maps.google.com",
    "translate.google.com",
}


class GoogleSerpAdapter:
    name = "google_serp"

    async def _try_accept_consent(self, page) -> None:
        selectors = [
            "button:has-text('Aceitar tudo')",
            "button:has-text('Aceitar')",
            "button:has-text('Concordo')",
            "button:has-text('Estou de acordo')",
            "button:has-text('I agree')",
            "button:has-text('Accept all')",
            "button:has-text('Accept')",
        ]
        for sel in selectors:
            try:
                await page.locator(sel).first.click(timeout=1500)
                return
            except Exception:
                continue

    async def _fetch_with_playwright(self, query: str, language: str) -> RawEvidence:
        params = {"q": query, "hl": language or "pt-BR", "gl": "BR", "pws": "0", "num": "10"}
        url = f"https://www.google.com/search?{urlencode(params)}"
        html = ""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])  # noqa
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                locale=language or "pt-BR",
            )
            page = await context.new_page()
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await self._try_accept_consent(page)
            try:
                await page.wait_for_selector("#search", timeout=20000)
            except Exception:
                pass
            # rolagem incremental
            try:
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, document.body.scrollHeight/2)")
                    await page.wait_for_timeout(800)
            except Exception:
                pass
            html = await page.content()
            await browser.close()
        return {"raw_url": url, "raw": {"html": html, "source": "html"}}

    async def fetch(self, input: FetchInput) -> RawEvidence:
        query = input["query"]
        language = input.get("language") or "pt-BR"
        region = input.get("region") or "BR"
        config = (input.get("config") or {})
        use_serpapi = config.get("use_serpapi")
        prefer_ai_overview = config.get("serpapi_ai_overview", True)
        no_cache = config.get("serpapi_no_cache")
        serp_key = os.getenv("SERPAPI_KEY")

        if use_serpapi and serp_key:
            try:
                base_url = "https://serpapi.com/search.json"
                # 1) Busca normal no Google para obter organic e (se disponível) AI Overview embed ou page_token
                params_google = {
                    "engine": "google",
                    "q": query,
                    "hl": language,
                    "gl": region,
                    "num": "10",
                    "api_key": serp_key,
                }
                if no_cache is not None:
                    params_google["no_cache"] = "true" if bool(no_cache) else "false"
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp_google = await client.get(base_url, params=params_google)
                    data_google = resp_google.json()

                ai_block = (data_google or {}).get("ai_overview") or {}
                ai_text_blocks = ai_block.get("text_blocks") or []
                ai_page_token = ai_block.get("page_token")

                # 2) Tentar AI Overview
                if prefer_ai_overview and (ai_text_blocks or ai_page_token):
                    # 2a) Se já veio embed, retornar diretamente
                    if ai_text_blocks:
                        return {
                            "raw_url": base_url,
                            "raw": {
                                "serpapi_ai": ai_block,
                                "serpapi_search": data_google,
                                "source": "serpapi_ai_embedded",
                            },
                        }
                    # 2b) Se só veio page_token, fazer a chamada dedicada do AI Overview
                    if ai_page_token:
                        params_ai = {
                            "engine": "google_ai_overview",
                            "page_token": ai_page_token,
                            "api_key": serp_key,
                        }
                        if no_cache is not None:
                            params_ai["no_cache"] = "true" if bool(no_cache) else "false"
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            resp_ai = await client.get(base_url, params=params_ai)
                            data_ai = resp_ai.json()
                        ai_payload = (data_ai or {}).get("ai_overview") or {}
                        if ai_payload.get("text_blocks"):
                            return {
                                "raw_url": base_url,
                                "raw": {
                                    "serpapi_ai": ai_payload,
                                    "serpapi_search": data_google,
                                    "source": "serpapi_ai",
                                },
                            }
                # 3) Caso não haja AI Overview, retornar o resultado normal do SerpApi (orgânico)
                return {
                    "raw_url": base_url,
                    "raw": {"serpapi": data_google, "source": "serpapi"},
                }
            except Exception:
                # fallback para Playwright em caso de erro no SerpApi
                return await self._fetch_with_playwright(query, language)

        # fallback para Playwright
        return await self._fetch_with_playwright(query, language)

    def _should_skip(self, href: str) -> bool:
        if not href or href.startswith("/preferences") or href.startswith("/setprefs"):
            return True
        if href.startswith("/search?") or href.startswith("/imgres?") or href.startswith("/advanced_search"):
            return True
        if href.startswith("#"):
            return True
        return False

    async def parse(self, raw: RawEvidence) -> ParsedAnswer:
        src = (raw.get("raw") or {}).get("source")
        links = []
        text_content = ""

        # 1) AI Overview (embedded ou extra request)
        if src in ("serpapi_ai", "serpapi_ai_embedded"):
            ai = (raw.get("raw") or {}).get("serpapi_ai") or {}
            text_blocks = ai.get("text_blocks") or []
            references = ai.get("references") or []

            # links a partir das referências do AI Overview
            for ref in references[:100]:
                url = resolve_known_redirects(ref.get("link") or ref.get("url") or "")
                title = ref.get("title")
                if not url:
                    continue
                parsed_url = urlparse(url)
                if parsed_url.netloc in BLOCKED_HOSTS:
                    continue
                links.append({"url": url, "title": title})

            # Fallback: se AI Overview não trouxe 'references', usar organic_results da busca normal
            used_fallback = False
            if not links:
                search_payload = (raw.get("raw") or {}).get("serpapi_search") or {}
                for item in (search_payload.get("organic_results") or [])[:20]:
                    url = resolve_known_redirects(item.get("link") or "")
                    title = item.get("title")
                    if not url:
                        continue
                    parsed_url = urlparse(url)
                    if parsed_url.netloc in BLOCKED_HOSTS:
                        continue
                    links.append({"url": url, "title": title})
                used_fallback = len(links) > 0

            # texto consolidado dos text_blocks
            def _flatten_blocks(blocks) -> str:
                parts = []
                for b in blocks or []:
                    snippet = b.get("snippet")
                    if snippet:
                        parts.append(snippet)
                    # listas aninhadas
                    if b.get("list"):
                        for li in b.get("list"):
                            li_snip = li.get("snippet") or li.get("title")
                            if li_snip:
                                parts.append(li_snip)
                            # nested list/text_blocks
                            if li.get("list"):
                                for sub in li.get("list"):
                                    if sub.get("snippet"):
                                        parts.append(sub.get("snippet"))
                            if li.get("text_blocks"):
                                parts.append(_flatten_blocks(li.get("text_blocks")))
                    if b.get("text_blocks"):
                        parts.append(_flatten_blocks(b.get("text_blocks")))
                return " \n".join([p for p in parts if p])

            text_content = _flatten_blocks(text_blocks)[:4000]
            return {
                "text": text_content,
                "blocks": text_blocks,
                "links": links,
                "meta": {"engine": self.name, "source": ("serpapi_ai_no_refs" if used_fallback else src)},
            }

        # 2) Resultados orgânicos via SerpApi (engine=google)
        if src == "serpapi":
            data = (raw.get("raw") or {}).get("serpapi") or {}
            for item in data.get("organic_results", [])[:20]:
                url = item.get("link")
                title = item.get("title")
                if url:
                    url = resolve_known_redirects(url)
                    links.append({"url": url, "title": title})
            text_content = (data.get("search_metadata") or {}).get("id", "")
            return {
                "text": text_content,
                "blocks": [],
                "links": links,
                "meta": {"engine": self.name, "source": src},
            }

        # 3) Fallback: HTML com Playwright
        html = (raw.get("raw") or {}).get("html") or ""
        soup = BeautifulSoup(html, "lxml")
        seen = set()
        for a in soup.select("#search a"):
            href = a.get("href")
            if not href or self._should_skip(href):
                continue
            url = None
            if href.startswith("/url?"):
                qs = parse_qs(urlparse(href).query)
                url = qs.get("q", [None])[0]
            elif href.startswith("http"):
                url = href
            if not url:
                continue
            url = resolve_known_redirects(url)
            parsed = urlparse(url)
            if parsed.netloc in BLOCKED_HOSTS:
                continue
            key = (parsed.scheme, parsed.netloc, parsed.path)
            if key in seen:
                continue
            seen.add(key)
            title = a.get_text(strip=True) or (a.select_one("h3").get_text(strip=True) if a.select_one("h3") else "")
            links.append({"url": url, "title": title})
        text_content = soup.get_text(" ", strip=True)[:3000]
        return {"text": text_content, "blocks": [], "links": links, "meta": {"engine": self.name, "source": src or "html"}}

    async def extract_citations(self, parsed: ParsedAnswer) -> List[Citation]:
        citations: List[Citation] = []
        source = (parsed.get("meta") or {}).get("source")
        ctype = "ai_reference" if source in ("serpapi_ai", "serpapi_ai_embedded") else "link"
        for link in parsed.get("links", [])[:50]:
            url = link.get("url")
            if not url:
                continue
            citations.append(
                {
                    "domain": url,
                    "url": url,
                    "anchor": link.get("title") or None,
                    "position": None,
                    "type": ctype,
                }
            )
        return citations

    async def normalize(self, parsed: ParsedAnswer) -> ParsedAnswer:
        return parsed
