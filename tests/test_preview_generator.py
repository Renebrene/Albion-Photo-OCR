"""
Unit tests for atomic preview generation in app.preview.generator.

Previews are written to a temporary file and published with os.replace only
after validation. These tests use the real generator (no database): they check
that no temporary file survives and that a failed regeneration keeps the
previously existing file untouched.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

from app.ingest.register import PhotoRecord
from app.preview.generator import build_preview_paths, generate_previews


def _record(source: Path, photo_id: str) -> PhotoRecord:
    return PhotoRecord(
        photo_id=photo_id,
        source_path=str(source),
        filename=source.name,
        sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        container_format="JPEG",
        frame_count=1,
        width=64,
        height=48,
    )


def _missing_record(source: Path, photo_id: str) -> PhotoRecord:
    return PhotoRecord(
        photo_id=photo_id,
        source_path=str(source),
        filename=source.name,
        sha256=hashlib.sha256(photo_id.encode()).hexdigest(),
        container_format="JPEG",
        frame_count=1,
        width=64,
        height=48,
    )


def _make_source(root: Path) -> Path:
    source = root / "src.JPG"
    Image.new("RGB", (64, 48), (10, 20, 30)).save(source, format="JPEG")
    return source


def _temp_files(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return [path.name for path in directory.iterdir() if path.name.startswith(".")]


def test_success_publishes_previews_without_temp(tmp_path):
    source = _make_source(tmp_path)
    record = _record(source, "PH_" + "0" * 24)
    root = tmp_path / "preview"

    result = generate_previews(
        record=record,
        preview_root=root,
        small_size=32,
        middle_size=64,
    )

    assert result.ready is True
    assert result.small.action == "CREATE"
    assert result.middle.action == "CREATE"
    # Расширение задаёт SCENE_PREVIEW_FORMAT: путь берём из генератора,
    # а не хардкодим .jpg.
    paths = build_preview_paths(preview_root=root, photo_id=record.photo_id)
    assert paths.small.exists()
    assert paths.middle.exists()
    assert _temp_files(root / "small") == []
    assert _temp_files(root / "middle") == []


def test_failed_create_leaves_no_output_and_no_temp(tmp_path):
    record = _missing_record(tmp_path / "missing.JPG", "PH_" + "1" * 24)
    root = tmp_path / "preview"

    result = generate_previews(
        record=record,
        preview_root=root,
        small_size=32,
        middle_size=64,
    )

    assert result.ready is False
    assert result.small.action == "ERROR"
    assert result.middle.action == "ERROR"
    paths = build_preview_paths(preview_root=root, photo_id=record.photo_id)
    assert not paths.small.exists()
    assert _temp_files(root / "small") == []
    assert _temp_files(root / "middle") == []


def test_failed_regenerate_keeps_existing_file(tmp_path):
    source = _make_source(tmp_path)
    record = _record(source, "PH_" + "2" * 24)
    root = tmp_path / "preview"

    generate_previews(
        record=record,
        preview_root=root,
        small_size=32,
        middle_size=64,
    )

    paths = build_preview_paths(preview_root=root, photo_id=record.photo_id)
    paths.small.write_bytes(b"corrupted-not-a-jpeg")
    paths.middle.write_bytes(b"corrupted-not-a-jpeg")

    # Both previews are damaged and the original is gone: nothing can be
    # rebuilt, so the existing files must stay exactly as they were.
    source.unlink()

    result = generate_previews(
        record=record,
        preview_root=root,
        small_size=32,
        middle_size=64,
    )

    assert result.small.action == "ERROR"
    assert result.middle.action == "ERROR"
    assert paths.small.read_bytes() == b"corrupted-not-a-jpeg"
    assert paths.middle.read_bytes() == b"corrupted-not-a-jpeg"
    assert _temp_files(root / "small") == []
    assert _temp_files(root / "middle") == []


def test_original_is_decoded_once_for_both_sizes(tmp_path, monkeypatch):
    source = _make_source(tmp_path)
    record = _record(source, "PH_" + "4" * 24)
    calls: list[str] = []

    import app.preview.generator as generator

    original = generator._load_visual_source

    def counted(record):
        calls.append(record.photo_id)
        return original(record)

    monkeypatch.setattr(generator, "_load_visual_source", counted)

    result = generate_previews(
        record=record,
        preview_root=tmp_path / "preview",
        small_size=32,
        middle_size=64,
        image_format="webp",
    )

    assert result.ready is True
    # Previously SMALL and MIDDLE each opened and decoded the original.
    assert calls == [record.photo_id]


def test_small_is_rebuilt_from_middle_when_source_is_gone(tmp_path):
    source = _make_source(tmp_path)
    record = _record(source, "PH_" + "5" * 24)
    root = tmp_path / "preview"

    generate_previews(
        record=record,
        preview_root=root,
        small_size=32,
        middle_size=64,
        image_format="webp",
    )

    paths = build_preview_paths(
        preview_root=root,
        photo_id=record.photo_id,
        image_format="webp",
    )
    paths.small.unlink()
    source.unlink()

    result = generate_previews(
        record=record,
        preview_root=root,
        small_size=32,
        middle_size=64,
        image_format="webp",
    )

    assert result.middle.action == "SKIP"
    assert result.small.action == "CREATE"
    assert result.small.valid is True
    assert paths.small.exists()


def test_preview_quality_is_validated(tmp_path):
    source = _make_source(tmp_path)
    record = _record(source, "PH_" + "3" * 24)

    for quality in (0, 101):
        try:
            generate_previews(
                record=record,
                preview_root=tmp_path / "preview",
                small_size=32,
                middle_size=64,
                quality=quality,
            )
        except ValueError:
            continue
        raise AssertionError(f"quality {quality} must be rejected")
