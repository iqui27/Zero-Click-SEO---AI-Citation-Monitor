from __future__ import annotations

import json
from typing import Any, Dict, Optional

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

from app.core.config import settings

_blob_service_client: Optional[BlobServiceClient] = None


def _get_service_client() -> BlobServiceClient:
    global _blob_service_client
    if not settings.azure_blob_connection_string:
        raise RuntimeError("Azure Blob connection string is not configured")
    if _blob_service_client is None:
        _blob_service_client = BlobServiceClient.from_connection_string(settings.azure_blob_connection_string)
    return _blob_service_client


def upload_json(container: str, blob_name: str, payload: Dict[str, Any]) -> str:
    service = _get_service_client()
    container_client = service.get_container_client(container)
    try:
        container_client.create_container()
    except ResourceExistsError:
        pass
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    blob_client = container_client.get_blob_client(blob_name)
    blob_client.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json; charset=utf-8"),
    )
    return blob_name


def download_json(container: str, blob_name: str) -> Dict[str, Any]:
    service = _get_service_client()
    blob_client = service.get_container_client(container).get_blob_client(blob_name)
    try:
        downloader = blob_client.download_blob()
    except ResourceNotFoundError as exc:
        raise FileNotFoundError(f"Blob not found: {blob_name}") from exc
    data = downloader.readall()
    if not data:
        return {}
    return json.loads(data.decode("utf-8"))


def delete_blob(container: str, blob_name: str) -> None:
    service = _get_service_client()
    blob_client = service.get_container_client(container).get_blob_client(blob_name)
    try:
        blob_client.delete_blob()
    except ResourceNotFoundError:
        pass
