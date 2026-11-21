"""
Подсказки строки поиска не предлагают запрещённые к выдаче слова.

Значения берутся из уже сохранённых карточек, и старая строка могла
сохраниться до появления фильтра. Даже тогда слово не должно всплывать в
строке поиска; «Торпедо» при этом остаётся подсказкой.
"""

from __future__ import annotations

from app.api import repository
from app.qwen import processor


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, sql, params=None):
        self._params = params

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Connection:
    def __init__(self, rows):
        self._cursor = _Cursor(rows)

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch(monkeypatch, rows, words):
    monkeypatch.setattr(repository, "get_connection", lambda: _Connection(rows))
    monkeypatch.setattr(processor, "forbidden_words", lambda: words)


def test_forbidden_values_are_not_suggested(monkeypatch):
    rows = [
        ("СистемаПедо", "brand", 1),
        ("бренд СистемаПедо", "tag", 1),
        ("Торпедо", "tag", 1),
        ("педагоги", "tag", 15),
    ]
    _patch(monkeypatch, rows, ["педо"])

    items = repository.suggest_terms("пед", limit=8)

    assert [item["value"] for item in items] == ["Торпедо", "педагоги"]


def test_without_the_setting_everything_is_suggested(monkeypatch):
    rows = [("СистемаПедо", "brand", 1), ("Торпедо", "tag", 1)]
    _patch(monkeypatch, rows, [])

    items = repository.suggest_terms("пед", limit=8)

    assert [item["value"] for item in items] == ["СистемаПедо", "Торпедо"]


def test_limit_still_holds_after_filtering(monkeypatch):
    rows = [
        ("СистемаПедо", "brand", 5),
        ("Педо", "tag", 4),
        ("Торпедо", "tag", 1),
        ("педагоги", "tag", 1),
    ]
    _patch(monkeypatch, rows, ["педо"])

    items = repository.suggest_terms("пед", limit=1)

    assert [item["value"] for item in items] == ["Торпедо"]
