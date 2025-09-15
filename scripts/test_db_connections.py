#!/usr/bin/env python3
"""
Test connectivity to two SQL Server databases (Azure SQL) using SQLAlchemy URLs.

Reads SOURCE_DATABASE_URL and TARGET_DATABASE_URL from environment variables.
Supports both styles:
- mssql+pyodbc://USER:PASS@HOST:1433/DB?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes...
- mssql+pyodbc:///?odbc_connect=<percent-encoded-connection-string>

It will:
- Extract hostname to test DNS resolution and TCP:1433 connectivity
- Attempt a simple SELECT 1 on each database
"""
from __future__ import annotations

import os
import re
import socket
import sys
from urllib.parse import urlparse, parse_qs, unquote, quote_plus

from sqlalchemy import create_engine, text


def parse_host_from_url(url: str) -> str | None:
    # Handle odbc_connect style
    if 'odbc_connect=' in url:
        q = url.split('?', 1)[-1]
        params = parse_qs(q)
        odbc_enc = params.get('odbc_connect', [None])[0]
        if not odbc_enc:
            return None
        odbc = unquote(odbc_enc)
        # Look for SERVER=hostname[,port]; semicolon separated
        m = re.search(r"SERVER\s*=\s*([^;]+)", odbc, flags=re.IGNORECASE)
        if not m:
            return None
        server = m.group(1).strip()
        # SERVER might be like host,1433
        return server.split(',')[0].strip()

    # Normal URL pattern
    parsed = urlparse(url)
    # netloc might include username:password@host:port
    netloc = parsed.netloc
    if '@' in netloc:
        netloc = netloc.split('@', 1)[1]
    host = netloc.split(':', 1)[0]
    return host or None


def parse_odbc_connect(url: str) -> dict | None:
    """Parse percent-encoded ODBC connect string from mssql+pyodbc URL into a dict.
    Returns keys like SERVER, DATABASE, UID, PWD, etc. or None if not found."""
    if 'odbc_connect=' not in url:
        return None
    q = url.split('?', 1)[-1]
    params = parse_qs(q)
    odbc_enc = params.get('odbc_connect', [None])[0]
    if not odbc_enc:
        return None
    odbc = unquote(odbc_enc)
    parts = odbc.split(';')
    kv = {}
    for p in parts:
        if not p.strip():
            continue
        if '=' in p:
            k, v = p.split('=', 1)
            kv[k.strip().upper()] = v.strip()
    return kv or None


essential_mssql_connect_args = {
    "timeout": 120,
    "login_timeout": 120,
    "autocommit": True,
}


def make_engine(url: str):
    if url.startswith("mssql"):
        return create_engine(
            url,
            pool_pre_ping=True,
            connect_args=essential_mssql_connect_args,
            pool_timeout=60,
            pool_recycle=3600,
        )
    return create_engine(url, pool_pre_ping=True)


def test_dns(host: str) -> bool:
    try:
        ip = socket.gethostbyname(host)
        print(f"  ✅ DNS: {host} -> {ip}")
        return True
    except Exception as e:
        print(f"  ❌ DNS failed for {host}: {e}")
        return False


def test_port(host: str, port: int = 1433) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"  ✅ TCP {host}:{port} reachable")
            return True
        print(f"  ❌ TCP {host}:{port} connect_ex={result}")
        return False
    except Exception as e:
        print(f"  ❌ TCP check failed for {host}:{port}: {e}")
        return False


def test_db(url: str) -> bool:
    try:
        engine = make_engine(url)
        with engine.connect() as conn:
            v = conn.execute(text("SELECT 1")).scalar()
            print(f"  ✅ DB query ok: SELECT 1 -> {v}")
            return True
    except Exception as e:
        print(f"  ❌ DB query failed (pyodbc/primary): {e}")
        # Try pymssql fallback if we have an odbc_connect URL and creds
        try:
            kv = parse_odbc_connect(url)
            if not kv:
                return False
            server = kv.get('SERVER')
            database = kv.get('DATABASE') or kv.get('DB')
            uid = kv.get('UID') or kv.get('USER') or kv.get('USERNAME')
            pwd = kv.get('PWD') or kv.get('PASSWORD')
            if not (server and database and uid and pwd):
                return False
            host = server.split(',')[0].strip()
            pymssql_url = (
                f"mssql+pymssql://{quote_plus(uid)}:{quote_plus(pwd)}@{host}:1433/{quote_plus(database)}?charset=utf8"
            )
            print("  ℹ️ Retrying via pymssql fallback: ", pymssql_url.replace(quote_plus(pwd), "***"))
            engine = create_engine(pymssql_url, pool_pre_ping=True)
            with engine.connect() as conn:
                v = conn.execute(text("SELECT 1")).scalar()
                print(f"  ✅ DB query ok (pymssql fallback): SELECT 1 -> {v}")
                return True
        except Exception as e2:
            print(f"  ❌ DB query failed (pymssql fallback): {e2}")
        return False


def run(label: str, url: str) -> bool:
    print(f"\n=== {label} ===")
    host = parse_host_from_url(url)
    if host:
        test_dns(host)
        test_port(host, 1433)
    else:
        print("  ℹ️ Could not parse host from URL; skipping DNS/TCP tests")
    return test_db(url)


def main() -> int:
    src = os.environ.get("SOURCE_DATABASE_URL")
    tgt = os.environ.get("TARGET_DATABASE_URL")
    if not src and not tgt:
        print("Provide SOURCE_DATABASE_URL and/or TARGET_DATABASE_URL in the environment.")
        return 2

    ok = True
    if src:
        ok &= run("SOURCE", src)
    if tgt:
        ok &= run("TARGET", tgt)

    print("\nSummary:")
    print(f"  SOURCE: {'OK' if src and run('SOURCE (recheck)', src) else 'SKIPPED' if not src else 'FAIL'}")
    print(f"  TARGET: {'OK' if tgt and run('TARGET (recheck)', tgt) else 'SKIPPED' if not tgt else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
