#!/usr/bin/env python3
"""
Script para inicializar o banco de dados SQLite local.
Execute este script para criar as tabelas e dados iniciais.
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório atual ao path para importar os módulos
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from app.db.session import engine
from app.models.models import Base
from app.core.config import settings


def init_database():
    """Inicializa o banco de dados criando todas as tabelas."""
    print("🔧 Inicializando banco de dados SQLite...")
    
    try:
        # Criar todas as tabelas
        Base.metadata.create_all(bind=engine)
        print("✅ Tabelas criadas com sucesso!")
        
        # Verificar se as tabelas foram criadas
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result]
            print(f"📋 Tabelas criadas: {', '.join(tables)}")
            
        print(f"🗄️  Banco de dados criado em: {settings.database_url}")
        
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        sys.exit(1)


def check_database():
    """Verifica se o banco de dados já existe e tem tabelas."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result]
            
        if tables:
            print(f"📋 Banco já existe com {len(tables)} tabelas: {', '.join(tables)}")
            return True
        else:
            print("📋 Banco existe mas não tem tabelas")
            return False
            
    except Exception:
        print("📋 Banco não existe")
        return False


if __name__ == "__main__":
    print("🚀 Iniciando configuração do banco de dados local...")
    
    if check_database():
        response = input("Banco já existe. Deseja recriar? (s/N): ").lower()
        if response == 's':
            # Remover arquivo do banco se existir
            db_path = settings.database_url.replace("sqlite:///", "")
            if os.path.exists(db_path):
                os.remove(db_path)
                print("🗑️  Banco anterior removido")
            init_database()
        else:
            print("✅ Mantendo banco existente")
    else:
        init_database()
    
    print("🎉 Configuração concluída!")