from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app.ingest import video_integrity, video_register
from app.ingest.integrity import Discovery


def _probe_json(*, duration="2.0", codec="h264", creation_time="2026-10-15T08:12:30Z"):
    return {
        "format": {
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
            "duration": duration,
            "size": "1234",
            "tags": {"creation_time": creation_time},
        },
        "streams": [
            {
                "codec_type": "video",
                "codec_name": codec,
                "width": 1920,
                "height": 1080,
                "avg_frame_rate": "25/1",
                "r_frame_rate": "25/1",
                "nb_frames": "50",
                "duration": duration,
            },
            {"codec_type": "audio", "codec_name": "aac"},
        ],
    }


def _install_probe(monkeypatch, metadata=None):
    calls = []

    # The probe matches on argv[0]; a deployment may pin the binaries through
    # SCENE_FFPROBE_BIN/SCENE_FFMPEG_BIN to absolute paths. Pin them here so the
    # test asserts the same thing regardless of the ambient environment.
    monkeypatch.setenv("SCENE_FFPROBE_BIN", "ffprobe")
    monkeypatch.setenv("SCENE_FFMPEG_BIN", "ffmpeg")

    def fake_run(args, *, timeout):
        calls.append((args, timeout))
        if args[0] == "ffprobe":
            return subprocess.CompletedProcess(args, 0, json.dumps(metadata or _probe_json()), "")
        assert args[0] == "ffmpeg"
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(video_integrity, "_run", fake_run)
    return calls


def _video_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"synthetic video fixture")
    return path


def test_video_integrity_uses_metadata_identity_without_reading_contents(tmp_path, monkeypatch):
    source = _video_file(tmp_path / "папка with spaces" / "sample.MP4")
    original_bytes = source.read_bytes()
    calls = _install_probe(monkeypatch)

    result = video_integrity.check_video_file(source)

    assert result["integrity_status"] == "VALID"
    assert result["sha256"] is None
    assert result["identity_hash"] == video_integrity.metadata_identity_hash(
        source.name, "2026-10-15", len(original_bytes)
    )
    assert result["identity_date"] == "2026-10-15"
    assert result["container_format"].startswith("mov")
    assert result["video_codec"] == "h264"
    assert (result["width"], result["height"]) == (1920, 1080)
    assert result["duration_seconds"] == 2
    assert result["fps"] == 25
    assert result["frame_count"] == 50
    assert result["size_bytes"] == len(original_bytes)
    assert result["taken_at"].isoformat() == "2026-10-15T08:12:30+00:00"
    assert [call[0][0] for call in calls] == ["ffprobe"]
    assert source.read_bytes() == original_bytes
    assert all(call[0].count(str(source)) == 1 for call in calls)


def test_video_identity_date_falls_back_to_utc_mtime_date(tmp_path, monkeypatch):
    source = _video_file(tmp_path / "fallback.mp4")
    stamp = 1_796_140_800  # 2026-12-01T00:00:00Z
    import os

    os.utime(source, (stamp, stamp))
    calls = _install_probe(monkeypatch, _probe_json(creation_time=None))

    result = video_integrity.check_video_file(source)

    assert result["integrity_status"] == "VALID"
    assert result["taken_at"] is None
    assert result["identity_date"] == "2026-12-01"
    assert result["identity_hash"] == video_integrity.metadata_identity_hash(
        source.name, "2026-12-01", source.stat().st_size
    )
    assert len(calls) == 1


def test_video_integrity_rejects_unsupported_extension_without_running_tools(tmp_path, monkeypatch):
    source = _video_file(tmp_path / "clip.avi")
    monkeypatch.setattr(
        video_integrity,
        "_run",
        lambda *_args, **_kwargs: pytest.fail("tools must not run for unsupported extension"),
    )

    result = video_integrity.check_video_file(source)

    assert result["integrity_status"] == "INVALID"
    assert result["extension_valid"] is False
    assert "расширение" in result["error"]


def test_video_integrity_accepts_duration_above_old_ingest_limit(tmp_path, monkeypatch):
    source = _video_file(tmp_path / "long.mp4")
    calls = _install_probe(monkeypatch, _probe_json(duration="21"))
    monkeypatch.setenv("SCENE_INGEST_MAX_VIDEO_SECONDS", "20")

    result = video_integrity.check_video_file(source)

    assert result["integrity_status"] == "VALID"
    assert result["duration_seconds"] == 21
    assert len(calls) == 1  # ingest does not run a full decode


def test_video_integrity_handles_missing_ffmpeg_as_actionable_error(tmp_path, monkeypatch):
    source = _video_file(tmp_path / "clip.mp4")

    def missing(_args, *, timeout):
        raise FileNotFoundError("not on PATH")

    monkeypatch.setattr(video_integrity, "_run", missing)
    result = video_integrity.check_video_file(source)

    assert result["integrity_status"] == "INVALID"
    assert "ffprobe не установлен" in result["error"]


def test_video_identity_hashes_basename_date_and_size_only():
    digest = video_register.metadata_identity_hash("folder/clip.mp4", "2026-10-15", 1234)
    assert video_register.create_video_identity("clip.mp4", "2026-10-15", 1234) == "VI_" + digest[:24]
    assert video_register.metadata_identity_hash("clip.mp4", "2026-10-15", 1235) != digest
    assert video_register.metadata_identity_hash("clip.mp4", "2026-10-16", 1234) != digest
    assert video_register.metadata_identity_hash("other.mp4", "2026-10-15", 1234) != digest


def test_register_video_validates_nullable_fields_and_metadata():
    identity_hash = video_register.metadata_identity_hash("clip.mp4", "2026-10-15", 900)
    record = video_register.register_video(
        source_path="/tmp/source/clip.mp4",
        filename="clip.mp4",
        sha256=None,
        identity_hash=identity_hash,
        identity_date="2026-10-15",
        container_format="mov,mp4,m4a",
        video_codec="h264",
        width=1920,
        height=1080,
        duration_seconds=3.2,
        fps=None,
        frame_count=None,
        size_bytes=900,
        taken_at=None,
    )

    assert record.video_id == "VI_" + identity_hash[:24]
    assert record.sha256 is None
    assert record.identity_hash == identity_hash
    assert record.fps is None
    assert record.frame_count is None
    assert record.taken_at is None

    with pytest.raises(ValueError):
        video_register.register_video(
            source_path="x", filename="x.mp4", sha256=None,
            identity_hash=video_register.metadata_identity_hash("x.mp4", "2026-10-15", 10),
            identity_date="2026-10-15",
            container_format="mp4", video_codec="h264", width=0,
            height=1080, duration_seconds=2, size_bytes=10,
        )


def test_ingest_directory_keeps_video_out_of_photo_records(tmp_path, monkeypatch):
    from app.ingest import runner
    from app.ingest.result import create_ingest_result

    video_path = _video_file(tmp_path / "video.mp4")
    monkeypatch.setattr(runner, "run", lambda *args, **kwargs: create_ingest_result([]))
    monkeypatch.setattr(runner, "check_identity_batch", lambda records: {"NEW": [], "EXISTING": [], "CONFLICT": []})
    monkeypatch.setattr(
        runner,
        "discover_videos",
        lambda *args, **kwargs: Discovery(files=[video_path], excluded_by_period=0),
    )
    monkeypatch.setattr(
        runner,
        "check_video_file",
        lambda _path: {
            "integrity_status": "VALID", "source_path": str(video_path),
            "filename": video_path.name, "sha256": None,
            "identity_hash": video_register.metadata_identity_hash(
                video_path.name, "2026-10-15", video_path.stat().st_size
            ), "identity_date": "2026-10-15",
            "container_format": "mp4", "video_codec": "h264", "width": 640,
            "height": 360, "duration_seconds": 2.0, "fps": 25.0,
            "frame_count": 50, "size_bytes": video_path.stat().st_size,
            "taken_at": None,
        },
    )
    monkeypatch.setattr(
        runner,
        "register_video_records",
        lambda records: {"NEW": records, "EXISTING": [], "CONFLICT": []},
    )
    monkeypatch.setattr(runner, "default_video_preview_root", lambda: tmp_path / "posters")
    monkeypatch.setattr(runner, "build_video_poster", lambda *_args, **_kwargs: tmp_path / "poster.jpg")

    result = runner.ingest_directory(tmp_path, workers=1)

    assert result["registered"] == 0  # photo pipeline remained unchanged
    assert result["videos"]["registered"] == 1
    assert result["videos"]["discovered"] == 1
    assert result["videos"]["conflicts"] == []
