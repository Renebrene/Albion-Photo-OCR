"""Фильтры грида: лимит списков, «только после HYBRID» и период в счётчиках."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import repository
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_many_client_filters_do_not_return_422(monkeypatch):
    """
    «Все» в панели клиентов отправляет каждого клиента отдельным параметром.
    Раньше список был ограничен 64 значениями и запрос падал с 422.
    """

    monkeypatch.setattr(repository, "list_photos", lambda **kwargs: ([], None))
    monkeypatch.setattr(repository, "count_photos", lambda **kwargs: 0)

    params = [("limit", "100")] + [
        ("client", f"client-{index}") for index in range(90)
    ]

    response = client.get("/api/v1/photos", params=params)

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_a_long_sort_cursor_is_accepted(monkeypatch):
    """
    Курсор страницы длиннее 64 символов не должен давать 422.

    Курсор — base64 от {"v": ключ сортировки, "id": photo_id}. Для даты это
    ~96 символов, для имени файла — до 156; старый Query(max_length=64) отбивал
    вторую страницу, и грид вставал на первых 100 фото с ошибкой
    «String should have at most 64 characters».
    """

    seen: dict = {}

    def fake_list_photos(**kwargs):
        seen.update(kwargs)
        return [], None

    monkeypatch.setattr(repository, "list_photos", fake_list_photos)
    monkeypatch.setattr(repository, "count_photos", lambda **kwargs: 0)

    cursor = repository.encode_cursor(
        "Конной Армии 32 А (10).JPG",
        "PH_a9fa729cd53e78f0ca31b800",
    )

    assert len(cursor) > 64

    response = client.get(
        "/api/v1/photos",
        params={"limit": "100", "sort": "filename", "cursor": cursor},
    )

    assert response.status_code == 200
    # Курсор дошёл до репозитория как есть, а не был обрезан.
    assert seen["cursor"] == cursor


def test_recognized_uses_the_latest_hybrid_verdict_only():
    """Старый успешный вердикт не должен пережить новый провальный прогон."""

    recognized = repository._recognized_sql("t")

    assert "ORDER BY h.finished_at DESC" in recognized
    assert "LIMIT 1" in recognized
    assert "hybrid_final_id IS NOT NULL" not in recognized
    assert "ORDER BY h.finished_at DESC" in repository._PHOTO_BASE
    assert "hybrid_final_id IS NOT NULL" not in repository._PHOTO_BASE


def test_address_filter_requires_an_active_directory_row():
    where, params = repository._photo_where(addresses=["addr:5"])

    assert "public.address_directory" in where
    assert "active" in where
    assert params == [5, 5]


def test_the_grid_asks_only_for_recognized_photos(monkeypatch):
    seen: dict = {}

    def fake_list_photos(**kwargs):
        seen.update(kwargs)
        return [], None

    monkeypatch.setattr(repository, "list_photos", fake_list_photos)
    monkeypatch.setattr(repository, "count_photos", lambda **kwargs: 0)

    response = client.get("/api/v1/photos")

    assert response.status_code == 200
    assert seen["recognized_only"] is True


def test_structured_suggestions_pass_exact_filters(monkeypatch):
    seen: dict = {}

    def fake_list_photos(**kwargs):
        seen.update(kwargs)
        return [], None

    monkeypatch.setattr(repository, "list_photos", fake_list_photos)
    monkeypatch.setattr(repository, "count_photos", lambda **kwargs: 0)

    response = client.get(
        "/api/v1/photos",
        params={"brand": "СТС", "tag": "реклама", "category": "щит"},
    )

    assert response.status_code == 200
    assert seen["brand"] == "СТС"
    assert seen["tag"] == "реклама"
    assert seen["category"] == "щит"


def test_addresses_pass_the_selected_period(monkeypatch):
    seen: dict = {}

    def fake_addresses(**kwargs):
        seen.update(kwargs)
        return []

    monkeypatch.setattr(repository, "list_addresses", fake_addresses)

    response = client.get(
        "/api/v1/addresses",
        params={
            "date_from": "2026-10-01",
            "date_to": "2026-10-31",
            "date_mode": "capture",
        },
    )

    assert response.status_code == 200
    assert seen == {
        # Длину списка адресов не ограничиваем (задание, 28.10.2026): усечение
        # прятало адреса от панели. None — «отдать всё».
        "limit": None,
        "date_from": "2026-10-01",
        "date_to": "2026-10-31",
        "date_mode": "capture",
        "clients": None,
        "group": None,
    }


def test_stats_pass_the_selected_period(monkeypatch):
    seen: dict = {}

    def fake_stats(**kwargs):
        seen.update(kwargs)
        return {
            "photos": 1,
            "videos": 2,
            "period_photos": 3,
            "period_videos": 4,
            "addresses": 5,
            "clients": 6,
            "last_photo_at": None,
            "last_video_at": None,
        }

    monkeypatch.setattr(repository, "stats", fake_stats)

    response = client.get(
        "/api/v1/stats",
        params={
            "date_from": "2026-10-01",
            "date_to": "2026-10-31",
            "date_mode": "upload",
        },
    )

    assert response.status_code == 200
    assert seen == {
        "date_from": "2026-10-01",
        "date_to": "2026-10-31",
        "date_mode": "upload",
    }
    assert response.json()["period_photos"] == 3
    assert response.json()["period_videos"] == 4


def test_tag_facets_combine_with_or():
    """
    Клиенты, бренд, тег и категория — альтернативы, а не уточнения:
    выбранный бренд добавляет свои фото к выбранным клиентам.
    """

    where, params = repository._photo_where(
        clients=["Клиент"],
        brand="СТС",
        tag="канал СТС",
    )

    assert "LOWER(t.brand) = LOWER(%s)" in where
    assert "ca.kind = 'brand'" in where
    assert " OR EXISTS (" in where
    assert params == ["Клиент", "Клиент", "СТС", "СТС", "канал СТС"]


def test_combine_union_ors_all_tag_facets():
    where, params = repository._photo_where(
        addresses=["addr:5"],
        clients=["Клиент"],
        brand="СТС",
        combine="union",
    )

    assert params == [5, 5, "Клиент", "Клиент", "СТС", "СТС"]
    assert "LOWER(t.brand) = LOWER(%s)" in where


def test_combine_address_makes_the_address_the_universe():
    where, params = repository._photo_where(
        addresses=["addr:5"],
        clients=["Клиент"],
        brand="СТС",
        combine="address",
    )

    assert params == [5, 5, "Клиент", "Клиент", "СТС", "СТС"]
    assert ") AND (" in where


def test_combine_client_prioritises_clients_and_keeps_param_order():
    where, params = repository._photo_where(
        addresses=["addr:5"],
        clients=["Клиент"],
        brand="СТС",
        combine="client",
    )

    assert params == ["Клиент", "Клиент", 5, 5, "СТС", "СТС"]
    assert ") AND (" in where


def test_malformed_address_value_matches_nothing():
    where, params = repository._photo_where(
        addresses=["addr:not-a-number"],
        combine="address",
    )

    assert "FALSE" in where
    assert params == []


def test_combine_rejects_unknown_mode():
    import pytest

    with pytest.raises(ValueError):
        repository._photo_where(addresses=["addr:5"], combine="nope")


def test_invalid_date_is_rejected_with_422(monkeypatch):
    monkeypatch.setattr(repository, "list_photos", lambda **kwargs: ([], None))
    monkeypatch.setattr(repository, "count_photos", lambda **kwargs: 0)

    response = client.get(
        "/api/v1/photos",
        params={"date_from": "abcdefghij"},
    )

    assert response.status_code == 422


def test_inverted_date_range_is_swapped(monkeypatch):
    seen = {}

    def fake_list_photos(**kwargs):
        seen.update(kwargs)
        return [], None

    monkeypatch.setattr(repository, "list_photos", fake_list_photos)
    monkeypatch.setattr(repository, "count_photos", lambda **kwargs: 0)

    response = client.get(
        "/api/v1/photos",
        params={"date_from": "2026-10-31", "date_to": "2026-10-01"},
    )

    assert response.status_code == 200
    assert seen["date_from"] == "2026-10-01"
    assert seen["date_to"] == "2026-10-31"


def test_photo_collection_filter_rejects_other_scopes(monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_collection",
        lambda collection_id, user_id=None: {
            "collection_id": collection_id,
            "scope": "clients",
        },
    )

    response = client.get("/api/v1/photos", params={"collection_id": 5})

    assert response.status_code == 422
    assert response.json()["detail"] == "collection scope must be photos"


def test_collection_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(
        repository,
        "add_collection_members",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("limit")),
    )
    monkeypatch.setattr(
        repository,
        "get_collection",
        lambda collection_id, user_id=None: {
            "collection_id": collection_id,
            "scope": "clients",
        },
    )

    response = client.post(
        "/api/v1/collections/5/members",
        json={"member_type": "client", "values": ["a", "b"]},
    )

    assert response.status_code == 422


def test_collection_member_type_must_match_scope(monkeypatch):
    monkeypatch.setattr(
        repository,
        "get_collection",
        lambda collection_id, user_id=None: {
            "collection_id": collection_id,
            "scope": "photos",
        },
    )

    response = client.post(
        "/api/v1/collections/5/members",
        json={"member_type": "client", "values": ["a"]},
    )

    assert response.status_code == 422
    assert "requires member_type photo" in response.json()["detail"]


def test_photo_read_sql_needs_a_preview():
    """
    Фото появляется в гриде и в счётчиках адресов только с превью: прогон
    «Обновление базы» наполняет галерею по мере создания превью, а битый
    файл (превью не создаётся) в выдачу не попадает вовсе.
    """

    assert "photo_previews" in repository._PREVIEW_READY_SQL
    # Условие стоит в базовом SELECT: его наследуют и список, и счётчик
    # периода, и панель адресов с «Требуют проверки».
    assert repository._PREVIEW_READY_SQL.strip() in repository._PHOTO_BASE
    assert "photo_previews" in repository._PHOTO_SELECT
