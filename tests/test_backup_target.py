"""Куда скрипты бэкапа имеют право писать (без PostgreSQL и без реальных дисков)."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

SCRIPTS = ("scripts/backup_db.py", "scripts/backup_data.py")


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("relative", SCRIPTS)
def test_missing_dir_is_created_under_a_mount_point(relative, tmp_path, monkeypatch):
    module = _load(Path(relative).stem, relative)
    monkeypatch.setattr(os.path, "ismount", lambda path: True)

    target = tmp_path / "backups"

    # tmp_path живёт на том же томе, что и проект, поэтому проверку тома
    # отключаем: здесь проверяется именно создание каталога.
    resolved = module._prepare_backup_dir(target, allow_same_filesystem=True)

    assert resolved == target.resolve()
    assert target.is_dir()
    # Внутри архива лежит env-файл с паролями, поэтому каталог закрыт.
    assert target.stat().st_mode & 0o077 == 0


@pytest.mark.parametrize("relative", SCRIPTS)
def test_unmounted_disk_is_refused_instead_of_written_to_the_system_disk(relative, tmp_path, monkeypatch):
    """Диск отключён → каталога нет, а родитель не точка монтирования."""

    module = _load(Path(relative).stem, relative)
    monkeypatch.setattr(os.path, "ismount", lambda path: False)

    target = tmp_path / "media" / "TEST" / "backups"

    with pytest.raises(RuntimeError, match="не точка монтирования"):
        module._prepare_backup_dir(target)

    assert not target.exists()
    assert not target.parent.exists()


@pytest.mark.parametrize("relative", SCRIPTS)
def test_backup_on_the_project_volume_is_refused_unless_allowed(relative, tmp_path):
    module = _load(Path(relative).stem, relative)
    target = tmp_path / "backups"
    target.mkdir()

    with pytest.raises(RuntimeError, match="том же томе"):
        module._prepare_backup_dir(target)

    assert module._prepare_backup_dir(target, allow_same_filesystem=True) == target.resolve()


def test_backup_data_cli_reports_the_refusal_and_keeps_the_flag(tmp_path, capsys):
    """Флаг --allow-same-filesystem доходит до проверки, а отказ — в stderr."""

    module = _load("backup_data_cli", "scripts/backup_data.py")

    data_dir = tmp_path / "data"
    (data_dir / "fingerprints").mkdir(parents=True)
    env_file = tmp_path / "scene-fingerprint.env"
    env_file.write_text("INGEST_DB_PASSWORD=not-a-real-secret\n")
    out_dir = tmp_path / "backups"
    out_dir.mkdir()

    common = [
        "--out-dir", str(out_dir),
        "--data-dir", str(data_dir),
        "--env-file", str(env_file),
        "--dry-run",
        "--json",
    ]

    assert module.main(common) == 1
    assert "том же томе" in capsys.readouterr().err

    assert module.main([*common, "--allow-same-filesystem"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["dry_run"] is True
    assert report["target"].startswith(str(out_dir.resolve()))
