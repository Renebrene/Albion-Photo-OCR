"""
Кропы для обрезанных JPEG.

Битая (недокопированная) картинка уже получает превью: PREVIEW декодирует
источник через libjpeg-turbo, который дочитывает файл серым. Детекция
открывала источник обычным Pillow и падала с "broken data stream", поэтому
у таких фото не появлялось ни кропов, ни региона — а значит и «Похожих».
Здесь проверяется, что нарезка кропа использует тот же терпимый декодер.
"""

from __future__ import annotations

import io
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from app.billboard import pipeline
from app.preview.turbo_decode import decode_rgb, turbo_decode


def _truncated_jpeg(tmp_path, *, size=(200, 150), keep=0.6):
    """JPEG, у которого физически отсутствует хвост (как у недокопированного)."""

    array = np.random.default_rng(7).integers(
        0, 255, (*size[::-1], 3), dtype=np.uint8
    )
    buffer = io.BytesIO()
    Image.fromarray(array, "RGB").save(buffer, format="JPEG", quality=90)

    data = buffer.getvalue()
    path = tmp_path / "broken.jpg"
    path.write_bytes(data[: int(len(data) * keep)])

    return path


def _region(x, y, w, h, score=0.8):
    return {
        "bbox_x": x,
        "bbox_y": y,
        "bbox_w": w,
        "bbox_h": h,
        "score": score,
        "label": "billboard",
    }


def test_truncated_source_is_rejected_by_pillow(tmp_path):
    """Предпосылка теста: обычный Pillow на этом файле падает."""

    source = _truncated_jpeg(tmp_path)

    with pytest.raises(Exception):
        with Image.open(source) as image:
            image.load()


def test_decode_rgb_reads_truncated_jpeg(tmp_path):
    source = _truncated_jpeg(tmp_path)

    if turbo_decode(source) is None:
        pytest.skip("libjpeg-turbo недоступен в этом окружении")

    image = decode_rgb(source)

    assert image is not None
    assert image.size == (200, 150)


def test_write_crop_cuts_from_truncated_source(tmp_path):
    source = _truncated_jpeg(tmp_path)
    output = tmp_path / "crops" / "PH_broken" / "crop_01.jpg"

    width, height = pipeline.write_crop(
        source, _region(20, 10, 100, 60), output
    )

    assert (width, height) == (100, 60)
    assert output.is_file()

    with Image.open(output) as crop:
        assert crop.size == (100, 60)


def test_detect_falls_back_when_opencv_cannot_open(monkeypatch, tmp_path):
    """Если cv2 не открыл файл, детекция пробует терпимый декодер."""

    import cv2

    from app.billboard import detector

    source = _truncated_jpeg(tmp_path)

    if turbo_decode(source) is None:
        pytest.skip("libjpeg-turbo недоступен в этом окружении")

    seen = {}

    class FakeBoxes(list):
        pass

    class FakeModel:
        def predict(self, image, conf=None, verbose=None):
            seen["shape"] = np.asarray(image).shape
            return [SimpleNamespace(boxes=FakeBoxes(), names={})]

    monkeypatch.setattr(cv2, "imread", lambda path: None)
    monkeypatch.setattr(detector, "_load_model", lambda *a, **k: FakeModel())

    regions = detector.detect_billboards(
        source,
        config={
            "enabled": True,
            "score": 0.4,
            "padding": 0.0,
            "max_side": 1920,
            "classes": ("billboard",),
            "model": "unused.pt",
            "detector": "test",
            "second_ratio": 0.35,
            "max_regions": 2,
        },
    )

    assert regions == []
    assert seen["shape"] == (150, 200, 3)
