from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.config import settings
from app.models.models import RunSemanticInsight

try:
    from app.services.blob_storage import upload_json, download_json
except Exception:  # pragma: no cover - blob helper may not be available during import time
    upload_json = None  # type: ignore
    download_json = None  # type: ignore


def _container_name() -> str:
    return settings.azure_blob_container_semantic or "semantic-insights"


def store_insight_payload(insight: RunSemanticInsight, payload: Dict[str, Any]) -> None:
    if settings.azure_blob_connection_string and upload_json is not None:
        blob_name = f"{insight.run_id}.json"
        upload_json(_container_name(), blob_name, payload)
        insight.payload_blob_path = blob_name
        insight.payload = None
    else:
        insight.payload = payload
        insight.payload_blob_path = None


def load_insight_payload(insight: Optional[RunSemanticInsight]) -> Dict[str, Any]:
    if not insight:
        return {}
    if insight.payload is not None:
        return dict(insight.payload)
    if insight.payload_blob_path and settings.azure_blob_connection_string and download_json is not None:
        try:
            return download_json(_container_name(), insight.payload_blob_path)
        except FileNotFoundError:
            return {}
    return {}
