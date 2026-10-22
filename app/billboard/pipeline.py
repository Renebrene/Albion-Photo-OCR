"""
Background billboard pipeline: detect -> crop -> QWEN on the crop.

Both steps run as deferred worker jobs. The crop is cut from the ORIGINAL
image at full resolution (only the detection runs on a downscaled copy), so
small banner text stays readable for the vision model. Files are published
atomically: temp file -> validation -> os.replace.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from app.billboard import database
from app.billboard.phash import file_dhash
from app.billboard.config import CROPS_ROOT, resolve_settings
from app.billboard.detector import detect_billboards
from app.core.errors import redact_absolute_paths
from app.ingest.database import get_registered_photo

# Crops keep the banner text readable; only very large crops are shrunk.
CROP_MAX_SIDE = int(os.getenv("SCENE_BILLBOARD_QWEN_MAX_SIDE", "2048"))

# Marks a completed detection run. The crop files are deleted after QWEN, so
# their presence alone cannot tell "one billboard" from "not detected yet".
CROPS_MARKER = ".crops.json"
CROPS_VERSION = 2

BILLBOARD_PROMPT = (
    "Ты анализируешь вырезанный рекламный щит (баннер). "
    "Верни СТРОГО JSON без пояснений со следующими ключами: "
    "description (краткое описание рекламы, строка), "
    "client (компания/клиент, строка или null), "
    "brand (бренд, строка или null), "
    "category (категория рекламы, строка или null), "
    "tags (массив не более 10 коротких строк). "
    "Мелкий текст (условия акции, сроки, цены) используй для description "
    "и tags, но НЕ переписывай его дословно и не повторяй длинные строки. "
    "Ответ должен быть коротким и полностью закрытым JSON. "
    "Если данных нет — используй null, не выдумывай."
)


def crop_dir(photo_id: str) -> Path:
    """Deterministic managed directory for one photo's crops."""

    if not photo_id:
        raise ValueError("photo_id is required")

    return CROPS_ROOT / photo_id


def _existing_crops(photo_id: str) -> list[str]:
    """Crop files of one photo, in detection order (crop_01, crop_02, ...)."""

    directory = crop_dir(photo_id)

    if not directory.is_dir():
        return []

    return [
        str(path)
        for path in sorted(directory.glob("crop_*.jpg"))
        if path.is_file()
    ]


def _write_marker(directory: Path, count: int) -> None:
    """Remember that detection completed, even when count == 1."""

    import json

    marker = directory / CROPS_MARKER
    handle, temp_name = tempfile.mkstemp(
        prefix=f".{CROPS_MARKER}.tmp-", dir=directory
    )

    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump({"version": CROPS_VERSION, "count": int(count)}, stream)

        os.replace(temp_name, marker)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _marker_present(directory: Path) -> bool:
    return (directory / CROPS_MARKER).is_file()


def write_crop(
    source_path: str | Path,
    region: dict,
    output_path: str | Path,
    *,
    quality: int = 95,
) -> tuple[int, int]:
    """
    Cut one bbox out of the original and publish it atomically.

    Returns (width, height). Never modifies the source file.
    """

    from PIL import Image

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    handle, temp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.tmp-",
        dir=output_path.parent,
    )
    os.close(handle)

    temp_path = Path(temp_name)

    try:
        with Image.open(source_path) as image:
            if getattr(image, "n_frames", 1) > 1:
                image.seek(0)

            image = image.convert("RGB")
            width, height = image.size

            x1 = min(max(0, int(region["bbox_x"])), width - 1)
            y1 = min(max(0, int(region["bbox_y"])), height - 1)
            x2 = min(width, x1 + max(1, int(region["bbox_w"])))
            y2 = min(height, y1 + max(1, int(region["bbox_h"])))

            crop = image.crop((x1, y1, x2, y2))
            crop.save(temp_path, format="JPEG", quality=quality)
            crop.close()

        with Image.open(temp_path) as check:
            check.load()
            crop_width, crop_height = check.size

        if crop_width < 1 or crop_height < 1:
            raise ValueError("crop is empty")

        os.replace(temp_path, output_path)

    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return crop_width, crop_height


def _detect_and_store(photo_id: str, cfg: dict) -> dict:
    """
    Detect billboards, cut one crop per billboard, persist the primary region.

    The database keeps one ``kind='billboard'`` row per photo (the largest
    box); extra crops are derived files in the same managed directory. They
    are all analysed by QWEN, and the results are merged into one photo_qwen
    row.

    Returns {"detected", "regions", "region_ids", "crop_path", "crops",
    "billboards", "score"}; never enqueues anything (the caller decides what
    runs next).
    """

    record = get_registered_photo(photo_id)

    if record is None:
        raise ValueError(f"photo not found: {photo_id}")

    regions = detect_billboards(record.source_path, config=cfg)

    if not regions:
        database.replace_regions(photo_id, [])
        return {
            "detected": False,
            "regions": 0,
            "region_ids": [],
            "crop_path": None,
            "crops": [],
            "billboards": 0,
        }

    # Old crops of this photo are derived artifacts; replace them as a set.
    out_dir = crop_dir(photo_id)
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    crops: list[dict] = []

    for index, region in enumerate(regions, start=1):
        output_path = out_dir / f"crop_{index:02d}.jpg"
        crop_width, crop_height = write_crop(
            record.source_path, region, output_path
        )
        crops.append(
            {
                **region,
                "kind": "billboard",
                "detector": cfg["detector"],
                "crop_path": str(output_path),
                "crop_width": crop_width,
                "crop_height": crop_height,
                # Хеш содержимого кропа и время съёмки фото: по ним серия
                # связывается позже, когда кропы уже лежат на диске.
                "crop_phash": file_dhash(output_path),
                # У фото может не быть EXIF-даты — тогда поле остаётся пустым.
                "photo_taken_at": getattr(record, "taken_at", None),
            }
        )

    _write_marker(out_dir, len(crops))

    # Only the largest box has a DB row today; the unique index enforces one
    # billboard region per photo. Extra crops stay as derived files.
    primary = crops[0]
    region_ids = database.replace_regions(photo_id, [primary])

    return {
        "detected": True,
        "regions": len(region_ids),
        "region_ids": region_ids,
        "crop_path": primary["crop_path"],
        "crops": [item["crop_path"] for item in crops],
        "billboards": len(crops),
        "score": primary["score"],
    }


def run_detect(photo_id: str) -> dict:
    """BILLBOARD_DETECT job: detect billboards and prepare their crops."""

    cfg = resolve_settings()

    if not cfg["enabled"]:
        return {"photo_id": photo_id, "status": "DISABLED"}

    try:
        result = _detect_and_store(photo_id, cfg)
    except Exception as exc:
        raise RuntimeError(
            f"billboard detection failed for {photo_id}: "
            f"{redact_absolute_paths(str(exc))}"
        ) from exc

    return {"photo_id": photo_id, **{k: result[k] for k in ("detected", "regions", "region_ids")}, "score": result.get("score")}


def ensure_crops(photo_id: str) -> list[str]:
    """
    Return all billboard crops of one photo, detecting them on demand.

    This is the input selector of the QWEN description pipeline: when the
    photo has billboards, the model analyses each crop instead of the whole
    frame. Detection failures degrade to an empty list (full-frame QWEN still
    works).

    A completed detection leaves a marker next to the crops. Without it, an
    old cached crop is re-detected once so a second side-by-side billboard is
    not missed; after that the marker makes the check cheap.
    """

    cfg = resolve_settings()
    if not cfg["enabled"]:
        return []

    try:
        region = database.get_billboard_region(photo_id)
    except Exception:  # noqa: BLE001 - a DB hiccup must not break QWEN
        region = None

    if region is not None:
        existing = _existing_crops(photo_id)

        if existing and _marker_present(crop_dir(photo_id)):
            return existing

    try:
        result = _detect_and_store(photo_id, cfg)
    except Exception:  # noqa: BLE001 - fall back to the full frame
        return []

    return list(result.get("crops") or [])


def ensure_crop(photo_id: str) -> str | None:
    """The primary billboard crop (backward-compatible wrapper)."""

    crops = ensure_crops(photo_id)

    return crops[0] if crops else None


def discard_crop(crop_path: str | Path) -> bool:
    """
    Delete a temporary recognition crop.

    Crops exist only until QWEN has read them successfully. The path must stay
    inside the managed crop root; an empty per-photo directory is removed too.
    A later QWEN run re-detects the billboard and recreates the crop on demand.
    """

    root = CROPS_ROOT.resolve()

    try:
        path = Path(crop_path).resolve()
    except OSError:
        return False

    if not path.is_relative_to(root):
        return False

    try:
        path.unlink(missing_ok=True)
    except OSError:
        return False

    try:
        parent = path.parent

        if parent != root and parent.is_dir():
            # The marker describes the whole crop set; it must go away with
            # the last crop, otherwise an empty directory looks "detected".
            if not any(parent.glob("crop_*.jpg")):
                (parent / CROPS_MARKER).unlink(missing_ok=True)

            if not any(parent.iterdir()):
                parent.rmdir()
    except OSError:
        pass

    return True


def discard_crops(crop_paths: list[str] | tuple[str, ...]) -> None:
    """Delete a set of temporary crops; cleanup never raises."""

    for crop_path in crop_paths:
        try:
            discard_crop(crop_path)
        except Exception:  # noqa: BLE001 - cleanup must not fail QWEN
            pass


def qwen_crop_config(base: dict) -> dict:
    """
    QWEN settings for a billboard crop.

    The crop is already the region of interest (no centering) and keeps more
    pixels than the full-frame default so fine print survives. Brand/client
    are still extracted; `address` is intentionally not requested because on
    banners it is usually the advertiser's legal address from fine print.
    """

    # Промпт можно отредактировать в «Распознавании»; пустое значение
    # возвращает встроенный.
    from app.qwen.processor import crop_prompt_override

    return {
        **base,
        "crop": {"mode": "off", "ratio": 1.0},
        "max_image_side": CROP_MAX_SIDE,
        "prompt": crop_prompt_override() or BILLBOARD_PROMPT,
        # Long fine print sometimes makes the model loop on one field until
        # the output cap; the penalty stops the repetition.
        "max_output_tokens": 768,
        "repeat_penalty": 1.1,
    }
