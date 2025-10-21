#!/bin/bash

# SEO Analyzer - Cache and Backup Cleanup Script
# Remove old Docker images, builder cache, and backups to free up disk space
# Usage: ./cleanup-cache.sh

set -e

SSH_KEY="/Users/hrocha/Documents/SSH Oracle/oci_ed25519"
SSH_USER="ubuntu"
SSH_HOST="129.148.63.199"
DEPLOY_DIR="/opt/seo-analyzer"

echo "🧹 SEO Analyzer - Cleanup Script"
echo "This will remove old Docker images, builder cache, and backups"
echo "Press Ctrl+C to cancel, or wait 3 seconds to continue..."
sleep 3

ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "
  echo '===================================================='
  echo 'Starting cleanup on $SSH_HOST'
  echo '===================================================='
  
  echo ''
  echo '📊 DISK USAGE BEFORE:'
  echo '====================='
  df -h / | awk 'NR==1 || NR==2'
  echo ''
  echo 'Docker directory:'
  sudo du -sh /var/lib/docker 2>/dev/null || echo 'N/A'
  
  echo ''
  echo '🗑️  CLEANING UP...'
  echo '====================='
  
  # Clean old backups (keep last 5)
  echo '1️⃣  Removing backups older than the last 5...'
  if [ -d $DEPLOY_DIR/backups ]; then
    backup_count=\$(ls -1d $DEPLOY_DIR/backups/* 2>/dev/null | wc -l)
    if [ \$backup_count -gt 5 ]; then
      ls -1dt $DEPLOY_DIR/backups/* 2>/dev/null | tail -n +6 | xargs -r rm -rf
      echo '✅ Old backups removed'
    else
      echo '✅ Only \$backup_count backups found (keep all)'
    fi
  else
    echo '⚠️  No backups directory found'
  fi
  
  echo ''
  echo '2️⃣  Pruning Docker builder cache (unused buildx layers)...'
  sudo docker buildx prune -af --filter 'until=720h' 2>/dev/null || true
  echo '✅ Builder cache pruned'
  
  echo ''
  echo '3️⃣  Removing unused Docker images (older than 7 days)...'
  sudo docker image prune -f --filter 'until=168h' 2>/dev/null || true
  echo '✅ Unused images removed'
  
  echo ''
  echo '4️⃣  Removing dangling volumes (unused)...'
  sudo docker volume prune -f 2>/dev/null || true
  echo '✅ Dangling volumes removed'
  
  echo ''
  echo '5️⃣  System-wide Docker cleanup (containers, networks - older than 7 days)...'
  sudo docker system prune -f --filter 'until=168h' 2>/dev/null || true
  echo '✅ System cleanup done'
  
  echo ''
  echo '6️⃣  Removing npm cache from frontend build...'
  [ -d $DEPLOY_DIR/frontend/node_modules/.cache ] && rm -rf $DEPLOY_DIR/frontend/node_modules/.cache || true
  echo '✅ NPM cache cleaned'
  
  echo ''
  echo '7️⃣  Removing Python cache from backend...'
  [ -d $DEPLOY_DIR/backend/__pycache__ ] && find $DEPLOY_DIR/backend -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
  echo '✅ Python cache cleaned'
  
  echo ''
  echo '📊 DISK USAGE AFTER:'
  echo '==================='
  df -h / | awk 'NR==1 || NR==2'
  echo ''
  echo 'Docker directory:'
  sudo du -sh /var/lib/docker 2>/dev/null || echo 'N/A'
  
  echo ''
  echo '===================================================='
  echo '✨ Cleanup complete!'
  echo '===================================================='
"

echo ""
echo "🎉 Cleanup finished successfully"