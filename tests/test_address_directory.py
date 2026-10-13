"""
Address directory (schema/022): legal/simple names for fingerprint ids.

Validation runs everywhere; the tests that touch rows skip unless PostgreSQL is
configured. Every created address is deleted again, including the fingerprint
mappings it owns (CASCADE), so the directory is left as it was found.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.api import directory as directory_mod
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.address_directory')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_directory = pytest.mark.skipif(
    not _db_available(),
    reason="schema/022 (address_directory) is not applied",
)


@pytest.fixture
def cleanup_addresses():
    """Delete the addresses a test created, keeping the directory intact."""

    created: list[int] = []

    yield created

    if not created:
        return

    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.address_directory WHERE address_id = ANY(%s)",
                (created,),
            )


# ---- validation (no database) ----


def test_clean_name_collapses_whitespace_and_bounds_length():
    assert directory_mod._clean_name("  ул.  Ленина, 1 ", field="x") == "ул. Ленина, 1"
    assert directory_mod._clean_name(None, field="x") == ""
    assert directory_mod._clean_name("", field="x") == ""


def test_clean_name_rejects_other_types_and_long_values():
    with pytest.raises(directory_mod.DirectoryError):
        directory_mod._clean_name(42, field="legal_address")

    with pytest.raises(directory_mod.DirectoryError):
        directory_mod._clean_name("я" * 400, field="legal_address")


def test_fingerprint_ids_are_restricted():
    assert directory_mod._check_fingerprint_id("83_v33") == "83_v33"
    assert directory_mod._check_fingerprint_id("78-2.v1") == "78-2.v1"

    for bad in ["", "83 v33", "83;drop table photos", "я" * 5, "a" * 65, None, 7]:
        with pytest.raises(directory_mod.DirectoryError):
            directory_mod._check_fingerprint_id(bad)


def test_create_address_needs_at_least_one_name():
    with pytest.raises(directory_mod.DirectoryError):
        directory_mod.create_address(legal_address="  ", simple_address="")


def test_create_address_rejects_a_bad_sort_order():
    with pytest.raises(directory_mod.DirectoryError):
        directory_mod.create_address(legal_address="ул. Мира, 1", sort_order="many")


def test_set_fingerprints_requires_a_list():
    with pytest.raises(directory_mod.DirectoryError):
        directory_mod.set_fingerprints(1, "83_v33")


# ---- lifecycle (database) ----


@requires_directory
def test_address_lifecycle(cleanup_addresses):
    created = directory_mod.create_address(
        legal_address="ООО «Ромашка», ул. Мира, 1",
        simple_address="Мира 1",
        sort_order=10,
    )
    cleanup_addresses.append(created["address_id"])

    assert created["legal_address"] == "ООО «Ромашка», ул. Мира, 1"
    assert created["simple_address"] == "Мира 1"
    assert created["fingerprints"] == []

    listed = directory_mod.list_addresses()
    assert any(
        item["address_id"] == created["address_id"] for item in listed
    )

    updated = directory_mod.update_address(
        created["address_id"],
        simple_address="Мира, 1",
    )
    assert updated["simple_address"] == "Мира, 1"
    assert updated["legal_address"] == created["legal_address"]

    assert directory_mod.update_address(10**9, simple_address="нет") is None

    assert directory_mod.delete_address(created["address_id"]) is True
    assert directory_mod.delete_address(created["address_id"]) is False


@requires_directory
def test_duplicate_legal_name_is_refused(cleanup_addresses):
    first = directory_mod.create_address(
        legal_address="ООО «Дубль», ул. Садовая, 7"
    )
    cleanup_addresses.append(first["address_id"])

    # Same name, different spacing/case: still the same address.
    with pytest.raises(directory_mod.DirectoryError):
        directory_mod.create_address(
            legal_address="ооо «дубль»,  ул. садовая, 7"
        )


@requires_directory
def test_fingerprints_are_moved_between_addresses(cleanup_addresses):
    left = directory_mod.create_address(legal_address="Адрес А")
    right = directory_mod.create_address(legal_address="Адрес Б")
    cleanup_addresses.extend([left["address_id"], right["address_id"]])

    mapped = directory_mod.set_fingerprints(left["address_id"], ["900_v33"])
    assert mapped["fingerprints"] == ["900_v33"]

    # The same id on another address moves instead of being duplicated.
    moved = directory_mod.set_fingerprints(right["address_id"], ["900_v33"])
    assert moved["fingerprints"] == ["900_v33"]

    left_after = directory_mod.get_address(left["address_id"])
    assert left_after["fingerprints"] == []

    # An empty list unmaps everything for that address.
    assert directory_mod.set_fingerprints(right["address_id"], [])[
        "fingerprints"
    ] == []

    assert directory_mod.set_fingerprints(10**9, ["900_v33"]) is None


@requires_directory
def test_photo_rows_carry_the_directory_names(cleanup_addresses):
    """The recognised id on a photo resolves to legal/simple address."""

    from app.api import repository

    # `address` is computed from the recognition pipeline, not stored on the
    # photo row, so pick a recognised photo through the API query itself.
    items, _cursor = repository.list_photos(limit=50)
    recognised = next((item for item in items if item.address), None)

    if recognised is None:
        pytest.skip("no recognised photo in the database")

    photo_id, fingerprint_id = recognised.photo_id, recognised.address

    before = repository.get_photo(photo_id)
    assert before.legal_address is None

    address = directory_mod.create_address(
        legal_address="Юридический адрес для теста",
        simple_address="Тестовый",
    )
    cleanup_addresses.append(address["address_id"])
    directory_mod.set_fingerprints(address["address_id"], [fingerprint_id])

    after = repository.get_photo(photo_id)
    assert after.legal_address == "Юридический адрес для теста"
    assert after.simple_address == "Тестовый"
    assert after.address == fingerprint_id


# ---- endpoints ----


def test_directory_endpoints_require_authentication():
    """Auth is fail-closed: without a credential the directory is not readable."""

    from app.api import auth

    if not auth.auth_enabled():
        pytest.skip("authentication is disabled in this test session")

    assert client.get("/api/v1/addresses/directory").status_code == 401


def test_directory_endpoint_returns_items():
    response = client.get("/api/v1/addresses/directory")

    assert response.status_code == 200
    assert isinstance(response.json()["items"], list)


@requires_directory
def test_create_address_endpoint_validates_input():
    response = client.post(
        "/api/v1/addresses/directory",
        json={"legal_address": "  ", "simple_address": ""},
    )

    assert response.status_code == 400
    assert "address" in response.json()["detail"]


@requires_directory
def test_address_endpoints_round_trip(cleanup_addresses):
    created = client.post(
        "/api/v1/addresses/directory",
        json={"legal_address": "Эндпоинт, д. 1", "simple_address": "Эндпоинт"},
    )

    assert created.status_code == 201
    address_id = created.json()["address_id"]
    cleanup_addresses.append(address_id)

    mapped = client.put(
        f"/api/v1/addresses/directory/{address_id}/fingerprints",
        json={"fingerprints": ["901_v33"]},
    )
    assert mapped.status_code == 200
    assert mapped.json()["fingerprints"] == ["901_v33"]

    updated = client.put(
        f"/api/v1/addresses/directory/{address_id}",
        json={"simple_address": "Эндпоинт 1"},
    )
    assert updated.status_code == 200
    assert updated.json()["simple_address"] == "Эндпоинт 1"

    missing = client.put(
        "/api/v1/addresses/directory/999999999",
        json={"simple_address": "нет"},
    )
    assert missing.status_code == 404

    deleted = client.delete(f"/api/v1/addresses/directory/{address_id}")
    assert deleted.status_code == 200
    cleanup_addresses.remove(address_id)

    again = client.delete(f"/api/v1/addresses/directory/{address_id}")
    assert again.status_code == 404
