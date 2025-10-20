#!/usr/bin/env python3
"""
Script para recalcular métricas IM-SEO e IM-SEOIA em runs existentes.
Útil após ajustes nos algoritmos de cálculo ou para processar runs antigas.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import SessionLocal
from app.models.models import Run, Citation, Evidence, Domain, Project
from app.services.im_metrics_simple import SimpleIMMetrics
from app.services.kpis import compute_run_report
from app.services.evidence_payload import load_evidence_payload
from sqlalchemy import func


def recalculate_all_metrics(limit: int = None, project_id: str = None):
    """
    Recalcula métricas para todas as runs completadas.
    
    Args:
        limit: Número máximo de runs para processar (None = todas)
        project_id: Filtrar por projeto específico (None = todos)
    """
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("🔄 RECÁLCULO DE MÉTRICAS IM-SEO E IM-SEOIA")
        print("=" * 60)
        
        # Buscar runs completadas
        query = db.query(Run).filter(Run.status == 'completed')
        
        if project_id:
            query = query.filter(Run.project_id == project_id)
            print(f"\n📁 Filtrando por projeto: {project_id}")
        
        if limit:
            query = query.limit(limit)
            print(f"📊 Limitando a {limit} runs")
        
        runs = query.all()
        
        if not runs:
            print("\n⚠️  Nenhuma run completada encontrada.")
            return
        
        print(f"\n🔍 Encontradas {len(runs)} runs para recalcular")
        print("\nProcessando...")
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for i, run in enumerate(runs, 1):
            try:
                # Mostrar progresso a cada 10 runs
                if i % 10 == 0 or i == len(runs):
                    print(f"   Processando: {i}/{len(runs)} ({i/len(runs)*100:.1f}%)")
                
                # Buscar citações da run
                citations_list = db.query(Citation).filter(Citation.run_id == run.id).all()
                citations_data = [
                    {
                        "domain": c.domain,
                        "url": c.url,
                        "is_ours": c.is_ours,
                    }
                    for c in citations_list
                ]
                
                # Preparar dados da run
                run_data = {
                    "amr_flag": run.amr_flag,
                    "dcr_flag": run.dcr_flag,
                    "zcrs": run.zcrs,
                }
                
                # Buscar dados do SerpAPI e domínios do projeto
                serp_data = None
                project_domains = []
                target_url = None
                try:
                    # Buscar evidence para extrair dados SERP
                    evidence = db.query(Evidence).filter(Evidence.run_id == run.id).first()
                    if evidence:
                        payload = load_evidence_payload(evidence)
                        if isinstance(payload, dict):
                            serp_data = payload.get("raw", {})

                            # Se não tem response_text, tentar extrair do payload
                            if not run.response_text:
                                try:
                                    parsed = payload.get("parsed", {}) if isinstance(payload.get("parsed"), dict) else {}
                                    response_text = parsed.get("text")
                                    if response_text:
                                        run.response_text = str(response_text)[:50000]
                                except Exception:
                                    pass
                        if not run.response_text and (evidence.response_text or "").strip():
                            run.response_text = str(evidence.response_text)[:50000]
                    
                    # Buscar domínios do projeto
                    project = db.query(Project).filter(Project.id == run.project_id).first()
                    if project:
                        domains_list = db.query(Domain).filter(Domain.project_id == project.id).all()
                        project_domains = [d.domain for d in domains_list]
                    
                    # Tentar extrair URL alvo das citações (primeira citação nossa)
                    for cit in citations_data:
                        if cit.get("is_ours"):
                            target_url = cit.get("url")
                            break
                    
                    # Se não houver citação nossa, usar domínio primário do projeto como fallback
                    if not target_url and project_domains:
                        primary_domain = db.query(Domain).filter(
                            Domain.project_id == project.id,
                            Domain.is_primary == True
                        ).first()
                        if primary_domain:
                            target_url = f"https://{primary_domain.domain}"
                        elif project_domains:
                            target_url = f"https://{project_domains[0]}"
                except Exception as e:
                    print(f"\n   ⚠️  Erro ao buscar dados SERP para run {run.id}: {e}")
                
                response_text = run.response_text
                if not response_text:
                    skipped_count += 1
                    continue
                
                # Calcular métricas (com SerpAPI e PageSpeed se disponíveis)
                im_metrics = SimpleIMMetrics.calculate_all(
                    run_data, 
                    citations_data, 
                    response_text,
                    serp_data=serp_data,
                    project_domains=project_domains,
                    target_url=target_url
                )
                
                # Atualizar run
                run.im_seo_score = im_metrics["im_seo_score"]
                run.im_seoia_score = im_metrics["im_seoia_score"]
                run.core_web_vitals_score = im_metrics["core_web_vitals_score"]
                run.lcp_score = im_metrics.get("lcp_score")
                run.fid_score = im_metrics.get("fid_score")
                run.cls_score = im_metrics.get("cls_score")
                run.share_of_voice_serp = im_metrics["share_of_voice_serp"]
                
                # Métricas do SerpAPI
                run.serp_features_presence = im_metrics.get("serp_features_presence")
                run.ia_resources_detected = im_metrics.get("ia_resources_detected")
                run.ia_serp_presence_score = im_metrics.get("ia_serp_presence_score")
                run.long_tail_terms_top10 = im_metrics.get("longtail_terms_top10")
                run.long_tail_terms_top20 = im_metrics.get("longtail_terms_top20")
                run.long_tail_coverage_score = im_metrics.get("longtail_coverage_score")
                run.schema_types_detected = im_metrics.get("schema_types_detected")
                run.schema_coverage_score = im_metrics.get("schema_coverage_score")
                
                # E-E-A-T
                eeat = im_metrics["eeat"]
                run.eeat_score = eeat["overall"]
                run.eeat_expertise = eeat["expertise"]
                run.eeat_experience = eeat["experience"]
                run.eeat_authoritativeness = eeat["authoritativeness"]
                run.eeat_trustworthiness = eeat["trustworthiness"]
                
                # IA-Ready Blocks
                ia_ready = im_metrics["ia_ready"]
                run.ia_ready_score = ia_ready["score"]
                run.ia_ready_blocks_count = ia_ready["blocks_count"]
                run.has_lists = ia_ready["has_lists"]
                run.has_faqs = ia_ready["has_faqs"]
                run.has_tables = ia_ready["has_tables"]
                run.has_step_by_step = ia_ready["has_step_by_step"]
                
                # IRZC
                irzc = im_metrics["irzc"]
                run.irzc_score = irzc["score"]
                run.ctr_expected = irzc["ctr_expected"]
                
                # Entidades
                entities = im_metrics["entities"]
                run.entities_relevance_score = entities["relevance_score"]
                run.entity_connection_score = entities["connection_score"]
                
                db.commit()
                success_count += 1
                
                # Atualizar KPIs de citações (AMR/DCR/ZCRS)
                try:
                    compute_run_report(db, run.id)
                except Exception as e:
                    print(f"\n   ⚠️  Erro ao recalcular KPIs (AMR/DCR) da run {run.id}: {e}")
                    db.rollback()
                    continue

            except Exception as e:
                print(f"\n   ❌ Erro na run {run.id}: {e}")
                error_count += 1
                db.rollback()
        
        print("✅ Recálculo concluído!")
        print("=" * 60)
        print(f"\n📊 Resumo:")
        print(f"   Processadas com sucesso: {success_count}")
        print(f"   Ignoradas (sem texto):   {skipped_count}")
        print(f"   Erros:                   {error_count}")
        
        # Estatísticas finais
        if success_count > 0:
            stats = db.query(
                func.avg(Run.im_seo_score).label('avg_im_seo'),
                func.avg(Run.im_seoia_score).label('avg_im_seoia'),
                func.avg(Run.eeat_score).label('avg_eeat'),
                func.avg(Run.irzc_score).label('avg_irzc')
            ).filter(
                Run.status == 'completed',
                Run.im_seo_score.isnot(None)
            ).first()
            
            print(f"\n📈 Estatísticas Gerais:")
            print(f"   IM-SEO médio:   {stats.avg_im_seo:.2f}")
            print(f"   IM-SEOIA médio: {stats.avg_im_seoia:.2f}")
            print(f"   E-E-A-T médio:  {stats.avg_eeat:.2f}")
            print(f"   IRZC médio:     {stats.avg_irzc:.2f}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Recalcula métricas IM-SEO e IM-SEOIA')
    parser.add_argument('--limit', type=int, help='Número máximo de runs para processar')
    parser.add_argument('--project-id', type=str, help='ID do projeto para filtrar')
    
    args = parser.parse_args()
    
    recalculate_all_metrics(limit=args.limit, project_id=args.project_id)
