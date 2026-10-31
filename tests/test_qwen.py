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
from app.qwen import processor
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
                "DELETE FROM public.photo_qwen_history WHERE photo_id = %s",
                (PROBE_PHOTO_ID,),
            )
            cur.execute(
                "DELETE FROM public.photo_qwen WHERE photo_id = %s",
                (PROBE_PHOTO_ID,),
            )
            cur.execute(
                "DELETE FROM public.photos WHERE photo_id = %s",
                (PROBE_PHOTO_ID,),
            )


def test_token_usage_reads_the_provider_counters():
    """Облако отдаёт usage; локальная Ollama — нет, там остаются None."""

    assert qwen_db.token_usage(
        {"usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}}
    ) == (10, 4, 14)
    assert qwen_db.token_usage({"usage": {"total_tokens": "7"}}) == (None, None, 7)
    assert qwen_db.token_usage({"choices": []}) == (None, None, None)
    assert qwen_db.token_usage(None) == (None, None, None)


def _history_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with qwen_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.photo_qwen_history')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_history = pytest.mark.skipif(
    not _history_available(),
    reason="photo_qwen_history not available (INGEST_DB_* / schema 036)",
)


@requires_db
@requires_history
def test_overwrite_keeps_the_previous_result_in_history():
    """
    Полная перезапись — да, но прежний результат остаётся.

    Владелец: «полная перезапись + история версий», чтобы смена модели не
    стирала то, что было, и результаты можно было сравнить.
    """

    photo_id = _make_probe_photo()

    try:
        qwen_db.save_success(
            photo_id,
            fields={"description": "первое описание", "client": "Яндекс"},
            raw={"usage": {"prompt_tokens": 10, "completion_tokens": 4,
                           "total_tokens": 14}},
            model="model-a",
            time_sec=1.0,
        )

        first = qwen_db.get(photo_id)
        assert first["description"] == "первое описание"
        assert first["total_tokens"] == 14
        assert qwen_db.list_history(photo_id) == []

        qwen_db.save_success(
            photo_id,
            fields={"description": "второе описание"},
            raw={"usage": {"prompt_tokens": 20, "completion_tokens": 6,
                           "total_tokens": 26}},
            model="model-b",
            time_sec=2.0,
        )

        current = qwen_db.get(photo_id)
        assert current["description"] == "второе описание"
        assert current["qwen_model"] == "model-b"
        assert current["total_tokens"] == 26

        history = qwen_db.list_history(photo_id)
        assert len(history) == 1
        assert history[0]["description"] == "первое описание"
        assert history[0]["qwen_model"] == "model-a"
        assert history[0]["replaced_by_model"] == "model-b"
    finally:
        _cleanup_probe_photo()


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

def test_worker_passes_a_one_off_provider_override(monkeypatch):
    """Кнопка «Пересканировать» просит конкретного провайдера одним заданием."""

    from app.jobs import worker

    seen = {}

    def fake_run_photo(photo_id, *, provider=None, model=None):
        seen.update({"photo_id": photo_id, "provider": provider, "model": model})
        return {"photo_id": photo_id}

    monkeypatch.setattr(processor, "run_photo", fake_run_photo)

    worker._execute(
        {
            "id": 1,
            "job_type": "QWEN_PHOTO",
            "payload": {
                "photo_id": PROBE_PHOTO_ID,
                "source": "manual",
                "provider": "openai",
                "model": "ling-3.0-flash-vl",
            },
        }
    )

    assert seen == {
        "photo_id": PROBE_PHOTO_ID,
        "provider": "openai",
        "model": "ling-3.0-flash-vl",
    }


def test_worker_does_not_enqueue_global_refine_for_scoped_qwen(monkeypatch):
    from app.jobs import worker

    monkeypatch.setattr(processor, "run_photo", lambda *a, **k: {})
    monkeypatch.setattr(worker, "_maybe_enqueue_refine", lambda: pytest.fail("global REFINE must be skipped"))

    worker._execute({
        "id": 3,
        "job_type": "QWEN_PHOTO",
        "payload": {"photo_id": PROBE_PHOTO_ID, "skip_refine": True},
    })


def test_worker_preserves_auto_refine_for_unscoped_qwen(monkeypatch):
    from app.jobs import worker

    called = []
    monkeypatch.setattr(processor, "run_photo", lambda *a, **k: {})
    monkeypatch.setattr(worker, "_maybe_enqueue_refine", lambda: called.append(True))

    worker._execute({
        "id": 4,
        "job_type": "QWEN_PHOTO",
        "payload": {"photo_id": PROBE_PHOTO_ID},
    })
    assert called == [True]


def test_worker_keeps_the_current_settings_without_an_override(monkeypatch):
    from app.jobs import worker

    seen = {}

    def fake_run_photo(photo_id, *, provider=None, model=None):
        seen.update({"provider": provider, "model": model})
        return {}

    monkeypatch.setattr(processor, "run_photo", fake_run_photo)

    worker._execute(
        {
            "id": 2,
            "job_type": "QWEN_PHOTO",
            "payload": {"photo_id": PROBE_PHOTO_ID},
        }
    )

    assert seen == {"provider": None, "model": None}


def _qwen_base_settings():
    return {
        "provider": "ollama",
        "model": "test-model",
        "crop": {"mode": "off", "ratio": 1.0},
    }


def test_run_photo_analyses_billboard_crop_when_present(monkeypatch, tmp_path):
    """Описание берётся с кропа щита, бренд/клиент остаются в промпте."""

    from PIL import Image
    from app.billboard import pipeline as billboard_pipeline

    crop = tmp_path / "crop_01.jpg"
    Image.new("RGB", (320, 180), (5, 6, 7)).save(crop)

    monkeypatch.setattr(processor.db, "get_photo_source", lambda pid: "/tmp/source.jpg")
    monkeypatch.setattr(processor.db, "mark_running", lambda pid: None)
    saved = {}
    monkeypatch.setattr(
        processor.db, "save_success",
        lambda pid, **kw: saved.update(kw),
    )
    monkeypatch.setattr(processor, "resolve_settings", _qwen_base_settings)
    monkeypatch.setattr(
        billboard_pipeline, "ensure_crops",
        lambda pid: [str(crop)],
    )

    discarded = []
    monkeypatch.setattr(
        billboard_pipeline, "discard_crops",
        lambda paths: discarded.extend(str(path) for path in paths),
    )

    seen = {}

    def fake_analyze(path, config=None):
        seen.update({"path": path, "config": config})
        return ({"brand": "X", "client": "Y"}, {}, 1.0)

    monkeypatch.setattr(processor, "analyze_image", fake_analyze)

    processor.run_photo("PH_" + "ab" * 12)

    assert seen["path"] == str(crop)
    assert seen["config"]["crop"] == {"mode": "off", "ratio": 1.0}
    assert seen["config"]["max_image_side"] > 1280
    assert "бренд" in seen["config"]["prompt"].lower()
    assert "client" in seen["config"]["prompt"]
    fields = saved["fields"]
    assert fields["brand"] == "X"
    assert fields["client"] == "Y"
    # Новый агрегат также фиксирует объединённые описания/теги и категорию.
    assert fields["tags"] == []
    assert fields["description"] is None
    # Кроп — временный: после успешного сохранения он удаляется.
    # Кропы больше не удаляются после успешного описания: по ним идёт
    # прогон серий (docs/series_merge.md), удаление — по возрасту.
    assert discarded == []


def test_run_photo_merges_two_billboard_crops(monkeypatch, tmp_path):
    """Два щита на фото: два кропа, один результат, второй клиент — в тегах."""

    from app.billboard import pipeline as billboard_pipeline

    first = tmp_path / "crop_01.jpg"
    second = tmp_path / "crop_02.jpg"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    monkeypatch.setattr(processor.db, "get_photo_source", lambda pid: "/tmp/source.jpg")
    monkeypatch.setattr(processor.db, "mark_running", lambda pid: None)
    saved = {}
    monkeypatch.setattr(
        processor.db, "save_success",
        lambda pid, **kw: saved.update(kw),
    )
    monkeypatch.setattr(processor, "resolve_settings", _qwen_base_settings)
    monkeypatch.setattr(
        billboard_pipeline, "ensure_crops",
        lambda pid: [str(first), str(second)],
    )

    discarded = []
    monkeypatch.setattr(
        billboard_pipeline, "discard_crops",
        lambda paths: discarded.extend(str(path) for path in paths),
    )

    calls = []

    def fake_analyze(path, config=None):
        calls.append(str(path))

        if str(path) == str(first):
            return (
                {
                    "description": "Щит LADA",
                    "client": "LADA",
                    "brand": "LADA",
                    "category": "авто",
                    "tags": ["авто", "акция"],
                },
                {"usage": {"prompt_tokens": 100, "completion_tokens": 20,
                           "total_tokens": 120}},
                2.0,
            )

        return (
            {
                "description": "Щит ВМЕСТЕ",
                "client": "ВМЕСТЕ",
                "brand": "ВМЕСТЕ",
                "category": "соцреклама",
                "tags": ["соцреклама", "акция"],
            },
            {"usage": {"prompt_tokens": 90, "completion_tokens": 10,
                       "total_tokens": 100}},
            3.0,
        )

    monkeypatch.setattr(processor, "analyze_image", fake_analyze)

    result = processor.run_photo("PH_" + "ef" * 12)

    assert calls == [str(first), str(second)]
    assert result["billboards"] == 2
    assert result["time_sec"] == 5.0

    fields = saved["fields"]
    # Скалярные поля — от главного (самого большого) щита: точные фильтры
    # клиента/бренда продолжают работать.
    assert fields["client"] == "LADA"
    assert fields["brand"] == "LADA"
    assert fields["category"] == "авто"
    # Второй рекламодатель не теряется — он в тегах и описании.
    assert fields["tags"] == ["авто", "акция", "соцреклама", "ВМЕСТЕ"]
    assert "Щит LADA" in fields["description"]
    assert "Щит ВМЕСТЕ" in fields["description"]

    # Токены двух вызовов суммируются.
    assert saved["raw"]["usage"]["total_tokens"] == 220
    # Оба кропа остаются на диске для прогона серий.
    assert discarded == []


def test_run_photo_persists_each_crop_result_on_its_region(monkeypatch, tmp_path):
    """Результат каждого кропа пишется в свою строку photo_regions."""

    from app.billboard import database as billboard_db
    from app.billboard import pipeline as billboard_pipeline

    first = tmp_path / "crop_01.jpg"
    second = tmp_path / "crop_02.jpg"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    monkeypatch.setattr(processor.db, "get_photo_source", lambda pid: "/tmp/source.jpg")
    monkeypatch.setattr(processor.db, "mark_running", lambda pid: None)
    monkeypatch.setattr(processor.db, "save_success", lambda pid, **kw: None)
    monkeypatch.setattr(processor, "resolve_settings", _qwen_base_settings)
    monkeypatch.setattr(
        billboard_pipeline, "ensure_crops",
        lambda pid: [str(first), str(second)],
    )
    monkeypatch.setattr(billboard_pipeline, "discard_crops", lambda paths: None)
    monkeypatch.setattr(
        billboard_db, "get_billboard_regions",
        lambda pid: [
            {"region_id": 101, "crop_index": 0},
            {"region_id": 102, "crop_index": 1},
        ],
    )

    running: list[int] = []
    saved: list[tuple[int, dict]] = []
    monkeypatch.setattr(billboard_db, "mark_qwen_running", running.append)
    monkeypatch.setattr(
        billboard_db, "save_qwen_success",
        lambda region_id, **kw: saved.append((region_id, kw["fields"])),
    )

    def fake_analyze(path, config=None):
        if str(path) == str(first):
            return ({"description": "Первый", "client": "A", "brand": "A", "tags": []}, {}, 1.0)
        return ({"description": "Второй", "client": "B", "brand": "B", "tags": []}, {}, 1.0)

    monkeypatch.setattr(processor, "analyze_image", fake_analyze)

    processor.run_photo("PH_" + "12" * 12)

    assert running == [101, 102]
    assert [region_id for region_id, _fields in saved] == [101, 102]
    assert saved[0][1]["brand"] == "A"
    assert saved[1][1]["brand"] == "B"


def test_run_photo_keeps_primary_result_when_second_crop_fails(monkeypatch, tmp_path):
    from app.billboard import pipeline as billboard_pipeline

    first = tmp_path / "crop_01.jpg"
    second = tmp_path / "crop_02.jpg"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    monkeypatch.setattr(processor.db, "get_photo_source", lambda pid: "/tmp/source.jpg")
    monkeypatch.setattr(processor.db, "mark_running", lambda pid: None)
    saved = {}
    monkeypatch.setattr(
        processor.db, "save_success",
        lambda pid, **kw: saved.update(kw),
    )
    monkeypatch.setattr(processor, "resolve_settings", _qwen_base_settings)
    monkeypatch.setattr(
        billboard_pipeline, "ensure_crops",
        lambda pid: [str(first), str(second)],
    )
    monkeypatch.setattr(billboard_pipeline, "discard_crops", lambda paths: None)

    def fake_analyze(path, config=None):
        if str(path) == str(first):
            return ({"description": "Первый", "client": "A", "tags": []}, {}, 1.0)

        raise RuntimeError("second crop failed")

    monkeypatch.setattr(processor, "analyze_image", fake_analyze)

    result = processor.run_photo("PH_" + "1b" * 12)

    assert saved["fields"]["client"] == "A"
    assert saved["fields"]["description"] == "Первый"
    assert result["crop_errors"] == ["second crop failed"]


def test_run_photo_falls_back_to_full_frame(monkeypatch):
    from app.billboard import pipeline as billboard_pipeline

    monkeypatch.setattr(processor.db, "get_photo_source", lambda pid: "/tmp/source.jpg")
    monkeypatch.setattr(processor.db, "mark_running", lambda pid: None)
    monkeypatch.setattr(processor.db, "save_success", lambda pid, **kw: None)
    monkeypatch.setattr(processor, "resolve_settings", _qwen_base_settings)
    monkeypatch.setattr(billboard_pipeline, "ensure_crops", lambda pid: [])

    seen = {}

    def fake_analyze(path, config=None):
        seen.update({"path": path, "config": config})
        return ({"description": "scene"}, {}, 1.0)

    monkeypatch.setattr(processor, "analyze_image", fake_analyze)

    processor.run_photo("PH_" + "cd" * 12)

    assert seen["path"] == "/tmp/source.jpg"
    assert "prompt" not in seen["config"]
