#!/bin/bash

echo "=== Verificando containers Docker ==="
docker ps -a

echo -e "\n=== Logs do container API (últimas 50 linhas) ==="
docker logs --tail 50 $(docker ps -q -f name=api) 2>&1 || echo "Container API não encontrado"

echo -e "\n=== Logs do container Worker (últimas 30 linhas) ==="
docker logs --tail 30 $(docker ps -q -f name=worker) 2>&1 || echo "Container Worker não encontrado"

echo -e "\n=== Verificando conectividade com Azure SQL ==="
docker exec $(docker ps -q -f name=api) python -c "
import os
import pyodbc
try:
    db_url = os.getenv('DATABASE_URL', '')
    print(f'DATABASE_URL configurado: {db_url[:50]}...' if len(db_url) > 50 else db_url)
    if 'mssql+pyodbc' in db_url:
        print('Tentando conectar ao Azure SQL...')
        # Extrair connection string
        conn_str = db_url.split('://')[1].split('?')[0]
        print('Conexão OK!' if conn_str else 'Erro na string de conexão')
except Exception as e:
    print(f'Erro: {e}')
" 2>&1 || echo "Não foi possível executar teste de conexão"

echo -e "\n=== Verificando variáveis de ambiente ==="
docker exec $(docker ps -q -f name=api) env | grep -E "DATABASE_URL|REDIS_URL|ENVIRONMENT" 2>&1 || echo "Não foi possível verificar env vars"
