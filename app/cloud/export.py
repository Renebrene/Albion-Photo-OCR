"""Worker-side export of one registered media item to Albion."""

from __future__ import annotations

from app.cloud import albion
from app.cloud import repository


def run_export(link_id: int) -> dict:
    link = repository.get(link_id)
    if link is None:
        raise ValueError(f"media link {link_id} not found")
    if link["status"] == "READY" and link["url"]:
        return {
            "link_id": link["link_id"],
            "status": "READY",
            "url": link["url"],
            "expires_at": link["expires_at"],
        }

    source = repository.media_source(link["media_kind"], link["media_id"])
    if source is None:
        message = "медиафайл не найден в реестре"
        repository.mark_failed(link_id, message)
        raise ValueError(message)

    try:
        uploaded = albion.upload_file(
            source["path"],
            source["filename"],
            ttl_days=None,
        )
    except Exception as exc:  # noqa: BLE001 - publish a safe FAILED state
        repository.mark_failed(link_id, str(exc))
        raise

    repository.mark_ready(
        link_id,
        url=uploaded["url"],
        expires_at=uploaded["expires_at"],
        object_key=uploaded.get("object_key"),
    )
    return {
        "link_id": link_id,
        "status": "READY",
        "url": uploaded["url"],
        "expires_at": uploaded["expires_at"],
    }
