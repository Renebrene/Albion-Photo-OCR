#!/usr/bin/env python
"""
Очистить базу результатов распознавания перед полным прогоном заново.

Удаляются только производные результаты, а регистрации остаются:

    удаляется                      остаётся
    ─────────────────────────────  ─────────────────────────────────────────
    dino_batches / dino_runs /     photos с их photo_id и source_path
    dino_candidates                video_assets, постеры и производные видео
    hybrid_runs / hybrid_results   photo_previews (готовые превью)
    photo_qwen, история QWEN       fingerprints, address_directory,
    photo_regions и файлы кропов   привязки слепков к адресам
                                   ручные утверждения адресов
                                   коллекции, поиски, пользователи, настройки
                                   run_history (журнал прогонов)

`photo_id` привязан к содержимому файла (схема metadata-v1 или SHA-256), а не
к результатам, поэтому после очистки инспектор не пересчитывает ID: он видит
уже зарегистрированные файлы и только доставляет превью, DINO, HYBRID, QWEN.

По умолчанию — сухой прогон: показывает, что и сколько будет удалено.
Для записи нужен `--confirm`. Скрипт отказывается работать, пока идёт прогон
«Обновление базы» или выполняются задания этих типов (`--force` — обойти).

    .venv/bin/python scripts/purge_results.py
    .venv/bin/python scripts/purge_results.py --confirm
    .venv/bin/python scripts/purge_results.py --confirm --previews --crops
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ingest.database import get_connection  # noqa: E402

# Таблицы результатов: порядок важен только для читаемости отчёта, удаление
# идёт одной транзакцией.
RESULT_TABLES = (
    "dino_candidates",
    "dino_runs",
    "dino_batches",
    "hybrid_results",
    "hybrid_runs",
    "photo_qwen_history",
    "photo_qwen",
)

# Эти типы заданий относятся к прогону: пока они выполняются, чистить нельзя.
ACTIVE_JOB_TYPES = (
    "INGEST_DIR",
    "PHOTO_PREVIEW",
    "DINO_BATCH",
    "HYBRID_RUN",
    "QWEN_PHOTO",
    "REFINE",
)


def _count(cur, table: str) -> int:
    cur.execute(f"SELECT count(*) FROM public.{table}")  # noqa: S608
    return int(cur.fetchone()[0])


def _active(cur) -> tuple[int, int]:
    """(активный прогон, выполняющиеся задания прогона)."""

    cur.execute(
        "SELECT count(*) FROM public.pipeline_runs "
        "WHERE status IN ('PENDING', 'RUNNING')"
    )
    runs = int(cur.fetchone()[0])

    cur.execute(
        "SELECT count(*) FROM public.job_queue "
        "WHERE status IN ('PENDING', 'RUNNING', 'PAUSED') "
        "AND job_type = ANY(%s)",
        (list(ACTIVE_JOB_TYPES),),
    )
    jobs = int(cur.fetchone()[0])

    return runs, jobs


def plan(cur, *, previews: bool, crops: bool) -> dict:
    report: dict = {"tables": {}}

    for table in RESULT_TABLES:
        report["tables"][table] = _count(cur, table)

    report["tables"]["photo_regions"] = _count(cur, "photo_regions")

    if previews:
        report["tables"]["photo_previews"] = _count(cur, "photo_previews")

    report["photos"] = _count(cur, "photos")
    return report


def _crops_root() -> Path:
    from app.billboard.config import CROPS_ROOT

    return Path(CROPS_ROOT)


def _preview_root() -> Path:
    from app.core.config import settings

    return Path(settings.preview_root)


def _dir_size(path: Path) -> tuple[int, int]:
    """(файлов, байт) в каталоге; отсутствующий каталог — нули."""

    if not path.is_dir():
        return 0, 0

    files = 0
    size = 0

    for item in path.rglob("*"):
        if item.is_file():
            files += 1
            size += item.stat().st_size

    return files, size


def purge(cur, *, previews: bool, crops: bool) -> dict:
    removed: dict = {}

    for table in ("photo_qwen_history", "photo_qwen", "hybrid_results", "hybrid_runs"):
        cur.execute(f"DELETE FROM public.{table}")  # noqa: S608
        removed[table] = cur.rowcount

    # dino_batches каскадом уносит dino_runs и dino_candidates.
    cur.execute("DELETE FROM public.dino_batches")
    removed["dino_batches"] = cur.rowcount
    removed["dino_runs"] = _count(cur, "dino_runs")
    removed["dino_candidates"] = _count(cur, "dino_candidates")

    cur.execute("DELETE FROM public.photo_regions")
    removed["photo_regions"] = cur.rowcount

    if previews:
        cur.execute("DELETE FROM public.photo_previews")
        removed["photo_previews"] = cur.rowcount

    return removed


def _wipe_dir(path: Path) -> dict:
    if not path.is_dir():
        return {"path": str(path), "files": 0, "bytes": 0}

    files, size = _dir_size(path)

    for item in path.iterdir():
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=False)
        else:
            item.unlink()

    return {"path": str(path), "files": files, "bytes": size}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument(
        "--previews",
        action="store_true",
        help="удалить и превью (по умолчанию готовые превью остаются)",
    )
    parser.add_argument(
        "--no-crops",
        action="store_true",
        help="не трогать файлы кропов",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    crops = not args.no_crops

    with get_connection() as conn:
        with conn.cursor() as cur:
            runs, jobs = _active(cur)

            if (runs or jobs) and not args.force:
                print(
                    f"остановлено: активный прогон {runs}, активных заданий {jobs}.\n"
                    "Дождитесь остановки или используйте --force.",
                    file=sys.stderr,
                )
                return 2

            before = plan(cur, previews=args.previews, crops=crops)
            report = {
                "mode": "ЗАПИСЬ" if args.confirm else "dry-run",
                "tables": before["tables"],
                "photos": before["photos"],
                "crops": str(_crops_root()) if crops else None,
                "previews_root": (
                    str(_preview_root()) if args.previews else None
                ),
                "removed": None,
                "files": [],
            }

            if not args.confirm:
                report["crops_files"] = _dir_size(_crops_root()) if crops else (0, 0)
                report["previews_files"] = (
                    _dir_size(_preview_root()) if args.previews else (0, 0)
                )
                if args.json:
                    print(json.dumps(report, ensure_ascii=False, indent=2))
                else:
                    _print(report)
                    print("ничего не изменено; для записи добавьте --confirm")
                return 0

            with conn.transaction():
                report["removed"] = purge(
                    cur, previews=args.previews, crops=crops
                )

    # Файлы удаляются после успешной фиксации транзакции: если БД откатилась,
    # кропы и превью остаются на месте и прогон просто переиспользует их.
    if crops:
        report["files"].append(_wipe_dir(_crops_root()))

    if args.previews:
        report["files"].append(_wipe_dir(_preview_root()))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print(report)
        print("результаты очищены; запускайте «Обновление базы» заново")

    return 0


def _print(report: dict) -> None:
    print(f"режим: {report['mode']}")
    print("будет удалено / осталось в базе:")
    for table, count in report["tables"].items():
        print(f"  {table:22s} {count}")
    print(f"  photos (остаются)      {report['photos']}")

    if report.get("removed"):
        print("удалено:")
        for table, count in report["removed"].items():
            print(f"  {table:22s} {count}")

    for item in report.get("files", []):
        print(
            f"  файлы {item['path']}: {item['files']} шт, "
            f"{item['bytes'] / 1024 ** 3:.2f} ГБ"
        )


if __name__ == "__main__":
    raise SystemExit(main())
