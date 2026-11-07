#!/usr/bin/env python3
"""Read-only object-embedding pilot for Zorge / Dachnaya.

Reference object prototypes are built from the two labelled folders:

    /media/alexice/TEST/зорге
    /media/alexice/TEST/дачная

Object crops are detected with YOLO-World (the detector already used by the
billboard branch) and embedded with DINOv2.  The query set is the same
balanced 200+200 sample as the v3.5 experiment, plus the current production
hard cases (photos labelled Zorge/Stachki but assigned to Dachnaya).

Nothing is written to PostgreSQL or to production fingerprints.  The v3.5
experimental fingerprints are read from data/experiments/v35.

    .venv/bin/python scripts/object_embedding_experiment.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.billboard.detector import _load_model  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.embedder import SceneEmbedder  # noqa: E402
from app.core.scene_analyzer import CompactDescriptor  # noqa: E402
from app.dino.runner import compare_loaded  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from scripts.dino_v35_experiment import load_labeled, query_path  # noqa: E402

OUT = Path("data/experiments/object_embed")
REPORT = Path(f"data/reports/object_embedding_experiment_{date.today():%Y%m%d}.md")
V35 = Path("data/experiments/v35")

CLASSES = (
    "billboard",
    "digital billboard screen",
    "building",
    "house",
    "tree",
    "traffic light",
    "bus stop",
    "road",
    "railway",
    "train",
)

# Screen content changes with every campaign, so it is not embedded.  Screen
# detection itself is still useful later for geometry/presence, but this pilot
# tests stable scene objects only.
CANONICAL_CLASS = {
    "billboard": "screen",
    "digital billboard screen": "screen",
    "building": "building",
    "house": "building",
    "tree": "tree",
    "traffic light": "traffic light",
    "bus stop": "bus stop",
    "road": "road",
    "railway": "railway",
    "train": "railway",
}
STABLE_CLASSES = (
    "building",
    "tree",
    "traffic light",
    "bus stop",
    "road",
    "railway",
)

DETECTION_CONF = 0.12
DETECTION_SIZE = 960
CROP_PADDING = 0.04
REFERENCE = {
    "dachnaya": Path("/media/alexice/TEST/дачная"),
    "zorge": Path("/media/alexice/TEST/зорге"),
}
GATES = (0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12)
TRAIN_MONTHS = set(range(1, 7))
TEST_MONTHS = {7, 8, 9, 10}
random.seed(7)


def normalize_rows(rows):
    rows = np.asarray(rows, dtype=np.float32)
    norms = np.linalg.norm(rows, axis=1, keepdims=True)
    return rows / np.maximum(norms, 1e-9)


def file_hash(path: Path) -> str | None:
    """SHA-256 of a source file, or None when only a preview exists."""

    if not path.exists() or not path.is_file():
        return None

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reference_hashes(paths: list[Path] | None = None) -> set[str]:
    """Exact duplicate protection: reference and query must not share files."""

    if paths is None:
        paths = [
            path
            for folder in REFERENCE.values()
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
        ]

    result = set()
    for path in paths:
        digest = file_hash(path)
        if digest:
            result.add(digest)
    return result


def image_month(path: Path) -> int | None:
    """EXIF month of a reference image; None when it has no date."""

    try:
        with Image.open(path) as image:
            value = image.getexif().get(306)
    except Exception:  # noqa: BLE001
        return None

    if not value:
        return None

    try:
        return int(str(value)[5:7])
    except ValueError:
        return None


def detect_objects(path: Path, model) -> list[dict]:
    """Return object crops and metadata in original image coordinates."""

    results = model.predict(
        str(path),
        conf=DETECTION_CONF,
        imgsz=DETECTION_SIZE,
        verbose=False,
    )
    if not results:
        return []

    with Image.open(path) as image:
        image = image.convert("RGB")
        width, height = image.size
        boxes = []

        for box in results[0].boxes:
            label = str(results[0].names[int(box.cls)])
            canonical = CANONICAL_CLASS.get(label)
            if canonical is None:
                continue

            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0])
            pad_x = (x2 - x1) * CROP_PADDING
            pad_y = (y2 - y1) * CROP_PADDING
            x1 = max(0, int(round(x1 - pad_x)))
            y1 = max(0, int(round(y1 - pad_y)))
            x2 = min(width, int(round(x2 + pad_x)))
            y2 = min(height, int(round(y2 + pad_y)))

            if x2 - x1 < 16 or y2 - y1 < 16:
                continue

            boxes.append(
                {
                    "class": canonical,
                    "label": label,
                    "confidence": float(box.conf),
                    "bbox": [x1, y1, x2, y2],
                    "area_ratio": ((x2 - x1) * (y2 - y1)) / (width * height),
                    "crop": image.crop((x1, y1, x2, y2)),
                }
            )

    return boxes


def build_reference(
    embedder: SceneEmbedder,
    model,
    *,
    months: set[int] | None = None,
) -> tuple[dict, dict, list[Path]]:
    """Embed stable object crops for each reference address."""

    prototypes = {
        address: defaultdict(list)
        for address in REFERENCE
    }
    coverage = {}
    used_paths: list[Path] = []

    for address, folder in REFERENCE.items():
        paths = sorted(
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}
            and (months is None or image_month(p) in months)
        )
        used_paths.extend(paths)
        object_count = Counter()
        images_with = Counter()

        for path in paths:
            try:
                objects = detect_objects(path, model)
            except Exception as exc:  # noqa: BLE001 - one bad image, not the pilot
                print(f"[objects] skip {path.name}: {exc}", flush=True)
                continue

            stable = [
                item for item in objects
                if item["class"] in STABLE_CLASSES
            ]
            for item in stable:
                object_count[item["class"]] += 1
                images_with[item["class"]] += 1

            if stable:
                vectors = normalize_rows(
                    embedder.embed_images([item["crop"] for item in stable])
                )
                for item, vector in zip(stable, vectors):
                    prototypes[address][item["class"]].append(vector)

        coverage[address] = {
            "images": len(paths),
            "objects": dict(object_count),
            "images_with": dict(images_with),
        }
        print(
            f"[objects] reference {address}: "
            f"{len(paths)} images, {dict(object_count)}",
            flush=True,
        )

    return {
        address: {
            name: normalize_rows(np.stack(vectors)) if vectors else np.zeros((0, 768))
            for name, vectors in by_class.items()
        }
        for address, by_class in prototypes.items()
    }, coverage, used_paths


def load_v35() -> dict:
    result = {}
    for name in ("dachnaya_v35", "zorge_v35"):
        root = V35 / name
        metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
        result[name] = {
            "centroid": np.load(root / "centroid.npy"),
            "embeddings": np.load(root / "embeddings.npy"),
            "environment_embeddings": np.load(root / "environment_embeddings.npy"),
            "color_embeddings": np.load(root / "color_embeddings.npy"),
            "spatial_embeddings": np.load(root / "spatial_embeddings.npy"),
            "metadata": metadata,
        }
    return result


def object_scores(
    query_objects: dict[str, list[np.ndarray]],
    prototypes: dict,
) -> tuple[float | None, dict[str, float]]:
    """Mean of per-class best object matches, equal weight per class."""

    per_class = {}

    for name, vectors in query_objects.items():
        reference = prototypes.get(name)
        if reference is None or len(reference) == 0:
            continue

        best = [
            float(np.max(reference @ vector))
            for vector in vectors
        ]
        if best:
            # Several traffic lights / trees in one frame should not drown the
            # class; the best few matches describe the scene well enough.
            per_class[name] = float(np.mean(sorted(best, reverse=True)[:3]))

    if not per_class:
        return None, {}

    return float(np.mean(list(per_class.values()))), per_class


def load_hard_cases() -> list[tuple]:
    """Current analogue of the old 151 hard cases."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT max(hybrid_run_id) FROM hybrid_runs WHERE status='DONE'")
            run_id = cur.fetchone()[0]
            cur.execute(
                """
                SELECT p.photo_id, p.filename, p.source_path
                FROM photos p
                JOIN hybrid_results h
                  ON h.photo_id = p.photo_id
                 AND h.status = 'DONE'
                 AND h.hybrid_run_id = %s
                WHERE h.hybrid_final_id = '51_v35'
                  AND p.filename ILIKE %s
                  AND p.filename ILIKE %s
                """,
                (run_id, "%Стачки%", "%Зорге%"),
            )
            return cur.fetchall()


def main() -> int:
    global OUT, REPORT

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--temporal",
        action="store_true",
        help="train on Jan-Jun reference images, test on Jul-Oct query photos",
    )
    parser.add_argument("--output-suffix", default="")
    args = parser.parse_args()

    if args.output_suffix:
        OUT = OUT.with_name(f"{OUT.name}_{args.output_suffix}")
        REPORT = REPORT.with_name(
            f"{REPORT.stem}_{args.output_suffix}{REPORT.suffix}"
        )

    OUT.mkdir(parents=True, exist_ok=True)
    cpu = replace(settings, device="cpu")
    embedder = SceneEmbedder(cpu)
    model = _load_model(CLASSES, "data/models/yolov8s-worldv2.pt")

    train_months = TRAIN_MONTHS if args.temporal else None
    print("[objects] building reference prototypes", flush=True)
    prototypes, coverage, reference_paths = build_reference(
        embedder, model, months=train_months
    )
    v35 = load_v35()

    dachnaya, zorge = load_labeled()
    sample = []
    for label, rows in (("dachnaya", dachnaya), ("zorge", zorge)):
        rows = list(rows)
        random.shuffle(rows)
        sample.extend((label, row) for row in rows[:200])

    # Exact-file leakage guard: the reference folders and the production
    # archive contain a number of byte-identical copies. Those photos must not
    # be scored as independent test cases.
    ref_hashes = reference_hashes(reference_paths)
    filtered = []
    dropped = 0
    for label, (pid, filename, source_path) in sample:
        digest = file_hash(Path(source_path))
        if digest in ref_hashes:
            dropped += 1
            continue
        filtered.append((label, (pid, filename, source_path)))
    sample = filtered

    hard = [
        row for row in load_hard_cases()
        if file_hash(Path(row[2])) not in ref_hashes
    ]

    if args.temporal:
        ids = [row[0] for _label, row in sample] + [row[0] for row in hard]
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT photo_id, EXTRACT(month FROM taken_at)::int "
                    "FROM public.photos WHERE photo_id = ANY(%s)",
                    (ids,),
                )
                months = {str(row[0]): int(row[1]) for row in cur.fetchall() if row[1]}

        sample = [
            row for row in sample
            if months.get(row[1][0]) in TEST_MONTHS
        ]
        hard = [
            row for row in hard
            if months.get(row[0]) in TEST_MONTHS
        ]

    print(
        f"[objects] query sample={len(sample)} "
        f"(dropped exact duplicates={dropped}) hard={len(hard)} "
        f"temporal={'yes' if args.temporal else 'no'}",
        flush=True,
    )

    rows = []
    for index, (label, (pid, filename, source_path)) in enumerate(sample, 1):
        path = query_path(pid, source_path)

        try:
            objects = detect_objects(path, model)
            stable = [item for item in objects if item["class"] in STABLE_CLASSES]
            query_objects = defaultdict(list)
            if stable:
                vectors = normalize_rows(
                    embedder.embed_images([item["crop"] for item in stable])
                )
                for item, vector in zip(stable, vectors):
                    query_objects[item["class"]].append(vector)

            image = CompactDescriptor._load(path)
            query = embedder.embed_paths([path])[0]
            env, color, spatial = CompactDescriptor.all_from_image(image)
            dino = {
                "dachnaya_v35": compare_loaded(query, env, color, spatial, v35["dachnaya_v35"]),
                "zorge_v35": compare_loaded(query, env, color, spatial, v35["zorge_v35"]),
            }
            obj = {
                address: object_scores(query_objects, prototypes[address])[0]
                for address in ("dachnaya", "zorge")
            }
            rows.append(
                {
                    "photo_id": pid,
                    "filename": filename,
                    "label": label,
                    "dino_dachnaya": dino["dachnaya_v35"]["score"],
                    "dino_zorge": dino["zorge_v35"]["score"],
                    "object_dachnaya": obj["dachnaya"],
                    "object_zorge": obj["zorge"],
                    "object_classes": {
                        name: len(vectors)
                        for name, vectors in query_objects.items()
                    },
                }
            )
        except Exception as exc:  # noqa: BLE001 - report the bad query, keep going
            print(f"[objects] query skip {pid}: {exc}", flush=True)

        if index % 50 == 0:
            print(f"[objects] query {index}/{len(sample)}", flush=True)

    hard_rows = []
    for pid, filename, source_path in hard:
        path = query_path(pid, source_path)
        try:
            objects = detect_objects(path, model)
            stable = [item for item in objects if item["class"] in STABLE_CLASSES]
            query_objects = defaultdict(list)
            if stable:
                vectors = normalize_rows(
                    embedder.embed_images([item["crop"] for item in stable])
                )
                for item, vector in zip(stable, vectors):
                    query_objects[item["class"]].append(vector)
            image = CompactDescriptor._load(path)
            query = embedder.embed_paths([path])[0]
            env, color, spatial = CompactDescriptor.all_from_image(image)
            dino = {
                "dachnaya_v35": compare_loaded(query, env, color, spatial, v35["dachnaya_v35"]),
                "zorge_v35": compare_loaded(query, env, color, spatial, v35["zorge_v35"]),
            }
            obj = {
                address: object_scores(query_objects, prototypes[address])[0]
                for address in ("dachnaya", "zorge")
            }
            hard_rows.append(
                {
                    "photo_id": pid,
                    "filename": filename,
                    "dino_dachnaya": dino["dachnaya_v35"]["score"],
                    "dino_zorge": dino["zorge_v35"]["score"],
                    "object_dachnaya": obj["dachnaya"],
                    "object_zorge": obj["zorge"],
                }
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[objects] hard skip {pid}: {exc}", flush=True)

    def dino_pred(row):
        return "dachnaya" if row["dino_dachnaya"] > row["dino_zorge"] else "zorge"

    def object_pred(row):
        if row["object_dachnaya"] is None or row["object_zorge"] is None:
            return None
        return "dachnaya" if row["object_dachnaya"] > row["object_zorge"] else "zorge"

    base_correct = sum(dino_pred(row) == row["label"] for row in rows)
    object_correct = sum(
        object_pred(row) == row["label"]
        for row in rows
        if object_pred(row) is not None
    )
    object_available = sum(object_pred(row) is not None for row in rows)

    gate_results = {}
    for gate in GATES:
        correct = 0
        changed = 0
        for row in rows:
            d_score = row["dino_dachnaya"]
            z_score = row["dino_zorge"]
            pred = dino_pred(row)
            obj = object_pred(row)
            if obj is not None and abs(d_score - z_score) < gate:
                changed += 1
                pred = obj
            correct += pred == row["label"]
        gate_results[str(gate)] = {
            "accuracy": correct / len(rows) if rows else None,
            "correct": correct,
            "total": len(rows),
            "changed": changed,
        }

    hard_base = sum(dino_pred(row) == "zorge" for row in hard_rows)
    hard_gate = {}
    for gate in GATES:
        correct = 0
        changed = 0
        for row in hard_rows:
            pred = dino_pred(row)
            obj = object_pred(row)
            if obj is not None and abs(row["dino_dachnaya"] - row["dino_zorge"]) < gate:
                changed += 1
                pred = obj
            correct += pred == "zorge"
        hard_gate[str(gate)] = {
            "correct": correct,
            "total": len(hard_rows),
            "changed": changed,
        }

    (OUT / "rows.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "hard_rows.json").write_text(
        json.dumps(hard_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = {
        "reference_coverage": coverage,
        "leakage_guard": {
            "reference_files": sum(item["images"] for item in coverage.values()),
            "dropped_query_duplicates": dropped,
            "sample_rows": len(rows),
            "hard_rows": len(hard_rows),
        },
        "sample": {
            "rows": len(rows),
            "dino_correct": base_correct,
            "dino_accuracy": base_correct / len(rows) if rows else None,
            "object_correct": object_correct,
            "object_available": object_available,
            "object_accuracy_available": (
                object_correct / object_available if object_available else None
            ),
        },
        "gated": gate_results,
        "hard": {
            "rows": len(hard_rows),
            "dino_zorge": hard_base,
            "dino_accuracy": hard_base / len(hard_rows) if hard_rows else None,
            "object_gated": hard_gate,
        },
    }
    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Пилот объектных эмбеддингов: Зорге / Дачная",
        "",
        f"Дата: {date.today():%d.%m.%Y}. Read-only: PostgreSQL и production-слепки не изменялись.",
        "",
        (
            "**Temporal holdout:** эталоны только за январь–июнь, проверка — июль–октябрь."
            if args.temporal
            else "**Полная выборка:** эталоны и проверка разделены по каталогам."
        ),
        "",
        "## Покрытие эталонов",
        "",
        "| Адрес | Фото | Объекты |",
        "|---|---:|---|",
    ]
    for address, item in coverage.items():
        lines.append(f"| `{address}` | {item['images']} | {item['objects']} |")

    lines += [
        "",
        "Классы для эмбеддинга: " + ", ".join(f"`{name}`" for name in STABLE_CLASSES) + ".",
        "Экран/щит детектируется, но его содержимое не эмбеддится: реклама меняется.",
        "",
        f"Проверочная выборка: **{len(rows)}** фото. Исключено точных дублей "
        f"эталонных файлов: **{dropped}**. Hard-набор: **{len(hard_rows)}**.",
        "",
        "## Проверочная выборка",
        "",
        f"- DINO v3.5: **{base_correct}/{len(rows)}**",
        f"- Объектный score доступен: **{object_available}/{len(rows)}**",
        f"- Только объекты: **{object_correct}/{object_available}**",
        "",
        "| Gate | DINO + объекты | Изменено строк |",
        "|---:|---:|---:|",
    ]
    for gate, item in gate_results.items():
        lines.append(
            f"| {gate} | {item['correct']}/{item['total']} "
            f"({100 * item['accuracy']:.1f}%) | {item['changed']} |"
        )

    lines += [
        "",
        f"## Hard-набор (сейчас {len(hard_rows)} фото: Зорге/Стачки, но production дал `51_v35`)",
        "",
        f"- DINO v3.5 отправляет в Зорге: **{hard_base}/{len(hard_rows)}**",
        "",
        "| Gate | Верно в Зорге | Изменено |",
        "|---:|---:|---:|",
    ]
    for gate, item in hard_gate.items():
        lines.append(f"| {gate} | {item['correct']}/{item['total']} | {item['changed']} |")

    lines += [
        "",
        "## Ограничения",
        "",
        (
            "- Temporal holdout: эталоны — январь–июнь, проверка — июль–октябрь;"
            " точные дубли файлов удалены."
            if args.temporal
            else "- Эталоны и проверка разделены по каталогам; точные дубли удалены,"
            " но даты съёмки могут пересекаться."
        ),
        "- Детектор YOLO-World на части кадров находит только щит, дорогу и остановку;",
        "  дом/дерево/железная дорога представлены слабо.",
        "- Экран как объект полезен геометрией/положением, но не содержимым.",
        "- Hard-набор — текущие production-ошибки `51_v35`, а не исходные 151 фото.",
    ]

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[objects] report: {REPORT}", flush=True)
    print(json.dumps(report, ensure_ascii=False, indent=2)[:4000])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
