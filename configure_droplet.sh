#!/usr/bin/env bash
# Script de configuração do droplet - SEO Analyzer
# 
# Este script configura o droplet com Docker, volumes, firewall, etc.

set -euo pipefail

echo "=== Configuração do Droplet - SEO Analyzer ==="
echo ""

# Verificar se o token da DigitalOcean está configurado
if [ -z "${DO_API_TOKEN:-}" ]; then
    echo "❌ Erro: Variável DO_API_TOKEN não está definida."
    echo "Configure com: export DO_API_TOKEN='seu_token_aqui'"
    echo ""
    echo "Para obter o token:"
    echo "1. Vá para: https://cloud.digitalocean.com/account/api/tokens"
    echo "2. Clique em 'Generate New Token'"
    echo "3. Dê um nome e marque 'Write' scope"
    echo "4. Copie o token e execute: export DO_API_TOKEN='token_aqui'"
    exit 1
fi

# Configurações do droplet (suas informações)
export DROPLET_ID=512874238
export DROPLET_NAME="zero-click"
export DROPLET_IP="198.211.98.85"
export DROPLET_REGION="nyc1"
export SSH_KEY="/Users/hrocha/.ssh/id_ed25519"
export DROPLET_USER="root"

# Configurações do projeto
export FIREWALL_NAME="web-ssh-zero-click"
export ALLOW_SSH_IPS="0.0.0.0/0,::/0"  # ATENÇÃO: Permite SSH de qualquer lugar - considere restringir depois
export VOLUMES_SPEC="app_data:1000:1000 db_data:999:999"

echo "📋 Configurações:"
echo "   Droplet ID: $DROPLET_ID"
echo "   Nome: $DROPLET_NAME"
echo "   IP: $DROPLET_IP"
echo "   Região: $DROPLET_REGION"
echo "   SSH Key: $SSH_KEY"
echo "   Firewall: $FIREWALL_NAME"
echo ""

# Verificar se a chave SSH existe
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ Erro: Chave SSH não encontrada em $SSH_KEY"
    exit 1
fi

echo "✅ Chave SSH encontrada"

# Testar conectividade SSH primeiro
echo "🔍 Testando conectividade SSH..."
if ssh -o BatchMode=yes -o ConnectTimeout=10 -i "$SSH_KEY" "$DROPLET_USER@$DROPLET_IP" true 2>/dev/null; then
    echo "✅ Conectividade SSH OK"
else
    echo "❌ Erro: Não foi possível conectar via SSH"
    echo "Verifique se:"
    echo "1. O droplet está ligado e acessível"
    echo "2. A chave SSH está configurada no droplet"
    echo "3. O IP está correto: $DROPLET_IP"
    exit 1
fi

echo ""
echo "🚀 Iniciando configuração do droplet..."
echo ""

# Executar o script de provisionamento
export EXECUTE=true
exec ./scripts/digitalocean_provision_runbook.sh
