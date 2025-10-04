#!/bin/bash

# Script para diagnosticar e corrigir problemas no deploy
# Execute este script NO SERVIDOR via SSH

set -e

DEPLOY_DIR="/opt/seo-analyzer"
cd $DEPLOY_DIR

echo "========================================="
echo "DIAGNÓSTICO DO DEPLOY - SEO ANALYZER"
echo "========================================="

echo -e "\n1. STATUS DOS CONTAINERS:"
sudo docker compose -f docker-compose.prod.yml ps

echo -e "\n2. LOGS DO BACKEND (últimas 100 linhas):"
sudo docker compose -f docker-compose.prod.yml logs --tail=100 api

echo -e "\n3. VERIFICANDO VARIÁVEIS DE AMBIENTE:"
sudo docker compose -f docker-compose.prod.yml exec -T api env | grep -E "DATABASE_URL|REDIS_URL|ENVIRONMENT" || echo "Container não está rodando"

echo -e "\n4. TESTANDO CONEXÃO COM AZURE SQL:"
sudo docker compose -f docker-compose.prod.yml exec -T api python -c "
import os
import sys
from sqlalchemy import create_engine, text

db_url = os.getenv('DATABASE_URL', '')
print(f'DATABASE_URL: {db_url[:80]}...')

try:
    engine = create_engine(db_url, echo=False)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1'))
        print('✅ Conexão com banco de dados OK!')
except Exception as e:
    print(f'❌ Erro na conexão: {e}')
    sys.exit(1)
" 2>&1 || echo "Falha ao testar conexão"

echo -e "\n5. VERIFICANDO TABELAS DO BANCO:"
sudo docker compose -f docker-compose.prod.yml exec -T api python -c "
from sqlalchemy import create_engine, inspect
import os

db_url = os.getenv('DATABASE_URL', '')
engine = create_engine(db_url, echo=False)
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f'Tabelas encontradas ({len(tables)}): {tables}')

# Verificar se tabela projects existe
if 'projects' in tables:
    columns = [col['name'] for col in inspector.get_columns('projects')]
    print(f'Colunas da tabela projects: {columns}')
else:
    print('⚠️  Tabela projects não existe!')
" 2>&1 || echo "Falha ao verificar tabelas"

echo -e "\n========================================="
echo "EXECUTANDO CORREÇÕES"
echo "========================================="

echo -e "\n6. RECRIANDO TABELAS (se necessário):"
sudo docker compose -f docker-compose.prod.yml exec -T api python -c "
from app.db.session import engine
from app.models.models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    logger.info('Criando/atualizando tabelas...')
    Base.metadata.create_all(bind=engine)
    logger.info('✅ Tabelas criadas/atualizadas com sucesso!')
except Exception as e:
    logger.error(f'❌ Erro ao criar tabelas: {e}')
    raise
" 2>&1

echo -e "\n7. REINICIANDO SERVIÇOS:"
sudo docker compose -f docker-compose.prod.yml restart api worker

echo -e "\n8. AGUARDANDO SERVIÇOS INICIAREM (30s)..."
sleep 30

echo -e "\n9. TESTANDO ENDPOINTS:"
echo "Health check:"
curl -s http://localhost/health || echo "❌ Health check falhou"

echo -e "\nProjects endpoint:"
curl -s http://localhost/api/projects || echo "❌ Projects endpoint falhou"

echo -e "\n========================================="
echo "DIAGNÓSTICO COMPLETO"
echo "========================================="
echo "Se ainda houver erros, verifique:"
echo "1. Firewall do Azure SQL permite IP do servidor OCI"
echo "2. Credenciais do banco estão corretas no .env"
echo "3. Logs detalhados: sudo docker compose -f docker-compose.prod.yml logs -f api"
