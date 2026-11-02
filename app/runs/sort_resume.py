"""Remembered stop point for a manual DINO/HYBRID sort.

A full reset runs for hours, so the owner can stop it and come back later.
The stop point is a small JSON value in app_settings:

    {"batch_id": 8, "stage": "DINO" | "HYBRID", "stopped_at": "..."}

`Continue` uses it to queue only unfinished work; `Reset` clears it and starts
over. Nothing here deletes completed DINO/HYBRID results.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app import settings_store

KEY = "sort_resume_v1"


def save(batch_id: int, stage: str) -> dict[str, Any]:
    value = {
        "batch_id": int(batch_id),
        "stage": "HYBRID" if stage == "HYBRID" else "DINO",
        "stopped_at": datetime.now(timezone.utc).isoformat(),
    }
    settings_store.set_value(KEY, value)
    return value


def load() -> dict[str, Any] | None:
    value = settings_store.get(KEY)
    if not isinstance(value, dict):
        return None

    try:
        batch_id = int(value["batch_id"])
    except (KeyError, TypeError, ValueError):
        return None

    stage = value.get("stage")
    return {
        "batch_id": batch_id,
        "stage": "HYBRID" if stage == "HYBRID" else "DINO",
        "stopped_at": value.get("stopped_at"),
    }


def clear() -> None:
    settings_store.set_value(KEY, None)
