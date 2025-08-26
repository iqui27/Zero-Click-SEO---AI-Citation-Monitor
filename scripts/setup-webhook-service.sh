#!/bin/bash

# Setup Webhook Service on Oracle Cloud
# This script installs and configures the webhook server as a systemd service

set -e

# Configuration
WEBHOOK_PORT=9000
SERVICE_NAME="seo-webhook"
WEBHOOK_SECRET="seo-analyzer-webhook-2024-secret"
DEPLOY_DIR="/opt/seo-analyzer"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Install Python dependencies
install_dependencies() {
    log "Installing Python dependencies..."
    
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
    
    # Create virtual environment for webhook server
    sudo python3 -m venv /opt/webhook-env
    sudo /opt/webhook-env/bin/pip install flask gunicorn
    
    success "Dependencies installed"
}

# Create systemd service
create_service() {
    log "Creating systemd service..."
    
    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=SEO Analyzer Webhook Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=${DEPLOY_DIR}
Environment=WEBHOOK_SECRET=${WEBHOOK_SECRET}
Environment=PYTHONPATH=${DEPLOY_DIR}
ExecStart=/opt/webhook-env/bin/gunicorn --bind 0.0.0.0:${WEBHOOK_PORT} --workers 2 --timeout 300 scripts.webhook-server:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    success "Systemd service created"
}

# Setup firewall rule for webhook port
setup_firewall() {
    log "Setting up firewall for webhook port ${WEBHOOK_PORT}..."
    
    # Ubuntu firewall
    sudo ufw allow ${WEBHOOK_PORT}/tcp comment "SEO Analyzer Webhook"
    
    success "Firewall configured"
    
    log "⚠️  Don't forget to add port ${WEBHOOK_PORT} to Oracle Cloud Security List:"
    log "   - Protocol: TCP"
    log "   - Source: 0.0.0.0/0"
    log "   - Destination Port: ${WEBHOOK_PORT}"
    log "   - Description: SEO Analyzer Webhook"
}

# Start and enable service
start_service() {
    log "Starting webhook service..."
    
    sudo systemctl daemon-reload
    sudo systemctl enable ${SERVICE_NAME}
    sudo systemctl start ${SERVICE_NAME}
    
    # Wait a moment and check status
    sleep 3
    
    if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
        success "Webhook service started successfully"
    else
        error "Failed to start webhook service"
    fi
}

# Test webhook server
test_webhook() {
    log "Testing webhook server..."
    
    sleep 5
    
    if curl -f -s http://localhost:${WEBHOOK_PORT}/health > /dev/null; then
        success "Webhook server is responding"
    else
        error "Webhook server is not responding"
    fi
}

# Show service status and logs
show_status() {
    log "Service status:"
    sudo systemctl status ${SERVICE_NAME} --no-pager
    
    log "Recent logs:"
    sudo journalctl -u ${SERVICE_NAME} --no-pager -n 20
}

# Main function
main() {
    log "Setting up webhook service for SEO Analyzer..."
    
    install_dependencies
    create_service
    setup_firewall
    start_service
    test_webhook
    show_status
    
    success "Webhook service setup completed!"
    log "Webhook URL: http://$(curl -s ifconfig.me):${WEBHOOK_PORT}/webhook"
    log "Health check: http://$(curl -s ifconfig.me):${WEBHOOK_PORT}/health"
    log "Status endpoint: http://$(curl -s ifconfig.me):${WEBHOOK_PORT}/status"
    log ""
    log "GitHub Webhook Configuration:"
    log "  - Payload URL: http://$(curl -s ifconfig.me):${WEBHOOK_PORT}/webhook"
    log "  - Content type: application/json"
    log "  - Secret: ${WEBHOOK_SECRET}"
    log "  - Events: Just the push event"
}

# Handle script arguments
case "${1:-}" in
    "status")
        show_status
        ;;
    "restart")
        sudo systemctl restart ${SERVICE_NAME}
        success "Service restarted"
        ;;
    "stop")
        sudo systemctl stop ${SERVICE_NAME}
        success "Service stopped"
        ;;
    "logs")
        sudo journalctl -u ${SERVICE_NAME} -f
        ;;
    *)
        main
        ;;
esac
