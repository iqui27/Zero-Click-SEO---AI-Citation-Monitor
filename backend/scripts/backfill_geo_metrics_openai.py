#!/usr/bin/env python3
"""
Script para calcular e popular métricas GEO para todas as runs da OpenAI.
Calcula indicadores de marca, posicionamento, engajamento e conversão.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import SessionLocal
from app.models.models import Run, Citation, Engine, Domain, Project, RunSemanticInsight, Evidence
from app.services.geo_metrics import calculate_all_geo_metrics
from sqlalchemy import func
import json


def backfill_geo_metrics_openai(limit: int = None, project_id: str = None, dry_run: bool = False):
    """
    Calcula métricas GEO para todas as runs da OpenAI.
    
    Args:
        limit: Número máximo de runs para processar (None = todas)
        project_id: Filtrar por projeto específico (None = todos)
        dry_run: Se True, apenas mostra o que seria feito sem salvar
    """
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("🌍 BACKFILL DE MÉTRICAS GEO - RUNS DA OPENAI")
        print("=" * 80)
        
        # Buscar runs da OpenAI completadas
        query = db.query(Run).join(Engine, Run.engine_id == Engine.id).filter(
            Engine.name == 'openai',
            Run.status == 'completed'
        )
        
        if project_id:
            query = query.filter(Run.project_id == project_id)
            print(f"\n📁 Filtrando por projeto: {project_id}")
        
        if limit:
            query = query.limit(limit)
            print(f"📊 Limitando a {limit} runs")
        
        runs = query.all()
        
        if not runs:
            print("\n⚠️  Nenhuma run da OpenAI completada encontrada.")
            return
        
        print(f"\n🔍 Encontradas {len(runs)} runs da OpenAI para processar")
        
        if dry_run:
            print("\n⚠️  MODO DRY-RUN: Nenhuma alteração será salva no banco")
        
        print("\nProcessando...")
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        # Estatísticas para relatório final
        stats = {
            'brand_mentions': [],
            'first_positions': [],
            'densities': [],
            'engagement_scores': [],
            'conversion_scores': [],
            'competitor_ratios': [],
            'cocitation_count': 0,
        }
        
        for i, run in enumerate(runs, 1):
            try:
                # Mostrar progresso
                if i % 50 == 0 or i == len(runs):
                    print(f"   Processando: {i}/{len(runs)} ({i/len(runs)*100:.1f}%)")
                
                # Buscar response_text da tabela evidences
                response_text = None
                evidence = db.query(Evidence).filter(Evidence.run_id == run.id).first()
                
                if evidence and evidence.parsed_json:
                    try:
                        parsed = json.loads(evidence.parsed_json) if isinstance(evidence.parsed_json, str) else evidence.parsed_json
                        response_text = parsed.get("parsed", {}).get("text", "")
                    except:
                        pass
                
                # Se não encontrou o texto, pular
                if not response_text or len(response_text) < 50:
                    skipped_count += 1
                    continue
                
                # Buscar citações da run
                citations_list = db.query(Citation).filter(Citation.run_id == run.id).all()
                citations_data = [
                    {
                        "domain": c.domain,
                        "url": c.url,
                        "is_ours": c.is_ours,
                        "position": c.position,
                        "anchor": c.anchor if hasattr(c, 'anchor') else None,
                    }
                    for c in citations_list
                ]
                
                # Buscar domínios do projeto
                project = db.query(Project).filter(Project.id == run.project_id).first()
                project_name = (project.name if project and project.name else "Marca") or "Marca"
                project_domains = []
                if project:
                    domains_list = db.query(Domain).filter(Domain.project_id == project.id).all()
                    project_domains = [d.domain for d in domains_list if d.domain]
                
                # Buscar competitors do Gemini semantic insights
                competitors_from_gemini = []
                semantic_insight = db.query(RunSemanticInsight).filter(
                    RunSemanticInsight.run_id == run.id
                ).first()
                
                if semantic_insight and semantic_insight.payload:
                    competitors_from_gemini = semantic_insight.payload.get("competitors", [])
                
                # Calcular métricas GEO
                geo_metrics = calculate_all_geo_metrics(
                    response_text=run.response_text,
                    project_name=project_name,
                    citations=citations_data,
                    competitors_from_gemini=competitors_from_gemini,
                    project_domains=project_domains,
                    brand_variations=None,  # TODO: adicionar se necessário
                    domain_variants_map=None,  # TODO: adicionar se necessário
                )
                
                # Atualizar run com métricas GEO
                if not dry_run:
                    # Métricas de marca
                    run.brand_mention_count = geo_metrics.get('brand_mention_count')
                    run.brand_first_mention_position = geo_metrics.get('brand_first_mention_position')
                    run.brand_mention_density = geo_metrics.get('brand_mention_density')
                    run.brand_prominence_score = geo_metrics.get('brand_prominence_score')
                    
                    # Métricas de engajamento
                    run.conversational_trigger_count = geo_metrics.get('conversational_trigger_count')
                    run.engagement_score = geo_metrics.get('engagement_score')
                    
                    # Métricas de conversão
                    run.conversion_potential_score = geo_metrics.get('conversion_potential_score')
                    run.conversion_potential = geo_metrics.get('conversion_potential')
                    
                    # Métricas de competição
                    run.competitor_mention_ratio = geo_metrics.get('competitor_mention_ratio')
                    run.share_of_voice_llm = geo_metrics.get('share_of_voice_llm')
                    
                    # Co-citação (JSON string)
                    cocitation = geo_metrics.get('cocitation_competitors', '[]')
                    if isinstance(cocitation, list):
                        run.cocitation_competitors = json.dumps(cocitation)
                    else:
                        run.cocitation_competitors = cocitation
                    
                    # Métricas de citação
                    run.citation_rate_observed = geo_metrics.get('citation_rate_observed')
                    run.citation_rate_corrected = geo_metrics.get('citation_rate_corrected')
                    
                    # Métricas avançadas
                    run.zero_click_presence = geo_metrics.get('zero_click_presence')
                    run.authority_score = geo_metrics.get('authority_score')
                    run.relevance_score = geo_metrics.get('relevance_score')
                    run.clarity_score = geo_metrics.get('clarity_score')
                    
                    # Categoria de produto
                    run.product_category = geo_metrics.get('product_category')
                    
                    # Qualidade de citação
                    run.citation_quality_score = geo_metrics.get('citation_quality_score')
                    run.first_citation_position = geo_metrics.get('first_citation_position')
                    
                    db.commit()
                
                # Coletar estatísticas
                if geo_metrics.get('brand_mention_count') is not None:
                    stats['brand_mentions'].append(geo_metrics['brand_mention_count'])
                if geo_metrics.get('brand_first_mention_position') is not None:
                    stats['first_positions'].append(geo_metrics['brand_first_mention_position'])
                if geo_metrics.get('brand_mention_density') is not None:
                    stats['densities'].append(geo_metrics['brand_mention_density'])
                if geo_metrics.get('engagement_score') is not None:
                    stats['engagement_scores'].append(geo_metrics['engagement_score'])
                if geo_metrics.get('conversion_potential_score') is not None:
                    stats['conversion_scores'].append(geo_metrics['conversion_potential_score'])
                if geo_metrics.get('competitor_mention_ratio') is not None:
                    stats['competitor_ratios'].append(geo_metrics['competitor_mention_ratio'])
                if geo_metrics.get('cocitation_competitors'):
                    stats['cocitation_count'] += 1
                
                success_count += 1
                
            except Exception as e:
                print(f"\n   ❌ Erro na run {run.id}: {e}")
                # Mostrar traceback completo para debug
                import traceback
                if error_count < 3:  # Mostrar apenas os 3 primeiros erros completos
                    traceback.print_exc()
                error_count += 1
                if not dry_run:
                    db.rollback()
        
        print("\n✅ Processamento concluído!")
        print("=" * 80)
        print(f"\n📊 Resumo:")
        print(f"   Processadas com sucesso: {success_count}")
        print(f"   Ignoradas (sem texto):   {skipped_count}")
        print(f"   Erros:                   {error_count}")
        
        # Estatísticas finais
        if success_count > 0 and stats['brand_mentions']:
            print(f"\n📈 Estatísticas das Métricas GEO:")
            print(f"   Menções de marca (média):        {sum(stats['brand_mentions']) / len(stats['brand_mentions']):.2f}")
            
            if stats['first_positions']:
                print(f"   Primeira posição (média):        {sum(stats['first_positions']) / len(stats['first_positions']):.1f}")
            
            if stats['densities']:
                print(f"   Densidade de menções (média):    {sum(stats['densities']) / len(stats['densities']):.2%}")
            
            if stats['engagement_scores']:
                print(f"   Score de engajamento (média):    {sum(stats['engagement_scores']) / len(stats['engagement_scores']):.2f}")
            
            if stats['conversion_scores']:
                print(f"   Score de conversão (média):      {sum(stats['conversion_scores']) / len(stats['conversion_scores']):.2f}")
            
            if stats['competitor_ratios']:
                print(f"   Ratio de competidores (média):   {sum(stats['competitor_ratios']) / len(stats['competitor_ratios']):.2f}")
            
            print(f"   Runs com co-citação:             {stats['cocitation_count']} ({stats['cocitation_count']/success_count*100:.1f}%)")
        
        if dry_run:
            print("\n⚠️  MODO DRY-RUN: Nenhuma alteração foi salva no banco")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill de métricas GEO para runs da OpenAI')
    parser.add_argument('--limit', type=int, help='Número máximo de runs para processar')
    parser.add_argument('--project-id', type=str, help='ID do projeto para filtrar')
    parser.add_argument('--dry-run', action='store_true', help='Modo dry-run (não salva alterações)')
    
    args = parser.parse_args()
    
    backfill_geo_metrics_openai(
        limit=args.limit,
        project_id=args.project_id,
        dry_run=args.dry_run
    )
