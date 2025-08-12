# Production Deployment Checklist

## ✅ Pre-flight checklist:

1. **Frontend built**: ✅ `frontend/dist/` exists
2. **Docker Compose configured**: ✅ `docker-compose.prod.yml` validated  
3. **Reverse proxy configured**: ✅ `Caddyfile` for `zero-click.iqui27.codes`
4. **Nginx configuration**: ✅ `deploy/nginx-default.conf`

## 🚀 Deploy to production server:

```bash
# 1. SSH to your server
ssh root@YOUR_SERVER_IP

# 2. Create project directory
mkdir -p /opt/seo-analyzer
cd /opt/seo-analyzer

# 3. Upload files (using scp, rsync, or git)
# Example with rsync:
# rsync -avz --exclude node_modules --exclude .env /path/to/local/seo-analyzer/ root@YOUR_IP:/opt/seo-analyzer/

# 4. Create production .env file
cat > .env << 'EOF'
# Production environment
POSTGRES_PASSWORD=secure_password_here_change_me

# Redis  
REDIS_URL=redis://redis:6379/0

# API Keys - ADD YOUR REAL KEYS HERE
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key  
PERPLEXITY_API_KEY=your_perplexity_key
SERPAPI_KEY=your_serpapi_key

# Frontend
VITE_API_BASE=/api

# CORS for production domain
CORS_ORIGINS=https://zero-click.iqui27.codes
EOF

# 5. Deploy with Docker Compose
docker compose -f docker-compose.prod.yml --env-file .env up -d --build

# 6. Check status
docker compose -f docker-compose.prod.yml ps
```

## 📊 This creates:

- **reverse-proxy** (Caddy): HTTPS + reverse proxy on ports 80/443
- **frontend** (Nginx): Serves React app 
- **api** (FastAPI): Backend API on port 8000
- **worker** (Celery): Background task processing
- **postgres**: Database with persistent storage
- **redis**: Cache & message broker

## 🔍 Verify deployment:

```bash  
# Check all services are running
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs api
docker compose -f docker-compose.prod.yml logs worker

# Test API endpoint
curl https://zero-click.iqui27.codes/api/healthz
```

## 🔒 Security Notes:

- ⚠️ **Change POSTGRES_PASSWORD** to a secure value
- ⚠️ **Add your real API keys** to .env
- ⚠️ **Never commit .env** to version control
- ✅ **Firewall**: Only allow ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
- ✅ **Domain**: Ensure `zero-click.iqui27.codes` points to server IP

## 🛠️ Troubleshooting:

```bash
# Rebuild specific service
docker compose -f docker-compose.prod.yml up -d --build api

# Access container for debugging
docker compose -f docker-compose.prod.yml exec api bash

# Follow logs in real-time
docker compose -f docker-compose.prod.yml logs -f worker
```
