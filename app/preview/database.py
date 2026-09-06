from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class PreviewRecord:
    """
    PostgreSQL representation of previews belonging to one photo_id.
    """

    photo_id: str

    small_path: str
    middle_path: str

    small_width: int
    small_height: int

    middle_width: int
    middle_height: int


def get_connection() -> psycopg.Connection:
    """
    Open a PostgreSQL connection using the same environment
    convention as INGEST.
    """

    return psycopg.connect(
        host=os.getenv("INGEST_DB_HOST", "localhost"),
        port=os.getenv("INGEST_DB_PORT", "5432"),
        dbname=os.getenv("INGEST_DB_NAME", "photobase_ingest_test"),
        user=os.getenv("INGEST_DB_USER", "lora_ingest"),
        password=os.environ["INGEST_DB_PASSWORD"],
    )


def upsert_preview(record: PreviewRecord) -> None:
    """
    Insert or update the preview paths and dimensions for one photo_id.

    The database is updated only with a completed, validated
    PreviewRecord supplied by the caller.
    """

    if not record.photo_id:
        raise ValueError("photo_id is required")

    if not record.small_path:
        raise ValueError("small_path is required")

    if not record.middle_path:
        raise ValueError("middle_path is required")

    if record.small_width < 1 or record.small_height < 1:
        raise ValueError("Invalid SMALL preview dimensions")

    if record.middle_width < 1 or record.middle_height < 1:
        raise ValueError("Invalid MIDDLE preview dimensions")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO photo_previews (
                    photo_id,
                    small_path,
                    middle_path,
                    small_width,
                    small_height,
                    middle_width,
                    middle_height
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (photo_id)
                DO UPDATE SET
                    small_path = EXCLUDED.small_path,
                    middle_path = EXCLUDED.middle_path,
                    small_width = EXCLUDED.small_width,
                    small_height = EXCLUDED.small_height,
                    middle_width = EXCLUDED.middle_width,
                    middle_height = EXCLUDED.middle_height,
                    small_created_at = CURRENT_TIMESTAMP,
                    middle_created_at = CURRENT_TIMESTAMP
                """,
                (
                    record.photo_id,
                    record.small_path,
                    record.middle_path,
                    record.small_width,
                    record.small_height,
                    record.middle_width,
                    record.middle_height,
                ),
            )

        connection.commit()


def get_preview(photo_id: str) -> PreviewRecord | None:
    """
    Return the registered previews for one photo_id.

    Returns None when no preview record exists.
    """

    if not photo_id:
        raise ValueError("photo_id is required")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    photo_id,
                    small_path,
                    middle_path,
                    small_width,
                    small_height,
                    middle_width,
                    middle_height
                FROM photo_previews
                WHERE photo_id = %s
                """,
                (photo_id,),
            )

            row = cursor.fetchone()

    if row is None:
        return None

    return PreviewRecord(
        photo_id=row[0],
        small_path=row[1],
        middle_path=row[2],
        small_width=row[3],
        small_height=row[4],
        middle_width=row[5],
        middle_height=row[6],
    )
