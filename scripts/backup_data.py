"""Back up the runtime data that is NOT in PostgreSQL: fingerprints, logs, reports and the environment file.

The database is dumped by `scripts/backup_db.py`; this script covers what lives
on disk, so a dead disk does not take the fingerprints with it:

  * ``data/fingerprints/`` — the reference fingerprints (FAISS/embeddings and
    the preview strips). Rebuilding them takes hours, so they are the most
    valuable files on disk;
  * ``data/logs/`` — the shadow identity log and other run logs;
  * ``data/reports/`` — the reports written by the pipeline;
  * the environment file (``~/.config/scene-fingerprint.env``) — it holds the
    database password and the Albion token, so it is only ever written into the
    backup directory (chmod 600) and never printed.

The archive is written to a temporary file, verified with ``tar -tz`` (every
expected root must be inside; a truncated archive fails the check), hashed and
only then published. Retention keeps the newest ``--keep-daily`` archives and
every archive from the newest ``--keep-monthly`` months.

Examples:
    .venv/bin/python scripts/backup_data.py --dry-run
    .venv/bin/python scripts/backup_data.py
    .venv/bin/python scripts/backup_data.py --out-dir /mnt/backup
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

DEFAULT_DIR = Path(
    os.getenv(
        "SCENE_BACKUP_DIR",
        str(Path.home() / "albion-photobase-backups"),
    )
)

DEFAULT_ENV_FILE = Path(
    os.getenv("SCENE_ENV_FILE", str(Path.home() / ".config" / "scene-fingerprint.env"))
)


def _data_dir() -> Path:
    return Path(os.getenv("SCENE_DATA", str(REPO / "data"))).expanduser()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sources(data_dir: Path, env_file: Path) -> list[tuple[str, Path]]:
    """Пары «имя в архиве → путь на диске». Отсутствующие пропускаются."""

    candidates = [
        ("data/fingerprints", data_dir / "fingerprints"),
        ("data/logs", data_dir / "logs"),
        ("data/reports", data_dir / "reports"),
        ("env/scene-fingerprint.env", env_file),
    ]

    return [(name, path) for name, path in candidates if path.exists()]


def _write_archive(target: Path, sources: list[tuple[str, Path]]) -> list[str]:
    """Собирает tar.gz и возвращает список имён файлов внутри."""

    names: list[str] = []

    with tarfile.open(target, "w:gz") as archive:
        for name, path in sources:
            # Права сохраняем: env-файл остаётся 600 и внутри архива.
            archive.add(path, arcname=name, recursive=True)
            names.append(name)

    return names


def _verify(target: Path, expected: list[str]) -> None:
    """
    Проверка архива до публикации.

    Читаем оглавление целиком: обрезанный или битый gzip падает здесь, а не
    при восстановлении. Каждый ожидаемый корень должен быть на месте.
    """

    with tarfile.open(target, "r:gz") as archive:
        listed = archive.getnames()

    missing = [name for name in expected if not any(item.startswith(name) for item in listed)]

    if missing:
        raise RuntimeError(f"архив не содержит: {', '.join(missing)}")


def select_retention(paths: list[Path], *, keep_daily: int, keep_monthly: int) -> tuple[list[Path], list[Path]]:
    """(keep, delete) для списка архивов; имя содержит YYYYMMDD_HHMMSS."""

    dated = []

    for path in paths:
        try:
            parts = path.name.split("_")
            moment = datetime.strptime(parts[-2] + "_" + parts[-1].split(".")[0], "%Y%m%d_%H%M%S")
        except (IndexError, ValueError):
            continue

        dated.append((moment, path))

    dated.sort(reverse=True)
    keep: set[Path] = set()
    seen_days: set[str] = set()
    seen_months: set[str] = set()

    for moment, path in dated:
        day = moment.strftime("%Y-%m-%d")
        month = moment.strftime("%Y-%m")

        if len(seen_days) < keep_daily and day not in seen_days:
            seen_days.add(day)
            keep.add(path)
        if len(seen_months) < keep_monthly and month not in seen_months:
            seen_months.add(month)
            keep.add(path)

    if dated and not keep:
        keep.add(dated[0][1])

    return sorted(keep), sorted(path for _, path in dated if path not in keep)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--keep-daily", type=int, default=14)
    parser.add_argument("--keep-monthly", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.keep_daily < 1 or args.keep_monthly < 0:
        print("--keep-daily must be >= 1, --keep-monthly >= 0", file=sys.stderr)
        return 2

    data_dir = (args.data_dir or _data_dir()).expanduser()
    sources = _sources(data_dir, args.env_file.expanduser())

    if not any(name.startswith("data/fingerprints") for name, _ in sources):
        print(f"fingerprints not found under {data_dir} — refusing to make an empty backup", file=sys.stderr)
        return 1

    directory = args.out_dir.expanduser()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / f"scene-data_{_timestamp()}.tar.gz"

    if args.dry_run:
        report = {"target": str(target), "sources": [name for name, _ in sources], "dry_run": True}
        print(json.dumps(report, ensure_ascii=False, sort_keys=True) if args.json else report)
        return 0

    temporary = target.with_suffix(target.suffix + ".part")

    try:
        expected = _write_archive(temporary, sources)
        _verify(temporary, expected)
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    except Exception as exc:  # noqa: BLE001 - сообщаем и не оставляем мусор
        temporary.unlink(missing_ok=True)
        print(f"backup failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    digest = _sha256(target)
    target.with_suffix(target.suffix + ".sha256").write_text(digest + "\n")
    manifest = {
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "archive": target.name,
        "size": target.stat().st_size,
        "sha256": digest,
        "sources": [{"name": name, "path": str(path)} for name, path in sources],
    }
    target.with_suffix(target.suffix + ".json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )

    keep, delete = select_retention(
        sorted(directory.glob("scene-data_*.tar.gz")),
        keep_daily=args.keep_daily,
        keep_monthly=args.keep_monthly,
    )

    for path in delete:
        try:
            path.unlink()
            path.with_suffix(path.suffix + ".sha256").unlink(missing_ok=True)
            path.with_suffix(path.suffix + ".json").unlink(missing_ok=True)
        except OSError as exc:
            print(f"could not remove {path.name}: {exc}", file=sys.stderr)

    report = {
        "target": str(target),
        "size": target.stat().st_size,
        "sha256": digest,
        "kept": len(keep),
        "deleted": len(delete),
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"backup: {target} ({report['size']} bytes) · "
            f"kept: {report['kept']} · deleted: {report['deleted']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
