# Copilot instructions for Zero‑Click SEO — AI Citation Monitor

Purpose: make AI coding agents instantly productive in this repo by codifying architecture, workflows, conventions, and gotchas observed in the codebase.

## Big picture
- Monorepo with three services via Docker Compose: FastAPI API + Celery worker + React/Vite frontend; infra uses Postgres and Redis.
- Data flow: frontend calls API at /api (proxied by Vite) → backend persists with SQLAlchemy (Postgres) → long jobs go to Celery (Redis broker) → live UI subscribes to SSE at GET /api/runs/{id}/stream with polling fallback.
- External adapters: OpenAI, Gemini, Perplexity for answers; SERP via Playwright (Chromium) with SerpAPI fallback.

Key files
- docker-compose.yml — services, env wiring, and the Celery queue name (runs).
- backend/app/main.py — app startup, CORS, “light migrations”, router include.
- backend/celery_app.py → app.services.tasks.celery — Celery app import point.
- backend/Dockerfile — installs Python deps and Playwright + Chromium.
- frontend/vite.config.ts — dev proxy for /api to backend:8000.
- README.md and docs/README-UX.md — product/UX, endpoints, and ops hints.

## Run and debug locally
- First run and rebuild
```bash
docker compose up -d --build
```
- Health and docs: API /health and /docs (Swagger). Frontend on http://localhost:5173.
- Logs and restarts
```bash
docker compose logs -f backend|worker|frontend
docker compose restart frontend  # fixes Vite/node_modules hiccups
```
- Minimal .env (Compose passes these through): PERPLEXITY_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, SERPAPI_KEY. Script: scripts/first-run.sh can scaffold a sandbox .env.

## Conventions and patterns
- API prefix is /api; add routes via app/api/... and aggregate under app.api.routes.api_router.
- Pydantic v2 models (pydantic and pydantic-settings); prefer orjson for payloads.
- DB: Base.metadata.create_all on startup; light “ALTER TABLE IF NOT EXISTS …” migrations are appended in main.py. There’s no Alembic.
  - When adding columns, mirror the pattern in main.py by appending another statement to stmts.
- Celery
  - Worker starts with: celery -A celery_app.celery_app worker -Q runs -l info.
  - Route long-running tasks to the runs queue (match the queue name).
- Streaming
  - Live timeline via SSE: GET /api/runs/{id}/stream; UI falls back to polling if 404.
- Frontend
  - React + Vite + Tailwind (darkMode: 'class'); TypeScript config is strict; /api proxied in dev.

## Integration points
- LLMs: openai, google-generativeai, perplexity (see backend/requirements.txt); adapters normalize citations and metrics (AMR/DCR/ZCRS) per README.
- SERP: Playwright headless Chromium is installed in the backend image; SerpAPI is a fallback.
- KPIs/analytics endpoints are documented in README.md; export CSV is GET /api/analytics/subprojects/{id}/export.csv.

## Tips and gotchas
- If frontend hot-reload or install issues occur, the container re-installs deps on boot; restart the frontend service.
- Playwright’s first Chromium install takes time; check backend logs.
- CORS is permissive for local dev; keep /api path to leverage Vite proxy in dev.

## Common tasks (examples by reference)
- New endpoint: add a router under app/api/... and include it in app.api.routes.api_router; models in app/schemas, persistence in app/models/app/db.
- New async job: define a Celery task under app/services (use queue='runs' if routing) and invoke from API layer; stream progress via events to SSE endpoint if applicable.
- New DB field: add SQLAlchemy model change and extend the main.py startup migration stmts.
