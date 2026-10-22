"""
Формат файлов превью: WebP по умолчанию, JPEG как переключаемый вариант.

Проверяется без базы: расширение, MIME, параметры кодирования, переходный
период (старый JPEG рядом с новым WebP) и очистка прежнего формата.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from PIL import Image

from app.preview import formats
from app.preview.generator import build_preview_paths, generate_previews
from app.preview.validator import validate_preview
from app.ingest.register import PhotoRecord


def _record(source: Path, photo_id: str = "PH_" + "7" * 24) -> PhotoRecord:
    return PhotoRecord(
        photo_id=photo_id,
        source_path=str(source),
        filename=source.name,
        sha256="ab" * 32,
        container_format="JPEG",
        frame_count=1,
        width=8,
        height=8,
        size_bytes=source.stat().st_size,
    )


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "source.jpg"
    Image.new("RGB", (64, 48), "white").save(path, format="JPEG", quality=95)
    return path


# ---- settings --------------------------------------------------------------


def test_webp_is_the_default_format():
    assert formats.DEFAULT_FORMAT == "webp"
    assert formats.extension() == ".webp"
    assert formats.media_type() == "image/webp"


def test_format_from_the_environment(monkeypatch):
    monkeypatch.setenv("SCENE_PREVIEW_FORMAT", "JPEG")
    assert formats.current_format() == "jpeg"
    assert formats.extension() == ".jpg"
    assert formats.media_type() == "image/jpeg"

    monkeypatch.setenv("SCENE_PREVIEW_FORMAT", "jpg")
    assert formats.current_format() == "jpeg"

    monkeypatch.setenv("SCENE_PREVIEW_FORMAT", "tiff")
    assert formats.current_format() == formats.DEFAULT_FORMAT


def test_quality_default_depends_on_the_format(monkeypatch):
    monkeypatch.delenv("SCENE_PREVIEW_QUALITY", raising=False)
    assert formats.quality_for("webp") == 80
    assert formats.quality_for("jpeg") == 90


def test_explicit_quality_wins_over_the_default(monkeypatch):
    monkeypatch.setenv("SCENE_PREVIEW_QUALITY", "85")
    assert formats.quality_for("webp") == 85
    assert formats.quality_for("jpeg", value=95) == 95


def test_broken_quality_value_falls_back(monkeypatch):
    monkeypatch.setenv("SCENE_PREVIEW_QUALITY", "not a number")
    assert formats.quality_for("webp") == 80


# ---- path and transition ---------------------------------------------------


def test_paths_follow_the_format(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENE_PREVIEW_FORMAT", "webp")
    webp_paths = build_preview_paths(preview_root=tmp_path, photo_id="PH_x")
    assert webp_paths.small.name == "PH_x.webp"

    monkeypatch.setenv("SCENE_PREVIEW_FORMAT", "jpeg")
    jpeg_paths = build_preview_paths(preview_root=tmp_path, photo_id="PH_x")
    assert jpeg_paths.small.name == "PH_x.jpg"


def test_candidate_paths_put_the_current_format_first(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENE_PREVIEW_FORMAT", "webp")
    target = tmp_path / "small" / "PH_x.webp"

    candidates = formats.candidate_paths(target)

    assert candidates[0] == target
    assert candidates[1] == tmp_path / "small" / "PH_x.jpg"


def test_candidate_paths_do_not_repeat_the_same_path(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENE_PREVIEW_FORMAT", "jpeg")
    target = tmp_path / "small" / "PH_x.jpg"

    assert formats.candidate_paths(target) == [target]


def test_is_legacy_marks_only_the_old_format(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENE_PREVIEW_FORMAT", "webp")

    assert formats.is_legacy(tmp_path / "PH_x.jpg") is True
    assert formats.is_legacy(tmp_path / "PH_x.webp") is False
    assert formats.is_legacy(tmp_path / "note.txt") is False


# ---- generation ------------------------------------------------------------


def test_generate_writes_webp_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("SCENE_PREVIEW_FORMAT", raising=False)
    source = _source(tmp_path)
    root = tmp_path / "preview"

    result = generate_previews(
        record=_record(source),
        preview_root=root,
        small_size=32,
        middle_size=48,
    )

    assert result.ready is True
    paths = build_preview_paths(preview_root=root, photo_id=result.photo_id)
    assert paths.small.suffix == ".webp"
    assert paths.middle.suffix == ".webp"

    with Image.open(paths.small) as image:
        assert image.format == "WEBP"


def test_generate_can_still_produce_jpeg(tmp_path, monkeypatch):
    monkeypatch.setenv("SCENE_PREVIEW_FORMAT", "jpeg")
    source = _source(tmp_path)
    root = tmp_path / "preview"

    result = generate_previews(
        record=_record(source, "PH_" + "8" * 24),
        preview_root=root,
        small_size=32,
        middle_size=48,
    )

    paths = build_preview_paths(preview_root=root, photo_id=result.photo_id)
    assert paths.small.suffix == ".jpg"

    with Image.open(paths.small) as image:
        assert image.format == "JPEG"


def test_webp_preview_is_smaller_than_jpeg(tmp_path, monkeypatch):
    """Смысл перехода: тот же кадр в WebP q80 легче JPEG q90."""

    source = tmp_path / "photo.jpg"
    Image.effect_noise((400, 300), 40).convert("RGB").save(source, format="JPEG", quality=95)
    record = _record(source, "PH_" + "9" * 24)

    sizes = {}
    for name in ("jpeg", "webp"):
        monkeypatch.setenv("SCENE_PREVIEW_FORMAT", name)
        monkeypatch.delenv("SCENE_PREVIEW_QUALITY", raising=False)
        root = tmp_path / name

        generate_previews(
            record=record,
            preview_root=root,
            small_size=320,
            middle_size=320,
        )
        paths = build_preview_paths(preview_root=root, photo_id=record.photo_id)
        sizes[name] = paths.middle.stat().st_size

    assert sizes["webp"] < sizes["jpeg"]


# ---- validator -------------------------------------------------------------


def test_validator_accepts_webp_and_jpeg(tmp_path):
    webp = tmp_path / "a.webp"
    jpeg = tmp_path / "b.jpg"
    Image.new("RGB", (8, 8)).save(webp, format="WEBP")
    Image.new("RGB", (8, 8)).save(jpeg, format="JPEG")

    assert validate_preview(webp).valid is True
    assert validate_preview(jpeg).valid is True


def test_validator_still_rejects_other_formats(tmp_path):
    png = tmp_path / "c.jpg"  # PNG-байты под именем .jpg
    Image.new("RGB", (8, 8)).save(png, format="PNG")

    result = validate_preview(png)

    assert result.valid is False
    assert "Unsupported preview format" in result.error


def test_validator_can_be_limited_to_one_format(tmp_path):
    jpeg = tmp_path / "d.jpg"
    Image.new("RGB", (8, 8)).save(jpeg, format="JPEG")

    assert validate_preview(jpeg, allowed_formats={"WEBP"}).valid is False


# ---- очистка прежнего формата ---------------------------------------------


def _load_script(name: str, relative: str):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(name, root / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def legacy_tree(tmp_path, monkeypatch):
    """Каталог превью: пара WebP+JPEG, JPEG без замены, чужой файл."""

    root = tmp_path / "preview"
    small = root / "small"
    small.mkdir(parents=True)
    (root / "videos").mkdir(parents=True)

    (small / "PH_pair.webp").write_bytes(b"new")
    (small / "PH_pair.jpg").write_bytes(b"old-bytes")
    (small / "PH_alone.jpg").write_bytes(b"old-bytes-2")
    (root / "videos" / "VI_poster.jpg").write_bytes(b"poster")

    monkeypatch.setenv("SCENE_PREVIEW_ROOT", str(root))
    monkeypatch.setenv("SCENE_PREVIEW_FORMAT", "webp")
    return root


def test_purge_dry_run_changes_nothing(legacy_tree):
    module = _load_script("rebuild_previews", "scripts/rebuild_previews.py")

    report = module._purge_legacy(dry_run=True, limit=100)

    assert report["removed"] == 1
    assert report["kept_without_replacement"] == 1
    assert (legacy_tree / "small" / "PH_pair.jpg").exists()


def test_purge_removes_only_the_replaced_legacy_file(legacy_tree):
    module = _load_script("rebuild_previews", "scripts/rebuild_previews.py")

    report = module._purge_legacy(dry_run=False, limit=100)

    assert report["removed"] == 1
    assert (legacy_tree / "small" / "PH_pair.jpg").exists() is False
    # Замена осталась, файл без замены не тронут, постеры видео не затронуты.
    assert (legacy_tree / "small" / "PH_pair.webp").exists() is True
    assert (legacy_tree / "small" / "PH_alone.jpg").exists() is True
    assert (legacy_tree / "videos" / "VI_poster.jpg").exists() is True


def test_purge_respects_the_limit(legacy_tree):
    module = _load_script("rebuild_previews", "scripts/rebuild_previews.py")
    (legacy_tree / "small" / "PH_pair2.webp").write_bytes(b"new")
    (legacy_tree / "small" / "PH_pair2.jpg").write_bytes(b"old")

    first = module._purge_legacy(dry_run=False, limit=1)

    assert first["removed"] == 1
    assert first["limited"] is True
