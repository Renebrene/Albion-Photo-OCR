"""Bounded worker-side H.264 derivative creation for registered source videos."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Callable

from PIL import Image

from app.api.config import ORIGINALS_ROOTS, SOURCE_ROOTS, VIDEO_STORYBOARD_ROOT
from app.api.file_access import allowed_media_path
from app.api.video_repository import update_derivative, video_source
from app.core.errors import redact_absolute_paths
from app.ingest.video_integrity import check_video_file
from app.video.profiles import PROFILES

Progress = Callable[[int, int, str], None]


class VideoTranscodeCancelled(RuntimeError):
    """The source job was cancelled during a running ffmpeg process."""


class FFmpegEncodeError(RuntimeError):
    """ffmpeg exited unsuccessfully; auto mode may retry with CPU H.264."""


def derivatives_root() -> Path:
    scene_data = Path(os.getenv("SCENE_DATA", "data"))
    return Path(os.getenv("SCENE_VIDEO_DERIVATIVES_ROOT", str(scene_data / "video_derivatives"))).expanduser().resolve()


def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _ffmpeg() -> str:
    return os.getenv("SCENE_FFMPEG_BIN", "ffmpeg")


@lru_cache(maxsize=1)
def nvenc_available() -> bool:
    """Return true only when the ffmpeg encoder also passes a tiny runtime encode."""

    ffmpeg = _ffmpeg()
    try:
        encoders = subprocess.run(
            [ffmpeg, "-hide_banner", "-encoders"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if encoders.returncode != 0 or "h264_nvenc" not in (encoders.stdout + encoders.stderr):
        return False

    with tempfile.TemporaryDirectory(prefix="scene-nvenc-") as directory:
        target = Path(directory) / "probe.mp4"
        try:
            smoke = subprocess.run(
                [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                    "-f", "lavfi", "-i", "color=c=black:s=320x240:d=0.08",
                    "-frames:v", "1", "-an", "-c:v", "h264_nvenc", "-f", "mp4", str(target),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=20,
                shell=False,
            )
            return smoke.returncode == 0 and target.is_file() and target.stat().st_size > 0
        except (OSError, subprocess.TimeoutExpired):
            return False


def choose_worker_mode(cpu_count: int | None = None) -> tuple[str, int]:
    """Auto uses one verified NVENC worker; the CPU baseline uses half the cores."""

    cpu_count = cpu_count or os.cpu_count() or 1
    mode = os.getenv("SCENE_VIDEO_ENCODER", "auto").strip().lower()
    override = os.getenv("SCENE_VIDEO_TRANSCODE_WORKERS")

    if mode not in {"auto", "cpu", "nvenc"}:
        mode = "auto"
    use_gpu = mode in {"auto", "nvenc"} and nvenc_available()
    if use_gpu:
        workers = int(override) if override and override.isdigit() else 1
        return "h264_nvenc", max(1, min(workers, 2))
    workers = int(override) if override and override.isdigit() else max(1, cpu_count // 2)
    return "libx264", max(1, workers)


def _scale_filter(width: int, height: int) -> str:
    # Keep aspect ratio and never upscale; cap both dimensions to the profile.
    return (
        f"scale=w='min({width},iw)':h='min({height},ih)':"
        "force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1,fps=25"
    )


def _progress_time(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="ascii", errors="ignore")
    except OSError:
        return None
    found = None
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep and key == "out_time_us":
            try:
                found = max(0, int(value))
            except ValueError:
                pass
    return found


def _call_progress(progress: Progress, done: int, total: int, stage: str = "VIDEO_TRANSCODE") -> None:
    try:
        progress(done, total, stage)
    except Exception as exc:
        if exc.__class__.__name__ == "JobCancelled":
            raise VideoTranscodeCancelled("задание конвертации отменено") from exc
        raise


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _ffmpeg_args(
    *, ffmpeg: str, encoder: str, source: Path, destination: Path,
    progress_file: Path, profile: dict, threads: int,
) -> list[str]:
    args = [
        ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
        "-stats_period", "1", "-progress", str(progress_file),
        "-i", str(source), "-map", "0:v:0", "-map", "0:a?", "-map_metadata", "0",
        "-vf", _scale_filter(profile["width"], profile["height"]),
        "-r", "25", "-fps_mode", "cfr", "-c:v", encoder,
    ]
    if encoder == "h264_nvenc":
        args.extend(["-preset", "p5", "-rc", "vbr", "-cq", str(profile["crf"]), "-b:v", "0"])
    else:
        args.extend(["-preset", "medium", "-crf", str(profile["crf"]), "-threads", str(threads)])
    args.extend(["-c:a", "aac", "-b:a", profile["audio_bitrate"], "-movflags", "+faststart", str(destination)])
    return args


def _run_encoder(
    args: list[str], *, progress_file: Path, temp_output: Path,
    total_us: int, progress: Progress, timeout: float,
    stage: str = "VIDEO_TRANSCODE",
) -> None:
    started = time.monotonic()
    stderr_file = tempfile.TemporaryFile(mode="w+b")
    process = None
    try:
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=stderr_file, shell=False)
        last_done = -1
        while process.poll() is None:
            if time.monotonic() - started > timeout:
                raise TimeoutError("конвертация видео превысила timeout")
            done = _progress_time(progress_file)
            if done is not None and done != last_done:
                last_done = done
                _call_progress(progress, min(done, total_us), total_us)
            else:
                _call_progress(progress, max(0, last_done), total_us)
            time.sleep(0.5)
        if process.returncode != 0:
            stderr_file.seek(0, os.SEEK_END)
            stderr_file.seek(max(0, stderr_file.tell() - 3000))
            detail = stderr_file.read().decode("utf-8", errors="replace")
            raise FFmpegEncodeError(redact_absolute_paths(detail[-1500:]) or "ffmpeg завершился с ошибкой")
        if not temp_output.is_file() or temp_output.stat().st_size == 0:
            raise FFmpegEncodeError("ffmpeg не создал выходной файл")
    except BaseException:
        if process is not None:
            _terminate(process)
        raise
    finally:
        stderr_file.close()


STORYBOARD_FRAME_COUNT = 8
STORYBOARD_MAX_EDGE = 480
STORYBOARD_MAX_BYTES = 8 * 1024 * 1024


def storyboard_frame_path(video_id: str, source_sha256: str, index: int) -> Path:
    if not 0 <= index < STORYBOARD_FRAME_COUNT:
        raise ValueError("invalid storyboard frame index")
    if not re.fullmatch(r"VI_[0-9a-f]{24}", video_id):
        raise ValueError("invalid video id")
    if not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("invalid source hash")
    return VIDEO_STORYBOARD_ROOT / video_id / source_sha256 / f"{index:02d}.jpg"


def _valid_storyboard_frame(path: Path, root: Path) -> bool:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
            return False
        resolved = path.resolve(strict=True)
        if not _within(resolved, root):
            return False
        if resolved.stat().st_size > STORYBOARD_MAX_BYTES:
            return False
        with Image.open(resolved) as image:
            image.verify()
        with Image.open(resolved) as image:
            image.load()
            return image.format == "JPEG" and max(image.size) <= STORYBOARD_MAX_EDGE
    except (OSError, ValueError):
        return False


def generate_storyboard(
    *, video_id: str, source_sha256: str, progress: Progress | None = None,
) -> dict:
    """Generate eight bounded JPEG storyboard frames under the managed preview root."""

    source_record = video_source(video_id)
    if source_record is None or source_record["sha256"] != source_sha256:
        raise ValueError("исходный видеофайл изменился или отсутствует")
    source = allowed_media_path(source_record["source_path"], ORIGINALS_ROOTS)
    if source is None:
        raise ValueError("исходное видео недоступно в разрешённом корне")
    duration = float(source_record["duration_seconds"])
    if duration <= 0:
        raise ValueError("invalid source duration")

    configured_root = VIDEO_STORYBOARD_ROOT.expanduser()
    configured_root.mkdir(parents=True, exist_ok=True)
    root = configured_root.resolve(strict=True)
    originals = [path.expanduser().resolve() for path in (*ORIGINALS_ROOTS, *SOURCE_ROOTS)]
    if any(_within(root, original) or _within(original, root) for original in originals):
        raise ValueError("storyboard root must be separate from source roots")
    target_dir = root / video_id / source_sha256
    target_dir.mkdir(parents=True, exist_ok=True)
    resolved_target = target_dir.resolve(strict=True)
    if not _within(resolved_target, root) or resolved_target != target_dir:
        raise ValueError("storyboard path escapes its managed root")
    ffmpeg = _ffmpeg()
    created = 0
    started = time.monotonic()
    deadline = started + 120
    for index in range(STORYBOARD_FRAME_COUNT):
        if progress:
            progress(index, STORYBOARD_FRAME_COUNT, "VIDEO_STORYBOARD")
        timestamp = duration * (index + 0.5) / STORYBOARD_FRAME_COUNT
        destination = target_dir / f"{index:02d}.jpg"
        if _valid_storyboard_frame(destination, root):
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("storyboard generation exceeded time limit")
        fd, temp_name = tempfile.mkstemp(prefix=f".{index:02d}-", suffix=".tmp.jpg", dir=target_dir)
        os.close(fd)
        temporary = Path(temp_name)
        try:
            command = [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-ss", f"{timestamp:.3f}", "-i", str(source), "-frames:v", "1", "-an",
                "-vf", f"scale=w='min({STORYBOARD_MAX_EDGE},iw)':h='min({STORYBOARD_MAX_EDGE},ih)':force_original_aspect_ratio=decrease",
                "-q:v", "4", "-threads:v", "1", str(temporary),
            ]
            stderr_file = tempfile.TemporaryFile(mode="w+b")
            process = None
            try:
                process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=stderr_file, shell=False)
                frame_started = time.monotonic()
                while process.poll() is None:
                    if progress:
                        progress(index, STORYBOARD_FRAME_COUNT, "VIDEO_STORYBOARD")
                    if time.monotonic() - frame_started > max(1.0, min(30.0, remaining)):
                        raise TimeoutError("storyboard frame generation exceeded timeout")
                    time.sleep(0.25)
                if process.returncode != 0:
                    stderr_file.seek(0, os.SEEK_END)
                    stderr_file.seek(max(0, stderr_file.tell() - 2000))
                    error_text = stderr_file.read().decode("utf-8", errors="replace")
                    raise RuntimeError(redact_absolute_paths(error_text[-1000:]) or "storyboard frame generation failed")
            except BaseException:
                if process is not None:
                    _terminate(process)
                raise
            finally:
                stderr_file.close()
            if not temporary.is_file() or temporary.stat().st_size <= 0:
                raise RuntimeError("storyboard frame generation failed")
            if temporary.stat().st_size > STORYBOARD_MAX_BYTES:
                raise RuntimeError("storyboard frame exceeds size limit")
            with Image.open(temporary) as image:
                image.verify()
            with Image.open(temporary) as image:
                image.load()
                if image.format != "JPEG" or max(image.size) > STORYBOARD_MAX_EDGE:
                    raise RuntimeError("invalid storyboard JPEG")
            os.replace(temporary, destination)
            created += 1
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        finally:
            temporary.unlink(missing_ok=True)
    if _sha256(source) != source_sha256:
        raise RuntimeError("исходник изменился во время storyboard generation")
    valid_count = sum(
        _valid_storyboard_frame(target_dir / f"{index:02d}.jpg", root)
        for index in range(STORYBOARD_FRAME_COUNT)
    )
    if valid_count != STORYBOARD_FRAME_COUNT:
        raise RuntimeError("storyboard output is incomplete")
    if progress:
        progress(STORYBOARD_FRAME_COUNT, STORYBOARD_FRAME_COUNT, "VIDEO_STORYBOARD")
    return {"video_id": video_id, "source_sha256": source_sha256, "frames": valid_count, "created": created}


def _trim_filter() -> str:
    return (
        "scale=w='min(2560,iw)':h='min(1440,ih)':"
        "force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1,fps=25"
    )


def run_trim(
    *,
    video_id: str,
    derivative_id: int,
    source_sha256: str,
    start_seconds: float,
    end_seconds: float,
    job_id: int,
    progress: Progress,
) -> dict:
    """Create a trimmed, CPU-encoded derivative without modifying the source."""

    start_seconds = round(float(start_seconds), 3)
    end_seconds = round(float(end_seconds), 3)
    if start_seconds < 0 or end_seconds - start_seconds < 0.25:
        raise ValueError("invalid trim range")
    source_record = video_source(video_id)
    if source_record is None or source_record["sha256"] != source_sha256:
        raise ValueError("исходный видеофайл изменился или отсутствует")
    if end_seconds > float(source_record["duration_seconds"]):
        raise ValueError("trim end exceeds source duration")
    source = allowed_media_path(source_record["source_path"], ORIGINALS_ROOTS)
    if source is None:
        raise ValueError("исходное видео недоступно в разрешённом корне")

    output_root = derivatives_root()
    source_roots = [root.expanduser().resolve() for root in (*ORIGINALS_ROOTS, *SOURCE_ROOTS)]
    if any(_within(output_root, root) or _within(root, output_root) for root in source_roots):
        raise ValueError("video derivatives root должен быть отдельно от originals roots")
    target_dir = output_root / video_id
    target_dir.mkdir(parents=True, exist_ok=True)
    if target_dir.resolve(strict=True) != target_dir:
        raise ValueError("video derivative path escapes its managed root")
    destination = target_dir / f"trim-{derivative_id}.mp4"
    temp_fd, temp_name = tempfile.mkstemp(prefix=f".trim-{job_id}-", suffix=".tmp.mp4", dir=target_dir)
    os.close(temp_fd)
    temporary = Path(temp_name)
    progress_file = temporary.with_suffix(".progress")
    try:
        update_derivative(derivative_id, status="RUNNING", job_id=job_id)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    duration_us = max(1, int((end_seconds - start_seconds) * 1_000_000))
    timeout = max(120.0, float(os.getenv("SCENE_VIDEO_TRANSCODE_TIMEOUT", "1800")))
    try:
        args = [
            _ffmpeg(), "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
            "-stats_period", "1", "-progress", str(progress_file),
            "-ss", f"{start_seconds:.3f}", "-accurate_seek", "-i", str(source),
            "-t", f"{end_seconds - start_seconds:.3f}",
            "-map", "0:v:0", "-map", "0:a?", "-map_metadata", "0",
            "-vf", _trim_filter(),
            "-r", "25", "-fps_mode", "cfr", "-c:v", "libx264",
            "-preset", "medium", "-crf", "23", "-threads", str(max(1, int(os.getenv("SCENE_VIDEO_TRANSCODE_THREADS", "2")))),
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(temporary),
        ]
        _run_encoder(args, progress_file=progress_file, temp_output=temporary, total_us=duration_us,
                     progress=progress, timeout=timeout)
        checked = check_video_file(temporary)
        if checked["integrity_status"] != "VALID" or checked["video_codec"] != "h264":
            raise RuntimeError(checked.get("error") or "trim output validation failed")
        if checked["width"] > 2560 or checked["height"] > 1440:
            raise RuntimeError("trim output exceeds allowed dimensions")
        if abs((checked["fps"] or 0) - 25) > 0.1:
            raise RuntimeError("trim output frame rate is not 25 fps")
        actual_duration = float(checked["duration_seconds"])
        expected_duration = end_seconds - start_seconds
        if abs(actual_duration - expected_duration) > 0.25:
            raise RuntimeError("trim output duration differs from selected range")
        if _sha256(source) != source_sha256:
            raise RuntimeError("исходник изменился во время обрезки")

        os.replace(temporary, destination)
        result = {
            "output_path": str(destination), "output_sha256": checked["sha256"],
            "output_size_bytes": checked["size_bytes"], "width": checked["width"],
            "height": checked["height"], "duration_seconds": checked["duration_seconds"],
            "fps": checked["fps"], "video_codec": checked["video_codec"], "encoder": "libx264",
            "operation_kind": "TRIM", "start_seconds": start_seconds, "end_seconds": end_seconds,
        }
        try:
            update_derivative(derivative_id, status="DONE", job_id=job_id, result=result)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        _call_progress(progress, duration_us, duration_us)
        return {
            "video_id": video_id, "derivative_id": derivative_id, "status": "DONE",
            "start_seconds": start_seconds, "end_seconds": end_seconds, "encoder": "libx264",
        }
    except BaseException:
        temporary.unlink(missing_ok=True)
        progress_file.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)
        progress_file.unlink(missing_ok=True)


def run_transcode(
    *,
    video_id: str,
    derivative_id: int,
    profile: str,
    source_sha256: str,
    job_id: int,
    progress: Progress,
) -> dict:
    """Encode one managed derivative. Source remains untouched/read-only."""

    if profile not in PROFILES:
        raise ValueError("неизвестный профиль видео")
    source_record = video_source(video_id)
    if source_record is None or source_record["sha256"] != source_sha256:
        raise ValueError("исходный видеофайл изменился или отсутствует")
    source = allowed_media_path(source_record["source_path"], ORIGINALS_ROOTS)
    if source is None:
        raise ValueError("исходное видео недоступно в разрешённом корне")

    output_root = derivatives_root()
    source_roots = [root.expanduser().resolve() for root in (*ORIGINALS_ROOTS, *SOURCE_ROOTS)]
    if any(_within(output_root, root) or _within(root, output_root) for root in source_roots):
        raise ValueError("video derivatives root должен быть отдельно от originals roots")

    profile_info = PROFILES[profile]
    target_dir = output_root / video_id
    target_dir.mkdir(parents=True, exist_ok=True)
    if target_dir.resolve(strict=True) != target_dir:
        raise ValueError("video derivative path escapes its managed root")
    destination = target_dir / f"{profile}.mp4"
    ffmpeg = _ffmpeg()
    resolved_encoder = os.getenv("SCENE_VIDEO_ENCODER_RESOLVED")
    if resolved_encoder in {"libx264", "h264_nvenc"}:
        encoder = resolved_encoder
        default_workers = 1 if encoder == "h264_nvenc" else max(1, (os.cpu_count() or 1) // 2)
    else:
        encoder, default_workers = choose_worker_mode()
    threads = max(1, int(os.getenv("SCENE_VIDEO_TRANSCODE_THREADS", str(max(1, (os.cpu_count() or 1) // default_workers)))))

    temp_fd, temp_name = tempfile.mkstemp(prefix=f".{profile}-{job_id}-", suffix=".tmp.mp4", dir=target_dir)
    os.close(temp_fd)
    temporary = Path(temp_name)
    progress_file = temporary.with_suffix(".progress")
    update_derivative(derivative_id, status="RUNNING", job_id=job_id)

    total_us = max(1, int(float(source_record.get("duration_seconds") or 0) * 1_000_000))
    timeout = max(120.0, float(os.getenv("SCENE_VIDEO_TRANSCODE_TIMEOUT", "1800")))
    try:
        args = _ffmpeg_args(
            ffmpeg=ffmpeg, encoder=encoder, source=source, destination=temporary,
            progress_file=progress_file, profile=profile_info, threads=threads,
        )
        try:
            _run_encoder(args, progress_file=progress_file, temp_output=temporary, total_us=total_us, progress=progress, timeout=timeout)
        except VideoTranscodeCancelled:
            raise
        except FFmpegEncodeError:
            if encoder != "h264_nvenc":
                raise
            # A driver/device can fail after capability probing; discard the
            # partial NVENC output and retry once with the reliable CPU path.
            temporary.unlink(missing_ok=True)
            progress_file.unlink(missing_ok=True)
            encoder = "libx264"
            args = _ffmpeg_args(
                ffmpeg=ffmpeg, encoder=encoder, source=source, destination=temporary,
                progress_file=progress_file, profile=profile_info, threads=threads,
            )
            _run_encoder(args, progress_file=progress_file, temp_output=temporary, total_us=total_us, progress=progress, timeout=timeout)

        checked = check_video_file(temporary)
        if checked["integrity_status"] != "VALID":
            raise RuntimeError(checked.get("error") or "проверка выходного файла не пройдена")
        if checked["video_codec"] != "h264":
            raise RuntimeError("выходной файл не подтвердил H.264 codec")
        if checked["width"] > profile_info["width"] or checked["height"] > profile_info["height"]:
            raise RuntimeError("выходное разрешение превышает выбранный профиль")
        if abs((checked["fps"] or 0) - 25) > 0.1:
            raise RuntimeError("выходная частота кадров не равна 25 fps")
        if _sha256(source) != source_sha256:
            raise RuntimeError("исходник изменился во время конвертации")

        os.replace(temporary, destination)
        result = {
            "output_path": str(destination),
            "output_sha256": checked["sha256"],
            "output_size_bytes": checked["size_bytes"],
            "width": checked["width"],
            "height": checked["height"],
            "duration_seconds": checked["duration_seconds"],
            "fps": checked["fps"],
            "video_codec": checked["video_codec"],
            "encoder": encoder,
        }
        try:
            update_derivative(derivative_id, status="DONE", job_id=job_id, result=result)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        _call_progress(progress, total_us, total_us)
        return {"video_id": video_id, "derivative_id": derivative_id, "profile": profile, "status": "DONE", "encoder": encoder}
    except BaseException:
        temporary.unlink(missing_ok=True)
        progress_file.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)
        progress_file.unlink(missing_ok=True)
