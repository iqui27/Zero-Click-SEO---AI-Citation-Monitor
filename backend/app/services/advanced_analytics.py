"""
Serviços de Analytics Avançadas para Métricas Zero-Click
Fornece KPIs agregados, análise competitiva e insights de negócio.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta

from app.models.models import Run, Citation, Domain, Project


class AdvancedAnalyticsService:
    """Serviço de analytics avançadas para métricas Zero-Click"""

    def __init__(self, db: Session):
        self.db = db

    def get_brand_presence_metrics(self, project_id: str,
                                 days: int = 30) -> Dict[str, Any]:
        """
        Métricas de presença da marca

        Returns:
            - % de consultas com BB citado
            - % de respostas com bb.com.br
            - Evolução temporal
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Total de runs completadas
        total_runs = self.db.query(func.count(Run.id)).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date
        ).scalar() or 0

        # Runs com marca como protagonista ou competidor
        brand_mentioned = self.db.query(func.count(Run.id)).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date,
            Run.brand_positioning.in_(["protagonista", "competidor"])
        ).scalar() or 0

        # Runs com domínio bb.com.br citado
        bb_domain_runs = self.db.query(func.count(Run.id.distinct())).join(Citation).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date,
            Citation.domain.like("%bb.com.br%")
        ).scalar() or 0

        # Evolução por dia (últimos 7 dias)
        daily_evolution = []
        for i in range(7):
            day_start = datetime.utcnow() - timedelta(days=i+1)
            day_end = datetime.utcnow() - timedelta(days=i)

            day_total = self.db.query(func.count(Run.id)).filter(
                Run.project_id == project_id,
                Run.status == "completed",
                Run.finished_at >= day_start,
                Run.finished_at < day_end
            ).scalar() or 0

            day_mentioned = self.db.query(func.count(Run.id)).filter(
                Run.project_id == project_id,
                Run.status == "completed",
                Run.finished_at >= day_start,
                Run.finished_at < day_end,
                Run.brand_positioning.in_(["protagonista", "competidor"])
            ).scalar() or 0

            daily_evolution.append({
                "date": day_start.date().isoformat(),
                "total_runs": day_total,
                "brand_mentioned": day_mentioned,
                "percentage": round((day_mentioned / day_total * 100) if day_total > 0 else 0, 1)
            })

        return {
            "period_days": days,
            "total_runs": total_runs,
            "brand_presence": {
                "mentioned_runs": brand_mentioned,
                "percentage": round((brand_mentioned / total_runs * 100) if total_runs > 0 else 0, 1)
            },
            "domain_presence": {
                "cited_runs": bb_domain_runs,
                "percentage": round((bb_domain_runs / total_runs * 100) if total_runs > 0 else 0, 1)
            },
            "daily_evolution": list(reversed(daily_evolution))  # Mais recente primeiro
        }

    def get_competitive_share_analysis(self, project_id: str,
                                     days: int = 30) -> Dict[str, Any]:
        """
        Análise de share competitivo

        Returns:
            - Menções por marca
            - Co-ocorrências
            - Gaps de conteúdo
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Runs com menções competitivas
        competitive_runs = self.db.query(
            Run.id,
            Run.competitive_mentions,
            Run.brand_positioning,
            Run.content_gap_detected
        ).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date,
            Run.competitive_mentions.isnot(None)
        ).all()

        total_competitive_runs = len(competitive_runs)
        runs_with_gaps = sum(1 for run in competitive_runs if run.content_gap_detected)

        # Distribuição de menções competitivas
        mention_distribution = {}
        for run in competitive_runs:
            mentions = run.competitive_mentions or 0
            mention_distribution[mentions] = mention_distribution.get(mentions, 0) + 1

        # Análise por posicionamento da marca
        positioning_analysis = self.db.query(
            Run.brand_positioning,
            func.count(Run.id).label('count'),
            func.avg(Run.competitive_mentions).label('avg_mentions')
        ).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date,
            Run.brand_positioning.isnot(None)
        ).group_by(Run.brand_positioning).all()

        return {
            "period_days": days,
            "competitive_landscape": {
                "total_runs_with_competitors": total_competitive_runs,
                "content_gaps_detected": runs_with_gaps,
                "gap_percentage": round((runs_with_gaps / total_competitive_runs * 100) if total_competitive_runs > 0 else 0, 1)
            },
            "mention_distribution": mention_distribution,
            "brand_positioning_analysis": [
                {
                    "positioning": row.brand_positioning,
                    "run_count": row.count,
                    "avg_competitive_mentions": round(float(row.avg_mentions or 0), 1)
                }
                for row in positioning_analysis
            ]
        }

    def get_satisfaction_and_quality_metrics(self, project_id: str,
                                           days: int = 30) -> Dict[str, Any]:
        """
        Métricas de satisfação e qualidade

        Returns:
            - Score médio de satisfação por LLM
            - Distribuição de qualidade
            - Correlação com citações
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Score médio por engine
        engine_satisfaction = self.db.query(
            Run.engine_id,
            func.avg(Run.satisfaction_score).label('avg_satisfaction'),
            func.avg(Run.classification_confidence).label('avg_confidence'),
            func.count(Run.id).label('run_count')
        ).join(
            self.db.query(Run.engine_id).distinct().subquery(),
            Run.engine_id == self.db.query(Run.engine_id).distinct().subquery().c.engine_id
        ).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date,
            Run.satisfaction_score.isnot(None)
        ).group_by(Run.engine_id).all()

        # Distribuição de níveis de suficiência
        sufficiency_distribution = self.db.query(
            Run.sufficiency_level,
            func.count(Run.id).label('count'),
            func.avg(Run.satisfaction_score).label('avg_satisfaction')
        ).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date,
            Run.sufficiency_level.isnot(None)
        ).group_by(Run.sufficiency_level).all()

        # Correlação entre satisfação e citações
        satisfaction_citation_correlation = self.db.query(
            func.avg(Run.satisfaction_score).label('avg_satisfaction'),
            func.avg(Run.citations_count).label('avg_citations'),
            func.avg(Run.our_citations_count).label('avg_our_citations')
        ).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date,
            Run.satisfaction_score.isnot(None)
        ).first()

        return {
            "period_days": days,
            "engine_performance": [
                {
                    "engine": row.engine_id,
                    "avg_satisfaction": round(float(row.avg_satisfaction or 0), 2),
                    "avg_confidence": round(float(row.avg_confidence or 0), 2),
                    "run_count": row.run_count
                }
                for row in engine_satisfaction
            ],
            "sufficiency_distribution": [
                {
                    "level": row.sufficiency_level,
                    "count": row.count,
                    "avg_satisfaction": round(float(row.avg_satisfaction or 0), 2)
                }
                for row in sufficiency_distribution
            ],
            "citation_correlation": {
                "avg_satisfaction": round(float(satisfaction_citation_correlation.avg_satisfaction or 0), 2),
                "avg_total_citations": round(float(satisfaction_citation_correlation.avg_citations or 0), 1),
                "avg_our_citations": round(float(satisfaction_citation_correlation.avg_our_citations or 0), 1)
            }
        }

    def get_conversion_and_value_metrics(self, project_id: str,
                                       days: int = 30) -> Dict[str, Any]:
        """
        Métricas de conversão e valor financeiro

        Returns:
            - Distribuição de potencial de conversão
            - Valor financeiro médio por intenção
            - Oportunidades identificadas
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Distribuição de potencial de conversão
        conversion_distribution = self.db.query(
            Run.conversion_potential,
            func.count(Run.id).label('count'),
            func.avg(Run.financial_value_score).label('avg_value')
        ).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date,
            Run.conversion_potential.isnot(None)
        ).group_by(Run.conversion_potential).all()

        # Valor por intenção do usuário
        intent_value_analysis = self.db.query(
            Run.user_intent,
            func.count(Run.id).label('count'),
            func.avg(Run.financial_value_score).label('avg_value'),
            func.avg(Run.satisfaction_score).label('avg_satisfaction')
        ).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date,
            Run.user_intent.isnot(None)
        ).group_by(Run.user_intent).all()

        # Oportunidades de alto valor com gaps
        high_value_opportunities = self.db.query(func.count(Run.id)).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date,
            Run.financial_value_score >= 7.0,
            Run.content_gap_detected == True
        ).scalar() or 0

        return {
            "period_days": days,
            "conversion_potential": [
                {
                    "level": row.conversion_potential,
                    "count": row.count,
                    "avg_financial_value": round(float(row.avg_value or 0), 1)
                }
                for row in conversion_distribution
            ],
            "intent_analysis": [
                {
                    "intent": row.user_intent,
                    "count": row.count,
                    "avg_financial_value": round(float(row.avg_value or 0), 1),
                    "avg_satisfaction": round(float(row.avg_satisfaction or 0), 2)
                }
                for row in intent_value_analysis
            ],
            "opportunities": {
                "high_value_gaps": high_value_opportunities,
                "description": f"{high_value_opportunities} consultas de alto valor com gaps de conteúdo detectados"
            }
        }

    def get_comprehensive_dashboard(self, project_id: str,
                                  days: int = 30) -> Dict[str, Any]:
        """
        Dashboard completo com todas as métricas principais
        """
        return {
            "project_id": project_id,
            "analysis_period": days,
            "generated_at": datetime.utcnow().isoformat(),
            "brand_presence": self.get_brand_presence_metrics(project_id, days),
            "competitive_analysis": self.get_competitive_share_analysis(project_id, days),
            "quality_metrics": self.get_satisfaction_and_quality_metrics(project_id, days),
            "value_metrics": self.get_conversion_and_value_metrics(project_id, days)
        }