#!/usr/bin/env python3
"""
Compare runs between SOURCE and TARGET Azure SQL (SQL Server).

Reads SOURCE_ODBC and TARGET_ODBC from environment (ODBC connection strings).
Prints counts and samples to help diagnose missing runs in the app UI.
"""
import os
import sys
import pyodbc

SOURCE_ODBC = os.environ.get("SOURCE_ODBC")
TARGET_ODBC = os.environ.get("TARGET_ODBC")

if not SOURCE_ODBC or not TARGET_ODBC:
    print("ERROR: Please set SOURCE_ODBC and TARGET_ODBC environment variables.")
    sys.exit(2)

QUERIES = {
    "total_runs": "SELECT COUNT(*) FROM runs",
    "runs_by_status": "SELECT status, COUNT(*) c FROM runs GROUP BY status ORDER BY c DESC",
    "runs_by_project": "SELECT project_id, COUNT(*) c FROM runs GROUP BY project_id ORDER BY c DESC",
    "date_range": "SELECT MIN(started_at) as min_started, MAX(started_at) as max_started FROM runs",
    "latest_runs": "SELECT TOP 10 id, project_id, status, started_at, finished_at FROM runs ORDER BY CASE WHEN started_at IS NULL THEN 1 ELSE 0 END, started_at DESC, id DESC",
}

PROJECT_QUERY = "SELECT id, name, country, language, timezone FROM projects WHERE id = ?"


def run_queries(label: str, odbc: str):
    print(f"\n=== {label} ===")
    cn = pyodbc.connect(odbc)
    cur = cn.cursor()
    results = {}
    for name, sql in QUERIES.items():
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            print(f"-- {name}:")
            for r in rows:
                print(tuple(r))
            results[name] = rows
        except Exception as e:
            print(f"ERROR in {name}: {e}")
            results[name] = None
    # Validate top project's presence in projects table
    top_proj = None
    try:
        r = results.get("runs_by_project")
        if r:
            top_proj = r[0][0]
    except Exception:
        top_proj = None
    if top_proj:
        try:
            cur.execute(PROJECT_QUERY, top_proj)
            p = cur.fetchone()
            print("-- project_present:", bool(p), p)
        except Exception as e:
            print("ERROR checking project_present:", e)
    cn.close()


def main():
    run_queries("SOURCE", SOURCE_ODBC)
    run_queries("TARGET", TARGET_ODBC)


if __name__ == "__main__":
    main()
