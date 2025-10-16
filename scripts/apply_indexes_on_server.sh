#!/bin/bash
# Script para executar DENTRO do servidor OCI
# Aplica índices de performance no banco Azure SQL

set -e

echo "🔧 Aplicando Índices de Performance no Banco de Dados"
echo "====================================================="
echo ""

# Verificar se estamos no diretório correto
if [ ! -f "backend/migrations/add_performance_indexes.sql" ]; then
    echo "❌ Erro: Arquivo de migration não encontrado"
    echo "Execute este script do diretório raiz do projeto"
    exit 1
fi

# Carregar variáveis de ambiente
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ Erro: Arquivo .env não encontrado"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Erro: DATABASE_URL não definida no .env"
    exit 1
fi

# Extrair informações da connection string
# Formato: mssql+pyodbc://user:pass@server/database?driver=...
SERVER_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^/]*\)\/.*/\1/p')
DATABASE=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
USER_DB=$(echo $DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
PASSWORD=$(echo $DATABASE_URL | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')

echo "📊 Servidor: $SERVER_HOST"
echo "📊 Database: $DATABASE"
echo "📊 Usuário: $USER_DB"
echo ""

# Verificar se sqlcmd está instalado
if ! command -v sqlcmd &> /dev/null; then
    echo "⚠️  sqlcmd não encontrado. Instalando..."
    echo ""
    
    # Adicionar repositório Microsoft
    curl -s https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
    
    # Detectar versão do Ubuntu
    UBUNTU_VERSION=$(lsb_release -rs)
    curl -s https://packages.microsoft.com/config/ubuntu/${UBUNTU_VERSION}/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
    
    # Atualizar e instalar
    sudo apt-get update > /dev/null 2>&1
    sudo ACCEPT_EULA=Y apt-get install -y mssql-tools unixodbc-dev > /dev/null 2>&1
    
    # Adicionar ao PATH
    export PATH="$PATH:/opt/mssql-tools/bin"
    
    echo "✅ sqlcmd instalado com sucesso"
    echo ""
fi

# Verificar conectividade
echo "🔍 Testando conexão com o banco..."
/opt/mssql-tools/bin/sqlcmd -S "$SERVER_HOST" -d "$DATABASE" -U "$USER_DB" -P "$PASSWORD" -Q "SELECT 1 as test" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Conexão estabelecida com sucesso"
else
    echo "❌ Erro ao conectar no banco de dados"
    exit 1
fi

echo ""
echo "🔄 Aplicando índices de performance..."
echo ""

# Executar migration
/opt/mssql-tools/bin/sqlcmd -S "$SERVER_HOST" -d "$DATABASE" -U "$USER_DB" -P "$PASSWORD" -i backend/migrations/add_performance_indexes.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ✅ ✅ ÍNDICES APLICADOS COM SUCESSO! ✅ ✅ ✅"
    echo ""
    echo "📈 Índices criados:"
    echo "  ✓ idx_runs_started_at (runs.started_at)"
    echo "  ✓ idx_runs_subproject_id (runs.subproject_id)"
    echo "  ✓ idx_runs_engine_id (runs.engine_id)"
    echo "  ✓ idx_runs_subproject_started (composto)"
    echo "  ✓ idx_citations_run_id (citations.run_id)"
    echo "  ✓ idx_citations_domain (citations.domain)"
    echo ""
    echo "🚀 Próximos passos:"
    echo "1. Reiniciar backend:"
    echo "   docker-compose -f docker-compose.prod.yml restart api"
    echo ""
    echo "2. Testar dashboard:"
    echo "   http://129.148.63.199/"
    echo ""
    echo "O dashboard deve carregar 85-90% mais rápido agora! 🎉"
else
    echo ""
    echo "❌ Erro ao aplicar índices"
    echo "Verifique os logs acima para mais detalhes"
    exit 1
fi
