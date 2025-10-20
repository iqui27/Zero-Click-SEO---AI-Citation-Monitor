"""Camada de compatibilidade para o pipeline de classificação baseado em Gemini."""

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import Run
from app.services.gemini_integration import (
    GeminiClassificationIntegrator,
    GeminiAnalysisResult,
)
from app.db.session import SessionLocal


CLASSIFIER_VERSION = "2.0-gemini"
ClassificationResult = GeminiAnalysisResult


class ClassificationIntegrator:
    """Adapter que delega toda a classificação para o integrador do Gemini."""

    def __init__(self, db: Session = None, use_gemini: bool = True):
        self.db = db or SessionLocal()
        self._should_close_db = db is None
        self.integrator = GeminiClassificationIntegrator(db=self.db, use_gemini=use_gemini)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_db:
            self.db.close()

    def classify_and_update_run(self, run_id: str, response_text: str = None) -> Optional[ClassificationResult]:
        try:
            result = self.integrator.classify_and_update_run_with_gemini(run_id, response_text)
            if result:
                print(
                    f"[CLASSIFICATION] Run {run_id} classificada via Gemini: "
                    f"{result.response_type.value}/{result.brand_positioning.value} "
                    f"(confiança: {result.confidence:.2f})"
                )
            return result
        except Exception as exc:
            print(f"[CLASSIFICATION] Erro ao classificar run {run_id} com Gemini: {exc}")
            return None

    def classify_multiple_runs(
        self,
        run_ids: List[str],
        batch_size: int = 50,
        skip_batches: int = 0,
    ) -> Dict[str, Optional[ClassificationResult]]:
        results: Dict[str, Optional[ClassificationResult]] = {}

        for i in range(0, len(run_ids), batch_size):
            batch_index = i // batch_size
            batch = run_ids[i : i + batch_size]

            if skip_batches and batch_index < skip_batches:
                print(
                    f"[CLASSIFICATION] Pulando lote {batch_index + 1} "
                    "(solicitado pelo parâmetro skip_batches)"
                )
                continue

            print(f"[CLASSIFICATION] Processando lote {batch_index + 1}: {len(batch)} runs")

            for run_id in batch:
                results[run_id] = self.classify_and_update_run(run_id)

            try:
                self.db.commit()
                print(f"[CLASSIFICATION] Lote {batch_index + 1} commitado com sucesso")
            except Exception as exc:
                print(f"[CLASSIFICATION] Erro ao commitar lote {batch_index + 1}: {exc}")
                self.db.rollback()

        return results

    def get_unclassified_runs(self, project_id: str = None, limit: int = 1000) -> List[str]:
        query = self.db.query(Run.id).filter(
            Run.status == "completed",
            Run.response_type.is_(None),
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


def classify_run_async(run_id: str, response_text: str = None) -> Optional[ClassificationResult]:
    with ClassificationIntegrator() as integrator:
        return integrator.classify_and_update_run(run_id, response_text)


def batch_classify_unclassified_runs(
    project_id: str = None,
    limit: int = 1000,
    skip_batches: int = 0,
    batch_size: int = 50,
) -> Dict[str, Optional[ClassificationResult]]:
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
    with ClassificationIntegrator() as integrator:
        return integrator.reclassify_existing_runs(
            project_id,
            force_update,
            limit,
            skip_batches=skip_batches,
            batch_size=batch_size,
        )
