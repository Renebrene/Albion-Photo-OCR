"""
Подсветка панелей по текущему поиску (владелец, 29.10.2026).

`search_matches` отвечает на вопрос «где встречается запрос»: имена
(клиент, бренд, тег) и адресные слепки. Сами панели при этом не фильтруются —
грид и подсветка считаются по одному условию (`_photo_where`).
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest


class _Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.queries: list[tuple[str, object]] = []

    def execute(self, sql, params=None):
        self.queries.append((" ".join(sql.split()), params))

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _patch(monkeypatch, cursor):
    @contextmanager
    def fake():
        yield type("Conn", (), {"cursor": lambda _self: cursor})()

    from app.api import repository

    monkeypatch.setattr(repository, "get_connection", fake)
    return cursor


def test_empty_query_does_not_touch_the_database(monkeypatch):
    from app.api import repository

    @contextmanager
    def boom():
        raise AssertionError("query without a term must not hit the database")
        yield  # pragma: no cover

    monkeypatch.setattr(repository, "get_connection", boom)

    assert repository.search_matches(query="   ") == {"names": [], "addresses": []}


def test_returns_names_and_addresses(monkeypatch):
    from app.api import repository

    cursor = _patch(
        monkeypatch,
        _Cursor(rows=[("name", "Байков"), ("address", "56_v33")]),
    )

    result = repository.search_matches(query="Байков")

    assert result == {"names": ["Байков"], "addresses": ["56_v33"]}

    sql, _params = cursor.queries[0]
    # Имена собираются из клиента, бренда и тегов QWEN; алиасы приводятся к
    # каноническому имени, как в панели.
    assert "jsonb_array_elements_text" in sql
    assert "client_aliases" in sql
    assert "FROM matched" in sql


def test_names_are_deduplicated_case_insensitively(monkeypatch):
    from app.api import repository

    _patch(
        monkeypatch,
        _Cursor(rows=[("name", "Байков"), ("name", "байков"), ("name", "СК10")]),
    )

    result = repository.search_matches(query="Байков")

    assert result["names"] == ["Байков", "СК10"]


def test_period_is_passed_to_the_search_predicate(monkeypatch):
    from app.api import repository

    cursor = _patch(monkeypatch, _Cursor(rows=[]))

    repository.search_matches(
        query="Байков", date_from="2026-10-01", date_to="2026-10-29"
    )

    sql, params = cursor.queries[0]
    assert "t.created_at >= %s::date" in sql
    assert "t.created_at < (%s::date + interval '1 day')" in sql
    # Порядок плейсхолдеров — по тексту: сначала условия поиска, затем даты.
    assert params[-2:] == ["2026-10-01", "2026-10-29"]


def test_capture_date_mode_filters_by_taken_at(monkeypatch):
    from app.api import repository

    cursor = _patch(monkeypatch, _Cursor(rows=[]))

    repository.search_matches(
        query="Байков", date_from="2026-10-01", date_mode="capture"
    )

    sql, _params = cursor.queries[0]
    assert "t.taken_at >= %s::date" in sql


def test_unknown_date_mode_is_rejected(monkeypatch):
    from app.api import repository

    with pytest.raises(ValueError):
        repository.search_matches(query="Байков", date_mode="bogus")
