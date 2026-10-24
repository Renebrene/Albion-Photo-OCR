"""Manual legal-address override for one photo."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import routes
from app.api.main import app

client = TestClient(app)

PHOTO_ID = "PH_" + "ab" * 12


def _override():
    return {
        "address_id": 5,
        "legal_address": "г. Ростов-на-Дону, ул. Комарова, 13",
        "simple_address": "Комарова 13",
        "updated_at": None,
    }


def test_set_photo_address_stores_override(monkeypatch):
    calls = []
    monkeypatch.setattr(
        routes.repository, "get_photo",
        lambda _pid: SimpleNamespace(model_dump=lambda: {"photo_id": PHOTO_ID}),
    )
    monkeypatch.setattr(
        routes.directory_mod,
        "get_address",
        lambda aid: {"address_id": aid, "active": True},
    )
    monkeypatch.setattr(
        routes.repository, "set_photo_address_override",
        lambda pid, aid: calls.append((pid, aid)) or _override(),
    )

    response = client.put(
        f"/api/v1/photos/{PHOTO_ID}/address",
        json={"address_id": 5},
    )

    assert response.status_code == 200
    assert response.json()["address_id"] == 5
    assert calls == [(PHOTO_ID, 5)]


def test_set_photo_address_requires_existing_photo(monkeypatch):
    monkeypatch.setattr(routes.repository, "get_photo", lambda _pid: None)

    response = client.put(
        f"/api/v1/photos/{PHOTO_ID}/address",
        json={"address_id": 5},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "photo not found"


def test_set_photo_address_requires_existing_address(monkeypatch):
    monkeypatch.setattr(
        routes.repository, "get_photo",
        lambda _pid: SimpleNamespace(model_dump=lambda: {"photo_id": PHOTO_ID}),
    )
    monkeypatch.setattr(routes.directory_mod, "get_address", lambda _aid: None)

    response = client.put(
        f"/api/v1/photos/{PHOTO_ID}/address",
        json={"address_id": 999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "address not found"


def test_set_photo_address_rejects_inactive_address(monkeypatch):
    monkeypatch.setattr(
        routes.repository, "get_photo",
        lambda _pid: SimpleNamespace(model_dump=lambda: {"photo_id": PHOTO_ID}),
    )
    monkeypatch.setattr(
        routes.directory_mod, "get_address",
        lambda aid: {"address_id": aid, "active": False},
    )

    response = client.put(
        f"/api/v1/photos/{PHOTO_ID}/address",
        json={"address_id": 5},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "address is inactive"


def test_clear_photo_address_removes_override(monkeypatch):
    monkeypatch.setattr(
        routes.repository, "get_photo",
        lambda _pid: SimpleNamespace(model_dump=lambda: {"photo_id": PHOTO_ID}),
    )
    monkeypatch.setattr(
        routes.repository, "clear_photo_address_override",
        lambda _pid: True,
    )

    response = client.delete(f"/api/v1/photos/{PHOTO_ID}/address")

    assert response.status_code == 200
    assert response.json() == {"photo_id": PHOTO_ID, "cleared": True}


def test_photo_details_include_address_override(monkeypatch):
    monkeypatch.setattr(
        routes.repository, "get_photo",
        lambda _pid: SimpleNamespace(model_dump=lambda: {"photo_id": PHOTO_ID}),
    )
    monkeypatch.setattr(routes.qwen_db, "get", lambda _pid: None)
    monkeypatch.setattr(
        routes.repository, "get_photo_address_override",
        lambda _pid: _override(),
    )

    body = client.get(f"/api/v1/photos/{PHOTO_ID}/details").json()

    assert body["address_override"]["address_id"] == 5
    assert body["address_override"]["simple_address"] == "Комарова 13"


def _fake_connection(monkeypatch, repository, captured):
    class Cursor:
        def execute(self, sql, params=None):
            captured.setdefault("queries", []).append((sql, params))

        def fetchall(self):
            return []

        def fetchone(self):
            # Счётчик корзины «Требуют проверки» читается отдельным запросом; фейк
            # отвечает на него парой нулей, чтобы распаковка не падала.
            sql = captured["queries"][-1][0] if captured.get("queries") else ""

            if "period_total" in sql:
                return (0, 0)

            return None

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class Connection:
        def cursor(self):
            return Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    @contextmanager
    def fake():
        yield Connection()

    monkeypatch.setattr(repository, "get_connection", fake)


def test_address_filter_ignores_recognized_id_after_override(monkeypatch):
    """Исправленное фото не находится по старому слепку (legacy-значение)."""

    from app.api import repository

    captured = {}
    _fake_connection(monkeypatch, repository, captured)

    repository.list_photos(limit=10, addresses=["89_v33"])

    sql, params = captured["queries"][0]
    assert "photo_address_overrides" in sql
    assert "LOWER(af.fingerprint_id) = LOWER(%s)" in sql
    assert "reg.active" in sql
    assert params[:2] == ["89_v33", "89_v33"]
    assert params[-1] == 11  # limit + 1 for the next-page probe


def test_address_filter_accepts_legal_address_ids(monkeypatch):
    """Панель отправляет addr:<address_id>; он матчит любой слепок адреса."""

    from app.api import repository

    captured = {}
    _fake_connection(monkeypatch, repository, captured)

    repository.list_photos(limit=10, addresses=["addr:5"])

    sql, params = captured["queries"][0]
    assert "ov.address_id = %s" in sql
    assert "af.address_id = %s AND af.active" in sql
    assert params[:2] == [5, 5]
    assert params[-1] == 11


def test_address_counts_follow_the_override(monkeypatch):
    """Панель считает фото по юридическому адресу, а не по одному слепку."""

    from app.api import repository

    captured = {}
    _fake_connection(monkeypatch, repository, captured)

    repository.list_addresses(limit=10)

    sql = captured["queries"][0][0]
    assert "public.address_directory" in sql
    assert "COALESCE(" in sql
    assert "ov.address_id" in sql
    assert "count(e.photo_id)" in sql
    assert "reg.active" in sql


def test_address_period_uses_the_alias_of_each_query(monkeypatch):
    """
    Период подставляется в два запроса с разными алиасами.

    Регрессия: в счётчике «Требуют проверки» оставался `e.`, тогда как там
    таблица называется `t` — PostgreSQL отвечал UndefinedTable, и панель
    адресов падала с 500 при выбранном периоде.
    """

    from app.api import repository

    captured = {}
    _fake_connection(monkeypatch, repository, captured)

    repository.list_addresses(
        limit=10,
        date_from="2026-10-01",
        date_to="2026-10-31",
        date_mode="capture",
    )

    address_sql = captured["queries"][0][0]
    review_sql = captured["queries"][1][0]

    assert "e.taken_at >= %s::date" in address_sql
    assert "t.taken_at >= %s::date" in review_sql
    assert "e.taken_at" not in review_sql


def test_save_manual_qwen_text(monkeypatch):
    photo = SimpleNamespace(model_dump=lambda: {"photo_id": PHOTO_ID})
    calls = []
    monkeypatch.setattr(routes.repository, "get_photo", lambda _pid: photo)
    monkeypatch.setattr(
        routes.qwen_db, "save_manual",
        lambda pid, fields: calls.append((pid, fields)),
    )
    monkeypatch.setattr(routes.qwen_db, "get", lambda _pid: {"status": "DONE"})

    response = client.put(
        f"/api/v1/photos/{PHOTO_ID}/qwen-text",
        json={
            "description": "Новое описание",
            "client": "Клиент",
            "brand": None,
            "category": "Реклама",
            "tags": ["тег", "ещё"],
        },
    )

    assert response.status_code == 200
    assert calls[0][0] == PHOTO_ID
    assert calls[0][1]["description"] == "Новое описание"
    assert calls[0][1]["tags"] == ["тег", "ещё"]


def test_save_manual_qwen_text_requires_photo(monkeypatch):
    monkeypatch.setattr(routes.repository, "get_photo", lambda _pid: None)

    response = client.put(
        f"/api/v1/photos/{PHOTO_ID}/qwen-text",
        json={"description": "x"},
    )

    assert response.status_code == 404


def test_address_list_narrows_to_clients(monkeypatch):
    """В приоритете по клиентам адреса сужаются до адресов этих клиентов."""

    from app.api import repository

    captured = {}
    _fake_connection(monkeypatch, repository, captured)

    repository.list_addresses(limit=10, clients=["Клиент"])

    sql, params = captured["queries"][0]
    assert "HAVING count(e.photo_id) > 0" in sql
    assert "LOWER(ca.canonical) = LOWER(%s)" in sql
    assert params == ["Клиент", "Клиент", 10]
    # Отбор по распознаванию обязан быть в скобках: без них `A OR B AND C`
    # разбирается как `A OR (B AND C)`, и клиентский фильтр отсекает только
    # фото с ручной заменой адреса — то есть не отсекает ничего.
    assert "(s.addr_fp IS NOT NULL OR ov.address_id IS NOT NULL)" in sql
    # Клиент берётся из QWEN и только для этого режима.
    assert "q.client AS client" in sql


def test_client_list_narrows_to_addresses(monkeypatch):
    """В приоритете по адресам клиенты сужаются до клиентов этих адресов."""

    from app.api import repository

    captured = {}
    _fake_connection(monkeypatch, repository, captured)

    repository.list_clients(limit=10, addresses=["addr:5"])

    sql, params = captured["queries"][0]
    assert "af.address_id = %s AND af.active" in sql
    assert "public.hybrid_results" in sql
    # На строку больше запрошенного: лишняя строка означает «есть продолжение».
    assert params == [5, 5, 11]
    # Отбор по адресу применяется один раз, а не в каждой ветке UNION:
    # иначе плейсхолдеры удваивались бы, а параметры шли вразнобой.
    assert sql.count("af.address_id = %s") == 1


def test_client_list_pages_by_name_and_kind(monkeypatch):
    """Курсор продолжает список по паре (имя, вид): под именем есть и бренд."""

    from app.api import repository

    captured = {}
    _fake_connection(monkeypatch, repository, captured)

    cursor = repository.encode_cursor("мира", "client")
    repository.list_clients(limit=10, cursor=cursor)

    sql, params = captured["queries"][0]
    assert "(sort_key, kind) > (%s, %s)" in sql
    assert params[-3:] == ["мира", "client", 11]


def test_client_list_counts_clients_and_brands(monkeypatch):
    """Список панели — клиенты и бренды вместе, каждый со своим видом."""

    from app.api import repository

    captured = {}
    _fake_connection(monkeypatch, repository, captured)

    repository.list_clients(limit=10)

    sql, _ = captured["queries"][0]
    assert "'client' AS kind" in sql
    assert "'brand' AS kind" in sql
    # Считаем по компактному источнику, а не по полной выборке карточки.
    assert "_PHOTO_SELECT" not in sql
    assert "LEFT JOIN LATERAL" in sql


def test_collection_client_limit_is_enforced_in_repository(monkeypatch):
    """Подборка не может содержать больше 100 клиентов."""

    import pytest

    from app.api import repository

    captured = {}
    _fake_connection(monkeypatch, repository, captured)

    with pytest.raises(ValueError):
        repository.add_collection_members(
            1,
            member_type="client",
            values=[f"client-{index}" for index in range(101)],
        )
