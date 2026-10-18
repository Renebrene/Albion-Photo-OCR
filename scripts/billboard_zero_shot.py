"""Этап 0: zero-shot детекция рекламных щитов (YOLO-World).

Пробный стенд, прод не затрагивает: читает изображения, рисует боксы,
пишет JSON-отчёт в data/output/billboard_stage0/.

Запуск:
    .venv/bin/python scripts/billboard_zero_shot.py IMG [IMG ...]
    .venv/bin/python scripts/billboard_zero_shot.py --corpus 30
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "data/output/billboard_stage0"
WEIGHTS = "yolov8s-worldv2.pt"

CLASSES = ["billboard", "digital billboard screen", "advertising screen"]

# Геометрические фильтры: щиты широкоформатные и крупные.
ASPECT_MIN = 0.8   # ширина / высота бокса
ASPECT_MAX = 4.0
SCORE_MIN = 0.05   # zero-shot уверенности занижены; фильтруем мягко

MAX_SIDE = 1920    # детекция на уменьшенной копии


def iou(a: dict, b: dict) -> float:
    ax, ay, aw, ah = a["bbox_orig"]
    bx, by, bw, bh = b["bbox_orig"]
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0.0


def dedup_and_pick_largest(regions: list[dict]) -> list[dict]:
    """Убираем дубли одной цели (IoU > 0.6) и оставляем самый большой бокс:
    щит на кадре один, мелкие кандидаты — мусор."""
    survivors: list[dict] = []
    for r in sorted(regions, key=lambda x: -x["score"]):
        if all(iou(r, s) <= 0.6 for s in survivors):
            survivors.append(r)
    if not survivors:
        return []
    best = max(survivors, key=lambda r: r["bbox_orig"][2] * r["bbox_orig"][3])
    return [best]


def detect(image_path: Path, model) -> dict:
    import cv2

    image = cv2.imread(str(image_path))
    if image is None:
        return {"image": str(image_path), "error": "unreadable"}

    orig_h, orig_w = image.shape[:2]
    scale = min(1.0, MAX_SIDE / max(orig_w, orig_h))
    if scale < 1.0:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    t0 = time.time()
    results = model.predict(image, verbose=False, conf=SCORE_MIN)
    elapsed = time.time() - t0

    regions = []
    for box in results[0].boxes:
        score = float(box.conf)
        x1, y1, x2, y2 = (float(v) for v in box.xyxy[0])
        w, h = x2 - x1, y2 - y1
        if h <= 0 or not (ASPECT_MIN <= w / h <= ASPECT_MAX):
            continue
        # Координаты пересчитываем в систему оригинала.
        regions.append({
            "bbox_orig": [round(x1 / scale), round(y1 / scale),
                          round(w / scale), round(h / scale)],
            "score": round(score, 3),
            "label": results[0].names[int(box.cls)],
        })
    regions.sort(key=lambda r: -r["score"])

    regions = dedup_and_pick_largest(regions)

    # Визуализация на уменьшенной копии — только для ручного просмотра.
    for r in regions[:5]:
        x, y, w, h = r["bbox_orig"]
        p1 = (int(x * scale), int(y * scale))
        p2 = (int((x + w) * scale), int((y + h) * scale))
        cv2.rectangle(image, p1, p2, (0, 200, 0), 3)
        cv2.putText(image, f"{r['score']:.2f}", p1,
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 0), 2)

    out_name = f"{image_path.stem}_boxes.jpg"
    cv2.imwrite(str(OUT_DIR / out_name), image)

    return {
        "image": image_path.name,
        "orig_size": [orig_w, orig_h],
        "seconds": round(elapsed, 2),
        "regions": regions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="*", help="пути к фото")
    parser.add_argument("--corpus", type=int, metavar="N",
                        help="прогнать первые N фото из data/input/")
    parser.add_argument("--min-score", type=float, default=SCORE_MIN)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = [Path(p) for p in args.images]
    if args.corpus:
        roots = [REPO_ROOT / "data/input"]
        corpus = sorted(
            p for root in roots for p in root.rglob("*")
            if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        )
        paths.extend(corpus[: args.corpus])
    if not paths:
        parser.error("укажите изображения или --corpus N")

    from ultralytics import YOLOWorld

    model = YOLOWorld(WEIGHTS)
    model.set_classes(CLASSES)

    report = []
    for path in paths:
        if not path.is_file():
            print(f"skip (no file): {path}", file=sys.stderr)
            continue
        item = detect(path, model)
        report.append(item)
        n = len(item.get("regions", []))
        top = item["regions"][0]["score"] if n else "-"
        print(f"{item['image']}: {n} region(s), top={top}, {item['seconds']}s")

    out_json = OUT_DIR / f"report_{int(time.time())}.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"report: {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
