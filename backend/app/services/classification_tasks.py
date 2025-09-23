"""
Tasks do Celery para processamento de classificação em background
"""

from celery import Celery
from app.services.classification_integration import (
    classify_run_async,
    batch_classify_unclassified_runs,
    retroactively_classify_all_runs
)


def create_classification_tasks(celery_app: Celery):
    """Cria tasks de classificação no app Celery"""

    @celery_app.task(name="classification.classify_single_run")
    def classify_single_run_task(run_id: str, response_text: str = None):
        """
        Task para classificar uma única run em background

        Args:
            run_id: ID da run
            response_text: Texto da resposta (opcional)

        Returns:
            Dict com resultado da classificação
        """
        try:
            result = classify_run_async(run_id, response_text)

            if result:
                return {
                    "success": True,
                    "run_id": run_id,
                    "classification": {
                        "response_type": result.response_type.value,
                        "sufficiency_level": result.sufficiency_level.value,
                        "actionability_type": result.actionability_type.value,
                        "trust_source": result.trust_source.value,
                        "brand_positioning": result.brand_positioning.value,
                        "confidence": result.confidence
                    }
                }
            else:
                return {
                    "success": False,
                    "run_id": run_id,
                    "error": "Classification failed"
                }

        except Exception as e:
            return {
                "success": False,
                "run_id": run_id,
                "error": str(e)
            }

    @celery_app.task(name="classification.batch_classify_project")
    def batch_classify_project_task(project_id: str, force_update: bool = False, limit: int = 1000):
        """
        Task para classificar todas as runs de um projeto em background

        Args:
            project_id: ID do projeto
            force_update: Se deve reclassificar runs já classificadas
            limit: Limite de runs a processar

        Returns:
            Dict com estatísticas do processamento
        """
        try:
            results = retroactively_classify_all_runs(
                project_id=project_id,
                force_update=force_update,
                limit=limit
            )

            total_processed = len(results)
            successful = sum(1 for r in results.values() if r is not None)
            failed = total_processed - successful

            return {
                "success": True,
                "project_id": project_id,
                "total_processed": total_processed,
                "successful": successful,
                "failed": failed,
                "force_update": force_update,
                "limit": limit
            }

        except Exception as e:
            return {
                "success": False,
                "project_id": project_id,
                "error": str(e)
            }

    @celery_app.task(name="classification.batch_classify_unclassified")
    def batch_classify_unclassified_task(project_id: str = None, limit: int = 1000):
        """
        Task para classificar runs não classificadas em background

        Args:
            project_id: ID do projeto (opcional, se None classifica de todos)
            limit: Limite de runs a processar

        Returns:
            Dict com estatísticas do processamento
        """
        try:
            results = batch_classify_unclassified_runs(
                project_id=project_id,
                limit=limit
            )

            total_processed = len(results)
            successful = sum(1 for r in results.values() if r is not None)
            failed = total_processed - successful

            return {
                "success": True,
                "project_id": project_id,
                "total_processed": total_processed,
                "successful": successful,
                "failed": failed,
                "limit": limit
            }

        except Exception as e:
            return {
                "success": False,
                "project_id": project_id,
                "error": str(e)
            }

    @celery_app.task(name="classification.periodic_classification")
    def periodic_classification_task(batch_size: int = 100):
        """
        Task periódica para classificar runs não classificadas
        Pode ser chamada por um scheduler/cron

        Args:
            batch_size: Tamanho do lote a processar

        Returns:
            Dict com estatísticas do processamento
        """
        try:
            results = batch_classify_unclassified_runs(
                project_id=None,  # Todas os projetos
                limit=batch_size
            )

            total_processed = len(results)
            successful = sum(1 for r in results.values() if r is not None)
            failed = total_processed - successful

            return {
                "success": True,
                "type": "periodic",
                "total_processed": total_processed,
                "successful": successful,
                "failed": failed,
                "batch_size": batch_size
            }

        except Exception as e:
            return {
                "success": False,
                "type": "periodic",
                "error": str(e)
            }

    return {
        "classify_single_run": classify_single_run_task,
        "batch_classify_project": batch_classify_project_task,
        "batch_classify_unclassified": batch_classify_unclassified_task,
        "periodic_classification": periodic_classification_task
    }


# Funções de conveniência para enfileirar tasks
def enqueue_single_run_classification(run_id: str, response_text: str = None):
    """Enfileira classificação de uma run específica"""
    from celery_app import celery_app
    return celery_app.send_task(
        "classification.classify_single_run",
        args=[run_id, response_text]
    )


def enqueue_project_batch_classification(project_id: str, force_update: bool = False, limit: int = 1000):
    """Enfileira classificação em lote de um projeto"""
    from celery_app import celery_app
    return celery_app.send_task(
        "classification.batch_classify_project",
        args=[project_id, force_update, limit]
    )


def enqueue_unclassified_batch_classification(project_id: str = None, limit: int = 1000):
    """Enfileira classificação de runs não classificadas"""
    from celery_app import celery_app
    return celery_app.send_task(
        "classification.batch_classify_unclassified",
        args=[project_id, limit]
    )