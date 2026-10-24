"""
Shared pytest configuration.

Most tests exercise pure logic only: no PostgreSQL, no model loading, no
network, and no writes outside pytest's temporary directories. PostgreSQL tests
are disabled by default because the local `photobase_ingest_test` database is
working data. Opt in only with SCENE_TEST_DB=1 and an explicit disposable
SCENE_TEST_DB_NAME (see docs/testing.md).
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest
from PIL import Image

# Make the application package importable when pytest is run
# directly from the repository root without an editable install.
ROOT = Path(__file__).resolve().parents[1]

# Database integration tests mutate queue/domain tables and therefore must never
# silently use the application's operational database. Opt in only after
# provisioning a disposable test database and naming it explicitly.
if os.getenv("SCENE_TEST_DB") == "1":
    test_db_name = os.getenv("SCENE_TEST_DB_NAME", "").strip()
    if not test_db_name:
        raise RuntimeError(
            "SCENE_TEST_DB=1 requires SCENE_TEST_DB_NAME for a disposable DB"
        )
    if test_db_name == "photobase_ingest_test":
        raise RuntimeError(
            "refusing to run DB integration tests against the operational "
            "photobase_ingest_test database"
        )
    os.environ["INGEST_DB_NAME"] = test_db_name
else:
    os.environ.pop("INGEST_DB_PASSWORD", None)

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _open_api_for_tests(monkeypatch):
    """
    Keep the API open for the test session.

    Authentication is fail-closed by default in production; tests opt into the
    old open behaviour explicitly, and individual tests can still enable auth
    by setting SCENE_API_TOKENS or removing SCENE_AUTH_REQUIRED.
    """

    monkeypatch.delenv("SCENE_API_TOKENS", raising=False)
    monkeypatch.setenv("SCENE_AUTH_REQUIRED", "0")


@pytest.fixture
def probe_fingerprints():
    """
    Two throwaway registry rows for tests that write human fields.

    `set_address()`/`update_address()`/`update_fingerprint()` and the address
    import all rewrite `fingerprints.display_name` and delete
    `address_fingerprints` rows, so such a test MUST work on its own row. While
    they picked the first registry entry, every run wiped the name and the
    address of the real `76_v33`. The rows are removed afterwards (the mapping
    goes with them by CASCADE).
    """

    from app.ingest.database import get_connection

    ids = ["998_v33", "999_v33"]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.fingerprints WHERE fingerprint_id = ANY(%s)",
                (ids,),
            )

            for fingerprint_id in ids:
                cur.execute(
                    "INSERT INTO public.fingerprints (fingerprint_id, display_name) "
                    "VALUES (%s, '')",
                    (fingerprint_id,),
                )

    yield ids

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.fingerprints WHERE fingerprint_id = ANY(%s)",
                (ids,),
            )


def ensure_preview_row(photo_id: str) -> None:
    """
    Строка превью для тестового фото.

    Грид и счётчики адресов показывают только фото с превью
    (`repository._PREVIEW_READY_SQL`), поэтому тест, которому нужно фото в
    выдаче, обязан создать и превью. Строка уходит каскадом вместе с фото.
    """

    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.photo_previews (
                    photo_id, small_path, middle_path,
                    small_width, small_height, middle_width, middle_height
                )
                VALUES (%s, %s, %s, 1, 1, 1, 1)
                ON CONFLICT (photo_id) DO NOTHING
                """,
                (
                    photo_id,
                    "/tmp/scene-test-small.webp",
                    "/tmp/scene-test-middle.webp",
                ),
            )


def recognize_photo(photo_id: str, fingerprint_id: str = "78_v33") -> dict:
    """
    Пометить фото распознанным: превью, минимальные DINO-прогон и вердикт HYBRID.

    Грид показывает фото с превью и адресом из HYBRID: без вердикта фото
    остаётся в «Требуют проверки», без превью его нет в выдаче вовсе.
    Тесты, которым нужно непустое содержимое, должны создавать вердикт HYBRID.

    Возвращает идентификаторы созданных строк: фото уходит каскадом, а
    батч и прогон HYBRID нужно прибрать явно.
    """

    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO public.dino_batches
                       (run_type, status, total_count, completed_count, failed_count)
                   VALUES ('FORCE_RERUN', 'DONE', 1, 1, 0)
                   RETURNING batch_id"""
            )
            batch_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO public.dino_runs
                       (batch_id, photo_id, run_type, status, dino_best_id, finished_at)
                   VALUES (%s, %s, 'FORCE_RERUN', 'DONE', %s, CURRENT_TIMESTAMP)
                   RETURNING run_id""",
                (batch_id, photo_id, fingerprint_id),
            )
            dino_run_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO public.hybrid_runs
                       (dino_batch_id, status, total_count, completed_count, failed_count)
                   VALUES (%s, 'DONE', 1, 1, 0)
                   RETURNING hybrid_run_id""",
                (batch_id,),
            )
            hybrid_run_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO public.hybrid_results
                       (hybrid_run_id, photo_id, dino_run_id, hybrid_original_id,
                        hybrid_final_id, hybrid_changed, hybrid_score, status, finished_at)
                   VALUES (%s, %s, %s, %s, %s, FALSE, 12.0, 'DONE', CURRENT_TIMESTAMP)""",
                (hybrid_run_id, photo_id, dino_run_id, fingerprint_id, fingerprint_id),
            )

    ensure_preview_row(photo_id)

    return {
        "batch_id": batch_id,
        "dino_run_id": dino_run_id,
        "hybrid_run_id": hybrid_run_id,
    }


def forget_recognized_photo(rows: dict) -> None:
    """Убрать за `recognize_photo`: батч удаляется каскадом вместе с прогонами."""

    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.dino_batches WHERE batch_id = %s",
                (rows["batch_id"],),
            )


@pytest.fixture
def sample_photo():
    """
    One registered photo for DB tests that assert on a non-empty corpus.

    They used to rely on the operational database having photos, so a fresh
    disposable database made them fail. The row is removed afterwards.
    """

    from app.ingest.database import get_connection

    photo_id = "PH_" + "a" * 24

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.photos WHERE photo_id = %s",
                (photo_id,),
            )
            cur.execute(
                """
                INSERT INTO public.photos
                    (photo_id, source_path, filename, sha256,
                     container_format, frame_count, width, height,
                     size_bytes, taken_at)
                VALUES (%s, %s, %s, %s, 'JPEG', 1, 16, 12, 1024,
                        '2026-01-02 03:04:05')
                """,
                (
                    photo_id,
                    "/tmp/scene-test-photo.jpg",
                    "scene-test-photo.jpg",
                    "b" * 64,
                ),
            )

    # Без превью и вердикта HYBRID фото не попадает в грид, а тесты этого
    # файла проверяют фильтры по непустому корпусу.
    rows = recognize_photo(photo_id)

    yield photo_id

    forget_recognized_photo(rows)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.photos WHERE photo_id = %s",
                (photo_id,),
            )


@pytest.fixture
def make_jpeg(tmp_path):
    """
    Create a small valid JPEG file and return its path.

    The bytes are deterministic, so the SHA-256 can be
    recomputed by the test using the same hashlib routine.
    """

    def _make(name: str = "photo.JPG", size=(16, 12)) -> Path:
        path = tmp_path / name
        image = Image.new("RGB", size, color=(120, 60, 30))
        image.save(path, format="JPEG")
        return path

    return _make


@pytest.fixture
def sha256_of():
    """Return the lowercase SHA-256 hex digest of a file, 1 MiB chunks."""

    def _digest(path: Path) -> str:
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    return _digest
