#!/bin/bash

# SEO Analyzer - Setup Periodic Cleanup via Cron
# This installs a cron job to automatically clean up old Docker cache weekly

set -e

SSH_KEY="/Users/hrocha/Documents/SSH Oracle/oci_ed25519"
SSH_USER="ubuntu"
SSH_HOST="129.148.63.199"
DEPLOY_DIR="/opt/seo-analyzer"

echo "⏰ Setting up automatic cleanup job (weekly)"
echo "This will create a cron job to clean Docker cache and backups every Sunday at 2 AM UTC"

ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "
  echo 'Setting up cron job...'
  
  # Create cleanup script on server
  cat > /tmp/weekly-cleanup.sh << 'CLEANUP_EOF'
#!/bin/bash
set -e
DEPLOY_DIR='$DEPLOY_DIR'
LOG_FILE=/var/log/seo-analyzer-cleanup.log

{
  echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] Starting weekly cleanup\"
  
  # Clean old backups (keep last 5)
  if [ -d \$DEPLOY_DIR/backups ]; then
    ls -1dt \$DEPLOY_DIR/backups/* 2>/dev/null | tail -n +6 | xargs -r rm -rf
    echo \"Removed old backups\"
  fi
  
  # Docker cleanup
  docker buildx prune -af --filter 'until=720h' 2>/dev/null || true
  docker image prune -f --filter 'until=168h' 2>/dev/null || true
  docker volume prune -f 2>/dev/null || true
  docker system prune -f --filter 'until=168h' 2>/dev/null || true
  
  # Python/NPM cache
  find \$DEPLOY_DIR -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
  [ -d \$DEPLOY_DIR/frontend/node_modules/.cache ] && rm -rf \$DEPLOY_DIR/frontend/node_modules/.cache || true
  
  echo \"Disk usage: \$(du -sh /var/lib/docker 2>/dev/null || echo 'N/A')\"
  echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] Cleanup completed\"
} >> \$LOG_FILE 2>&1
CLEANUP_EOF
  
  sudo mv /tmp/weekly-cleanup.sh /usr/local/bin/seo-analyzer-weekly-cleanup.sh
  sudo chmod +x /usr/local/bin/seo-analyzer-weekly-cleanup.sh
  
  # Add cron job (Sunday 2 AM UTC)
  # First, check if job already exists
  if sudo crontab -l 2>/dev/null | grep -q 'seo-analyzer-weekly-cleanup'; then
    echo 'Cron job already exists, skipping...'
  else
    # Create temporary file with current crontab + new job
    (sudo crontab -l 2>/dev/null || true; echo '0 2 * * 0 /usr/local/bin/seo-analyzer-weekly-cleanup.sh') | sudo crontab -
    echo 'Cron job installed'
  fi
  
  # Show installed cron job
  echo 'Current cron jobs:'
  sudo crontab -l 2>/dev/null | grep seo-analyzer || echo 'None found'
  
  # Create log file
  sudo touch /var/log/seo-analyzer-cleanup.log
  sudo chmod 644 /var/log/seo-analyzer-cleanup.log
"

echo ""
echo "✅ Cron job installed successfully"
echo ""
echo "📋 Schedule:"
echo "  • Runs: Every Sunday at 2:00 AM UTC"
echo "  • Logs to: /var/log/seo-analyzer-cleanup.log"
echo ""
echo "🛠️  To view the log:"
echo "  ssh -i \"$SSH_KEY\" \"$SSH_USER@$SSH_HOST\" tail -f /var/log/seo-analyzer-cleanup.log"
echo ""
echo "🚫 To remove the cron job:"
echo "  ssh -i \"$SSH_KEY\" \"$SSH_USER@$SSH_HOST\" sudo crontab -e"
echo "  (then delete the seo-analyzer-weekly-cleanup line)"