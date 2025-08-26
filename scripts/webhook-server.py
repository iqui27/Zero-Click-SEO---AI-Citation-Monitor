#!/usr/bin/env python3
"""
Git Webhook Server for Automated Deployment
Listens for GitHub webhooks and triggers deployment to Oracle Cloud
"""

import os
import json
import hmac
import hashlib
import subprocess
import logging
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'your-webhook-secret-change-this')
DEPLOY_SCRIPT = '/opt/seo-analyzer/scripts/deploy.sh'
LOG_FILE = '/var/log/webhook-deploy.log'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def verify_signature(payload_body, signature_header):
    """Verify GitHub webhook signature"""
    if not signature_header:
        return False
    
    sha_name, signature = signature_header.split('=')
    if sha_name != 'sha256':
        return False
    
    mac = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_body,
        digestmod=hashlib.sha256
    )
    
    return hmac.compare_digest(mac.hexdigest(), signature)

def run_deployment():
    """Execute deployment script"""
    try:
        logger.info("Starting deployment process...")
        
        # Change to deployment directory
        os.chdir('/opt/seo-analyzer')
        
        # Run deployment script
        result = subprocess.run(
            ['bash', DEPLOY_SCRIPT],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info("Deployment completed successfully")
            return True, result.stdout
        else:
            logger.error(f"Deployment failed: {result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        logger.error("Deployment timed out")
        return False, "Deployment timed out after 10 minutes"
    except Exception as e:
        logger.error(f"Deployment error: {str(e)}")
        return False, str(e)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle GitHub webhook"""
    try:
        # Verify signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not verify_signature(request.data, signature):
            logger.warning("Invalid webhook signature")
            return jsonify({'error': 'Invalid signature'}), 401
        
        # Parse payload
        payload = request.get_json()
        
        # Check if it's a push to main branch
        if (payload.get('ref') == 'refs/heads/main' and 
            payload.get('repository', {}).get('name') == 'seo-analyzer'):
            
            logger.info(f"Received push to main branch from {payload.get('pusher', {}).get('name')}")
            
            # Run deployment in background
            success, output = run_deployment()
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': 'Deployment completed successfully',
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Deployment failed',
                    'error': output,
                    'timestamp': datetime.now().isoformat()
                }), 500
        else:
            logger.info(f"Ignoring webhook for ref: {payload.get('ref')}")
            return jsonify({'status': 'ignored', 'message': 'Not a main branch push'})
            
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'webhook-server'
    })

@app.route('/status', methods=['GET'])
def status():
    """Get deployment status"""
    try:
        # Check if services are running
        result = subprocess.run(
            ['docker', 'compose', '-f', 'docker-compose.prod.yml', 'ps', '--format', 'json'],
            capture_output=True,
            text=True,
            cwd='/opt/seo-analyzer'
        )
        
        if result.returncode == 0:
            services = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    service = json.loads(line)
                    services.append({
                        'name': service.get('Service'),
                        'state': service.get('State'),
                        'status': service.get('Status')
                    })
            
            return jsonify({
                'status': 'running',
                'services': services,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to get service status',
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    logger.info("Starting webhook server...")
    app.run(host='0.0.0.0', port=9000, debug=False)
