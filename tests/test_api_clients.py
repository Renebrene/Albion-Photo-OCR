"""
Tests for client alias normalization (schema 016, /v1/client-aliases).

Scope checks run everywhere; the lifecycle test needs PostgreSQL and creates a
throwaway photo + photo_qwen row it removes afterwards.
"""

from __future__ import annotations

import hashlib
import os

import pytest
from fastapi.testclient import TestClient

from app.api import repository
from app.api.main import app
from app.ingest.database import get_connection

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.client_aliases')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="client_aliases not available (INGEST_DB_* / schema 016)",
)

PROBE_ID = "PH_" + "9" * 24
PROBE_RAW = "__alias_probe_raw__"
PROBE_CANON = "__alias_probe_canonical__"

# Отдельное фото для проверок бренд-алиасов в строке поиска.
PROBE_BRAND_ID = "PH_" + "8" * 24


def _insert_photo(photo_id: str, *, brand: str | None = None) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photos (
                    photo_id, source_path, filename, sha256,
                    container_format, frame_count, width, height
                )
                VALUES (%s, %s, %s, %s, 'JPEG', 1, 10, 10)
                """,
                (
                    photo_id,
                    f"/tmp/{photo_id}.jpg",
                    f"{photo_id}.jpg",
                    hashlib.sha256(photo_id.encode()).hexdigest(),
                ),
            )
            cur.execute(
                """
                INSERT INTO public.photo_qwen (photo_id, status, brand)
                VALUES (%s, 'DONE', %s)
                """,
                (photo_id, brand),
            )


def _cleanup() -> None:
    ids = [PROBE_ID, PROBE_BRAND_ID]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.client_aliases WHERE alias LIKE %s",
                ("__alias_probe%",),
            )
            cur.execute(
                "DELETE FROM public.client_alias_audit WHERE alias LIKE %s",
                ("__alias_probe%",),
            )
            cur.execute(
                "DELETE FROM public.photo_qwen WHERE photo_id = ANY(%s)", (ids,)
            )
            cur.execute(
                "DELETE FROM public.photos WHERE photo_id = ANY(%s)", (ids,)
            )


def test_upsert_requires_collections_write(monkeypatch):
    monkeypatch.setenv("SCENE_API_TOKENS", "tok:read")
    response = client.put(
        "/api/v1/client-aliases",
        json={"alias": "a", "canonical": "b"},
        headers={"Authorization": "Bearer tok"},
    )
    assert response.status_code == 403


def test_upsert_validates_body():
    assert (
        client.put("/api/v1/client-aliases", json={"alias": ""}).status_code
        == 422
    )


@requires_db
def test_alias_folds_clients_and_lifecycle():
    _cleanup()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.photos (
                        photo_id, source_path, filename, sha256,
                        container_format, frame_count, width, height
                    )
                    VALUES (%s, %s, %s, %s, 'JPEG', 1, 10, 10)
                    """,
                    (
                        PROBE_ID,
                        f"/tmp/{PROBE_RAW}.jpg",
                        f"{PROBE_RAW}.jpg",
                        hashlib.sha256(PROBE_ID.encode()).hexdigest(),
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO public.photo_qwen (photo_id, status, client)
                    VALUES (%s, 'DONE', %s)
                    """,
                    (PROBE_ID, PROBE_RAW),
                )

        # Before aliasing, the raw client is its own facet. The probe has no
        # HYBRID verdict, so query the repository without recognized_only.
        raw_clients = [
            c["client"]
            for c in repository.list_clients(
                limit=1000, recognized_only=False,
            )
        ]
        assert PROBE_RAW in raw_clients
        assert PROBE_CANON not in raw_clients

        created = client.put(
            "/api/v1/client-aliases",
            json={"alias": PROBE_RAW, "canonical": PROBE_CANON},
        )
        assert created.status_code == 200

        aliases = client.get("/api/v1/client-aliases").json()["items"]
        assert {
            "alias": PROBE_RAW,
            "canonical": PROBE_CANON,
            "kind": "client",
        } in aliases

        folded = repository.list_clients(
            limit=1000, recognized_only=False,
        )
        names = [c["client"] for c in folded]
        assert PROBE_CANON in names
        assert PROBE_RAW not in names

        # Filtering by the canonical client also matches the aliased row.
        filtered, _ = repository.list_photos(
            limit=100,
            clients=[PROBE_CANON],
            recognized_only=False,
        )
        assert PROBE_ID in {item.photo_id for item in filtered}

        assert (
            client.delete(
                "/api/v1/client-aliases", params={"alias": PROBE_RAW}
            ).status_code
            == 200
        )
        assert (
            client.delete(
                "/api/v1/client-aliases", params={"alias": PROBE_RAW}
            ).status_code
            == 404
        )
    finally:
        _cleanup()


def _kinds_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = 'client_aliases' AND column_name = 'kind'"
                )
                return cur.fetchone() is not None
    except Exception:
        return False


requires_kinds = pytest.mark.skipif(
    not _kinds_available(),
    reason="client_aliases.kind not available (schema 035)",
)

BRAND_RAW = "__alias_probe_brand__"
BRAND_CANON = "__alias_probe_brand_canonical__"


@requires_kinds
def test_brand_aliases_live_apart_from_clients():
    """Бренд и клиент — разные виды одного справочника (schema/035)."""

    _cleanup()

    try:
        created = client.put(
            "/api/v1/client-aliases",
            json={"alias": BRAND_RAW, "canonical": BRAND_CANON},
            params={"kind": "brand"},
        )
        assert created.status_code == 200
        assert created.json()["kind"] == "brand"

        brands = client.get(
            "/api/v1/client-aliases", params={"kind": "brand"}
        ).json()["items"]
        assert {"alias": BRAND_RAW, "canonical": BRAND_CANON, "kind": "brand"} in brands

        # В списке клиентов бренд-строка не появляется.
        clients_ = client.get(
            "/api/v1/client-aliases", params={"kind": "client"}
        ).json()["items"]
        assert all(item["alias"] != BRAND_RAW for item in clients_)

        # Журнал правок тоже разделён по виду.
        brand_audit = client.get(
            "/api/v1/client-aliases/audit", params={"kind": "brand"}
        ).json()["items"]
        assert any(
            row["alias"] == BRAND_RAW and row["kind"] == "brand"
            for row in brand_audit
        )

        client_audit = client.get(
            "/api/v1/client-aliases/audit", params={"kind": "client"}
        ).json()["items"]
        assert all(row["alias"] != BRAND_RAW for row in client_audit)

        # Удаление без указания вида не тронет бренд.
        assert (
            client.delete(
                "/api/v1/client-aliases", params={"alias": BRAND_RAW}
            ).status_code
            == 404
        )
        assert (
            client.delete(
                "/api/v1/client-aliases",
                params={"alias": BRAND_RAW, "kind": "brand"},
            ).status_code
            == 200
        )
    finally:
        _cleanup()


@requires_kinds
def test_brand_alias_is_found_by_the_search_string():
    """Строка поиска по каноническому бренду находит «сырое» написание QWEN."""

    _cleanup()

    try:
        _insert_photo(PROBE_BRAND_ID, brand=BRAND_RAW)

        before, _ = repository.list_photos(
            limit=100, query=BRAND_CANON, recognized_only=False,
        )
        assert PROBE_BRAND_ID not in {item.photo_id for item in before}

        saved = client.put(
            "/api/v1/client-aliases",
            json={"alias": BRAND_RAW, "canonical": BRAND_CANON},
            params={"kind": "brand"},
        )
        assert saved.status_code == 200

        # Ищем по каноническому имени — фото с «сырым» брендом должно найтись.
        found, _ = repository.list_photos(
            limit=100, query=BRAND_CANON, recognized_only=False,
        )
        assert PROBE_BRAND_ID in {item.photo_id for item in found}
    finally:
        _cleanup()


@requires_kinds
def test_client_alias_does_not_resolve_a_brand():
    """Словарь клиентов не подставляет бренд: виды не смешиваются."""

    _cleanup()

    try:
        _insert_photo(PROBE_BRAND_ID, brand=BRAND_RAW)

        # Алиас того же «сырого» текста, но вида client.
        saved = client.put(
            "/api/v1/client-aliases",
            json={"alias": BRAND_RAW, "canonical": BRAND_CANON},
            params={"kind": "client"},
        )
        assert saved.status_code == 200

        found, _ = repository.list_photos(
            limit=100, query=BRAND_CANON, recognized_only=False,
        )
        assert PROBE_BRAND_ID not in {item.photo_id for item in found}
    finally:
        _cleanup()


@requires_kinds
def test_unknown_kind_is_rejected():
    assert (
        client.get(
            "/api/v1/client-aliases", params={"kind": "address"}
        ).status_code
        == 422
    )
