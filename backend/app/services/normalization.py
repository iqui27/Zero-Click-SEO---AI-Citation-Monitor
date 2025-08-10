from __future__ import annotations

from urllib.parse import urlparse, parse_qs, urlunparse
import httpx


def normalize_domain(url_or_domain: str) -> str:
    value = (url_or_domain or "").strip().lower()
    if not value:
        return value
    if "://" in value:
        netloc = urlparse(value).netloc
    else:
        netloc = value
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if netloc.startswith("m."):
        netloc = netloc[2:]
    return netloc


def extract_url_from_google_wrapper(url: str) -> str:
    """Se a URL for google redirect (/url?q=...), retorna o valor de q."""
    try:
        parsed = urlparse(url)
        if parsed.netloc.endswith("google.com") and parsed.path.startswith("/url"):
            qs = parse_qs(parsed.query)
            q = qs.get("q", [None])[0]
            if q:
                return q
    except Exception:
        pass
    return url


def resolve_vertexai_grounding_redirect(url: str, timeout_seconds: float = 8.0) -> str:
    """Segue o redirect do endpoint vertexaisearch grounding-api-redirect e retorna a URL final."""
    try:
        parsed = urlparse(url)
        if parsed.netloc == "vertexaisearch.cloud.google.com" and "grounding-api-redirect" in parsed.path:
            with httpx.Client(follow_redirects=False, timeout=timeout_seconds) as client:
                r = client.get(url)
                if 300 <= r.status_code < 400:
                    loc = r.headers.get("location") or r.headers.get("Location")
                    if loc:
                        return loc
    except Exception:
        pass
    return url


def resolve_known_redirects(url: str) -> str:
    if not url:
        return url
    url1 = extract_url_from_google_wrapper(url)
    url2 = resolve_vertexai_grounding_redirect(url1)
    return url2


def normalize_url_for_dedupe(url: str) -> str:
    """Normaliza URL para deduplicação: schema/host lowercase, remove fragmentos e UTMs, remove trailing '/'."""
    if not url:
        return url
    url = resolve_known_redirects(url)
    p = urlparse(url)
    scheme = (p.scheme or "http").lower()
    netloc = normalize_domain(p.netloc or "")
    path = (p.path or "/").rstrip("/") or "/"
    # remove parâmetros de tracking comuns
    if p.query:
        qs = parse_qs(p.query)
        filtered = {k: v for k, v in qs.items() if not k.lower().startswith(("utm_", "gclid", "fbclid"))}
        query = "&".join([f"{k}={v[0]}" for k, v in filtered.items()]) if filtered else ""
    else:
        query = ""
    return urlunparse((scheme, netloc, path, "", query, ""))
