#!/usr/bin/env python
"""
How many photos does a fingerprint need, and which ones? (backlog item 4)

Builds, for every address, an alternative fingerprint from a subset of source
photos and compares what recognition says about a held-out corpus with what the
production fingerprint set says.

Two ways to pick the subset:

  * `--select stride` (default) - every Nth photo from the sorted list, which is
    how the 10/15/20/30/40 measurement was run;
  * `--select scene` - `app/core/scene_select.py`: 20-30 photos from different
    shooting conditions (pHash/dHash/colour/brightness, one medoid per cluster),
    built as `<address>_v34` (dHash on) and `<address>_v34nd` (off).

Nothing in the working set is touched:

  * the variant fingerprints are written under --scratch (SCENE_DATA is pointed
    there for both `create` and `recognize`), so data/fingerprints keeps its
    production fingerprints;
  * recognition is run through the CLI (`app.cli recognize`), which only reads
    fingerprints and images - no PostgreSQL, no job queue;
  * the source photos are only read, then copied into the scratch input folder
    that the builder walks (the fingerprint builder works on folders).

Usage:
    python scripts/fingerprint_size_experiment.py --dry-run
    python scripts/fingerprint_size_experiment.py
    python scripts/fingerprint_size_experiment.py --select scene
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.scene_select import (  # noqa: E402
    DEFAULT_SELECT_MAX,
    DEFAULT_SELECT_MIN,
    select_scene_photos,
)

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


def effective_size(count: int, size: int) -> int:
    """Photos actually used for a variant: never more than the address has."""

    return min(size, count)


def planned_variants(count: int, variants: list[int]) -> list[int]:
    """
    The subset size each variant really uses for this address.

    An address with fewer photos than the requested size keeps *all* of them
    instead of dropping out of the set: a set missing whole addresses would
    measure the effect of absent fingerprints, not the effect of a smaller
    fingerprint. The returned values are the effective sizes.
    """

    return sorted({effective_size(count, size) for size in variants})


class Variant(NamedTuple):
    """One fingerprint set of the comparison."""

    name: str  # v20 / v34 / v34nd - used as the scratch folder name
    mode: str  # stride (every Nth photo) | scene (app/core/scene_select.py)
    size: int | None  # requested size, stride only
    use_dhash: bool  # feature composition, scene only

    def label(self) -> str:
        """Human label for the report table."""

        if self.mode == "stride":
            return f"{self.size} фото шагом"

        return "сцены, dHash" if self.use_dhash else "сцены, без dHash"

    def fingerprint_id(self, address_id: str, selected: int) -> str:
        """Id of the built fingerprint; the size is visible for stride runs."""

        if self.mode == "stride":
            return f"{address_id}_v33_s{selected}"

        return f"{address_id}_v34" if self.use_dhash else f"{address_id}_v34nd"


def scene_variants(names: str) -> list[Variant]:
    """Scene sets to build: with dHash (v34) and/or without it (v34nd)."""

    known = {
        "v34": Variant("v34", "scene", None, True),
        "v34nd": Variant("v34nd", "scene", None, False),
    }

    chosen = [
        known[item.strip()] for item in str(names).split(",") if item.strip() in known
    ]

    return chosen or [known["v34"]]


def scene_subset(
    photos: list[Path],
    *,
    workers: int,
    use_dhash: bool,
    select_min: int,
    select_max: int,
) -> tuple[list[Path], dict]:
    """Pick 20-30 photos from different shooting conditions, plus diagnostics."""

    result = select_scene_photos(
        photos,
        workers=workers,
        select_min=select_min,
        select_max=select_max,
        use_dhash=use_dhash,
    )

    return [Path(path) for path in result["picked"]], result


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


def run_cli(
    args: list[str],
    *,
    env_data_dir: Path,
    timeout: int = 3600,
    threads: int | None = None,
) -> str:
    """Run `python -m app.cli ...` with SCENE_DATA pointed at the scratch root."""

    env = dict(os.environ)
    env["SCENE_DATA"] = str(env_data_dir)

    if threads:
        # Building is CPU-bound; several builders at once must not each grab
        # every core, so the pool hands each child its own budget.
        env["OMP_NUM_THREADS"] = str(threads)
        env["MKL_NUM_THREADS"] = str(threads)

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


def address_key(fingerprint_id: str | None) -> str | None:
    """
    Verdicts are compared by address, not by fingerprint version.

    78_v33, 78_v33_s20 and 78_v34 all mean address 78: the run being measured
    differs in which photos went into the fingerprint, not in which address it
    describes.
    """

    if not fingerprint_id:
        return None

    head, sep, _tail = str(fingerprint_id).partition("_")

    return head if sep else str(fingerprint_id)


def compare(
    baseline: dict[str, dict],
    variant: dict[str, dict],
) -> dict:
    """Agreement between a variant run and the production fingerprints."""

    shared = sorted(set(baseline) & set(variant))
    same = 0
    changed: list[dict] = []

    for name in shared:
        want = address_key(best_id(baseline[name]))
        got = address_key(best_id(variant[name]))

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
        help="Subset sizes to test (comma separated, stride mode only)",
    )
    parser.add_argument(
        "--select",
        choices=["stride", "scene"],
        default="stride",
        help=(
            "How the subset is picked: 'stride' - every Nth photo (the original "
            "size measurement); 'scene' - 20-30 photos from different shooting "
            "conditions (app/core/scene_select.py)"
        ),
    )
    parser.add_argument(
        "--scene-sets",
        default="v34,v34nd",
        help="Scene sets to build: v34 (with dHash) and/or v34nd (without)",
    )
    parser.add_argument(
        "--select-min",
        type=int,
        default=DEFAULT_SELECT_MIN,
        help="Scene mode: fewest photos per fingerprint",
    )
    parser.add_argument(
        "--select-max",
        type=int,
        default=DEFAULT_SELECT_MAX,
        help="Scene mode: most photos per fingerprint",
    )
    parser.add_argument(
        "--decode-workers",
        type=int,
        default=0,
        help="Scene mode: processes hashing the photos (0 - all cores)",
    )
    parser.add_argument(
        "--build-workers",
        type=int,
        default=max(1, (os.cpu_count() or 1) // 2),
        help=(
            "fingerprints built at once; each child gets cores/workers torch "
            "threads (default: half the cores)"
        ),
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
        "--build-only",
        action="store_true",
        help="Build the variant fingerprints and stop (no recognition runs)",
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

    if args.select == "scene":
        variants = scene_variants(args.scene_sets)
    else:
        variants = [
            Variant(f"v{int(item)}", "stride", int(item), False)
            for item in str(args.variants).split(",")
            if item.strip()
        ]

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
        entry = {
            "address": address_id,
            "photos": len(photos),
            "sets": [variant.name for variant in variants],
        }

        if args.select == "stride":
            entry["variant_sizes"] = planned_variants(
                len(photos), [variant.size for variant in variants]
            )
        else:
            entry["select_range"] = [args.select_min, args.select_max]

        plan.append(entry)

    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    started = time.time()
    report: dict = {
        "corpus": str(args.corpus),
        "mode": args.select,
        "variants": [variant.name for variant in variants],
        "plan": plan,
        "runs": {},
        "selections": {},
    }

    # ---- 1. build the variant fingerprint sets -------------------------------
    threads = max(1, (os.cpu_count() or 1) // max(1, args.build_workers))
    decode_workers = max(1, args.decode_workers or (os.cpu_count() or 1))

    for variant in variants:
        data_dir = args.scratch / variant.name / "data"

        if args.skip_build and (data_dir / "fingerprints").is_dir():
            log(f"{variant.name}: reusing {data_dir / 'fingerprints'}")
            continue

        jobs = []

        for address_id, folder, photos in addresses:
            if variant.mode == "scene":
                subset, diagnostics = scene_subset(
                    photos,
                    workers=decode_workers,
                    use_dhash=variant.use_dhash,
                    select_min=args.select_min,
                    select_max=args.select_max,
                )

                if not subset:
                    log(f"  {address_id}: no readable photos, skipped")
                    continue

                report["selections"].setdefault(variant.name, {})[address_id] = {
                    "photos": len(photos),
                    "series": diagnostics["series"],
                    "natural_scenes": diagnostics["natural_scenes"],
                    "scenes": diagnostics["scenes"],
                    "picked": len(subset),
                }
            else:
                # An address with fewer photos than requested keeps all of them;
                # the id carries the size actually used.
                subset = sample(photos, effective_size(len(photos), variant.size))

            fingerprint_id = variant.fingerprint_id(address_id, len(subset))
            input_dir = args.scratch / variant.name / "input" / fingerprint_id
            write_source_subset(subset, input_dir)

            jobs.append((fingerprint_id, input_dir))

        log(
            f"{variant.name} ({variant.label()}): building {len(jobs)} fingerprints "
            f"({args.build_workers} at a time, {threads} threads each)"
        )

        with ThreadPoolExecutor(max_workers=max(1, args.build_workers)) as pool:
            futures = {
                pool.submit(
                    run_cli,
                    ["create", fingerprint_id, str(input_dir)],
                    env_data_dir=data_dir,
                    threads=threads,
                ): fingerprint_id
                for fingerprint_id, input_dir in jobs
            }

            for future in as_completed(futures):
                fingerprint_id = futures[future]
                future.result()  # re-raise a builder failure
                log(f"  built {fingerprint_id}")

    if args.build_only:
        log(f"build only: {round(time.time() - started, 1)} s")
        return 0

    # ---- 2. recognition runs -------------------------------------------------
    log("recognising the corpus with the production fingerprints")
    baseline = recognize_corpus(
        args.corpus,
        data_dir=ROOT / "data",
        top_k=args.top_k,
        workers=args.workers,
    )

    report["runs"]["production"] = {
        "label": "текущие",
        "fingerprints": sorted(
            path.name for path in (ROOT / "data" / "fingerprints").iterdir() if path.is_dir()
        ),
        "recognised": len(baseline),
        "best": {name: address_key(best_id(row)) for name, row in baseline.items()},
    }

    for variant in variants:
        data_dir = args.scratch / variant.name / "data"

        log(f"recognising the corpus with {variant.name} ({variant.label()})")
        verdicts = recognize_corpus(
            args.corpus,
            data_dir=data_dir,
            top_k=args.top_k,
            workers=args.workers,
        )

        report["runs"][variant.name] = {
            "label": variant.label(),
            "recognised": len(verdicts),
            "comparison": compare(baseline, verdicts),
            "best": {name: address_key(best_id(row)) for name, row in verdicts.items()},
        }

    report["seconds"] = round(time.time() - started, 1)
    report["build_workers"] = args.build_workers
    report["baseline_verdicts"] = {
        name: address_key(best_id(row)) for name, row in baseline.items()
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

    for variant in variants:
        run = report["runs"].get(variant.name)

        if not run:
            continue

        comparison = run["comparison"]
        lines.append(
            f"| {run['label']} ({variant.name}) | {comparison['same']} | "
            f"{comparison['share']} | {len(comparison['changed'])} |"
        )

    lines.append("")
    lines.append("## Сколько фото попадает на каждый адрес")
    lines.append("")

    addresses = sorted(
        {
            value
            for run in report["runs"].values()
            for value in (run.get("best") or {}).values()
            if value
        }
    )

    def counts(run_name):
        best = report["runs"][run_name].get("best") or {}
        result = {address: 0 for address in addresses}
        for value in best.values():
            if value in result:
                result[value] += 1
        return result

    columns = ["production"] + [
        variant.name for variant in variants if report["runs"].get(variant.name)
    ]
    per_address = {name: counts(name) for name in columns}

    header = "| Адрес | " + " | ".join(
        (
            "текущее"
            if name == "production"
            else report["runs"][name].get("label", name)
        )
        for name in columns
    ) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(columns) + 1))

    for address in addresses:
        row = [f"{address}"]
        for name in columns:
            value = per_address[name][address]
            base = per_address["production"][address]
            delta = "" if name == "production" or value == base else f" ({value - base:+d})"
            row.append(f"{value}{delta}")
        lines.append("| " + " | ".join(row) + " |")

    if report["selections"]:
        lines.append("")
        lines.append("## Состав слепка по сценам (что выбрано из папки)")
        lines.append("")
        lines.append("| Адрес | Фото в папке | Серий | Сцен нашлось | Сцен взято | В слепке |")
        lines.append("|---|---|---|---|---|---|")

        for variant in variants:
            selection = report["selections"].get(variant.name) or {}

            if not selection:
                continue

            lines.append(f"| **{variant.label()}** | | | | | |")

            for address in sorted(selection):
                cell = selection[address]
                lines.append(
                    f"| {address} | {cell['photos']} | {cell['series']} | "
                    f"{cell['natural_scenes']} | {cell['scenes']} | {cell['picked']} |"
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
