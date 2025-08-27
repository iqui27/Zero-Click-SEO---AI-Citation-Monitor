#!/bin/bash
# Script para testar conexão com Azure SQL Database no servidor Oracle Cloud

echo "=== Teste de Conexão Azure SQL Database ==="
echo "Servidor: seoanalyzer.database.windows.net"
echo "Database: SEO"
echo "Usuário: iqui27"
echo ""

# 1. Testar conectividade TCP
echo "1. Testando conectividade TCP na porta 1433..."
timeout 10 bash -c "</dev/tcp/seoanalyzer.database.windows.net/1433" && echo "✅ Porta 1433 acessível" || echo "❌ Porta 1433 inacessível"

# 2. Testar com telnet se disponível
echo -e "\n2. Testando com telnet..."
if command -v telnet &> /dev/null; then
    timeout 10 telnet seoanalyzer.database.windows.net 1433 || echo "❌ Telnet falhou"
else
    echo "Telnet não disponível"
fi

# 3. Testar resolução DNS
echo -e "\n3. Testando resolução DNS..."
nslookup seoanalyzer.database.windows.net || echo "❌ DNS não resolve"

# 4. Testar com Python pymssql
echo -e "\n4. Testando conexão Python pymssql..."
python3 -c "
import pymssql
try:
    conn = pymssql.connect(
        server='seoanalyzer.database.windows.net',
        user='iqui27@seoanalyzer',
        password='IquinhoiF27!',
        database='SEO',
        timeout=30,
        login_timeout=30
    )
    print('✅ Conexão pymssql bem-sucedida')
    conn.close()
except Exception as e:
    print(f'❌ Erro pymssql: {e}')
"

# 5. Testar com SQLAlchemy
echo -e "\n5. Testando conexão SQLAlchemy..."
python3 -c "
from sqlalchemy import create_engine, text
try:
    # Formato pymssql
    url = 'mssql+pymssql://iqui27:IquinhoiF27%21@seoanalyzer.database.windows.net:1433/SEO?charset=utf8'
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1 as test'))
        print('✅ Conexão SQLAlchemy pymssql bem-sucedida')
except Exception as e:
    print(f'❌ Erro SQLAlchemy pymssql: {e}')
    
    try:
        # Formato pyodbc alternativo
        url2 = 'mssql+pyodbc://iqui27:IquinhoiF27%21@seoanalyzer.database.windows.net:1433/SEO?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&Connection+Timeout=30'
        engine2 = create_engine(url2, pool_pre_ping=True)
        with engine2.connect() as conn:
            result = conn.execute(text('SELECT 1 as test'))
            print('✅ Conexão SQLAlchemy pyodbc bem-sucedida')
    except Exception as e2:
        print(f'❌ Erro SQLAlchemy pyodbc: {e2}')
"

# 6. Verificar se Azure SQL está pausado
echo -e "\n6. Verificando status do Azure SQL..."
echo "Se todos os testes falharam, o Azure SQL Database pode estar:"
echo "- Pausado (precisa ser reativado no portal)"
echo "- Com firewall bloqueando este IP"
echo "- Temporariamente indisponível"

echo -e "\n=== Fim do Teste ==="
