# SEO Analyzer Production Deployment

## Prerequisites

1. Server with Docker and Docker Compose installed
2. Domain name pointing to the server (zero-click.iqui27.codes)
3. Ports 80 and 443 open on the server

## Deployment Steps

### 1. Upload files to server

Upload the entire project to `/opt/seo-analyzer/` on your server.

### 2. Create production environment file

Create a `.env` file in `/opt/seo-analyzer/` with the following content:

```bash
# Production environment configuration
# Database
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE

# Redis
REDIS_URL=redis://redis:6379/0

# Application secrets (ADD YOUR API KEYS)
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
PERPLEXITY_API_KEY=your_perplexity_key_here
SERPAPI_KEY=your_serpapi_key_here

# Frontend
VITE_API_BASE=/api

# CORS configuration for production
CORS_ORIGINS=https://zero-click.iqui27.codes
```

### 3. Deploy with Docker Compose

```bash
# SSH to your server
ssh root@YOUR_SERVER_IP

# Navigate to project directory
cd /opt/seo-analyzer

# Deploy the application
docker compose -f docker-compose.prod.yml --env-file .env up -d --build

# Check status
docker compose -f docker-compose.prod.yml ps
```

### 4. Verify deployment

The deployment creates the following services:
- **reverse-proxy** (Caddy): Handles HTTPS, reverse proxy
- **frontend** (Nginx): Serves the React/Vite frontend  
- **api** (FastAPI): Backend API server
- **worker** (Celery): Background task processing
- **postgres**: Database
- **redis**: Cache and message broker

### 5. Check logs if needed

```bash
# View all logs
docker compose -f docker-compose.prod.yml logs

# View specific service logs
docker compose -f docker-compose.prod.yml logs api
docker compose -f docker-compose.prod.yml logs worker
```

## Domain Configuration

The Caddyfile is configured for `zero-click.iqui27.codes` with automatic HTTPS via Let's Encrypt.

## Important Security Notes

- Change the default PostgreSQL password in the .env file
- Add all your real API keys to the .env file
- Never commit the production .env file to version control
- Ensure your server firewall only allows necessary ports (22, 80, 443)
