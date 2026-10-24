"""Backup and restore service.

Rules that this module enforces, not the UI:

  * the backup directory must live on another filesystem than the project —
    a backup inside the disk it protects does not survive that disk;
  * a missing backup directory is created only under an existing mount
    point, so an unmounted backup disk fails loudly instead of quietly
    collecting dumps on the system disk;
  * a database restore never touches the working database unless the caller
    explicitly allowed it (the API only does that when the operator typed
    the database name);
  * a file restore extracts only the requested members, refuses paths that
    escape the target directory, and overwrites nothing without permission.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

DEFAULT_BACKUP_DIR = "/media/alexice/TEST/albion-photobase-backups"
DEFAULT_RETENTION = {"keep_daily": 14, "keep_weekly": 8, "keep_monthly": 6}
TIMER_UNIT = "scene-backup.timer"
SETTING_KEY = "backup"

DUMP_RE = re.compile(r"^(?P<db>.+)_(?P<stamp>\d{8}_\d{6})\.dump$")
ARCHIVE_RE = re.compile(r"^scene-data_(?P<stamp>\d{8}_\d{6})\.tar\.gz$")


# --- settings ---------------------------------------------------------------


def _stored() -> dict:
    """Stored backup settings; an empty dict when the database is unavailable."""

    try:
        from app import settings_store

        value = settings_store.get(SETTING_KEY, {}) or {}
    except Exception:  # noqa: BLE001 - настройки не должны ронять сервис
        return {}

    return value if isinstance(value, dict) else {}


def stored_settings() -> dict:
    """The stored backup settings (directory, retention)."""

    return dict(_stored())


def save_settings(values: dict) -> dict:
    """Store the backup settings and return what was stored."""

    from app import settings_store

    settings_store.set_value(SETTING_KEY, dict(values))
    return dict(values)


def backup_dir() -> Path:
    """Where the backups live: UI setting, then environment, then default."""

    stored = _stored().get("backup_dir")
    raw = stored or os.getenv("SCENE_BACKUP_DIR") or DEFAULT_BACKUP_DIR
    return Path(raw).expanduser()


def retention() -> dict:
    """How many generations to keep (the same keys the scripts take)."""

    stored = _stored().get("retention") or {}
    result = dict(DEFAULT_RETENTION)

    for key, fallback in DEFAULT_RETENTION.items():
        value = stored.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            continue
        if key == "keep_daily" and value < 1:
            continue
        if value < 0:
            continue
        result[key] = value

    return result


def data_dir() -> Path:
    return Path(os.getenv("SCENE_DATA", str(REPO / "data"))).expanduser()


def logs_dir() -> Path:
    """Where the run logs are written (see app/runs/log_store.py)."""

    raw = os.getenv("SCENE_RUN_LOG_ROOT", "data/logs")
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (REPO / path)


def env_file() -> Path:
    return Path(
        os.getenv("SCENE_ENV_FILE", str(Path.home() / ".config" / "scene-fingerprint.env"))
    ).expanduser()


def models_hub_dir() -> Path:
    """Кеш HuggingFace с моделью эмбеддингов (scripts/backup_data.py — то же)."""

    model_id = os.getenv("SCENE_MODEL", "facebook/dinov2-base")
    hub = Path(os.getenv("HF_HOME", str(Path.home() / ".cache" / "huggingface"))) / "hub"
    return hub / ("models--" + model_id.replace("/", "--"))


def working_db_name() -> str:
    """The database the application itself uses; restores must not touch it by accident."""

    return os.getenv("INGEST_DB_NAME", "photobase_ingest_test")


# --- state ------------------------------------------------------------------


def _on_a_mount_point(directory: Path) -> bool:
    """True when the path sits on a disk mounted separately from the root.

    The backup directory itself is usually a subdirectory of a mount point
    (/media/alexice/TEST/...), so only the leaf cannot be checked. The root
    filesystem does not count: it is where the project lives, and «диск
    бэкапов смонтирован» means a volume of its own.
    """

    current = directory

    while current != current.parent:
        if os.path.ismount(current):
            return True
        current = current.parent

    return False


def directory_state(directory: Path) -> dict:
    """Whether the backup directory exists, is on a mount and is writable."""

    exists = directory.is_dir()
    mounted = _on_a_mount_point(directory) if exists else False
    writable = os.access(directory, os.W_OK) if exists else False
    same_filesystem = None

    if exists:
        try:
            same_filesystem = directory.stat().st_dev == REPO.stat().st_dev
        except OSError:
            same_filesystem = None

    return {
        "path": str(directory),
        "exists": exists,
        "mounted": mounted,
        "writable": writable,
        "same_filesystem_as_project": same_filesystem,
    }


def disk_info(path: Path) -> dict:
    target = path if path.exists() else path.parent
    try:
        usage = shutil.disk_usage(target)
    except OSError:
        return {"path": str(target), "total": None, "free": None, "used": None, "used_pct": None}

    return {
        "path": str(target),
        "total": usage.total,
        "free": usage.free,
        "used": usage.used,
        "used_pct": round(usage.used / usage.total * 100, 1) if usage.total else None,
    }


def _systemd_time_to_iso(value: str | None) -> str | None:
    """«Sat 2026-10-24 02:32:30 MSK» → ISO в локальной зоне.

    systemd печатает эти свойства уже отформатированными; точная строка
    показывается как есть, а ISO — только удобство для интерфейса.
    """

    if not value:
        return None

    parts = value.split()

    if len(parts) < 3:
        return None

    try:
        moment = datetime.strptime(" ".join(parts[1:3]), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    return moment.astimezone().isoformat(timespec="seconds")


def schedule() -> dict:
    """The backup timer: its calendar expression, next and last run."""

    result: dict = {
        "unit": TIMER_UNIT,
        "on_calendar": "",
        "next": None,
        "next_human": None,
        "last": None,
        "last_human": None,
        "active": False,
        "available": False,
        "error": None,
    }

    unit_file = Path.home() / ".config" / "systemd" / "user" / TIMER_UNIT

    try:
        for line in unit_file.read_text().splitlines():
            if line.strip().startswith("OnCalendar="):
                result["on_calendar"] = line.split("=", 1)[1].strip()
    except OSError:
        pass

    try:
        completed = subprocess.run(
            [
                "systemctl",
                "--user",
                "show",
                TIMER_UNIT,
                "--property=ActiveState,NextElapseUSecRealtime,NextElapseUSec,LastTriggerUSec",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    if completed.returncode != 0:
        result["error"] = (completed.stderr or "systemctl show не отработал").strip()
        return result

    props = dict(
        line.split("=", 1) for line in completed.stdout.splitlines() if "=" in line
    )

    result["active"] = props.get("ActiveState") == "active"
    result["available"] = True
    result["next_human"] = props.get("NextElapseUSecRealtime") or None
    result["last_human"] = props.get("LastTriggerUSec") or None
    result["next"] = _systemd_time_to_iso(result["next_human"])
    result["last"] = _systemd_time_to_iso(result["last_human"])

    return result


def logs_state() -> dict:
    """The log directory, its size and the newest files."""

    directory = logs_dir()
    files: list[dict] = []
    total = 0

    if directory.is_dir():
        for path in sorted(directory.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
            if not path.is_file():
                continue
            try:
                size = path.stat().st_size
                mtime = path.stat().st_mtime
            except OSError:
                continue
            total += size
            files.append(
                {
                    "name": path.name,
                    "size": size,
                    "modified": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(timespec="seconds"),
                }
            )

    shadow = Path(os.getenv("SCENE_DATA", str(REPO / "data"))) / "logs" / "identity_shadow.jsonl"

    return {
        "directory": str(directory),
        "exists": directory.is_dir(),
        "files": len(files),
        "bytes": total,
        "newest": files[:10],
        "shadow_log": str(shadow),
    }


# --- inventory ---------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_sidecar(path: Path, suffix: str) -> str | None:
    sidecar = path.with_suffix(path.suffix + suffix)
    try:
        return sidecar.read_text().strip()
    except OSError:
        return None


def _read_manifest(path: Path) -> dict:
    """The manifest next to the archive, without the absolute host paths.

    The manifest records where every source lived at backup time; that is
    useful on disk and must not travel to a browser (Гость has `read`).
    """

    manifest = path.with_suffix(path.suffix + ".json")
    try:
        value = json.loads(manifest.read_text())
    except (OSError, ValueError):
        return {}

    if not isinstance(value, dict):
        return {}

    sources = value.get("sources")

    if isinstance(sources, list):
        value["sources"] = [
            {"name": item.get("name")} if isinstance(item, dict) else {"name": str(item)}
            for item in sources
        ]

    return value


def list_backups(directory: Path | None = None) -> list[dict]:
    """Every dump and data archive in the backup directory, newest first."""

    directory = directory or backup_dir()

    if not directory.is_dir():
        return []

    items: list[dict] = []

    for path in directory.iterdir():
        if not path.is_file():
            continue

        name = path.name
        kind = None
        stamp = None

        if match := ARCHIVE_RE.match(name):
            kind = "data"
            stamp = match.group("stamp")
        elif match := DUMP_RE.match(name):
            kind = "database"
            stamp = match.group("stamp")

        if kind is None or stamp is None:
            continue

        try:
            stat = path.stat()
        except OSError:
            continue

        items.append(
            {
                "name": name,
                "kind": kind,
                "stamp": stamp,
                "created": datetime.strptime(stamp, "%Y%m%d_%H%M%S")
                .replace(tzinfo=timezone.utc)
                .isoformat(timespec="seconds"),
                "size": stat.st_size,
                "sha256": _read_sidecar(path, ".sha256"),
                "manifest": _read_manifest(path),
            }
        )

    items.sort(key=lambda item: item["stamp"], reverse=True)
    return items


def resolve_artifact(name: str, directory: Path | None = None) -> Path:
    """Resolve a client-supplied artifact name inside the backup directory.

    The name may not contain a path separator: the client picks a file from
    the list, it does not choose a path.
    """

    directory = directory or backup_dir()

    if not name or "/" in name or "\\" in name or name in {".", ".."}:
        raise ValueError("недопустимое имя файла бэкапа")

    path = (directory / name).resolve()

    if path.parent != directory.resolve():
        raise ValueError("файл бэкапа лежит вне каталога бэкапов")

    if not path.is_file():
        raise FileNotFoundError(name)

    return path


def archive_members(name: str, directory: Path | None = None) -> list[str]:
    """The files inside a data archive (for a restore of individual members)."""

    path = resolve_artifact(name, directory)

    if not ARCHIVE_RE.match(path.name):
        raise ValueError("состав доступен только для архива данных (scene-data_*.tar.gz)")

    with tarfile.open(path, "r:gz") as archive:
        return [member.name for member in archive.getmembers() if member.isfile()]


# --- backup ------------------------------------------------------------------


def _run_script(relative_path: str, arguments: list[str]) -> dict:
    """Run one of the backup scripts (a repo-relative path) and parse its report."""

    command = [sys.executable, str(REPO / relative_path), "--json", *arguments]
    name = Path(relative_path).name

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=str(REPO),
        timeout=3600,
        check=False,
    )

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"{name}: {detail or f'код {completed.returncode}'}")

    try:
        return json.loads(completed.stdout)
    except ValueError as exc:
        raise RuntimeError(f"{name}: не удалось разобрать отчёт") from exc


def run_backup(payload: dict, control=None) -> dict:
    """Create a backup of the database, the data files, or both."""

    requested = payload.get("parts")

    if requested is None:
        requested = ["database", "data"]

    parts = [part for part in requested if part in {"database", "data", "models"}]

    if not parts:
        raise ValueError("нечего копировать: выберите базу данных или данные")

    # Модели едут в том же архиве, что и данные: отдельный архив на 350 МБ,
    # который меняется раз в полгода, только запутал бы восстановление.
    with_data = "data" in parts or "models" in parts

    directory = Path(payload.get("out_dir") or backup_dir()).expanduser()
    keep = retention()
    stamp = payload.get("stamp") or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    steps: list[tuple[str, list[str]]] = []

    if "database" in parts:
        steps.append(
            (
                "database",
                [
                    "scripts/backup_db.py",
                    "--out-dir",
                    str(directory),
                    "--stamp",
                    stamp,
                    "--keep-daily",
                    str(keep["keep_daily"]),
                    "--keep-weekly",
                    str(keep["keep_weekly"]),
                    "--keep-monthly",
                    str(keep["keep_monthly"]),
                ],
            )
        )

    if with_data:
        arguments = [
            "scripts/backup_data.py",
            "--out-dir",
            str(directory),
            "--stamp",
            stamp,
            "--keep-daily",
            str(keep["keep_daily"]),
            "--keep-monthly",
            str(keep["keep_monthly"]),
        ]

        if "models" in parts:
            arguments.append("--with-models")

        steps.append(("data", arguments))

    results: dict[str, dict] = {}

    for index, (kind, arguments) in enumerate(steps):
        if control is not None:
            control(index, len(steps), f"бэкап: {kind}")

        results[kind] = _run_script(arguments[0], arguments[1:])

    if control is not None:
        control(len(steps), len(steps), "бэкап готов")

    return {
        "parts": parts,
        "stamp": stamp,
        "directory": str(directory),
        "results": results,
    }


# --- restore -----------------------------------------------------------------


def _safe_member(name: str) -> bool:
    """A member of the archive may not be absolute and may not climb out."""

    if not name or name.startswith("/") or name.startswith("\\"):
        return False

    parts = Path(name).parts
    return ".." not in parts


def _in_place_destination(member: str) -> Path:
    """Where a member goes when it is restored over the working installation."""

    if member.startswith("data/"):
        return REPO / member

    if member == "env/scene-fingerprint.env":
        return env_file()

    if member.startswith("models/dinov2/"):
        return models_hub_dir() / member[len("models/dinov2/") :]

    if member.startswith("models/data/"):
        return data_dir() / "models" / member[len("models/data/") :]

    raise ValueError(f"восстановление «на место» не знает, куда класть {member}")


def restore_data(
    name: str,
    members: list[str] | None = None,
    *,
    target_dir: str | None = None,
    in_place: bool = False,
    overwrite: bool = False,
) -> dict:
    """Restore files from a data archive.

    `members=None` restores the whole archive. `target_dir` restores into a
    separate directory (nothing of the working installation is touched);
    `in_place` restores over the working installation and needs `overwrite`.
    """

    path = resolve_artifact(name)

    if not ARCHIVE_RE.match(path.name):
        raise ValueError("это не архив данных: выберите scene-data_*.tar.gz")

    if in_place and target_dir:
        raise ValueError("нельзя восстанавливать одновременно «на место» и в отдельную папку")

    if in_place:
        base = None
    else:
        base = Path(target_dir or (REPO / "data" / "restored")).expanduser()
        base.mkdir(parents=True, exist_ok=True)

    with tarfile.open(path, "r:gz") as archive:
        available = {member.name: member for member in archive.getmembers() if member.isfile()}

        if members is None:
            wanted = list(available)
        else:
            wanted = list(dict.fromkeys(members))
            missing = [item for item in wanted if item not in available]
            if missing:
                raise ValueError(f"в архиве нет: {', '.join(missing[:5])}")

        for member in wanted:
            if not _safe_member(member):
                raise ValueError(f"небезопасный путь в архиве: {member}")

        restored: list[dict] = []
        skipped: list[str] = []

        for member in wanted:
            info = available[member]
            destination = _in_place_destination(member) if in_place else (base / member)

            if destination.exists() and not overwrite:
                skipped.append(member)
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(info)
            if source is None:
                continue

            with destination.open("wb") as stream:
                shutil.copyfileobj(source, stream)

            os.chmod(destination, 0o600 if in_place else 0o644)
            restored.append({"member": member, "path": str(destination), "size": info.size})

    return {
        "archive": path.name,
        "mode": "in_place" if in_place else "folder",
        "target": str(base) if base else str(REPO),
        "restored": restored,
        "skipped": skipped,
        "total": len(restored),
    }


def _database_exists(name: str) -> bool:
    try:
        import psycopg
    except ImportError:  # pragma: no cover - psycopg is a hard dependency
        return True

    env = os.environ.copy()
    env.setdefault("PGHOST", env.get("INGEST_DB_HOST", "localhost"))
    env.setdefault("PGPORT", env.get("INGEST_DB_PORT", "5432"))
    env.setdefault("PGUSER", env.get("INGEST_DB_USER", "lora_ingest"))

    try:
        with psycopg.connect(
            dbname=name,
            user=env["PGUSER"],
            host=env["PGHOST"],
            port=env["PGPORT"],
            password=env.get("INGEST_DB_PASSWORD"),
            connect_timeout=5,
        ):
            return True
    except Exception:  # noqa: BLE001 - «нет такой БД» и «нет прав» различаем ниже
        return False


def restore_database(
    name: str,
    target_db: str,
    *,
    allow_production: bool = False,
) -> dict:
    """Restore a dump into a named database.

    The working database is refused unless the caller explicitly allowed it:
    the API only sets that flag when the operator typed the database name.
    """

    path = resolve_artifact(name)

    if not path.name.endswith(".dump"):
        raise ValueError("это не дамп базы данных: выберите *.dump")

    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$", target_db or ""):
        raise ValueError("недопустимое имя базы данных")

    working = working_db_name()

    if target_db == working and not allow_production:
        raise PermissionError(
            f"восстановление в рабочую базу {working} запрещено без явного подтверждения"
        )

    expected = _read_sidecar(path, ".sha256")

    if expected:
        actual = _sha256_file(path)
        if actual != expected:
            raise RuntimeError("контрольная сумма дампа не совпала — файл повреждён")

    if not _database_exists(target_db):
        raise RuntimeError(
            f"база {target_db} не существует; создайте её: "
            f"sudo -u postgres createdb -O {os.getenv('INGEST_DB_USER', 'lora_ingest')} {target_db}"
        )

    env = os.environ.copy()
    env.setdefault("PGHOST", env.get("INGEST_DB_HOST", "localhost"))
    env.setdefault("PGPORT", env.get("INGEST_DB_PORT", "5432"))
    env.setdefault("PGUSER", env.get("INGEST_DB_USER", "lora_ingest"))
    env.setdefault("PGDATABASE", target_db)

    completed = subprocess.run(
        [
            "pg_restore",
            "--no-owner",
            "--exit-on-error",
            "--dbname",
            target_db,
            str(path),
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=7200,
        check=False,
    )

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"pg_restore: {detail or f'код {completed.returncode}'}")

    return {
        "dump": path.name,
        "database": target_db,
        "sha256_verified": bool(expected),
        "is_working_database": target_db == working,
    }


def run_restore(payload: dict, control=None) -> dict:
    """Restore chosen files and/or a database dump, as one job."""

    target = payload.get("target") or "files"

    if control is not None:
        control(0, 1, "восстановление")

    if target == "database":
        result = restore_database(
            payload["file"],
            payload.get("target_db") or "",
            allow_production=bool(payload.get("allow_production")),
        )
        return {"target": "database", "result": result}

    result = restore_data(
        payload["file"],
        payload.get("members"),
        target_dir=payload.get("target_dir"),
        in_place=bool(payload.get("in_place")),
        overwrite=bool(payload.get("overwrite")),
    )
    return {"target": "files", "result": result}


def status() -> dict:
    """Everything the technical section shows about backups and logs."""

    directory = backup_dir()

    return {
        "backup_dir": str(directory),
        "directory": directory_state(directory),
        "disk": disk_info(directory if directory.exists() else directory.parent),
        "project_dir": str(REPO),
        "data_dir": str(data_dir()),
        "logs": logs_state(),
        "schedule": schedule(),
        "retention": retention(),
        "backups": list_backups(directory),
        "working_database": working_db_name(),
    }
