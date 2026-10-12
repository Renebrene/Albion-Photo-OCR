"""
Integration tests for the PREVIEW -> PostgreSQL upsert policy.

Requires a real PostgreSQL test database (INGEST_DB_*). Skipped otherwise.
Previews are written to a temporary root; photos are inserted and removed
around each test, so the configured preview directory and the corpus are
never touched.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import replace

import pytest
from PIL import Image

psycopg = pytest.importorskip("psycopg")  # noqa: F841

from app.core.config import settings as base_settings  # noqa: E402
from app.ingest import database as ingest_db  # noqa: E402
from app.ingest.register import PhotoRecord  # noqa: E402
from app.preview import pipeline as preview_pipeline  # noqa: E402


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        with ingest_db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.photo_previews')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="integration PostgreSQL is not configured (INGEST_DB_*)",
)


TEMP_IDS = ("PH_" + "c" * 24, "PH_" + "a" * 24)


@pytest.fixture
def temp_photos(tmp_path):
    records = []
    for index, photo_id in enumerate(TEMP_IDS):
        image_path = tmp_path / f"{photo_id}.JPG"
        Image.new("RGB", (64, 48), (index * 40, 20, 30)).save(
            image_path, format="JPEG"
        )
        records.append(
            PhotoRecord(
                photo_id=photo_id,
                source_path=str(image_path),
                filename=image_path.name,
                sha256=hashlib.sha256(image_path.read_bytes()).hexdigest(),
                container_format="JPEG",
                frame_count=1,
                width=64,
                height=48,
            )
        )

    for record in records:
        try:
            ingest_db.insert_photo(record)
        except Exception:
            pass

    yield records

    ids = [record.photo_id for record in records]
    with ingest_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.photo_previews WHERE photo_id = ANY(%s)",
                (ids,),
            )
            cur.execute(
                "DELETE FROM public.photos WHERE photo_id = ANY(%s)",
                (ids,),
            )


@pytest.fixture
def preview_env(monkeypatch, tmp_path):
    root = tmp_path / "preview"
    monkeypatch.setattr(
        preview_pipeline,
        "settings",
        replace(
            base_settings,
            preview_root=root,
            preview_small_size=32,
            preview_middle_size=64,
        ),
    )
    return root


def test_first_run_updates_then_second_run_skips(temp_photos, preview_env):
    first = preview_pipeline.run(temp_photos)

    assert first.ready == 2
    assert first.database_updated == 2
    assert first.database_skipped == 0

    second = preview_pipeline.run(temp_photos)

    assert second.ready == 2
    assert second.database_updated == 0
    assert second.database_skipped == 2


def test_missing_db_row_is_rewritten(temp_photos, preview_env):
    preview_pipeline.run(temp_photos)

    ids = [record.photo_id for record in temp_photos]
    with ingest_db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.photo_previews WHERE photo_id = ANY(%s)",
                (ids,),
            )

    again = preview_pipeline.run(temp_photos)

    assert again.database_updated == 2
    assert again.database_skipped == 0
