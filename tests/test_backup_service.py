"""Бэкапы и восстановление: правила, которые защищают рабочие данные.

Тесты не трогают ни рабочую БД, ни диск бэкапов: каталог подменяется на
pytest-овый, а pg_restore — на заглушку.
"""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

import pytest

from app.backup import service


ENV_MEMBER = "env/scene-fingerprint.env"
FINGERPRINT_MEMBER = "data/fingerprints/56_v33/faiss.index"
MODEL_MEMBER = "models/dinov2/config.json"
DETECTOR_MEMBER = "models/data/yolov8s-worldv2.pt"


@pytest.fixture
def archive_tree(tmp_path, monkeypatch):
    """Каталог бэкапов с одним синтетическим архивом данных."""

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr(service, "backup_dir", lambda: backup_dir)

    archive = backup_dir / "scene-data_20260101_120000.tar.gz"
    payload = {
        ENV_MEMBER: b"INGEST_DB_PASSWORD=not-a-real-secret\n",
        FINGERPRINT_MEMBER: b"faiss-bytes",
        MODEL_MEMBER: b"{}",
        DETECTOR_MEMBER: b"weights",
    }

    with tarfile.open(archive, "w:gz") as bundle:
        for name, data in payload.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            bundle.addfile(info, io.BytesIO(data))

    return backup_dir


# --- выбор файлов ------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["../../etc/passwd", "/etc/passwd", "sub/dir.dump", "..", "", "a\\b.dump"],
)
def test_artifact_name_may_not_be_a_path(name, tmp_path):
    with pytest.raises((ValueError, FileNotFoundError)):
        service.resolve_artifact(name, tmp_path)


def test_artifact_must_exist(tmp_path):
    with pytest.raises(FileNotFoundError):
        service.resolve_artifact("photobase_20260101_120000.dump", tmp_path)


@pytest.mark.parametrize("member", ["/etc/passwd", "../escape", "a/../../b"])
def test_unsafe_archive_members_are_rejected(member):
    assert service._safe_member(member) is False


def test_archive_members_lists_only_files(archive_tree):
    members = service.archive_members("scene-data_20260101_120000.tar.gz")

    assert set(members) == {ENV_MEMBER, FINGERPRINT_MEMBER, MODEL_MEMBER, DETECTOR_MEMBER}


def test_archive_members_refuse_a_dump(archive_tree):
    (archive_tree / "photobase_20260101_120000.dump").write_bytes(b"x")

    with pytest.raises(ValueError):
        service.archive_members("photobase_20260101_120000.dump")


# --- восстановление файлов ---------------------------------------------------


def test_restore_into_a_folder_leaves_the_installation_alone(archive_tree, tmp_path):
    target = tmp_path / "restored"
    # В проекте такой файл есть (слепки лежат и в git) — он не должен измениться.
    live = service.REPO / FINGERPRINT_MEMBER
    before = live.read_bytes() if live.exists() else None

    result = service.restore_data(
        "scene-data_20260101_120000.tar.gz",
        [FINGERPRINT_MEMBER, MODEL_MEMBER],
        target_dir=str(target),
    )

    assert result["mode"] == "folder"
    assert result["total"] == 2
    assert (target / FINGERPRINT_MEMBER).read_bytes() == b"faiss-bytes"
    assert (target / MODEL_MEMBER).read_bytes() == b"{}"
    # Рабочая установка не тронута.
    assert (live.read_bytes() if live.exists() else None) == before


def test_restore_never_overwrites_without_permission(archive_tree, tmp_path):
    target = tmp_path / "restored"
    target.mkdir()
    (target / MODEL_MEMBER).parent.mkdir(parents=True)
    (target / MODEL_MEMBER).write_bytes(b"old")

    first = service.restore_data(
        "scene-data_20260101_120000.tar.gz", [MODEL_MEMBER], target_dir=str(target)
    )
    assert first["skipped"] == [MODEL_MEMBER]
    assert (target / MODEL_MEMBER).read_bytes() == b"old"

    second = service.restore_data(
        "scene-data_20260101_120000.tar.gz",
        [MODEL_MEMBER],
        target_dir=str(target),
        overwrite=True,
    )
    assert second["total"] == 1
    assert (target / MODEL_MEMBER).read_bytes() == b"{}"


def test_restore_refuses_a_member_that_is_not_in_the_archive(archive_tree):
    with pytest.raises(ValueError):
        service.restore_data("scene-data_20260101_120000.tar.gz", ["data/nothing.txt"])


def test_full_restore_takes_every_member(archive_tree, tmp_path):
    result = service.restore_data(
        "scene-data_20260101_120000.tar.gz", None, target_dir=str(tmp_path / "all")
    )

    assert result["total"] == 4


def test_in_place_restore_needs_its_own_mode(archive_tree):
    with pytest.raises(ValueError):
        service.restore_data(
            "scene-data_20260101_120000.tar.gz", [MODEL_MEMBER], target_dir="/tmp/x", in_place=True
        )


def test_in_place_destinations_cover_every_archive_root():
    """«На место» знает все корни архива: данные, слепки-модели, env."""

    assert service._in_place_destination("data/fingerprints/56_v33/faiss.index") == (
        service.REPO / "data/fingerprints/56_v33/faiss.index"
    )
    assert service._in_place_destination(ENV_MEMBER) == service.env_file()
    assert service._in_place_destination(MODEL_MEMBER) == (
        service.models_hub_dir() / "config.json"
    )
    assert service._in_place_destination(DETECTOR_MEMBER) == (
        service.data_dir() / "models" / "yolov8s-worldv2.pt"
    )

    with pytest.raises(ValueError):
        service._in_place_destination("something-else/file.bin")


# --- восстановление базы -----------------------------------------------------


def test_working_database_needs_an_explicit_allow(archive_tree, monkeypatch):
    (archive_tree / "photobase_20260101_120000.dump").write_bytes(b"dump")
    monkeypatch.setenv("INGEST_DB_NAME", "photobase_ingest_test")

    def explode(*args, **kwargs):  # pragma: no cover - не должен вызываться
        raise AssertionError("pg_restore не должен запускаться")

    monkeypatch.setattr(service.subprocess, "run", explode)

    with pytest.raises(PermissionError):
        service.restore_database("photobase_20260101_120000.dump", "photobase_ingest_test")


def test_restore_into_a_named_database_runs_pg_restore(archive_tree, monkeypatch):
    (archive_tree / "photobase_20260101_120000.dump").write_bytes(b"dump")
    monkeypatch.setenv("INGEST_DB_NAME", "photobase_ingest_test")
    monkeypatch.setattr(service, "_database_exists", lambda name: True)

    calls: list[list[str]] = []

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        return Completed()

    monkeypatch.setattr(service.subprocess, "run", fake_run)

    result = service.restore_database("photobase_20260101_120000.dump", "photobase_probe_test")

    assert result["database"] == "photobase_probe_test"
    assert result["is_working_database"] is False
    assert calls and calls[0][0] == "pg_restore"
    assert "--dbname" in calls[0] and "photobase_probe_test" in calls[0]


def test_restore_refuses_a_database_that_does_not_exist(archive_tree, monkeypatch):
    (archive_tree / "photobase_20260101_120000.dump").write_bytes(b"dump")
    monkeypatch.setattr(service, "_database_exists", lambda name: False)

    with pytest.raises(RuntimeError, match="не существует"):
        service.restore_database("photobase_20260101_120000.dump", "photobase_absent_test")


def test_restore_verifies_the_checksum_before_touching_anything(archive_tree, monkeypatch):
    dump = archive_tree / "photobase_20260101_120000.dump"
    dump.write_bytes(b"dump")
    dump.with_suffix(".dump.sha256").write_text("0" * 64 + "\n")
    monkeypatch.setattr(service, "_database_exists", lambda name: True)

    with pytest.raises(RuntimeError, match="контрольная сумма"):
        service.restore_database(dump.name, "photobase_probe_test")


@pytest.mark.parametrize("target", ["pg; DROP DATABASE x", "1bad", "", "with space"])
def test_database_names_are_validated(archive_tree, target):
    (archive_tree / "photobase_20260101_120000.dump").write_bytes(b"dump")

    with pytest.raises(ValueError):
        service.restore_database("photobase_20260101_120000.dump", target)


# --- опись и настройки -------------------------------------------------------


def test_inventory_groups_dumps_and_archives(archive_tree):
    (archive_tree / "photobase_ingest_test_20260101_120000.dump").write_bytes(b"a")
    (archive_tree / "photobase_ingest_test_20260101_120000.dump.json").write_text(
        json.dumps({"sources": [], "database": "photobase_ingest_test"})
    )
    (archive_tree / "photobase_ingest_test_20260101_120000.dump.sha256").write_text("deadbeef\n")
    (archive_tree / "не-бэкап.txt").write_text("ignore me")
    (archive_tree / "notes").mkdir()

    items = service.list_backups(archive_tree)
    by_kind = {item["kind"]: item for item in items}

    assert set(by_kind) == {"database", "data"}
    assert by_kind["database"]["stamp"] == "20260101_120000"
    assert by_kind["database"]["sha256"] == "deadbeef"
    assert by_kind["data"]["size"] > 0


def test_manifest_never_leaks_absolute_paths(archive_tree):
    """Манифест описывает, откуда взяты файлы; в браузер пути не уходят."""

    archive = archive_tree / "scene-data_20260101_120000.tar.gz"
    Path(str(archive) + ".json").write_text(
        json.dumps(
            {
                "archive": archive.name,
                "sources": [
                    {"name": "data/fingerprints", "path": "/home/someone/secret/fingerprints"}
                ],
            }
        )
    )

    item = service.list_backups(archive_tree)[0]

    assert item["manifest"]["sources"] == [{"name": "data/fingerprints"}]
    assert "someone" not in json.dumps(item["manifest"])


def test_retention_defaults_and_clamps(monkeypatch):
    monkeypatch.setattr(service, "_stored", lambda: {})
    assert service.retention() == service.DEFAULT_RETENTION

    monkeypatch.setattr(service, "_stored", lambda: {"retention": {"keep_daily": 0, "keep_weekly": 3, "keep_monthly": -5}})
    assert service.retention() == {"keep_daily": 14, "keep_weekly": 3, "keep_monthly": 6}

    monkeypatch.setattr(service, "_stored", lambda: {"retention": {"keep_daily": "много", "keep_weekly": True}})
    assert service.retention() == service.DEFAULT_RETENTION


def test_backup_dir_prefers_the_stored_setting(monkeypatch, tmp_path):
    monkeypatch.setenv("SCENE_BACKUP_DIR", "/from/env")
    monkeypatch.setattr(service, "_stored", lambda: {})
    assert service.backup_dir() == Path("/from/env")

    monkeypatch.setattr(service, "_stored", lambda: {"backup_dir": str(tmp_path)})
    assert service.backup_dir() == tmp_path


# --- запуск бэкапа -----------------------------------------------------------


def test_run_backup_maps_parts_to_script_arguments(monkeypatch, tmp_path):
    monkeypatch.setattr(service, "_stored", lambda: {})
    monkeypatch.setenv("SCENE_BACKUP_DIR", str(tmp_path))

    calls: list[tuple[str, list[str]]] = []

    def fake_script(relative_path, arguments):
        calls.append((relative_path, arguments))
        return {"ok": True}

    monkeypatch.setattr(service, "_run_script", fake_script)

    result = service.run_backup({"parts": ["database", "data", "models"], "stamp": "20260101_120000"})

    scripts = [path for path, _ in calls]
    assert scripts == ["scripts/backup_db.py", "scripts/backup_data.py"]
    assert "--stamp" in calls[0][1] and "20260101_120000" in calls[0][1]
    assert "--with-models" in calls[1][1]
    assert result["stamp"] == "20260101_120000"
    assert set(result["results"]) == {"database", "data"}


def test_models_ride_inside_the_data_archive(monkeypatch, tmp_path):
    """Отдельного архива под модели нет: они едут в архив данных."""

    monkeypatch.setattr(service, "_stored", lambda: {})
    monkeypatch.setenv("SCENE_BACKUP_DIR", str(tmp_path))

    calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(
        service, "_run_script", lambda path, arguments: calls.append((path, arguments)) or {}
    )

    service.run_backup({"parts": ["models"]})

    assert [path for path, _ in calls] == ["scripts/backup_data.py"]
    assert "--with-models" in calls[0][1]


def test_run_backup_needs_at_least_one_part(monkeypatch, tmp_path):
    monkeypatch.setenv("SCENE_BACKUP_DIR", str(tmp_path))

    with pytest.raises(ValueError):
        service.run_backup({"parts": []})


# --- расписание и каталог ----------------------------------------------------


def test_systemd_time_is_shown_as_iso():
    assert service._systemd_time_to_iso("Sat 2026-10-24 02:32:30 MSK").startswith("2026-10-24T02:32:30")
    assert service._systemd_time_to_iso("") is None
    assert service._systemd_time_to_iso("n/a") is None


def test_mount_detection_ignores_the_root_filesystem(monkeypatch):
    """Каталог бэкапа — подкаталог точки монтирования, а не она сама.

    Корень в расчёт не идёт: это тот же диск, на котором лежит проект.
    """

    monkeypatch.setattr(service.os.path, "ismount", lambda path: str(path) == "/")
    assert service._on_a_mount_point(Path("/tmp/backups")) is False

    monkeypatch.setattr(
        service.os.path, "ismount", lambda path: str(path) in {"/", "/media/alexice/TEST"}
    )
    assert service._on_a_mount_point(Path("/media/alexice/TEST/albion-photobase-backups")) is True
    assert service._on_a_mount_point(Path("/media/alexice/TEST")) is True
    assert service._on_a_mount_point(Path("/tmp/backups")) is False


def test_directory_state_reports_a_missing_directory(tmp_path):
    state = service.directory_state(tmp_path / "nope")

    assert state["exists"] is False
    assert state["mounted"] is False
    assert state["writable"] is False
