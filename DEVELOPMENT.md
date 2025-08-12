# SEO Analyzer - Development Environment

This document provides instructions for setting up and running the SEO Analyzer application in a development environment.

## Prerequisites

- **Docker**: Version 28.3.2 or higher
- **Docker Compose**: v2 or higher
- **Node.js**: Version 18 or higher
- **npm/pnpm**: Latest version
- **Git**: Latest version

## Project Structure

```
SEO Analyzer/
├── backend/              # FastAPI backend service
├── frontend/             # Vite + React frontend
├── dist/                 # Built frontend assets
├── nginx-default.conf    # Nginx configuration for production
├── Caddyfile            # Caddy reverse proxy configuration
├── docker-compose.yml   # Development Docker Compose
├── docker-compose.prod.yml  # Production Docker Compose
├── .env.example         # Environment variables template
└── scripts/             # Utility scripts
```

## Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "SEO Analyzer"
```

### 2. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your development configuration:

```env
# Database Configuration
POSTGRES_DB=seo_analyzer_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_dev_password
DATABASE_URL=postgresql://postgres:your_dev_password@localhost:5432/seo_analyzer_dev

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_SECRET_KEY=your-dev-secret-key-here
API_DEBUG=true
API_CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# External API Keys (development)
OPENAI_API_KEY=your-openai-api-key
SERP_API_KEY=your-serp-api-key
GOOGLE_API_KEY=your-google-api-key
GOOGLE_CSE_ID=your-google-cse-id

# Development URLs
FRONTEND_URL=http://localhost:5173
API_URL=http://localhost:8000
```

### 3. Frontend Development

#### Install Dependencies

```bash
cd frontend
npm install
# or
pnpm install
```

#### Run Development Server

```bash
npm run dev
# or
pnpm dev
```

The frontend will be available at `http://localhost:5173`

#### Build for Production

```bash
npm run build
# or
pnpm build
```

Built assets will be in the `dist/` directory.

### 4. Backend Development

#### Using Docker Compose (Recommended)

Start the development stack:

```bash
docker compose up -d
```

This will start:
- PostgreSQL database on port 5432
- Redis on port 6379
- FastAPI backend on port 8000

#### Manual Setup (Alternative)

If you prefer to run the backend manually:

1. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

2. Start PostgreSQL and Redis locally
3. Run database migrations
4. Start the FastAPI server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Worker Process (Celery)

For background task processing:

```bash
# Using Docker Compose (included in docker compose up)
docker compose up worker

# Or manually
cd backend
celery -A main.celery worker --loglevel=info
```

## Development Workflow

### 1. Daily Development

1. Start the development stack:
```bash
docker compose up -d
```

2. Start the frontend development server:
```bash
cd frontend && npm run dev
```

3. Open `http://localhost:5173` in your browser

### 2. API Development

- API documentation: `http://localhost:8000/docs`
- API health check: `http://localhost:8000/health`
- Database admin (if enabled): `http://localhost:8000/admin`

### 3. Database Management

#### Migrations
```bash
# Apply migrations
docker compose exec api alembic upgrade head

# Create new migration
docker compose exec api alembic revision --autogenerate -m "description"
```

#### Database Access
```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d seo_analyzer_dev
```

### 4. Testing

#### Backend Tests
```bash
cd backend
pytest
```

#### Frontend Tests
```bash
cd frontend
npm test
```

#### Integration Tests
```bash
# Run full test suite
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

## Debugging

### Backend Debugging

1. Enable debug mode in `.env`:
```env
API_DEBUG=true
```

2. Check API logs:
```bash
docker compose logs -f api
```

3. Connect to API container:
```bash
docker compose exec api bash
```

### Frontend Debugging

1. Use browser developer tools
2. Check console logs
3. Use React Developer Tools extension

### Database Debugging

1. Check database logs:
```bash
docker compose logs -f postgres
```

2. Connect to database:
```bash
docker compose exec postgres psql -U postgres -d seo_analyzer_dev
```

## Common Development Tasks

### Reset Development Environment

```bash
# Stop all containers
docker compose down

# Remove volumes (this will delete data!)
docker compose down -v

# Rebuild and start fresh
docker compose up -d --build
```

### Update Dependencies

#### Backend
```bash
cd backend
pip freeze > requirements.txt
```

#### Frontend
```bash
cd frontend
npm update
# or
pnpm update
```

### Code Formatting and Linting

#### Backend
```bash
cd backend
black .
flake8 .
```

#### Frontend
```bash
cd frontend
npm run lint
npm run format
```

## Environment Variables Reference

| Variable | Description | Development Default |
|----------|-------------|-------------------|
| `POSTGRES_DB` | Database name | `seo_analyzer_dev` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `your_dev_password` |
| `DATABASE_URL` | Full database URL | `postgresql://...` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `API_SECRET_KEY` | JWT secret key | Random string |
| `API_DEBUG` | Enable debug mode | `true` |
| `API_CORS_ORIGINS` | CORS allowed origins | `["http://localhost:3000", "http://localhost:5173"]` |
| `OPENAI_API_KEY` | OpenAI API key | Your API key |
| `SERP_API_KEY` | SERP API key | Your API key |
| `GOOGLE_API_KEY` | Google API key | Your API key |
| `GOOGLE_CSE_ID` | Google Custom Search Engine ID | Your CSE ID |

## Troubleshooting

### Port Conflicts
If ports are already in use, update `docker-compose.yml` to use different ports:

```yaml
services:
  postgres:
    ports:
      - "5433:5432"  # Changed from 5432:5432
```

### Docker Issues
```bash
# Clean up Docker resources
docker system prune -a

# Rebuild without cache
docker compose build --no-cache
```

### Permission Issues (macOS/Linux)
```bash
# Fix file permissions
sudo chown -R $(whoami):$(whoami) .
```

### API Connection Issues
- Check if the API is running: `curl http://localhost:8000/health`
- Verify environment variables
- Check Docker container logs

## IDE Setup

### VS Code
Recommended extensions:
- Python
- ES7+ React/Redux/React-Native snippets
- Prettier - Code formatter
- ESLint
- Docker

### PyCharm
- Configure Python interpreter to use the Docker container
- Set up remote debugging if needed

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Run tests: `npm test` and `pytest`
4. Commit with conventional commits: `git commit -m "feat: add new feature"`
5. Push and create a pull request

## Next Steps

- Review the [PRODUCTION.md](./PRODUCTION.md) for deployment instructions
- Check [MAINTENANCE.md](./MAINTENANCE.md) for operational procedures
- See API documentation at `http://localhost:8000/docs` when running
