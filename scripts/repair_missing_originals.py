#!/usr/bin/env python
"""
Перевесить записи фото, чей оригинал пропал, на найденные копии файлов.

Зачем: photo_id строится из метаданных снимка (камера, время, размер), поэтому
копия или переименованная копия того же кадра — это та же запись. Когда папку
корпуса переименовали или разложили по-другому, `source_path` в базе продолжает
указывать на старое место: фото остаётся в базе, превью и распознавание целы,
но оригинал «недоступен». Инспектор такую запись не перерегистрирует (он видит,
что кадр уже в базе), поэтому путь нужно перевесить отдельно.

Что делает: находит строки `photos`, у которых файла по записанному пути нет,
и ищет в указанной папке файл с той же identity (тот же photo_id). По флагу
`--apply` обновляет `source_path` и `filename`. `photo_id`, `identity_hash`,
`sha256`, превью, DINO/HYBRID и QWEN не меняются — это тот же снимок.

По умолчанию — dry-run: показывает, сколько записей нашлось и какие примеры
изменятся, ничего не пишет. Перед записью полные старые и новые значения
сохраняются в `data/reports/originals_repointed_<штамп>.json` (след, не откат).

    .venv/bin/python scripts/repair_missing_originals.py \
        --from-folder /media/alexice/TEST/новаябазафото/ноябрь/11,11

    .venv/bin/python scripts/repair_missing_originals.py \
        --from-folder ... --scope /media/alexice/TEST/новаябазафото/октябрь/ноябрь --apply

`--scope` ограничивает, среди каких записей искать сломанные пути (префикс
source_path); без него проверяется вся таблица.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.config import ORIGINALS_ROOTS  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from app.ingest.metadata_pipeline import process_file_metadata  # noqa: E402

REPORT_DIR = Path(os.getenv("SCENE_DATA", "data")) / "reports"
REPORT_PREFIX = "originals_repointed"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def _inside_allowed_roots(path: str) -> bool:
    """API отдаёт оригинал только из разрешённых корней — новый путь должен
    быть внутри, иначе запись снова окажется «недоступной»."""

    for root in ORIGINALS_ROOTS:
        root = str(root).rstrip("/")
        if path == root or path.startswith(root + "/"):
            return True

    return False


def _rows(scope: str | None) -> list[dict]:
    sql = (
        "SELECT photo_id, source_path, filename, identity_hash, sha256 "
        "FROM public.photos"
    )
    params: tuple = ()

    if scope:
        sql += " WHERE source_path LIKE %s"
        params = (scope.rstrip("/") + "/%",)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [description[0] for description in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]


def _candidates(folder: str) -> dict[str, list[tuple[str, str]]]:
    """photo_id -> [(filename, path)] для файлов папки (рекурсивно)."""

    found: dict[str, list[tuple[str, str]]] = {}

    for base, _dirs, files in os.walk(folder):
        for name in sorted(files):
            if Path(name).suffix.lower() not in IMAGE_SUFFIXES:
                continue

            path = os.path.join(base, name)
            try:
                record = process_file_metadata(path)
            except Exception:  # noqa: BLE001 - битый файл не должен ронять проход
                continue

            found.setdefault(record.photo_id, []).append((name, path))

    return found


def plan(
    rows: list[dict],
    candidates: dict[str, list[tuple[str, str]]],
) -> dict:
    """
    Что можно починить: сломанные строки, для которых есть рабочий файл.

    Неоднозначность (два файла с одной identity) и путь вне разрешённых
    корней — отдельные списки: такие строки молча не меняются.
    """

    broken = []
    repairable = []
    ambiguous = []
    outside_roots = []
    already_ok = 0

    for row in rows:
        path = row["source_path"]

        if path and os.path.isfile(path):
            already_ok += 1
            continue

        broken.append(row)
        matches = candidates.get(row["photo_id"]) or []

        if len(matches) > 1:
            ambiguous.append({**row, "matches": [m[1] for m in matches]})
            continue

        if not matches:
            continue

        name, new_path = matches[0]

        if not _inside_allowed_roots(new_path):
            outside_roots.append({**row, "new_path": new_path})
            continue

        repairable.append(
            {
                "photo_id": row["photo_id"],
                "old_path": path,
                "old_filename": row["filename"],
                "new_path": new_path,
                "new_filename": name,
            }
        )

    return {
        "checked": len(rows),
        "already_ok": already_ok,
        "broken": len(broken),
        "repairable": repairable,
        "ambiguous": ambiguous,
        "outside_roots": outside_roots,
    }


def _report_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORT_DIR / f"{REPORT_PREFIX}_{stamp}.json"

    counter = 2
    while path.exists():
        path = REPORT_DIR / f"{REPORT_PREFIX}_{stamp}_{counter}.json"
        counter += 1

    return path


def apply(repairable: list[dict]) -> tuple[int, Path | None]:
    if not repairable:
        return 0, None

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = _report_path()
    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "records": repairable,
    }

    with open(report_path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)

    updated = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            for item in repairable:
                # Путь в WHERE защищает от гонки: строку мог починить другой
                # проход, пока мы сканировали папку.
                cur.execute(
                    "UPDATE public.photos SET source_path=%s, filename=%s "
                    "WHERE photo_id=%s AND source_path=%s",
                    (
                        item["new_path"],
                        item["new_filename"],
                        item["photo_id"],
                        item["old_path"],
                    ),
                )
                updated += cur.rowcount

    return updated, report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-folder",
        required=True,
        help="папка с рабочими копиями файлов (сканируется рекурсивно)",
    )
    parser.add_argument(
        "--scope",
        default=None,
        help="проверять только записи с этим префиксом source_path",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="обновить пути (по умолчанию только показать)",
    )
    parser.add_argument("--json", action="store_true", help="вывод в JSON")
    args = parser.parse_args()

    folder = args.from_folder
    if not os.path.isdir(folder):
        print(f"Папка не найдена: {folder}")
        return 2

    rows = _rows(args.scope)
    candidates = _candidates(folder)
    result = plan(rows, candidates)

    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "folder": folder,
        "scope": args.scope,
        "checked": result["checked"],
        "already_ok": result["already_ok"],
        "broken": result["broken"],
        "repairable": len(result["repairable"]),
        "ambiguous": len(result["ambiguous"]),
        "outside_roots": len(result["outside_roots"]),
    }

    if args.apply:
        updated, report_path = apply(result["repairable"])
        payload["updated"] = updated
        payload["report"] = str(report_path) if report_path else None
    else:
        payload["updated"] = 0
        payload["report"] = None
        payload["records"] = result["repairable"][:20]

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(
        f"Проверено записей: {payload['checked']}, на месте: {payload['already_ok']}, "
        f"без файла: {payload['broken']}"
    )
    print(f"Найдены рабочие копии: {payload['repairable']}")

    if result["ambiguous"]:
        print(f"Неоднозначно (несколько копий): {len(result['ambiguous'])} — пропущены")
        for item in result["ambiguous"][:5]:
            print(f"  {item['photo_id']}  {item['old_filename']}")

    if result["outside_roots"]:
        print(
            f"Копии вне разрешённых корней: {len(result['outside_roots'])} — "
            "пропущены, добавьте корень в SCENE_ORIGINALS_ROOTS"
        )

    for item in result["repairable"][:10]:
        print(f"  {item['photo_id']}")
        print(f"    было:  {item['old_path']}")
        print(f"    стало: {item['new_path']}")

    if not args.apply:
        print("\nНичего не изменено. Для записи добавьте --apply.")
        return 0

    print(f"\nОбновлено записей: {payload['updated']}")
    if payload["report"]:
        print(f"След сохранён: {payload['report']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
