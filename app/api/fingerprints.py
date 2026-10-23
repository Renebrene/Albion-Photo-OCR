"""
Fingerprint registry (schema/023): names, descriptions, versions, archiving.

The vectors stay where they are - data/fingerprints/<id>/, with metadata.json
as the source of truth for what a fingerprint contains (photo count, saved file
names, algorithm version). This module mirrors that into PostgreSQL so the UI
can name a fingerprint, describe it, archive it and keep a version journal
without the API re-reading the disk for every row.

Nothing here writes vectors or changes recognition: sync_from_disk() only reads
metadata.json, and the registry tables can be rebuilt from the disk at any
time. The human fields (display_name, description, source_folder, active) live
only in the database.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from app.api.config import FINGERPRINTS_ROOT, FINGERPRINT_PREVIEW_NAME
from app.ingest.database import get_connection

FINGERPRINT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

MAX_NAME_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000
MAX_SOURCE_FOLDER_LENGTH = 1000


class FingerprintError(ValueError):
    """A request the registry refuses (bad id, unknown row, bad value)."""


def _check_id(fingerprint_id: object) -> str:
    if not isinstance(fingerprint_id, str) or not FINGERPRINT_ID_RE.match(
        fingerprint_id
    ):
        raise FingerprintError("fingerprint id has an unexpected format")

    return fingerprint_id


def _text(value: object, *, field: str, limit: int) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        raise FingerprintError(f"{field} must be a string")

    text = " ".join(value.split())

    if len(text) > limit:
        raise FingerprintError(f"{field} is too long")

    return text


# ---------------------------------------------------------------------------
# disk -> registry
# ---------------------------------------------------------------------------


def _read_metadata(directory: Path) -> dict | None:
    metadata_file = directory / "metadata.json"

    if not metadata_file.is_file():
        return None

    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    if not isinstance(metadata, dict):
        return None

    names = metadata.get("image_names")
    names = [str(name) for name in names] if isinstance(names, list) else []

    # schema/024: the builder records each source photo with its capture date,
    # because the originals are not kept anywhere.
    meta = metadata.get("image_meta")
    meta = meta if isinstance(meta, list) else []

    cleaned_meta = [
        {
            "name": str(item.get("name")),
            "taken_at": item.get("taken_at"),
        }
        for item in meta
        if isinstance(item, dict) and item.get("name")
    ]

    return {
        "fingerprint_id": directory.name,
        "algorithm_version": metadata.get("version"),
        "model": metadata.get("model"),
        "dimension": metadata.get("dimension"),
        "images_count": int(metadata.get("images") or len(names) or 0),
        "image_names": names,
        "image_meta": cleaned_meta,
        "source_folder": metadata.get("source_folder"),
    }


def disk_inventory() -> list[dict]:
    """Every fingerprint directory on disk that has a readable metadata.json."""

    root = Path(FINGERPRINTS_ROOT)

    if not root.is_dir():
        return []

    items: list[dict] = []

    for directory in sorted(root.iterdir()):
        if not directory.is_dir() or directory.name.startswith("."):
            continue

        metadata = _read_metadata(directory)

        if metadata is not None:
            items.append(metadata)

    return items


def sync_from_disk() -> dict:
    """
    Insert/refresh registry rows and append a version when a fingerprint was
    rebuilt with a different set of photos.

    Idempotent: running it twice in a row inserts nothing the second time. A
    version row is added only when the photo count or the saved file names
    differ from the current version, so a plain re-scan does not spam history.
    """

    inventory = disk_inventory()
    added_versions: list[str] = []
    created: list[str] = []
    updated: list[str] = []

    with get_connection() as conn:
        with conn.cursor() as cur:
            for item in inventory:
                fingerprint_id = item["fingerprint_id"]

                cur.execute(
                    "SELECT 1 FROM public.fingerprints WHERE fingerprint_id = %s",
                    (fingerprint_id,),
                )
                exists = cur.fetchone() is not None

                if exists:
                    cur.execute(
                        """
                        UPDATE public.fingerprints
                        SET algorithm_version = COALESCE(%s, algorithm_version),
                            model = COALESCE(%s, model),
                            dimension = COALESCE(%s, dimension),
                            images_count = %s,
                            -- Fill the source folder only when it is empty: a
                            -- manual edit in the window wins over the disk.
                            source_folder = COALESCE(source_folder, %s),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE fingerprint_id = %s
                        """,
                        (
                            item["algorithm_version"],
                            item["model"],
                            item["dimension"],
                            item["images_count"],
                            item.get("source_folder"),
                            fingerprint_id,
                        ),
                    )
                    updated.append(fingerprint_id)
                else:
                    cur.execute(
                        """
                        INSERT INTO public.fingerprints
                            (fingerprint_id, algorithm_version, model,
                             dimension, images_count, source_folder)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            fingerprint_id,
                            item["algorithm_version"],
                            item["model"],
                            item["dimension"],
                            item["images_count"],
                            item.get("source_folder"),
                        ),
                    )
                    created.append(fingerprint_id)

                cur.execute(
                    """
                    SELECT images_count, image_names
                    FROM public.fingerprint_versions
                    WHERE fingerprint_id = %s AND is_current
                    """,
                    (fingerprint_id,),
                )
                current = cur.fetchone()

                if current is not None:
                    same_count = int(current[0]) == item["images_count"]
                    stored_names = current[1] or []
                    same_names = list(stored_names) == item["image_names"]

                    if same_count and same_names:
                        # Keep the capture dates fresh on an unchanged set too.
                        if item.get("image_meta"):
                            cur.execute(
                                """
                                UPDATE public.fingerprint_versions
                                SET images_meta = %s
                                WHERE fingerprint_id = %s AND is_current
                                """,
                                (
                                    json.dumps(item["image_meta"]),
                                    fingerprint_id,
                                ),
                            )
                        continue

                    cur.execute(
                        """
                        UPDATE public.fingerprint_versions
                        SET is_current = FALSE
                        WHERE fingerprint_id = %s AND is_current
                        """,
                        (fingerprint_id,),
                    )

                cur.execute(
                    """
                    INSERT INTO public.fingerprint_versions
                        (fingerprint_id, algorithm_version, images_count,
                         image_names, images_meta, source_folder, is_current)
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                    """,
                    (
                        fingerprint_id,
                        item["algorithm_version"],
                        item["images_count"],
                        json.dumps(item["image_names"]),
                        json.dumps(item.get("image_meta") or []),
                        item.get("source_folder"),
                    ),
                )
                added_versions.append(fingerprint_id)

    return {
        "on_disk": len(inventory),
        "created": created,
        "updated": updated,
        "versions_added": added_versions,
    }


# ---------------------------------------------------------------------------
# registry reads
# ---------------------------------------------------------------------------


def resolve_name(
    display_name: object,
    simple_address: object,
    legal_address: object,
    fingerprint_id: str,
) -> str:
    """
    The name a fingerprint is shown by.

    A name typed by hand wins; otherwise the alias of the address the
    fingerprint is mapped to is used - that is where people keep the short name
    of an address. Without an alias the legal address is the fallback, and a
    fingerprint with no address at all keeps its technical id.
    """

    for value in (display_name, simple_address, legal_address):
        if isinstance(value, str) and value.strip():
            return value.strip()

    return fingerprint_id


def _row_to_fingerprint(row) -> dict:
    return {
        "fingerprint_id": row[0],
        "display_name": row[1],
        # display_name resolved against the address directory (see above); the
        # window shows this, display_name stays the stored human field.
        "name": resolve_name(row[1], row[13], row[12], row[0]),
        "description": row[2],
        "algorithm_version": row[3],
        "model": row[4],
        "dimension": row[5],
        "images_count": int(row[6]),
        "source_folder": row[7],
        "active": bool(row[8]),
        "created_at": row[9],
        "updated_at": row[10],
        "address": {
            "address_id": row[11],
            "legal_address": row[12],
            "simple_address": row[13],
        }
        if row[11] is not None
        else None,
        "current_version": {
            "images_count": int(row[14]) if row[14] is not None else None,
            "created_at": row[15],
        }
        if row[14] is not None
        else None,
    }


_REGISTRY_SELECT = """
    SELECT
        f.fingerprint_id, f.display_name, f.description, f.algorithm_version,
        f.model, f.dimension, f.images_count, f.source_folder, f.active,
        f.created_at, f.updated_at,
        d.address_id, d.legal_address, d.simple_address,
        v.images_count, v.created_at
    FROM public.fingerprints AS f
    LEFT JOIN public.address_fingerprints AS af
           ON af.fingerprint_id = f.fingerprint_id AND af.active
    LEFT JOIN public.address_directory AS d
           ON d.address_id = af.address_id AND d.active
    LEFT JOIN public.fingerprint_versions AS v
           ON v.fingerprint_id = f.fingerprint_id AND v.is_current
"""


def list_registry() -> list[dict]:
    """Registry rows with their address and current version."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_REGISTRY_SELECT + " ORDER BY f.fingerprint_id")
            rows = cur.fetchall()

    on_disk = {item["fingerprint_id"] for item in disk_inventory()}

    items = []

    for row in rows:
        item = _row_to_fingerprint(row)
        item["on_disk"] = item["fingerprint_id"] in on_disk
        items.append(item)

    return items


def active_fingerprint_ids() -> set[str] | None:
    """
    Fingerprints that may take part in recognition.

    Returns ``None`` when the registry is empty or unavailable: an older
    database without schema/023 must keep the previous disk-only behaviour
    instead of suddenly recognising nothing.
    """

    try:
        rows = list_registry()
    except Exception:
        return None

    if not rows:
        return None

    return {
        str(item["fingerprint_id"])
        for item in rows
        if item.get("active")
    }


def get_fingerprint(fingerprint_id: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _REGISTRY_SELECT + " WHERE f.fingerprint_id = %s",
                (_check_id(fingerprint_id),),
            )
            row = cur.fetchone()

    return _row_to_fingerprint(row) if row is not None else None


def preview_path(fingerprint_id: str) -> Path | None:
    """
    The montage stored with a fingerprint, or None when it has none.

    The path is built from the validated id inside the fingerprints root, so a
    request cannot aim it anywhere else. Fingerprints built before previews
    existed have none until they are rebuilt (scripts/backfill_fingerprint_previews.py
    makes one from the source folder while it still exists).
    """

    fingerprint_id = _check_id(fingerprint_id)

    path = Path(FINGERPRINTS_ROOT) / fingerprint_id / FINGERPRINT_PREVIEW_NAME

    return path if path.is_file() else None


def list_versions(fingerprint_id: str) -> list[dict] | None:
    """Version journal, newest first; None when the fingerprint is unknown."""

    fingerprint_id = _check_id(fingerprint_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM public.fingerprints WHERE fingerprint_id = %s",
                (fingerprint_id,),
            )

            if cur.fetchone() is None:
                return None

            cur.execute(
                """
                SELECT version_id, algorithm_version, images_count,
                       image_names, images_meta, source_folder, is_current,
                       created_at, recreated_at
                FROM public.fingerprint_versions
                WHERE fingerprint_id = %s
                ORDER BY created_at DESC, version_id DESC
                """,
                (fingerprint_id,),
            )
            rows = cur.fetchall()

    return [
        {
            "version_id": int(row[0]),
            "algorithm_version": row[1],
            "images_count": int(row[2]),
            "image_names": list(row[3] or []),
            "images_meta": list(row[4] or []),
            "source_folder": row[5],
            "is_current": bool(row[6]),
            "created_at": row[7],
            "recreated_at": row[8],
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# registry writes (human fields only)
# ---------------------------------------------------------------------------


def update_fingerprint(
    fingerprint_id: str,
    *,
    display_name: object = None,
    description: object = None,
    active: object = None,
    source_folder: object = None,
) -> dict | None:
    """Update the supplied human fields; None fields keep their value."""

    fingerprint_id = _check_id(fingerprint_id)

    assignments: list[str] = []
    params: list[object] = []

    if display_name is not None:
        assignments.append("display_name = %s")
        params.append(_text(display_name, field="display_name", limit=MAX_NAME_LENGTH))

    if description is not None:
        assignments.append("description = %s")
        params.append(
            _text(description, field="description", limit=MAX_DESCRIPTION_LENGTH)
        )

    if source_folder is not None:
        assignments.append("source_folder = %s")
        params.append(
            _text(
                source_folder,
                field="source_folder",
                limit=MAX_SOURCE_FOLDER_LENGTH,
            )
        )

    if active is not None:
        assignments.append("active = %s")
        params.append(bool(active))

    if not assignments:
        return get_fingerprint(fingerprint_id)

    assignments.append("updated_at = CURRENT_TIMESTAMP")
    params.append(fingerprint_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.fingerprints SET "
                + ", ".join(assignments)
                + " WHERE fingerprint_id = %s",
                params,
            )

            if cur.rowcount != 1:
                return None

    return get_fingerprint(fingerprint_id)


def _active_recognition_jobs(cur, fingerprint_id: str) -> int:
    """Recognition or a rebuild currently using the registry."""

    cur.execute(
        """
        SELECT count(*)
        FROM public.job_queue
        WHERE status IN ('PENDING', 'RUNNING', 'PAUSED')
          AND (
              job_type IN ('DINO_BATCH', 'HYBRID_RUN')
              OR (
                  job_type = 'FINGERPRINT_BUILD'
                  AND payload ->> 'fingerprint_id' = %s
              )
          )
        """,
        (fingerprint_id,),
    )
    return int(cur.fetchone()[0])


def delete_fingerprint(fingerprint_id: str) -> dict | None:
    """
    Remove one fingerprint completely: registry row, address link, files.

    Historical DINO/HYBRID rows keep the id as text; they are results of past
    runs and are left untouched. Recognition must not be running while the
    vectors disappear, so an active DINO/HYBRID/rebuild job blocks the call.
    """

    fingerprint_id = _check_id(fingerprint_id)
    root = Path(FINGERPRINTS_ROOT).resolve()
    target = (root / fingerprint_id).resolve()

    if target.parent != root:
        raise FingerprintError("unsafe fingerprint path")

    with get_connection() as conn:
        with conn.cursor() as cur:
            if _active_recognition_jobs(cur, fingerprint_id):
                raise FingerprintError(
                    "recognition or a fingerprint rebuild is running; "
                    "stop it before deleting"
                )

            cur.execute(
                "SELECT fingerprint_id FROM public.fingerprints "
                "WHERE fingerprint_id = %s",
                (fingerprint_id,),
            )

            if cur.fetchone() is None:
                return None

            cur.execute(
                "DELETE FROM public.address_fingerprints "
                "WHERE fingerprint_id = %s",
                (fingerprint_id,),
            )
            cur.execute(
                "DELETE FROM public.fingerprints WHERE fingerprint_id = %s",
                (fingerprint_id,),
            )

    removed = 0

    if target.is_dir():
        removed = sum(1 for path in target.rglob("*") if path.is_file())

        try:
            shutil.rmtree(target)
        except OSError as exc:
            return {
                "fingerprint_id": fingerprint_id,
                "files_removed": 0,
                "files_total": removed,
                "error": f"registry row removed, files left: {type(exc).__name__}",
            }

    return {
        "fingerprint_id": fingerprint_id,
        "files_removed": removed,
        "files_total": removed,
        "error": None,
    }


def address_label(simple_address: object, legal_address: object) -> str:
    """The short name of a directory row: the alias, else the legal name."""

    for value in (simple_address, legal_address):
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def set_address(fingerprint_id: str, address_id: int | None) -> dict | None:
    """
    Map a fingerprint to an address from the directory, or clear the mapping.

    The fingerprint id is the primary key of address_fingerprints, so a
    fingerprint belongs to exactly one address: mapping it elsewhere moves it.

    The name follows the address: picking one writes its alias into
    display_name straight away, so the name is stored and not only resolved at
    read time. A name typed by hand is left alone, and the mapping only clears
    the name it wrote itself (the alias of the address being removed).

    Returns the refreshed registry row, or None when the fingerprint is unknown.
    """

    fingerprint_id = _check_id(fingerprint_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT display_name FROM public.fingerprints "
                "WHERE fingerprint_id = %s",
                (fingerprint_id,),
            )
            row = cur.fetchone()

            if row is None:
                return None

            stored_name = (row[0] or "").strip()

            # The alias of the address the fingerprint sits on now: that is the
            # name we wrote last time, so replacing it loses nothing.
            cur.execute(
                """
                SELECT d.simple_address, d.legal_address
                FROM public.address_fingerprints AS af
                JOIN public.address_directory AS d
                  ON d.address_id = af.address_id
                WHERE af.fingerprint_id = %s
                """,
                (fingerprint_id,),
            )
            previous = cur.fetchone()
            previous_label = (
                address_label(previous[0], previous[1]) if previous else ""
            )

            if address_id is None:
                cur.execute(
                    "DELETE FROM public.address_fingerprints "
                    "WHERE fingerprint_id = %s",
                    (fingerprint_id,),
                )
                new_label = ""
            else:
                cur.execute(
                    "SELECT simple_address, legal_address "
                    "FROM public.address_directory WHERE address_id = %s",
                    (int(address_id),),
                )
                target = cur.fetchone()

                if target is None:
                    raise FingerprintError("адрес не найден")

                new_label = address_label(target[0], target[1])

                cur.execute(
                    """
                    INSERT INTO public.address_fingerprints
                        (fingerprint_id, address_id)
                    VALUES (%s, %s)
                    ON CONFLICT (fingerprint_id) DO UPDATE
                       SET address_id = EXCLUDED.address_id,
                           updated_at = CURRENT_TIMESTAMP
                    """,
                    (fingerprint_id, int(address_id)),
                )

            # Only a name we put there ourselves (or no name at all) is replaced.
            if stored_name in ("", previous_label) and stored_name != new_label:
                cur.execute(
                    "UPDATE public.fingerprints "
                    "SET display_name = %s, updated_at = CURRENT_TIMESTAMP "
                    "WHERE fingerprint_id = %s",
                    (new_label, fingerprint_id),
                )

    return get_fingerprint(fingerprint_id)
