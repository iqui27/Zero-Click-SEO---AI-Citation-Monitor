from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from app.core.config import settings
from app.models.models import Evidence

try:  # pragma: no cover - blob helper may not be available in some environments
    from app.services.blob_storage import upload_json, download_json
except Exception:  # pragma: no cover
    upload_json = None  # type: ignore
    download_json = None  # type: ignore


def _container_name() -> str:
    return settings.azure_blob_container_evidence or "evidence-payloads"


def _default_blob_name(evidence: Evidence) -> str:
    uid = uuid4().hex
    run_id = evidence.run_id or "unknown"
    return f"{run_id}/{uid}.json"


def store_evidence_payload(evidence: Evidence, payload: Dict[str, Any]) -> None:
    if settings.azure_blob_connection_string and upload_json is not None:
        blob_name = evidence.payload_blob_path or _default_blob_name(evidence)
        upload_json(_container_name(), blob_name, payload)
        evidence.payload_blob_path = blob_name
        evidence.parsed_json = None
    else:
        evidence.parsed_json = payload
        evidence.payload_blob_path = None


def load_evidence_payload(evidence: Optional[Evidence]) -> Dict[str, Any]:
    if evidence is None:
        return {}

    if evidence.payload_blob_path and settings.azure_blob_connection_string and download_json is not None:
        try:
            return download_json(_container_name(), evidence.payload_blob_path)
        except FileNotFoundError:
            pass

    return dict(evidence.parsed_json or {})
