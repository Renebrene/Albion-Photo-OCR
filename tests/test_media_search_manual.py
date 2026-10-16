"""
Ручной режим умного поиска (этап 5): describe-only и поиск по фильтрам.

DB-free: QWEN и поиск подменяются заглушками, маршруты проверяются на права
и валидацию.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import routes as api_routes
from app.api.main import app
from app.api import media_search

client = TestClient(app, raise_server_exceptions=False)

_FIELDS = {
    "description": "щит с врачом",
    "address": None,
    "client": "Яндекс",
    "brand": None,
    "category": "наружка",
    "tags": ["щит", "врач"],
}


def test_run_rejects_unknown_mode(tmp_path):
    with pytest.raises(ValueError):
        media_search.run(tmp_path / "x.jpg", kind="image", mode="banana")


def test_describe_mode_does_not_search(monkeypatch, tmp_path):
    calls = {"search": 0}

    monkeypatch.setattr(
        media_search, "describe",
        lambda path, **kw: {"fields": dict(_FIELDS), "seconds": 0.1, "fallback": False},
    )
    monkeypatch.setattr(
        media_search, "search",
        lambda *a, **k: calls.__setitem__("search", calls["search"] + 1)
        or {"photo_ids": [], "count": 0, "truncated": False},
    )

    out = media_search.run(tmp_path / "photo.jpg", kind="image", mode="describe")

    assert out["mode"] == "describe"
    assert out["photo_ids"] == []
    assert out["count"] == 0
    assert calls["search"] == 0
    assert out["qwen"]["description"] == "щит с врачом"


def test_search_ranks_by_number_of_matched_terms(monkeypatch):
    from app.api import repository

    class Item:
        def __init__(self, photo_id):
            self.photo_id = photo_id

    def fake_list_photos(limit, query):
        # "щит" → A,B ; "Яндекс" → A ; "KVAS" → C
        return {
            "щит": [Item("A"), Item("B")],
            "Яндекс": [Item("A")],
            "KVAS": [Item("C")],
        }.get(query, []), None

    monkeypatch.setattr(repository, "list_photos", fake_list_photos)

    out = media_search.search(
        {"q": "щит", "client": "Яндекс", "brand": "KVAS", "category": None}
    )

    # A matched description (+1) and client (+2) → first.
    assert out["photo_ids"][0] == "A"
    assert out["scores"]["A"] == 3
    assert set(out["photo_ids"]) == {"A", "B", "C"}


def test_search_with_no_terms_is_empty(monkeypatch):
    from app.api import repository

    monkeypatch.setattr(repository, "list_photos", lambda **kw: ([], None))

    out = media_search.search({"q": None, "client": None, "brand": None, "category": None})
    assert out["photo_ids"] == []
    assert out["count"] == 0


def test_describe_mode_with_frame_seconds_extracts_one_frame(monkeypatch, tmp_path):
    seen = {}

    def fake_extract(path, *, seconds=None):
        seen["seconds"] = seconds
        return [{"path": tmp_path / "f.jpg", "sec": float(seconds[0])}]

    monkeypatch.setattr(media_search, "extract_frames", fake_extract)
    monkeypatch.setattr(
        media_search, "describe",
        lambda path, **kw: {"fields": dict(_FIELDS), "seconds": 0.1, "fallback": False},
    )

    out = media_search.run(
        tmp_path / "clip.mp4", kind="video", mode="describe", frame_seconds=4.0,
    )

    assert seen["seconds"] == (4.0,)
    assert out["per_frame"][0]["sec"] == 4.0


def test_run_rejects_negative_frame_seconds(tmp_path):
    with pytest.raises(ValueError):
        media_search.run(tmp_path / "c.mp4", kind="video", frame_seconds=-1)


def test_auto_mode_searches(monkeypatch, tmp_path):
    monkeypatch.setattr(
        media_search, "describe",
        lambda path, **kw: {"fields": dict(_FIELDS), "seconds": 0.1, "fallback": False},
    )
    monkeypatch.setattr(
        media_search, "search",
        lambda *a, **k: {"photo_ids": ["PH_1"], "count": 1, "truncated": False},
    )

    out = media_search.run(tmp_path / "photo.jpg", kind="image", mode="auto")

    assert out["photo_ids"] == ["PH_1"]
    assert out["mode"] == "auto"


def test_worker_query_mode_searches_without_a_file(monkeypatch):
    from app.jobs import worker

    seen = {}

    def fake_search(filters, **kwargs):
        seen.update(filters)
        return {"photo_ids": ["PH_9"], "count": 1, "truncated": False}

    monkeypatch.setattr(media_search, "search", fake_search)

    result = worker._execute({
        "id": 1,
        "job_type": "MEDIA_SEARCH",
        "payload": {
            "filters": {
                "q": "щит", "client": None, "brand": None,
                "category": None, "address": None,
            }
        },
    })

    assert result["photo_ids"] == ["PH_9"]
    assert result["mode"] == "query"
    assert seen["q"] == "щит"


def test_query_endpoint_rejects_empty(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:searches:write")
    response = client.post(
        "/api/v1/search/query", json={},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 422


def test_query_endpoint_enqueues(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:searches:write")
    monkeypatch.setattr(api_routes.jobs_db, "enqueue", lambda job_type, payload: 7)

    response = client.post(
        "/api/v1/search/query", json={"q": "щит", "client": "Яндекс"},
        headers={"Authorization": "Bearer tok"},
    )

    assert response.status_code == 202
    assert response.json()["job_id"] == 7


def test_query_endpoint_requires_write_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.post(
        "/api/v1/search/query", json={"q": "щит"},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_describe_endpoint_requires_write_scope(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.post(
        "/api/v1/search/media/describe",
        files={"file": ("a.jpg", b"not-an-image", "image/jpeg")},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def _ids_db_available() -> bool:
    import os

    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.photos')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_ids_db = pytest.mark.skipif(
    not _ids_db_available(),
    reason="photos table not available",
)


@requires_ids_db
def test_list_photos_preserves_the_given_id_order():
    from app.api import repository

    all_ids = repository.all_photo_ids()

    if len(all_ids) < 3:
        pytest.skip("needs at least three photos")

    wanted = [all_ids[2], all_ids[0], all_ids[1]]
    items, _ = repository.list_photos(limit=10, ids=wanted)

    assert [item.photo_id for item in items][:3] == wanted
