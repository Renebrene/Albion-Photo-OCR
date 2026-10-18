"""Registration records and persistence for durable source video assets."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import date, datetime
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
    sha256: str | None
    identity_hash: str
    identity_date: date
    container_format: str
    video_codec: str
    width: int
    height: int
    duration_seconds: float
    fps: float | None
    frame_count: int | None
    size_bytes: int
    taken_at: datetime | None


def metadata_identity_hash(filename: str, identity_date: date | str, size_bytes: int) -> str:
    """Hash only canonical metadata; video contents are never read for identity."""
    day = identity_date.isoformat() if isinstance(identity_date, date) else str(identity_date)
    payload = json.dumps(
        [Path(filename).name, day, int(size_bytes)], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def create_video_identity(filename: str, identity_date: date | str, size_bytes: int) -> str:
    identity_hash = metadata_identity_hash(filename, identity_date, size_bytes)
    return f"VI_{identity_hash[:24]}"


def register_video(**values: Any) -> VideoRecord:
    """Validate integrity output and make a VideoRecord without DB access."""

    identity_hash = values.get("identity_hash")
    identity_date_value = values.get("identity_date")
    if not isinstance(identity_hash, str) or not SHA256_RE.fullmatch(identity_hash):
        raise ValueError("некорректный metadata identity видео")
    try:
        identity_date = (
            identity_date_value if isinstance(identity_date_value, date)
            else date.fromisoformat(str(identity_date_value))
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("некорректная дата идентичности видео") from exc
    sha256 = values.get("sha256")
    if sha256 is not None and (not isinstance(sha256, str) or not SHA256_RE.fullmatch(sha256)):
        raise ValueError("некорректный legacy SHA-256 видео")
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
    filename = str(values["filename"])
    expected_identity_hash = metadata_identity_hash(filename, identity_date, size_bytes)
    if identity_hash != expected_identity_hash:
        raise ValueError("metadata identity не соответствует имени, дате и размеру видео")

    fps_value = values.get("fps")
    fps = float(fps_value) if fps_value is not None else None
    frames_value = values.get("frame_count")
    frame_count = int(frames_value) if frames_value is not None else None
    if fps is not None and fps <= 0:
        fps = None
    if frame_count is not None and frame_count <= 0:
        frame_count = None

    return VideoRecord(
        video_id=f"VI_{identity_hash[:24]}",
        source_path=str(Path(values["source_path"])),
        filename=filename,
        sha256=sha256,
        identity_hash=identity_hash,
        identity_date=identity_date,
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


def _classify_existing(cur, record: VideoRecord) -> tuple[str, str] | None:
    cur.execute(
        """SELECT video_id,identity_hash,identity_date,filename,size_bytes,source_path,taken_at
           FROM public.video_assets WHERE video_id=%s OR identity_hash=%s""",
        (record.video_id, record.identity_hash),
    )
    rows = cur.fetchall()
    for video_id, identity_hash, identity_date, filename, size_bytes, source_path, taken_at in rows:
        if identity_hash == record.identity_hash:
            if filename == record.filename and int(size_bytes) == record.size_bytes and identity_date == record.identity_date:
                return ("EXISTING", str(video_id))
            return ("CONFLICT", str(video_id))
        if (
            identity_hash is None
            and source_path == record.source_path
            and filename == record.filename
            and int(size_bytes) == record.size_bytes
            and (taken_at is None or taken_at == record.taken_at)
        ):
            return ("EXISTING", str(video_id))
        return ("CONFLICT", str(video_id))

    cur.execute(
        """SELECT video_id,taken_at FROM public.video_assets
           WHERE identity_hash IS NULL AND source_path=%s AND filename=%s AND size_bytes=%s""",
        (record.source_path, record.filename, record.size_bytes),
    )
    legacy = cur.fetchone()
    if legacy:
        return ("EXISTING", str(legacy[0])) if legacy[1] is None or legacy[1] == record.taken_at else ("CONFLICT", str(legacy[0]))
    return None


def register_video_records(records: list[VideoRecord]) -> dict[str, list[VideoRecord]]:
    """Idempotently insert metadata-identified assets without content hashing."""

    result: dict[str, list[VideoRecord]] = {"NEW": [], "EXISTING": [], "CONFLICT": []}
    if not records:
        return result

    seen: dict[str, tuple[str, date, int]] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            for record in records:
                prior = seen.get(record.identity_hash)
                if prior is not None:
                    if prior == (record.filename, record.identity_date, record.size_bytes):
                        result["EXISTING"].append(record)
                    else:
                        result["CONFLICT"].append(record)
                    continue
                seen[record.identity_hash] = (record.filename, record.identity_date, record.size_bytes)

                existing = _classify_existing(cur, record)
                if existing:
                    status, existing_id = existing
                    result[status].append(
                        record if existing_id == record.video_id else replace(record, video_id=existing_id)
                    )
                    continue

                cur.execute(
                    """INSERT INTO public.video_assets (
                           video_id, source_path, filename, sha256, identity_hash,
                           identity_date, identity_scheme, container_format, video_codec,
                           width, height, duration_seconds, fps, frame_count,
                           size_bytes, taken_at
                       ) VALUES (
                           %(video_id)s, %(source_path)s, %(filename)s, %(sha256)s,
                           %(identity_hash)s, %(identity_date)s, 'metadata-v1',
                           %(container_format)s, %(video_codec)s, %(width)s, %(height)s,
                           %(duration_seconds)s, %(fps)s, %(frame_count)s,
                           %(size_bytes)s, %(taken_at)s
                       ) ON CONFLICT DO NOTHING
                       RETURNING video_id""",
                    record.__dict__,
                )
                inserted = cur.fetchone()
                if inserted:
                    result["NEW"].append(record)
                    continue

                raced = _classify_existing(cur, record)
                if raced:
                    status, existing_id = raced
                    result[status].append(
                        record if existing_id == record.video_id else replace(record, video_id=existing_id)
                    )
                else:
                    result["CONFLICT"].append(record)

    return result


def known_video_ids() -> set[str]:
    """Stable IDs registered in the video table (optional UI/report helper)."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT video_id FROM public.video_assets")
            return {str(row[0]) for row in cur.fetchall()}
