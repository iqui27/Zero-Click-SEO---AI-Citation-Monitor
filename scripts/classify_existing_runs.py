#!/usr/bin/env python3
"""
Script para classificação retroativa de runs existentes
Pode ser executado independentemente ou integrado com o sistema de deploy.
"""

import os
import sys
import argparse
from pathlib import Path

# Adicionar o diretório backend ao Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.classification_integration import (
    ClassificationIntegrator,
    batch_classify_unclassified_runs,
    retroactively_classify_all_runs
)
from app.db.session import SessionLocal


def main():
    parser = argparse.ArgumentParser(description='Classificação retroativa de runs')
    parser.add_argument(
        '--project-id',
        type=str,
        help='ID do projeto específico (se não fornecido, processa todos os projetos)'
    )
    parser.add_argument(
        '--force-update',
        action='store_true',
        help='Reclassificar runs já classificadas'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=1000,
        help='Limite de runs a processar (padrão: 1000)'
    )
    parser.add_argument(
        '--only-unclassified',
        action='store_true',
        help='Processar apenas runs não classificadas (padrão)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Tamanho do lote para processamento (padrão: 50)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Apenas mostrar quantas runs seriam processadas, sem executar'
    )
    parser.add_argument(
        '--skip-batches',
        type=int,
        default=0,
        help='Ignorar N lotes completos antes de começar o processamento'
    )

    args = parser.parse_args()

    print("=== Classificação Retroativa de Runs ===")
    print(f"Projeto: {args.project_id or 'Todos'}")
    print(f"Forçar atualização: {args.force_update}")
    print(f"Limite: {args.limit}")
    print(f"Apenas não classificadas: {args.only_unclassified}")
    print(f"Dry run: {args.dry_run}")
    print()

    try:
        with ClassificationIntegrator() as integrator:
            # Contar runs não classificadas
            unclassified_runs = integrator.get_unclassified_runs(args.project_id, args.limit)
            print(f"Runs não classificadas encontradas: {len(unclassified_runs)}")

            if args.only_unclassified or not args.force_update:
                target_runs = unclassified_runs
                print(f"Processando apenas runs não classificadas: {len(target_runs)}")
            else:
                # Contar total de runs completadas
                db = SessionLocal()
                try:
                    from app.models.models import Run
                    query = db.query(Run.id).filter(Run.status == "completed")
                    if args.project_id:
                        query = query.filter(Run.project_id == args.project_id)
                    all_completed = [row[0] for row in query.limit(args.limit).all()]
                    target_runs = all_completed
                    print(f"Processando todas as runs completadas: {len(target_runs)}")
                finally:
                    db.close()

            if args.dry_run:
                print(f"\n[DRY RUN] Seriam processadas {len(target_runs)} runs")
                if target_runs:
                    print("Exemplos de IDs:")
                    for i, run_id in enumerate(target_runs[:5]):
                        print(f"  {i+1}. {run_id}")
                    if len(target_runs) > 5:
                        print(f"  ... e mais {len(target_runs) - 5} runs")
                return

            if not target_runs:
                print("Nenhuma run para processar.")
                return

            # Processar em lotes
            print(f"\nIniciando processamento de {len(target_runs)} runs...")

            if args.only_unclassified or not args.force_update:
                results = batch_classify_unclassified_runs(
                    project_id=args.project_id,
                    limit=args.limit,
                    skip_batches=args.skip_batches,
                    batch_size=args.batch_size
                )
            else:
                results = retroactively_classify_all_runs(
                    project_id=args.project_id,
                    force_update=args.force_update,
                    limit=args.limit,
                    skip_batches=args.skip_batches,
                    batch_size=args.batch_size
                )

            # Estatísticas finais
            total_processed = len(results)
            successful = sum(1 for r in results.values() if r is not None)
            failed = total_processed - successful

            print(f"\n=== Resultado ===")
            print(f"Total processadas: {total_processed}")
            print(f"Sucesso: {successful}")
            print(f"Falhas: {failed}")
            print(f"Taxa de sucesso: {(successful/total_processed*100):.1f}%" if total_processed > 0 else "N/A")

            # Mostrar distribuição de classificações
            if successful > 0:
                print(f"\n=== Distribuição de Classificações ===")

                response_types = {}
                brand_positions = {}
                question_types = {}
                funnel_stages = {}

                for result in results.values():
                    if result:
                        rt = result.response_type.value
                        bp = result.brand_positioning.value
                        qt = result.question_type.value
                        fs = result.funnel_stage.value

                        response_types[rt] = response_types.get(rt, 0) + 1
                        brand_positions[bp] = brand_positions.get(bp, 0) + 1
                        question_types[qt] = question_types.get(qt, 0) + 1
                        funnel_stages[fs] = funnel_stages.get(fs, 0) + 1

                print("Tipos de Resposta:")
                for rt, count in sorted(response_types.items()):
                    print(f"  {rt}: {count}")

                print("\nPosicionamento da Marca:")
                for bp, count in sorted(brand_positions.items()):
                    print(f"  {bp}: {count}")

                print("\nTipos de Pergunta:")
                for qt, count in sorted(question_types.items()):
                    print(f"  {qt}: {count}")

                print("\nEstágios de Funil:")
                for fs, count in sorted(funnel_stages.items()):
                    print(f"  {fs}: {count}")

    except Exception as e:
        print(f"Erro durante o processamento: {e}")
        sys.exit(1)

    print("\nClassificação concluída com sucesso!")


if __name__ == "__main__":
    main()
