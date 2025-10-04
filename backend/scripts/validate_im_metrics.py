#!/usr/bin/env python3
"""
Script de validação das métricas IM-SEO e IM-SEOIA.
Verifica se as métricas estão sendo calculadas corretamente.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.session import SessionLocal
from app.models.models import Run
from sqlalchemy import func


def validate_im_metrics():
    """Valida o status das métricas IM nas runs."""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("📊 VALIDAÇÃO DE MÉTRICAS IM-SEO E IM-SEOIA")
        print("=" * 60)
        
        # Contar runs totais
        total = db.query(Run).filter(Run.status == 'completed').count()
        print(f"\n✅ Total de runs completadas: {total}")
        
        if total == 0:
            print("\n⚠️  Nenhuma run completada encontrada.")
            print("   Execute algumas runs primeiro para testar as métricas.")
            return
        
        # Contar runs com métricas IM
        with_im_seo = db.query(Run).filter(
            Run.status == 'completed',
            Run.im_seo_score.isnot(None)
        ).count()
        
        with_im_seoia = db.query(Run).filter(
            Run.status == 'completed',
            Run.im_seoia_score.isnot(None)
        ).count()
        
        with_eeat = db.query(Run).filter(
            Run.status == 'completed',
            Run.eeat_score.isnot(None)
        ).count()
        
        with_ia_ready = db.query(Run).filter(
            Run.status == 'completed',
            Run.ia_ready_score.isnot(None)
        ).count()
        
        with_irzc = db.query(Run).filter(
            Run.status == 'completed',
            Run.irzc_score.isnot(None)
        ).count()
        
        print(f"\n📈 Cobertura de Métricas:")
        print(f"   IM-SEO:     {with_im_seo}/{total} ({with_im_seo/total*100:.1f}%)")
        print(f"   IM-SEOIA:   {with_im_seoia}/{total} ({with_im_seoia/total*100:.1f}%)")
        print(f"   E-E-A-T:    {with_eeat}/{total} ({with_eeat/total*100:.1f}%)")
        print(f"   IA-Ready:   {with_ia_ready}/{total} ({with_ia_ready/total*100:.1f}%)")
        print(f"   IRZC:       {with_irzc}/{total} ({with_irzc/total*100:.1f}%)")
        
        # Calcular médias
        if with_im_seo > 0:
            stats = db.query(
                func.avg(Run.im_seo_score).label('avg_im_seo'),
                func.min(Run.im_seo_score).label('min_im_seo'),
                func.max(Run.im_seo_score).label('max_im_seo'),
                func.avg(Run.im_seoia_score).label('avg_im_seoia'),
                func.min(Run.im_seoia_score).label('min_im_seoia'),
                func.max(Run.im_seoia_score).label('max_im_seoia'),
                func.avg(Run.eeat_score).label('avg_eeat'),
                func.avg(Run.irzc_score).label('avg_irzc'),
                func.avg(Run.ia_ready_score).label('avg_ia_ready'),
            ).filter(
                Run.status == 'completed',
                Run.im_seo_score.isnot(None)
            ).first()
            
            print(f"\n📊 Estatísticas Gerais:")
            print(f"\n   IM-SEO:")
            print(f"      Média: {stats.avg_im_seo:.2f}")
            print(f"      Min:   {stats.min_im_seo:.2f}")
            print(f"      Max:   {stats.max_im_seo:.2f}")
            
            print(f"\n   IM-SEOIA:")
            print(f"      Média: {stats.avg_im_seoia:.2f}")
            print(f"      Min:   {stats.min_im_seoia:.2f}")
            print(f"      Max:   {stats.max_im_seoia:.2f}")
            
            print(f"\n   Sub-Métricas (Médias):")
            print(f"      E-E-A-T:    {stats.avg_eeat:.2f}")
            print(f"      IRZC:       {stats.avg_irzc:.2f}")
            print(f"      IA-Ready:   {stats.avg_ia_ready:.2f}")
            
            # Distribuição de scores
            excellent_im_seo = db.query(func.count(Run.id)).filter(
                Run.status == 'completed',
                Run.im_seo_score >= 80
            ).scalar() or 0
            
            good_im_seo = db.query(func.count(Run.id)).filter(
                Run.status == 'completed',
                Run.im_seo_score >= 60,
                Run.im_seo_score < 80
            ).scalar() or 0
            
            fair_im_seo = db.query(func.count(Run.id)).filter(
                Run.status == 'completed',
                Run.im_seo_score >= 40,
                Run.im_seo_score < 60
            ).scalar() or 0
            
            poor_im_seo = db.query(func.count(Run.id)).filter(
                Run.status == 'completed',
                Run.im_seo_score < 40
            ).scalar() or 0
            
            print(f"\n   Distribuição IM-SEO:")
            print(f"      Excelente (80-100): {excellent_im_seo}")
            print(f"      Bom (60-79):        {good_im_seo}")
            print(f"      Regular (40-59):    {fair_im_seo}")
            print(f"      Ruim (0-39):        {poor_im_seo}")
            
            # Verificar integridade dos dados
            print(f"\n🔍 Verificação de Integridade:")
            
            invalid_scores = db.query(func.count(Run.id)).filter(
                Run.status == 'completed',
                or_(
                    Run.im_seo_score < 0,
                    Run.im_seo_score > 100,
                    Run.im_seoia_score < 0,
                    Run.im_seoia_score > 100
                )
            ).scalar() or 0
            
            if invalid_scores > 0:
                print(f"   ⚠️  {invalid_scores} runs com scores inválidos (fora de 0-100)")
            else:
                print(f"   ✅ Todos os scores estão no intervalo válido (0-100)")
            
            # Verificar runs com response_text
            with_response_text = db.query(func.count(Run.id)).filter(
                Run.status == 'completed',
                Run.response_text.isnot(None)
            ).scalar() or 0
            
            print(f"   ✅ {with_response_text}/{total} runs com response_text salvo")
            
        else:
            print("\n⚠️  Nenhuma métrica IM calculada ainda.")
            print("   As métricas serão calculadas automaticamente nas próximas runs.")
            print("   Para recalcular runs existentes, use:")
            print("   python scripts/recalculate_im_metrics.py")
        
        print("\n" + "=" * 60)
        print("✅ Validação concluída!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Erro durante validação: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    from sqlalchemy import or_
    validate_im_metrics()
