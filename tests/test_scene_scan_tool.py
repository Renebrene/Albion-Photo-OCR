from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from PIL import Image, ImageDraw

from tools.scene_scan.scan import (
    export_selected,
    normalize_stem,
    relative_name_group,
    scan,
)


def make_scene(path: Path, scene: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (96, 96), "black")
    draw = ImageDraw.Draw(image)
    left = (scene % 4) * 24
    top = (scene // 4) * 24
    draw.rectangle((left, top, left + 20, top + 20), fill="white")
    # Add a small distinct mark so visually similar positions still hash apart.
    draw.line((0, scene * 7 % 96, 95, (scene * 7 + 20) % 96), fill=(scene * 23 % 255, 80, 200), width=3)
    image.save(path, format="JPEG", quality=95)
    return path


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_only_terminal_numeric_parenthesis_suffix_is_normalized():
    assert normalize_stem("Building (12).JPG") == "building"
    assert normalize_stem("Building (draft).jpg") == "building (draft)"
    assert normalize_stem("Building 12.jpg") == "building 12"
    assert normalize_stem("(12).jpg") == ""


def test_same_name_in_different_directories_is_not_same_name_group(tmp_path):
    root = tmp_path / "source"
    first = make_scene(root / "one" / "photo.jpg", 1)
    second = make_scene(root / "two" / "photo (2).JPG", 2)

    assert relative_name_group(root, first) == "one/photo"
    assert relative_name_group(root, second) == "two/photo"


def test_scan_recurses_caches_hashes_and_keeps_sources_unchanged(tmp_path, monkeypatch):
    root = tmp_path / "исходные фото with spaces"
    originals = []
    for scene in range(4):
        originals.append(make_scene(root / f"Address {scene}" / f"scene_{scene}.jpg", scene))
        originals.append(make_scene(root / f"Address {scene}" / f"scene_{scene} (1).jpg", scene))
    before = {path: file_hash(path) for path in originals}
    database = tmp_path / "working" / "scene.sqlite3"
    csv_path = tmp_path / "working" / "report.csv"

    calls = 0
    from app.core import scene_select

    original = scene_select.frame_features

    def counted(path):
        nonlocal calls
        calls += 1
        return original(path)

    monkeypatch.setattr(scene_select, "frame_features", counted)

    result1 = scan(root, database, limit=3, csv_path=csv_path)
    first_calls = calls
    result2 = scan(root, database, limit=3)

    assert result1["total_files"] == 8
    assert result1["readable_files"] == 8
    assert result1["groups_by_name"] == 4
    assert result1["selected"] <= 3
    assert result2["selected"] == result1["selected"]
    assert calls == first_calls  # unchanged size + mtime reused stored hashes/features
    assert csv_path.read_text(encoding="utf-8-sig").startswith("relative_path;")
    assert {path: file_hash(path) for path in originals} == before

    with sqlite3.connect(database) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM files").fetchone()[0] == 8
        assert conn.execute("SELECT COUNT(*) FROM scan_runs WHERE status='DONE'").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM scan_items WHERE selected=1").fetchone()[0] <= 6
        assert conn.execute("SELECT COUNT(*) FROM files WHERE sha256 IS NOT NULL").fetchone()[0] == 8


def test_changed_file_is_rehashed_and_deleted_file_is_retained_as_missing(tmp_path, monkeypatch):
    root = tmp_path / "source"
    target = make_scene(root / "one.jpg", 1)
    other = make_scene(root / "two.jpg", 2)
    database = tmp_path / "index.sqlite3"

    first = scan(root, database, limit=1)
    with sqlite3.connect(database) as conn:
        old_digest = conn.execute("SELECT sha256 FROM files WHERE relative_path='one.jpg'").fetchone()[0]

    make_scene(target, 9)
    target.touch()
    second = scan(root, database, limit=1)
    with sqlite3.connect(database) as conn:
        new_digest = conn.execute("SELECT sha256 FROM files WHERE relative_path='one.jpg'").fetchone()[0]
    assert new_digest != old_digest

    other.unlink()
    scan(root, database, limit=1)
    with sqlite3.connect(database) as conn:
        missing = conn.execute("SELECT missing FROM files WHERE relative_path='two.jpg'").fetchone()[0]
    assert missing == 1
    assert first["run_id"] < second["run_id"]


def test_selection_caps_at_twenty_when_tree_has_more_candidates(tmp_path):
    root = tmp_path / "source"
    for scene in range(24):
        make_scene(root / f"view_{scene:02}.jpg", scene)
    database = tmp_path / "index.sqlite3"

    result = scan(root, database, limit=20)

    assert result["total_files"] == 24
    assert result["selected"] <= 20
    assert result["series"] >= result["selected"]
    if result["series"] >= 20:
        assert result["selected"] == 20


def test_database_and_csv_are_required_outside_source(tmp_path):
    root = tmp_path / "source"
    make_scene(root / "photo.jpg", 1)

    try:
        scan(root, root / "inside.sqlite3")
    except ValueError as exc:
        assert "вне сканируемой" in str(exc)
    else:
        raise AssertionError("database inside source must be rejected")

    try:
        scan(root, tmp_path / "index.sqlite3", csv_path=root / "report.csv")
    except ValueError as exc:
        assert "CSV-отчёт" in str(exc)
    else:
        raise AssertionError("CSV inside source must be rejected")


def test_unreadable_image_is_recorded_and_does_not_stop_scan(tmp_path):
    root = tmp_path / "source"
    make_scene(root / "valid.jpg", 1)
    broken = root / "broken.jpg"
    broken.write_bytes(b"not a jpeg")
    database = tmp_path / "index.sqlite3"

    result = scan(root, database)

    assert result["total_files"] == 2
    assert result["readable_files"] == 1
    assert result["errors"] == 1
    with sqlite3.connect(database) as conn:
        error = conn.execute("SELECT scan_error FROM files WHERE relative_path='broken.jpg'").fetchone()[0]
    assert error


def test_fewer_than_requested_photos_are_all_selected_and_export_is_copy_only(tmp_path):
    root = tmp_path / "source"
    first = make_scene(root / "a" / "duplicate.jpg", 1)
    second = make_scene(root / "b" / "duplicate.jpg", 2)
    before = {first: file_hash(first), second: file_hash(second)}
    database = tmp_path / "index.sqlite3"

    result = scan(root, database, limit=20)
    output = tmp_path / "selected"
    exported = export_selected(database, output)

    assert result["selected"] == 2
    assert exported["copied"] == 2
    assert len(list(output.glob("*.jpg"))) == 2
    assert len({path.name.casefold() for path in output.glob("*.jpg")}) == 2
    assert {first: file_hash(first), second: file_hash(second)} == before

    # Second export is idempotent and does not overwrite or duplicate copies.
    repeated = export_selected(database, output)
    assert repeated["copied"] == 0
    assert repeated["skipped_same"] == 2
    assert len(list(output.glob("*.jpg"))) == 2


def test_export_refuses_source_and_preserves_unrelated_existing_file(tmp_path):
    root = tmp_path / "source"
    source = make_scene(root / "photo.jpg", 2)
    database = tmp_path / "index.sqlite3"
    scan(root, database)

    try:
        export_selected(database, root)
    except ValueError as exc:
        assert "отдельно" in str(exc)
    else:
        raise AssertionError("export into source tree must be rejected")

    output = tmp_path / "selected"
    output.mkdir()
    unrelated = output / "photo.jpg"
    unrelated.write_bytes(b"user file - must remain untouched")
    unrelated_hash = file_hash(unrelated)

    export_selected(database, output)

    assert file_hash(unrelated) == unrelated_hash
    assert file_hash(source) != unrelated_hash
    assert len(list(output.iterdir())) == 2
