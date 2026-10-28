"""
Разбор записей видео без файла (scripts/purge_missing_videos.py).

База не нужна: проверяется решение «файла нет», по которому скрипт выбирает
строки для удаления. Ошибка здесь означала бы удаление живых записей.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import purge_missing_videos as purge  # noqa: E402


def _roots(monkeypatch, roots):
    monkeypatch.setattr(purge, "_allowed_roots", lambda: [str(root) for root in roots])


def test_existing_file_is_kept(tmp_path, monkeypatch):
    _roots(monkeypatch, [tmp_path])
    present = tmp_path / "clip.mp4"
    present.write_bytes(b"x")

    assert purge._has_file(str(present)) is True


def test_missing_file_is_reported(tmp_path, monkeypatch):
    _roots(monkeypatch, [tmp_path])

    assert purge._has_file(str(tmp_path / "gone.mp4")) is False


def test_empty_path_is_missing(monkeypatch, tmp_path):
    _roots(monkeypatch, [tmp_path])

    assert purge._has_file(None) is False
    assert purge._has_file("") is False


def test_path_outside_the_allowed_roots_is_missing(tmp_path, monkeypatch):
    """Файл может существовать, но вне корней: для записи он недоступен."""

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"x")
    _roots(monkeypatch, [allowed])

    assert purge._has_file(str(outside)) is False


def test_a_sibling_name_does_not_count_as_inside_the_root(tmp_path, monkeypatch):
    """`/data/video` и `/data/video-old` — разные корни, не префикс строки."""

    allowed = tmp_path / "video"
    allowed.mkdir()
    sibling = tmp_path / "video-old"
    sibling.mkdir()
    inside_sibling = sibling / "clip.mp4"
    inside_sibling.write_bytes(b"x")
    _roots(monkeypatch, [allowed])

    assert purge._has_file(str(inside_sibling)) is False


def test_a_root_itself_is_never_kept(tmp_path, monkeypatch):
    """Строка с путём самого корня файлом не считается."""

    _roots(monkeypatch, [tmp_path])

    assert purge._has_file(str(tmp_path)) is False


def test_json_ready_converts_dates():
    from datetime import datetime, timezone

    moment = datetime(2026, 10, 28, 10, 0, tzinfo=timezone.utc)

    assert purge._json_ready({"created_at": moment, "video_id": "VI_1"}) == {
        "created_at": moment.isoformat(),
        "video_id": "VI_1",
    }
