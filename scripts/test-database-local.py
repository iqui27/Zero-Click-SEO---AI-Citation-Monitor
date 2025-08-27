#!/usr/bin/env python3
"""
Script para testar conectividade com Azure SQL Database usando DATABASE_URL
Execute: python test-database-local.py
"""

import os
import sys
from urllib.parse import urlparse
import time

def test_database_connection():
    """Testa a conectividade com o banco de dados usando DATABASE_URL"""
    
    # Verificar se DATABASE_URL está definida
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não encontrada nas variáveis de ambiente")
        print("💡 Defina a variável: set DATABASE_URL=sua_string_de_conexao")
        return False
    
    print("🔍 Testando conectividade com Azure SQL Database...")
    print(f"📋 DATABASE_URL encontrada (primeiros 50 chars): {database_url[:50]}...")
    
    # Parse da URL para extrair informações
    try:
        parsed = urlparse(database_url)
        
        print(f"🎯 Servidor: {parsed.hostname}")
        print(f"🔌 Porta: {parsed.port or 1433}")
        print(f"🗄️  Database: {parsed.path.lstrip('/')}")
        print(f"👤 Usuário: {parsed.username}")
        
    except Exception as e:
        print(f"❌ Erro ao fazer parse da DATABASE_URL: {e}")
        return False
    
    # Testar conectividade TCP primeiro
    print("\n🔌 Testando conectividade TCP...")
    try:
        import socket
        
        host = parsed.hostname
        port = parsed.port or 1433
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print("✅ Conectividade TCP: OK")
        else:
            print("❌ Conectividade TCP: FALHOU")
            print("   Possíveis causas:")
            print("   - Firewall do Azure SQL bloqueando este IP")
            print("   - Problema de rede/DNS")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste TCP: {e}")
        return False
    
    # Testar conexão SQL
    print("\n🗄️  Testando conexão SQL...")
    try:
        # Tentar importar pyodbc
        try:
            import pyodbc
        except ImportError:
            print("❌ pyodbc não instalado. Instale com: pip install pyodbc")
            return False
        
        # Tentar conectar
        print("⏳ Conectando ao banco de dados...")
        
        # Timeout de 30 segundos
        conn = pyodbc.connect(database_url, timeout=30)
        
        print("✅ Conexão SQL: OK")
        
        # Testar uma query simples
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            print("✅ Query de teste: OK")
        
        cursor.close()
        conn.close()
        
        print("🎉 Teste de conectividade: SUCESSO!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão SQL: {e}")
        
        # Analisar tipos específicos de erro
        error_str = str(e).lower()
        
        if "timeout" in error_str:
            print("💡 Erro de timeout - verifique firewall do Azure SQL")
        elif "login failed" in error_str:
            print("💡 Erro de login - verifique usuário/senha")
        elif "cannot open database" in error_str:
            print("💡 Erro de database - verifique nome do banco")
        elif "ssl" in error_str:
            print("💡 Erro SSL - verifique configuração de certificados")
        
        return False

def main():
    """Função principal"""
    print("🚀 Teste de Conectividade Azure SQL Database")
    print("=" * 50)
    
    # Verificar se estamos no diretório correto
    if not os.path.exists('.env.example'):
        print("⚠️  Execute este script no diretório raiz do projeto")
    
    # Tentar carregar .env se existir
    env_file = '.env'
    if os.path.exists(env_file):
        print(f"📁 Carregando variáveis de {env_file}...")
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
        except Exception as e:
            print(f"⚠️  Erro ao carregar .env: {e}")
    
    # Executar teste
    success = test_database_connection()
    
    if success:
        print("\n✅ Todos os testes passaram!")
        sys.exit(0)
    else:
        print("\n❌ Teste falhou - verifique configurações")
        sys.exit(1)

if __name__ == "__main__":
    main()
