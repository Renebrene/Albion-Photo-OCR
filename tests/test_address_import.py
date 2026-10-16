"""
Importing legal addresses from a spreadsheet and mapping a fingerprint to one.

Parsing is pure; the tests that write rows skip unless PostgreSQL is configured
and clean up everything they created (imported addresses and the mapping).
"""

from __future__ import annotations

import io
import os

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.api import directory as directory_mod
from app.api import fingerprints as fingerprints_mod
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)

PREFIX = "ТЕСТ-ИМПОРТ "


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


def _xlsx(rows: list[list[str]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active

    for row in rows:
        sheet.append(row)

    buffer = io.BytesIO()
    workbook.save(buffer)

    return buffer.getvalue()


@pytest.fixture
def cleanup_imported():
    """Delete every address this test created (and its mappings)."""

    yield

    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.address_directory WHERE legal_address LIKE %s",
                (PREFIX + "%",),
            )


# ---- parsing ----


def test_parses_an_xlsx_with_russian_headers():
    content = _xlsx(
        [
            ["Юридический адрес", "Упрощённый адрес"],
            ["ООО «Ромашка», ул. Мира, 1", "Мира 1"],
            ["ООО «Тюльпан», ул. Садовая, 7", ""],
        ]
    )

    items = directory_mod.parse_address_table(content, "адреса.xlsx")

    assert items == [
        {"legal_address": "ООО «Ромашка», ул. Мира, 1", "simple_address": "Мира 1"},
        {"legal_address": "ООО «Тюльпан», ул. Садовая, 7", "simple_address": ""},
    ]


def test_parses_english_headers_in_any_order():
    content = _xlsx(
        [
            ["simple_address", "legal_address"],
            ["Мира 1", "ООО «Ромашка»"],
        ]
    )

    items = directory_mod.parse_address_table(content, "addresses.xlsx")

    assert items == [
        {"legal_address": "ООО «Ромашка»", "simple_address": "Мира 1"},
    ]


def test_parses_a_table_without_headers():
    content = _xlsx([["ООО «Ромашка»", "Ромашка"]])

    items = directory_mod.parse_address_table(content, "no-header.xlsx")

    assert items == [
        {"legal_address": "ООО «Ромашка»", "simple_address": "Ромашка"},
    ]


def test_parses_csv_and_skips_empty_rows():
    content = "адрес,alias\nМира 1,М1\n,\nСадовая 7,С7\n".encode("utf-8")

    items = directory_mod.parse_address_table(content, "адреса.csv")

    assert items == [
        {"legal_address": "Мира 1", "simple_address": "М1"},
        {"legal_address": "Садовая 7", "simple_address": "С7"},
    ]


def test_rejects_an_unsupported_format():
    with pytest.raises(directory_mod.DirectoryError):
        directory_mod.parse_address_table(b"x", "адреса.pdf")


def test_rejects_a_broken_xlsx():
    with pytest.raises(directory_mod.DirectoryError):
        directory_mod.parse_address_table(b"not a zip", "адреса.xlsx")


# ---- import (database) ----


@requires_directory
def test_import_creates_updates_and_skips(cleanup_imported):
    first = directory_mod.import_addresses(
        [
            {
                "legal_address": f"{PREFIX}ул. Мира, 1",
                "simple_address": "Мира 1",
            },
            {
                "legal_address": f"{PREFIX}ул. Садовая, 7",
                "simple_address": "Садовая 7",
            },
            {"legal_address": "", "simple_address": ""},
        ]
    )

    assert first["created"] == 2
    assert first["skipped"] == 1

    # Second run: the same rows change nothing; a new simple name is applied.
    second = directory_mod.import_addresses(
        [
            {
                "legal_address": f"{PREFIX}ул. Мира, 1",
                "simple_address": "Мира 1",
            },
            {
                "legal_address": f"{PREFIX}ул. Садовая, 7",
                "simple_address": "Садовая, 7",
            },
        ]
    )

    assert second["created"] == 0
    assert second["updated"] == 1
    assert second["skipped"] == 1

    addresses = {
        item["legal_address"]: item
        for item in directory_mod.list_addresses()
        if item["legal_address"].startswith(PREFIX)
    }
    assert addresses[f"{PREFIX}ул. Садовая, 7"]["simple_address"] == "Садовая, 7"


@requires_directory
def test_import_matches_case_and_spacing(cleanup_imported):
    directory_mod.import_addresses(
        [{"legal_address": f"{PREFIX}ул. Мира, 1", "simple_address": ""}]
    )

    again = directory_mod.import_addresses(
        [{"legal_address": f"  {PREFIX}УЛ.  МИРА, 1 ", "simple_address": ""}]
    )

    assert again["created"] == 0
    assert again["skipped"] == 1


# ---- import endpoint ----


@requires_directory
def test_import_endpoint_accepts_an_xlsx(cleanup_imported):
    content = _xlsx(
        [
            ["Юридический адрес", "Упрощённый адрес"],
            [f"{PREFIX}ул. Полевая, 3", "Полевая 3"],
        ]
    )

    response = client.post(
        "/api/v1/addresses/import",
        files={
            "file": (
                "адреса.xlsx",
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 1
    assert body["created"] == 1


def test_import_endpoint_rejects_an_empty_file():
    response = client.post(
        "/api/v1/addresses/import",
        files={"file": ("пусто.csv", b"", "text/csv")},
    )

    assert response.status_code == 400


def test_import_endpoint_rejects_a_wrong_format():
    response = client.post(
        "/api/v1/addresses/import",
        files={"file": ("адреса.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 400


# ---- mapping a fingerprint to an address ----


@requires_directory
def test_fingerprint_can_be_mapped_to_an_address(cleanup_imported):
    items = fingerprints_mod.list_registry()

    if not items:
        pytest.skip("registry is empty")

    fingerprint_id = items[0]["fingerprint_id"]

    created = directory_mod.import_addresses(
        [{"legal_address": f"{PREFIX}для привязки", "simple_address": "Привязка"}]
    )
    assert created["created"] == 1

    address = next(
        item
        for item in directory_mod.list_addresses()
        if item["legal_address"] == f"{PREFIX}для привязки"
    )

    mapped = client.put(
        f"/api/v1/fingerprints/registry/{fingerprint_id}/address",
        json={"address_id": address["address_id"]},
    )

    assert mapped.status_code == 200
    assert mapped.json()["address"]["legal_address"] == f"{PREFIX}для привязки"

    cleared = client.put(
        f"/api/v1/fingerprints/registry/{fingerprint_id}/address",
        json={"address_id": None},
    )

    assert cleared.status_code == 200
    assert cleared.json()["address"] is None


@requires_directory
def test_mapping_to_an_unknown_address_is_refused():
    items = fingerprints_mod.list_registry()

    if not items:
        pytest.skip("registry is empty")

    response = client.put(
        f"/api/v1/fingerprints/registry/{items[0]['fingerprint_id']}/address",
        json={"address_id": 10**9},
    )

    assert response.status_code == 400


@requires_directory
def test_mapping_an_unknown_fingerprint_is_404():
    response = client.put(
        "/api/v1/fingerprints/registry/999_v33/address",
        json={"address_id": 1},
    )

    assert response.status_code == 404
