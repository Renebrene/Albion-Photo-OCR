from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app.core.errors import redact_paths
from app.ingest.register import PhotoRecord
from app.preview import formats
from app.preview.result import PreviewFileResult, PreviewResult
from app.preview.validator import validate_preview


@dataclass(frozen=True)
class PreviewPaths:
    """
    Filesystem paths of previews belonging to one photo_id.
    """

    small: Path
    middle: Path


def build_preview_paths(
    *,
    preview_root: str | Path,
    photo_id: str,
    image_format: str | None = None,
) -> PreviewPaths:
    """
    Build deterministic filesystem paths for one photo_id.

    The extension follows the preview format (SCENE_PREVIEW_FORMAT): the same
    photo has different paths for JPEG and WebP, which is what lets the
    regeneration detect that a photo has no file in the current format yet.
    """

    if not photo_id:
        raise ValueError("photo_id is required")

    root = Path(preview_root)
    suffix = formats.extension(image_format)

    return PreviewPaths(
        small=root / "small" / f"{photo_id}{suffix}",
        middle=root / "middle" / f"{photo_id}{suffix}",
    )


def _resize_preserving_aspect(
    image: Image.Image,
    *,
    max_size: int,
) -> Image.Image:
    """
    Resize an image so its longest side is max_size.

    Images are never enlarged.
    """

    if max_size < 1:
        raise ValueError("max_size must be >= 1")

    width, height = image.size

    if width < 1 or height < 1:
        raise ValueError("Invalid source image dimensions")

    longest_side = max(width, height)

    if longest_side <= max_size:
        return image.copy()

    scale = max_size / longest_side

    new_width = max(1, round(width * scale))
    new_height = max(1, round(height * scale))

    return image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS,
    )


def _load_visual_source(record: PhotoRecord) -> Image.Image:
    """
    Load the visual source used for preview generation.

    MPO -> frame 0
    JPEG -> original image

    The source file is opened read-only.
    """

    source_path = Path(record.source_path)

    image = Image.open(source_path)

    if record.container_format == "MPO":
        image.seek(0)

    image.load()

    return image.convert("RGB")


def _save_preview(
    *,
    preview: Image.Image,
    output_path: Path,
    kind: str,
    action: str,
    quality: int | None = None,
    image_format: str | None = None,
    error_paths: tuple[object, ...] = (),
) -> PreviewFileResult:
    """
    Encode one already-resized image in a temporary file, validate, publish.

    The preview is written next to its final path and moved into place with
    os.replace only after it passes validation, so a failure never leaves a
    partial preview behind. The caller keeps ownership of *preview*.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    handle, temp_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.tmp-",
        dir=output_path.parent,
    )
    os.close(handle)

    temp_path = Path(temp_name)

    try:
        formats.save_preview(
            preview,
            temp_path,
            image_format=image_format,
            quality=quality,
        )
    except Exception as exc:
        temp_path.unlink(missing_ok=True)

        return PreviewFileResult(
            kind=kind,
            path=str(output_path),
            action="ERROR",
            valid=False,
            width=None,
            height=None,
            error=redact_paths(str(exc), *error_paths, temp_path),
        )

    validation = validate_preview(temp_path)

    if not validation.valid:
        temp_path.unlink(missing_ok=True)

        return PreviewFileResult(
            kind=kind,
            path=str(output_path),
            action="ERROR",
            valid=False,
            width=validation.width,
            height=validation.height,
            error=redact_paths(
                validation.error,
                temp_path,
                output_path,
                *error_paths,
            ),
        )

    os.replace(temp_path, output_path)

    return PreviewFileResult(
        kind=kind,
        path=str(output_path),
        action=action,
        valid=True,
        width=validation.width,
        height=validation.height,
        error=None,
    )


def _create_one(
    *,
    record: PhotoRecord,
    output_path: Path,
    kind: str,
    max_size: int,
    action: str,
    quality: int | None = None,
    image_format: str | None = None,
) -> PreviewFileResult:
    """Load the original, resize and publish one preview."""

    source = None
    preview = None

    try:
        source = _load_visual_source(record)

        preview = _resize_preserving_aspect(
            source,
            max_size=max_size,
        )

        return _save_preview(
            preview=preview,
            output_path=output_path,
            kind=kind,
            action=action,
            quality=quality,
            image_format=image_format,
            error_paths=(record.source_path,),
        )

    except Exception as exc:
        return PreviewFileResult(
            kind=kind,
            path=str(output_path),
            action="ERROR",
            valid=False,
            width=None,
            height=None,
            error=redact_paths(str(exc), record.source_path, output_path),
        )

    finally:
        if preview is not None:
            preview.close()

        if source is not None:
            source.close()


def generate_previews(
    *,
    record: PhotoRecord,
    preview_root: str | Path,
    small_size: int,
    middle_size: int,
    quality: int | None = None,
    image_format: str | None = None,
) -> PreviewResult:
    """
    Create or validate small and middle previews for one photo.

    The operation is independent of DINO/HYBRID and does not
    assign an address to the photo.

    Existing valid previews are never overwritten.
    """

    if small_size < 1:
        raise ValueError("small_size must be >= 1")

    if middle_size < 1:
        raise ValueError("middle_size must be >= 1")

    resolved_quality = formats.quality_for(image_format, quality)

    if not 1 <= resolved_quality <= 100:
        raise ValueError("quality must be in 1..100")

    paths = build_preview_paths(
        preview_root=preview_root,
        photo_id=record.photo_id,
        image_format=image_format,
    )

    # MIDDLE first, SMALL derived from it: DINO reads MIDDLE and may start
    # before SMALL is ready, and the original is decoded once instead of
    # twice. If MIDDLE already exists, only its 1280 px file is opened.
    middle_validation = validate_preview(paths.middle)
    small_validation = validate_preview(paths.small)

    if middle_validation.valid:
        middle = PreviewFileResult(
            kind="MIDDLE",
            path=str(paths.middle),
            action="SKIP",
            valid=True,
            width=middle_validation.width,
            height=middle_validation.height,
        )

        if small_validation.valid:
            small = PreviewFileResult(
                kind="SMALL",
                path=str(paths.small),
                action="SKIP",
                valid=True,
                width=small_validation.width,
                height=small_validation.height,
            )
        else:
            small = _small_from_middle(
                record=record,
                middle_path=paths.middle,
                output_path=paths.small,
                max_size=small_size,
                action="REGENERATE" if small_validation.exists else "CREATE",
                quality=resolved_quality,
                image_format=image_format,
            )

        return PreviewResult(
            photo_id=record.photo_id,
            small=small,
            middle=middle,
        )

    middle_action = "REGENERATE" if middle_validation.exists else "CREATE"
    small_action = "REGENERATE" if small_validation.exists else "CREATE"

    source = None
    middle_image = None
    small_image = None

    try:
        source = _load_visual_source(record)
        middle_image = _resize_preserving_aspect(source, max_size=middle_size)

        middle = _save_preview(
            preview=middle_image,
            output_path=paths.middle,
            kind="MIDDLE",
            action=middle_action,
            quality=resolved_quality,
            image_format=image_format,
            error_paths=(record.source_path,),
        )

        # SMALL is cut from the already-resized MIDDLE; if MIDDLE could not
        # be written, fall back to the decoded original (no second read).
        base = middle_image if middle.valid else source
        small_image = _resize_preserving_aspect(base, max_size=small_size)

        small = _save_preview(
            preview=small_image,
            output_path=paths.small,
            kind="SMALL",
            action=small_action,
            quality=resolved_quality,
            image_format=image_format,
            error_paths=(record.source_path,),
        )

    except Exception as exc:
        message = redact_paths(str(exc), record.source_path)

        middle = PreviewFileResult(
            kind="MIDDLE",
            path=str(paths.middle),
            action="ERROR",
            valid=False,
            error=message,
        )
        small = PreviewFileResult(
            kind="SMALL",
            path=str(paths.small),
            action="ERROR",
            valid=False,
            error=message,
        )

    finally:
        for image in (small_image, middle_image, source):
            if image is not None:
                image.close()

    return PreviewResult(
        photo_id=record.photo_id,
        small=small,
        middle=middle,
    )


def _small_from_middle(
    *,
    record: PhotoRecord,
    middle_path: Path,
    output_path: Path,
    max_size: int,
    action: str,
    quality: int | None,
    image_format: str | None,
) -> PreviewFileResult:
    """
    Build SMALL from an existing MIDDLE preview.

    Falls back to the original when the MIDDLE file cannot be decoded, so a
    damaged preview never blocks the small one.
    """

    source = None
    preview = None

    try:
        with Image.open(middle_path) as image:
            image.load()
            source = image.convert("RGB")

        preview = _resize_preserving_aspect(source, max_size=max_size)

        return _save_preview(
            preview=preview,
            output_path=output_path,
            kind="SMALL",
            action=action,
            quality=quality,
            image_format=image_format,
            error_paths=(record.source_path, middle_path),
        )

    except Exception:
        return _create_one(
            record=record,
            output_path=output_path,
            kind="SMALL",
            max_size=max_size,
            action=action,
            quality=quality,
            image_format=image_format,
        )

    finally:
        if preview is not None:
            preview.close()

        if source is not None:
            source.close()
