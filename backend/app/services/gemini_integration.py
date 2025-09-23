"""
Integração do Gemini 2.0 Flash para Classificação Avançada
Versão aprimorada que usa IA generativa para análises mais precisas.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.models import Run, Domain, Evidence, Citation
from app.services.gemini_classifier import (
    GeminiZeroClickAnalyzer, GeminiAnalysisResult, analyze_with_gemini_classifier
)
from app.services.question_funnel_whitelist import RUN_IDS_ALLOWED_FOR_QUESTION_FUNNEL_UPDATE
from app.db.session import SessionLocal


class GeminiClassificationIntegrator:
    """Integrador usando Gemini 2.0 Flash para análise avançada"""

    def __init__(self, db: Session = None, use_gemini: bool = True):
        self.db = db or SessionLocal()
        self._should_close_db = db is None
        self.use_gemini = use_gemini

        if self.use_gemini:
            try:
                self.gemini_analyzer = GeminiZeroClickAnalyzer()
                print("[GEMINI_INTEGRATION] Gemini 2.0 Flash configurado com sucesso")
            except Exception as e:
                print(f"[GEMINI_INTEGRATION] Falha ao configurar Gemini: {e}")
                print("[GEMINI_INTEGRATION] Usando classificador local como fallback")
                self.use_gemini = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_db:
            self.db.close()

    def classify_and_update_run_with_gemini(self, run_id: str, response_text: str = None) -> Optional[GeminiAnalysisResult]:
        """
        Classifica uma run usando Gemini 2.0 Flash e atualiza no banco

        Args:
            run_id: ID da run
            response_text: Texto da resposta (opcional)

        Returns:
            GeminiAnalysisResult ou None se falhou
        """
        try:
            # Buscar a run no banco
            run = self.db.query(Run).filter(Run.id == run_id).first()
            if not run:
                print(f"[GEMINI_INTEGRATION] Run {run_id} não encontrada")
                return None

            # Obter dados necessários
            response_text = response_text or self._extract_response_from_evidences(run_id)
            if not response_text:
                print(f"[GEMINI_INTEGRATION] Nenhuma resposta encontrada para run {run_id}")
                return None

            citations = self._get_citations_for_run(run_id)
            prompt_text = self._get_prompt_text_for_run(run)

            if not prompt_text:
                print(f"[GEMINI_INTEGRATION] Prompt não encontrado para run {run_id}")
                return None

            # Executar análise com Gemini
            if self.use_gemini:
                result = self.gemini_analyzer.analyze_with_gemini(
                    prompt_text=prompt_text,
                    response_text=response_text,
                    citations=citations
                )
            else:
                # Fallback para análise local
                result = analyze_with_gemini_classifier(prompt_text, response_text, citations)

            # Atualizar a run no banco
            self._update_run_with_gemini_result(run, result)

            print(f"[GEMINI_INTEGRATION] Run {run_id} analisada: {result.response_type.value}/{result.brand_positioning.value} (confiança: {result.confidence:.2f})")
            return result

        except Exception as e:
            print(f"[GEMINI_INTEGRATION] Erro ao analisar run {run_id}: {e}")
            return None

    def batch_classify_with_gemini(self, run_ids: List[str], batch_size: int = 20) -> Dict[str, Optional[GeminiAnalysisResult]]:
        """
        Classifica múltiplas runs em lote com Gemini

        Args:
            run_ids: Lista de IDs das runs
            batch_size: Tamanho do lote (menor para evitar rate limits)

        Returns:
            Dicionário com resultados
        """
        results = {}
        total_runs = len(run_ids)

        for i in range(0, total_runs, batch_size):
            batch = run_ids[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_runs + batch_size - 1) // batch_size

            print(f"[GEMINI_INTEGRATION] Processando lote {batch_num}/{total_batches}: {len(batch)} runs")

            for j, run_id in enumerate(batch):
                print(f"[GEMINI_INTEGRATION] Analisando run {j+1}/{len(batch)}: {run_id}")

                results[run_id] = self.classify_and_update_run_with_gemini(run_id)

                # Pequena pausa para evitar rate limiting
                import time
                time.sleep(0.5)

            # Commit em lotes
            try:
                self.db.commit()
                print(f"[GEMINI_INTEGRATION] Lote {batch_num} commitado com sucesso")
            except Exception as e:
                print(f"[GEMINI_INTEGRATION] Erro ao commitar lote {batch_num}: {e}")
                self.db.rollback()

            # Pausa entre lotes
            if i + batch_size < total_runs:
                print(f"[GEMINI_INTEGRATION] Pausa entre lotes...")
                time.sleep(2.0)

        return results

    def get_gemini_insights_summary(self, project_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Gera resumo de insights estratégicos baseado nas análises do Gemini

        Args:
            project_id: ID do projeto
            days: Número de dias para análise

        Returns:
            Resumo de insights e sugestões
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Buscar runs recentes com classificação
        runs = self.db.query(Run).filter(
            Run.project_id == project_id,
            Run.status == "completed",
            Run.finished_at >= cutoff_date,
            Run.response_type.isnot(None)
        ).all()

        if not runs:
            return {"message": "Nenhuma run classificada encontrada no período"}

        # Análises agregadas
        total_runs = len(runs)
        high_value_runs = [r for r in runs if r.financial_value_score and r.financial_value_score >= 7.0]
        gap_runs = [r for r in runs if r.content_gap_detected]
        high_satisfaction = [r for r in runs if r.satisfaction_score and r.satisfaction_score >= 0.8]

        # Distribuições
        intent_distribution = {}
        positioning_distribution = {}
        for run in runs:
            if run.user_intent:
                intent_distribution[run.user_intent] = intent_distribution.get(run.user_intent, 0) + 1
            if run.brand_positioning:
                positioning_distribution[run.brand_positioning] = positioning_distribution.get(run.brand_positioning, 0) + 1

        # Oportunidades prioritárias
        priority_opportunities = []
        for run in gap_runs:
            if run.financial_value_score and run.financial_value_score >= 6.0:
                priority_opportunities.append({
                    "run_id": run.id,
                    "value_score": run.financial_value_score,
                    "competitive_mentions": run.competitive_mentions,
                    "intent": run.user_intent
                })

        priority_opportunities.sort(key=lambda x: x["value_score"], reverse=True)

        return {
            "analysis_period": f"Últimos {days} dias",
            "summary": {
                "total_runs_analyzed": total_runs,
                "high_value_opportunities": len(high_value_runs),
                "content_gaps_detected": len(gap_runs),
                "high_satisfaction_responses": len(high_satisfaction),
                "gap_percentage": round(len(gap_runs) / total_runs * 100, 1) if total_runs > 0 else 0
            },
            "intent_distribution": intent_distribution,
            "brand_positioning": positioning_distribution,
            "priority_opportunities": priority_opportunities[:10],  # Top 10
            "strategic_insights": [
                f"Detectados {len(gap_runs)} gaps de conteúdo em {total_runs} análises",
                f"{len(high_value_runs)} consultas de alto valor identificadas",
                f"Taxa de satisfação alta em {len(high_satisfaction)} respostas ({round(len(high_satisfaction)/total_runs*100, 1)}%)"
            ],
            "recommendations": [
                "Priorizar criação de conteúdo para gaps de alto valor",
                "Otimizar respostas para intenções transacionais",
                "Melhorar presença em comparações competitivas"
            ]
        }

    def _extract_response_from_evidences(self, run_id: str) -> Optional[str]:
        """Extrai texto da resposta das evidências"""
        evidences = self.db.query(Evidence).filter(Evidence.run_id == run_id).all()

        response_texts = []
        for evidence in evidences:
            if evidence.parsed_json:
                parsed = evidence.parsed_json
                if isinstance(parsed, dict):
                    # Extrair de diferentes estruturas
                    if "parsed" in parsed and isinstance(parsed["parsed"], dict):
                        if "text" in parsed["parsed"]:
                            response_texts.append(str(parsed["parsed"]["text"]))
                    elif "response" in parsed:
                        response_texts.append(str(parsed["response"]))
                    elif "text" in parsed:
                        response_texts.append(str(parsed["text"]))

        return " ".join(response_texts) if response_texts else None

    def _get_citations_for_run(self, run_id: str) -> List[Dict]:
        """Busca citações de uma run"""
        citations = self.db.query(Citation).filter(Citation.run_id == run_id).all()
        return [
            {
                "domain": citation.domain,
                "url": citation.url,
                "anchor": citation.anchor,
                "position": citation.position
            }
            for citation in citations
        ]

    def _get_prompt_text_for_run(self, run: Run) -> Optional[str]:
        """Busca o texto do prompt usado na run"""
        try:
            from app.models.models import PromptVersion
            prompt_version = self.db.query(PromptVersion).filter(
                PromptVersion.id == run.prompt_version_id
            ).first()
            return prompt_version.text if prompt_version else None
        except Exception:
            return None

    def _update_run_with_gemini_result(self, run: Run, result: GeminiAnalysisResult):
        """Atualiza run com resultado completo do Gemini"""
        # Classificação básica
        run.response_type = result.response_type.value
        run.sufficiency_level = result.sufficiency_level.value
        run.actionability_type = result.actionability_type.value
        run.trust_source = result.trust_source.value
        run.brand_positioning = result.brand_positioning.value
        if run.id in RUN_IDS_ALLOWED_FOR_QUESTION_FUNNEL_UPDATE:
            run.question_type = result.question_type.value
            run.funnel_stage = result.funnel_stage.value
        run.classification_confidence = result.confidence
        run.classified_at = datetime.utcnow()
        run.classification_version = "2.0-gemini"

        # Métricas avançadas
        run.user_intent = result.user_intent.value
        run.satisfaction_score = result.satisfaction_score
        run.competitive_mentions = result.competitive_mentions
        run.financial_value_score = result.financial_value_score
        run.content_gap_detected = result.content_gap_detected
        run.conversion_potential = result.conversion_potential.value

        # Salvar insights como JSON nos metadados (se necessário)
        # Pode ser usado para dashboard avançado
        insights_metadata = {
            "strategic_insights": result.strategic_insights,
            "optimization_suggestions": result.optimization_suggestions,
            "detailed_reasoning": result.reasoning,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }

        # Note: Se quiser persistir insights, adicione campo JSON na tabela ou crie tabela separada


# Funções de conveniência para uso externo
def classify_run_with_gemini(run_id: str, response_text: str = None) -> Optional[GeminiAnalysisResult]:
    """Classifica uma run usando Gemini"""
    with GeminiClassificationIntegrator() as integrator:
        return integrator.classify_and_update_run_with_gemini(run_id, response_text)

def batch_classify_with_gemini_service(project_id: str = None, limit: int = 500) -> Dict[str, Optional[GeminiAnalysisResult]]:
    """Classificação em lote usando Gemini"""
    with GeminiClassificationIntegrator() as integrator:
        # Buscar runs não classificadas ou com versão antiga
        query = integrator.db.query(Run.id).filter(
            Run.status == "completed",
            or_(
                Run.response_type.is_(None),
                Run.classification_version != "2.0-gemini"
            )
        )

        if project_id:
            query = query.filter(Run.project_id == project_id)

        run_ids = [row[0] for row in query.limit(limit).all()]

        if run_ids:
            print(f"[GEMINI_INTEGRATION] Iniciando análise de {len(run_ids)} runs com Gemini")
            return integrator.batch_classify_with_gemini(run_ids)
        else:
            print("[GEMINI_INTEGRATION] Nenhuma run para processar")
            return {}


def get_gemini_insights_for_project(project_id: str, days: int = 7) -> Dict[str, Any]:
    """Obtém insights do Gemini para um projeto"""
    with GeminiClassificationIntegrator() as integrator:
        return integrator.get_gemini_insights_summary(project_id, days)
