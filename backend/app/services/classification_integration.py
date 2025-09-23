"""
Integração do Sistema de Classificação com o Pipeline de Runs
Aplica classificação automática nas respostas e atualiza o banco de dados.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.models import Run, Domain, Evidence, Citation
from app.services.response_classifier import (
    CLASSIFIER_VERSION,
    classify_run_response,
    ClassificationResult,
)
from app.services.question_funnel_whitelist import RUN_IDS_ALLOWED_FOR_QUESTION_FUNNEL_UPDATE
from app.db.session import SessionLocal


class ClassificationIntegrator:
    """Integra o sistema de classificação com o pipeline de processamento de runs"""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self._should_close_db = db is None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_db:
            self.db.close()

    def classify_and_update_run(self, run_id: str, response_text: str = None) -> Optional[ClassificationResult]:
        """
        Classifica uma run e atualiza os campos no banco de dados

        Args:
            run_id: ID da run a ser classificada
            response_text: Texto da resposta (se não fornecido, busca das evidences)

        Returns:
            ClassificationResult ou None se falhou
        """
        try:
            # Buscar a run no banco
            run = self.db.query(Run).filter(Run.id == run_id).first()
            if not run:
                print(f"[CLASSIFICATION] Run {run_id} não encontrada")
                return None

            # Obter dados necessários para classificação
            response_text = response_text or self._extract_response_from_evidences(run_id)
            if not response_text:
                print(f"[CLASSIFICATION] Nenhuma resposta encontrada para run {run_id}")
                return None

            citations = self._get_citations_for_run(run_id)
            prompt_text = self._get_prompt_text_for_run(run)
            target_domains = self._get_target_domains_for_project(run.project_id)
            brand_keywords = self._get_brand_keywords_for_project(run.project_id)

            # Executar classificação
            result = classify_run_response(
                run_id=run_id,
                response_text=response_text,
                citations=citations,
                prompt_text=prompt_text,
                target_domains=target_domains,
                brand_keywords=brand_keywords
            )

            # Atualizar a run no banco
            self._update_run_classification(run, result)

            print(f"[CLASSIFICATION] Run {run_id} classificada: {result.response_type}/{result.brand_positioning}")
            return result

        except Exception as e:
            print(f"[CLASSIFICATION] Erro ao classificar run {run_id}: {e}")
            return None

    def classify_multiple_runs(self, run_ids: List[str], batch_size: int = 50, skip_batches: int = 0) -> Dict[str, Optional[ClassificationResult]]:
        """
        Classifica múltiplas runs em lote

        Args:
            run_ids: Lista de IDs das runs
            batch_size: Tamanho do lote para processamento

        Returns:
            Dicionário com resultados {run_id: ClassificationResult}
        """
        results = {}

        for i in range(0, len(run_ids), batch_size):
            batch_index = i // batch_size
            batch = run_ids[i:i + batch_size]

            if skip_batches and batch_index < skip_batches:
                print(f"[CLASSIFICATION] Pulando lote {batch_index + 1} (solicitado pelo parâmetro skip_batches)")
                continue

            print(f"[CLASSIFICATION] Processando lote {batch_index + 1}: {len(batch)} runs")

            for run_id in batch:
                results[run_id] = self.classify_and_update_run(run_id)

            # Commit em lotes
            try:
                self.db.commit()
                print(f"[CLASSIFICATION] Lote {batch_index + 1} commitado com sucesso")
            except Exception as e:
                print(f"[CLASSIFICATION] Erro ao commitar lote {batch_index + 1}: {e}")
                self.db.rollback()

        return results

    def get_unclassified_runs(self, project_id: str = None, limit: int = 1000) -> List[str]:
        """
        Busca runs que ainda não foram classificadas

        Args:
            project_id: Filtrar por projeto específico
            limit: Limite de runs a retornar

        Returns:
            Lista de IDs de runs não classificadas
        """
        query = self.db.query(Run.id).filter(
            Run.status == "completed",
            Run.response_type.is_(None)
        )

        if project_id:
            query = query.filter(Run.project_id == project_id)

        run_ids = [row[0] for row in query.limit(limit).all()]
        print(f"[CLASSIFICATION] Encontradas {len(run_ids)} runs não classificadas")
        return run_ids

    def reclassify_existing_runs(
        self,
        project_id: str = None,
        force_update: bool = False,
        limit: int = 1000,
        skip_batches: int = 0,
        batch_size: int = 50,
    ) -> Dict[str, Optional[ClassificationResult]]:
        """
        Reclassifica runs existentes (retroativo)

        Args:
            project_id: Filtrar por projeto específico
            force_update: Se True, reclassifica mesmo runs já classificadas
            limit: Limite de runs a processar

        Returns:
            Dicionário com resultados
        """
        query = self.db.query(Run.id).filter(Run.status == "completed")

        if not force_update:
            query = query.filter(Run.response_type.is_(None))

        if project_id:
            query = query.filter(Run.project_id == project_id)

        run_ids = [row[0] for row in query.limit(limit).all()]

        print(f"[CLASSIFICATION] Iniciando reclassificação de {len(run_ids)} runs")
        return self.classify_multiple_runs(
            run_ids,
            batch_size=batch_size,
            skip_batches=skip_batches,
        )

    def _extract_response_from_evidences(self, run_id: str) -> Optional[str]:
        """Extrai texto da resposta das evidências"""
        evidences = self.db.query(Evidence).filter(Evidence.run_id == run_id).all()

        response_texts = []
        for evidence in evidences:
            if not evidence.parsed_json:
                continue

            parsed = evidence.parsed_json
            if not isinstance(parsed, dict):
                continue

            # Formatos diretos
            if "response" in parsed:
                response_texts.append(str(parsed["response"]))
                continue
            if "answer" in parsed:
                response_texts.append(str(parsed["answer"]))
                continue
            if "content" in parsed:
                response_texts.append(str(parsed["content"]))
                continue
            if "text" in parsed:
                response_texts.append(str(parsed["text"]))
                continue

            # Estruturas aninhadas comuns (ex.: {"parsed": {"text": ...}})
            nested = parsed.get("parsed")
            if isinstance(nested, dict):
                text_val = nested.get("text") or nested.get("response")
                if text_val:
                    response_texts.append(str(text_val))
                    continue

            # Alguns providers guardam texto em raw -> message
            raw = parsed.get("raw")
            if isinstance(raw, dict):
                # Anthropic/OpenAI style -> raw["response"]["output"][...]
                if "text" in raw:
                    response_texts.append(str(raw["text"]))
                    continue
                raw_resp = raw.get("response")
                if isinstance(raw_resp, dict):
                    text_val = raw_resp.get("text")
                    if text_val:
                        response_texts.append(str(text_val))
                        continue
                    # Alguns modelos retornam lista em output
                    output = raw_resp.get("output")
                    if isinstance(output, list):
                        for item in output:
                            if isinstance(item, dict):
                                text_val = item.get("content") or item.get("text")
                                if text_val:
                                    response_texts.append(str(text_val))
                                    break

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
        # Buscar through the relationships
        if hasattr(run, 'prompt_version') and run.prompt_version:
            return run.prompt_version.text
        return None

    def _get_target_domains_for_project(self, project_id: str) -> List[str]:
        """Busca domínios alvo do projeto"""
        domains = self.db.query(Domain.domain).filter(Domain.project_id == project_id).all()
        return [domain[0] for domain in domains]

    def _get_brand_keywords_for_project(self, project_id: str) -> List[str]:
        """
        Busca palavras-chave da marca para o projeto
        Por enquanto retorna keywords padrão, mas pode ser configurável por projeto
        """
        # TODO: Implementar configuração de keywords por projeto
        # Por enquanto, usar keywords padrão baseadas nos domínios
        domains = self._get_target_domains_for_project(project_id)

        keywords = []
        for domain in domains:
            if "bb.com.br" in domain:
                keywords.extend(["Banco do Brasil", "BB", "Banco do Brasil S.A."])
            # Adicionar mais mapeamentos conforme necessário

        return keywords

    def _update_run_classification(self, run: Run, result: ClassificationResult):
        """Atualiza os campos de classificação no modelo Run"""
        run.response_type = result.response_type.value
        run.sufficiency_level = result.sufficiency_level.value
        run.actionability_type = result.actionability_type.value
        run.trust_source = result.trust_source.value
        run.brand_positioning = result.brand_positioning.value
        run.classification_confidence = result.confidence
        run.classified_at = datetime.utcnow()
        run.classification_version = CLASSIFIER_VERSION

        if run.id in RUN_IDS_ALLOWED_FOR_QUESTION_FUNNEL_UPDATE:
            run.question_type = result.question_type.value
            run.funnel_stage = result.funnel_stage.value

        # Calcular e aplicar métricas avançadas
        try:
            from app.services.advanced_metrics import analyze_run_advanced_metrics

            # Buscar dados necessários
            response_text = self._extract_response_from_evidences(run.id)
            prompt_text = self._get_prompt_text_for_run(run)
            citations = self._get_citations_for_run(run.id)

            if response_text and prompt_text:
                advanced_metrics = analyze_run_advanced_metrics(
                    prompt_text=prompt_text,
                    response_text=response_text,
                    citations=citations
                )

                # Aplicar métricas avançadas
                run.user_intent = advanced_metrics.user_intent.value
                run.satisfaction_score = advanced_metrics.satisfaction_score
                run.competitive_mentions = advanced_metrics.competitive_mentions
                run.financial_value_score = advanced_metrics.financial_value_score
                run.content_gap_detected = advanced_metrics.content_gap_detected
                run.conversion_potential = advanced_metrics.conversion_potential.value

        except Exception as e:
            print(f"[ADVANCED_METRICS] Erro ao calcular métricas avançadas para run {run.id}: {e}")
            # Continuar mesmo se métricas avançadas falharem


def classify_run_async(run_id: str, response_text: str = None) -> Optional[ClassificationResult]:
    """
    Função de conveniência para classificação assíncrona de uma run
    Pode ser usada em tasks do Celery
    """
    with ClassificationIntegrator() as integrator:
        return integrator.classify_and_update_run(run_id, response_text)


def batch_classify_unclassified_runs(
    project_id: str = None,
    limit: int = 1000,
    skip_batches: int = 0,
    batch_size: int = 50,
) -> Dict[str, Optional[ClassificationResult]]:
    """
    Função de conveniência para classificação em lote de runs não classificadas
    """
    with ClassificationIntegrator() as integrator:
        unclassified = integrator.get_unclassified_runs(project_id, limit)
        if unclassified:
            return integrator.classify_multiple_runs(
                unclassified,
                batch_size=batch_size,
                skip_batches=skip_batches,
            )
        return {}


def retroactively_classify_all_runs(
    project_id: str = None,
    force_update: bool = False,
    limit: int = 1000,
    skip_batches: int = 0,
    batch_size: int = 50,
) -> Dict[str, Optional[ClassificationResult]]:
    """
    Função de conveniência para classificação retroativa de todas as runs
    """
    with ClassificationIntegrator() as integrator:
        return integrator.reclassify_existing_runs(
            project_id,
            force_update,
            limit,
            skip_batches=skip_batches,
            batch_size=batch_size,
        )
