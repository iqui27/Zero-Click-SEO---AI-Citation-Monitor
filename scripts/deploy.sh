#!/bin/bash

# SEO Analyzer - Oracle Cloud Deployment Script
# This script handles the complete deployment process to Oracle Cloud

set -e  # Exit on any error

# Configuration
ORACLE_HOST="129.148.63.199"
ORACLE_USER="ubuntu"
SSH_KEY="C:/Users/hftra/.ssh/oci_ed25519"
DEPLOY_DIR="/opt/seo-analyzer"
REPO_URL="https://github.com/yourusername/seo-analyzer.git"  # Update with your repo
BRANCH="main"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if [ ! -f "$SSH_KEY" ]; then
        error "SSH key not found at $SSH_KEY"
    fi
    
    if ! command -v ssh &> /dev/null; then
        error "SSH command not found"
    fi
    
    if ! command -v docker &> /dev/null; then
        warning "Docker not found locally (not required for deployment)"
    fi
    
    success "Prerequisites check passed"
}

# Test SSH connection
test_ssh() {
    log "Testing SSH connection to Oracle Cloud..."
    
    if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o BatchMode=yes "$ORACLE_USER@$ORACLE_HOST" "echo 'SSH connection successful'" &>/dev/null; then
        success "SSH connection to Oracle Cloud successful"
    else
        error "Failed to connect to Oracle Cloud via SSH"
    fi
}

# Build frontend locally
build_frontend() {
    log "Building frontend locally..."
    
    cd frontend
    
    if [ ! -d "node_modules" ]; then
        log "Installing frontend dependencies..."
        npm install
    fi
    
    log "Building production frontend..."
    npm run build
    
    if [ ! -d "dist" ]; then
        error "Frontend build failed - dist directory not found"
    fi
    
    success "Frontend built successfully"
    cd ..
}

# Deploy to Oracle Cloud
deploy_to_oracle() {
    log "Deploying to Oracle Cloud..."
    
    # Create deployment directory on server
    ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_HOST" "
        sudo mkdir -p $DEPLOY_DIR
        sudo chown $ORACLE_USER:$ORACLE_USER $DEPLOY_DIR
    "
    
    # Copy files to server
    log "Copying files to server..."
    rsync -avz --delete \
        -e "ssh -i '$SSH_KEY'" \
        --exclude 'node_modules' \
        --exclude '.git' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.env' \
        ./ "$ORACLE_USER@$ORACLE_HOST:$DEPLOY_DIR/"
    
    # Copy environment file
    if [ -f ".env.production" ]; then
        log "Copying production environment file..."
        scp -i "$SSH_KEY" .env.production "$ORACLE_USER@$ORACLE_HOST:$DEPLOY_DIR/.env"
    else
        warning "No .env.production file found. Make sure to create .env on server manually."
    fi
    
    success "Files copied to server"
}

# Setup and start services on Oracle Cloud
setup_services() {
    log "Setting up services on Oracle Cloud..."
    
    ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_HOST" "
        cd $DEPLOY_DIR
        
        # Stop existing services if running
        if [ -f docker-compose.prod.yml ]; then
            echo 'Stopping existing services...'
            sudo docker compose -f docker-compose.prod.yml down || true
        fi
        
        # Build and start services
        echo 'Building and starting services...'
        sudo docker compose -f docker-compose.prod.yml build --no-cache
        sudo docker compose -f docker-compose.prod.yml up -d
        
        # Wait for services to be ready
        echo 'Waiting for services to start...'
        sleep 30
        
        # Check service status
        echo 'Checking service status...'
        sudo docker compose -f docker-compose.prod.yml ps
        
        # Run database migrations
        echo 'Running database migrations...'
        sudo docker compose -f docker-compose.prod.yml exec -T api python -c \"
from app.db.database import engine
from app.models.models import Base
Base.metadata.create_all(bind=engine)
print('Database tables created successfully')
        \" || echo 'Migration failed or already exists'
        
        # Test health endpoint
        echo 'Testing health endpoint...'
        sleep 10
        curl -f http://localhost/health || echo 'Health check failed'
    "
    
    success "Services deployed and started"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Test external access
    if curl -f -s "http://$ORACLE_HOST/health" > /dev/null; then
        success "External health check passed"
    else
        warning "External health check failed - check firewall rules"
    fi
    
    # Check service logs
    log "Checking service logs..."
    ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_HOST" "
        cd $DEPLOY_DIR
        echo '=== API Logs ==='
        sudo docker compose -f docker-compose.prod.yml logs --tail=20 api
        echo '=== Worker Logs ==='
        sudo docker compose -f docker-compose.prod.yml logs --tail=20 worker
        echo '=== Nginx Logs ==='
        sudo docker compose -f docker-compose.prod.yml logs --tail=20 reverse-proxy
    "
}

# Main deployment function
main() {
    log "Starting SEO Analyzer deployment to Oracle Cloud..."
    
    check_prerequisites
    test_ssh
    build_frontend
    deploy_to_oracle
    setup_services
    verify_deployment
    
    success "Deployment completed successfully!"
    log "Application is available at: http://$ORACLE_HOST"
    log "Health check: http://$ORACLE_HOST/health"
}

# Handle script arguments
case "${1:-}" in
    "build")
        build_frontend
        ;;
    "deploy")
        deploy_to_oracle
        setup_services
        ;;
    "verify")
        verify_deployment
        ;;
    "logs")
        ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_HOST" "cd $DEPLOY_DIR && sudo docker compose -f docker-compose.prod.yml logs -f"
        ;;
    "status")
        ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_HOST" "cd $DEPLOY_DIR && sudo docker compose -f docker-compose.prod.yml ps"
        ;;
    "restart")
        ssh -i "$SSH_KEY" "$ORACLE_USER@$ORACLE_HOST" "cd $DEPLOY_DIR && sudo docker compose -f docker-compose.prod.yml restart"
        ;;
    *)
        main
        ;;
esac
