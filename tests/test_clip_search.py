"""CLIP-поиск: сервис на синтетическом индексе и эндпоинты /v1/search/visual."""

from __future__ import annotations

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.clip import service

client = TestClient(app, raise_server_exceptions=False)

# Ожидаемое обогащение из БД: region_id → (crop_index, address_id,
# legal_address, simple_address, brand, client) — как в реальном fetchall().
ENRICH_ROWS = {
    1: (0, 51, "Адрес 1", None, "Бренд 1", None),
    2: (1, 52, "Адрес 2", None, None, "Клиент 2"),
    3: (0, None, None, None, None, None),
    4: (1, 51, "Адрес 1", None, None, None),
}


class FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self._params = params

    def fetchall(self):
        # Возвращаем строки только для запрошенных region_id.
        wanted = list(self._params[0]) if self._params else []
        return [
            (region_id, *ENRICH_ROWS[region_id])
            for region_id in wanted
            if region_id in ENRICH_ROWS
        ]

    def fetchone(self):
        return (len(ENRICH_ROWS),)


class FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return FakeCursor()


@pytest.fixture()
def clip_index(tmp_path, monkeypatch):
    """Мини-индекс: r1/r2 — одинаковые кропы разных фото, r3 — другое, r4 —
    второе фото A (должно исключаться при поиске по фото A)."""

    rows = [
        {"region_id": 1, "photo_id": "PH_aaaaaaaaaaaaaaaaaaaaaaaa", "crop_path": "data/crops/PH_A/crop_01.jpg", "score": 0.9},
        {"region_id": 2, "photo_id": "PH_bbbbbbbbbbbbbbbbbbbbbbbb", "crop_path": "data/crops/PH_B/crop_01.jpg", "score": 0.8},
        {"region_id": 3, "photo_id": "PH_cccccccccccccccccccccccc", "crop_path": "data/crops/PH_C/crop_01.jpg", "score": 0.7},
        {"region_id": 4, "photo_id": "PH_aaaaaaaaaaaaaaaaaaaaaaaa", "crop_path": "data/crops/PH_A/crop_02.jpg", "score": 0.6},
    ]
    emb = np.array(
        [
            [1.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [0.35, 0.936],
        ],
        dtype="float32",
    )
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)

    import faiss

    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)

    monkeypatch.setattr(service, "CLIP_DIR", tmp_path)
    monkeypatch.setattr(service, "INDEX_FILE", tmp_path / "clip_index.faiss")
    monkeypatch.setattr(service, "META_FILE", tmp_path / "clip_meta.jsonl")
    monkeypatch.setattr(service, "INFO_FILE", tmp_path / "index_info.json")
    monkeypatch.setattr(service, "get_connection", lambda: FakeConn())
    monkeypatch.setattr(service, "_state", service._State())

    faiss.write_index(index, str(tmp_path / "clip_index.faiss"))
    with (tmp_path / "clip_meta.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    (tmp_path / "index_info.json").write_text(
        json.dumps({"model": "test-model", "vectors": len(rows)}),
        encoding="utf-8",
    )
    return rows


def test_search_by_region_excludes_the_query_photo(clip_index):
    """Похожие для региона 1: r2 (тот же вектор) первый, фото A исключено."""

    result = service.search_by_region(1, top_k=10)

    assert result["count"] == 2  # r2 и r3; r4 (то же фото) отфильтрован
    assert result["matches"][0]["region_id"] == 2
    assert result["matches"][0]["score"] == pytest.approx(1.0, abs=1e-4)
    assert result["matches"][1]["region_id"] == 3
    # Обогащение из БД дошло до ответа.
    assert result["matches"][0]["address"] == "Адрес 2"
    assert result["matches"][0]["brand"] is None
    assert result["matches"][0]["client"] == "Клиент 2"


def test_search_by_region_returns_only_top_k(clip_index):
    """top_k обрезает выдачу."""

    result = service.search_by_region(1, top_k=1)

    assert result["count"] == 1
    assert len(result["matches"]) == 1


def test_search_by_photo_uses_first_crop(clip_index):
    """Для фото A берётся первый кроп (r1); r4 того же фото исключён."""

    result = service.search_by_photo("PH_aaaaaaaaaaaaaaaaaaaaaaaa", top_k=10)

    assert result["query_photo_id"] == "PH_aaaaaaaaaaaaaaaaaaaaaaaa"
    assert result["matches"][0]["region_id"] == 2


def test_search_by_unknown_photo_raises(clip_index):
    """Фото без кропов в индексе — KeyError (эндпоинт отвечает 404)."""

    with pytest.raises(KeyError):
        service.search_by_photo("PH_MISSING")


def test_missing_index_is_reported(monkeypatch, tmp_path):
    """Без файлов индекса сервис сообщает о недоступности, а эндпоинт — 503."""

    monkeypatch.setattr(service, "CLIP_DIR", tmp_path)
    monkeypatch.setattr(service, "INDEX_FILE", tmp_path / "clip_index.faiss")
    monkeypatch.setattr(service, "META_FILE", tmp_path / "clip_meta.jsonl")
    monkeypatch.setattr(service, "INFO_FILE", tmp_path / "index_info.json")
    monkeypatch.setattr(service, "_state", service._State())

    assert service.status()["available"] is False

    response = client.get("/api/v1/search/visual", params={"photo_id": "PH_aaaaaaaaaaaaaaaaaaaaaaaa"})

    assert response.status_code == 503
    # Абсолютные пути в ответе не раскрываются.
    assert str(tmp_path) not in response.json()["detail"]


def test_status_reports_vectors_and_freshness(clip_index):
    """Статус: векторы, отставание от БД считается по числу регионов."""

    status = service.status()

    assert status["available"] is True
    assert status["vectors"] == 4
    assert status["db_regions"] == 4
    assert status["stale"] is False


def test_visual_endpoint_requires_exactly_one_query(clip_index):
    """region_id и photo_id — ровно один из двух."""

    both = client.get(
        "/api/v1/search/visual", params={"region_id": 1, "photo_id": "PH_aaaaaaaaaaaaaaaaaaaaaaaa"}
    )
    neither = client.get("/api/v1/search/visual")

    assert both.status_code == 422
    assert neither.status_code == 422


def test_visual_endpoint_top_k_bounds(clip_index):
    """top_k ограничен 1..50."""

    response = client.get("/api/v1/search/visual", params={"region_id": 1, "top_k": 99})

    assert response.status_code == 422


def test_visual_endpoint_unknown_region_is_404(clip_index):
    """Регион не из индекса — 404, а не 500."""

    response = client.get("/api/v1/search/visual", params={"region_id": 999})

    assert response.status_code == 404


def test_visual_endpoint_by_photo(clip_index):
    """Эндпоинт отдаёт совпадения по фото."""

    response = client.get("/api/v1/search/visual", params={"photo_id": "PH_aaaaaaaaaaaaaaaaaaaaaaaa"})

    assert response.status_code == 200
    body = response.json()
    assert body["query_photo_id"] == "PH_aaaaaaaaaaaaaaaaaaaaaaaa"
    assert body["matches"][0]["region_id"] == 2
    assert body["matches"][0]["address"] == "Адрес 2"
