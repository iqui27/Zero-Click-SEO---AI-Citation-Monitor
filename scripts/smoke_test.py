#!/usr/bin/env python3
"""
Smoke test script for zero-click.iqui27.codes

Checks performed:
 1) GET BASE_URL -> 200 and contains `<title>SEO Analyzer</title>`
 2) GET BASE_URL + /api/health -> JSON {"status": "ok"}
 3) Start job -> poll SSE stream at /api/runs/{id}/stream until completion

Configuration via environment variables:
 - BASE_URL: Base URL of the deployment (default: https://zero-click.iqui27.codes)
 - HEALTH_PATH: Health endpoint path (default: /api/health)
 - START_PATH: Endpoint to create a new run/job (default: /api/runs)
 - START_METHOD: HTTP method to start job (default: POST; supports GET/POST)
 - START_BODY: JSON string to send as body when starting job (default: {})
 - STREAM_PATH_TEMPLATE: Template for SSE stream path (default: /api/runs/{id}/stream)
 - AUTH_BEARER: Optional bearer token to include as Authorization header
 - EXTRA_HEADERS: Optional JSON object with extra headers to send on all requests
 - TIMEOUT_SECS: Per-request timeout in seconds (default: 15)
 - STREAM_TIMEOUT_SECS: Max time in seconds to wait for stream completion (default: 300)

Exit codes (for CI visibility):
 0 = success
 2 = homepage check failed (status/content)
 3 = health check failed
 4 = start job failed
 5 = stream failed or did not complete in time
 6 = unexpected error (exceptions, bad configs)

This script uses only the Python standard library.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
from http.client import HTTPResponse
from typing import Dict, Optional

import ssl
import http.client


def build_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"User-Agent": "smoke-test/1.0"}
    auth = os.getenv("AUTH_BEARER")
    if auth:
        headers["Authorization"] = f"Bearer {auth}"
    extra = os.getenv("EXTRA_HEADERS")
    if extra:
        try:
            extra_obj = json.loads(extra)
            if not isinstance(extra_obj, dict):
                raise ValueError("EXTRA_HEADERS must be a JSON object")
            for k, v in extra_obj.items():
                headers[str(k)] = str(v)
        except Exception as e:
            print(f"[warn] Ignoring EXTRA_HEADERS (invalid JSON): {e}")
    return headers


def request(method: str, url: str, headers: Dict[str, str], body: Optional[bytes] = None, timeout: int = 15) -> HTTPResponse:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme in URL: {url}")

    if parsed.scheme == "https":
        context = ssl.create_default_context()
        conn = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=timeout, context=context)
    else:
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=timeout)

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    conn.request(method, path, body=body, headers=headers)
    return conn.getresponse()


def read_all(resp: HTTPResponse) -> bytes:
    data = resp.read()
    resp.close()
    return data


def join(base_url: str, path: str) -> str:
    return urllib.parse.urljoin(base_url if base_url.endswith('/') else base_url + '/', path.lstrip('/'))


def get_env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v is not None and v != "" else default


def homepage_check(base_url: str, headers: Dict[str, str], timeout: int) -> None:
    url = base_url
    print(f"[info] Checking homepage: {url}")
    resp = request("GET", url, headers, timeout=timeout)
    status = resp.status
    body = read_all(resp)
    if status != 200:
        print(f"[error] Homepage returned status {status}")
        sys.exit(2)
    body_text = body.decode(errors="replace")
    if "<title>SEO Analyzer</title>" not in body_text:
        print("[error] Homepage does not contain expected <title>SEO Analyzer</title>")
        sys.exit(2)
    print("[ok] Homepage check passed")


def health_check(base_url: str, health_path: str, headers: Dict[str, str], timeout: int) -> None:
    url = join(base_url, health_path)
    print(f"[info] Checking health: {url}")
    resp = request("GET", url, headers, timeout=timeout)
    status = resp.status
    body = read_all(resp)
    if status != 200:
        print(f"[error] Health returned status {status}")
        sys.exit(3)
    try:
        data = json.loads(body.decode("utf-8"))
    except Exception as e:
        print(f"[error] Health body is not JSON: {e}")
        sys.exit(3)
    if data.get("status") != "ok":
        print(f"[error] Health JSON unexpected: {data}")
        sys.exit(3)
    print("[ok] Health check passed")


def start_job(base_url: str, start_path: str, method: str, start_body: str, headers: Dict[str, str], timeout: int) -> str:
    url = join(base_url, start_path)
    print(f"[info] Starting job: {method} {url}")
    body_bytes = None
    local_headers = dict(headers)
    if method.upper() in ("POST", "PUT", "PATCH"):
        try:
            payload_obj = json.loads(start_body or "{}") if start_body else {}
        except Exception as e:
            print(f"[error] START_BODY is not valid JSON: {e}")
            sys.exit(6)
        body_bytes = json.dumps(payload_obj).encode("utf-8")
        local_headers.setdefault("Content-Type", "application/json")

    resp = request(method.upper(), url, local_headers, body=body_bytes, timeout=timeout)
    status = resp.status
    body = read_all(resp)
    if status >= 400:
        print(f"[error] Start job returned status {status}: {body.decode(errors='replace')}")
        sys.exit(4)
    try:
        data = json.loads(body.decode("utf-8"))
    except Exception as e:
        print(f"[error] Start job response is not JSON: {e}")
        sys.exit(4)

    # Try common id shapes
    run_id = data.get("id") or data.get("run_id")
    if not run_id:
        run = data.get("run") or {}
        run_id = run.get("id") or run.get("run_id")
    if not run_id:
        print(f"[error] Could not locate run id in response: {data}")
        sys.exit(4)

    print(f"[ok] Job started with id: {run_id}")
    return str(run_id)


def poll_sse_until_done(base_url: str, stream_tpl: str, run_id: str, headers: Dict[str, str], timeout_secs: int, per_request_timeout: int) -> None:
    # Heuristic: completion when we see one of these markers
    done_markers = (
        'event: done',
        '"status":"completed"',
        '"state":"completed"',
        '"completed":true',
        '"phase":"completed"',
        '"done":true',
    )

    path = stream_tpl.replace("{id}", run_id)
    url = join(base_url, path)
    print(f"[info] Polling SSE stream: {url}")

    headers_sse = dict(headers)
    headers_sse.setdefault("Accept", "text/event-stream")

    start_time = time.time()
    # We re-open the stream if the server closes it before done within overall timeout
    while time.time() - start_time < timeout_secs:
        try:
            resp = request("GET", url, headers_sse, timeout=per_request_timeout)
            status = resp.status
            if status != 200:
                body = read_all(resp)
                print(f"[warn] SSE stream returned status {status}: {body.decode(errors='replace')}")
                # brief backoff before retry
                time.sleep(1.5)
                continue

            # Read incremental lines without closing early
            buf = b""
            last_progress_log = time.time()
            while True:
                chunk = resp.read(1024)
                if not chunk:
                    break
                buf += chunk
                # Process line by line for SSE semantics
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    s = line.decode(errors="replace").strip()
                    if s:
                        # periodic progress log
                        now = time.time()
                        if now - last_progress_log > 5:
                            print("[info] ...streaming...")
                            last_progress_log = now
                        # print debug lines lightly
                        # print(f"[debug] {s}")
                        if any(marker in s for marker in done_markers):
                            print(f"[ok] Completion detected in stream: {s}")
                            resp.close()
                            return
            resp.close()
        except Exception as e:
            print(f"[warn] SSE stream exception: {e}")
        # brief delay before re-open
        time.sleep(1.5)

    print("[error] Stream did not signal completion within timeout")
    sys.exit(5)


def main() -> None:
    try:
        base_url = get_env("BASE_URL", "https://zero-click.iqui27.codes")
        health_path = get_env("HEALTH_PATH", "/api/health")
        start_path = get_env("START_PATH", "/api/runs")
        start_method = get_env("START_METHOD", "POST").upper()
        start_body = get_env("START_BODY", "{}")
        stream_tpl = get_env("STREAM_PATH_TEMPLATE", "/api/runs/{id}/stream")
        timeout_secs = int(get_env("TIMEOUT_SECS", "15"))
        stream_timeout_secs = int(get_env("STREAM_TIMEOUT_SECS", "300"))

        headers = build_headers()

        homepage_check(base_url, headers, timeout_secs)
        health_check(base_url, health_path, headers, timeout_secs)
        run_id = start_job(base_url, start_path, start_method, start_body, headers, timeout_secs)
        poll_sse_until_done(base_url, stream_tpl, run_id, headers, stream_timeout_secs, timeout_secs)
        print("[ok] All smoke tests passed")
        sys.exit(0)
    except SystemExit as se:
        # pass through explicit exit codes
        raise se
    except Exception as e:
        print(f"[error] Unexpected failure: {e}")
        sys.exit(6)


if __name__ == "__main__":
    main()

