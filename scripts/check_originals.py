#!/usr/bin/env python
"""
Отчёт о доступности оригиналов: у каких фото файл пропал.

Только чтение: скрипт делает `resolve()` и `is_file()` по пути, сохранённому
в базе, и ничего не меняет — ни запись фото, ни превью, ни оригинал.

Зачем: основная масса данных лежит на сетевом томе. Если том отмонтирован,
уехал или файл удалили руками, фото в гриде остаётся, превью работает, а
«посмотреть/скачать» падает. Скрипт показывает масштаб заранее, до нажатия
кнопки: см. `GET /v1/photos/{photo_id}/original/status` в UI и
`docs/preview.txt`.

Тот же обход выполняется заданием ORIGINALS_CHECK из технического раздела
(«Данные» → «Доступность оригиналов»): счётчики и причины общие — см.
`app/originals/check.py`. Здесь остаются только аргументы, вывод и код возврата,
чтобы ручная проверка и кнопка не разошлись в трактовке.

Использование:

    .venv/bin/python scripts/check_originals.py --dry-run
    .venv/bin/python scripts/check_originals.py --json --limit 50000
    .venv/bin/python scripts/check_originals.py --photo-id PH_ab... --photo-id PH_cd...

Код возврата 1, если найдены недоступные оригиналы (удобно для алерта),
2 — ошибка конфигурации (не задан SCENE_ORIGINALS_ROOTS).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.config import ORIGINALS_ROOTS  # noqa: E402
from app.originals.check import REASONS, scan  # noqa: E402

# В консольном отчёте примеров меньше, чем в файле отчёта задания.
_SAMPLE_LIMIT = 20


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Проверить, доступны ли оригиналы зарегистрированных фото",
    )
    parser.add_argument("--dry-run", action="store_true", help="ничего не менять (по умолчанию и так только чтение)")
    parser.add_argument("--json", action="store_true", help="машиночитаемый вывод")
    parser.add_argument("--limit", type=int, default=0, help="проверить не больше N фото (0 — все)")
    parser.add_argument(
        "--photo-id",
        dest="photo_ids",
        action="append",
        default=None,
        help="проверить только это фото (можно повторить)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not ORIGINALS_ROOTS:
        print(
            "SCENE_ORIGINALS_ROOTS не задан: оригиналы не отдаются, "
            "проверять нечего",
            file=sys.stderr,
        )
        return 2

    counts = scan(
        ORIGINALS_ROOTS,
        photo_ids=args.photo_ids,
        limit=max(0, args.limit),
    )

    report = {
        "checked": counts["checked"],
        "available": counts["available"],
        "missing": counts["missing"],
        "outside_roots": counts["outside_roots"],
        "root_unavailable": counts["root_unavailable"],
        # В консольном отчёте — число корней; полный список с состоянием
        # каталогов отдаёт /v1/originals/health и файл отчёта задания.
        "roots": len(ORIGINALS_ROOTS),
        "samples": counts["samples"][:_SAMPLE_LIMIT],
        "dry_run": True,
        "limit": max(0, args.limit),
        "photo_ids": args.photo_ids or [],
    }

    missing = counts["missing"]
    outside = counts["outside_roots"]
    root_unavailable = counts["root_unavailable"]

    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    else:
        print(f"проверено: {report['checked']}")
        print(f"доступно:  {report['available']}")
        print(f"не найдено: {missing}")
        if outside:
            print(f"вне разрешённых корней: {outside}")
        if root_unavailable:
            print(f"корень оригиналов не подключён: {root_unavailable}")
        for sample in report["samples"]:
            print(f"  {sample['photo_id']}: {sample['reason']}")
        if root_unavailable:
            print(
                "\nКорень оригиналов не смонтирован: проверьте тома из "
                "SCENE_ORIGINALS_ROOTS или перенесите пути "
                "(scripts/remap_source_root.py)."
            )
        if missing or outside:
            print(
                "\nЗаписи фото не удаляются: в гриде доступно превью, "
                "а «посмотреть/скачать» покажет «оригинал недоступен»."
            )

    return 1 if (missing or outside or root_unavailable) else 0


if __name__ == "__main__":
    raise SystemExit(main())
