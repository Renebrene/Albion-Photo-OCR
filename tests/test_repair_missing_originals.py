"""
Разбор записей фото без оригинала (scripts/repair_missing_originals.py).

База не нужна: проверяется решение «какие строки перевесить». Ошибка здесь
означала бы либо потерянные оригиналы, либо тихую подмену файла.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import repair_missing_originals as repair  # noqa: E402


def _row(photo_id, path, filename="one.jpg"):
    return {
        "photo_id": photo_id,
        "source_path": str(path),
        "filename": filename,
        "identity_hash": None,
        "sha256": None,
    }


def test_rows_with_a_file_are_left_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(repair, "ORIGINALS_ROOTS", [tmp_path])
    present = tmp_path / "kept.jpg"
    present.write_bytes(b"x")

    result = repair.plan([_row("PH_kept", present)], {"PH_kept": [("kept.jpg", str(present))]})

    assert result["already_ok"] == 1
    assert result["repairable"] == []


def test_missing_row_is_repointed_to_the_found_copy(tmp_path, monkeypatch):
    monkeypatch.setattr(repair, "ORIGINALS_ROOTS", [tmp_path])
    copy = tmp_path / "ноябрь" / "IMG_1.JPG"
    copy.parent.mkdir()
    copy.write_bytes(b"x")

    result = repair.plan(
        [_row("PH_one", tmp_path / "old" / "IMG_1.JPG", "IMG_1.JPG")],
        {"PH_one": [("IMG_1.JPG", str(copy))]},
    )

    assert result["broken"] == 1
    assert result["repairable"] == [
        {
            "photo_id": "PH_one",
            "old_path": str(tmp_path / "old" / "IMG_1.JPG"),
            "old_filename": "IMG_1.JPG",
            "new_path": str(copy),
            "new_filename": "IMG_1.JPG",
        }
    ]


def test_renamed_copy_takes_its_new_name(tmp_path, monkeypatch):
    """Копия может называться иначе: имя записи меняется вместе с путём."""

    monkeypatch.setattr(repair, "ORIGINALS_ROOTS", [tmp_path])
    copy = tmp_path / "Вавилова А (2).JPG"
    copy.write_bytes(b"x")

    result = repair.plan(
        [_row("PH_two", tmp_path / "old" / "IMG_2.JPG", "IMG_2.JPG")],
        {"PH_two": [("Вавилова А (2).JPG", str(copy))]},
    )

    assert result["repairable"][0]["new_filename"] == "Вавилова А (2).JPG"


def test_two_copies_are_reported_not_chosen(tmp_path, monkeypatch):
    monkeypatch.setattr(repair, "ORIGINALS_ROOTS", [tmp_path])
    first = tmp_path / "a" / "one.jpg"
    second = tmp_path / "b" / "two.jpg"
    for item in (first, second):
        item.parent.mkdir()
        item.write_bytes(b"x")

    result = repair.plan(
        [_row("PH_dup", tmp_path / "old" / "one.jpg")],
        {"PH_dup": [("one.jpg", str(first)), ("two.jpg", str(second))]},
    )

    assert result["repairable"] == []
    assert len(result["ambiguous"]) == 1


def test_copy_outside_allowed_roots_is_skipped(tmp_path, monkeypatch):
    """API не отдаст оригинал вне корней: такой путь чинить нельзя."""

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside" / "one.jpg"
    outside.parent.mkdir()
    outside.write_bytes(b"x")
    monkeypatch.setattr(repair, "ORIGINALS_ROOTS", [allowed])

    result = repair.plan(
        [_row("PH_out", allowed / "old" / "one.jpg")],
        {"PH_out": [("one.jpg", str(outside))]},
    )

    assert result["repairable"] == []
    assert len(result["outside_roots"]) == 1


def test_no_copy_means_nothing_to_do(tmp_path, monkeypatch):
    monkeypatch.setattr(repair, "ORIGINALS_ROOTS", [tmp_path])

    result = repair.plan([_row("PH_gone", tmp_path / "gone.jpg")], {})

    assert result["broken"] == 1
    assert result["repairable"] == []


def test_inside_allowed_roots_does_not_match_a_sibling_prefix(tmp_path, monkeypatch):
    allowed = tmp_path / "video"
    allowed.mkdir()
    monkeypatch.setattr(repair, "ORIGINALS_ROOTS", [allowed])

    assert repair._inside_allowed_roots(str(allowed / "one.jpg")) is True
    assert repair._inside_allowed_roots(str(tmp_path / "video-old" / "one.jpg")) is False
    assert repair._inside_allowed_roots(os.fspath(allowed)) is True
