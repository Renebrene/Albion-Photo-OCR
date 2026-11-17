#!/usr/bin/env python
"""
Обновить блок `weights` в metadata.json слепков.

Блок `weights` в metadata.json описывает веса компонентов при ранжировании
DINO (global/environment/color/spatial). Он пишется при сборке слепка и
остаётся со старыми значениями после смены весов в `app/dino/runner.py`.
Скрипт приводит блок к текущим весам; векторы и остальные ключи не трогаются.

Зачем: таблица слепков и «Качество распознавания» показывают этот блок как
справку; расхождение с реальными весами вводит в заблуждение.

Что делает, для каждого слепка, где блок отличается:

  1. читает metadata.json;
  2. заменяет только ключ `weights` (отсутствующий — добавляется);
  3. пишет metadata.json атомарно (временный файл → os.replace).

Использование:

    python scripts/backfill_fingerprint_weights.py --dry-run
    python scripts/backfill_fingerprint_weights.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_FINGERPRINTS = ROOT / "data" / "fingerprints"

# Текущие веса ранжирования DINO (app/dino/runner.py). Менять и здесь, и там.
CURRENT_WEIGHTS = {
    "global": 0.40,
    "environment": 0.35,
    "color": 0.00,
    "spatial": 0.25,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", type=Path, default=DEFAULT_FINGERPRINTS)
    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(f"fingerprints root not found: {args.root}", file=sys.stderr)
        return 2

    updated = 0
    unchanged = 0

    for metadata_path in sorted(args.root.glob("*/metadata.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        if metadata.get("weights") == CURRENT_WEIGHTS:
            unchanged += 1
            continue

        updated += 1
        old = metadata.get("weights")

        if args.dry_run:
            print(
                f"[weights] {metadata_path.parent.name}: "
                f"{old} -> {CURRENT_WEIGHTS}"
            )
            continue

        metadata["weights"] = dict(CURRENT_WEIGHTS)

        fd, temp_name = tempfile.mkstemp(
            dir=metadata_path.parent,
            prefix=".metadata.",
            suffix=".tmp",
        )
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(temp_name, metadata_path)

    action = "обновлено бы" if args.dry_run else "обновлено"
    print(
        f"[weights] слепков: {action} {updated}, без изменений {unchanged}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
