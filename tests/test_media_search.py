"""
Smart search by an uploaded photo (backlog item 2, first increment).

Storage, filters and the worker branch are pure logic; only the endpoints that
enqueue a job need PostgreSQL and schema/020 (they skip otherwise).
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api import media_search
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def _jpeg_bytes(size=(16, 12)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color=(10, 20, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.job_queue')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


def _media_job_type_available() -> bool:
    """True once schema/020 widened the job_type CHECK to MEDIA_SEARCH."""

    if not _db_available():
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_get_constraintdef(oid) "
                    "FROM pg_constraint WHERE conname = 'job_queue_job_type_check'"
                )
                row = cur.fetchone()
                return bool(row) and "MEDIA_SEARCH" in row[0]
    except Exception:
        return False


requires_media_job = pytest.mark.skipif(
    not _media_job_type_available(),
    reason="schema/020 (MEDIA_SEARCH job type) is not applied",
)


@pytest.fixture(autouse=True)
def query_dir(tmp_path, monkeypatch):
    """Keep every test's query files inside the pytest temp directory."""

    directory = tmp_path / "media_search"
    monkeypatch.setattr(media_search, "QUERY_DIR", directory)
    return directory


# ---- filename and storage safety ----


def test_sanitize_filename_accepts_images_and_strips_paths():
    assert media_search.sanitize_filename("banner.JPG") == "banner.JPG"
    assert media_search.sanitize_filename("shot.png") == "shot.png"
    # A client path is reduced to a basename and unsafe characters replaced.
    assert media_search.sanitize_filename("../../etc/pa ss.png") == "pa_ss.png"


@pytest.mark.parametrize("name", ["", None, "notes.txt", "archive.zip", "."])
def test_sanitize_filename_rejects_non_images(name):
    assert media_search.sanitize_filename(name) is None


def test_store_query_writes_a_complete_file(query_dir):
    path = media_search.store_query("query.jpg", io.BytesIO(_jpeg_bytes()))

    assert path.exists()
    assert path.parent == query_dir
    assert path.stat().st_size == len(_jpeg_bytes())
    assert path.suffix == ".jpg"


def test_store_query_rejects_an_empty_file(query_dir):
    with pytest.raises(ValueError):
        media_search.store_query("empty.jpg", io.BytesIO(b""))

    assert list(query_dir.iterdir()) == []


def test_store_query_enforces_the_size_limit(query_dir, monkeypatch):
    monkeypatch.setattr(media_search, "MAX_FILE_BYTES", 10)

    with pytest.raises(ValueError):
        media_search.store_query("big.jpg", io.BytesIO(b"x" * 64))

    # Nothing partial is left behind.
    assert list(query_dir.iterdir()) == []


def test_store_query_uses_one_name_per_upload(query_dir):
    first = media_search.store_query("same.jpg", io.BytesIO(b"a" * 4))
    second = media_search.store_query("same.jpg", io.BytesIO(b"b" * 4))

    assert first != second
    assert first.exists() and second.exists()


def test_verify_image_accepts_a_jpeg_and_rejects_text(query_dir):
    good = media_search.store_query("good.jpg", io.BytesIO(_jpeg_bytes()))
    bad = media_search.store_query("bad.jpg", io.BytesIO(b"not an image"))

    media_search.verify_image(good)

    with pytest.raises(ValueError):
        media_search.verify_image(bad)


def test_delete_query_is_idempotent(query_dir):
    path = media_search.store_query("gone.jpg", io.BytesIO(b"a" * 4))

    assert media_search.delete_query(path) is True
    assert media_search.delete_query(path) is False


def test_prune_stale_removes_only_old_files(query_dir, monkeypatch):
    old = media_search.store_query("old.jpg", io.BytesIO(b"a" * 4))
    fresh = media_search.store_query("fresh.jpg", io.BytesIO(b"b" * 4))

    stale_time = old.stat().st_mtime - media_search.MAX_AGE_SECONDS - 60
    os.utime(old, (stale_time, stale_time))

    assert media_search.prune_stale() == 1
    assert not old.exists()
    assert fresh.exists()


# ---- filters derived from the QWEN description ----


def test_description_filters_use_the_description_and_metadata():
    filters = media_search.description_filters(
        {
            "description": "рекламный щит у дороги",
            "brand": "KVAS",
            "category": "реклама",
            "client": "Волгский Дон",
            "tags": ["щит", "дорога"],
        }
    )

    assert filters == {
        "q": "рекламный щит у дороги",
        "client": "Волгский Дон",
        "brand": "KVAS",
        "category": "реклама",
        "address": None,
    }


def test_description_filters_fall_back_to_tags_and_blank_metadata():
    filters = media_search.description_filters(
        {"description": "  ", "tags": ["вывеска", "магазин"], "brand": None}
    )

    assert filters["q"] == "вывеска, магазин"
    assert filters["brand"] is None
    assert filters["client"] is None


def test_description_filters_without_any_text_are_empty():
    filters = media_search.description_filters({})

    assert filters["q"] is None
    assert all(value is None for value in filters.values())


def test_search_unions_terms_and_reports_truncation(monkeypatch):
    """The search asks the repository per term and de-duplicates the ids."""

    class Item:
        def __init__(self, photo_id: str):
            self.photo_id = photo_id

    calls: list[tuple] = []

    def fake_list_photos(*, limit, query):
        calls.append((limit, query))

        if query == "KVAS":
            return [Item("PH_a"), Item("PH_b")], "cursor"  # truncated

        return [Item("PH_b"), Item("PH_c")], None

    monkeypatch.setattr("app.api.repository.list_photos", fake_list_photos)

    result = media_search.search({"q": "щит", "brand": "KVAS"})

    # Terms are searched in order and the ids are de-duplicated (PH_b appears
    # in both term results).
    assert result["photo_ids"] == ["PH_b", "PH_c", "PH_a"]
    assert result["count"] == 3
    assert result["truncated"] is True
    assert calls == [
        (media_search.MAX_PER_TERM, "щит"),
        (media_search.MAX_PER_TERM, "KVAS"),
    ]


def test_search_without_terms_makes_no_query(monkeypatch):
    def explode(**_kwargs):
        raise AssertionError("no term should be searched")

    monkeypatch.setattr("app.api.repository.list_photos", explode)

    assert media_search.search({"q": None, "brand": None})["count"] == 0


def test_describe_falls_back_to_the_raw_answer(monkeypatch):
    """A model that answers with prose must not fail the search job."""

    from app.qwen.processor import QwenParseError

    def prose(*_args, **_kwargs):
        raise QwenParseError(
            "QWEN response has no JSON object",
            raw="<think>рассуждение</think> Городская улица, щит с врачом",
        )

    monkeypatch.setattr("app.qwen.processor.analyze_image", prose)

    described = media_search.describe("query.jpg")

    assert described["fallback"] is True
    assert described["fields"]["description"] == "Городская улица, щит с врачом"
    assert described["fields"]["brand"] is None


def test_describe_reraises_an_empty_answer(monkeypatch):
    from app.qwen.processor import QwenParseError

    def empty(*_args, **_kwargs):
        raise QwenParseError("QWEN response is empty", raw="   ")

    monkeypatch.setattr("app.qwen.processor.analyze_image", empty)

    with pytest.raises(QwenParseError):
        media_search.describe("query.jpg")


def test_describe_asks_the_model_for_a_longer_answer(monkeypatch):
    seen: dict = {}

    def capture(path, *, model=None, config=None):
        seen["config"] = config
        return ({"description": "щит"}, {}, 1.5)

    monkeypatch.setattr("app.qwen.processor.analyze_image", capture)

    described = media_search.describe("query.jpg")

    assert described["fallback"] is False
    assert described["seconds"] == 1.5
    assert seen["config"]["max_output_tokens"] == media_search.QUERY_MAX_OUTPUT_TOKENS


def test_run_reports_the_fallback_flag(monkeypatch):
    monkeypatch.setattr(
        media_search,
        "describe",
        lambda path: {
            "fields": {"description": "улица", "tags": []},
            "seconds": 0.0,
            "fallback": True,
        },
    )
    monkeypatch.setattr(
        "app.api.repository.list_photos",
        lambda **_kwargs: ([], None),
    )

    result = media_search.run("query.jpg")

    assert result["fallback"] is True
    assert result["filters"]["q"] == "улица"


def test_parse_result_keeps_the_raw_text():
    from app.qwen.processor import QwenParseError, parse_result

    with pytest.raises(QwenParseError) as raised:
        parse_result("просто текст без json")

    assert raised.value.raw == "просто текст без json"


# ---- worker branch ----


def test_media_search_job_describes_then_deletes_the_file(query_dir, monkeypatch):
    from app.jobs import worker

    path = media_search.store_query("q.jpg", io.BytesIO(_jpeg_bytes()))
    seen: list[str] = []

    def fake_run(argument):
        seen.append(str(argument))
        return {"photo_ids": ["PH_a"], "count": 1}

    monkeypatch.setattr("app.api.media_search.run", fake_run)

    result = worker._execute(
        {"job_type": "MEDIA_SEARCH", "payload": {"path": str(path)}}
    )

    assert result == {"photo_ids": ["PH_a"], "count": 1}
    assert seen == [str(path)]
    # Transient by design: the query image is gone after the job.
    assert not path.exists()


def test_media_search_job_deletes_the_file_on_failure(query_dir, monkeypatch):
    from app.jobs import worker

    path = media_search.store_query("q.jpg", io.BytesIO(_jpeg_bytes()))

    def explode(_argument):
        raise RuntimeError("model is unavailable")

    monkeypatch.setattr("app.api.media_search.run", explode)

    with pytest.raises(RuntimeError):
        worker._execute({"job_type": "MEDIA_SEARCH", "payload": {"path": str(path)}})

    assert not path.exists()


def test_media_search_loads_the_model_for_idle_unload():
    from app.jobs import worker

    assert "MEDIA_SEARCH" in worker._MODEL_JOB_TYPES


# ---- endpoints ----


def _stored_query_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []

    return list(directory.iterdir())


def test_media_search_endpoint_rejects_a_non_image(query_dir):
    response = client.post(
        "/api/v1/search/media",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    # The rejected upload leaves nothing behind.
    assert _stored_query_files(query_dir) == []


def test_media_search_endpoint_rejects_an_undecodable_file(query_dir):
    response = client.post(
        "/api/v1/search/media",
        files={"file": ("fake.jpg", b"not really a jpeg", "image/jpeg")},
    )

    assert response.status_code == 400
    assert _stored_query_files(query_dir) == []


@requires_media_job
def test_media_search_endpoint_enqueues_a_job(query_dir):
    response = client.post(
        "/api/v1/search/media",
        files={"file": ("banner.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert isinstance(job_id, int)

    job = client.get(f"/api/v1/jobs/media-search/{job_id}")
    assert job.status_code == 200
    assert job.json()["job_type"] == "MEDIA_SEARCH"

    # Clean up the queued job so the worker never runs it.
    from app.jobs import database as jobs_db

    jobs_db.mark_cancelled(job_id)


def test_media_search_job_lookup_rejects_other_job_types():
    response = client.get("/api/v1/jobs/media-search/999999999")

    assert response.status_code == 404


def test_cancel_unknown_job_returns_409():
    response = client.post("/api/v1/jobs/999999999/cancel")

    assert response.status_code == 409
