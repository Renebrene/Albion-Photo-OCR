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
