from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer
from app.core.scene_analyzer import SceneAnalyzer
from app.pipeline.queue import JobQueue


def build_parser():
    parser = argparse.ArgumentParser(
        prog="scene-fingerprint",
        description=(
            "Scene fingerprinting and "
            "recognition v3.3 compact"
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------

    create_parser = subparsers.add_parser(
        "create",
        help="Create v3.3 compact fingerprint",
    )

    create_parser.add_argument(
        "fingerprint",
        help="Fingerprint ID",
    )

    create_parser.add_argument(
        "folder",
        help="Folder with reference images",
    )

    # --------------------------------------------------
    # INGEST
    # --------------------------------------------------

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Scan a folder and register its new photos (INGEST)",
    )

    ingest_parser.add_argument(
        "folder",
        help="Folder with working photos (scanned recursively)",
    )

    ingest_parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Parallel workers (default: half of the CPU threads)",
    )

    ingest_parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Hash every file, even when (name, size) is already registered",
    )

    ingest_parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Only look at the top level of the folder",
    )

    # --------------------------------------------------
    # QUEUE ADD
    # --------------------------------------------------

    queue_add_parser = subparsers.add_parser(
        "queue-add",
        help="Add fingerprint creation job to queue",
    )

    queue_add_parser.add_argument(
        "fingerprint",
        help="Fingerprint ID",
    )

    queue_add_parser.add_argument(
        "folder",
        help="Folder with reference images",
    )

    queue_add_parser.add_argument(
        "--priority",
        type=int,
        default=0,
        help="Job priority",
    )

    # --------------------------------------------------
    # QUEUE BATCH ADD
    # --------------------------------------------------

    queue_batch_parser = subparsers.add_parser(
        "queue-batch-add",
        help="Add a range of folders to fingerprint queue",
    )

    queue_batch_parser.add_argument(
        "start",
        type=int,
        help="First address ID",
    )

    queue_batch_parser.add_argument(
        "end",
        type=int,
        help="Last address ID",
    )

    queue_batch_parser.add_argument(
        "--priority",
        type=int,
        default=0,
        help="Queue priority",
    )

    # --------------------------------------------------
    # ANALYZE
    # --------------------------------------------------

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze one fingerprint",
    )

    analyze_parser.add_argument(
        "folder",
        help="Folder with query images",
    )

    analyze_parser.add_argument(
        "--fingerprint",
        required=True,
        help="Fingerprint ID",
    )

    # --------------------------------------------------
    # RECOGNIZE
    # --------------------------------------------------

    recognize_parser = subparsers.add_parser(
        "recognize",
        help="Recognize images",
    )

    recognize_parser.add_argument(
        "folder",
        help="Folder with query images",
    )

    recognize_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of candidates",
    )

    recognize_parser.add_argument(
        "--threshold",
        type=float,
        default=0.65,
        help="Minimum absolute match score",
    )

    recognize_parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Number of CPU workers for descriptor calculation",
    )

    recognize_parser.add_argument(
        "--fingerprints",
        type=str,
        default=None,
        help="Comma-separated fingerprint IDs to use",
    )

    recognize_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON",
    )

    return parser


def print_analyze_result(
    path,
    result,
):
    print()
    print(
        f"## {Path(path).name}"
    )
    print()

    print(
        f"GLOBAL        "
        f"{result['global_score']:.4f}"
    )

    print(
        f"BEST IMAGE    "
        f"{result['best_image_score']:.4f}"
    )

    print(
        "PATCH         "
        "0.0000 (DISABLED)"
    )

    print(
        f"COLOR         "
        f"{result['color_score']:.4f}"
    )

    print(
        f"SPATIAL       "
        f"{result['spatial_score']:.4f}"
    )

    print(
        f"ENVIRONMENT   "
        f"{result['environment_score']:.4f}"
    )

    print(
        f"FINAL         "
        f"{result['final_score']:.4f}"
    )

    print(
        f"BEST MATCH    "
        f"{result['best_image']}"
    )


def print_recognition_result(
    result,
):
    filename = Path(
        result["file"]
    ).name

    print()
    print(
        f"## {filename}"
    )
    print()

    best_id = result.get(
        "best_id"
    )

    score = float(
        result.get(
            "score",
            0.0,
        )
    )

    second_score = float(
        result.get(
            "second_score",
            0.0,
        )
    )

    margin = float(
        result.get(
            "margin",
            0.0,
        )
    )

    confidence = result.get(
        "confidence",
        "NO_MATCH",
    )

    status = result.get(
        "status",
        "NO_MATCH",
    )

    print(
        f"MATCH        "
        f"{best_id or 'NONE'}"
    )

    print(
        f"SCORE        "
        f"{score:.4f}"
    )

    print(
        f"SECOND       "
        f"{second_score:.4f}"
    )

    print(
        f"MARGIN       "
        f"{margin:.4f}"
    )

    print(
        f"CONFIDENCE   "
        f"{confidence}"
    )

    print(
        f"STATUS       "
        f"{status}"
    )

    best_image = result.get(
        "best_image"
    )

    if best_image:
        print(
            f"BEST IMAGE   "
            f"{best_image}"
        )

    candidates = result.get(
        "candidates",
        [],
    )

    if candidates:
        print()
        print(
            "TOP CANDIDATES"
        )

        for index, candidate in enumerate(
            candidates,
            start=1,
        ):
            print(
                f"{index}. "
                f"{candidate['id']:<14} "
                f"{candidate['score']:.4f}"
            )


def main():
    parser = build_parser()
    args = parser.parse_args()

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------

    if args.command == "ingest":

        from app.ingest.pipeline import DEFAULT_WORKERS
        from app.ingest.runner import ingest_directory

        folder = Path(args.folder)

        if not folder.is_dir():
            raise FileNotFoundError(f"Folder not found: {folder}")

        workers = args.workers or DEFAULT_WORKERS

        print(f"[Ingest] folder={folder}")
        print(f"[Ingest] workers={workers}")

        summary = ingest_directory(
            folder,
            workers=workers,
            skip_known=not args.no_skip,
            recursive=not args.no_recursive,
        )

        counters = summary["counters"]

        print(
            f"[Ingest] discovered={summary['discovered']} "
            f"valid={counters['VALID']} "
            f"skipped={counters['SKIPPED']} "
            f"invalid={counters['INVALID']}"
        )
        print(
            f"[Ingest] registered={summary['registered']} "
            f"existing={summary['existing']} "
            f"conflicts={len(summary['conflicts'])}"
        )

        for item in summary["errors"]:
            print(f"[Ingest] error {item['filename']}: {item['error']}")

        for photo_id in summary["conflicts"]:
            print(f"[Ingest] conflict {photo_id}")

        return 0

    if args.command == "queue-add":

        folder = Path(args.folder)

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {folder}"
            )

        queue = JobQueue(
            settings.data_dir / "jobs.db"
        )

        job_id = queue.add(
            source_folder=folder,
            fingerprint_id=args.fingerprint,
            priority=args.priority,
        )

        print(
            f"[Queue] Job added: {job_id}"
        )
        print(
            f"[Queue] fingerprint={args.fingerprint}"
        )
        print(
            f"[Queue] folder={folder}"
        )
        print(
            f"[Queue] priority={args.priority}"
        )
        print(
            "[Queue] status=PENDING"
        )

        return 0

    if args.command == "create":

        folder = Path(
            args.folder
        )

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: "
                f"{folder}"
            )

        embedder = SceneEmbedder(
            settings
        )

        manager = FingerprintManager(
            settings,
            embedder,
        )

        metadata = manager.create(
            args.fingerprint,
            folder,
            embedder,
        )

        print()

        print(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 0

    # --------------------------------------------------
    # QUEUE BATCH ADD
    # --------------------------------------------------

    if args.command == "queue-batch-add":

        from app.pipeline.queue import JobQueue

        queue = JobQueue(
            settings.data_dir / "jobs.db"
        )

        if args.end < args.start:
            raise ValueError(
                "END must be greater than or equal to START"
            )

        added = 0
        skipped_existing = 0
        skipped_queue = 0
        missing = 0

        for fingerprint_id in range(
            args.start,
            args.end + 1,
        ):
            fingerprint_id = str(
                fingerprint_id
            )

            source_folder = (
                settings.data_dir
                / "input"
                / fingerprint_id
            )

            if not source_folder.exists():
                print(
                    f"[Queue] MISSING: "
                    f"{source_folder}"
                )
                missing += 1
                continue

            image_files = [
                p
                for p in source_folder.iterdir()
                if p.is_file()
                and p.suffix.lower()
                in {
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                }
            ]

            if not image_files:
                print(
                    f"[Queue] NO IMAGES: "
                    f"{source_folder}"
                )
                missing += 1
                continue

            fingerprint_dir = (
                settings.fingerprints_dir
                / fingerprint_id
            )

            if fingerprint_dir.exists():
                print(
                    f"[Queue] SKIP EXISTING: "
                    f"{fingerprint_id}"
                )
                skipped_existing += 1
                continue

            existing_jobs = queue.list()

            already_queued = any(
                str(job["fingerprint_id"])
                == fingerprint_id
                and job["status"]
                in {
                    "PENDING",
                    "PROCESSING",
                    "DONE",
                }
                for job in existing_jobs
            )

            if already_queued:
                print(
                    f"[Queue] SKIP QUEUED: "
                    f"{fingerprint_id}"
                )
                skipped_queue += 1
                continue

            job_id = queue.add(
                source_folder,
                fingerprint_id,
                priority=args.priority,
            )

            print(
                f"[Queue] ADD "
                f"{fingerprint_id} "
                f"({len(image_files)} images) "
                f"job={job_id}"
            )

            added += 1

        print()
        print("=" * 60)
        print("[Queue] BATCH COMPLETE")
        print("=" * 60)
        print(f"Added:             {added}")
        print(f"Skipped existing:  {skipped_existing}")
        print(f"Skipped queued:    {skipped_queue}")
        print(f"Missing/no images: {missing}")
        print()
        print("Queue:", queue.counts())

        return 0

    # --------------------------------------------------
    # ANALYZE
    # --------------------------------------------------

    if args.command == "analyze":

        folder = Path(
            args.folder
        )

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: "
                f"{folder}"
            )

        embedder = SceneEmbedder(
            settings
        )

        manager = FingerprintManager(
            settings,
            embedder,
        )

        analyzer = SceneAnalyzer(
            embedder,
            manager,
        )

        for result in analyzer.analyze(
            folder,
            args.fingerprint,
        ):
            print_analyze_result(
                result["file"],
                result,
            )

        return 0

    # --------------------------------------------------
    # RECOGNIZE
    # --------------------------------------------------

    if args.command == "recognize":

        folder = Path(
            args.folder
        )

        if not folder.exists():
            raise FileNotFoundError(
                f"Folder not found: "
                f"{folder}"
            )

        embedder = SceneEmbedder(
            settings
        )

        manager = FingerprintManager(
            settings,
            embedder,
        )

        recognizer = SceneRecognizer(
            settings,
            embedder,
            manager,
        )

        selected_fingerprints = None

        if args.fingerprints:
            selected_fingerprints = [
                item.strip()
                for item in args.fingerprints.split(",")
                if item.strip()
            ]

        results = (
            recognizer.recognize_folder(
                folder,
                top_k=args.top_k,
                threshold=args.threshold,
                workers=args.workers,
                fingerprints=selected_fingerprints,
            )
        )

        if args.json:
            print(
                json.dumps(
                    results,
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            for result in results:
                print_recognition_result(
                    result
                )

        return 0

    parser.print_help()

    return 1


if __name__ == "__main__":
    sys.exit(main())
