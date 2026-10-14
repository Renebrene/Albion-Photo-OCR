#!/usr/bin/env python
"""
How many photos does a fingerprint need? (backlog item 4)

Builds, for every address, an alternative fingerprint from a subset of 20/30/40
source photos and compares what recognition says about a held-out corpus with
what the production fingerprint set says.

Nothing in the working set is touched:

  * the variant fingerprints are written under --scratch (SCENE_DATA is pointed
    there for both `create` and `recognize`), so data/fingerprints keeps its
    18 production fingerprints;
  * recognition is run through the CLI (`app.cli recognize`), which only reads
    fingerprints and images - no PostgreSQL, no job queue;
  * the source photos are only read, then copied into the scratch input folder
    that the builder walks (the fingerprint builder works on folders).

Usage:
    python scripts/fingerprint_size_experiment.py --dry-run
    python scripts/fingerprint_size_experiment.py
    python scripts/fingerprint_size_experiment.py --variants 20,30 --limit 3

Output: a JSON + Markdown report under --report-dir (default
data/output/fingerprint_size_experiment) and a short summary on stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SOURCE_ROOT = ROOT / "data" / "input"
DEFAULT_CORPUS = Path("/home/alexice/Desktop/test")
DEFAULT_SCRATCH = ROOT / "data" / "output" / "fingerprint_size_experiment"
DEFAULT_REPORT_DIR = DEFAULT_SCRATCH
SUPPORTED_SUFFIXES = {".jpg", ".jpeg"}


def log(message: str) -> None:
    print(f"[experiment] {message}", flush=True)


def source_folders(root: Path) -> list[tuple[str, Path, list[Path]]]:
    """[(address_id, folder, photos)] for every folder that has photos."""

    items: list[tuple[str, Path, list[Path]]] = []

    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue

        photos = sorted(
            path
            for path in folder.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        )

        if photos:
            items.append((folder.name, folder, photos))

    return items


def sample(photos: list[Path], count: int) -> list[Path]:
    """
    Take *count* photos spread across the list.

    A stride instead of "the first N": the files are sorted by name, so the
    first N would be one burst of shots from the same moment and viewpoint.
    """

    if count >= len(photos):
        return list(photos)

    stride = len(photos) / count

    return [photos[int(index * stride)] for index in range(count)]


def planned_variants(count: int, variants: list[int]) -> list[int]:
    """Variants that fit: never more photos than the address actually has."""

    return [size for size in variants if size <= count]


def production_addresses(fingerprints_root: Path) -> set[str]:
    """Address ids that have a production fingerprint (78_v33 -> 78)."""

    if not fingerprints_root.is_dir():
        return set()

    result = set()

    for directory in fingerprints_root.iterdir():
        if not directory.is_dir():
            continue

        name = directory.name
        head, sep, _tail = name.partition("_")

        if sep and head:
            result.add(head)

    return result


def run_cli(args: list[str], *, env_data_dir: Path, timeout: int = 3600) -> str:
    """Run `python -m app.cli ...` with SCENE_DATA pointed at the scratch root."""

    env = dict(os.environ)
    env["SCENE_DATA"] = str(env_data_dir)

    completed = subprocess.run(
        [sys.executable, "-m", "app.cli", *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip().splitlines()[-3:]
        raise RuntimeError(f"app.cli {' '.join(args)} failed: {' | '.join(tail)}")

    return completed.stdout


def parse_recognize_json(stdout: str) -> list[dict]:
    """The CLI prints service lines before the JSON array; take the last one."""

    start = None
    lines = stdout.splitlines()

    for index, line in enumerate(lines):
        if line.strip() == "[":
            start = index
            break

    if start is None:
        raise RuntimeError("recognize printed no JSON array")

    return json.loads("\n".join(lines[start:]))


def write_source_subset(
    photos: list[Path],
    destination: Path,
) -> None:
    """Copy the sampled photos into the folder the builder will walk."""

    if destination.exists():
        shutil.rmtree(destination)

    destination.mkdir(parents=True, exist_ok=True)

    for photo in photos:
        shutil.copy2(photo, destination / photo.name)


def recognize_corpus(
    corpus: Path,
    *,
    data_dir: Path,
    top_k: int,
    workers: int,
) -> dict[str, dict]:
    """{photo filename: best_id/top list/score} for one fingerprint set."""

    stdout = run_cli(
        [
            "recognize",
            str(corpus),
            "--top-k",
            str(top_k),
            "--workers",
            str(workers),
            "--json",
        ],
        env_data_dir=data_dir,
    )

    results = parse_recognize_json(stdout)

    verdicts: dict[str, dict] = {}

    for row in results:
        name = Path(str(row.get("file") or row.get("filename") or "")).name
        verdicts[name] = row

    return verdicts


def best_id(row: dict | None) -> str | None:
    if not row:
        return None

    for key in ("best_id", "fingerprint", "matched_id"):
        value = row.get(key)

        if value:
            return str(value)

    candidates = row.get("candidates") or row.get("top") or []

    if candidates and isinstance(candidates[0], dict):
        value = candidates[0].get("id") or candidates[0].get("fingerprint_id")
        return str(value) if value else None

    return None


def strip_variant(fingerprint_id: str | None) -> str | None:
    """78_v33_s20 -> 78_v33 (so variants compare against the production ids)."""

    if not fingerprint_id:
        return None

    marker = "_s"
    head, sep, tail = fingerprint_id.rpartition(marker)

    if sep and tail.isdigit():
        return head

    return fingerprint_id


def compare(
    baseline: dict[str, dict],
    variant: dict[str, dict],
) -> dict:
    """Agreement between a variant run and the production fingerprints."""

    shared = sorted(set(baseline) & set(variant))
    same = 0
    changed: list[dict] = []

    for name in shared:
        want = strip_variant(best_id(baseline[name]))
        got = strip_variant(best_id(variant[name]))

        if want == got:
            same += 1
        else:
            changed.append({"file": name, "baseline": want, "variant": got})

    total = len(shared)

    return {
        "photos": total,
        "same": same,
        "share": round(same / total, 4) if total else None,
        "changed": changed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--scratch", type=Path, default=DEFAULT_SCRATCH)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument(
        "--variants",
        default="20,30,40",
        help="Subset sizes to test (comma separated)",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only the first N addresses (a quick smoke test)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan (addresses, subsets, variants) and stop",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Reuse fingerprints already present in the scratch root",
    )
    parser.add_argument(
        "--include-new-addresses",
        action="store_true",
        help=(
            "Also measure folders that have no production fingerprint "
            "(64, 65): taking part in the build makes the comparison noisy, "
            "because the reference set then differs in composition"
        ),
    )

    args = parser.parse_args()

    variants = [int(item) for item in str(args.variants).split(",") if item.strip()]

    if not args.source_root.is_dir():
        print(f"source root not found: {args.source_root}", file=sys.stderr)
        return 2

    if not args.corpus.is_dir():
        print(f"corpus not found: {args.corpus}", file=sys.stderr)
        return 2

    addresses = source_folders(args.source_root)

    if not args.include_new_addresses:
        known = production_addresses(ROOT / "data" / "fingerprints")
        skipped = [item[0] for item in addresses if item[0] not in known]
        addresses = [item for item in addresses if item[0] in known]

        if skipped:
            log(f"skipping folders without a production fingerprint: {skipped}")

    if args.limit:
        addresses = addresses[: args.limit]

    if not addresses:
        print("no source folders with photos", file=sys.stderr)
        return 2

    plan = []

    for address_id, folder, photos in addresses:
        plan.append(
            {
                "address": address_id,
                "photos": len(photos),
                "variants": planned_variants(len(photos), variants),
            }
        )

    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    started = time.time()
    report: dict = {
        "corpus": str(args.corpus),
        "variants": variants,
        "plan": plan,
        "runs": {},
    }

    # ---- 1. build the variant fingerprint sets -------------------------------
    for size in variants:
        data_dir = args.scratch / f"v{size}" / "data"

        if args.skip_build and (data_dir / "fingerprints").is_dir():
            log(f"v{size}: reusing {data_dir / 'fingerprints'}")
            continue

        log(f"v{size}: building fingerprints")

        for address_id, folder, photos in addresses:
            if size not in planned_variants(len(photos), variants):
                continue

            subset = sample(photos, size)
            fingerprint_id = f"{address_id}_v33_s{size}"

            input_dir = args.scratch / f"v{size}" / "input" / fingerprint_id
            write_source_subset(subset, input_dir)

            log(f"  {fingerprint_id}: {len(subset)}/{len(photos)} photos")

            run_cli(
                ["create", fingerprint_id, str(input_dir)],
                env_data_dir=data_dir,
            )

    # ---- 2. recognition runs -------------------------------------------------
    log("recognising the corpus with the production fingerprints")
    baseline = recognize_corpus(
        args.corpus,
        data_dir=ROOT / "data",
        top_k=args.top_k,
        workers=args.workers,
    )

    report["runs"]["production"] = {
        "fingerprints": sorted(
            path.name for path in (ROOT / "data" / "fingerprints").iterdir() if path.is_dir()
        ),
        "recognised": len(baseline),
    }

    for size in variants:
        data_dir = args.scratch / f"v{size}" / "data"

        log(f"recognising the corpus with the {size}-photo fingerprints")
        variant = recognize_corpus(
            args.corpus,
            data_dir=data_dir,
            top_k=args.top_k,
            workers=args.workers,
        )

        report["runs"][f"v{size}"] = {
            "recognised": len(variant),
            "comparison": compare(baseline, variant),
        }

    report["seconds"] = round(time.time() - started, 1)
    report["baseline_verdicts"] = {
        name: strip_variant(best_id(row)) for name, row in baseline.items()
    }

    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / "result.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = ["# Сколько фото нужно для слепка — замер", ""]
    lines.append(f"Корпус: {args.corpus} ({len(baseline)} фото)")
    lines.append("")
    lines.append("| Набор слепков | Совпало с рабочим | Доля | Изменилось |")
    lines.append("|---|---|---|---|")

    for size in variants:
        run = report["runs"].get(f"v{size}")

        if not run:
            continue

        comparison = run["comparison"]
        lines.append(
            f"| {size} фото на адрес | {comparison['same']} | "
            f"{comparison['share']} | {len(comparison['changed'])} |"
        )

    lines.append("")
    lines.append(f"Время: {report['seconds']} с")
    lines.append("")
    lines.append("Подробности: result.json")

    markdown_path = args.report_dir / "report.md"
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    log(f"report: {markdown_path}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
