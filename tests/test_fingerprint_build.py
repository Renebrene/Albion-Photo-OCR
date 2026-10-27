"""
Building a fingerprint from a folder (job FINGERPRINT_BUILD, schema/024).

The heavy part (DINOv2) is not exercised here: the tests cover sampling, the
photo metadata (names + capture dates), the job payload mapping and the API
endpoints. Anything that queues a job cleans it up.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.main import app
from app.core.fingerprint import image_meta, sample_paths

client = TestClient(app, raise_server_exceptions=False)


def _db_available() -> bool:
    if not os.getenv("INGEST_DB_PASSWORD"):
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select to_regclass('public.job_queue')")
                return cur.fetchone()[0] is not None
    except Exception:
        return False


def _build_job_type_available() -> bool:
    if not _db_available():
        return False
    try:
        from app.ingest.database import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conname = 'job_queue_job_type_check'"
                )
                row = cur.fetchone()
                return bool(row) and "FINGERPRINT_BUILD" in row[0]
    except Exception:
        return False


requires_build_job = pytest.mark.skipif(
    not _build_job_type_available(),
    reason="schema/024 (FINGERPRINT_BUILD) is not applied",
)


@pytest.fixture
def photo_folder(tmp_path):
    """A folder with three photos, one of them carrying an EXIF capture date."""

    for index in range(3):
        Image.new("RGB", (16, 12), color=(10, 20, 30)).save(
            tmp_path / f"{index}.jpg", format="JPEG"
        )

    exif = Image.Exif()
    exif.get_ifd(0x8769)[0x9003] = "2026:05:01 10:20:30"
    Image.new("RGB", (16, 12), color=(1, 2, 3)).save(
        tmp_path / "with_date.jpg", format="JPEG", exif=exif
    )

    return tmp_path


# ---- sampling ----


def test_sample_paths_takes_a_stride_not_the_first_n():
    paths = [f"{index}.jpg" for index in range(1, 11)]

    assert sample_paths(paths, 3) == ["1.jpg", "4.jpg", "7.jpg"]
    # stride = 10/4 = 2.5 -> indices 0, 2, 5, 7
    assert sample_paths(paths, 4) == ["1.jpg", "3.jpg", "6.jpg", "8.jpg"]


def test_sample_paths_keeps_everything_when_the_folder_is_smaller():
    paths = ["a.jpg", "b.jpg"]

    assert sample_paths(paths, 30) == paths
    assert sample_paths(paths, 0) == paths
    assert sample_paths([], 30) == []


# ---- photo names + capture dates ----


def test_image_meta_records_names_and_dates(photo_folder):
    names = sorted(path.name for path in photo_folder.iterdir())
    meta = image_meta(sorted(photo_folder.iterdir()))

    assert [item["name"] for item in meta] == names
    dated = {item["name"]: item["taken_at"] for item in meta}

    assert dated["with_date.jpg"] == "2026-05-01 10:20:30"
    # A photo without EXIF is still listed, just without a date.
    assert dated.get("0.jpg") is None


def test_image_meta_survives_an_unreadable_file(tmp_path):
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"not an image")

    meta = image_meta([broken])

    assert meta == [{"name": "broken.jpg", "taken_at": None}]


# ---- job payload ----


def test_worker_maps_the_build_payload(monkeypatch):
    from app.jobs import worker

    seen: dict = {}

    def fake_build(
        fingerprint_id,
        folder,
        *,
        max_photos=None,
        replace=True,
        recalculate=False,
        batch_id=None,
        job_id=None,
        progress=None,
    ):
        seen.update(
            fingerprint_id=fingerprint_id,
            folder=folder,
            max_photos=max_photos,
            replace=replace,
            recalculate=recalculate,
            batch_id=batch_id,
            job_id=job_id,
            has_progress=callable(progress),
        )
        return {"fingerprint_id": fingerprint_id, "images": 20}

    monkeypatch.setattr("app.pipeline.build.build_fingerprint", fake_build)

    result = worker._execute(
        {
            # A real job row always carries its id; the build reports progress
            # and checks pause/cancel through it.
            "id": 1,
            "job_type": "FINGERPRINT_BUILD",
            "payload": {
                "fingerprint_id": "78_v33",
                "folder": "/photos/78",
                "max_photos": 30,
                "replace": True,
                "recalculate": True,
            },
        }
    )

    assert seen == {
        "fingerprint_id": "78_v33",
        "folder": "/photos/78",
        "max_photos": 30,
        "replace": True,
        "recalculate": True,
        "batch_id": None,
        "job_id": 1,
        # The worker hands the builder a progress callback it can report with.
        "has_progress": True,
    }
    assert result["images"] == 20


def test_build_does_not_mark_the_qwen_model_busy():
    """Fingerprint building uses DINOv2, so it must not trigger QWEN unload."""

    from app.jobs import worker

    assert "FINGERPRINT_BUILD" not in worker._MODEL_JOB_TYPES


# ---- builder sizing and the embedding cache ----

def test_descriptor_workers_split_between_builders(monkeypatch):
    """
    N builders must not each take half the cores: the share is divided, so the
    descriptor thread pools together add up to at most half of them.
    """

    from app.pipeline import build

    monkeypatch.setattr(build.os, "cpu_count", lambda: 12)

    monkeypatch.delenv("SCENE_BUILD_PARALLEL", raising=False)
    assert build.default_descriptor_workers() == 6

    monkeypatch.setenv("SCENE_BUILD_PARALLEL", "3")
    assert build.default_descriptor_workers() == 2

    monkeypatch.setenv("SCENE_BUILD_PARALLEL", "6")
    assert build.default_descriptor_workers() == 1

    # A nonsensical value must not crash or produce zero workers.
    monkeypatch.setenv("SCENE_BUILD_PARALLEL", "0")
    assert build.default_descriptor_workers() >= 1


def test_get_embedder_loads_the_model_once(monkeypatch):
    """A builder process serves many jobs; DINOv2 is loaded once, not per job."""

    from app.pipeline import build

    calls = []

    class FakeEmbedder:
        def __init__(self, settings):
            calls.append(settings)

    build._EMBEDDER_CACHE.clear()
    monkeypatch.setattr(build, "SceneEmbedder", FakeEmbedder)

    try:
        first = build.get_embedder()
        second = build.get_embedder()
    finally:
        build._EMBEDDER_CACHE.clear()

    assert first is second
    assert len(calls) == 1


# ---- recalculation after a replacement ----


class _FakeManager:
    def __init__(self, *args, **kwargs):
        pass

    def create(self, fingerprint_id, folder_path, embedder, **kwargs):
        return {"images": 3, "version": "3.3"}


def _prepare_build(monkeypatch, tmp_path):
    from dataclasses import replace

    from app.api import fingerprints as registry
    from app.core.config import settings
    from app.pipeline import build

    (tmp_path / "src").mkdir()
    (tmp_path / "fingerprints").mkdir()

    monkeypatch.setattr(
        build,
        "settings",
        replace(settings, data_dir=tmp_path),
    )
    monkeypatch.setattr(build, "FingerprintManager", _FakeManager)
    monkeypatch.setattr(build, "get_embedder", lambda: object())
    monkeypatch.setattr(
        registry, "sync_from_disk", lambda: {"versions_added": []}
    )

    return build


def test_replacing_an_existing_fingerprint_queues_recalculation(
    monkeypatch, tmp_path
):
    build = _prepare_build(monkeypatch, tmp_path)

    existing = tmp_path / "fingerprints" / "78_v33"
    existing.mkdir()
    (existing / "metadata.json").write_text("{}")

    calls: list[dict] = []

    def fake_recalc(**kwargs):
        calls.append(kwargs)
        return {"batch_id": 5, "job_id": 7, "total": 326, "run_id": 9}

    monkeypatch.setattr(
        "app.dino.recalc.enqueue_recalculation", fake_recalc
    )

    result = build.build_fingerprint(
        "78_v33", str(tmp_path / "src"), recalculate=True
    )

    assert calls == [
        {"reason": "замены", "fingerprint_id": "78_v33"},
    ]
    assert result["replaced_existing"] is True
    assert result["recalculated"] is True
    assert result["recalc"]["job_id"] == 7


def test_a_new_fingerprint_does_not_queue_recalculation(
    monkeypatch, tmp_path
):
    build = _prepare_build(monkeypatch, tmp_path)

    calls: list[dict] = []
    monkeypatch.setattr(
        "app.dino.recalc.enqueue_recalculation",
        lambda **kwargs: calls.append(kwargs),
    )

    result = build.build_fingerprint(
        "99_v33", str(tmp_path / "src"), recalculate=True
    )

    assert calls == []
    assert result["replaced_existing"] is False
    assert result["recalculated"] is False


# ---- endpoints ----


def test_build_rejects_an_empty_folder(tmp_path):
    response = client.post(
        "/api/v1/fingerprints/build",
        json={"fingerprint_id": "test_v33", "folder": str(tmp_path)},
    )

    assert response.status_code == 400
    assert "фотограф" in response.json()["detail"]


def test_build_rejects_a_bad_fingerprint_id(photo_folder):
    response = client.post(
        "/api/v1/fingerprints/build",
        json={"fingerprint_id": "bad id!", "folder": str(photo_folder)},
    )

    assert response.status_code == 400


def test_build_rejects_a_missing_folder(tmp_path):
    response = client.post(
        "/api/v1/fingerprints/build",
        json={
            "fingerprint_id": "test_v33",
            "folder": str(tmp_path / "nope"),
        },
    )

    assert response.status_code == 404


@requires_build_job
def test_build_queues_a_job_and_can_be_cancelled(photo_folder):
    response = client.post(
        "/api/v1/fingerprints/build",
        json={
            "fingerprint_id": "test_build_v33",
            "folder": str(photo_folder),
            "max_photos": 2,
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"]
    assert payload["photos"] == 4
    assert payload["max_photos"] == 2

    # Cancel it so the worker never runs the real build.
    cancelled = client.post(f"/api/v1/jobs/{payload['job_id']}/cancel")
    assert cancelled.status_code == 200


def test_browse_starts_at_the_allowed_roots():
    response = client.get("/api/v1/fingerprints/browse")

    assert response.status_code == 200
    body = response.json()
    assert body["path"] is None
    assert isinstance(body["dirs"], list)


def test_browse_lists_subfolders(photo_folder):
    child = photo_folder / "nested"
    child.mkdir()
    Image.new("RGB", (16, 12)).save(child / "a.jpg", format="JPEG")

    response = client.get(
        "/api/v1/fingerprints/browse",
        params={"path": str(photo_folder)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == str(photo_folder)
    names = [item["name"] for item in body["dirs"]]
    assert "nested" in names
    nested = next(item for item in body["dirs"] if item["name"] == "nested")
    assert nested["photos"] == 1
    assert body["photos"] == 4  # the photos directly in the folder


def test_browse_rejects_a_unknown_path(tmp_path):
    response = client.get(
        "/api/v1/fingerprints/browse",
        params={"path": str(tmp_path / "nope")},
    )

    assert response.status_code == 404


def test_native_picker_is_off_by_default():
    """
    The flag is checked BEFORE the request: when the picker is enabled the
    endpoint opens a real desktop dialog and blocks until someone closes it, so
    a test must never call it.
    """

    from app.api import routes

    if routes.NATIVE_PICKER:
        pytest.skip("the native picker is enabled in this environment")

    response = client.post("/api/v1/fingerprints/pick-folder")

    assert response.status_code == 501


# ---- системный выбор папки: отмена ≠ сбой ---------------------------------


def _enable_picker(monkeypatch, *, display=True):
    from app.api import routes

    monkeypatch.setattr(routes, "NATIVE_PICKER", True)
    monkeypatch.setattr(routes.shutil, "which", lambda _name: "/usr/bin/zenity")

    if display:
        monkeypatch.setenv("DISPLAY", ":0")
    else:
        monkeypatch.delenv("DISPLAY", raising=False)
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)


def test_native_picker_without_a_display_says_so(monkeypatch):
    """Служба без графической сессии: это не «отмена», а недоступность."""

    _enable_picker(monkeypatch, display=False)

    response = client.post("/api/v1/fingerprints/pick-folder")

    assert response.status_code == 503
    assert "графической" in response.json()["detail"]


def test_native_picker_reports_a_failure_to_open(monkeypatch):
    """zenity не смог открыть окно — показываем его причину, а не «отменён»."""

    from app.api import routes

    _enable_picker(monkeypatch)

    class Done:
        returncode = 1
        stdout = ""
        stderr = "cannot open display :0\n"

    monkeypatch.setattr(routes.subprocess, "run", lambda *a, **k: Done())

    response = client.post("/api/v1/fingerprints/pick-folder")

    assert response.status_code == 503
    assert "cannot open display" in response.json()["detail"]


def test_native_picker_reports_a_cancel_as_a_cancel(monkeypatch):
    """Пустой stderr и код 1 — человек закрыл окно."""

    from app.api import routes

    _enable_picker(monkeypatch)

    class Done:
        returncode = 1
        stdout = ""
        stderr = ""

    monkeypatch.setattr(routes.subprocess, "run", lambda *a, **k: Done())

    response = client.post("/api/v1/fingerprints/pick-folder")

    assert response.status_code == 409
    assert "отменён" in response.json()["detail"]
