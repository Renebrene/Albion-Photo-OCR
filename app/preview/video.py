"""Atomic poster-frame generation for registered source videos."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

from PIL import Image

VIDEO_ID_RE = re.compile(r"^VI_[0-9a-f]{24}$")


def default_video_preview_root() -> Path:
    preview_root = Path(os.getenv("SCENE_PREVIEW_ROOT", "data/preview"))
    return Path(os.getenv("SCENE_VIDEO_PREVIEW_ROOT", str(preview_root / "videos")))


def build_video_poster(
    video_id: str,
    source_path: str | Path,
    output_root: str | Path,
    *,
    duration_seconds: float | None = None,
) -> Path:
    """Write one JPEG poster to a managed preview root, never beside the source."""

    if not VIDEO_ID_RE.fullmatch(video_id):
        raise ValueError("invalid video id")
    source = Path(source_path)
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"{video_id}.jpg"
    fd, temporary_name = tempfile.mkstemp(prefix=f".{video_id}-", suffix=".jpg", dir=root)
    os.close(fd)
    temporary = Path(temporary_name)
    capture = None
    try:
        import cv2

        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise ValueError("video cannot be opened for poster generation")
        seek_seconds = max(0.0, min((duration_seconds or 0.0) / 10.0, 2.0))
        if seek_seconds:
            capture.set(cv2.CAP_PROP_POS_MSEC, seek_seconds * 1000)
        ok, frame = capture.read()
        if not ok or frame is None:
            capture.set(cv2.CAP_PROP_POS_MSEC, 0)
            ok, frame = capture.read()
        if not ok or frame is None or not cv2.imwrite(str(temporary), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82]):
            raise ValueError("video frame could not be written")
        with Image.open(temporary) as image:
            if image.format != "JPEG" or image.width <= 0 or image.height <= 0:
                raise ValueError("poster is not a valid JPEG")
            image.verify()
        os.replace(temporary, target)
        return target
    finally:
        if capture is not None:
            capture.release()
        temporary.unlink(missing_ok=True)
