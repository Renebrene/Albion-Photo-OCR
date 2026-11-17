"""TurboJPEG decode: MPO и JPEG с libjpeg-turbo, fallback на Pillow."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.ingest.register import PhotoRecord
from app.preview.generator import _load_visual_source, build_preview_paths, generate_previews
from app.preview.turbo_decode import turbo_decode


def _mpo_bytes(size=(3000, 4000)) -> bytes:
    """Create synthetic 2-frame MPO (first frame random, second black)."""

    arr1 = (np.random.default_rng(42).integers(0, 255, (*size, 3), dtype=np.uint8) // 4) * 4
    arr2 = np.zeros((*size, 3), dtype=np.uint8)

    buf = io.BytesIO()
    Image.fromarray(arr1, "RGB").save(buf, format="JPEG", quality=85)
    frame1 = buf.getvalue()

    buf = io.BytesIO()
    Image.fromarray(arr2, "RGB").save(buf, format="JPEG", quality=85)
    frame2 = buf.getvalue()

    return frame1 + frame2


@pytest.fixture
def mpo_file(tmp_path) -> Path:
    """Create a real MPO file on disk."""

    path = tmp_path / "test.mpo"
    path.write_bytes(_mpo_bytes())
    return path


def test_turbo_decode_returns_rgb_array(mpo_file):
    array = turbo_decode(str(mpo_file))

    assert array is not None
    assert array.dtype == np.uint8
    assert array.ndim == 3
    assert array.shape[2] == 3  # RGB
    assert array.shape[0] == 3000  # height
    assert array.shape[1] == 4000  # width


def test_turbo_decode_handles_mpo_first_frame(mpo_file):
    """MPO has two frames; turbo_decode must return only frame 0."""

    array = turbo_decode(str(mpo_file))

    assert array is not None
    # The first frame is nearly-white random; the second is black.
    # If both were decoded the mean would be much lower (half the image black).
    assert float(array.mean()) > 80, (
        f"first frame only expected, got mean={array.mean():.1f}"
    )


def test_turbo_decode_fallback_on_missing_library(monkeypatch, mpo_file):
    """When the library cannot be loaded, returns None (caller falls back)."""

    monkeypatch.setattr(
        "app.preview.turbo_decode._load_turbojpeg",
        lambda: None,
    )

    assert turbo_decode(str(mpo_file)) is None


def test_load_visual_source_uses_turbo_when_available(monkeypatch, mpo_file):
    """_load_visual_source forwards the array from turbo_decode."""

    record = PhotoRecord(
        photo_id="PH_" + "b" * 24,
        source_path=str(mpo_file),
        filename=mpo_file.name,
        sha256=hashlib.sha256(mpo_file.read_bytes()).hexdigest(),
        container_format="MPO",
        frame_count=2,
        width=4000,
        height=3000,
    )

    img = _load_visual_source(record)

    assert img.size == (4000, 3000)
    assert img.mode == "RGB"
    assert hasattr(img, "_source_array"), "expected turbo_path, not Pillow"


def test_load_visual_source_falls_back_to_pillow_without_turbo(monkeypatch, mpo_file):
    """When turbo_decode is unavailable, Pillow handles MPO normally."""

    monkeypatch.setattr(
        "app.preview.turbo_decode._load_turbojpeg",
        lambda: None,
    )

    record = PhotoRecord(
        photo_id="PH_" + "d" * 24,
        source_path=str(mpo_file),
        filename=mpo_file.name,
        sha256=hashlib.sha256(mpo_file.read_bytes()).hexdigest(),
        container_format="MPO",
        frame_count=2,
        width=4000,
        height=3000,
    )

    img = _load_visual_source(record)

    assert img.size == (4000, 3000)
    assert img.mode == "RGB"
    assert not hasattr(img, "_source_array"), "Pillow path, not turbo"


def test_full_preview_pipeline_with_mpo(monkeypatch, mpo_file, tmp_path):
    """Full generate_previews with an MPO file using TurboJPEG."""

    record = PhotoRecord(
        photo_id="PH_" + "c" * 24,
        source_path=str(mpo_file),
        filename=mpo_file.name,
        sha256=hashlib.sha256(mpo_file.read_bytes()).hexdigest(),
        container_format="MPO",
        frame_count=2,
        width=4000,
        height=3000,
    )

    result = generate_previews(
        record=record,
        preview_root=tmp_path,
        small_size=320,
        middle_size=1280,
    )

    assert result.ready is True

    paths = build_preview_paths(preview_root=tmp_path, photo_id=record.photo_id)

    with Image.open(paths.small) as small:
        assert max(small.size) == 320

    with Image.open(paths.middle) as middle:
        assert max(middle.size) == 1280