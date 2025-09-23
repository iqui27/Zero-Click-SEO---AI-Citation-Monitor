#!/usr/bin/env python3
"""
Script para Análise Retroativa com Gemini 2.0 Flash
Versão avançada que usa IA generativa para insights mais profundos.
"""

import os
import sys
import argparse
import time
from pathlib import Path
from typing import Dict, List

# Adicionar o diretório backend ao Python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.gemini_integration import (
    GeminiClassificationIntegrator,
    batch_classify_with_gemini_service,
    get_gemini_insights_for_project
)
from app.db.session import SessionLocal


def main():
    parser = argparse.ArgumentParser(description='Análise Retroativa com Gemini 2.0 Flash')
    parser.add_argument(
        '--project-id',
        type=str,
        help='ID do projeto específico'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=500,
        help='Limite de runs a processar (padrão: 500)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=20,
        help='Tamanho do lote para evitar rate limits (padrão: 20)'
    )
    parser.add_argument(
        '--upgrade-existing',
        action='store_true',
        help='Migrar classificações básicas existentes para Gemini'
    )
    parser.add_argument(
        '--generate-insights',
        action='store_true',
        help='Gerar relatório de insights após classificação'
    )
    parser.add_argument(
        '--insights-days',
        type=int,
        default=30,
        help='Dias para análise de insights (padrão: 30)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Apenas mostrar o que seria processado'
    )
    parser.add_argument(
        '--delay-between-batches',
        type=float,
        default=3.0,
        help='Delay em segundos entre lotes (padrão: 3.0)'
    )

    args = parser.parse_args()

    print("=== 🚀 Análise Retroativa com Gemini 2.0 Flash ===")
    print(f"Projeto: {args.project_id or 'Todos'}")
    print(f"Limite: {args.limit}")
    print(f"Tamanho do lote: {args.batch_size}")
    print(f"Migrar existentes: {args.upgrade_existing}")
    print(f"Gerar insights: {args.generate_insights}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Verificar configuração da API do Gemini
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERRO: API key do Google/Gemini não configurada")
        print("Configure GOOGLE_API_KEY ou GEMINI_API_KEY no .env")
        sys.exit(1)

    print("✅ API key do Gemini configurada")

    try:
        with GeminiClassificationIntegrator() as integrator:
            # Verificar status atual
            print("\n📊 Analisando status atual...")

            db = SessionLocal()
            try:
                from app.models.models import Run
                from sqlalchemy import func, or_

                # Contar runs por status
                query_base = db.query(Run.id).filter(Run.status == "completed")
                if args.project_id:
                    query_base = query_base.filter(Run.project_id == args.project_id)

                total_runs = query_base.count()

                unclassified_runs = query_base.filter(Run.response_type.is_(None)).count()

                basic_classified = query_base.filter(
                    Run.classification_version == "1.0",
                    Run.response_type.isnot(None)
                ).count()

                gemini_classified = query_base.filter(
                    Run.classification_version == "2.0-gemini"
                ).count()

                print(f"Total de runs completadas: {total_runs}")
                print(f"Não classificadas: {unclassified_runs}")
                print(f"Classificação básica (v1.0): {basic_classified}")
                print(f"Classificação Gemini (v2.0): {gemini_classified}")

                # Determinar candidatos para processamento
                if args.upgrade_existing:
                    # Incluir tanto não classificadas quanto básicas
                    candidates_query = query_base.filter(
                        or_(
                            Run.response_type.is_(None),
                            Run.classification_version == "1.0"
                        )
                    )
                    target_description = "não classificadas + classificações básicas"
                else:
                    # Apenas não classificadas
                    candidates_query = query_base.filter(Run.response_type.is_(None))
                    target_description = "não classificadas"

                candidate_ids = [row[0] for row in candidates_query.limit(args.limit).all()]

            finally:
                db.close()

            print(f"\n🎯 Alvos para processamento ({target_description}): {len(candidate_ids)}")

            if args.dry_run:
                print(f"\n[DRY RUN] Seriam processadas {len(candidate_ids)} runs com Gemini")
                if candidate_ids:
                    print("Exemplos de IDs:")
                    for i, run_id in enumerate(candidate_ids[:5]):
                        print(f"  {i+1}. {run_id}")
                    if len(candidate_ids) > 5:
                        print(f"  ... e mais {len(candidate_ids) - 5} runs")

                print(f"\nConfiguração do processamento:")
                print(f"- Lotes de {args.batch_size} runs")
                print(f"- Delay de {args.delay_between_batches}s entre lotes")
                print(f"- Tempo estimado: {estimate_processing_time(len(candidate_ids), args.batch_size, args.delay_between_batches)}")
                return

            if not candidate_ids:
                print("✅ Nenhuma run para processar - todas já estão classificadas!")

                if args.generate_insights and args.project_id:
                    print(f"\n📈 Gerando insights para projeto {args.project_id}...")
                    generate_insights_report(args.project_id, args.insights_days)

                return

            # Confirmar processamento
            print(f"\n⚠️  Será executada análise com Gemini 2.0 Flash em {len(candidate_ids)} runs")
            print(f"Tempo estimado: {estimate_processing_time(len(candidate_ids), args.batch_size, args.delay_between_batches)}")

            if input("Deseja continuar? (s/N): ").lower() != 's':
                print("Operação cancelada.")
                return

            # Executar processamento
            print(f"\n🤖 Iniciando análise com Gemini...")
            start_time = time.time()

            results = batch_classify_with_gemini_service(
                project_id=args.project_id,
                limit=args.limit
            )

            end_time = time.time()
            processing_time = end_time - start_time

            # Estatísticas finais
            total_processed = len(results)
            successful = sum(1 for r in results.values() if r is not None)
            failed = total_processed - successful

            print(f"\n🎉 Processamento concluído!")
            print(f"⏱️  Tempo total: {processing_time/60:.1f} minutos")
            print(f"📊 Estatísticas:")
            print(f"  - Total processadas: {total_processed}")
            print(f"  - Sucesso: {successful}")
            print(f"  - Falhas: {failed}")
            print(f"  - Taxa de sucesso: {(successful/total_processed*100):.1f}%" if total_processed > 0 else "N/A")

            # Análise de resultados
            if successful > 0:
                analyze_gemini_results(results)

            # Gerar insights se solicitado
            if args.generate_insights and args.project_id:
                print(f"\n📈 Gerando relatório de insights...")
                generate_insights_report(args.project_id, args.insights_days)

    except Exception as e:
        print(f"❌ Erro durante o processamento: {e}")
        sys.exit(1)

    print("\n✅ Análise com Gemini concluída com sucesso!")


def estimate_processing_time(total_runs: int, batch_size: int, delay: float) -> str:
    """Estima tempo de processamento"""
    if total_runs == 0:
        return "0 minutos"

    num_batches = (total_runs + batch_size - 1) // batch_size
    avg_time_per_run = 2.0  # segundos por run (estimativa)
    total_time = (total_runs * avg_time_per_run) + (num_batches * delay)

    if total_time < 60:
        return f"{total_time:.0f} segundos"
    else:
        return f"{total_time/60:.1f} minutos"


def analyze_gemini_results(results: Dict) -> None:
    """Analisa resultados do processamento Gemini"""
    print(f"\n🔍 Análise dos Resultados:")

    successful_results = [r for r in results.values() if r is not None]

    if not successful_results:
        print("Nenhum resultado para analisar.")
        return

    # Distribuições
    response_types = {}
    brand_positions = {}
    user_intents = {}
    conversion_potentials = {}

    total_insights = []
    total_suggestions = []

    confidence_scores = []
    satisfaction_scores = []
    value_scores = []

    for result in successful_results:
        # Contadores
        rt = result.response_type.value
        bp = result.brand_positioning.value
        ui = result.user_intent.value
        cp = result.conversion_potential.value

        response_types[rt] = response_types.get(rt, 0) + 1
        brand_positions[bp] = brand_positions.get(bp, 0) + 1
        user_intents[ui] = user_intents.get(ui, 0) + 1
        conversion_potentials[cp] = conversion_potentials.get(cp, 0) + 1

        # Métricas
        confidence_scores.append(result.confidence)
        satisfaction_scores.append(result.satisfaction_score)
        value_scores.append(result.financial_value_score)

        # Insights
        total_insights.extend(result.strategic_insights)
        total_suggestions.extend(result.optimization_suggestions)

    # Exibir análises
    print(f"\n📈 Distribuições:")
    print(f"Tipos de Resposta: {dict(sorted(response_types.items(), key=lambda x: x[1], reverse=True))}")
    print(f"Posicionamento da Marca: {dict(sorted(brand_positions.items(), key=lambda x: x[1], reverse=True))}")
    print(f"Intenções do Usuário: {dict(sorted(user_intents.items(), key=lambda x: x[1], reverse=True))}")
    print(f"Potencial de Conversão: {dict(sorted(conversion_potentials.items(), key=lambda x: x[1], reverse=True))}")

    print(f"\n📊 Métricas Médias:")
    print(f"Confiança da Classificação: {sum(confidence_scores)/len(confidence_scores):.2f}")
    print(f"Score de Satisfação: {sum(satisfaction_scores)/len(satisfaction_scores):.2f}")
    print(f"Valor Financeiro: {sum(value_scores)/len(value_scores):.1f}")

    # Top insights únicos
    unique_insights = list(set(total_insights))[:10]
    unique_suggestions = list(set(total_suggestions))[:10]

    if unique_insights:
        print(f"\n💡 Top Insights Estratégicos:")
        for i, insight in enumerate(unique_insights, 1):
            print(f"  {i}. {insight}")

    if unique_suggestions:
        print(f"\n🎯 Top Sugestões de Otimização:")
        for i, suggestion in enumerate(unique_suggestions, 1):
            print(f"  {i}. {suggestion}")


def generate_insights_report(project_id: str, days: int) -> None:
    """Gera relatório de insights do projeto"""
    try:
        insights = get_gemini_insights_for_project(project_id, days)

        print(f"\n📋 Relatório de Insights - Projeto {project_id}")
        print(f"Período: Últimos {days} dias")

        summary = insights.get("summary", {})
        print(f"\n📊 Resumo:")
        print(f"  - Runs analisadas: {summary.get('total_runs_analyzed', 0)}")
        print(f"  - Oportunidades de alto valor: {summary.get('high_value_opportunities', 0)}")
        print(f"  - Gaps de conteúdo: {summary.get('content_gaps_detected', 0)}")
        print(f"  - Taxa de gaps: {summary.get('gap_percentage', 0)}%")

        strategic_insights = insights.get("strategic_insights", [])
        if strategic_insights:
            print(f"\n💡 Insights Estratégicos:")
            for i, insight in enumerate(strategic_insights, 1):
                print(f"  {i}. {insight}")

        recommendations = insights.get("recommendations", [])
        if recommendations:
            print(f"\n🎯 Recomendações:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")

        opportunities = insights.get("priority_opportunities", [])
        if opportunities:
            print(f"\n🔥 Top Oportunidades Prioritárias:")
            for i, opp in enumerate(opportunities[:5], 1):
                print(f"  {i}. Valor: {opp.get('financial_value', 0):.1f} | Intent: {opp.get('intent', 'N/A')} | Run: {opp.get('run_id', 'N/A')}")

    except Exception as e:
        print(f"❌ Erro ao gerar insights: {e}")


if __name__ == "__main__":
    main()