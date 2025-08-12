#!/bin/bash

# SEO Analyzer Update Script
# Usage: ./update-app.sh

set -e  # Exit on any error

PROJECT_DIR="/opt/seo-analyzer"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"
BACKUP_DIR="/opt/seo-analyzer/backups"

echo "=== SEO Analyzer Update Process ==="
echo "Starting update at $(date)"

# Change to project directory
cd $PROJECT_DIR

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Step 1: Create database backup before update
echo "1. Creating database backup..."
BACKUP_FILE="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T postgres pg_dump -U postgres seo_analyzer > $BACKUP_FILE
echo "Database backup saved to: $BACKUP_FILE"

# Step 2: Pull latest code from repository
echo "2. Pulling latest code..."
git pull origin main || git pull origin master

# Step 3: Install frontend dependencies and build
echo "3. Installing frontend dependencies..."
npm --prefix frontend ci

echo "4. Building frontend..."
npm --prefix frontend run build

# Step 4: Rebuild and restart containers
echo "5. Rebuilding and restarting containers..."
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE down
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d --build

# Step 5: Wait for services to be ready
echo "6. Waiting for services to start..."
sleep 10

# Step 6: Health check
echo "7. Performing health check..."
MAX_ATTEMPTS=30
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    if curl -f http://localhost/api/healthz > /dev/null 2>&1; then
        echo "✓ Application is healthy and running!"
        break
    else
        echo "Attempt $ATTEMPT/$MAX_ATTEMPTS: Waiting for application to be ready..."
        sleep 5
        ATTEMPT=$((ATTEMPT + 1))
    fi
done

if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
    echo "✗ Application failed to start properly after $MAX_ATTEMPTS attempts"
    echo "Rolling back to previous state..."
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE logs --tail=50
    exit 1
fi

# Step 7: Show final status
echo "8. Final status check..."
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE ps

echo "=== Update completed successfully at $(date) ==="
echo "Backup available at: $BACKUP_FILE"
