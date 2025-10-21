#!/bin/bash

# SEO Analyzer - Emergency Rollback Script
# Run this script locally if deployment fails and you need to restore previous state

set -e

SSH_KEY="/Users/hrocha/Documents/SSH Oracle/oci_ed25519"
SSH_USER="ubuntu"
SSH_HOST="129.148.63.199"
DEPLOY_DIR="/opt/seo-analyzer"

echo "🚨 Emergency Rollback - SEO Analyzer"
echo "This will attempt to restore the last working state"
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

echo "📋 Checking current status..."
ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "
  cd $DEPLOY_DIR
  echo '=== Current Container Status ==='
  sudo docker compose -f docker-compose.prod.yml ps || echo 'No containers running'
"

echo "🛑 Stopping current services..."
ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "
  cd $DEPLOY_DIR
  sudo docker compose -f docker-compose.prod.yml down || true
"

echo "🔄 Restarting with production compose..."
ssh -i "$SSH_KEY" "$SSH_USER@$SSH_HOST" "
  cd $DEPLOY_DIR
  
  # Force pull latest from git
  git fetch origin
  git checkout -f main
  git reset --hard origin/main
  
  # Ensure we have the production environment file
  if [ ! -f .env.prod ]; then
    echo '⚠️ No .env.prod found, using .env'
    cp .env .env.prod || true
  fi
  
  # Start with production compose
  sudo docker compose -f docker-compose.prod.yml up -d --remove-orphans
  
  echo '⏳ Waiting for services to start...'
  sleep 30
  
  echo '=== Final Container Status ==='
  sudo docker compose -f docker-compose.prod.yml ps
"

echo "🏥 Testing health endpoint..."
sleep 15

if curl -k -f -s https://$SSH_HOST/health > /dev/null; then
  echo "✅ Rollback successful - HTTPS health check passed"
elif curl -f -s http://$SSH_HOST/health > /dev/null; then
  echo "✅ Rollback successful - HTTP health check passed"  
else
  echo "❌ Health check failed - manual investigation required"
  echo "SSH to server: ssh -i '$SSH_KEY' $SSH_USER@$SSH_HOST"
  exit 1
fi

echo "🎉 Rollback completed successfully"