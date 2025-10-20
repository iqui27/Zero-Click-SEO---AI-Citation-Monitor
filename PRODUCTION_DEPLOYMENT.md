# Production Deployment Guide

## Overview

This guide covers deploying the Zero-Click SEO & AI Citation Monitor to production on Oracle Cloud Infrastructure (OCI).

## Prerequisites

- OCI instance running Ubuntu (instance-20250825-1241)
- Docker and Docker Compose installed
- SSL certificates (Cloudflare)
- Domain configured (iqui27.app)

## Quick Start

### 1. Connect to Production Server

```bash
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199
```

### 2. Clone/Update Repository

```bash
cd /opt
sudo git clone <repository-url> seo-analyzer
cd seo-analyzer
```

### 3. Configure Environment

```bash
# Copy production template
cp .env.production.template .env

# Edit with your actual credentials
nano .env
```

**Required configurations:**
- `SECRET_KEY`: Generate a secure random key
- `DATABASE_URL`: Your Azure SQL or PostgreSQL connection string
- `ALLOWED_ORIGINS`: Your domain(s)
- API keys for LLM services

### 4. Build and Deploy

```bash
# Build optimized production images
docker compose -f docker-compose.prod.yml build --no-cache

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

## Architecture

### Services

1. **reverse-proxy** (Nginx)
   - Handles HTTPS/TLS termination
   - Static file serving
   - API proxying
   - Rate limiting
   - Security headers

2. **api** (FastAPI + Uvicorn)
   - REST API endpoints
   - Database migrations
   - Scheduler for monitors
   - Non-root user (appuser)
   - Health checks

3. **worker** (Celery)
   - Background task processing
   - LLM API calls
   - SERP scraping
   - Metrics calculation

4. **redis**
   - Message broker for Celery
   - Task result backend
   - Caching layer
   - Persistence enabled

### Network

- **public_net**: Internet-facing (Nginx)
- **internal_net**: Backend services (API, Worker, Redis)

### Volumes

- **redis_data**: Redis persistence
- **app_data**: Application data (SQLite fallback)
- **nginx_logs**: Nginx access/error logs

## Optimization Features

### Backend

✅ **Security**
- Non-root user in containers
- Security headers (HSTS, CSP, X-Frame-Options)
- CORS properly configured
- Environment-based debug mode
- Secret management via environment

✅ **Performance**
- Connection pooling (configurable per environment)
- SQLite optimizations (WAL mode, cache tuning)
- GZip compression
- Structured logging (JSON in production)
- Request/response logging with timing

✅ **Reliability**
- Health checks on all services
- Graceful shutdown handling
- Database migration on startup
- Automatic retry for broker connections
- Task acknowledgment after execution

### Celery Workers

✅ **Configuration**
- Optimized prefetch multiplier (4)
- Worker lifecycle management (1000 tasks/child)
- Retry policies with exponential backoff
- Task routing and queues
- Monitoring via signals

✅ **Task Management**
- Soft/hard time limits
- Automatic retries on failure
- Dead letter queue support
- Task result expiration (24h)
- Connection keep-alive

### Docker

✅ **Multi-stage Build**
- Separate builder stage
- Production stage (minimal)
- Development stage (with tools)
- Layer caching optimization
- Reduced image size (~40% smaller)

✅ **Security**
- Non-root user (UID 1000)
- Minimal runtime dependencies
- No build tools in production image
- Read-only file systems where possible

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Nginx health
curl http://localhost/health

# Worker status
docker compose -f docker-compose.prod.yml exec worker \
  celery -A celery_app.celery_app inspect ping
```

### Logs

```bash
# Follow all logs
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f worker
docker compose -f docker-compose.prod.yml logs -f redis

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100
```

### Metrics

```bash
# Container stats
docker stats

# Redis stats
docker compose -f docker-compose.prod.yml exec redis redis-cli INFO stats

# Database connections (if using PostgreSQL)
docker compose -f docker-compose.prod.yml exec api \
  python -c "from app.db.session import engine; print(engine.pool.status())"
```

## Maintenance

### Update Application

```bash
cd /opt/seo-analyzer

# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

# Check for issues
docker compose -f docker-compose.prod.yml logs -f
```

### Database Backup (Azure SQL)

```bash
# Automated backup via Azure Portal
# Or use Azure CLI:
az sql db export \
  --resource-group <resource-group> \
  --server <server-name> \
  --name <database-name> \
  --storage-uri <blob-storage-uri> \
  --storage-key <storage-key> \
  --administrator-login <admin-user> \
  --administrator-login-password <password>
```

### Redis Persistence

Redis is configured with AOF (append-only file):
- Automatic persistence every second
- Data survives restarts
- Volume: `redis_data`

### Clean Up

```bash
# Remove old images
docker image prune -a

# Remove unused volumes
docker volume prune

# Full cleanup (CAREFUL - removes all unused data)
docker system prune -a --volumes
```

## Performance Tuning

### Database

**Azure SQL:**
- Use appropriate tier (Standard S3+ for production)
- Enable Query Performance Insights
- Configure connection pooling: 20-40 connections

**PostgreSQL:**
```sql
-- Recommended settings
max_connections = 100
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
```

### Redis

Current configuration:
- Max memory: 256MB
- Policy: allkeys-lru
- Persistence: AOF

For higher load:
```bash
# Edit docker-compose.prod.yml
command: ["redis-server", "--appendonly", "yes", "--maxmemory", "512mb", "--maxmemory-policy", "allkeys-lru"]
```

### Uvicorn Workers

For multi-core systems, increase workers:

```yaml
# docker-compose.prod.yml
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Rule of thumb:** `(2 x num_cores) + 1`

### Celery Workers

For higher throughput:

```yaml
# docker-compose.prod.yml
command: bash -lc "celery -A celery_app.celery_app worker -Q runs -l info --concurrency=8"
```

## Troubleshooting

### API Not Responding

```bash
# Check API logs
docker compose -f docker-compose.prod.yml logs api

# Check API health
docker compose -f docker-compose.prod.yml exec api curl localhost:8000/health

# Restart API
docker compose -f docker-compose.prod.yml restart api
```

### Worker Not Processing Tasks

```bash
# Check worker logs
docker compose -f docker-compose.prod.yml logs worker

# Check Redis connection
docker compose -f docker-compose.prod.yml exec worker \
  celery -A celery_app.celery_app inspect active

# Restart worker
docker compose -f docker-compose.prod.yml restart worker
```

### Database Connection Issues

```bash
# Test connection
docker compose -f docker-compose.prod.yml exec api \
  python -c "from app.db.session import engine; engine.connect()"

# Check pool status
docker compose -f docker-compose.prod.yml exec api \
  python -c "from app.db.session import engine; print(engine.pool.status())"
```

### High Memory Usage

```bash
# Check container stats
docker stats

# Reduce worker concurrency
# Edit docker-compose.prod.yml worker command:
command: bash -lc "celery -A celery_app.celery_app worker -Q runs -l info --concurrency=2"

# Restart services
docker compose -f docker-compose.prod.yml restart worker
```

## Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Configure ALLOWED_ORIGINS to specific domains
- [ ] Use strong database passwords
- [ ] Enable firewall on OCI (ports 80, 443 only)
- [ ] Keep SSL certificates up to date
- [ ] Regularly update Docker images
- [ ] Monitor logs for suspicious activity
- [ ] Enable Azure SQL firewall rules
- [ ] Use Azure Key Vault for secrets (optional)
- [ ] Configure backup retention policies

## Rollback Procedure

If deployment fails:

```bash
# Stop new containers
docker compose -f docker-compose.prod.yml down

# Revert code
git reset --hard <previous-commit>

# Rebuild and start
docker compose -f docker-compose.prod.yml up -d --build
```

## Support

For issues or questions:
- Check logs: `docker compose -f docker-compose.prod.yml logs -f`
- Review this documentation
- Check GitHub issues: https://github.com/anthropics/claude-code/issues

## Performance Benchmarks

Expected performance on OCI instance:
- API response time: < 200ms (p95)
- Background task processing: 10-20 runs/minute
- Database queries: < 100ms (p95)
- Memory usage: ~2GB total
- CPU usage: 20-40% under normal load
