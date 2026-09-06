from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class PreviewValidation:
    """
    Validation result for one preview file.
    """

    path: str
    exists: bool
    valid: bool
    width: int | None
    height: int | None
    format: str | None
    error: str | None


def validate_preview(
    path: str | Path,
    *,
    expected_width: int | None = None,
    expected_height: int | None = None,
) -> PreviewValidation:
    """
    Validate an existing preview JPEG.

    Validation includes:
      - file existence and regular-file check;
      - JPEG format check;
      - Pillow structural verification;
      - full image decoding;
      - optional exact dimension check.

    The preview file is never modified.
    """

    path = Path(path)

    if not path.exists() or not path.is_file():
        return PreviewValidation(
            path=str(path),
            exists=False,
            valid=False,
            width=None,
            height=None,
            format=None,
            error="File does not exist or is not a regular file",
        )

    try:
        with Image.open(path) as image:
            image_format = image.format
            width, height = image.size

            if image_format != "JPEG":
                return PreviewValidation(
                    path=str(path),
                    exists=True,
                    valid=False,
                    width=width,
                    height=height,
                    format=image_format,
                    error=f"Unsupported preview format: {image_format}",
                )

            image.verify()

        # verify() checks structure but does not perform full decoding.
        # Reopen the file and force complete decoding.
        with Image.open(path) as image:
            image.load()

            width, height = image.size

            if expected_width is not None and width != expected_width:
                return PreviewValidation(
                    path=str(path),
                    exists=True,
                    valid=False,
                    width=width,
                    height=height,
                    format=image.format,
                    error=(
                        f"Unexpected width: {width}; "
                        f"expected {expected_width}"
                    ),
                )

            if expected_height is not None and height != expected_height:
                return PreviewValidation(
                    path=str(path),
                    exists=True,
                    valid=False,
                    width=width,
                    height=height,
                    format=image.format,
                    error=(
                        f"Unexpected height: {height}; "
                        f"expected {expected_height}"
                    ),
                )

        return PreviewValidation(
            path=str(path),
            exists=True,
            valid=True,
            width=width,
            height=height,
            format="JPEG",
            error=None,
        )

    except Exception as exc:
        return PreviewValidation(
            path=str(path),
            exists=True,
            valid=False,
            width=None,
            height=None,
            format=None,
            error=str(exc),
        )
