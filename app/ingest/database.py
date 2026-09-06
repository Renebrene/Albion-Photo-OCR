from __future__ import annotations

import os

import psycopg

from app.ingest.register import PhotoRecord


def get_connection() -> psycopg.Connection:
    """
    Open a connection to the dedicated INGEST PostgreSQL database.

    Connection parameters are taken from environment variables.
    No credentials are stored in source code.
    """
    return psycopg.connect(
        host=os.getenv("INGEST_DB_HOST", "localhost"),
        port=os.getenv("INGEST_DB_PORT", "5432"),
        dbname=os.getenv("INGEST_DB_NAME", "photobase_ingest_test"),
        user=os.getenv("INGEST_DB_USER", "lora_ingest"),
        password=os.environ["INGEST_DB_PASSWORD"],
    )


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

    Returns the identity classification.
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
        insert_photos(result["NEW"])

    return result


def insert_photos(records: list[PhotoRecord]) -> None:
    """
    Insert multiple PhotoRecord objects in one PostgreSQL transaction.

    One database connection is used for the complete batch.
    If any insert fails, the transaction is rolled back.
    """
    if not records:
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO public.photos (
                    photo_id,
                    source_path,
                    filename,
                    sha256,
                    container_format,
                    frame_count,
                    width,
                    height
                )
                VALUES (
                    %(photo_id)s,
                    %(source_path)s,
                    %(filename)s,
                    %(sha256)s,
                    %(container_format)s,
                    %(frame_count)s,
                    %(width)s,
                    %(height)s
                )
                """,
                [
                    {
                        "photo_id": record.photo_id,
                        "source_path": record.source_path,
                        "filename": record.filename,
                        "sha256": record.sha256,
                        "container_format": record.container_format,
                        "frame_count": record.frame_count,
                        "width": record.width,
                        "height": record.height,
                    }
                    for record in records
                ],
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
                    height
                )
                VALUES (
                    %(photo_id)s,
                    %(source_path)s,
                    %(filename)s,
                    %(sha256)s,
                    %(container_format)s,
                    %(frame_count)s,
                    %(width)s,
                    %(height)s
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
                },
            )
