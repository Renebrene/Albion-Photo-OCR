"""Registration records and persistence for durable source video assets."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.ingest.database import get_connection

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VIDEO_ID_RE = re.compile(r"^VI_[0-9a-f]{24}$")


@dataclass(frozen=True)
class VideoRecord:
    """Immutable validated metadata for one physical source video."""

    video_id: str
    source_path: str
    filename: str
    sha256: str
    container_format: str
    video_codec: str
    width: int
    height: int
    duration_seconds: float
    fps: float | None
    frame_count: int | None
    size_bytes: int
    taken_at: datetime | None


def create_video_identity(sha256: str) -> str:
    if not isinstance(sha256, str) or not SHA256_RE.fullmatch(sha256):
        raise ValueError("sha256 должен содержать 64 строчных hex-символа")
    return f"VI_{sha256[:24]}"


def register_video(**values: Any) -> VideoRecord:
    """Validate integrity output and make a VideoRecord without DB access."""

    sha256 = values.get("sha256")
    if not isinstance(sha256, str) or not SHA256_RE.fullmatch(sha256):
        raise ValueError("некорректный SHA-256 видео")
    required = (
        "source_path", "filename", "container_format", "video_codec",
        "width", "height", "duration_seconds", "size_bytes",
    )
    if any(not values.get(name) for name in required):
        raise ValueError("неполные метаданные видео")
    try:
        width, height = int(values["width"]), int(values["height"])
        size_bytes = int(values["size_bytes"])
        duration = float(values["duration_seconds"])
    except (TypeError, ValueError) as exc:
        raise ValueError("некорректные числовые метаданные видео") from exc
    if width <= 0 or height <= 0 or size_bytes <= 0 or duration <= 0:
        raise ValueError("размер, разрешение и длительность должны быть положительными")

    fps_value = values.get("fps")
    fps = float(fps_value) if fps_value is not None else None
    frames_value = values.get("frame_count")
    frame_count = int(frames_value) if frames_value is not None else None
    if fps is not None and fps <= 0:
        fps = None
    if frame_count is not None and frame_count <= 0:
        frame_count = None

    return VideoRecord(
        video_id=create_video_identity(sha256),
        source_path=str(Path(values["source_path"])),
        filename=str(values["filename"]),
        sha256=sha256,
        container_format=str(values["container_format"]),
        video_codec=str(values["video_codec"]),
        width=width,
        height=height,
        duration_seconds=duration,
        fps=fps,
        frame_count=frame_count,
        size_bytes=size_bytes,
        taken_at=values.get("taken_at"),
    )


def _classify_existing(cur, record: VideoRecord) -> str | None:
    cur.execute(
        """SELECT video_id, sha256 FROM public.video_assets
           WHERE video_id = %s OR sha256 = %s""",
        (record.video_id, record.sha256),
    )
    rows = cur.fetchall()
    if not rows:
        return None
    if any(video_id == record.video_id and sha256 == record.sha256 for video_id, sha256 in rows):
        return "EXISTING"
    return "CONFLICT"


def register_video_records(records: list[VideoRecord]) -> dict[str, list[VideoRecord]]:
    """Idempotently insert a batch, handling races on ID/SHA constraints."""

    result: dict[str, list[VideoRecord]] = {"NEW": [], "EXISTING": [], "CONFLICT": []}
    if not records:
        return result

    seen_ids: dict[str, str] = {}
    seen_hashes: dict[str, str] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            for record in records:
                prior_hash = seen_ids.get(record.video_id)
                prior_id = seen_hashes.get(record.sha256)
                if prior_hash is not None or prior_id is not None:
                    if prior_hash == record.sha256 and prior_id == record.video_id:
                        result["EXISTING"].append(record)
                    else:
                        result["CONFLICT"].append(record)
                    continue
                seen_ids[record.video_id] = record.sha256
                seen_hashes[record.sha256] = record.video_id

                existing = _classify_existing(cur, record)
                if existing:
                    result[existing].append(record)
                    continue

                cur.execute(
                    """INSERT INTO public.video_assets (
                           video_id, source_path, filename, sha256, container_format,
                           video_codec, width, height, duration_seconds, fps,
                           frame_count, size_bytes, taken_at
                       ) VALUES (
                           %(video_id)s, %(source_path)s, %(filename)s, %(sha256)s,
                           %(container_format)s, %(video_codec)s, %(width)s,
                           %(height)s, %(duration_seconds)s, %(fps)s,
                           %(frame_count)s, %(size_bytes)s, %(taken_at)s
                       ) ON CONFLICT DO NOTHING
                       RETURNING video_id""",
                    record.__dict__,
                )
                inserted = cur.fetchone()
                if inserted:
                    result["NEW"].append(record)
                    continue

                # A parallel ingest may have inserted the same SHA/ID after the
                # first SELECT; classify the committed identity after conflict.
                raced = _classify_existing(cur, record)
                result[raced or "CONFLICT"].append(record)

    return result


def known_video_ids() -> set[str]:
    """Stable IDs registered in the video table (optional UI/report helper)."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT video_id FROM public.video_assets")
            return {str(row[0]) for row in cur.fetchall()}
