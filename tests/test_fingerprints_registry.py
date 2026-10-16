"""
Fingerprint registry (schema/023): names, versions, archiving.

Validation is pure; the tests that touch rows skip unless PostgreSQL is
configured. Renames are reverted at the end so the registry keeps its state.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.api import fingerprints as fp
from app.api.main import app

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.fingerprints')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


requires_registry = pytest.mark.skipif(
    not _db_available(),
    reason="schema/023 (fingerprints) is not applied",
)


# Тесты, которые пишут в человеческие поля слепка (имя, описание, папка), берут
# временную строку из фикстуры `probe_fingerprints` (tests/conftest.py).
# Раньше они работали на первом слепке реестра и «восстанавливали» его в пустое
# состояние — так у реального 76_v33 пропадало имя.


# ---- validation ----


def test_resolve_name_falls_back_to_alias_then_legal_then_id():
    """The order the window, the grid and the address panel all rely on."""

    assert fp.resolve_name("", "Мира 1", "ООО «Ромашка»", "78_v33") == "Мира 1"
    assert fp.resolve_name("Своё имя", "Мира 1", "ООО «Ромашка»", "78_v33") == "Своё имя"
    assert fp.resolve_name("", "", "ООО «Ромашка»", "78_v33") == "ООО «Ромашка»"
    assert fp.resolve_name("", None, None, "78_v33") == "78_v33"
    # Whitespace is not a name.
    assert fp.resolve_name("  ", " ", None, "78_v33") == "78_v33"


def test_ids_are_restricted():
    assert fp._check_id("78_v33") == "78_v33"

    for bad in ["", "78 v33", "drop;table", "я" * 5, None, 7, "a" * 65]:
        with pytest.raises(fp.FingerprintError):
            fp._check_id(bad)


def test_text_fields_are_normalised_and_bounded():
    assert fp._text("  ООО   «Ромашка»  ", field="display_name", limit=200) == (
        "ООО «Ромашка»"
    )
    assert fp._text(None, field="description", limit=10) == ""

    with pytest.raises(fp.FingerprintError):
        fp._text("я" * 300, field="description", limit=10)

    with pytest.raises(fp.FingerprintError):
        fp._text(42, field="display_name", limit=10)


def test_update_rejects_a_bad_id_before_touching_the_database():
    with pytest.raises(fp.FingerprintError):
        fp.update_fingerprint("bad id", display_name="x")


# ---- disk inventory ----


def test_disk_inventory_reads_the_fingerprints_directory():
    items = fp.disk_inventory()

    if not items:
        pytest.skip("no fingerprints on disk")

    first = items[0]
    assert first["fingerprint_id"]
    assert first["images_count"] > 0
    assert isinstance(first["image_names"], list)
    assert first["algorithm_version"]


# ---- registry (database) ----


@requires_registry
def test_sync_is_idempotent():
    first = fp.sync_from_disk()
    second = fp.sync_from_disk()

    assert first["on_disk"] > 0
    assert second["versions_added"] == []
    assert second["created"] == []


@requires_registry
def test_a_rebuilt_fingerprint_appends_a_version(monkeypatch):
    """A different photo set becomes a new current version, keeping history."""

    inventory = fp.disk_inventory()
    target = inventory[0]
    fingerprint_id = target["fingerprint_id"]

    before = fp.list_versions(fingerprint_id)
    assert before, "the fingerprint should already have a version row"

    def bigger():
        item = dict(target)
        item["images_count"] = target["images_count"] + 5
        item["image_names"] = target["image_names"] + ["new_photo.JPG"]
        return [item]

    monkeypatch.setattr(fp, "disk_inventory", bigger)

    result = fp.sync_from_disk()
    assert fingerprint_id in result["versions_added"]

    after = fp.list_versions(fingerprint_id)
    assert len(after) == len(before) + 1
    assert after[0]["is_current"] is True
    assert after[0]["images_count"] == target["images_count"] + 5
    assert sum(1 for version in after if version["is_current"]) == 1

    # Clean the extra version up again.
    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.fingerprint_versions WHERE version_id = %s",
                (after[0]["version_id"],),
            )
            cur.execute(
                """
                UPDATE public.fingerprint_versions
                SET is_current = TRUE
                WHERE version_id = %s
                """,
                (after[1]["version_id"],),
            )
            cur.execute(
                """
                UPDATE public.fingerprints
                SET images_count = %s
                WHERE fingerprint_id = %s
                """,
                (target["images_count"], fingerprint_id),
            )


@requires_registry
def test_rename_describe_archive_round_trip(probe_fingerprints):
    fingerprint_id = probe_fingerprints[0]

    updated = fp.update_fingerprint(
        fingerprint_id,
        display_name="Комарова 13",
        description="Слепок для проверки",
        source_folder="data/input/78",
        active=False,
    )

    assert updated["display_name"] == "Комарова 13"
    assert updated["description"] == "Слепок для проверки"
    assert updated["source_folder"] == "data/input/78"
    assert updated["active"] is False

    # An unknown id is reported as missing, not as a validation error.
    # (900_v33 — заведомо несуществующий id; 998/999_v33 заняты временными
    # строками фикстуры `probe_fingerprints`.)
    assert fp.update_fingerprint("900_v33", display_name="нет") is None
    assert fp.list_versions("900_v33") is None


@requires_registry
def test_registry_rows_carry_disk_and_version_state():
    items = fp.list_registry()

    if not items:
        pytest.skip("registry is empty")

    for item in items:
        assert item["on_disk"] is True
        assert item["images_count"] > 0
        assert item["current_version"] is not None
        assert item["current_version"]["images_count"] == item["images_count"]
        # No address is mapped by default; the directory fills this in.
        assert "address" in item


@requires_registry
def test_mapping_an_address_names_the_fingerprint(probe_fingerprints):
    """
    Choosing a legal address writes its alias into the fingerprint's name right
    away, so the name is stored and not only resolved when the row is read. A
    name typed by hand survives a later mapping, and removing the address
    removes only the name the mapping itself wrote.

    The temporary address (and its mapping) is removed afterwards.
    """

    from app.api import directory as directory_mod

    fingerprint_id = probe_fingerprints[0]

    # No address yet: the name is the technical id.
    fresh = fp.get_fingerprint(fingerprint_id)
    assert fresh["name"] == fingerprint_id
    assert fresh["display_name"] == ""

    address = directory_mod.create_address(
        legal_address="Тестовая ул. 1, A",
        simple_address="Тестовая 1",
    )

    try:
        mapped = fp.set_address(fingerprint_id, address["address_id"])

        assert mapped["display_name"] == "Тестовая 1"
        assert mapped["name"] == "Тестовая 1"

        # A name typed by hand is not replaced by re-mapping the same address.
        fp.update_fingerprint(fingerprint_id, display_name="Своё имя")
        again = fp.set_address(fingerprint_id, address["address_id"])

        assert again["display_name"] == "Своё имя"
        assert again["name"] == "Своё имя"

        # An address without an alias falls back to its legal name.
        directory_mod.update_address(address["address_id"], simple_address="")
        fp.update_fingerprint(fingerprint_id, display_name="")

        assert fp.get_fingerprint(fingerprint_id)["name"] == "Тестовая ул. 1, A"

        # Unmapping clears the name the mapping wrote, leaving the id.
        directory_mod.update_address(
            address["address_id"], simple_address="Тестовая 1"
        )
        fp.set_address(fingerprint_id, address["address_id"])
        cleared = fp.set_address(fingerprint_id, None)

        assert cleared["display_name"] == ""
        assert cleared["name"] == fingerprint_id
    finally:
        fp.set_address(fingerprint_id, None)
        directory_mod.delete_address(address["address_id"])


@requires_registry
def test_renaming_an_alias_renames_the_fingerprint(probe_fingerprints):
    """
    The name a fingerprint copied from its address follows the directory: the
    alias is the single place to rename, a hand-typed name is never touched.
    """

    from app.api import directory as directory_mod

    fingerprint_id = probe_fingerprints[0]

    address = directory_mod.create_address(
        legal_address="Тестовая ул. 3, A",
        simple_address="Тестовая 3",
    )

    try:
        fp.set_address(fingerprint_id, address["address_id"])
        assert fp.get_fingerprint(fingerprint_id)["display_name"] == "Тестовая 3"

        directory_mod.update_address(
            address["address_id"], simple_address="Тестовая 3А"
        )
        assert fp.get_fingerprint(fingerprint_id)["display_name"] == "Тестовая 3А"

        # A hand-typed name is not dragged along.
        fp.update_fingerprint(fingerprint_id, display_name="Своё имя")
        directory_mod.update_address(
            address["address_id"], simple_address="Тестовая 3Б"
        )
        assert fp.get_fingerprint(fingerprint_id)["display_name"] == "Своё имя"
    finally:
        fp.set_address(fingerprint_id, None)
        directory_mod.delete_address(address["address_id"])


def test_preview_path_comes_from_the_validated_id(tmp_path, monkeypatch):
    """The montage is looked up inside the fingerprints root, never elsewhere."""

    monkeypatch.setattr(fp, "FINGERPRINTS_ROOT", tmp_path)

    (tmp_path / "78_v33").mkdir()
    saved = tmp_path / "78_v33" / "preview.jpg"
    saved.write_bytes(b"\xff\xd8\xff\xe0")

    assert fp.preview_path("78_v33") == saved

    # Built before previews existed: nothing saved yet.
    (tmp_path / "90_v33").mkdir()
    assert fp.preview_path("90_v33") is None

    with pytest.raises(fp.FingerprintError):
        fp.preview_path("../etc/passwd")


def test_preview_endpoint_serves_the_saved_montage(tmp_path, monkeypatch):
    monkeypatch.setattr(fp, "FINGERPRINTS_ROOT", tmp_path)

    (tmp_path / "78_v33").mkdir()
    (tmp_path / "78_v33" / "preview.jpg").write_bytes(b"\xff\xd8\xff\xe0preview")

    found = client.get("/api/v1/fingerprints/registry/78_v33/preview")

    assert found.status_code == 200
    assert found.headers["content-type"] == "image/jpeg"
    assert found.content.startswith(b"\xff\xd8\xff")
    # Rebuilding keeps the id, so the browser must not cache the picture.
    assert found.headers["cache-control"] == "no-cache"

    missing = client.get("/api/v1/fingerprints/registry/90_v33/preview")
    assert missing.status_code == 404


# ---- endpoints ----


@requires_registry
def test_registry_endpoints():
    listed = client.get("/api/v1/fingerprints/registry")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert items

    fingerprint_id = items[0]["fingerprint_id"]

    one = client.get(f"/api/v1/fingerprints/registry/{fingerprint_id}")
    assert one.status_code == 200
    assert one.json()["fingerprint_id"] == fingerprint_id

    versions = client.get(
        f"/api/v1/fingerprints/registry/{fingerprint_id}/versions"
    )
    assert versions.status_code == 200
    assert versions.json()["items"]

    missing = client.get("/api/v1/fingerprints/registry/999_v33")
    assert missing.status_code == 404

    bad = client.put(
        "/api/v1/fingerprints/registry/999_v33",
        json={"display_name": "нет"},
    )
    assert bad.status_code == 404


@requires_registry
def test_sync_endpoint_is_available():
    """The sync route exists and is guarded like the other maintenance calls."""

    response = client.post("/api/v1/fingerprints/sync")

    # Either it ran (auth disabled in tests) or the scope stopped it.
    assert response.status_code in {200, 401, 403}
