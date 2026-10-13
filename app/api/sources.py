"""
The working (source) folder for INGEST: selection, validation and counting.

Nothing here reads image contents: a folder is only stat()-ed, so counting a
large tree stays cheap and the originals are never touched.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException

from app import settings_store
from app.api.config import (
    SOURCE_FOLDER_DEFAULT,
    SOURCE_FOLDER_KEY,
    SOURCE_ROOTS,
    SOURCE_SCAN_FILE_LIMIT,
)
from app.ingest.integrity import SUPPORTED_EXTENSIONS


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False

    return True


def resolve_directory(raw: str) -> Path:
    """
    Validate a client-supplied folder and return its resolved path.

    Errors never echo server-side paths back: the message is generic, the
    status code carries the meaning. When SCENE_SOURCE_ROOTS is set, anything
    outside those roots is refused.
    """

    candidate = (raw or "").strip()

    if not candidate:
        raise HTTPException(status_code=400, detail="path is required")

    try:
        resolved = Path(candidate).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise HTTPException(status_code=404, detail="folder not found") from exc

    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="not a directory")

    if SOURCE_ROOTS and not any(
        _is_within(resolved, root) for root in SOURCE_ROOTS
    ):
        raise HTTPException(
            status_code=403,
            detail="folder is outside the allowed source roots",
        )

    return resolved


def folder_stats(path: Path) -> dict:
    """
    Count supported photos and their total size below *path*.

    Bounded by SOURCE_SCAN_FILE_LIMIT; hidden directories are skipped (they
    hold tooling/caches, not working photos).
    """

    files = 0
    total = 0
    truncated = False

    for root, dirs, names in os.walk(path):
        dirs[:] = [name for name in dirs if not name.startswith(".")]

        for name in names:
            if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            files += 1

            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                # A file that vanished mid-walk is simply not counted.
                continue

            if files >= SOURCE_SCAN_FILE_LIMIT:
                truncated = True
                break

        if truncated:
            break

    return {
        "path": str(path),
        "files": files,
        "bytes": total,
        "truncated": truncated,
    }


def current_folder() -> str:
    """Configured working folder (database value, then env default)."""

    stored = settings_store.get(SOURCE_FOLDER_KEY)

    if isinstance(stored, str) and stored.strip():
        return stored

    return SOURCE_FOLDER_DEFAULT


def folder_state() -> dict:
    """Configured folder plus its statistics, for the settings panel."""

    configured = current_folder()
    state = {"configured": configured, "files": 0, "bytes": 0,
             "truncated": False, "exists": False}

    if not configured:
        return state

    path = Path(configured).expanduser()

    if not path.is_dir():
        return state

    stats = folder_stats(path)

    state.update(
        files=stats["files"],
        bytes=stats["bytes"],
        truncated=stats["truncated"],
        exists=True,
    )

    return state


def set_folder(raw: str) -> dict:
    """Persist a validated folder and return the new state."""

    resolved = resolve_directory(raw)
    settings_store.set_value(SOURCE_FOLDER_KEY, str(resolved))

    return folder_state()
