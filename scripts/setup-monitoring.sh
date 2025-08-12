#!/bin/bash

# SEO Analyzer Monitoring Setup Script
# Run this script on the server to set up monitoring and maintenance

set -e

PROJECT_DIR="/opt/seo-analyzer"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
BACKUP_DIR="$PROJECT_DIR/backups"

echo "=== SEO Analyzer Monitoring Setup ==="
echo "Setting up monitoring and maintenance tools..."

# Ensure we're in the right directory
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Project directory $PROJECT_DIR not found"
    exit 1
fi

cd $PROJECT_DIR

# Create necessary directories
echo "Creating directories..."
mkdir -p $SCRIPTS_DIR
mkdir -p $BACKUP_DIR

# Make scripts executable
echo "Setting up scripts..."
chmod +x $SCRIPTS_DIR/*.sh

# Set up log files
echo "Setting up log files..."
touch /var/log/seo-analyzer-backup.log
touch /var/log/seo-analyzer-health.log
touch /var/log/seo-analyzer-update.log

# Set proper permissions
chown root:root /var/log/seo-analyzer-*.log
chmod 644 /var/log/seo-analyzer-*.log

# Install cron job for automated backups
echo "Setting up cron jobs..."
cp $SCRIPTS_DIR/seo-analyzer-cron /etc/cron.d/
chown root:root /etc/cron.d/seo-analyzer-cron
chmod 644 /etc/cron.d/seo-analyzer-cron

# Reload cron
systemctl reload cron

# Test scripts
echo "Testing scripts..."

# Test monitoring script
if [ -f "$SCRIPTS_DIR/monitor-services.sh" ]; then
    echo "Testing monitor-services.sh..."
    $SCRIPTS_DIR/monitor-services.sh health || echo "Warning: Health check failed"
else
    echo "Warning: monitor-services.sh not found"
fi

# Test backup script
if [ -f "$SCRIPTS_DIR/backup-database.sh" ]; then
    echo "Testing backup script..."
    $SCRIPTS_DIR/backup-database.sh local || echo "Warning: Backup test failed"
else
    echo "Warning: backup-database.sh not found"
fi

echo ""
echo "=== Setup Complete ==="
echo "✓ Scripts installed and made executable"
echo "✓ Log files created"
echo "✓ Cron jobs configured"
echo "✓ Backup directory created: $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "1. Verify cron jobs: crontab -l"
echo "2. Check logs: tail -f /var/log/seo-analyzer-*.log"
echo "3. Test health check: $SCRIPTS_DIR/monitor-services.sh health"
echo "4. Run manual backup: $SCRIPTS_DIR/backup-database.sh local"
echo "5. Set up external uptime monitoring (see MAINTENANCE.md)"
echo ""
echo "Monitoring is now active!"
