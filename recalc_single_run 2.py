#!/usr/bin/env python3
"""Recalcula métricas de uma run específica."""

import sys
sys.path.insert(0, 'backend')

from app.db.session import SessionLocal
from app.models.models import Run, Citation, Evidence, Domain, Project
from app.services.im_metrics_simple import SimpleIMMetrics

run_id = "run_60073db0"

db = SessionLocal()
try:
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        print(f"❌ Run {run_id} não encontrada")
        sys.exit(1)
    
    print(f"✅ Run encontrada: {run.id}")
    print(f"   Status: {run.status}")
    
    # Buscar citações
    citations_list = db.query(Citation).filter(Citation.run_id == run.id).all()
    citations_data = [{"domain": c.domain, "url": c.url, "is_ours": c.is_ours} for c in citations_list]
    print(f"   Citações: {len(citations_list)}")
    
    # Buscar dados SERP
    serp_data = None
    project_domains = []
    target_url = None
    
    evidence = db.query(Evidence).filter(Evidence.run_id == run.id).first()
    if evidence and evidence.parsed_json:
        serp_data = evidence.parsed_json.get("raw", {})
        print(f"   SERP data: {'✅ Disponível' if serp_data else '❌ Não encontrado'}")
    
    # Buscar domínios do projeto
    project = db.query(Project).filter(Project.id == run.project_id).first()
    if project:
        domains_list = db.query(Domain).filter(Domain.project_id == project.id).all()
        project_domains = [d.domain for d in domains_list]
        print(f"   Domínios do projeto: {len(project_domains)}")
    
    # URL alvo
    for cit in citations_data:
        if cit.get("is_ours"):
            target_url = cit.get("url")
            break
    print(f"   URL alvo: {target_url or 'Não encontrada'}")
    
    # Calcular métricas
    print("\n🔄 Calculando métricas...")
    run_data = {"amr_flag": run.amr_flag, "dcr_flag": run.dcr_flag, "zcrs": run.zcrs}
    im_metrics = SimpleIMMetrics.calculate_all(
        run_data, citations_data, run.response_text,
        serp_data=serp_data, project_domains=project_domains, target_url=target_url
    )
    
    # Atualizar run
    run.im_seo_score = im_metrics["im_seo_score"]
    run.im_seoia_score = im_metrics["im_seoia_score"]
    run.core_web_vitals_score = im_metrics["core_web_vitals_score"]
    run.lcp_score = im_metrics.get("lcp_score")
    run.fid_score = im_metrics.get("fid_score")
    run.cls_score = im_metrics.get("cls_score")
    run.share_of_voice_serp = im_metrics["share_of_voice_serp"]
    
    # SERP metrics
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
    
    # IA-Ready
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
    run.entities_detected = entities["detected"]
    run.entities_relevance_score = entities["relevance_score"]
    run.entity_connection_score = entities["connection_score"]
    
    db.commit()
    
    print(f"\n✅ Métricas calculadas com sucesso!")
    print(f"   IM-SEO: {run.im_seo_score}")
    print(f"   IM-SEOIA: {run.im_seoia_score}")
    print(f"   Core Web Vitals: {run.core_web_vitals_score}")
    print(f"   Share of Voice: {run.share_of_voice_serp}")
    print(f"   SERP Features: {run.serp_features_presence}")
    print(f"   E-E-A-T: {run.eeat_score}")
    print(f"   IA-Ready: {run.ia_ready_score}")
    print(f"   IRZC: {run.irzc_score}")
    
except Exception as e:
    print(f"\n❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
