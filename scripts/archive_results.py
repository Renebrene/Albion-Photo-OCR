#!/usr/bin/env python
"""
Нулевое состояние с архивом: результаты распознавания — в `*_archive`.

Отличие от `scripts/purge_results.py`: тот удалял результаты безвозвратно,
этот сначала переносит их в архивные таблицы (schema/049), а потом очищает
рабочие. Интерфейс и счётчики начинаются с нуля, история распознавания
остаётся в базе.

    переносится в архив               удаляется            остаётся
    ──────────────────────────────    ──────────────────   ──────────────────
    dino_batches / dino_runs /        превью (строки и      photos с photo_id,
    dino_candidates                   файлы)               video_assets
    hybrid_runs / hybrid_results      кропы (строки и      fingerprints
    photo_qwen / photo_qwen_history   файлы)               справочник адресов
    photo_regions                                          коллекции, настройки
                                                           run_history, логи
                                                           заданий в очереди

По умолчанию — сухой прогон. Запись — только с `--confirm`. Остановка при
активном прогоне или выполняющихся заданиях (кроме случаев, когда задания
прогона только стоят в очереди: их отменяет сам скрипт, см. `--keep-jobs`).

    .venv/bin/python scripts/archive_results.py
    .venv/bin/python scripts/archive_results.py --confirm
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ingest.database import get_connection  # noqa: E402

# (рабочая таблица, архивная таблица, колонка ключа для перезапуска счётчика)
ARCHIVE_PAIRS = (
    ("dino_candidates", "dino_candidates_archive", None),
    ("dino_runs", "dino_runs_archive", "run_id"),
    ("dino_batches", "dino_batches_archive", "batch_id"),
    ("hybrid_results", "hybrid_results_archive", None),
    ("hybrid_runs", "hybrid_runs_archive", "hybrid_run_id"),
    ("photo_qwen_history", "photo_qwen_history_archive", None),
    ("photo_qwen", "photo_qwen_archive", None),
    ("photo_regions", "photo_regions_archive", "region_id"),
)

# Задания прогона: после архивации они бы работали по пустым таблицам.
PIPELINE_JOB_TYPES = (
    "PHOTO_PREVIEW",
    # Детекция щита и кроп нужны только QWEN: без результатов распознавания
    # они работают впустую.
    "BILLBOARD_DETECT",
    "DINO_BATCH",
    "HYBRID_RUN",
    "QWEN_PHOTO",
    "REFINE",
)

RUNNING_STATUSES = ("RUNNING",)
# Отменяем и выполняющиеся задания: воркеры на время операции останавливают,
# иначе они продолжили бы писать превью и кропы после очистки.
ACTIVE_STATUSES = ("PENDING", "RUNNING", "PAUSED")


def _count(cur, table: str) -> int:
    cur.execute(f"SELECT count(*) FROM public.{table}")  # noqa: S608
    return int(cur.fetchone()[0])


def _exists(cur, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
    return cur.fetchone()[0] is not None


def _active(cur) -> tuple[int, int]:
    cur.execute(
        "SELECT count(*) FROM public.pipeline_runs "
        "WHERE status IN ('PENDING', 'RUNNING')"
    )
    runs = int(cur.fetchone()[0])

    cur.execute(
        "SELECT count(*) FROM public.job_queue "
        "WHERE status = ANY(%s) AND job_type = ANY(%s)",
        (list(RUNNING_STATUSES), list(PIPELINE_JOB_TYPES)),
    )
    running = int(cur.fetchone()[0])

    return runs, running


def plan(cur) -> dict:
    report = {"tables": {}, "missing_archive": []}

    for source, archive, _key in ARCHIVE_PAIRS:
        report["tables"][source] = _count(cur, source)

        if not _exists(cur, archive):
            report["missing_archive"].append(archive)

    report["previews"] = {
        "rows": _count(cur, "photo_previews"),
        "files": _dir_size(_preview_root()),
    }
    report["crops"] = {
        "rows": _count(cur, "photo_regions"),
        "files": _dir_size(_crops_root()),
    }
    report["kept"] = {
        "photos": _count(cur, "photos"),
        "video_assets": _count(cur, "video_assets"),
        "fingerprints": _count(cur, "fingerprints"),
        "address_directory": _count(cur, "address_directory"),
        "run_history": _count(cur, "run_history"),
    }

    return report


def _crops_root() -> Path:
    from app.billboard.config import CROPS_ROOT

    return Path(CROPS_ROOT)


def _preview_root() -> Path:
    from app.core.config import settings

    return Path(settings.preview_root)


def _dir_size(path: Path) -> dict:
    if not path.is_dir():
        return {"path": str(path), "files": 0, "bytes": 0}

    files = 0
    size = 0

    for item in path.rglob("*"):
        if item.is_file():
            files += 1
            size += item.stat().st_size

    return {"path": str(path), "files": files, "bytes": size}


def cancel_queued_jobs(cur) -> int:
    """Отменить незавершённые задания прогона (сами логи остаются)."""

    cur.execute(
        """
        UPDATE public.job_queue
        SET status = 'CANCELLED',
            finished_at = CURRENT_TIMESTAMP,
            error_message = COALESCE(error_message, 'результаты перенесены в архив')
        WHERE status = ANY(%s) AND job_type = ANY(%s)
        """,
        (list(ACTIVE_STATUSES), list(PIPELINE_JOB_TYPES)),
    )
    return cur.rowcount


def _reset_sequence(cur, table: str, column: str | None) -> None:
    """Счётчик идентификаторов начинается заново — «чистим счётчики»."""

    if column is None:
        return

    cur.execute("SELECT pg_get_serial_sequence(%s, %s)", (f"public.{table}", column))
    row = cur.fetchone()

    if not row or not row[0]:
        return

    cur.execute(f"ALTER SEQUENCE {row[0]} RESTART WITH 1")  # noqa: S608


def archive_tables(cur) -> dict:
    moved: dict = {}

    for source, archive, key in ARCHIVE_PAIRS:
        cur.execute(
            f"INSERT INTO public.{archive} SELECT * FROM public.{source}"  # noqa: S608
        )
        archived = cur.rowcount
        cur.execute(f"DELETE FROM public.{source}")  # noqa: S608
        cleared = cur.rowcount
        _reset_sequence(cur, source, key)
        moved[source] = {"archived": archived, "cleared": cleared}

    return moved


def wipe_dir(path: Path) -> dict:
    report = _dir_size(path)

    if not path.is_dir():
        return report

    for item in path.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument(
        "--keep-jobs",
        action="store_true",
        help="не отменять стоящие в очереди задания прогона",
    )
    parser.add_argument(
        "--keep-previews",
        action="store_true",
        help="не удалять превью (только результаты распознавания)",
    )
    parser.add_argument(
        "--keep-crops",
        action="store_true",
        help="не удалять кропы",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    with get_connection() as conn:
        with conn.cursor() as cur:
            runs, running = _active(cur)

            if (runs or running) and not args.force:
                print(
                    f"остановлено: активный прогон {runs}, выполняющихся заданий "
                    f"{running}. Остановите воркеры (scene-preview-worker, "
                    "scene-billboard-worker) и повторите, либо используйте "
                    "--force.",
                    file=sys.stderr,
                )
                return 2

            report = {
                "mode": "ЗАПИСЬ" if args.confirm else "dry-run",
                "before": plan(cur),
                "cancelled_jobs": None,
                "moved": None,
                "previews": None,
                "crops": None,
            }

            if report["before"]["missing_archive"]:
                print(
                    "не применена миграция schema/049_results_archive.sql: нет "
                    + ", ".join(report["before"]["missing_archive"]),
                    file=sys.stderr,
                )
                return 3

            if not args.confirm:
                if args.json:
                    print(json.dumps(report, ensure_ascii=False, indent=2))
                else:
                    _print(report)
                    print("ничего не изменено; для записи добавьте --confirm")
                return 0

            with conn.transaction():
                if not args.keep_jobs:
                    report["cancelled_jobs"] = cancel_queued_jobs(cur)

                report["moved"] = archive_tables(cur)

                if not args.keep_previews:
                    cur.execute("DELETE FROM public.photo_previews")
                    report["previews"] = {"rows": cur.rowcount}

            # Файлы — после фиксации транзакции: если база откатилась, превью
            # и кропы остаются на месте и прогон переиспользует их.
            if not args.keep_previews:
                report["previews"] = {
                    **(report["previews"] or {}),
                    "files": wipe_dir(_preview_root()),
                }

            if not args.keep_crops:
                report["crops"] = {"files": wipe_dir(_crops_root())}

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print(report)
        print("система в нулевом состоянии: результаты в архиве, превью удалены")

    return 0


def _print(report: dict) -> None:
    before = report["before"]

    print(f"режим: {report['mode']}")
    print("переносится в архив:")
    for table, count in before["tables"].items():
        print(f"  {table:22s} {count}")

    for name in ("previews", "crops"):
        item = before[name]
        files = item["files"]

        if isinstance(files, dict):
            print(
                f"удаляется {name}: {item['rows']} строк, файлов {files['files']} "
                f"({files['bytes'] / 1024 ** 3:.2f} ГБ) в {files['path']}"
            )

    print("остаётся:")
    for name, count in before["kept"].items():
        print(f"  {name:22s} {count}")

    if report.get("cancelled_jobs") is not None:
        print(f"отменено заданий в очереди: {report['cancelled_jobs']}")

    if report.get("moved"):
        print("перенесено в архив:")
        for table, counts in report["moved"].items():
            print(
                f"  {table:22s} архив {counts['archived']:8d} "
                f"очищено {counts['cleared']:8d}"
            )

    if report.get("previews", {}).get("files"):
        files = report["previews"]["files"]
        print(f"удалено файлов превью: {files['files']}")

    if report.get("crops", {}).get("files"):
        files = report["crops"]["files"]
        print(f"удалено файлов кропов: {files['files']}")


if __name__ == "__main__":
    raise SystemExit(main())
