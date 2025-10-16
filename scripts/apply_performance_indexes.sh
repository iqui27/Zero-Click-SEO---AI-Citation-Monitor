#!/bin/bash
# Script para aplicar índices de performance no Azure SQL
# Uso: ./scripts/apply_performance_indexes.sh

set -e

echo "🔧 Aplicando índices de performance no banco de dados..."

# Verificar se DATABASE_URL está definida
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Erro: DATABASE_URL não está definida"
    echo "Configure a variável de ambiente DATABASE_URL antes de executar este script"
    exit 1
fi

# Extrair informações da connection string
# Formato esperado: mssql+pyodbc://user:pass@server/database?driver=...
SERVER=$(echo $DATABASE_URL | sed -n 's/.*@\([^/]*\)\/.*/\1/p')
DATABASE=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')
USER=$(echo $DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')

echo "📊 Servidor: $SERVER"
echo "📊 Database: $DATABASE"
echo "📊 Usuário: $USER"

# Solicitar senha
echo -n "🔑 Digite a senha do banco de dados: "
read -s PASSWORD
echo ""

# Aplicar migration
echo "⚙️  Executando migration de índices..."

sqlcmd -S "$SERVER" -d "$DATABASE" -U "$USER" -P "$PASSWORD" -i backend/migrations/add_performance_indexes.sql

if [ $? -eq 0 ]; then
    echo "✅ Índices aplicados com sucesso!"
    echo ""
    echo "📈 Índices criados:"
    echo "  - idx_runs_started_at (runs.started_at)"
    echo "  - idx_runs_subproject_id (runs.subproject_id)"
    echo "  - idx_runs_engine_id (runs.engine_id)"
    echo "  - idx_runs_subproject_started (composto)"
    echo "  - idx_citations_run_id (citations.run_id)"
    echo "  - idx_citations_domain (citations.domain)"
    echo ""
    echo "🚀 O dashboard deve carregar muito mais rápido agora!"
else
    echo "❌ Erro ao aplicar índices"
    exit 1
fi
