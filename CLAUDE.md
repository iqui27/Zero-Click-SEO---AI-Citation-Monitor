# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zero-Click SEO & AI Citation Monitor - A FastAPI/React application that monitors AI citations and SERP data across multiple engines (Gemini, OpenAI, Perplexity, Google SERP). Features real-time monitoring with scheduling, analytics dashboards, and CSV exports.

## Development Commands

### Docker Compose (Recommended)
```bash
# Start all services (API, Worker, Frontend, DB, Redis)
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
```

### Backend Development
```bash
cd backend
# Dependencies in requirements.txt
# No manual testing commands defined - relies on Docker setup
```

## Architecture

### Stack
- **Backend**: FastAPI + SQLAlchemy + Celery + Redis
- **Frontend**: React + Vite + Tailwind CSS (with dark mode)
- **Database**: PostgreSQL (with SQL Server/Azure SQL support)
- **External APIs**: OpenAI, Gemini, Perplexity, SerpAPI, Playwright for SERP scraping

### Service Communication
- Frontend → FastAPI API (via `/api` prefix)
- Long-running tasks → Celery worker (queue: `runs`)
- Real-time updates → SSE streaming (`/api/runs/{id}/stream`) with polling fallback
- Database migrations → Manual schema updates in `backend/app/main.py` startup

### Key File Structure
```
backend/
├── app/main.py              # FastAPI app, CORS, startup migrations, scheduler
├── app/api/routes.py        # API route definitions
├── app/models/models.py     # SQLAlchemy models
├── app/schemas/schemas.py   # Pydantic schemas
├── app/core/config.py       # Settings and environment variables
├── celery_app.py           # Celery configuration
└── requirements.txt        # Python dependencies

frontend/
├── src/lib/api.ts          # API client and TypeScript types
├── src/pages/Runs.tsx      # Runs list interface
├── src/pages/RunDetail.tsx # Run details interface
└── package.json           # Node.js dependencies
```

## Development Patterns

### Adding New Fields (E2E Example)
1. **Database Model**: Add column to `backend/app/models/models.py`
2. **Schema Migration**: Add `ALTER TABLE IF NOT EXISTS` statement to `backend/app/main.py` startup
3. **Pydantic Schemas**: Update schemas in `backend/app/schemas/schemas.py`
4. **API Routes**: Update endpoints in `backend/app/api/routes.py`
5. **Frontend Types**: Mirror types in `frontend/src/lib/api.ts`
6. **UI Components**: Update relevant React components

### Database Changes
- **No Alembic**: Uses manual schema updates in `main.py` startup
- **Multi-DB Support**: PostgreSQL primary, SQL Server/Azure SQL compatibility
- **Schema Updates**: Add new `ALTER TABLE IF NOT EXISTS` statements to startup migration list

### API Development
- **Prefix**: All API routes use `/api` prefix
- **Streaming**: SSE for real-time updates with polling fallback
- **Async Jobs**: Route long-running tasks to Celery queue `runs`

### Frontend Development
- **Dev Proxy**: Vite proxies `/api` calls to `:8000`
- **Styling**: Tailwind CSS with dark mode support
- **Real-time**: SSE streaming with automatic polling fallback

## Environment Setup

Required environment variables in `.env`:
```bash
# API Keys (optional but recommended)
PERPLEXITY_API_KEY=...
GOOGLE_API_KEY=...
OPENAI_API_KEY=...
SERPAPI_KEY=...

# Database (provided by Docker Compose)
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

## External Integrations

### LLM Adapters
- **Gemini**: Uses `google_search` tools with fallbacks
- **OpenAI**: URL extraction via regex
- **Perplexity**: Collects citations and search results

### SERP Collection
- **Primary**: Playwright (Chromium headless)
- **Fallback**: SerpAPI when Playwright fails

## Testing and Quality

- **API Documentation**: Available at `http://localhost:8000/docs` (Swagger)
- **Health Check**: `GET /health`
- **No formal test commands defined** - relies on manual testing through Docker setup

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

- **Frontend hot-reload issues**: `docker compose restart frontend`
- **Playwright slow first install**: Check backend logs for Chromium download
- **SSE connection issues**: UI automatically falls back to polling
- **Port conflicts**: Modify `docker-compose.yml` port mappings
- **OCI SSH access**: Ensure SSH key permissions are 600: `chmod 600 "/Users/hrocha/Documents/SSH Oracle/oci_ed25519"`
- **Production deployment issues**: Check OCI instance status and security group rules