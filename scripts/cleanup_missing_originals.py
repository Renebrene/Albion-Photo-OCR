#!/usr/bin/env python3
"""Remove previews for photos whose originals are gone.

QWEN rows, photo rows and regions are deliberately preserved.  Preview files
are moved to a quarantine directory instead of being unlinked, so the action
is reversible; the ``photo_previews`` row is deleted.

    .venv/bin/python scripts/cleanup_missing_originals.py --dry-run
    .venv/bin/python scripts/cleanup_missing_originals.py --apply --confirm CLEANUP
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.config import PREVIEW_ROOT  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from app.preview.generator import build_preview_paths  # noqa: E402

OUT = Path("data/experiments/cleanup_missing_originals")
QUARANTINE = Path("data/preview_quarantine")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args(argv)

    if args.apply and args.confirm != "CLEANUP":
        print("refusing; pass --apply --confirm CLEANUP", file=sys.stderr)
        return 2
    if args.apply and args.dry_run:
        print("choose either --dry-run or --apply", file=sys.stderr)
        return 2

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT photo_id, source_path FROM public.photos")
            rows = cur.fetchall()

    missing = [
        (str(photo_id), str(source_path))
        for photo_id, source_path in rows
        if not os.path.isfile(str(source_path))
    ]

    affected = []
    for photo_id, source_path in missing:
        paths = build_preview_paths(
            preview_root=PREVIEW_ROOT, photo_id=photo_id
        )
        files = [path for path in (paths.small, paths.middle) if path.is_file()]
        if files:
            affected.append(
                {
                    "photo_id": photo_id,
                    "source_path": source_path,
                    "files": [str(path) for path in files],
                }
            )

    report = {
        "dry_run": not args.apply,
        "missing_originals": len(missing),
        "with_previews": len(affected),
        "files": sum(len(item["files"]) for item in affected),
        "quarantine": str(QUARANTINE),
        "samples": affected[:10],
    }

    if not args.apply:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    QUARANTINE.mkdir(parents=True, exist_ok=True)
    moved = 0
    deleted_rows = 0

    for item in affected:
        photo_id = item["photo_id"]
        target = QUARANTINE / photo_id
        target.mkdir(parents=True, exist_ok=True)
        for path_value in item["files"]:
            path = Path(path_value)
            try:
                shutil.move(str(path), str(target / path.name))
                moved += 1
            except OSError:
                pass

    with get_connection() as conn:
        with conn.cursor() as cur:
            ids = [item["photo_id"] for item in affected]
            for start in range(0, len(ids), 500):
                chunk = ids[start : start + 500]
                cur.execute(
                    "DELETE FROM public.photo_previews "
                    "WHERE photo_id = ANY(%s)",
                    (chunk,),
                )
                deleted_rows += cur.rowcount
        conn.commit()

    report["moved_files"] = moved
    report["deleted_preview_rows"] = deleted_rows
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        f"[cleanup] missing={len(missing)} with_previews={len(affected)} "
        f"moved={moved} rows={deleted_rows}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
