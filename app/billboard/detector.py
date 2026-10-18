"""
Zero-shot billboard detector (YOLO-World) with a largest-box filter.

Detection runs on a downscaled copy (small billboards are still found, and the
copy is cheap); every bbox is mapped back to ORIGINAL image coordinates. The
crop itself is always cut from the original at full resolution by the
pipeline, so small banner text survives.

The model is loaded once per worker process. A photo yields at most one region
(the largest box after IoU dedup), matching the current product contract.
"""

from __future__ import annotations

from pathlib import Path

from app.billboard.config import resolve_settings

IOU_DEDUP = 0.6

_MODEL = None
_MODEL_CLASSES: tuple[str, ...] | None = None


def iou(a: dict, b: dict) -> float:
    """Intersection over union for two region dicts (original coordinates)."""

    ax, ay, aw, ah = a["bbox_x"], a["bbox_y"], a["bbox_w"], a["bbox_h"]
    bx, by, bw, bh = b["bbox_x"], b["bbox_y"], b["bbox_w"], b["bbox_h"]

    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)

    if x2 <= x1 or y2 <= y1:
        return 0.0

    inter = (x2 - x1) * (y2 - y1)
    union = aw * ah + bw * bh - inter

    return inter / union if union else 0.0


def dedup(regions: list[dict], *, threshold: float = IOU_DEDUP) -> list[dict]:
    """Drop duplicate boxes of the same target, best score first."""

    survivors: list[dict] = []

    for region in sorted(regions, key=lambda item: -item["score"]):
        if all(iou(region, kept) <= threshold for kept in survivors):
            survivors.append(region)

    return survivors


def pick_largest(regions: list[dict]) -> dict | None:
    """The billboard is a single large object: keep the biggest box."""

    if not regions:
        return None

    return max(regions, key=lambda item: item["bbox_w"] * item["bbox_h"])


def pad_bbox(
    region: dict,
    *,
    ratio: float,
    image_width: int,
    image_height: int,
) -> dict:
    """Grow a bbox by *ratio* of its size, clamped to the image bounds."""

    if ratio <= 0:
        return region

    pad_x = int(round(region["bbox_w"] * ratio))
    pad_y = int(round(region["bbox_h"] * ratio))

    x1 = max(0, region["bbox_x"] - pad_x)
    y1 = max(0, region["bbox_y"] - pad_y)
    x2 = min(image_width, region["bbox_x"] + region["bbox_w"] + pad_x)
    y2 = min(image_height, region["bbox_y"] + region["bbox_h"] + pad_y)

    return {
        **region,
        "bbox_x": x1,
        "bbox_y": y1,
        "bbox_w": max(1, x2 - x1),
        "bbox_h": max(1, y2 - y1),
    }


def _load_model(classes: tuple[str, ...], model_name: str):
    """Load (once per process) YOLO-World with the requested classes."""

    global _MODEL, _MODEL_CLASSES

    if _MODEL is not None and _MODEL_CLASSES == classes:
        return _MODEL

    from ultralytics import YOLOWorld

    model_path = Path(model_name)

    # An existing local checkpoint is preferred; otherwise Ultralytics resolves
    # the bare name (and downloads it on first use).
    source = str(model_path) if model_path.is_file() else model_path.name

    model = YOLOWorld(source)
    model.set_classes(list(classes))

    _MODEL = model
    _MODEL_CLASSES = classes

    return model


def detect_billboard(
    image_path: str | Path,
    *,
    config: dict | None = None,
) -> dict | None:
    """
    Detect the largest billboard on one photo.

    Returns a region dict with bbox in ORIGINAL coordinates, or None.
    The photo is never modified.
    """

    import cv2

    cfg = config or resolve_settings()

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError("source image is unreadable")

    orig_height, orig_width = image.shape[:2]
    scale = min(1.0, cfg["max_side"] / max(orig_width, orig_height))

    if scale < 1.0:
        image = cv2.resize(
            image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
        )

    model = _load_model(cfg["classes"], cfg["model"])
    results = model.predict(image, conf=cfg["score"], verbose=False)

    regions: list[dict] = []

    for box in results[0].boxes:
        x1, y1, x2, y2 = (float(value) for value in box.xyxy[0])
        width, height = x2 - x1, y2 - y1

        if width <= 0 or height <= 0:
            continue

        regions.append(
            {
                "bbox_x": round(x1 / scale),
                "bbox_y": round(y1 / scale),
                "bbox_w": round(width / scale),
                "bbox_h": round(height / scale),
                "score": round(float(box.conf), 4),
                "label": str(results[0].names[int(box.cls)]),
            }
        )

    best = pick_largest(dedup(regions))

    if best is None:
        return None

    return pad_bbox(
        best,
        ratio=cfg["padding"],
        image_width=orig_width,
        image_height=orig_height,
    )
