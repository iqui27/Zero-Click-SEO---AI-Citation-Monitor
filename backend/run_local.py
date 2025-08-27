#!/usr/bin/env python3
"""
Script para executar a aplicação FastAPI localmente com banco SQLite.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Adicionar o diretório atual ao path para importar os módulos
sys.path.append(str(Path(__file__).parent))

def main():
    """Executa a aplicação FastAPI localmente."""
    print("🚀 Iniciando aplicação local...")
    
    # Verificar se o banco existe
    if not os.path.exists("app.db"):
        print("🗄️  Banco de dados não encontrado. Criando...")
        os.system("python init_db.py")
    
    # Configurações da aplicação
    host = "0.0.0.0"
    port = 8000
    reload = True
    
    print(f"🌐 Servidor rodando em: http://{host}:{port}")
    print("📚 Documentação da API: http://localhost:8000/docs")
    print("🔧 Modo reload ativado (alterações automáticas)")
    print("💡 Pressione Ctrl+C para parar")
    
    # Executar a aplicação
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    main()