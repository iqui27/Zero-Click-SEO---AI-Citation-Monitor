#!/usr/bin/env python3
"""
Script de gerenciamento do banco de dados SQLite local.
Permite backup, reset, status e outras operações.
"""

import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Adicionar o diretório atual ao path para importar os módulos
sys.path.append(str(Path(__file__).parent))

from app.core.config import settings


def get_db_path():
    """Retorna o caminho do arquivo do banco de dados."""
    db_url = settings.database_url
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "")
    return "app.db"


def backup_database():
    """Cria um backup do banco de dados."""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print("❌ Banco de dados não encontrado")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backup_{timestamp}.db"
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup criado: {backup_path}")
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")


def reset_database():
    """Remove o banco de dados atual."""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print("❌ Banco de dados não encontrado")
        return
    
    try:
        os.remove(db_path)
        print("🗑️  Banco de dados removido")
        print("💡 Execute 'python init_db.py' para recriar")
    except Exception as e:
        print(f"❌ Erro ao remover banco: {e}")


def show_status():
    """Mostra o status atual do banco de dados."""
    db_path = get_db_path()
    
    print("📊 Status do Banco de Dados")
    print("=" * 40)
    
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        size_mb = size / (1024 * 1024)
        modified = datetime.fromtimestamp(os.path.getmtime(db_path))
        
        print(f"📍 Localização: {db_path}")
        print(f"📏 Tamanho: {size_mb:.2f} MB")
        print(f"🕒 Última modificação: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 URL: {settings.database_url}")
        
        # Verificar se é SQLite
        if settings.database_url.startswith("sqlite"):
            print("🗄️  Tipo: SQLite (Local)")
        else:
            print("🗄️  Tipo: Outro")
            
    else:
        print("❌ Banco de dados não encontrado")
        print("💡 Execute 'python init_db.py' para criar")


def show_help():
    """Mostra a ajuda do script."""
    print("🔧 Gerenciador de Banco de Dados SQLite")
    print("=" * 40)
    print("Comandos disponíveis:")
    print("  status    - Mostra status do banco")
    print("  backup    - Cria backup do banco")
    print("  reset     - Remove o banco atual")
    print("  help      - Mostra esta ajuda")
    print("")
    print("Exemplos:")
    print("  python manage_db.py status")
    print("  python manage_db.py backup")
    print("  python manage_db.py reset")


def main():
    """Função principal do script."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        show_status()
    elif command == "backup":
        backup_database()
    elif command == "reset":
        confirm = input("⚠️  Tem certeza que deseja remover o banco? (s/N): ").lower()
        if confirm == 's':
            reset_database()
        else:
            print("✅ Operação cancelada")
    elif command == "help":
        show_help()
    else:
        print(f"❌ Comando desconhecido: {command}")
        show_help()


if __name__ == "__main__":
    main()