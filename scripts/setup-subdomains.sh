#!/bin/bash

# Script para configurar subdomínios no servidor Oracle Cloud
# Este script deve ser executado no servidor (129.148.63.199)

set -e

echo "🚀 Configurando subdomínios para n8n, Evolution API e SEO Analyzer..."

# Verificar se estamos no servidor correto
if [ "$(hostname)" != "instance-20250825-1241" ]; then
    echo "⚠️  Este script deve ser executado no servidor Oracle Cloud"
    echo "   Execute: ssh -i ~/.ssh/oci_ed25519 ubuntu@129.148.63.199"
    exit 1
fi

# Verificar se o diretório do projeto existe
if [ ! -d "/opt/seo-analyzer" ]; then
    echo "❌ Diretório /opt/seo-analyzer não encontrado"
    exit 1
fi

cd /opt/seo-analyzer

echo "📋 Verificando serviços em execução..."

# Verificar se os containers estão rodando
echo "🔍 Status dos containers:"
sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🔍 Verificando conectividade dos serviços:"

# Testar n8n
if curl -s -f http://localhost:5678/ > /dev/null; then
    echo "✅ n8n está respondendo na porta 5678"
else
    echo "❌ n8n não está respondendo na porta 5678"
fi

# Testar Evolution API
if curl -s -f http://localhost:8080/ > /dev/null; then
    echo "✅ Evolution API está respondendo na porta 8080"
else
    echo "❌ Evolution API não está respondendo na porta 8080"
fi

# Testar SEO Analyzer
if curl -s -f http://localhost/health > /dev/null; then
    echo "✅ SEO Analyzer está respondendo na porta 80"
else
    echo "❌ SEO Analyzer não está respondendo na porta 80"
fi

echo ""
echo "🔄 Reiniciando o container do Nginx para aplicar nova configuração..."

# Reiniciar apenas o container do nginx
sudo docker compose -f docker-compose.prod.yml restart reverse-proxy

echo "⏳ Aguardando o Nginx reiniciar..."
sleep 5

# Verificar se o Nginx está funcionando
if curl -s -f http://localhost/health > /dev/null; then
    echo "✅ Nginx reiniciado com sucesso!"
else
    echo "❌ Erro ao reiniciar o Nginx"
    echo "📋 Logs do Nginx:"
    sudo docker logs seo-analyzer-prod-reverse-proxy-1 --tail 20
    exit 1
fi

echo ""
echo "🎉 Configuração de subdomínios aplicada com sucesso!"
echo ""
echo "📝 Próximos passos:"
echo "1. Configure os registros DNS A para apontar para 129.148.63.199:"
echo "   - n8n.seudominio.com      → 129.148.63.199"
echo "   - evolution.seudominio.com → 129.148.63.199"
echo "   - seudominio.com          → 129.148.63.199"
echo ""
echo "2. Após configurar o DNS, teste os acessos:"
echo "   - http://n8n.seudominio.com"
echo "   - http://evolution.seudominio.com"
echo "   - http://seudominio.com"
echo ""
echo "🔧 Para testar localmente (adicione ao /etc/hosts):"
echo "129.148.63.199 n8n.seudominio.com"
echo "129.148.63.199 evolution.seudominio.com"
echo "129.148.63.199 seudominio.com"
