# SEO Analyzer - Production Deployment

This document provides comprehensive instructions for deploying and managing the SEO Analyzer application in a production environment.

## Production Architecture

The production deployment uses the following stack:
- **Reverse Proxy**: Caddy (automatic HTTPS/TLS)
- **Frontend**: Nginx serving static React build
- **Backend API**: FastAPI with Gunicorn
- **Worker**: Celery for background tasks
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Container Orchestration**: Docker Compose

## Production URL

🌐 **Live Application**: https://zero-click.iqui27.codes

## Prerequisites

### Local Machine
- **Docker**: Version 28.3.2 or higher
- **Docker Compose**: v2 or higher
- **Node.js**: Version 18 or higher (for building frontend)
- **Git**: Latest version
- **SSH Client**: For server access

### Production Server
- **DigitalOcean Droplet** (or compatible VPS)
- **Ubuntu 22.04 LTS** (recommended)
- **Minimum 2GB RAM, 2 vCPUs**
- **Docker and Docker Compose installed**
- **Domain name** pointing to server IP

## Server Information

### Current Production Server
- **Provider**: DigitalOcean
- **IP Address**: `198.211.98.85`
- **Domain**: `zero-click.iqui27.codes`
- **OS**: Ubuntu 22.04 LTS
- **Access**: SSH with root user

## Initial Server Setup

### 1. Server Preparation

Connect to the server:
```bash
ssh root@198.211.98.85
```

Update the system:
```bash
apt update && apt upgrade -y
```

### 2. Install Docker

```bash
# Install Docker using official script
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Enable and start Docker
systemctl enable docker
systemctl start docker

# Verify installation
docker --version
docker compose version
```

### 3. Create Application Directory

```bash
mkdir -p /opt/seo-analyzer
cd /opt/seo-analyzer
```

## Deployment Process

### 1. Local Preparation

#### Build Frontend Assets
```bash
cd frontend
pnpm install
pnpm build
```

This creates the `dist/` directory with production-ready static files.

#### Prepare Environment File
Create a production `.env` file:
```bash
cp .env.example .env.prod
```

Edit `.env.prod` with production values:
```env
# Production Database Configuration
POSTGRES_DB=seo_analyzer_prod
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_production_password
DATABASE_URL=postgresql://postgres:your_secure_production_password@postgres:5432/seo_analyzer_prod

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# API Configuration
API_SECRET_KEY=your-super-secure-production-secret-key-min-32-chars
API_DEBUG=false
API_CORS_ORIGINS=["https://zero-click.iqui27.codes"]

# Production API Keys
OPENAI_API_KEY=sk-your-production-openai-api-key
SERP_API_KEY=your-production-serp-api-key
GOOGLE_API_KEY=your-production-google-api-key
GOOGLE_CSE_ID=your-production-google-cse-id

# Production URLs
FRONTEND_URL=https://zero-click.iqui27.codes
API_URL=https://zero-click.iqui27.codes/api
DOMAIN=zero-click.iqui27.codes
```

### 2. Upload Project Files

#### Using rsync (Recommended)
```bash
# From local project root
rsync -avz --exclude 'node_modules' --exclude '.git' --exclude '__pycache__' \
  ./ root@198.211.98.85:/opt/seo-analyzer/
```

#### Using scp (Alternative)
```bash
# Upload project files
scp -r ./* root@198.211.98.85:/opt/seo-analyzer/

# Upload environment file
scp .env.prod root@198.211.98.85:/opt/seo-analyzer/.env
```

### 3. Deploy on Server

Connect to the server and navigate to project directory:
```bash
ssh root@198.211.98.85
cd /opt/seo-analyzer
```

#### Start the Production Stack
```bash
# Deploy all services
docker compose -f docker-compose.prod.yml --env-file .env up -d --build

# Check service status
docker compose -f docker-compose.prod.yml ps
```

#### Verify Deployment
```bash
# Check all services are healthy
docker compose -f docker-compose.prod.yml ps

# Check logs
docker compose -f docker-compose.prod.yml logs -f

# Test API health
curl -k https://zero-click.iqui27.codes/api/health

# Test frontend
curl -k https://zero-click.iqui27.codes/
```

## Production Services Configuration

### Caddy (Reverse Proxy)
- **Configuration**: `Caddyfile`
- **Automatic HTTPS**: Via Let's Encrypt
- **Port**: 80, 443
- **Features**: 
  - Automatic TLS certificate generation and renewal
  - HTTP to HTTPS redirection
  - Static file serving
  - API reverse proxying

### Frontend (Nginx)
- **Configuration**: `nginx-default.conf`
- **Port**: Internal 80
- **Serves**: Static React build from `dist/`
- **Features**: 
  - Gzip compression
  - Cache headers for assets
  - SPA routing support

### API (FastAPI)
- **Port**: Internal 8000
- **Production Server**: Gunicorn with multiple workers
- **Health Check**: `/health` endpoint
- **Features**: 
  - JWT authentication
  - OpenAPI documentation at `/docs`
  - Background task queuing

### Worker (Celery)
- **Purpose**: Background task processing
- **Broker**: Redis
- **Tasks**: 
  - SEO analysis jobs
  - Report generation
  - Data processing

### Database (PostgreSQL)
- **Version**: 15
- **Port**: Internal 5432
- **Features**: 
  - Persistent data storage
  - Automated backups (configured separately)
  - Connection pooling

### Cache (Redis)
- **Version**: 7
- **Port**: Internal 6379
- **Usage**: 
  - Celery task broker
  - API response caching
  - Session storage

## Domain and SSL Configuration

### Domain Setup
1. Domain `zero-click.iqui27.codes` points to `198.211.98.85`
2. DNS A record configured
3. Caddy automatically obtains SSL certificate from Let's Encrypt

### SSL Certificate Management
- **Automatic**: Caddy handles certificate issuance and renewal
- **Certificate Location**: Inside Caddy container
- **Renewal**: Automatic every 60 days
- **Backup**: Not needed (automatic re-issuance)

## Environment Variables (Production)

| Variable | Production Value | Description |
|----------|------------------|-------------|
| `POSTGRES_DB` | `seo_analyzer_prod` | Production database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `[SECURE_PASSWORD]` | Strong production password |
| `DATABASE_URL` | `postgresql://postgres:[PASSWORD]@postgres:5432/seo_analyzer_prod` | Full database connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `API_SECRET_KEY` | `[SECURE_32_CHAR_KEY]` | JWT signing key |
| `API_DEBUG` | `false` | Disable debug mode |
| `API_CORS_ORIGINS` | `["https://zero-click.iqui27.codes"]` | CORS allowed origins |
| `OPENAI_API_KEY` | `sk-[PRODUCTION_KEY]` | Production OpenAI API key |
| `SERP_API_KEY` | `[PRODUCTION_KEY]` | Production SERP API key |
| `GOOGLE_API_KEY` | `[PRODUCTION_KEY]` | Production Google API key |
| `GOOGLE_CSE_ID` | `[PRODUCTION_ID]` | Production Google CSE ID |
| `FRONTEND_URL` | `https://zero-click.iqui27.codes` | Frontend URL |
| `API_URL` | `https://zero-click.iqui27.codes/api` | API URL |
| `DOMAIN` | `zero-click.iqui27.codes` | Primary domain |

## Production Monitoring

### Service Health Checks
```bash
# Check all container status
docker compose -f docker-compose.prod.yml ps

# Check service logs
docker compose -f docker-compose.prod.yml logs [service_name]

# Monitor real-time logs
docker compose -f docker-compose.prod.yml logs -f
```

### Application Health Endpoints
- **API Health**: `https://zero-click.iqui27.codes/api/health`
- **Frontend**: `https://zero-click.iqui27.codes/`
- **API Docs**: `https://zero-click.iqui27.codes/api/docs`

### System Resources
```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check CPU usage
top

# Check Docker resource usage
docker stats
```

## Update Procedures

### 1. Application Updates

#### Frontend Updates
```bash
# Local machine - build new frontend
cd frontend
pnpm build

# Upload new build
rsync -avz dist/ root@198.211.98.85:/opt/seo-analyzer/dist/

# Restart frontend service
ssh root@198.211.98.85 "cd /opt/seo-analyzer && docker compose -f docker-compose.prod.yml restart frontend"
```

#### Backend Updates
```bash
# Upload backend changes
rsync -avz --exclude '__pycache__' backend/ root@198.211.98.85:/opt/seo-analyzer/backend/

# Rebuild and restart API and worker
ssh root@198.211.98.85 "cd /opt/seo-analyzer && docker compose -f docker-compose.prod.yml up -d --build api worker"
```

#### Full Application Update
```bash
# Upload all changes
rsync -avz --exclude 'node_modules' --exclude '.git' --exclude '__pycache__' \
  ./ root@198.211.98.85:/opt/seo-analyzer/

# Rebuild and restart all services
ssh root@198.211.98.85 "cd /opt/seo-analyzer && docker compose -f docker-compose.prod.yml up -d --build"
```

### 2. Rollback Procedures

#### Quick Rollback
```bash
# Stop current deployment
docker compose -f docker-compose.prod.yml down

# Restore from backup
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps
```

## Backup Procedures

### 1. Database Backup

#### Manual Backup
```bash
# Create backup
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres seo_analyzer_prod > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Automated Backup (Cron)
```bash
# Add to crontab
0 2 * * * cd /opt/seo-analyzer && docker compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres seo_analyzer_prod > /opt/backups/db_$(date +\%Y\%m\%d_\%H\%M\%S).sql
```

### 2. File System Backup

#### Application Files
```bash
# Backup entire application
tar -czf seo-analyzer-backup-$(date +%Y%m%d).tar.gz /opt/seo-analyzer
```

#### DigitalOcean Snapshots
```bash
# Create droplet snapshot via DigitalOcean API or dashboard
# Recommended: Weekly automated snapshots
```

## Security Considerations

### 1. Server Security
- **Firewall**: Only ports 80, 443, 22 open
- **SSH**: Key-based authentication recommended
- **Updates**: Regular security updates
- **Monitoring**: Failed login attempts

### 2. Application Security
- **HTTPS**: Enforced via Caddy
- **API Keys**: Stored in environment variables
- **Database**: Internal network only
- **CORS**: Restricted to production domain

### 3. Data Protection
- **Backups**: Regular automated backups
- **Encryption**: TLS in transit, database encryption at rest
- **Access Control**: Limited server access

## Performance Optimization

### 1. Application Performance
- **Frontend**: Static file caching, Gzip compression
- **API**: Connection pooling, Redis caching
- **Database**: Proper indexing, query optimization
- **Workers**: Scaled based on task volume

### 2. Infrastructure Performance
- **CDN**: Consider adding CloudFlare for global performance
- **Database**: Separate database server for scale
- **Load Balancing**: Multiple API instances for high load

## Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs [service_name]

# Check configuration
docker compose -f docker-compose.prod.yml config

# Restart service
docker compose -f docker-compose.prod.yml restart [service_name]
```

#### SSL Certificate Issues
```bash
# Check Caddy logs
docker compose -f docker-compose.prod.yml logs reverse-proxy

# Force certificate renewal
docker compose -f docker-compose.prod.yml exec reverse-proxy caddy reload
```

#### Database Connection Issues
```bash
# Check database status
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# Check connection from API
docker compose -f docker-compose.prod.yml exec api python -c "import psycopg2; print('DB OK')"
```

#### High Resource Usage
```bash
# Check resource usage
docker stats

# Scale workers if needed
docker compose -f docker-compose.prod.yml up -d --scale worker=3
```

### Log Locations
- **Application Logs**: `docker compose logs`
- **System Logs**: `/var/log/`
- **Nginx Logs**: Inside nginx container
- **Database Logs**: Inside postgres container

## Disaster Recovery

### 1. Complete Server Failure
1. Provision new server
2. Restore from DigitalOcean snapshot
3. Update DNS if IP changed
4. Verify all services

### 2. Database Corruption
1. Stop application
2. Restore database from backup
3. Restart services
4. Verify data integrity

### 3. Certificate Issues
1. Caddy automatically handles renewal
2. If manual intervention needed:
   ```bash
   docker compose -f docker-compose.prod.yml restart reverse-proxy
   ```

## Maintenance Schedule

### Daily
- Monitor service status
- Check error logs
- Verify backups completed

### Weekly
- Update system packages
- Review resource usage
- Test backup restoration
- Create system snapshot

### Monthly
- Security audit
- Performance review
- Update application dependencies
- Review and rotate API keys if needed

## Support and Monitoring

### External Monitoring
- **Uptime Monitoring**: UptimeRobot, Pingdom, or similar
- **Performance Monitoring**: Consider APM tools
- **Log Aggregation**: ELK stack or similar for large scale

### Alerts
- Service downtime
- High resource usage
- Failed backups
- Certificate expiration warnings

## Contact and Emergency

For production issues:
1. Check service status: `docker compose -f docker-compose.prod.yml ps`
2. Review logs: `docker compose -f docker-compose.prod.yml logs -f`
3. Follow troubleshooting procedures above
4. For critical issues, refer to disaster recovery procedures

## Additional Resources

- **MAINTENANCE.md**: Detailed operational procedures
- **DEVELOPMENT.md**: Development environment setup
- **API Documentation**: https://zero-click.iqui27.codes/api/docs
- **DigitalOcean Dashboard**: Server management and monitoring
