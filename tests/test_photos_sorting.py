"""Сортировка выдачи: выражение ORDER BY, составной курсор, WHERE-условие."""

from __future__ import annotations

import base64
import json
from datetime import datetime

from app.api import repository as repo


def test_known_sort_keys_have_expressions():
    assert repo.sort_expression("filename") == "t.filename"
    assert repo.sort_expression("client") == "COALESCE(t.client, '')"
    assert repo.sort_expression("date").startswith("COALESCE(t.taken_at")
    assert repo.sort_expression("address").startswith("COALESCE(NULLIF(btrim(")


def test_unknown_sort_key_falls_back_to_photo_id():
    assert repo.sort_expression("nonsense") == "t.photo_id"
    assert "photo_id" in repo.SORT_KEYS


def test_similarity_sort_key_is_temporary_and_address_aware():
    """Ключ нужен API, но реальное выражение строится из выбранного адреса."""

    assert "similarity" in repo.SORT_KEYS
    assert repo.sort_expression("similarity") == "t.confidence"

    address_ids, fingerprint_ids = repo._selected_similarity_scope(
        ["addr:51", "addr:review", "92_v33", "bad"]
    )

    assert address_ids == [51]
    assert fingerprint_ids == ["92_v33", "bad"]


def test_similarity_sql_uses_latest_verdict_and_selected_address():
    sql, params = repo._similarity_sql("base", [51], ["92_v33"])

    assert "max(c.score)" in sql
    assert "h.hybrid_run_id = (" in sql
    assert "af.address_id = ANY(%s)" in sql
    assert "LOWER(af.fingerprint_id) = ANY(%s)" in sql
    assert params == [[51], ["92_v33"]]


def test_similarity_cursor_is_offset_based():
    """У сходства нет значения в строке, поэтому курсор — смещение."""

    where, params = repo._photo_where(cursor="sim:50", sort="similarity")

    assert "photo_id > %s" not in where
    assert params == []


def test_similarity_params_come_before_inner_date_params(monkeypatch):
    """
    Регрессия 500: similarity-выражение стоит в OUTER SELECT, поэтому его
    placeholder идёт первым. При датном диапазоне сдвиг параметров давал
    «cannot cast type smallint[] to date».
    """

    seen: dict = {}

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, sql, params):
            seen["sql"] = sql
            seen["params"] = list(params)

        def fetchall(self):
            return []

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(repo, "get_connection", lambda: FakeConnection())

    items, cursor = repo.list_photos(
        limit=10,
        sort="similarity",
        order="desc",
        addresses=["addr:144"],
        date_from="2026-10-01",
        date_to="2026-10-31",
        date_mode="capture",
    )

    assert items == []
    assert cursor is None
    # outer similarity -> inner address (2) -> dates (2) -> limit/offset
    assert seen["params"][0] == [144]
    assert seen["params"][3:5] == ["2026-10-01", "2026-10-31"]
    assert seen["params"][-2:] == [11, 0]


def test_cursor_roundtrip_keeps_value_and_id():
    photo_id = "PH_" + "a" * 24
    cursor = repo.encode_cursor("Мира 1", photo_id)

    assert repo.decode_cursor(cursor) == ("Мира 1", photo_id)


def test_cursor_roundtrip_for_datetime():
    cursor = repo.encode_cursor(datetime(2026, 10, 24, 12, 0, 0), "PH_x")
    value, photo_id = repo.decode_cursor(cursor)

    assert value == "2026-10-24 12:00:00.000000"
    assert photo_id == "PH_x"


def test_broken_cursor_is_ignored():
    assert repo.decode_cursor("не-base64") is None
    assert repo.decode_cursor(base64.urlsafe_b64encode(b'{"x": 1}').decode()) is None


def test_default_cursor_stays_photo_id():
    where, params = repo._photo_where(cursor="PH_b")

    assert "t.photo_id > %s" in where
    assert params[-1] == "PH_b"


def test_descending_photo_id_cursor_flips_the_comparison():
    where, _params = repo._photo_where(cursor="PH_b", order="desc")

    assert "t.photo_id < %s" in where


def test_key_sorting_uses_pair_comparison():
    cursor = repo.encode_cursor("Мира 1", "PH_a")
    where, params = repo._photo_where(cursor=cursor, sort="address", order="asc")

    assert "((COALESCE(NULLIF(btrim(t.simple_address), ''), t.legal_address, t.address, ''))" in where
    assert "%s::text, %s::text" in where
    assert params[-2:] == ["Мира 1", "PH_a"]


def test_date_cursor_is_cast_to_timestamp():
    cursor = repo.encode_cursor(datetime(2026, 10, 24, 12, 0, 0), "PH_a")
    where, params = repo._photo_where(cursor=cursor, sort="date", order="desc")

    assert "%s::timestamp" in where
    assert params[-1] == "PH_a"


def test_sort_value_reads_the_visible_fields():
    class Row:
        photo_id = "PH_a"
        taken_at = None
        created_at = datetime(2026, 1, 2, 3, 4, 5)
        simple_address = None
        legal_address = "Мира 1"
        address = "78_v33"
        filename = "a.JPG"
        client = None

    assert repo._sort_value(Row(), "date") == datetime(2026, 1, 2, 3, 4, 5)
    assert repo._sort_value(Row(), "address") == "Мира 1"
    assert repo._sort_value(Row(), "filename") == "a.JPG"
    assert repo._sort_value(Row(), "client") == ""
