"""Recursive image scan, local SQLite catalog, scene selection and safe export."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from contextlib import contextmanager
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

# This standalone tool reuses only the light scene selector, not app startup,
# torch, PostgreSQL, or the job queue. Run it from the repository root or via
# run_windows.bat, which places the root on PYTHONPATH.
try:
    from app.core import scene_select
except ModuleNotFoundError as exc:  # clear setup error for standalone use
    if exc.name in {"app", "app.core", "app.core.scene_select"}:
        raise SystemExit(
            "Не найден app/core/scene_select.py. Запускайте из корня репозитория "
            "или через tools\\scene_scan\\run_windows.bat."
        ) from exc
    raise SystemExit(
        f"Не найдена зависимость {exc.name}. Установите tools\\scene_scan\\requirements.txt."
    ) from exc

SUPPORTED = scene_select.SUPPORTED
SCHEMA_VERSION = 1
DEFAULT_LIMIT = 20
NORMALIZED_SUFFIX = re.compile(r"\s*\(\d+\)$", re.UNICODE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_stem(filename: str) -> str:
    """Strip only a terminal numeric copy marker: `photo (2).jpg` -> `photo`."""

    stem = Path(filename).stem
    normalized = NORMALIZED_SUFFIX.sub("", stem).strip()
    return normalized.casefold()


def relative_name_group(root: Path, path: Path) -> str:
    """A grouping hint; equal names in different directories remain separate."""

    rel = path.relative_to(root)
    parent = PurePosixPath(*rel.parent.parts).as_posix()
    stem = normalize_stem(path.name)
    return f"{parent}/{stem}" if parent not in ("", ".") else stem


def iter_images(root: Path, exclude: set[Path] | None = None) -> list[Path]:
    """Recursively list supported image files in stable, case-insensitive order."""

    root = root.resolve(strict=True)
    excluded = {path.resolve() for path in (exclude or set())}
    files = []

    for path in root.rglob("*"):
        try:
            if path.is_file() and path.suffix.casefold() in SUPPORTED:
                resolved = path.resolve()
                if resolved not in excluded and _is_within(resolved, root):
                    files.append(path)
        except OSError:
            # A permission/disappearing-file problem should not abort the scan.
            continue

    return sorted(files, key=lambda path: (str(path.relative_to(root)).casefold(), str(path)))


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stat_signature(path: Path) -> tuple[int, int]:
    info = path.stat()
    return info.st_size, info.st_mtime_ns


def connect_db(path: Path) -> sqlite3.Connection:
    """Open the scanner's own database, never the PhotoBAse job queue."""

    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    try:
        _init_db(conn)
    except Exception:
        conn.close()
        raise
    return conn


@contextmanager
def database(path: Path):
    conn = connect_db(path)
    try:
        yield conn
    finally:
        conn.close()


def _init_db(conn: sqlite3.Connection) -> None:
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if version > SCHEMA_VERSION:
        raise RuntimeError(
            f"База создана более новой версией сканера (schema {version}); "
            f"текущая версия поддерживает до {SCHEMA_VERSION}."
        )

    if version == SCHEMA_VERSION:
        return

    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS roots (
                root_id INTEGER PRIMARY KEY,
                root_path TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scan_runs (
                run_id INTEGER PRIMARY KEY,
                root_id INTEGER NOT NULL REFERENCES roots(root_id),
                started_at TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                options_json TEXT NOT NULL,
                total_files INTEGER NOT NULL DEFAULT 0,
                readable_files INTEGER NOT NULL DEFAULT 0,
                group_count INTEGER NOT NULL DEFAULT 0,
                selected_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS files (
                file_id INTEGER PRIMARY KEY,
                root_id INTEGER NOT NULL REFERENCES roots(root_id),
                relative_path TEXT NOT NULL,
                original_name TEXT NOT NULL,
                name_group TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL,
                sha256 TEXT,
                phash_hex TEXT,
                dhash_hex TEXT,
                color_json TEXT,
                brightness REAL,
                scan_error TEXT,
                missing INTEGER NOT NULL DEFAULT 0,
                last_seen_run INTEGER,
                UNIQUE(root_id, relative_path)
            );
            CREATE INDEX IF NOT EXISTS ix_files_group
                ON files(root_id, name_group);

            CREATE TABLE IF NOT EXISTS scan_items (
                run_id INTEGER NOT NULL REFERENCES scan_runs(run_id),
                file_id INTEGER NOT NULL REFERENCES files(file_id),
                relative_path TEXT NOT NULL,
                sha256 TEXT,
                scene_no INTEGER,
                selected INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                PRIMARY KEY(run_id, file_id)
            );
            CREATE INDEX IF NOT EXISTS ix_scan_items_selected
                ON scan_items(run_id, selected);

            CREATE TABLE IF NOT EXISTS exports (
                run_id INTEGER NOT NULL,
                file_id INTEGER NOT NULL,
                destination_relative TEXT,
                sha256 TEXT,
                status TEXT NOT NULL,
                error TEXT,
                exported_at TEXT,
                PRIMARY KEY(run_id, file_id),
                FOREIGN KEY(run_id, file_id)
                    REFERENCES scan_items(run_id, file_id)
            );
            """
        )
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _root_id(conn: sqlite3.Connection, root: Path) -> int:
    canonical = os.path.normcase(str(root.resolve(strict=True)))
    conn.execute(
        "INSERT OR IGNORE INTO roots(root_path, created_at) VALUES (?, ?)",
        (canonical, utc_now()),
    )
    row = conn.execute("SELECT root_id FROM roots WHERE root_path = ?", (canonical,)).fetchone()
    assert row is not None
    return int(row["root_id"])


def _feature_cache_usable(row: sqlite3.Row | None, size: int, mtime_ns: int, force: bool) -> bool:
    return bool(
        row
        and not force
        and row["size_bytes"] == size
        and row["mtime_ns"] == mtime_ns
        and row["sha256"]
        and row["phash_hex"]
        and row["dhash_hex"]
        and row["color_json"]
        and row["brightness"] is not None
    )


def _feature_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "path": row["relative_path"],
        "phash": int(row["phash_hex"], 16),
        "dhash": int(row["dhash_hex"], 16),
        "color": json.loads(row["color_json"]),
        "brightness": float(row["brightness"]),
    }


def _compute_file(path: Path) -> tuple[str, dict[str, Any] | None, str | None, int, int]:
    """Hash and decode one file; detect changes while the scan is reading it."""

    before_size, before_mtime = _stat_signature(path)
    digest = _sha256(path)
    feature = scene_select.frame_features(str(path))
    after_size, after_mtime = _stat_signature(path)

    if (before_size, before_mtime) != (after_size, after_mtime):
        return digest, None, "файл изменился во время сканирования; повторите scan", after_size, after_mtime
    if feature is None:
        return digest, None, "не удалось декодировать изображение", after_size, after_mtime

    return digest, feature, None, after_size, after_mtime


def _select_from_cached(
    rows: list[dict[str, Any]], *, limit: int, dedup: int, use_dhash: bool
) -> dict[str, Any]:
    """Use the project's scene-selection functions on cached feature rows."""

    if not rows:
        return {"series": 0, "natural_scenes": 0, "scenes": 0, "selected": [], "assignments": {}, "silhouette": None}

    hashes = np.array([row["phash"] for row in rows], dtype=np.uint64)
    groups = scene_select.dedup_groups(scene_select.hamming_matrix(hashes), dedup)
    keep = [group[0] for group in groups]
    features = scene_select.scene_features(rows, keep, use_dhash)
    natural, scores, labels, silhouette = scene_select.choose_k(features)
    scenes = scene_select.target_scenes(natural, len(keep), limit, limit)

    if scenes != natural and len(keep) >= 2:
        labels = scene_select.cluster(features, scenes)

    picked = scene_select.pick_representatives(features, labels, rows, keep)
    assignments: dict[str, int] = {}
    selected = set(picked)

    for position, group in enumerate(groups):
        scene_no = labels[position] if position < len(labels) else None
        for row_index in group:
            assignments[rows[row_index]["path"]] = int(scene_no) if scene_no is not None else 0

    return {
        "series": len(groups),
        "natural_scenes": natural,
        "scenes": scenes,
        "selected": sorted(selected),
        "assignments": assignments,
        "silhouette": silhouette,
        "scores": scores,
    }


def scan(
    source: Path,
    db_path: Path,
    *,
    limit: int = DEFAULT_LIMIT,
    dedup: int = scene_select.DEFAULT_DEDUP,
    use_dhash: bool = True,
    force: bool = False,
    csv_path: Path | None = None,
    max_files: int = 1000,
) -> dict[str, Any]:
    """Recursively scan one source tree and persist hashes + scene assignments."""

    source = source.expanduser().resolve(strict=True)
    if not source.is_dir():
        raise ValueError(f"Источник не является папкой: {source}")
    if limit < 1 or limit > 500:
        raise ValueError("--limit должен быть от 1 до 500")
    if max_files < 1 or max_files > 5000:
        raise ValueError("--max-files должен быть от 1 до 5000")
    db_path = db_path.expanduser().resolve()
    if _is_within(db_path, source):
        raise ValueError("SQLite-базу разместите вне сканируемой папки")
    if csv_path is not None and _is_within(csv_path.expanduser().resolve(), source):
        raise ValueError("CSV-отчёт разместите вне исходной папки")

    with database(db_path) as conn:
        root_id = _root_id(conn, source)
        started = utc_now()
        options = {"limit": limit, "dedup": dedup, "use_dhash": use_dhash, "max_files": max_files}
        cursor = conn.execute(
            """INSERT INTO scan_runs(root_id, started_at, algorithm, options_json, status)
               VALUES (?, ?, ?, ?, 'RUNNING')""",
            (root_id, started, "scene-select-v1", json.dumps(options, sort_keys=True)),
        )
        run_id = int(cursor.lastrowid)
        excluded = {db_path, Path(str(db_path) + "-wal"), Path(str(db_path) + "-shm")}
        paths = iter_images(source, exclude=excluded)
        if len(paths) > max_files:
            raise ValueError(
                f"Найдено {len(paths)} изображений, лимит scan — {max_files}. "
                "Разделите архив на меньшие папки или задайте --max-files (не выше 5000)."
            )
        cached_by_rel: dict[str, sqlite3.Row] = {}
        feature_rows: list[dict[str, Any]] = []
        file_ids: dict[str, int] = {}
        errors = 0

        with conn:
            for path in paths:
                relative = path.relative_to(source).as_posix()
                # Mark present before stat/decode; an unreadable but existing
                # path is not the same as a file deleted from the source tree.
                conn.execute(
                    "UPDATE files SET last_seen_run = ?, missing = 0 WHERE root_id = ? AND relative_path = ?",
                    (run_id, root_id, relative),
                )
                try:
                    size, mtime_ns = _stat_signature(path)
                except OSError:
                    errors += 1
                    continue

                cached = conn.execute(
                    "SELECT * FROM files WHERE root_id = ? AND relative_path = ?",
                    (root_id, relative),
                ).fetchone()

                if _feature_cache_usable(cached, size, mtime_ns, force):
                    file_row = cached
                else:
                    try:
                        digest, feature, error, size, mtime_ns = _compute_file(path)
                    except OSError as exc:
                        digest, feature, error = None, None, f"ошибка чтения: {exc.__class__.__name__}"

                    conn.execute(
                        """INSERT INTO files(
                               root_id, relative_path, original_name, name_group,
                               size_bytes, mtime_ns, sha256, phash_hex, dhash_hex,
                               color_json, brightness, scan_error, missing, last_seen_run
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                           ON CONFLICT(root_id, relative_path) DO UPDATE SET
                               original_name=excluded.original_name,
                               name_group=excluded.name_group,
                               size_bytes=excluded.size_bytes,
                               mtime_ns=excluded.mtime_ns,
                               sha256=excluded.sha256,
                               phash_hex=excluded.phash_hex,
                               dhash_hex=excluded.dhash_hex,
                               color_json=excluded.color_json,
                               brightness=excluded.brightness,
                               scan_error=excluded.scan_error,
                               missing=0,
                               last_seen_run=excluded.last_seen_run""",
                        (
                            root_id,
                            relative,
                            path.name,
                            relative_name_group(source, path),
                            size,
                            mtime_ns,
                            digest,
                            f"{feature['phash']:016x}" if feature else None,
                            f"{feature['dhash']:016x}" if feature else None,
                            json.dumps(feature["color"]) if feature else None,
                            feature["brightness"] if feature else None,
                            error,
                            run_id,
                        ),
                    )
                    file_row = conn.execute(
                        "SELECT * FROM files WHERE root_id = ? AND relative_path = ?",
                        (root_id, relative),
                    ).fetchone()

                if file_row is None:
                    continue
                if file_row["scan_error"]:
                    errors += 1
                file_id = int(file_row["file_id"])
                file_ids[relative] = file_id
                cached_by_rel[relative] = file_row
                conn.execute(
                    """INSERT INTO scan_items(run_id, file_id, relative_path, sha256, error)
                       VALUES (?, ?, ?, ?, ?)""",
                    (run_id, file_id, relative, file_row["sha256"], file_row["scan_error"]),
                )
                if not file_row["scan_error"] and file_row["phash_hex"]:
                    feature_rows.append(_feature_row(file_row))

            # Keep vanished-file history; only mark cache rows not seen in this run.
            conn.execute(
                "UPDATE files SET missing = 1 WHERE root_id = ? AND (last_seen_run IS NULL OR last_seen_run != ?)",
                (root_id, run_id),
            )

            selection = _select_from_cached(
                feature_rows, limit=limit, dedup=dedup, use_dhash=use_dhash
            )
            selected_paths = set(selection["selected"])
            assignments = selection["assignments"]

            by_rel_feature = {
                Path(row["path"]).as_posix(): row for row in feature_rows
            }
            for relative, file_id in file_ids.items():
                feature = by_rel_feature.get(relative)
                scene_no = assignments.get(relative) if feature else None
                conn.execute(
                    """UPDATE scan_items
                       SET scene_no = ?, selected = ?
                       WHERE run_id = ? AND file_id = ?""",
                    (
                        scene_no,
                        int(relative in selected_paths),
                        run_id,
                        file_id,
                    ),
                )

            conn.execute(
                """UPDATE scan_runs SET total_files = ?, readable_files = ?,
                   group_count = ?, selected_count = ?, status = 'DONE'
                   WHERE run_id = ?""",
                (
                    len(paths),
                    len(feature_rows),
                    len({row["name_group"] for row in cached_by_rel.values()}),
                    len(selected_paths),
                    run_id,
                ),
            )

        result = {
            "run_id": run_id,
            "root": str(source),
            "db": str(db_path),
            "total_files": len(paths),
            "readable_files": len(feature_rows),
            "groups_by_name": len({row["name_group"] for row in cached_by_rel.values()}),
            "series": selection["series"],
            "natural_scenes": selection["natural_scenes"],
            "scenes": selection["scenes"],
            "selected": len(selected_paths),
            "errors": errors,
            "silhouette": selection["silhouette"],
            "csv": str(csv_path) if csv_path else None,
        }
        if csv_path:
            write_csv(conn, run_id, csv_path)
        return result


def write_csv(conn: sqlite3.Connection, run_id: int, destination: Path) -> None:
    destination = destination.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = conn.execute(
        """SELECT i.relative_path, f.original_name, f.name_group, i.sha256,
                  i.scene_no, i.selected, i.error
           FROM scan_items AS i JOIN files AS f ON f.file_id = i.file_id
           WHERE i.run_id = ? ORDER BY i.relative_path COLLATE NOCASE""",
        (run_id,),
    ).fetchall()
    with destination.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(
            ["relative_path", "filename", "name_group", "sha256", "scene", "selected", "error"]
        )
        for row in rows:
            writer.writerow(
                [row["relative_path"], row["original_name"], row["name_group"], row["sha256"], row["scene_no"], row["selected"], row["error"]]
            )


def latest_run(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute(
        """SELECT scan_runs.*, roots.root_path
           FROM scan_runs JOIN roots USING(root_id)
           WHERE status = 'DONE' ORDER BY run_id DESC LIMIT 1"""
    ).fetchone()
    if row is None:
        raise ValueError("В базе ещё нет завершённого scan")
    return row


def safe_export_name(relative: str, sha256: str | None, used: set[str]) -> str:
    """Flatten names safely and disambiguate collisions without overwriting."""

    original = Path(relative).name
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", original).rstrip(" .") or "photo"
    stem, suffix = Path(name).stem, Path(name).suffix
    if stem.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        stem = f"_{stem}"
    candidate = f"{stem}{suffix}"
    key = candidate.casefold()
    if key in used:
        marker = (sha256 or hashlib.sha256(relative.encode("utf-8")).hexdigest())[:10]
        candidate = f"{stem}__{marker}{suffix}"
        key = candidate.casefold()
        counter = 2
        while key in used:
            candidate = f"{stem}__{marker}_{counter}{suffix}"
            key = candidate.casefold()
            counter += 1
    used.add(key)
    return candidate


def _publish_copy(source: Path, destination: Path, expected_sha256: str, output: Path) -> bool:
    """Copy through a temp file and atomically create destination without overwrite."""

    fd, temp_name = tempfile.mkstemp(prefix=".scene-scan-", suffix=".tmp", dir=output)
    os.close(fd)
    temp = Path(temp_name)
    try:
        shutil.copy2(source, temp)
        if _sha256(temp) != expected_sha256:
            raise OSError("контрольная сумма копии не совпала")
        # Windows os.rename refuses an existing destination and works on
        # filesystems without hard-link support (for example, exFAT). POSIX
        # rename may replace, so use an atomic hard-link there instead.
        if os.name == "nt":
            os.rename(temp, destination)
        else:
            os.link(temp, destination)
        return True
    finally:
        temp.unlink(missing_ok=True)


def export_selected(
    db_path: Path,
    output: Path,
    *,
    run_id: int | None = None,
    overwrite_same: bool = True,
) -> dict[str, Any]:
    """Copy selected photos; refuse outputs inside the source tree."""

    db_path = db_path.expanduser().resolve(strict=True)
    output = output.expanduser().resolve()

    with database(db_path) as conn:
        run = conn.execute(
            "SELECT r.*, roots.root_path FROM scan_runs r JOIN roots USING(root_id) WHERE r.run_id = ?",
            (run_id,),
        ).fetchone() if run_id is not None else latest_run(conn)
        if run is None or run["status"] != "DONE":
            raise ValueError("Не найден завершённый scan с таким run-id")
        source = Path(run["root_path"]).resolve(strict=True)
        if _is_within(output, source) or _is_within(source, output):
            raise ValueError("Папка экспорта должна быть отдельно от исходной папки")
        output.mkdir(parents=True, exist_ok=True)

        rows = conn.execute(
            """SELECT i.file_id, i.relative_path, i.sha256, f.size_bytes
               FROM scan_items i JOIN files f ON f.file_id = i.file_id
               WHERE i.run_id = ? AND i.selected = 1
               ORDER BY i.relative_path COLLATE NOCASE""",
            (run["run_id"],),
        ).fetchall()
        used: set[str] = set()
        copied = skipped = errors = 0

        with conn:
            for row in rows:
                rel = PurePosixPath(row["relative_path"])
                src = (source / Path(*rel.parts)).resolve()
                if not _is_within(src, source) or not src.is_file():
                    message = "исходный путь отсутствует или выходит за корень"
                    _record_export(conn, run["run_id"], row["file_id"], None, row["sha256"], "ERROR", message)
                    errors += 1
                    continue
                try:
                    digest = _sha256(src)
                except OSError as exc:
                    _record_export(conn, run["run_id"], row["file_id"], None, row["sha256"], "ERROR", f"ошибка чтения: {exc.__class__.__name__}")
                    errors += 1
                    continue
                if digest != row["sha256"]:
                    _record_export(conn, run["run_id"], row["file_id"], None, digest, "ERROR", "файл изменился после scan; повторите scan")
                    errors += 1
                    continue

                source_name = Path(row["relative_path"]).name
                stem, suffix = Path(source_name).stem, Path(source_name).suffix
                exported = False

                for attempt in range(100):
                    candidate_rel = row["relative_path"] if attempt == 0 else f"{stem}__{digest[:10]}_{attempt}{suffix}"
                    name = safe_export_name(candidate_rel, digest, used)
                    dest = output / name

                    if dest.exists():
                        try:
                            if overwrite_same and _sha256(dest) == digest:
                                _record_export(conn, run["run_id"], row["file_id"], name, digest, "SKIPPED_SAME", None)
                                skipped += 1
                                exported = True
                                break
                        except OSError:
                            pass
                        continue

                    try:
                        _publish_copy(src, dest, digest, output)
                    except FileExistsError:
                        # Another process won the name between exists() and
                        # link(); inspect it, then pick a new name if different.
                        try:
                            if overwrite_same and _sha256(dest) == digest:
                                _record_export(conn, run["run_id"], row["file_id"], name, digest, "SKIPPED_SAME", None)
                                skipped += 1
                                exported = True
                                break
                        except OSError:
                            pass
                        continue
                    except OSError as exc:
                        _record_export(conn, run["run_id"], row["file_id"], name, digest, "ERROR", f"ошибка копирования: {exc.__class__.__name__}")
                        errors += 1
                        exported = True
                        break

                    _record_export(conn, run["run_id"], row["file_id"], name, digest, "COPIED", None)
                    copied += 1
                    exported = True
                    break

                if not exported:
                    _record_export(conn, run["run_id"], row["file_id"], None, digest, "ERROR", "не удалось подобрать свободное имя экспорта")
                    errors += 1

    return {"run_id": int(run["run_id"]), "output": str(output), "selected": len(rows), "copied": copied, "skipped_same": skipped, "errors": errors}


def _record_export(conn, run_id, file_id, dest, digest, status, error):
    conn.execute(
        """INSERT INTO exports(run_id, file_id, destination_relative, sha256, status, error, exported_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(run_id, file_id) DO UPDATE SET
             destination_relative=excluded.destination_relative,
             sha256=excluded.sha256, status=excluded.status, error=excluded.error,
             exported_at=excluded.exported_at""",
        (run_id, file_id, dest, digest, status, error, utc_now()),
    )


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("нужно целое число") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("значение должно быть больше нуля")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Локальный рекурсивный сканер сцен и хешей")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_parser = sub.add_parser("scan", help="просканировать изображения и записать сцены/хеши в SQLite")
    scan_parser.add_argument("source", type=Path, help="исходная папка (оригиналы не изменяются)")
    scan_parser.add_argument("--db", required=True, type=Path, help="отдельная SQLite-база сканера")
    scan_parser.add_argument("--limit", type=_positive_int, default=DEFAULT_LIMIT, help="сколько фото отобрать (по умолчанию 20)")
    scan_parser.add_argument("--dedup", type=int, default=scene_select.DEFAULT_DEDUP, help="порог схлопывания серии по pHash, 0–64")
    scan_parser.add_argument("--no-dhash", action="store_true", help="отключить dHash")
    scan_parser.add_argument("--force", action="store_true", help="пересчитать признаки даже если файл не менялся")
    scan_parser.add_argument("--max-files", type=_positive_int, default=1000, help="защита от слишком большой квадратичной кластеризации (макс. 5000)")
    scan_parser.add_argument("--csv", type=Path, default=None, help="сохранить CSV-отчёт")

    export_parser = sub.add_parser("export", help="скопировать выбранные фото в отдельную папку")
    export_parser.add_argument("--db", required=True, type=Path, help="SQLite-база сканера")
    export_parser.add_argument("--output", required=True, type=Path, help="новая папка для копий, вне исходной")
    export_parser.add_argument("--run-id", type=int, default=None, help="scan id; по умолчанию последний завершённый")

    args = parser.parse_args(argv)

    try:
        if args.command == "scan":
            if not 0 <= args.dedup <= 64:
                parser.error("--dedup должен быть в диапазоне 0–64")
            result = scan(
                args.source,
                args.db,
                limit=args.limit,
                dedup=args.dedup,
                use_dhash=not args.no_dhash,
                force=args.force,
                csv_path=args.csv,
                max_files=args.max_files,
            )
        else:
            result = export_selected(args.db, args.output, run_id=args.run_id)
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
