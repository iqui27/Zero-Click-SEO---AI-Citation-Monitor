#!/bin/bash
# Script para gerar certificado Let's Encrypt

# Instalar certbot se não existir
if ! command -v certbot &> /dev/null; then
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
fi

# Parar nginx temporariamente
sudo docker-compose -f /opt/seo-analyzer/docker-compose.prod.yml stop reverse-proxy

# Gerar certificado para iqui27.app e subdomínios
sudo certbot certonly --standalone \
    -d iqui27.app \
    -d www.iqui27.app \
    -d n8n.iqui27.app \
    -d evolution.iqui27.app \
    --email admin@iqui27.app \
    --agree-tos \
    --non-interactive

# Copiar certificados para o diretório SSL
sudo cp /etc/letsencrypt/live/iqui27.app/fullchain.pem /opt/seo-analyzer/deploy/ssl/cloudflare-cert.pem
sudo cp /etc/letsencrypt/live/iqui27.app/privkey.pem /opt/seo-analyzer/deploy/ssl/cloudflare-key.pem

# Ajustar permissões
sudo chown ubuntu:ubuntu /opt/seo-analyzer/deploy/ssl/*.pem
sudo chmod 644 /opt/seo-analyzer/deploy/ssl/cloudflare-cert.pem
sudo chmod 600 /opt/seo-analyzer/deploy/ssl/cloudflare-key.pem

# Reiniciar containers
cd /opt/seo-analyzer
sudo docker-compose -f docker-compose.prod.yml up -d

echo "✅ Certificado Let's Encrypt configurado!"
echo "🌐 Teste: https://iqui27.app"
