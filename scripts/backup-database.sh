#!/bin/bash

# SEO Analyzer Database Backup Script
# Usage: ./backup-database.sh [local|remote]

PROJECT_DIR="/opt/seo-analyzer"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"
BACKUP_DIR="/opt/seo-analyzer/backups"
RETENTION_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

case "${1:-local}" in
  "local")
    echo "=== Creating Local Database Backup ==="
    cd $PROJECT_DIR
    
    BACKUP_FILE="$BACKUP_DIR/seo_analyzer_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    echo "Creating backup: $BACKUP_FILE"
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T postgres pg_dump -U postgres seo_analyzer > $BACKUP_FILE
    
    if [ $? -eq 0 ]; then
        echo "✓ Backup created successfully: $BACKUP_FILE"
        echo "File size: $(du -h $BACKUP_FILE | cut -f1)"
        
        # Compress the backup
        gzip $BACKUP_FILE
        echo "✓ Backup compressed: ${BACKUP_FILE}.gz"
        
        # Clean up old backups (keep last 30 days)
        echo "Cleaning up backups older than $RETENTION_DAYS days..."
        find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
        
        echo "Current backups:"
        ls -lah $BACKUP_DIR/*.sql.gz 2>/dev/null || echo "No compressed backups found"
    else
        echo "✗ Backup failed"
        exit 1
    fi
    ;;
    
  "remote")
    echo "=== Creating Remote Database Backup ==="
    
    # Load environment variables to get database connection info
    if [ -f "$PROJECT_DIR/$ENV_FILE" ]; then
        source "$PROJECT_DIR/$ENV_FILE"
    else
        echo "✗ Environment file not found: $PROJECT_DIR/$ENV_FILE"
        exit 1
    fi
    
    # You'll need to replace these with your actual database connection details
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"
    DB_NAME="${DB_NAME:-seo_analyzer}"
    DB_USER="${DB_USER:-postgres}"
    
    BACKUP_FILE="$BACKUP_DIR/seo_analyzer_remote_backup_$(date +%Y%m%d_%H%M%S).sql"
    
    echo "Creating remote backup from $DB_HOST:$DB_PORT/$DB_NAME"
    
    # Use pg_dump for remote backup (requires postgresql-client)
    PGPASSWORD="$DB_PASSWORD" pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME > $BACKUP_FILE
    
    if [ $? -eq 0 ]; then
        echo "✓ Remote backup created successfully: $BACKUP_FILE"
        echo "File size: $(du -h $BACKUP_FILE | cut -f1)"
        
        # Compress the backup
        gzip $BACKUP_FILE
        echo "✓ Backup compressed: ${BACKUP_FILE}.gz"
    else
        echo "✗ Remote backup failed"
        exit 1
    fi
    ;;
    
  *)
    echo "Usage: $0 [local|remote]"
    echo "  local  - Backup from local Docker container (default)"
    echo "  remote - Backup from remote database server"
    exit 1
    ;;
esac

echo "=== Backup completed at $(date) ==="
