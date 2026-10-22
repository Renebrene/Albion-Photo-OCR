"""Read-only metadata checks for source video assets.

This path is deliberately separate from photo integrity. It probes container
metadata and file stats without reading video contents or writing to the source.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.core.errors import redact_paths
from app.ingest.integrity import Discovery, date_in_period, file_date

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mpeg", ".mpg"}
DEFAULT_PROBE_TIMEOUT_SECONDS = 60.0


def _positive_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def discover_videos(
    directory: str | Path,
    *,
    recursive: bool = True,
    since: date | None = None,
    until: date | None = None,
) -> Discovery:
    """Same contract as the photo discovery, for the video extensions."""

    root = Path(directory)
    if not root.is_dir():
        return Discovery(files=[], excluded_by_period=0)

    walker = root.rglob if recursive else root.glob
    matched: list[Path] = []
    excluded = 0

    for path in walker("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
            continue
        if date_in_period(file_date(path), since, until):
            matched.append(path)
        else:
            excluded += 1

    return Discovery(files=sorted(matched), excluded_by_period=excluded)


def discover_video_files(
    directory: str | Path,
    *,
    recursive: bool = True,
    since: date | None = None,
    until: date | None = None,
) -> list[Path]:
    return discover_videos(
        directory, recursive=recursive, since=since, until=until
    ).files


def metadata_identity_hash(filename: str, identity_date: str, size_bytes: int) -> str:
    """Hash a canonical JSON tuple; this is not a hash of file contents."""
    payload = json.dumps(
        [Path(filename).name, str(identity_date), int(size_bytes)],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _rational(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = value.split("/", 1)
        denominator_value = float(denominator)
        if denominator_value == 0:
            return None
        rate = float(numerator) / denominator_value
        return rate if rate > 0 else None
    except (ValueError, ZeroDivisionError):
        try:
            rate = float(value)
            return rate if rate > 0 else None
        except (TypeError, ValueError):
            return None


def _parse_creation_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        result = datetime.fromisoformat(raw)
    except ValueError:
        return None
    # ISO creation_time in QuickTime/ffprobe is UTC when no offset is written.
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _run(args: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )


def _probe(path: Path) -> dict[str, Any]:
    ffprobe = os.getenv("SCENE_FFPROBE_BIN", "ffprobe")
    timeout = _positive_env("SCENE_INGEST_PROBE_TIMEOUT", DEFAULT_PROBE_TIMEOUT_SECONDS)
    result = _run(
        [
            ffprobe,
            "-v", "error",
            "-show_format", "-show_streams",
            "-show_entries",
            "format=format_name,duration,size:format_tags=creation_time:"
            "stream=codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,nb_frames,duration:"
            "stream_tags=creation_time",
            "-of", "json",
            str(path),
        ],
        timeout=timeout,
    )
    if result.returncode != 0:
        # Avoid including the input path or arbitrary stderr from media metadata.
        raise ValueError("ffprobe не смог прочитать контейнер видео")
    try:
        metadata = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("ffprobe вернул некорректные метаданные") from exc
    if not isinstance(metadata, dict):
        raise ValueError("ffprobe вернул некорректные метаданные")
    return metadata


def _metadata_fields(probe: dict[str, Any], size_bytes: int) -> dict[str, Any]:
    streams = probe.get("streams")
    if not isinstance(streams, list):
        streams = []
    video = next(
        (item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"),
        None,
    )
    if video is None:
        raise ValueError("в контейнере не найден видеопоток")

    try:
        width = int(video.get("width") or 0)
        height = int(video.get("height") or 0)
    except (ValueError, TypeError) as exc:
        raise ValueError("не удалось определить разрешение видео") from exc

    duration_values = []
    for source in (video, probe.get("format", {})):
        try:
            duration = float(source.get("duration") or 0)
        except (TypeError, ValueError):
            duration = 0
        if duration > 0:
            duration_values.append(duration)
    duration = max(duration_values, default=0.0)
    if duration <= 0 or width <= 0 or height <= 0:
        raise ValueError("не удалось определить длительность или разрешение видео")

    fps = _rational(video.get("avg_frame_rate")) or _rational(video.get("r_frame_rate"))
    try:
        frames = int(video.get("nb_frames")) if video.get("nb_frames") not in (None, "N/A") else None
    except (ValueError, TypeError):
        frames = None
    if frames is None and fps:
        frames = round(duration * fps)

    tags = video.get("tags") if isinstance(video.get("tags"), dict) else {}
    format_info = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    format_tags = format_info.get("tags") if isinstance(format_info.get("tags"), dict) else {}
    taken_at = _parse_creation_time(tags.get("creation_time") or format_tags.get("creation_time"))
    container = str(format_info.get("format_name") or "unknown")[:120]
    codec = str(video.get("codec_name") or "unknown")[:80]

    return {
        "container_format": container,
        "video_codec": codec,
        "width": width,
        "height": height,
        "duration_seconds": round(duration, 3),
        "fps": round(fps, 3) if fps else None,
        "frame_count": frames if frames and frames > 0 else None,
        "size_bytes": size_bytes,
        "taken_at": taken_at,
    }


def check_video_file(path: str | Path) -> dict[str, Any]:
    """Validate a supported source video and collect physical-file metadata."""

    path = Path(path)
    result: dict[str, Any] = {
        "filename": path.name,
        "source_path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "extension_valid": path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS,
        "sha256": None,  # retained only for legacy records; new video ingest does not hash contents
        "identity_hash": None,
        "identity_date": None,
        "integrity_status": "INVALID",
        "error": None,
        "container_format": None,
        "video_codec": None,
        "width": None,
        "height": None,
        "duration_seconds": None,
        "fps": None,
        "frame_count": None,
        "size_bytes": None,
        "taken_at": None,
    }
    if not result["exists"] or not result["is_file"]:
        result["error"] = "файл не существует или не является обычным файлом"
        return result
    if not result["extension_valid"]:
        result["error"] = f"неподдерживаемое расширение: {path.suffix.lower()}"
        return result

    try:
        before = path.stat()
        size_bytes = before.st_size
        result["size_bytes"] = size_bytes
        if size_bytes <= 0:
            raise ValueError("видеофайл пуст")

        # No file-content reads: identity uses only basename, capture day, and size.
        fields = _metadata_fields(_probe(path), size_bytes)
        capture_date = fields["taken_at"]
        identity_date = (
            capture_date.astimezone(timezone.utc).date().isoformat()
            if capture_date is not None
            else datetime.fromtimestamp(before.st_mtime, timezone.utc).date().isoformat()
        )
        identity_hash = metadata_identity_hash(path.name, identity_date, size_bytes)

        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("файл изменился во время INGEST; повторите сканирование")

        result.update(fields)
        result["identity_hash"] = identity_hash
        result["identity_date"] = identity_date
        result["integrity_status"] = "VALID"
    except FileNotFoundError:
        result["error"] = "ffprobe не установлен или файл исчез во время проверки"
    except subprocess.TimeoutExpired:
        result["error"] = "проверка видео превысила допустимое время"
    except ValueError as exc:
        result["error"] = str(exc)
    except OSError as exc:
        # Do not expose the absolute source path or low-level stderr to API/job logs.
        result["error"] = redact_paths(f"ошибка чтения видео: {exc.__class__.__name__}", path)
    except Exception as exc:  # noqa: BLE001 - one invalid file must not stop directory INGEST
        result["error"] = redact_paths(f"ошибка проверки видео: {exc.__class__.__name__}", path)

    return result
