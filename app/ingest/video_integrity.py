"""Read-only integrity and metadata checks for source video assets.

This path is deliberately separate from photo integrity. It probes and fully
reads the video stream, computes a SHA-256 identity, and never writes to the
source file. Inference (DINO/HYBRID/QWEN) is not part of video INGEST.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.errors import redact_paths

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mpeg", ".mpg"}
DEFAULT_MAX_VIDEO_BYTES = 300 * 1024 * 1024
DEFAULT_MAX_VIDEO_SECONDS = 20.0
DEFAULT_PROBE_TIMEOUT_SECONDS = 30.0
DEFAULT_DECODE_TIMEOUT_SECONDS = 180.0


def _positive_env(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def max_video_bytes() -> int:
    return int(_positive_env("SCENE_INGEST_MAX_VIDEO_BYTES", DEFAULT_MAX_VIDEO_BYTES))


def max_video_seconds() -> float:
    return _positive_env("SCENE_INGEST_MAX_VIDEO_SECONDS", DEFAULT_MAX_VIDEO_SECONDS)


def discover_video_files(directory: str | Path, *, recursive: bool = True) -> list[Path]:
    root = Path(directory)
    if not root.is_dir():
        return []
    walker = root.rglob if recursive else root.glob
    return sorted(
        path
        for path in walker("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def _decode_check(path: Path) -> None:
    ffmpeg = os.getenv("SCENE_FFMPEG_BIN", "ffmpeg")
    timeout = _positive_env("SCENE_INGEST_DECODE_TIMEOUT", DEFAULT_DECODE_TIMEOUT_SECONDS)
    result = _run(
        [
            ffmpeg,
            "-nostdin", "-v", "error", "-xerror",
            "-i", str(path),
            "-map", "0:v:0",
            "-f", "null", "-",
        ],
        timeout=timeout,
    )
    if result.returncode != 0:
        raise ValueError("полная проверка декодирования видео не пройдена")


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
        "sha256": None,
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
        if size_bytes > max_video_bytes():
            raise ValueError(f"видеофайл превышает лимит {max_video_bytes()} байт")

        digest = _sha256(path)
        fields = _metadata_fields(_probe(path), size_bytes)
        if fields["duration_seconds"] > max_video_seconds():
            raise ValueError(
                f"длительность превышает лимит {max_video_seconds():.0f} секунд"
            )
        _decode_check(path)

        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("файл изменился во время INGEST; повторите сканирование")

        result.update(fields)
        result["sha256"] = digest
        result["integrity_status"] = "VALID"
    except FileNotFoundError:
        result["error"] = "ffprobe/ffmpeg не установлен или файл исчез во время проверки"
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
