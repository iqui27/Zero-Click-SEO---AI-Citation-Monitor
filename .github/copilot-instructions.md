## Copilot instructions for Zero‑Click SEO — AI Citation Monitor

Purpose: make AI agents productive fast by encoding what matters in THIS repo: architecture, workflows, conventions, integrations, and workflows with Linear.

### Architecture (big picture)
- Monorepo via Docker Compose with three services: FastAPI API, Celery worker, React/Vite frontend; Postgres + Redis.
- Data flow: frontend calls /api → FastAPI persists via SQLAlchemy → long jobs → Celery (queue: runs) with Redis → UI streams via SSE GET /api/runs/{id}/stream (polling fallback).
- External adapters: OpenAI, Gemini, Perplexity for answers; SERP scraping with Playwright (Chromium) and SerpAPI fallback.

Key files to read
- docker-compose.yml (service wiring, env, queues)
- backend/app/main.py (startup, CORS, “light migrations”, router include)
- backend/celery_app.py (Celery app bootstrap)
- backend/requirements.txt (LLMs, Playwright)
- frontend/vite.config.ts (dev proxy /api → :8000)
- README.md and docs/README-UX.md (UX flows, endpoints, KPIs)
 - backend/app/api/routes.py (FastAPI routes incl. runs list/detail/create/delete)
 - backend/app/schemas/schemas.py (Pydantic schemas for API input/output)
 - backend/app/models/models.py (SQLAlchemy models; e.g., Run)
 - frontend/src/lib/api.ts (API client and types that must mirror backend schemas)
 - frontend/src/pages/Runs.tsx (Runs list UI)
 - frontend/src/pages/RunDetail.tsx (Run details UI)

### E2E field addition checklist (example: cycles_total)
- DB model: add the column to `backend/app/models/models.py` (e.g., `Run.cycles_total` with a default). Append an `ALTER TABLE IF NOT EXISTS ... ADD COLUMN` in `backend/app/main.py` startup statements.
- Schemas: add the field to `RunOut`, `RunListItem`, and `RunDetailOut` in `backend/app/schemas/schemas.py`.
- Routes: ensure `/runs` (list), `/runs/{id}` (detail), and run creation map/select the field in `backend/app/api/routes.py` (e.g., map incoming `cycles` to `cycles_total` on create).
- Frontend types: add the field to `RunListItem` and `RunDetail` in `frontend/src/lib/api.ts`.
- Frontend UI: display the field where relevant (e.g., Runs card and Run detail metrics in `frontend/src/pages/Runs.tsx` and `frontend/src/pages/RunDetail.tsx`).
- Test: create a run with a non-default value and verify list/detail show it; check SSE/polling still work; no type errors.

### Local dev workflow
- First run: docker compose up -d --build; API at :8000 (/docs), UI at :5173.
- Logs: docker compose logs -f backend|worker|frontend; restart frontend if Vite deps glitch.
- Env keys (in .env): PERPLEXITY_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, SERPAPI_KEY. Optional helper: scripts/first-run.sh.

### Conventions you must follow
- API: prefix /api, routers under backend/app/api, aggregate in app.api.routes.api_router.
- Models: Pydantic v2; prefer orjson for JSON responses.
- DB: No Alembic. Startup applies Base.metadata.create_all and a list of ALTER TABLE IF NOT EXISTS statements in main.py. When adding columns, append a new stmt there.
- Celery: worker command is celery -A celery_app.celery_app worker -Q runs -l info. Route long tasks to queue runs.
- Streaming: prefer emitting progress events to show in SSE timeline; UI auto-falls back to polling if SSE 404.
- Frontend: React + Vite + Tailwind (dark mode via class). Dev proxy expects /api.

### Integration specifics
- LLMs: openai, google-generativeai, perplexity. Prefer GPT‑5 (Preview) where available; fall back to project-defaults if not.
- SERP: Prefer Playwright (Chromium) bundled in the backend image; use SerpAPI only as fallback.
- Analytics export: GET /api/analytics/subprojects/{id}/export.csv; KPIs AMR/DCR/ZCRS are computed per run.

### Linear workflow (mandatory)
- All work must map to a Linear issue. Reference the Linear issue ID in PR titles and commit messages, e.g., "feat(analytics): CSV export for subproject (LIN-123)".
- Create/triage tasks in Linear before coding; keep status in sync (In Progress → Review → Done).
- For ambiguous scope, open a "Spike" issue in Linear with timebox notes; link results in PR description.

### Common tasks (patterns from code)
- New endpoint: create router in backend/app/api/... and include in app.api.routes.api_router; define Pydantic schema in backend/app/schemas; persist via backend/app/models and backend/app/db; extend startup stmts if schema changes.
- New async job: add Celery task in backend/app/services, route to queue runs, emit progress events for SSE.
- Frontend call to backend: use fetch/axios against /api path to leverage Vite proxy; keep types in sync with backend schemas.

### Gotchas
- First Playwright Chromium install is slow; check backend logs.
- If frontend hot-reload fails, docker compose restart frontend usually fixes it.
- Keep /api prefix to avoid CORS and to use the dev proxy.
