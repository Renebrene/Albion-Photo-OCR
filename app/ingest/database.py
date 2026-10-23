from __future__ import annotations

import os
import threading

import psycopg
from psycopg_pool import ConnectionPool

from app.ingest.register import PhotoRecord


def _conn_params() -> dict:
    """Connection parameters from the environment (no secrets in code)."""

    return {
        "host": os.getenv("INGEST_DB_HOST", "localhost"),
        "port": os.getenv("INGEST_DB_PORT", "5432"),
        "dbname": os.getenv("INGEST_DB_NAME", "photobase_ingest_test"),
        "user": os.getenv("INGEST_DB_USER", "lora_ingest"),
        "password": os.environ["INGEST_DB_PASSWORD"],
    }


def _pool_enabled() -> bool:
    return os.getenv("SCENE_DB_POOL", "1").strip().lower() not in {
        "0",
        "false",
        "no",
    }


# The pool lives in long-lived processes (API, worker). INGEST/PREVIEW fork via
# ProcessPoolExecutor: the child inherits the pool's connections, so it must not
# use them (and must not let them be garbage-collected, which would send a
# Terminate on the parent's socket). So the child only sets a flag and leaves
# the pool object referenced.
_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()
_pool_disabled_in_child = False


def _after_fork_child() -> None:  # pragma: no cover - fork side effect
    global _pool_disabled_in_child
    _pool_disabled_in_child = True


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_after_fork_child)


def _get_pool() -> ConnectionPool | None:
    global _pool

    if not _pool_enabled() or _pool_disabled_in_child:
        return None

    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ConnectionPool(
                    conninfo=psycopg.conninfo.make_conninfo(**_conn_params()),
                    min_size=int(os.getenv("SCENE_DB_POOL_MIN", "1")),
                    max_size=int(os.getenv("SCENE_DB_POOL_MAX", "10")),
                    open=True,
                    name="scene",
                )

    return _pool


def get_connection():
    """
    Return a connection context manager for the INGEST PostgreSQL database.

    With pooling enabled (default) the connection comes from a bounded pool
    and is committed/rolled back on context exit, exactly like a fresh
    ``psycopg.connect()``. Set SCENE_DB_POOL=0 to always open a new connection.
    """

    pool = _get_pool()

    if pool is None:
        return psycopg.connect(**_conn_params())

    return pool.connection()


def known_source_files(entries: list[tuple[str, int]]) -> set[tuple[str, int]]:
    """
    Which (filename, size_bytes) pairs are already registered.

    A cheap pre-filter for repeated folder scans: a match means this name and
    size are in the database, so the file does not have to be hashed again.
    It is a shortcut only - the sha256 identity check still decides what is
    written. Trade-off: a *different* file that happens to share both name and
    byte size with a registered one is skipped too, which is why callers may
    turn the shortcut off.
    """

    if not entries:
        return set()

    filenames = [name for name, _ in entries]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT filename, size_bytes
                FROM public.photos
                WHERE filename = ANY(%s)
                  AND size_bytes IS NOT NULL
                """,
                (filenames,),
            )
            stored = {(filename, size) for filename, size in cur.fetchall()}

    return stored & set(entries)


def check_identity_batch(
    records: list[PhotoRecord],
) -> dict[str, list[PhotoRecord]]:
    """
    Check database identity state without modifying the database.

    Returns records classified as:
      NEW       - neither photo_id nor sha256 exists
      EXISTING  - same photo_id already exists with the same sha256
      CONFLICT  - photo_id or sha256 exists with a different counterpart
    """
    result = {
        "NEW": [],
        "EXISTING": [],
        "CONFLICT": [],
    }

    if not records:
        return result

    photo_ids = [record.photo_id for record in records]
    sha256s = [record.sha256 for record in records]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, sha256
                FROM public.photos
                WHERE photo_id = ANY(%s)
                   OR sha256 = ANY(%s)
                """,
                (photo_ids, sha256s),
            )

            existing = cur.fetchall()

    by_photo_id = {photo_id: sha256 for photo_id, sha256 in existing}
    by_sha256 = {sha256: photo_id for photo_id, sha256 in existing}

    for record in records:
        db_sha256 = by_photo_id.get(record.photo_id)
        db_photo_id = by_sha256.get(record.sha256)

        if db_sha256 is None and db_photo_id is None:
            result["NEW"].append(record)

        elif (
            db_sha256 == record.sha256
            and db_photo_id == record.photo_id
        ):
            result["EXISTING"].append(record)

        else:
            result["CONFLICT"].append(record)

    return result


def register_new_photos(
    records: list[PhotoRecord],
) -> dict[str, list[PhotoRecord]]:
    """
    Register only NEW PhotoRecord objects.

    EXISTING records are skipped without modification.
    CONFLICT records cause an error before any INSERT is performed.

    Two concurrent ingests can both see a file as NEW; INSERT ... ON CONFLICT
    DO NOTHING makes the loser lose the race gracefully, and those records are
    reclassified as EXISTING instead of failing the whole batch.

    Returns the identity classification (NEW contains only inserted rows).
    """
    result = check_identity_batch(records)

    if result["CONFLICT"]:
        conflicts = ", ".join(
            record.photo_id for record in result["CONFLICT"]
        )
        raise ValueError(
            f"Identity conflicts detected: {conflicts}"
        )

    if result["NEW"]:
        result = _apply_insert_result(result, result["NEW"])

    return result


def _apply_insert_result(
    result: dict[str, list[PhotoRecord]],
    candidates: list[PhotoRecord],
) -> dict[str, list[PhotoRecord]]:
    """Keep only rows actually inserted; raced rows become EXISTING."""

    inserted = insert_photos(candidates)

    if inserted is None:
        # Defensive: a stub that does not report ids keeps old behaviour.
        return result

    new_records = [record for record in candidates if record.photo_id in inserted]
    raced = [record for record in candidates if record.photo_id not in inserted]

    result["NEW"] = new_records
    result["EXISTING"].extend(raced)
    return result


def insert_photos(records: list[PhotoRecord]) -> set[str]:
    """
    Insert multiple PhotoRecord objects in one PostgreSQL transaction.

    INSERT ... ON CONFLICT DO NOTHING makes concurrent ingests of the same
    file safe: the second one inserts nothing instead of raising
    UniqueViolation. Returns the photo_ids actually inserted.
    """

    if not records:
        return set()

    inserted: set[str] = set()

    with get_connection() as conn:
        with conn.cursor() as cur:
            for record in records:
                cur.execute(
                    """
                    INSERT INTO public.photos (
                        photo_id,
                        source_path,
                        filename,
                        sha256,
                        container_format,
                        frame_count,
                        width,
                        height,
                        size_bytes,
                        taken_at
                    )
                    VALUES (
                        %(photo_id)s,
                        %(source_path)s,
                        %(filename)s,
                        %(sha256)s,
                        %(container_format)s,
                        %(frame_count)s,
                        %(width)s,
                        %(height)s,
                        %(size_bytes)s,
                        %(taken_at)s
                    )
                    ON CONFLICT DO NOTHING
                    RETURNING photo_id
                    """,
                    {
                        "photo_id": record.photo_id,
                        "source_path": record.source_path,
                        "filename": record.filename,
                        "sha256": record.sha256,
                        "container_format": record.container_format,
                        "frame_count": record.frame_count,
                        "width": record.width,
                        "height": record.height,
                        "size_bytes": record.size_bytes,
                        "taken_at": record.taken_at,
                    },
                )
                row = cur.fetchone()

                if row is not None:
                    inserted.add(str(row[0]))

    return inserted


def get_registered_photo(photo_id: str) -> PhotoRecord | None:
    """Read one persisted photo record for deferred PREVIEW work."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT photo_id, source_path, filename, sha256, container_format,
                          frame_count, width, height, size_bytes, taken_at
                   FROM public.photos WHERE photo_id=%s""",
                (photo_id,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return PhotoRecord(
        photo_id=str(row[0]), source_path=str(row[1]), filename=str(row[2]),
        # NULL for metadata-v1 rows: they deliberately carry no content hash.
        sha256=str(row[3]) if row[3] is not None else None,
        container_format=str(row[4]), frame_count=int(row[5]),
        width=int(row[6]), height=int(row[7]),
        size_bytes=int(row[8]) if row[8] is not None else None,
        taken_at=row[9].isoformat(sep=" ") if hasattr(row[9], "isoformat") else row[9],
    )


def insert_photo(record: PhotoRecord) -> None:
    """
    Insert one PhotoRecord into the PostgreSQL photos table.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photos (
                    photo_id,
                    source_path,
                    filename,
                    sha256,
                    container_format,
                    frame_count,
                    width,
                    height,
                    size_bytes,
                    taken_at
                )
                VALUES (
                    %(photo_id)s,
                    %(source_path)s,
                    %(filename)s,
                    %(sha256)s,
                    %(container_format)s,
                    %(frame_count)s,
                    %(width)s,
                    %(height)s,
                    %(size_bytes)s,
                    %(taken_at)s
                )
                """,
                {
                    "photo_id": record.photo_id,
                    "source_path": record.source_path,
                    "filename": record.filename,
                    "sha256": record.sha256,
                    "container_format": record.container_format,
                    "frame_count": record.frame_count,
                    "width": record.width,
                    "height": record.height,
                    "size_bytes": record.size_bytes,
                    "taken_at": record.taken_at,
                },
            )
