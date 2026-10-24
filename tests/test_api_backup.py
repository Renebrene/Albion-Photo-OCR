"""Бэкапы через API: подтверждения доходят до очереди, а не мимо неё.

Тесты не ставят настоящих работ: `jobs_db.enqueue` подменяется записью
вызовов. Иначе запущенный scene-backup-worker подхватил бы тестовое задание и
действительно сделал бэкап во время pytest.
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import backup as backup_api
from app.api.main import app
from app.backup import service

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def backup_dir(tmp_path, monkeypatch):
    """Каталог бэкапов с одним архивом данных и одним дампом."""

    directory = tmp_path / "backups"
    directory.mkdir()
    monkeypatch.setattr(service, "backup_dir", lambda: directory)

    archive = directory / "scene-data_20260101_120000.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        for name in ("data/fingerprints/56_v33/faiss.index", "env/scene-fingerprint.env"):
            data = name.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            bundle.addfile(info, io.BytesIO(data))

    (directory / "photobase_ingest_test_20260101_120000.dump").write_bytes(b"dump")

    return directory


@pytest.fixture
def enqueued(monkeypatch):
    """Записывает постановки в очередь вместо записи в рабочую базу."""

    calls: list[tuple[str, dict]] = []

    def fake_enqueue(job_type, payload, **kwargs):
        calls.append((job_type, payload))
        return 4242

    monkeypatch.setattr(backup_api.jobs_db, "enqueue", fake_enqueue)
    return calls


def test_status_is_readable_without_a_database(backup_dir):
    response = client.get("/api/v1/backup/status")

    assert response.status_code == 200
    body = response.json()

    for key in ("backup_dir", "directory", "disk", "schedule", "retention", "backups", "working_database"):
        assert key in body, key

    assert {item["name"] for item in body["backups"]} >= {"scene-data_20260101_120000.tar.gz"}


def test_archive_members_are_listed(backup_dir):
    response = client.get("/api/v1/backup/archive/scene-data_20260101_120000.tar.gz")

    assert response.status_code == 200
    assert response.json()["members"] == [
        "data/fingerprints/56_v33/faiss.index",
        "env/scene-fingerprint.env",
    ]


def test_archive_endpoint_refuses_unknown_files(backup_dir):
    assert client.get("/api/v1/backup/archive/nope.tar.gz").status_code == 404


def test_archive_endpoint_never_serves_a_traversal(backup_dir):
    """Попытка выйти из каталога бэкапа не должна отдавать состав архива.

    URL с %2F нормализуется до /api/v1/backup/etc/passwd — это не маршрут API,
    и ответ приходит от SPA; важно, что содержимое архива наружу не уходит.
    Отказ самого сервиса на «../» проверен в tests/test_backup_service.py.
    """

    response = client.get("/api/v1/backup/archive/..%2F..%2Fetc%2Fpasswd")

    assert not response.headers.get("content-type", "").startswith("application/json")


def test_run_requires_a_chosen_part(backup_dir, enqueued):
    response = client.post("/api/v1/backup/run", json={"parts": []})

    assert response.status_code == 422
    assert enqueued == []


def test_run_enqueues_a_backup_job(backup_dir, enqueued):
    response = client.post("/api/v1/backup/run", json={"parts": ["data", "models"]})

    assert response.status_code == 200
    assert response.json()["job_id"] == 4242
    assert enqueued == [("BACKUP", {"parts": ["data", "models"], "allow_same_filesystem": False})]


def test_restore_into_a_named_database_enqueues(backup_dir, enqueued):
    response = client.post(
        "/api/v1/backup/restore",
        json={
            "file": "photobase_ingest_test_20260101_120000.dump",
            "target": "database",
            "target_db": "photobase_probe_test",
        },
    )

    assert response.status_code == 200
    job_type, payload = enqueued[0]
    assert job_type == "RESTORE"
    assert payload["target_db"] == "photobase_probe_test"
    assert "allow_production" not in payload


def test_restore_into_the_working_database_needs_the_typed_name(backup_dir, enqueued, monkeypatch):
    monkeypatch.setenv("INGEST_DB_NAME", "photobase_ingest_test")
    body = {
        "file": "photobase_ingest_test_20260101_120000.dump",
        "target": "database",
        "target_db": "photobase_ingest_test",
    }

    refused = client.post("/api/v1/backup/restore", json=body)
    assert refused.status_code == 409
    assert "photobase_ingest_test" in refused.json()["detail"]
    assert enqueued == []

    wrong = client.post("/api/v1/backup/restore", json={**body, "confirm": "photobase_other"})
    assert wrong.status_code == 409
    assert enqueued == []

    agreed = client.post(
        "/api/v1/backup/restore",
        json={**body, "confirm": "photobase_ingest_test", "allow_production": True},
    )
    assert agreed.status_code == 200
    assert enqueued[0][1]["allow_production"] is True


def test_restore_in_place_needs_the_typed_words(backup_dir, enqueued):
    body = {"file": "scene-data_20260101_120000.tar.gz", "target": "files", "in_place": True}

    assert client.post("/api/v1/backup/restore", json=body).status_code == 409

    mixed_case = client.post(
        "/api/v1/backup/restore", json={**body, "confirm": " НА МЕСТО "}
    )
    assert mixed_case.status_code == 200
    payload = enqueued[0][1]
    assert payload["in_place"] is True
    assert payload["overwrite"] is True


def test_restore_of_selected_files_into_a_folder(backup_dir, enqueued, tmp_path):
    target = tmp_path / "restored"

    response = client.post(
        "/api/v1/backup/restore",
        json={
            "file": "scene-data_20260101_120000.tar.gz",
            "target": "files",
            "members": ["data/fingerprints/56_v33/faiss.index"],
            "target_dir": str(target),
        },
    )

    assert response.status_code == 200
    assert enqueued[0][1]["members"] == ["data/fingerprints/56_v33/faiss.index"]
    assert enqueued[0][1]["in_place"] is False


def test_restore_of_an_unknown_file_is_refused(backup_dir, enqueued):
    response = client.post(
        "/api/v1/backup/restore",
        json={"file": "нет-такого.dump", "target": "database", "target_db": "photobase_probe_test"},
    )

    assert response.status_code == 404
    assert enqueued == []


def test_settings_are_stored(monkeypatch, backup_dir):
    """PUT сохраняет каталог и retention в app_settings (без рабочей БД — заглушка)."""

    stored: dict = {}
    monkeypatch.setattr(service, "stored_settings", lambda: dict(stored))
    monkeypatch.setattr(service, "save_settings", lambda values: stored.update(values) or dict(values))

    response = client.put(
        "/api/v1/backup/settings",
        json={"backup_dir": "/media/alexice/TEST/backups", "retention": {"keep_daily": 7}},
    )

    assert response.status_code == 200
    assert stored["backup_dir"] == "/media/alexice/TEST/backups"
    assert stored["retention"]["keep_daily"] == 7
    # Остальные сроки берутся из текущих значений, а не обнуляются.
    assert stored["retention"]["keep_monthly"] == service.DEFAULT_RETENTION["keep_monthly"]


def test_settings_refuse_a_zero_retention_for_days(backup_dir, monkeypatch):
    monkeypatch.setattr(service, "stored_settings", lambda: {})
    monkeypatch.setattr(service, "save_settings", lambda values: values)

    response = client.put("/api/v1/backup/settings", json={"retention": {"keep_daily": 0}})

    assert response.status_code == 422
