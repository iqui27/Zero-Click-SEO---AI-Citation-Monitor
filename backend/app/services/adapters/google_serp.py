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
        use_serpapi = (input.get("config") or {}).get("use_serpapi")
        serp_key = os.getenv("SERPAPI_KEY")
        if use_serpapi and serp_key:
            params = {
                "engine": "google",
                "q": query,
                "hl": language,
                "gl": "BR",
                "num": "10",
                "api_key": serp_key,
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get("https://serpapi.com/search.json", params=params)
                data = r.json()
                return {"raw_url": "https://serpapi.com/search.json", "raw": {"serpapi": data, "source": "serpapi"}}
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
        if src == "serpapi":
            data = (raw.get("raw") or {}).get("serpapi") or {}
            for item in data.get("organic_results", [])[:20]:
                url = item.get("link")
                title = item.get("title")
                if url:
                    url = resolve_known_redirects(url)
                    links.append({"url": url, "title": title})
            text_content = (data.get("search_metadata") or {}).get("id", "")
        else:
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
                    "type": "link",
                }
            )
        return citations

    async def normalize(self, parsed: ParsedAnswer) -> ParsedAnswer:
        return parsed
