# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zero-Click SEO & AI Citation Monitor - A FastAPI/React application that monitors AI citations and SERP data across multiple engines (Gemini, OpenAI, Perplexity, Google SERP). Features real-time monitoring with scheduling, analytics dashboards, IM-SEO/IM-SEOIA metrics, GEO (Generative Engine Optimization) analysis, and CSV exports.

## Development Commands

### Docker Compose (Recommended)
```bash
# Start all services (API, Worker, Frontend, Redis)
# Note: Uses SQLite in dev (app_data volume), Azure SQL in production
docker compose up -d --build

# View logs
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# Stop services
docker compose down

# Production deployment
docker compose -f docker-compose.prod.yml up -d --build
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev          # Development server (http://localhost:5173)
npm run build        # Production build
npm run lint         # ESLint check
npm run preview      # Preview production build
```

### Backend Development
```bash
cd backend
# Dependencies in requirements.txt
# Backend runs via Docker - see docker compose commands above
```

## Architecture

### Stack
- **Backend**: FastAPI + SQLAlchemy + Celery (billiard) + Redis
- **Frontend**: React + Vite + TypeScript + Tailwind CSS + Recharts
- **Database**: SQLite (dev) / Azure SQL Server (prod) / PostgreSQL (supported)
- **External APIs**: OpenAI, Gemini, Perplexity, SerpAPI, Google Search Console, PageSpeed Insights
- **Scraping**: Playwright (Chromium headless) for SERP collection

### Service Communication
- Frontend → FastAPI API (via `/api` prefix)
- Long-running tasks → Celery worker (queue: `runs`)
- Real-time updates → SSE streaming (`/api/runs/{id}/stream`) with polling fallback
- Database migrations → Manual schema updates in `backend/app/main.py` startup

### Key File Structure
```
backend/
├── app/main.py                      # FastAPI app, CORS, startup migrations, scheduler
├── app/api/
│   ├── routes.py                   # Core API routes (projects, runs, monitors, etc.)
│   ├── analytics_routes.py         # Analytics dashboards and insights
│   ├── export_routes.py            # CSV/Excel export endpoints
│   ├── geo_routes.py               # GEO metrics and dashboards
│   └── search_console_routes.py    # Google Search Console integration
├── app/models/models.py             # SQLAlchemy models (Run, Citation, SerpFeature, etc.)
├── app/schemas/schemas.py           # Pydantic request/response schemas
├── app/services/
│   ├── adapters/                   # Engine adapters (Gemini, OpenAI, Perplexity, SERP)
│   │   ├── base.py                 # Base adapter interface
│   │   ├── gemini.py               # Google Gemini adapter
│   │   ├── openai_adapter.py       # OpenAI/ChatGPT adapter
│   │   ├── perplexity.py           # Perplexity adapter
│   │   └── google_serp.py          # Google SERP scraping (Playwright + SerpAPI)
│   ├── tasks.py                    # Celery task definitions (run_task)
│   ├── engine_runner.py            # Adapter orchestration with subprocess timeout
│   ├── scheduler.py                # Cron-based monitor scheduler
│   ├── geo_metrics.py              # GEO metric calculations
│   ├── geo_dashboard.py            # GEO dashboard aggregations
│   ├── im_metrics_simple.py        # IM-SEO/IM-SEOIA calculations
│   ├── advanced_analytics.py       # SWOT, competitive analysis
│   └── search_console.py           # GSC OAuth and data fetching
├── app/core/config.py               # Settings (env vars, API keys)
├── app/db/
│   ├── base.py                     # SQLAlchemy Base
│   └── session.py                  # DB engine and SessionLocal
├── celery_app.py                    # Celery app import
└── requirements.txt                 # Python dependencies

frontend/
├── src/
│   ├── lib/
│   │   ├── api.ts                  # Axios client and TypeScript interfaces
│   │   └── geo.ts                  # GEO-specific types and utilities
│   ├── pages/
│   │   ├── Dashboard.tsx           # Main analytics dashboard
│   │   ├── Runs.tsx                # Runs list with filters
│   │   ├── RunDetail.tsx           # Individual run details
│   │   ├── Monitors.tsx            # Monitor management
│   │   ├── Projects.tsx            # Project management
│   │   ├── Subprojects.tsx         # Subproject management
│   │   ├── Templates.tsx           # Prompt template library
│   │   ├── IMMetricsDashboard.tsx  # IM-SEO/IM-SEOIA dashboard
│   │   ├── GEOdashboard.tsx        # GEO metrics dashboard
│   │   └── Insights.tsx            # AI-generated insights
│   ├── components/                 # Reusable UI components
│   └── main.tsx                    # React app entry point
├── vite.config.ts                   # Vite config with /api proxy
└── package.json                     # Node.js dependencies
```

## Development Patterns

### Engine Adapter Pattern
Each LLM/SERP engine implements the base adapter interface from `backend/app/services/adapters/base.py`:
- `fetch()`: Calls the external API and returns `RawEvidence`
- `parse()`: Extracts structured data into `ParsedAnswer`
- `normalize()`: Normalizes data formats
- `extract_citations()`: Extracts citations/sources

Adapters run in isolated subprocesses via `engine_runner.py` with hard timeouts to prevent hangs from blocking SDK calls.

### Adding New Fields (E2E Example)
1. **Database Model**: Add column to `backend/app/models/models.py` (e.g., `Run` model)
2. **Schema Migration**: Add migration statement to `backend/app/main.py` startup event:
   - SQLite: `add_column_if_not_exists(table, column, type)`
   - PostgreSQL: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...`
   - SQL Server: `IF NOT EXISTS (...) BEGIN ALTER TABLE ... END`
3. **Pydantic Schemas**: Update schemas in `backend/app/schemas/schemas.py`
4. **API Routes**: Update endpoints in `backend/app/api/*.py`
5. **Frontend Types**: Mirror types in `frontend/src/lib/api.ts`
6. **UI Components**: Update relevant React components in `frontend/src/pages/` or `frontend/src/components/`

### Database Changes
- **No Alembic**: Uses manual schema updates in `main.py` startup event
- **Multi-DB Support**: SQLite (dev), SQL Server/Azure SQL (prod), PostgreSQL (supported)
- **Schema Updates**: Add dialect-specific migrations to `on_startup()` in `main.py`:
  - SQLite uses helper function `add_column_if_not_exists()`
  - PostgreSQL uses `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
  - SQL Server uses `IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS ...) BEGIN ... END`
- **Important Tables**:
  - `runs`: Main table with 100+ columns for metrics (IM-SEO, GEO, zero-click classification)
  - `citations`: LLM citations with `is_ours` flag for domain tracking
  - `serp_features`: SERP feature detection (PAA, Knowledge Panel, AI Overview, etc.)
  - `entities`: Named entities extracted from content
  - `run_semantic_insights`: Gemini-generated semantic analysis (JSON payload)
  - `domain_variants`: Maps variant domains to canonical (e.g., ourocard.com.br → bb.com.br)
  - `url_metadata`: Crawled URL metadata (title, OG tags, llms.txt, ai.txt, robots.txt)

### API Development
- **Prefix**: All API routes use `/api` prefix
- **Streaming**: SSE for real-time updates with polling fallback
- **Async Jobs**: Route long-running tasks to Celery queue `runs`

### Frontend Development
- **Dev Proxy**: Vite proxies `/api` calls to `localhost:8000` (or `VITE_PROXY_TARGET` env var)
- **Styling**: Tailwind CSS with dark mode support, shadcn/ui components (Radix UI)
- **Real-time**: SSE streaming (`EventSource`) with automatic polling fallback
- **Charts**: Recharts for analytics visualizations
- **State Management**: React hooks (no Redux/Zustand - API calls via axios)

## Environment Setup

Required environment variables in `.env`:
```bash
# LLM API Keys (optional - engines will be skipped if missing)
PERPLEXITY_API_KEY=...
GOOGLE_API_KEY=...          # For Gemini
OPENAI_API_KEY=...
SERPAPI_KEY=...             # Fallback for SERP scraping
PAGESPEED_API_KEY=...       # For Core Web Vitals metrics

# Database (auto-configured by Docker Compose in dev)
DATABASE_URL=sqlite:////app/data/app.db  # Dev default
# DATABASE_URL=mssql+pyodbc://...         # Production (Azure SQL)
REDIS_URL=redis://redis:6379/0

# Application
SECRET_KEY=devsecret        # Change in production
```

## External Integrations

### LLM/Search Engine Adapters
Located in `backend/app/services/adapters/`:
- **Gemini** (`gemini.py`): Google Gemini API with `google_search` grounding, citation extraction
- **OpenAI** (`openai_adapter.py`): ChatGPT API, URL extraction via regex patterns
- **Perplexity** (`perplexity.py`): Perplexity API with native citation support
- **Google SERP** (`google_serp.py`): Playwright-based scraping for organic results, SERP features (PAA, Knowledge Panel, AI Overview), with SerpAPI fallback
- **Sandbox** (`sandbox.py`): Mock adapter for testing/demos

### Google Services
- **Search Console**: OAuth 2.0 flow with token encryption, query analytics, URL inspection
- **PageSpeed Insights**: Core Web Vitals (LCP, FID, CLS) for IM-SEO metrics

### SERP Scraping
- **Primary**: Playwright (Chromium headless) - detects PAA, Knowledge Panels, AI Overviews, Featured Snippets
- **Fallback**: SerpAPI when Playwright fails or times out

## Key Features & Metrics

### IM-SEO/IM-SEOIA (Intent-Matched SEO for AI)
Calculated in `backend/app/services/im_metrics_simple.py`:
- **Performance**: Core Web Vitals (LCP, FID, CLS) from PageSpeed Insights
- **Traffic**: Share of Voice (SoV) in SERP, SERP features presence
- **AI Readiness**: E-E-A-T scores, entity detection, schema coverage, AI-ready content blocks (FAQs, lists, tables)
- **Zero-Click Risk**: IRZC score (CTR expected vs real)
- **Composite Scores**: IM-SEO (0-100), IM-SEOIA (0-100)

### GEO (Generative Engine Optimization)
Calculated in `backend/app/services/geo_metrics.py` - **LLM-only metrics**:
- **Brand Presence**: Mention count, first mention position, mention density, prominence score
- **Citation Quality**: Citation rate (observed/corrected), first citation position, quality score
- **Competitive Intelligence**: Competitor mention ratio, share of voice (LLM), co-citation analysis
- **Engagement**: Conversational triggers, engagement score
- **Advanced**: Zero-click presence, authority, relevance, clarity, conversion potential

### Zero-Click Classification
AI-powered classification of LLM responses:
- **Response Type**: direct, explanatory, instructional, comparative, consultive, navigational
- **Sufficiency Level**: total, partial, insufficient
- **Actionability**: transactional, informational
- **Trust Source**: cited, generic
- **Brand Positioning**: protagonist, competitor, absent
- **Funnel Stage**: awareness, consideration, conversion

### Monitors & Scheduling
- **Cron-based**: Define monitors with cron schedules (e.g., "0 9 * * *")
- **Template Libraries**: Reusable prompt templates with categories, intents, personas
- **Subprojects**: Organize runs by subproject for better segmentation
- **Automated Runs**: Scheduler runs in background thread, creates runs via Celery

### AI Optimization Files
The system detects and crawls special AI/LLM optimization files:
- **llms.txt**: Machine-readable site structure for LLMs (emerging standard)
- **ai.txt**: AI-specific instructions and content hints
- **robots.txt**: Full robots.txt content for AI crawler detection
- Stored in `url_metadata` table and used for AI-readiness scoring

### Domain Variants & Citation Consolidation
The `domain_variants` table maps related domains to a canonical domain:
- **Use Case**: Track bb.com.br, bancodobrasil.com.br, ourocard.com.br → "Banco do Brasil"
- **Impact**: Consolidates citation counts across brand variants
- **GEO Metrics**: `citation_rate_corrected` adjusts for variant consolidation

## Testing and Quality

- **API Documentation**: Available at `http://localhost:8000/docs` (Swagger)
- **Health Check**: `GET /health`
- **Frontend Linting**: `npm run lint` in `frontend/`
- **No formal backend tests** - relies on manual testing through Docker setup

## Production Deployment (Oracle Cloud Infrastructure)

### OCI Instance Information
```
Instance ID:  ocid1.instance.oc1.sa-saopaulo-1.antxeljrjnucp5yctmlmdargt5byzjce2dfdouwnuncrwu7kcl2ie2zmp7ba
Display Name: instance-20250825-1241
Public IP:    129.148.63.199
Private IP:   10.0.0.197
Region:       sa-saopaulo-1
SSH Key:      /Users/hrocha/Documents/SSH Oracle/oci_ed25519
SSH User:     ubuntu
```

### OCI CLI Configuration
```bash
# OCI CLI config location: ~/.oci/config
User OCID:    ocid1.user.oc1..aaaaaaaa3b7gtiinwmcgo5zeqaqa7grk4je4zwmgi2ykkxyz73wih4memgnq
Tenancy OCID: ocid1.tenancy.oc1..aaaaaaaab3khzlpcurua4ba3fh4q6uthyjz7iw52tltgfv5g3ltg2ciycw3a
Fingerprint:  40:46:e0:0d:18:5e:ab:bd:ad:ec:b9:e9:56:54:cd:2a
```

### Deployment Commands
```bash
# Connect to production server
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199

# Deploy application
cd /opt/seo-analyzer
docker compose -f docker-compose.prod.yml up -d --build

# Check deployment status
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
```

### OCI Resource Management
```bash
# List instances
TENANCY_ID="ocid1.tenancy.oc1..aaaaaaaab3khzlpcurua4ba3fh4q6uthyjz7iw52tltgfv5g3ltg2ciycw3a"
oci compute instance list --compartment-id $TENANCY_ID --output table

# Instance management
INSTANCE_ID="ocid1.instance.oc1.sa-saopaulo-1.antxeljrjnucp5yctmlmdargt5byzjce2dfdouwnuncrwu7kcl2ie2zmp7ba"
oci compute instance get --instance-id $INSTANCE_ID --output json
oci compute instance action --action START --instance-id $INSTANCE_ID
oci compute instance action --action STOP --instance-id $INSTANCE_ID
```

### Security Groups & Network
```bash
# Current open ports on OCI Security List:
# - 22 (SSH)
# - 80 (HTTP)
# - 443 (HTTPS)
# - 5678 (n8n)
# - 8000 (API - if needed)
# - 8080 (Evolution API)

SECURITY_LIST_ID="ocid1.securitylist.oc1.sa-saopaulo-1.aaaaaaaaz2qvoojbladmbw75s5kep6assbhoi5frk2r6yaid7dybn653ut7a"
oci network security-list get --security-list-id $SECURITY_LIST_ID --output json
```

## Common Troubleshooting

### Development
- **Frontend hot-reload issues**: `docker compose restart frontend`
- **Playwright slow first install**: Check backend logs for Chromium download (~100MB)
- **SSE connection issues**: UI automatically falls back to polling
- **Port conflicts**: Modify `docker-compose.yml` port mappings (default: 5173, 8000, 6379)
- **Celery worker not processing**: Check `docker compose logs -f worker` and Redis connectivity
- **Database locked (SQLite)**: Restart backend service or use separate read/write sessions

### Production
- **OCI SSH access**: Ensure SSH key permissions are 600: `chmod 600 "/Users/hrocha/Documents/SSH Oracle/oci_ed25519"`
- **Production deployment issues**: Check OCI instance status and security group rules
- **Azure SQL timeouts**: Check connection string and firewall rules in Azure portal
- **Missing API keys**: Some engines will be skipped if keys are not configured (check logs)