#!/bin/bash

# Monitor SEO Analyzer Services
# Usage: ./monitor-services.sh [logs|status]

PROJECT_DIR="/opt/seo-analyzer"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"

cd $PROJECT_DIR

case "${1:-status}" in
  "status")
    echo "=== SEO Analyzer Services Status ==="
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE ps
    echo ""
    echo "=== Container Health ==="
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    ;;
  "logs")
    echo "=== Following logs for all services ==="
    echo "Press Ctrl+C to stop"
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE logs -f
    ;;
  "logs-backend")
    echo "=== Backend logs ==="
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE logs -f backend
    ;;
  "logs-frontend")
    echo "=== Frontend logs ==="
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE logs -f frontend
    ;;
  "logs-db")
    echo "=== Database logs ==="
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE logs -f postgres
    ;;
  "health")
    echo "=== Health Check ==="
    curl -f http://localhost/api/healthz && echo "✓ Backend healthy" || echo "✗ Backend unhealthy"
    curl -f http://localhost/ && echo "✓ Frontend accessible" || echo "✗ Frontend inaccessible"
    ;;
  *)
    echo "Usage: $0 [status|logs|logs-backend|logs-frontend|logs-db|health]"
    exit 1
    ;;
esac
