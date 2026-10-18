from __future__ import annotations

from pathlib import Path

import pytest

from app.api import file_access
from app.ingest.video_integrity import metadata_identity_hash
from app.video import transcode


def test_cpu_worker_default_is_half_the_logical_cores(monkeypatch):
    monkeypatch.setenv("SCENE_VIDEO_ENCODER", "cpu")
    monkeypatch.delenv("SCENE_VIDEO_TRANSCODE_WORKERS", raising=False)
    assert transcode.choose_worker_mode(cpu_count=12) == ("libx264", 6)
    assert transcode.choose_worker_mode(cpu_count=1) == ("libx264", 1)


def test_profiles_use_expected_caps_and_crf():
    from app.video.profiles import PROFILES

    assert (PROFILES["strong_720p"]["width"], PROFILES["strong_720p"]["height"]) == (1280, 720)
    assert (PROFILES["standard_1080p"]["width"], PROFILES["standard_1080p"]["height"]) == (1920, 1080)
    assert (PROFILES["light_1440p"]["width"], PROFILES["light_1440p"]["height"]) == (2560, 1440)
    assert PROFILES["strong_720p"]["crf"] > PROFILES["light_1440p"]["crf"]


def _setup_transcode(monkeypatch, tmp_path):
    source_root = tmp_path / "source"
    source_root.mkdir()
    source = source_root / "clip.mp4"
    source.write_bytes(b"original-source-content")
    source_digest = metadata_identity_hash(source.name, "2026-10-15", source.stat().st_size)
    output_root = tmp_path / "derivatives"
    monkeypatch.setattr(transcode, "ORIGINALS_ROOTS", [source_root])
    monkeypatch.setattr(transcode, "video_source", lambda _video_id: {
        "source_path": str(source), "filename": source.name,
        "sha256": source_digest, "identity_hash": source_digest,
        "identity_scheme": "metadata-v1", "identity_date": None, "taken_at": None,
        "duration_seconds": 2.0, "size_bytes": source.stat().st_size,
    })
    monkeypatch.setattr(transcode, "derivatives_root", lambda: output_root)
    monkeypatch.setattr(transcode, "choose_worker_mode", lambda: ("libx264", 2))
    monkeypatch.setenv("SCENE_VIDEO_TRANSCODE_THREADS", "2")
    monkeypatch.delenv("SCENE_VIDEO_ENCODER_RESOLVED", raising=False)
    updates = []
    monkeypatch.setattr(transcode, "update_derivative", lambda *args, **kwargs: updates.append((args, kwargs)))
    monkeypatch.setattr(transcode, "check_video_file", lambda path: {
        "integrity_status": "VALID",
        "filename": Path(path).name,
        "identity_hash": metadata_identity_hash(Path(path).name, "2026-10-15", Path(path).stat().st_size),
        "identity_date": "2026-10-15",
        "taken_at": None,
        "video_codec": "h264",
        "width": 640,
        "height": 360,
        "duration_seconds": 2.0,
        "fps": 25.0,
        "size_bytes": Path(path).stat().st_size,
    })
    return source, source_digest, output_root, updates


def test_run_transcode_publishes_new_derivative_and_preserves_source(tmp_path, monkeypatch):
    source, digest, output_root, updates = _setup_transcode(monkeypatch, tmp_path)
    before = source.read_bytes()
    captured = {}

    def fake_encode(args, *, progress_file, temp_output, total_us, progress, timeout):
        captured["args"] = args
        temp_output.write_bytes(b"encoded-output")
        progress(total_us, total_us, "VIDEO_TRANSCODE")

    monkeypatch.setattr(transcode, "_run_encoder", fake_encode)
    result = transcode.run_transcode(
        video_id="VI_" + "11" * 12,
        derivative_id=7,
        profile="strong_720p",
        source_sha256=digest,
        job_id=13,
        progress=lambda *_args: None,
    )

    output = Path(updates[-1][1]["result"]["output_path"])
    assert output.is_file()
    assert output.read_bytes() == b"encoded-output"
    assert source.read_bytes() == before
    assert result["status"] == "DONE"
    assert result["encoder"] == "libx264"
    assert "-threads" in captured["args"]
    assert "25" in captured["args"]
    assert updates[0][1]["status"] == "RUNNING"
    assert updates[-1][1]["status"] == "DONE"


def test_nvenc_runtime_error_falls_back_to_cpu(tmp_path, monkeypatch):
    source, digest, output_root, updates = _setup_transcode(monkeypatch, tmp_path)
    monkeypatch.setenv("SCENE_VIDEO_ENCODER_RESOLVED", "h264_nvenc")
    attempts = []

    def fake_encode(args, *, progress_file, temp_output, total_us, progress, timeout):
        encoder_index = args.index("-c:v") + 1
        encoder = args[encoder_index]
        attempts.append(encoder)
        if encoder == "h264_nvenc":
            raise transcode.FFmpegEncodeError("NVENC device unavailable")
        temp_output.write_bytes(b"cpu-encoded")

    monkeypatch.setattr(transcode, "_run_encoder", fake_encode)
    result = transcode.run_transcode(
        video_id="VI_" + "22" * 12,
        derivative_id=8,
        profile="standard_1080p",
        source_sha256=digest,
        job_id=14,
        progress=lambda *_args: None,
    )

    assert attempts == ["h264_nvenc", "libx264"]
    assert result["encoder"] == "libx264"
    output_path = updates[-1][1]["result"]["output_path"]
    assert Path(output_path).read_bytes() == b"cpu-encoded"


def test_failed_database_publish_removes_completed_output(tmp_path, monkeypatch):
    source, digest, output_root, updates = _setup_transcode(monkeypatch, tmp_path)

    def fake_encode(_args, *, temp_output, **_kwargs):
        temp_output.write_bytes(b"encoded-output")

    def fail_done_update(*_args, **kwargs):
        if kwargs.get("status") == "DONE":
            raise OSError("database unavailable")
        updates.append(((), kwargs))

    monkeypatch.setattr(transcode, "_run_encoder", fake_encode)
    monkeypatch.setattr(transcode, "update_derivative", fail_done_update)

    with pytest.raises(OSError, match="database unavailable"):
        transcode.run_transcode(
            video_id="VI_" + "44" * 12,
            derivative_id=10,
            profile="strong_720p",
            source_sha256=digest,
            job_id=16,
            progress=lambda *_args: None,
        )

    assert not list(output_root.rglob("*.mp4"))
    assert source.read_bytes() == b"original-source-content"


def test_cancel_terminates_without_publishing_original_or_partial(tmp_path, monkeypatch):
    source, digest, output_root, updates = _setup_transcode(monkeypatch, tmp_path)
    original = source.read_bytes()

    def cancelled(*_args, **_kwargs):
        raise transcode.VideoTranscodeCancelled("cancel")

    monkeypatch.setattr(transcode, "_run_encoder", cancelled)
    with pytest.raises(transcode.VideoTranscodeCancelled):
        transcode.run_transcode(
            video_id="VI_" + "33" * 12,
            derivative_id=9,
            profile="light_1440p",
            source_sha256=digest,
            job_id=15,
            progress=lambda *_args: None,
        )

    assert source.read_bytes() == original
    assert not list(output_root.rglob("*.mp4"))
