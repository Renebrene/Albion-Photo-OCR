"""
The working (source) folder for INGEST: selection, validation and counting.

Nothing here reads image contents: a folder is only stat()-ed, so counting a
large tree stays cheap and the originals are never touched.
"""

from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

from fastapi import HTTPException

from app import settings_store
from app.api.config import (
    SOURCE_FOLDER_DEFAULT,
    SOURCE_FOLDER_KEY,
    SOURCE_ROOTS,
    SOURCE_SCAN_FILE_LIMIT,
    SOURCE_SCAN_TIMEOUT_SECONDS,
)
from app.ingest.integrity import SUPPORTED_EXTENSIONS, date_in_period, file_date
from app.ingest.video_integrity import SUPPORTED_VIDEO_EXTENSIONS

MEDIA_EXTENSIONS = SUPPORTED_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS
_PROBLEM_SAMPLE_LIMIT = 20


def _now() -> float:
    """Indirection for the scan deadline, patched in unit tests."""
    return time.monotonic()


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


def folder_stats(
    path: Path,
    *,
    since: date | None = None,
    until: date | None = None,
) -> dict:
    """
    Count supported photos and videos below *path* without reading contents.

    This is a preliminary check for the folder picker: sizes come from stat(),
    so a corrupt image/video is not detected until the INSPECT worker decodes it.
    Hidden directories are skipped. The walk is bounded by both a time budget
    and SOURCE_SCAN_FILE_LIMIT; either bound sets truncated=True.

    *since*/*until* (inclusive) apply the scan depth by time over each file's
    own date — the same cheap filter the worker uses in "дата загрузки" mode.
    Files outside the window are counted separately in *excluded_by_period*,
    so the counters keep describing the whole folder.
    """

    photos = 0
    videos = 0
    photo_bytes = 0
    video_bytes = 0
    excluded = 0
    extensions: dict[str, int] = {}
    problems: list[dict[str, str]] = []
    problem_count = 0
    truncated = False
    timed_out = False
    processed = 0
    deadline = (
        _now() + SOURCE_SCAN_TIMEOUT_SECONDS
        if SOURCE_SCAN_TIMEOUT_SECONDS > 0
        else None
    )

    def note_problem(name: str, reason: str) -> None:
        nonlocal problem_count

        problem_count += 1
        if len(problems) < _PROBLEM_SAMPLE_LIMIT:
            problems.append({"filename": name, "reason": reason})

    for root, dirs, names in os.walk(path):
        dirs[:] = [name for name in dirs if not name.startswith(".")]

        for name in names:
            suffix = Path(name).suffix.lower()

            if suffix not in MEDIA_EXTENSIONS:
                continue

            if deadline is not None and _now() >= deadline:
                timed_out = True
                truncated = True
                break

            is_video = suffix in SUPPORTED_VIDEO_EXTENSIONS
            entry = Path(root) / name

            if is_video:
                videos += 1
            else:
                photos += 1

            extensions[suffix] = extensions.get(suffix, 0) + 1
            processed += 1

            if processed >= SOURCE_SCAN_FILE_LIMIT:
                truncated = True
                break

            try:
                size = entry.stat().st_size
            except OSError:
                note_problem(name, "не удалось прочитать размер файла")
            else:
                if not date_in_period(file_date(entry), since, until):
                    excluded += 1
                else:
                    if is_video:
                        video_bytes += size
                    else:
                        photo_bytes += size

                    if size <= 0:
                        note_problem(name, "файл пуст")

        if truncated:
            break

    return {
        "path": str(path),
        # `files` stays the photo count for older clients; new clients use
        # `photos`/`videos` explicitly.
        "files": photos,
        "photos": photos,
        "videos": videos,
        "media_files": photos + videos,
        "bytes": photo_bytes + video_bytes,
        "photo_bytes": photo_bytes,
        "video_bytes": video_bytes,
        "extensions": dict(sorted(extensions.items())),
        # Scan depth by time: the counters above describe the whole folder,
        # these two say how much of it the selected period would scan.
        "excluded_by_period": excluded,
        "in_period": photos + videos - excluded,
        "period_applied": bool(since or until),
        "problem_count": problem_count,
        "problems": problems,
        "preliminary": True,
        "truncated": truncated,
        "timed_out": timed_out,
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
    state = {
        "configured": configured,
        "files": 0,
        "photos": 0,
        "videos": 0,
        "media_files": 0,
        "bytes": 0,
        "photo_bytes": 0,
        "video_bytes": 0,
        "extensions": {},
        "problem_count": 0,
        "problems": [],
        "preliminary": True,
        "truncated": False,
        "timed_out": False,
        "exists": False,
    }

    if not configured:
        return state

    path = Path(configured).expanduser()

    if not path.is_dir():
        return state

    stats = folder_stats(path)

    state.update(
        files=stats["files"],
        photos=stats["photos"],
        videos=stats["videos"],
        media_files=stats["media_files"],
        bytes=stats["bytes"],
        photo_bytes=stats["photo_bytes"],
        video_bytes=stats["video_bytes"],
        extensions=stats["extensions"],
        problem_count=stats["problem_count"],
        problems=stats["problems"],
        preliminary=stats["preliminary"],
        truncated=stats["truncated"],
        timed_out=stats["timed_out"],
        exists=True,
    )

    return state


def set_folder(raw: str) -> dict:
    """Persist a validated folder and return the new state."""

    resolved = resolve_directory(raw)
    settings_store.set_value(SOURCE_FOLDER_KEY, str(resolved))

    return folder_state()
