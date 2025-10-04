#!/usr/bin/env python3
"""
Script de migração do banco de dados Azure SQL
Adiciona colunas faltantes que foram adicionadas nas novas features
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect

# Usar DATABASE_URL do ambiente ou fallback
DATABASE_URL = os.getenv('DATABASE_URL', '')

if not DATABASE_URL:
    print("❌ DATABASE_URL não configurada!")
    sys.exit(1)

print(f"Conectando ao banco: {DATABASE_URL[:60]}...")
engine = create_engine(DATABASE_URL, echo=False)
inspector = inspect(engine)

# Definir migrações necessárias
migrations = {
    'projects': [
        ('search_console_token', 'NVARCHAR(MAX) NULL'),
        ('search_console_connected_at', 'DATETIME NULL'),
        ('search_console_site_url', 'NVARCHAR(500) NULL'),
    ],
    # Adicione outras tabelas aqui conforme necessário
}

def get_existing_columns(table_name):
    """Retorna lista de colunas existentes na tabela"""
    return [col['name'] for col in inspector.get_columns(table_name)]

def add_column(table_name, column_name, column_type):
    """Adiciona uma coluna à tabela"""
    with engine.connect() as conn:
        sql = text(f'ALTER TABLE {table_name} ADD {column_name} {column_type}')
        print(f'  Executando: ALTER TABLE {table_name} ADD {column_name} {column_type}')
        conn.execute(sql)
        conn.commit()
        print(f'  ✅ Coluna {column_name} adicionada')

def main():
    print("\n" + "="*60)
    print("MIGRAÇÃO DO BANCO DE DADOS - SEO ANALYZER")
    print("="*60 + "\n")
    
    total_added = 0
    total_skipped = 0
    
    for table_name, columns in migrations.items():
        print(f"\n📊 Verificando tabela: {table_name}")
        
        existing_columns = get_existing_columns(table_name)
        print(f"   Colunas existentes: {len(existing_columns)}")
        
        for column_name, column_type in columns:
            if column_name not in existing_columns:
                try:
                    add_column(table_name, column_name, column_type)
                    total_added += 1
                except Exception as e:
                    print(f'  ❌ Erro ao adicionar {column_name}: {e}')
            else:
                print(f'  ⏭️  Coluna {column_name} já existe')
                total_skipped += 1
    
    print("\n" + "="*60)
    print(f"✅ MIGRAÇÃO CONCLUÍDA!")
    print(f"   Colunas adicionadas: {total_added}")
    print(f"   Colunas já existentes: {total_skipped}")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
