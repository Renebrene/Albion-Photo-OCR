"""
TurboJPEG decode for PREVIEW image source loading.

Replaces Pillow JPEG/MPO decoding with libjpeg-turbo on the CPU — ~1.7× faster
(220 ms → 132 ms on 12 MP originals measured on this machine).

MPO (Multi-Picture Object, common in HDR cameras) starts with the same SOI
marker as JPEG and has APP2 metadata before frame 0.  libjpeg-turbo ignores
unknown markers and decodes frame 0 directly — no ``seek(0)`` needed.

The fallback to Pillow is built-in: if the turbojpeg library is not found or
a file fails to decode, the caller should fall back to ``_load_visual_source``
from ``app.preview.generator``.
"""

from __future__ import annotations

import ctypes.util
import os
from pathlib import Path

import numpy as np

_TURBOJPEG = None

_DEFAULT_LIB_PATHS = [
    "/usr/lib/x86_64-linux-gnu/libturbojpeg.so.0",
    "/usr/local/lib/libturbojpeg.dylib",
    # Snap copies from krita.
    "/snap/krita/109/usr/lib/x86_64-linux-gnu/libturbojpeg.so.0",
    # User-local copies.
    os.path.expanduser("~/.local/lib/libturbojpeg.so.0"),
]


def _load_turbojpeg():
    """Return a TurboJPEG instance or None."""

    global _TURBOJPEG  # noqa: PLW0603

    if _TURBOJPEG is not None:
        return _TURBOJPEG

    try:
        from turbojpeg import TurboJPEG

        lib = ctypes.util.find_library("turbojpeg")

        if lib is None:
            for candidate in _DEFAULT_LIB_PATHS:
                if Path(candidate).is_file():
                    lib = candidate
                    break

        if lib is None:
            return None

        _TURBOJPEG = TurboJPEG(lib_path=lib)
        return _TURBOJPEG

    except Exception:  # noqa: BLE001 — CPU fallback remains
        return None


def turbo_decode(path: str | Path) -> np.ndarray | None:
    """
    Decode a JPEG/MPO (first frame only) with libjpeg-turbo.

    Returns a ``(H, W, 3)`` uint8 array or None on failure (caller falls back
    to Pillow).
    """

    tj = _load_turbojpeg()

    if tj is None:
        return None

    try:
        data = Path(path).read_bytes()
        array = tj.decode(data, pixel_format=0)  # TJPF_RGB = 0
        return np.require(array, dtype=np.uint8, requirements="C")
    except Exception:  # noqa: BLE001 — CPU fallback
        return None


def decode_rgb(path: str | Path) -> "Image.Image | None":
    """
    Tolerant RGB decode of a JPEG/MPO source, or None when TurboJPEG is absent.

    libjpeg-turbo decodes truncated files that Pillow and OpenCV reject (it
    fills the missing scanlines with grey), so derived artifacts — previews and
    billboard crops — are still produced from a partially copied original.
    Callers must keep a Pillow fallback for the None case.
    """

    from PIL import Image

    array = turbo_decode(path)

    if array is None:
        return None

    # Image.frombuffer shares the buffer — keep the array alive as long as the
    # PIL image exists.
    image = Image.frombuffer("RGB", (array.shape[1], array.shape[0]), array)
    image._source_array = array  # noqa: SLF001 — keepalive reference
    return image