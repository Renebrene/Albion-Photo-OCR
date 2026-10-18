from __future__ import annotations

from pathlib import Path

import pytest

from app.video import transcode
from app.ingest.video_integrity import metadata_identity_hash
from app.api import video_repository
from app.api.schemas import VideoTrimRequest
from pydantic import ValidationError


def _setup_trim(monkeypatch, tmp_path):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    source = source_root / "synthetic.mp4"
    source.write_bytes(b"synthetic-source")
    source_sha = metadata_identity_hash(source.name, "2026-10-15", source.stat().st_size)
    output_root = tmp_path / "derivatives"
    monkeypatch.setattr(transcode, "ORIGINALS_ROOTS", [source_root])
    monkeypatch.setattr(transcode, "SOURCE_ROOTS", [source_root])
    monkeypatch.setattr(transcode, "video_source", lambda _video_id: {
        "source_path": str(source), "filename": source.name, "sha256": source_sha,
        "identity_hash": source_sha, "identity_scheme": "metadata-v1", "identity_date": None,
        "taken_at": None, "duration_seconds": 10.0, "size_bytes": source.stat().st_size,
    })
    monkeypatch.setattr(transcode, "derivatives_root", lambda: output_root)
    monkeypatch.setattr(transcode, "_ffmpeg", lambda: "/fake/ffmpeg")
    monkeypatch.setenv("SCENE_VIDEO_TRANSCODE_THREADS", "2")
    monkeypatch.setattr(transcode, "update_derivative", lambda *_args, **_kwargs: None)
    def checked(path):
        path = Path(path)
        return {
            "integrity_status": "VALID", "filename": path.name,
            "video_codec": "h264", "width": 640, "height": 360,
            "duration_seconds": 10.0 if path == source else 3.0, "fps": 25.0,
            "identity_hash": metadata_identity_hash(path.name, "2026-10-15", path.stat().st_size),
            "identity_date": "2026-10-15", "taken_at": None,
            "size_bytes": path.stat().st_size,
        }

    monkeypatch.setattr(transcode, "check_video_file", checked)
    return source, source_sha, output_root


def test_trim_request_schema_rejects_invalid_ranges():
    assert VideoTrimRequest(start_seconds=0, end_seconds=1).end_seconds == 1
    for payload in (
        {"start_seconds": -1, "end_seconds": 1},
        {"start_seconds": 2, "end_seconds": 1},
        {"start_seconds": 1, "end_seconds": 1.1},
        {"start_seconds": float("nan"), "end_seconds": 2},
        {"start_seconds": 1, "end_seconds": float("inf")},
    ):
        with pytest.raises(ValidationError):
            VideoTrimRequest(**payload)


def _storyboard_source(monkeypatch, source, duration):
    monkeypatch.setattr(transcode, "video_source", lambda _video_id: {
        "source_path": str(source), "filename": source.name, "sha256": "ef" * 32,
        "identity_scheme": "legacy-content-sha256", "taken_at": None,
        "duration_seconds": duration, "size_bytes": source.stat().st_size,
    })
    monkeypatch.setattr(transcode, "check_video_file", lambda path: {
        "integrity_status": "VALID", "filename": Path(path).name,
        "size_bytes": Path(path).stat().st_size, "duration_seconds": duration,
        "taken_at": None,
    })


def test_storyboard_creates_bounded_jpegs_without_touching_source(monkeypatch, tmp_path):
    from PIL import Image

    source_root = tmp_path / "source"
    source_root.mkdir()
    source = source_root / "synthetic.mp4"
    source.write_bytes(b"synthetic-video")
    source_hash = "ef" * 32
    storyboard_root = tmp_path / "storyboards"
    monkeypatch.setattr(transcode, "ORIGINALS_ROOTS", [source_root])
    monkeypatch.setattr(transcode, "SOURCE_ROOTS", [source_root])
    monkeypatch.setattr(transcode, "VIDEO_STORYBOARD_ROOT", storyboard_root)
    _storyboard_source(monkeypatch, source, 12.0)

    class CompletedProcess:
        returncode = 0

        def poll(self):
            return self.returncode

    def fake_popen(args, **_kwargs):
        with Image.new("RGB", (320, 180)) as image:
            image.save(args[-1], format="JPEG")
        return CompletedProcess()

    monkeypatch.setattr(transcode.subprocess, "Popen", fake_popen)
    progress = []
    result = transcode.generate_storyboard(
        video_id="VI_" + "78" * 12, source_sha256=source_hash,
        progress=lambda *args: progress.append(args),
    )

    assert result["frames"] == transcode.STORYBOARD_FRAME_COUNT == 8
    assert len(list(storyboard_root.rglob("*.jpg"))) == 8
    assert source.read_bytes() == b"synthetic-video"
    assert progress[-1][0:2] == (8, 8)


def test_storyboard_cancellation_terminates_ffmpeg_child(tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    source_root.mkdir()
    source = source_root / "synthetic.mp4"
    source.write_bytes(b"synthetic-video")
    source_hash = "ef" * 32
    monkeypatch.setattr(transcode, "ORIGINALS_ROOTS", [source_root])
    monkeypatch.setattr(transcode, "SOURCE_ROOTS", [source_root])
    monkeypatch.setattr(transcode, "VIDEO_STORYBOARD_ROOT", tmp_path / "storyboards")
    _storyboard_source(monkeypatch, source, 10.0)

    class Process:
        returncode = None
        terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        def wait(self, timeout=None):
            self.returncode = -15

    process = Process()
    monkeypatch.setattr(transcode.subprocess, "Popen", lambda *_args, **_kwargs: process)
    progress_calls = 0

    def cancel_on_poll(_done, _total, _stage):
        nonlocal progress_calls
        progress_calls += 1
        if progress_calls >= 2:
            raise transcode.VideoTranscodeCancelled("cancel")

    with pytest.raises(transcode.VideoTranscodeCancelled):
        transcode.generate_storyboard(
            video_id="VI_" + "78" * 12, source_sha256=source_hash, progress=cancel_on_poll,
        )
    assert process.terminated is True


def test_storyboard_rejects_symlinked_video_directory(tmp_path, monkeypatch):
    source_root = tmp_path / "source"
    source_root.mkdir()
    source = source_root / "synthetic.mp4"
    source.write_bytes(b"synthetic-video")
    source_hash = "ef" * 32
    storyboard_root = tmp_path / "storyboards"
    storyboard_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (storyboard_root / ("VI_" + "78" * 12)).symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(transcode, "ORIGINALS_ROOTS", [source_root])
    monkeypatch.setattr(transcode, "SOURCE_ROOTS", [source_root])
    monkeypatch.setattr(transcode, "VIDEO_STORYBOARD_ROOT", storyboard_root)
    _storyboard_source(monkeypatch, source, 10.0)

    with pytest.raises(ValueError, match="escapes"):
        transcode.generate_storyboard(video_id="VI_" + "78" * 12, source_sha256=source_hash)


def test_trim_range_normalizes_key_and_rejects_invalid_intervals():
    assert video_repository.normalize_trim_range(1.23456, 4.56789) == (1.235, 4.568, "trim:1.235:4.568")
    with pytest.raises(ValueError):
        video_repository.normalize_trim_range(4, 4)
    with pytest.raises(ValueError):
        video_repository.normalize_trim_range(-1, 1)


def test_trim_publishes_unique_derivative_and_preserves_source(tmp_path, monkeypatch):
    source, source_sha, output_root = _setup_trim(monkeypatch, tmp_path)
    original = source.read_bytes()
    captured = {}

    def fake_encode(args, *, temp_output, **_kwargs):
        captured["args"] = args
        temp_output.write_bytes(b"trimmed-output")

    monkeypatch.setattr(transcode, "_run_encoder", fake_encode)
    updates = []
    monkeypatch.setattr(transcode, "update_derivative", lambda *args, **kwargs: updates.append((args, kwargs)))

    result = transcode.run_trim(
        video_id="VI_" + "12" * 12, derivative_id=14, source_sha256=source_sha,
        start_seconds=2.0, end_seconds=5.0, job_id=77, progress=lambda *_args: None,
    )

    output = output_root / ("VI_" + "12" * 12) / "synthetic_копия.mp4"
    assert output.read_bytes() == b"trimmed-output"
    assert source.read_bytes() == original
    assert result["status"] == "DONE"
    assert result["start_seconds"] == 2.0 and result["end_seconds"] == 5.0
    assert updates[-1][1]["result"]["operation_kind"] == "TRIM"
    assert updates[-1][1]["result"]["output_path"] == str(output)
    assert captured["args"][captured["args"].index("-ss") + 1] == "2.000"
    assert captured["args"][captured["args"].index("-t") + 1] == "3.000"
    assert "trim=" not in captured["args"][captured["args"].index("-vf") + 1]
    assert "libx264" in captured["args"]
    assert "h264_nvenc" not in captured["args"]


def test_storyboard_worker_dispatches_bounded_generation(monkeypatch):
    from app.jobs import worker

    calls = []
    monkeypatch.setattr(transcode, "generate_storyboard", lambda **kwargs: calls.append(kwargs) or {"frames": 8})
    monkeypatch.setattr(worker, "job_control", lambda _job_id: lambda *_args: None)
    result = worker._execute({
        "id": 21, "job_type": "VIDEO_STORYBOARD",
        "payload": {"video_id": "VI_" + "67" * 12, "source_sha256": "ef" * 32},
    })
    assert result == {"frames": 8}
    assert calls[0]["video_id"] == "VI_" + "67" * 12


def test_trim_worker_dispatches_trim_job(monkeypatch):
    from app.jobs import worker

    calls = []
    monkeypatch.setattr(transcode, "run_trim", lambda **kwargs: calls.append(kwargs) or {"status": "DONE"})
    monkeypatch.setattr(worker, "job_control", lambda _job_id: lambda *_args: None)
    monkeypatch.setattr(video_repository, "register_completed_derivative", lambda _id: "VI_" + "ab" * 12)
    monkeypatch.setattr(video_repository, "registered_asset_source", lambda _id: {"source_path": "/tmp/copy.mp4", "duration_seconds": 1.0})
    from app.preview import video as preview_video
    monkeypatch.setattr(preview_video, "build_video_poster", lambda *_args, **_kwargs: None)

    result = worker._execute({
        "id": 99,
        "job_type": "VIDEO_TRIM",
        "payload": {
            "video_id": "VI_" + "56" * 12,
            "derivative_id": 19,
            "source_sha256": "cd" * 32,
            "start_seconds": 1.25,
            "end_seconds": 4.5,
        },
    })

    assert result == {"status": "DONE", "asset_video_id": "VI_" + "ab" * 12}
    assert calls[0]["start_seconds"] == 1.25
    assert calls[0]["end_seconds"] == 4.5


def test_trim_rejects_symlinked_derivative_video_directory(tmp_path, monkeypatch):
    source, source_sha, output_root = _setup_trim(monkeypatch, tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    output_root.mkdir()
    video_id = "VI_" + "90" * 12
    (output_root / video_id).symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="managed root"):
        transcode.run_trim(
            video_id=video_id, derivative_id=16, source_sha256=source_sha,
            start_seconds=1, end_seconds=4, job_id=79, progress=lambda *_args: None,
        )

    assert not list(outside.iterdir())
    assert source.read_bytes() == b"synthetic-source"


def test_trim_rejects_range_past_source_duration(tmp_path, monkeypatch):
    source, source_sha, _ = _setup_trim(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="source duration"):
        transcode.run_trim(
            video_id="VI_" + "34" * 12, derivative_id=15, source_sha256=source_sha,
            start_seconds=9.0, end_seconds=11.0, job_id=78, progress=lambda *_args: None,
        )
