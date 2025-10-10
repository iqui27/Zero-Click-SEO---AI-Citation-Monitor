# Repository Guidelines

## Project Structure & Module Organization
The repo splits into `backend/` (FastAPI app under `app/` with `api`, `services`, `db`, and migrations) and `frontend/` (React + Vite in `src/` with Tailwind styling). Shared scripts live in `scripts/`, dataset seeds in `data/`, docs in `docs/`, and deployment tooling in `deploy/` plus `docker-compose*.yml`. Add assets beside their feature modules and mirror backend route names in `frontend/src/api`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt` sets backend dependencies.
- `uvicorn --app-dir backend app.main:app --reload` runs the API with auto-reload.
- `cd frontend && npm install && npm run dev` starts the Vite dev server on all interfaces.
- `docker-compose up --build` runs the full stack (API, Redis, workers); use this path to validate infra changes.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; align response models with schemas in `backend/app/schemas`. Modules stay snake_case, classes PascalCase.
- Favor dependency-injected services and extend `app/services` with cohesive modules rather than scattering helpers.
- In the frontend, keep TypeScript strict mode defaults, PascalCase components in `src/components`, camelCase hooks/utilities in `src/lib`, and centralize Tailwind tokens in `tailwind.config.js`.

## Testing Guidelines
- Backend tests run with `pytest backend/tests`; add cases near fixtures, name files `test_<feature>.py`, and mark calls that hit external services.
- For API contracts, add integration checks that exercise `/analytics`, `/geo`, and `/export` via the FastAPI test client.
- Frontend currently relies on linting; add React Testing Library specs under `frontend/src/__tests__` when introducing interactive flows.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat:`, `refactor:`, `fix:`) as seen in history; scope components after the colon when helpful.
- Keep commits focused, separating schema migrations and generated assets for easier review.
- PRs describe user-facing outcomes, list affected endpoints or UI routes, and reference tracking issues. Attach screenshots or terminal output for visible changes.
- Verify lint, unit tests, and docker-compose startup before requesting review, noting skipped checks explicitly.

## Deployment & Configuration Tips
Store secrets in ignored env files; the backend reads settings via `pydantic-settings`. When touching Celery or scheduler behavior, keep Redis URLs aligned across `docker-compose.yml` and `backend/celery_app.py`, and adjust `deploy/` scripts if commands or artifact paths change.
