#!/bin/bash

# Script rápido para verificar conexão com Azure SQL
# Execute NO SERVIDOR

cd /opt/seo-analyzer

echo "Testando conexão com Azure SQL..."

sudo docker compose -f docker-compose.prod.yml exec -T api python << 'PYTHON_SCRIPT'
import os
import pyodbc
import sys

# Pegar DATABASE_URL do ambiente
db_url = os.getenv('DATABASE_URL', '')

if not db_url:
    print("❌ DATABASE_URL não está configurada!")
    sys.exit(1)

print(f"DATABASE_URL configurada: {db_url[:60]}...")

# Tentar conexão direta com pyodbc
try:
    # Extrair parâmetros da URL
    # Formato: mssql+pyodbc://user:pass@server/database?driver=...
    if 'mssql+pyodbc://' in db_url:
        parts = db_url.replace('mssql+pyodbc://', '').split('@')
        user_pass = parts[0].split(':')
        server_db = parts[1].split('/')
        
        user = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        server = server_db[0]
        database = server_db[1].split('?')[0] if len(server_db) > 1 else 'SEO'
        
        # Construir connection string
        conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server},1433;DATABASE={database};UID={user};PWD={password};Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=30;"
        
        print(f"\nTentando conectar:")
        print(f"  Server: {server}")
        print(f"  Database: {database}")
        print(f"  User: {user}")
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        print("\n✅ CONEXÃO COM AZURE SQL OK!")
        
        # Verificar tabelas
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\n📊 Tabelas no banco ({len(tables)}):")
        for table in sorted(tables):
            print(f"  - {table}")
        
        cursor.close()
        conn.close()
        
    else:
        print("⚠️  DATABASE_URL não é Azure SQL (mssql+pyodbc)")
        
except pyodbc.Error as e:
    print(f"\n❌ ERRO DE CONEXÃO PYODBC:")
    print(f"  {e}")
    
    if "40615" in str(e):
        print("\n🔥 FIREWALL BLOQUEADO!")
        print("  Adicione o IP do servidor OCI no firewall do Azure SQL")
        print("  IP do servidor: execute 'curl ifconfig.me' para descobrir")
    elif "HYT00" in str(e) or "timeout" in str(e).lower():
        print("\n⏱️  TIMEOUT DE CONEXÃO!")
        print("  Verifique:")
        print("  1. Firewall do Azure SQL")
        print("  2. Conectividade de rede")
        print("  3. DNS resolution")
    
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ ERRO GERAL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_SCRIPT

echo -e "\n========================================="
echo "Para verificar o IP público do servidor:"
echo "  curl ifconfig.me"
echo ""
echo "Adicione este IP no firewall do Azure SQL Portal:"
echo "  Azure Portal > SQL Server > Networking > Firewall rules"
echo "========================================="
