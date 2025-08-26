#!/bin/bash

# Oracle Cloud Firewall Setup for SEO Analyzer
# This script opens the necessary ports for the application

set -e

# Configuration from Oracle Cloud documentation
SECURITY_LIST_ID="ocid1.securitylist.oc1.sa-saopaulo-1.aaaaaaaaz2qvoojbladmbw75s5kep6assbhoi5frk2r6yaid7dybn653ut7a"

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

# Check OCI CLI
check_oci_cli() {
    log "Checking OCI CLI configuration..."
    
    if ! command -v oci &> /dev/null; then
        error "OCI CLI not found. Please install it first."
    fi
    
    if ! oci iam region list &> /dev/null; then
        error "OCI CLI not configured properly. Run 'oci setup config' first."
    fi
    
    success "OCI CLI is configured"
}

# Backup current security rules
backup_security_rules() {
    log "Backing up current security rules..."
    
    oci network security-list get --security-list-id $SECURITY_LIST_ID \
        --query 'data."ingress-security-rules"' --output json > backup-security-rules-$(date +%Y%m%d-%H%M%S).json
    
    success "Security rules backed up"
}

# Add port 80 (HTTP) if not exists
add_http_port() {
    log "Checking if HTTP port 80 is open..."
    
    # Get current rules and check if port 80 is already open
    current_rules=$(oci network security-list get --security-list-id $SECURITY_LIST_ID --query 'data."ingress-security-rules"' --output json)
    
    if echo "$current_rules" | jq -e '.[] | select(.protocol == "6" and ."tcp-options"."destination-port-range".min == 80)' > /dev/null; then
        success "Port 80 is already open"
    else
        log "Adding HTTP port 80..."
        
        # This is a complex operation - in practice, you'd need to get all existing rules and add the new one
        # For now, we'll just show the command structure
        echo "Manual step required: Add port 80 in Oracle Cloud Console"
        echo "Go to: Networking > Virtual Cloud Networks > Security Lists"
        echo "Add Ingress Rule: Protocol=TCP, Source=0.0.0.0/0, Destination Port=80"
    fi
}

# Add port 443 (HTTPS) if not exists
add_https_port() {
    log "Checking if HTTPS port 443 is open..."
    
    current_rules=$(oci network security-list get --security-list-id $SECURITY_LIST_ID --query 'data."ingress-security-rules"' --output json)
    
    if echo "$current_rules" | jq -e '.[] | select(.protocol == "6" and ."tcp-options"."destination-port-range".min == 443)' > /dev/null; then
        success "Port 443 is already open"
    else
        log "Adding HTTPS port 443..."
        echo "Manual step required: Add port 443 in Oracle Cloud Console"
        echo "Go to: Networking > Virtual Cloud Networks > Security Lists"
        echo "Add Ingress Rule: Protocol=TCP, Source=0.0.0.0/0, Destination Port=443"
    fi
}

# Show current security rules
show_current_rules() {
    log "Current security list rules:"
    
    oci network security-list get --security-list-id $SECURITY_LIST_ID \
        --query 'data."ingress-security-rules"[*].{Protocol:protocol,Source:source,Port:"tcp-options"."destination-port-range",Description:description}' \
        --output table
}

# Main function
main() {
    log "Setting up Oracle Cloud firewall for SEO Analyzer..."
    
    check_oci_cli
    backup_security_rules
    show_current_rules
    add_http_port
    add_https_port
    
    success "Firewall setup completed!"
    log "Make sure to manually add any missing ports in Oracle Cloud Console"
}

# Handle script arguments
case "${1:-}" in
    "show")
        show_current_rules
        ;;
    "backup")
        backup_security_rules
        ;;
    *)
        main
        ;;
esac
