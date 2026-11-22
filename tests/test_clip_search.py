"""CLIP-поиск: сервис на синтетическом индексе и эндпоинты /v1/search/visual."""

from __future__ import annotations

import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api import repository
from app.api.main import app
from app.clip import service

client = TestClient(app, raise_server_exceptions=False)

# Ожидаемое обогащение из БД: region_id → (crop_index, address_id,
# legal_address, simple_address, brand, client) — как в реальном fetchall().
# 9 колонок как в реальном fetchall(): region_id + (crop_index,
# address_id, legal, simple, brand, client, taken_at, created_at).
ENRICH_ROWS = {
    1: (0, 51, "Адрес 1", None, "Бренд 1", None,
        "2026-11-01T10:00:00", "2026-11-02T10:00:00"),
    2: (1, 52, "Адрес 2", None, None, "Клиент 2",
        "2026-11-15T10:00:00", "2026-11-16T10:00:00"),
    3: (0, None, None, None, None, None, None, None),
    4: (1, 51, "Адрес 1", None, None, None,
        "2026-10-01T10:00:00", "2026-10-02T10:00:00"),
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
    monkeypatch.setattr(service, "PENDING_FILE", tmp_path / "pending.jsonl")
    monkeypatch.setattr(service, "get_connection", lambda: FakeConn())
    monkeypatch.setattr(service, "_state", service._State())
    # Список низкого приоритета читается из настроек БД; в базовом сценарии
    # он пуст — поведение прежнее (первый кроп). Отдельные тесты подменяют его.
    monkeypatch.setattr(service, "_low_priority_keys", lambda: set())

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


class _RegionsCursor:
    """Ответ на запрос qwen-полей регионов: region_id, client, brand."""

    def __init__(self, rows):
        self._rows = rows

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _RegionsConn:
    def __init__(self, rows):
        self._cursor = _RegionsCursor(rows)

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_search_by_photo_skips_low_priority_crop(clip_index, monkeypatch):
    """Первый кроп — Sunlight: поиск идёт по другому щиту того же кадра."""

    monkeypatch.setattr(service, "_low_priority_keys", lambda: {"sunlight"})
    monkeypatch.setattr(
        service,
        "get_connection",
        lambda: _RegionsConn([(1, "SUNLIGHT", None), (4, None, None)]),
    )

    result = service.search_by_photo("PH_aaaaaaaaaaaaaaaaaaaaaaaa", top_k=10)

    # Запрос ушёл по r4 (crop_02): ближайший — r3, а не r2, как у r1.
    assert result["matches"][0]["region_id"] == 3


def test_search_by_photo_keeps_first_crop_when_every_crop_is_low_priority(
    clip_index, monkeypatch
):
    monkeypatch.setattr(service, "_low_priority_keys", lambda: {"sunlight"})
    monkeypatch.setattr(
        service,
        "get_connection",
        lambda: _RegionsConn([(1, "Sunlight", None), (4, "SUNLIGHT", None)]),
    )

    result = service.search_by_photo("PH_aaaaaaaaaaaaaaaaaaaaaaaa", top_k=10)

    assert result["matches"][0]["region_id"] == 2


def test_photo_query_position_falls_back_on_db_error(monkeypatch):
    """Сбой чтения регионов не должен ломать «Похожие» — остаётся первый кроп."""

    monkeypatch.setattr(service, "_low_priority_keys", lambda: {"sunlight"})
    monkeypatch.setattr(
        service._state,
        "rows",
        [{"region_id": 1}, {"region_id": 4}],
        raising=False,
    )

    class BrokenConn:
        def __enter__(self):
            raise RuntimeError("db down")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(service, "get_connection", lambda: BrokenConn())

    assert service._photo_query_position("PH_" + "a" * 24, [0, 1]) == 0


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


def test_rebuild_publish_writes_final_files(tmp_path, monkeypatch):
    """Публикация ребилда: все четыре файла лежат под финальными именами.

    Регрессия: np.save молча дописывает '.npy' к tmp-имени без него, из-за
    чего os.replace не находил файл и публикация падала после ~35 минут
    эмбеддинга (18.11.2026).
    """

    import faiss as faiss_mod
    import importlib.util
    from pathlib import Path

    # Модуль скрипта требует CUDA_VISIBLE_DEVICES="" ещё на импорте.
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "clip_rebuild_test", root / "scripts" / "clip_rebuild.py"
    )
    rebuild = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(rebuild)

    monkeypatch.setattr(rebuild, "CLIP_DIR", tmp_path)
    monkeypatch.setattr(rebuild, "EMB_FILE", tmp_path / "clip_embeddings.npy")
    monkeypatch.setattr(rebuild, "META_FILE", tmp_path / "clip_meta.jsonl")
    monkeypatch.setattr(rebuild, "INDEX_FILE", tmp_path / "clip_index.faiss")
    monkeypatch.setattr(rebuild, "INFO_FILE", tmp_path / "index_info.json")

    emb = np.array([[1.0, 0.0], [0.0, 1.0]], dtype="float32")
    meta = [
        {"region_id": 1, "photo_id": "PH_A", "crop_path": "x"},
        {"region_id": 2, "photo_id": "PH_B", "crop_path": "y"},
    ]

    rebuild.publish(emb, meta, {"mode": "full"})

    for name in (
        "clip_embeddings.npy",
        "clip_meta.jsonl",
        "clip_index.faiss",
        "index_info.json",
    ):
        assert (tmp_path / name).is_file(), name

    # tmp-файлов не осталось.
    assert not [path for path in tmp_path.iterdir() if ".tmp" in path.name]

    # Опубликованный индекс согласован с метой.
    index = faiss_mod.read_index(str(tmp_path / "clip_index.faiss"))
    assert index.ntotal == 2


# ---------------------------------------------------------------------------
# Реальное время: pending-очередь новых кропов (docs/clip_search.txt §5)
# ---------------------------------------------------------------------------


def test_pending_absorb_adds_vectors_and_persists(clip_index, monkeypatch):
    """Вектор из pending попадает в поиск; после порога — и на диск.

    Сервис: поглощение мгновенно (в память), публикация файлов — по порогу
    100 векторов. Здесь порог снижен, чтобы проверить запись файлов.
    """

    import base64

    import numpy as np

    monkeypatch.setattr(service, "PERSIST_THRESHOLD_VECTORS", 1)

    # Вектор «нового кропа»: рядом с r1/r2 (фото A), но другое фото.
    vector = np.array([0.9, 0.1], dtype="float32")
    vector /= np.linalg.norm(vector)
    service.queue_region(
        77, "PH_" + "d" * 24, "data/crops/PH_D/crop_01.jpg", vector.tolist()
    )

    result = service.search_by_region(1, top_k=10)

    # Новый регион найден, фото запроса (PH_A) по-прежнему исключено.
    region_ids = [match["region_id"] for match in result["matches"]]
    assert 77 in region_ids
    assert all(match["photo_id"] != "PH_A" for match in result["matches"])
    # pending-файл вычеркнут после публикации на диск.
    assert not service.PENDING_FILE.exists() or service.PENDING_FILE.stat().st_size == 0
    # Файлы индекса обновлены: векторов стало 5.
    assert service.status()["vectors"] == 5
    _ = base64


def test_pending_absorb_is_idempotent(clip_index, monkeypatch):
    """Повторное поглощение тех же строк не дублирует векторы."""

    import numpy as np

    monkeypatch.setattr(service, "PERSIST_THRESHOLD_VECTORS", 10 ** 6)

    vector = np.array([0.0, 1.0], dtype="float32")
    service.queue_region(88, "PH_" + "e" * 24, "data/crops/PH_E/crop_01.jpg", vector.tolist())

    service.search_by_region(1, top_k=5)  # первое поглощение
    service.search_by_photo("PH_" + "b" * 24, top_k=5)  # второе — те же строки

    assert service.status()["vectors"] == 5


# ---------------------------------------------------------------------------
# Дата-фильтр «Похожих» по дате съёмки (taken_at)
# ---------------------------------------------------------------------------


def test_days_filter_keeps_recent_matches(clip_index):
    """days=30: остаются только совпадения со съёмкой за последний месяц."""

    # r2 (фото B): taken_at 2026-11-15 — свежее; r1 (фото A, исключён);
    # r3 (фото C): taken_at None — в окно не попадает.
    result = service.search_by_region(1, top_k=10, days=30)

    assert result["count"] == 1
    assert result["matches"][0]["region_id"] == 2


def test_days_zero_returns_everything(clip_index):
    """days=0 — всё время: фильтр не режет выдачу."""

    result = service.search_by_region(1, top_k=10, days=0)

    assert result["count"] == 2


def test_matches_carry_dates(clip_index):
    """Дата съёмки и дата загрузки доезжают до ответа."""

    result = service.search_by_region(1, top_k=10, days=0)

    match = result["matches"][0]
    assert match["taken_at"] is not None
    assert match["created_at"] is not None


# ---------------------------------------------------------------------------
# Эндпоинты /v1/favorites (служебная фото-подборка пользователя)
# ---------------------------------------------------------------------------


def _authorize(monkeypatch, role: str) -> dict[str, str]:
    """Сессия заданной роли без PostgreSQL: паттерн test_role_scopes.py."""

    from app.users import database as users_db

    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "1")
    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    monkeypatch.setattr(
        users_db,
        "get_session",
        lambda token: (
            {"user_id": 7, "name": "tester", "role": role}
            if token == "sess"
            else None
        ),
    )
    return {"Authorization": "Bearer sess"}


def _favorites_repository(monkeypatch):
    """Мок хранилища избранного: словарь user_id -> {photo_id}."""

    state: dict[str, set[str]] = {}

    monkeypatch.setattr(
        repository, "favorites_collection_id", lambda user_id: 4242
    )

    def fake_ids(user_id):
        return sorted(state.get(str(user_id), set()))

    def fake_add(user_id, photo_ids):
        bucket = state.setdefault(str(user_id), set())
        bucket.update(photo_ids)
        return fake_ids(user_id)

    def fake_remove(user_id, photo_ids):
        bucket = state.setdefault(str(user_id), set())
        bucket.difference_update(photo_ids)
        return fake_ids(user_id)

    monkeypatch.setattr(repository, "favorites_photo_ids", fake_ids)
    monkeypatch.setattr(repository, "add_favorite_photos", fake_add)
    monkeypatch.setattr(repository, "remove_favorite_photos", fake_remove)
    return state


def test_favorites_add_list_remove(monkeypatch):
    """Полный цикл: добавить → получить → удалить (администратор)."""

    headers = _authorize(monkeypatch, "Администратор")
    state = _favorites_repository(monkeypatch)

    photo_a = "PH_" + "a" * 24
    photo_b = "PH_" + "b" * 24

    added = client.post(
        "/api/v1/favorites",
        json={"photo_ids": [photo_a, photo_b, photo_a]},
        headers=headers,
    )
    assert added.status_code == 200
    body = added.json()
    assert body["collection_id"] == 4242
    assert body["count"] == 2  # дубликат photo_a пропущен

    listed = client.get("/api/v1/favorites", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["photo_ids"] == sorted([photo_a, photo_b])

    removed = client.delete(f"/api/v1/favorites/{photo_a}", headers=headers)
    assert removed.status_code == 200
    assert removed.json()["photo_ids"] == [photo_b]
    assert state == {"7": {photo_b}}


def test_favorites_requires_valid_photo_id(monkeypatch):
    """Битый photo_id — 404 (конвенция _validate_photo_id: не раскрывать,
    что id существует), в избранное он не попадает."""

    headers = _authorize(monkeypatch, "Администратор")
    _favorites_repository(monkeypatch)

    bad = client.post(
        "/api/v1/favorites", json={"photo_ids": ["GARBAGE"]}, headers=headers
    )

    assert bad.status_code == 404


def test_favorites_rejects_empty_list(monkeypatch):
    """Пустой список — 422, а не тихий успех."""

    headers = _authorize(monkeypatch, "Администратор")
    _favorites_repository(monkeypatch)

    empty = client.post(
        "/api/v1/favorites", json={"photo_ids": []}, headers=headers
    )

    assert empty.status_code == 422


def test_favorites_write_is_denied_to_guest(monkeypatch):
    """Гость может читать (read), но добавлять не может (collections:write)."""

    headers = _authorize(monkeypatch, "Гость")
    _favorites_repository(monkeypatch)

    listed = client.get("/api/v1/favorites", headers=headers)
    added = client.post(
        "/api/v1/favorites", json={"photo_ids": ["PH_" + "c" * 24]}, headers=headers
    )

    assert listed.status_code == 200
    assert added.status_code == 403


def test_favorites_collection_cannot_be_deleted(monkeypatch):
    """Служебную подборку нельзя удалить через общий DELETE /collections."""

    headers = _authorize(monkeypatch, "Менеджер")

    collection = {
        "collection_id": 4242,
        "name": repository.FAVORITES_COLLECTION_NAME,
        "kind": "Моя",
        "scope": "photos",
        "members": 3,
    }
    monkeypatch.setattr(
        repository, "get_collection", lambda collection_id, user_id: collection
    )

    deleted: list[int] = []
    monkeypatch.setattr(
        repository,
        "delete_collection",
        lambda collection_id, user_id: deleted.append(collection_id) or True,
    )

    response = client.delete("/api/v1/collections/4242", headers=headers)

    assert response.status_code == 409
    assert deleted == []


def test_create_collection_reserves_favorites_name(monkeypatch):
    """Пользователь не может занять имя служебной подборки."""

    headers = _authorize(monkeypatch, "Менеджер")

    created: list[dict] = []
    monkeypatch.setattr(
        repository,
        "create_collection",
        lambda **kwargs: created.append(kwargs) or {"collection_id": 1},
    )

    response = client.post(
        "/api/v1/collections",
        json={"name": repository.FAVORITES_COLLECTION_NAME, "scope": "photos"},
        headers=headers,
    )

    assert response.status_code == 409
    assert created == []
