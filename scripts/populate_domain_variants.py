#!/usr/bin/env python3
"""
Script para popular domain_variants com dados reais do Banco do Brasil.

Uso:
    python scripts/populate_domain_variants.py --project-id prj_xxx
"""

import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.models import Project, DomainVariant
from datetime import datetime


# Mapeamento de variantes de domínio para grandes bancos brasileiros
DOMAIN_VARIANTS_DATA = {
    "bb.com.br": {
        "name": "Banco do Brasil",
        "variants": [
            "bancodobrasil.com.br",
            "bb.com",
            "ourocard.com.br",
            "ourocard.com",
            "bbseguros.com.br",
            "bb.com.br/pbb",
            "bb.com.br/empresas",
            "bb.com.br/mei",
            "atendimento.bb.com.br",
            "www42.bb.com.br",
        ]
    },
    "nubank.com.br": {
        "name": "Nubank",
        "variants": [
            "nu.com.br",
            "nubank.com",
            "nuconta.com.br",
            "nuinvest.com.br",
        ]
    },
    "itau.com.br": {
        "name": "Itaú",
        "variants": [
            "itau.com",
            "itaucard.com.br",
            "itauempresarial.com.br",
            "itauinvestimentos.com.br",
            "itauseguros.com.br",
        ]
    },
    "bradesco.com.br": {
        "name": "Bradesco",
        "variants": [
            "bradesco.com",
            "bradescocard.com.br",
            "bradescoempresarial.com.br",
            "bradescoseguros.com.br",
        ]
    },
    "santander.com.br": {
        "name": "Santander",
        "variants": [
            "santander.com",
            "santandercard.com.br",
            "santanderempresas.com.br",
            "santanderseguros.com.br",
        ]
    },
    "caixa.gov.br": {
        "name": "Caixa Econômica Federal",
        "variants": [
            "caixa.com.br",
            "caixaseguros.com.br",
            "caixaempresas.com.br",
        ]
    },
    "bancointer.com.br": {
        "name": "Banco Inter",
        "variants": [
            "inter.com.br",
            "inter.co",
            "bancointer.com",
        ]
    },
    "c6bank.com.br": {
        "name": "C6 Bank",
        "variants": [
            "c6bank.com",
            "c6.com.br",
        ]
    },
    "pagbank.com.br": {
        "name": "PagBank",
        "variants": [
            "pagseguro.com.br",
            "pagseguro.uol.com.br",
            "pagbank.com",
        ]
    },
}


def populate_variants_for_project(db: Session, project_id: str, canonical_domain: str):
    """
    Popula variantes de domínio para um projeto específico.
    
    Args:
        db: Sessão do banco
        project_id: ID do projeto
        canonical_domain: Domínio canônico (ex: "bb.com.br")
    """
    # Verificar se projeto existe
    project = db.get(Project, project_id)
    if not project:
        print(f"❌ Projeto {project_id} não encontrado!")
        return False
    
    # Verificar se domínio está no mapeamento
    if canonical_domain not in DOMAIN_VARIANTS_DATA:
        print(f"❌ Domínio {canonical_domain} não encontrado no mapeamento!")
        print(f"Domínios disponíveis: {', '.join(DOMAIN_VARIANTS_DATA.keys())}")
        return False
    
    data = DOMAIN_VARIANTS_DATA[canonical_domain]
    variants = data["variants"]
    
    print(f"\n🏦 Populando variantes para {data['name']} ({canonical_domain})")
    print(f"📊 Total de variantes: {len(variants)}")
    print("-" * 60)
    
    added_count = 0
    skipped_count = 0
    
    for variant_domain in variants:
        # Verificar se já existe
        existing = db.query(DomainVariant).filter(
            DomainVariant.project_id == project_id,
            DomainVariant.variant_domain == variant_domain,
        ).first()
        
        if existing:
            print(f"⏭️  {variant_domain} → já existe")
            skipped_count += 1
            continue
        
        # Criar nova variante
        domain_variant = DomainVariant(
            project_id=project_id,
            variant_domain=variant_domain,
            canonical_domain=canonical_domain,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        
        db.add(domain_variant)
        print(f"✅ {variant_domain} → {canonical_domain}")
        added_count += 1
    
    # Commit
    try:
        db.commit()
        print("-" * 60)
        print(f"✅ Sucesso! {added_count} variantes adicionadas, {skipped_count} já existiam")
        return True
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao salvar: {e}")
        return False


def list_available_domains():
    """Lista todos os domínios disponíveis no mapeamento."""
    print("\n📋 Domínios Disponíveis:")
    print("=" * 60)
    for canonical, data in DOMAIN_VARIANTS_DATA.items():
        print(f"\n🏦 {data['name']}")
        print(f"   Canônico: {canonical}")
        print(f"   Variantes: {len(data['variants'])}")
        for variant in data['variants'][:3]:
            print(f"      - {variant}")
        if len(data['variants']) > 3:
            print(f"      ... e mais {len(data['variants']) - 3}")
    print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Popular domain_variants com dados reais")
    parser.add_argument("--project-id", help="ID do projeto (ex: prj_xxx)")
    parser.add_argument("--domain", help="Domínio canônico (ex: bb.com.br)")
    parser.add_argument("--list", action="store_true", help="Listar domínios disponíveis")
    
    args = parser.parse_args()
    
    if args.list:
        list_available_domains()
        return
    
    if not args.project_id or not args.domain:
        print("❌ Erro: --project-id e --domain são obrigatórios")
        print("\nUso:")
        print("  python scripts/populate_domain_variants.py --project-id prj_xxx --domain bb.com.br")
        print("  python scripts/populate_domain_variants.py --list")
        sys.exit(1)
    
    # Criar sessão
    db = SessionLocal()
    
    try:
        success = populate_variants_for_project(db, args.project_id, args.domain)
        sys.exit(0 if success else 1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
