# SEO Analyzer - Oracle Cloud Deployment Guide

## 🚀 Quick Start

### 1. Manual Deployment
```bash
# Build and deploy manually
./scripts/deploy.sh

# Or step by step
./scripts/deploy.sh build    # Build frontend only
./scripts/deploy.sh deploy   # Deploy to Oracle Cloud
./scripts/deploy.sh verify   # Verify deployment
```

### 2. Automated Deployment (Recommended)

#### Setup GitHub Actions (One-time)
1. Add these secrets to your GitHub repository:
   ```
   ORACLE_SSH_KEY          # Content of /Users/hrocha/Documents/SSH Oracle/oci_ed25519
   POSTGRES_PASSWORD       # Database password (e.g., seo123!@#)
   SECRET_KEY             # Django/FastAPI secret key
   OPENAI_API_KEY         # Your OpenAI API key
   GEMINI_API_KEY         # Your Google Gemini API key
   PERPLEXITY_API_KEY     # Your Perplexity API key
   SERPAPI_KEY            # Your SerpAPI key
   ```

2. Push to `main` branch - deployment happens automatically!

#### Setup Webhook Server (Optional - for instant deployment)
```bash
# On Oracle Cloud server
ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199
cd /opt/seo-analyzer
sudo ./scripts/setup-webhook-service.sh
```

Then configure GitHub webhook:
- URL: `http://129.148.63.199:9000/webhook`
- Content type: `application/json`
- Secret: `seo-analyzer-webhook-2024-secret`
- Events: Just push events

## 🏗️ Architecture

### Production Stack
- **Nginx**: Reverse proxy + static file serving
- **FastAPI**: Backend API (Python/Uvicorn)
- **Celery**: Background task processing
- **PostgreSQL**: Primary database
- **Redis**: Cache + message broker

### Network Configuration
- **Port 80**: HTTP (Nginx)
- **Port 443**: HTTPS (Nginx) 
- **Port 9000**: Webhook server (optional)

## 📁 File Structure

```
/opt/seo-analyzer/                 # Deployment directory
├── docker-compose.prod.yml       # Production Docker setup
├── .env                          # Environment variables
├── frontend/dist/                # Built React app
├── backend/                      # Python API
├── scripts/                      # Deployment scripts
└── deploy/                       # Nginx configuration
```

## 🔧 Management Commands

### Service Management
```bash
# Check status
./scripts/deploy.sh status

# View logs
./scripts/deploy.sh logs

# Restart services
./scripts/deploy.sh restart
```

### Direct Docker Commands
```bash
# On Oracle Cloud server
cd /opt/seo-analyzer

# Check services
sudo docker compose -f docker-compose.prod.yml ps

# View logs
sudo docker compose -f docker-compose.prod.yml logs -f api
sudo docker compose -f docker-compose.prod.yml logs -f worker

# Restart specific service
sudo docker compose -f docker-compose.prod.yml restart api
```

## 🔍 Monitoring

### Health Checks
- **Application**: http://129.148.63.199/health
- **Webhook**: http://129.148.63.199:9000/health
- **Status**: http://129.148.63.199:9000/status

### Log Locations
- **Application logs**: `docker compose logs`
- **Nginx logs**: `/var/log/nginx/` (in container)
- **Webhook logs**: `journalctl -u seo-webhook`

## 🛠️ Troubleshooting

### Common Issues

#### 1. Port Access Issues
```bash
# Check Oracle Cloud Security List
./scripts/setup-oracle-firewall.sh show

# Test port connectivity
curl -f http://129.148.63.199/health
```

#### 2. Database Connection Issues
```bash
# Check PostgreSQL
sudo docker compose -f docker-compose.prod.yml exec postgres pg_isready -U seoanalyzer

# Run migrations manually
sudo docker compose -f docker-compose.prod.yml exec api python -c "
from app.db.database import engine
from app.models.models import Base
Base.metadata.create_all(bind=engine)
"
```

#### 3. Service Not Starting
```bash
# Check service logs
sudo docker compose -f docker-compose.prod.yml logs api

# Rebuild and restart
sudo docker compose -f docker-compose.prod.yml down
sudo docker compose -f docker-compose.prod.yml build --no-cache
sudo docker compose -f docker-compose.prod.yml up -d
```

## 🔐 Security Considerations

### Environment Variables
- Never commit `.env` files to git
- Use strong passwords for database
- Rotate API keys regularly
- Use HTTPS in production (configure SSL certificates)

### Firewall Rules
- Only open necessary ports (80, 443, 9000)
- Consider restricting webhook port to GitHub IPs
- Regular security updates: `sudo apt update && sudo apt upgrade`

## 📊 Performance Optimization

### Resource Limits
- **PostgreSQL**: Optimized for Oracle Cloud free tier
- **Redis**: 256MB memory limit with LRU eviction
- **Celery**: Single worker (can scale up)

### Scaling Options
```bash
# Scale workers
sudo docker compose -f docker-compose.prod.yml up -d --scale worker=3

# Monitor resource usage
sudo docker stats
```

## 🔄 Backup & Recovery

### Database Backup
```bash
# Create backup
sudo docker compose -f docker-compose.prod.yml exec postgres pg_dump -U seoanalyzer seoanalyzer > backup.sql

# Restore backup
sudo docker compose -f docker-compose.prod.yml exec -T postgres psql -U seoanalyzer seoanalyzer < backup.sql
```

### Full System Backup
```bash
# Backup volumes
sudo docker run --rm -v seo-analyzer-prod_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz -C /data .
sudo docker run --rm -v seo-analyzer-prod_app_data:/data -v $(pwd):/backup alpine tar czf /backup/app-backup.tar.gz -C /data .
```

## 📞 Support

### Oracle Cloud Resources
- **Instance**: instance-20250825-1241 (129.148.63.199)
- **Region**: sa-saopaulo-1
- **SSH**: `ssh -i "/Users/hrocha/Documents/SSH Oracle/oci_ed25519" ubuntu@129.148.63.199`

### Application URLs
- **Main App**: http://129.148.63.199
- **API Health**: http://129.148.63.199/health
- **Webhook Status**: http://129.148.63.199:9000/status

---

**Last Updated**: August 2025  
**Version**: 1.0.0
