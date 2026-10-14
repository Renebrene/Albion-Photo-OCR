"""
Tests for the QWEN metadata process (app.qwen).

Pure parsing runs everywhere; database round-trips need PostgreSQL. A live
model test runs only when QWEN_LIVE_TEST=1 (it calls Ollama).
"""

from __future__ import annotations

import hashlib
import os

import pytest

from app.qwen import database as qwen_db
from app.qwen.processor import answer_truncated, parse_result


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
# «Thinking» models that never reach the answer (2026-10-14: qwen3-vl:8b)
# ---------------------------------------------------------------------------


def test_truncated_answer_is_explained():
    """
    The whole budget went into reasoning: the error must name the model and
    say what to do, not just «no JSON object».
    """

    payload = {
        "done_reason": "length",
        "message": {"content": "", "thinking": "<think>Думаю про вывеску..."},
    }

    error = answer_truncated(payload, "", "qwen3-vl:8b", 512)

    assert error is not None
    assert "qwen3-vl:8b" in str(error)
    assert "instruct" in str(error)
    assert error.raw.startswith("<think>")


def test_a_finished_answer_is_not_blamed_on_truncation():
    # A real answer, even an unusable one, is the parser's business.
    assert answer_truncated({"done_reason": "stop"}, "текст", "m", 512) is None

    # Truncated but with content: the parser reports the missing JSON.
    assert answer_truncated({"done_reason": "length"}, "текст", "m", 512) is None


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


# A throwaway photo owned by the tests. Never use a real corpus photo here:
# these tests write and then DELETE the photo_qwen row, which would destroy
# the real metadata of an existing photo.
PROBE_PHOTO_ID = "PH_" + "8" * 24


def _make_probe_photo(source_path: str | None = None) -> str:
    path = source_path or f"/tmp/{PROBE_PHOTO_ID}.jpg"

    with qwen_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photos (
                    photo_id, source_path, filename, sha256,
                    container_format, frame_count, width, height
                )
                VALUES (%s, %s, %s, %s, 'JPEG', 1, 10, 10)
                ON CONFLICT (photo_id) DO UPDATE SET
                    source_path = EXCLUDED.source_path,
                    filename = EXCLUDED.filename,
                    sha256 = EXCLUDED.sha256
                """,
                (
                    PROBE_PHOTO_ID,
                    path,
                    os.path.basename(path),
                    hashlib.sha256(PROBE_PHOTO_ID.encode()).hexdigest(),
                ),
            )

    return PROBE_PHOTO_ID


def _cleanup_probe_photo() -> None:
    with qwen_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.photo_qwen WHERE photo_id = %s",
                (PROBE_PHOTO_ID,),
            )
            cur.execute(
                "DELETE FROM public.photos WHERE photo_id = %s",
                (PROBE_PHOTO_ID,),
            )


@requires_db
def test_qwen_upsert_roundtrip():
    photo_id = _make_probe_photo()

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
        _cleanup_probe_photo()


@pytest.mark.skipif(
    not os.getenv("QWEN_LIVE_TEST"),
    reason="set QWEN_LIVE_TEST=1 to run the live Ollama smoke test",
)
@requires_db
def test_qwen_live_smoke(tmp_path):
    from PIL import Image

    from app.qwen.processor import run_photo

    # Use a throwaway photo with a real (temporary) image file.
    image_path = tmp_path / "probe.jpg"
    Image.new("RGB", (32, 24), color=(30, 90, 30)).save(image_path, format="JPEG")

    photo_id = _make_probe_photo(str(image_path))

    try:
        result = run_photo(photo_id)
        assert result["photo_id"] == photo_id
        assert qwen_db.get(photo_id)["status"] == "DONE"
    finally:
        _cleanup_probe_photo()
