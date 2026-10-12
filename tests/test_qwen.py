"""
Tests for the QWEN metadata process (app.qwen).

Pure parsing runs everywhere; database round-trips need PostgreSQL. A live
model test runs only when QWEN_LIVE_TEST=1 (it calls Ollama).
"""

from __future__ import annotations

import os

import pytest

from app.qwen import database as qwen_db
from app.qwen.processor import parse_result


def test_parse_result_from_json_string():
    content = (
        '{"description":"Двор","address":"ул. Ленина 1",'
        '"client":null,"brand":null,"category":"Дом",'
        '"tags":["дом","двор"]}'
    )

    result = parse_result(content)

    assert result["description"] == "Двор"
    assert result["address"] == "ул. Ленина 1"
    assert result["client"] is None
    assert result["brand"] is None
    assert result["category"] == "Дом"
    assert result["tags"] == ["дом", "двор"]


def test_parse_result_tags_from_string():
    result = parse_result('{"tags":"a, b , c"}')
    assert result["tags"] == ["a", "b", "c"]


def test_parse_result_missing_fields_become_none():
    result = parse_result('{"description":"x"}')
    assert result["description"] == "x"
    assert result["address"] is None
    assert result["client"] is None
    assert result["tags"] == []


def test_parse_result_blank_string_becomes_none():
    result = parse_result('{"description":"   "}')
    assert result["description"] is None


def test_parse_result_invalid_json_raises():
    with pytest.raises(ValueError):
        parse_result("not json at all")


def test_parse_result_strips_think_block():
    content = '<think>рассуждение</think>{"description":"Дом","address":null}'

    result = parse_result(content)

    assert result["description"] == "Дом"
    assert result["address"] is None


def test_parse_result_extracts_json_from_prose():
    content = 'Вот результат: {"description":"Двор"} — всё.'

    result = parse_result(content)

    assert result["description"] == "Двор"


# ---------------------------------------------------------------------------
# Database round-trip (requires PostgreSQL with schema 007)
# ---------------------------------------------------------------------------


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with qwen_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.photo_qwen')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="photo_qwen not available (INGEST_DB_* / schema 007)",
)


def _first_photo_id() -> str | None:
    with qwen_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("select photo_id from public.photos order by photo_id limit 1")
            row = cur.fetchone()
    return row[0] if row else None


@requires_db
def test_qwen_upsert_roundtrip():
    photo_id = _first_photo_id()

    if photo_id is None:
        pytest.skip("no photos registered")

    try:
        qwen_db.mark_running(photo_id)
        assert qwen_db.get(photo_id)["status"] == "RUNNING"

        qwen_db.save_success(
            photo_id,
            fields={
                "description": "test scene",
                "address": "ул. Тестовая 1",
                "client": "ООО Тест",
                "brand": None,
                "category": "дом",
                "tags": ["дом", "двор"],
            },
            raw={"message": {"content": "{}"}},
            model="test-model",
            time_sec=0.5,
        )

        row = qwen_db.get(photo_id)
        assert row["status"] == "DONE"
        assert row["address"] == "ул. Тестовая 1"
        assert row["client"] == "ООО Тест"
        assert row["tags"] == ["дом", "двор"]
        assert row["qwen_model"] == "test-model"

        qwen_db.save_failure(photo_id, "boom")
        assert qwen_db.get(photo_id)["status"] == "FAILED"
    finally:
        with qwen_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.photo_qwen WHERE photo_id = %s",
                    (photo_id,),
                )


@pytest.mark.skipif(
    not os.getenv("QWEN_LIVE_TEST"),
    reason="set QWEN_LIVE_TEST=1 to run the live Ollama smoke test",
)
@requires_db
def test_qwen_live_smoke():
    from app.qwen.processor import run_photo

    photo_id = _first_photo_id()

    if photo_id is None:
        pytest.skip("no photos registered")

    try:
        result = run_photo(photo_id)
        assert result["photo_id"] == photo_id
        assert qwen_db.get(photo_id)["status"] == "DONE"
    finally:
        with qwen_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.photo_qwen WHERE photo_id = %s",
                    (photo_id,),
                )
