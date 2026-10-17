"""Unreadable source files are skipped instead of failing a fingerprint build."""

from __future__ import annotations

from PIL import Image

from app.core.fingerprint import readable_paths


def test_corrupt_image_is_skipped(tmp_path):
    good = tmp_path / "good.JPG"
    Image.new("RGB", (64, 48), (10, 20, 30)).save(good, format="JPEG")

    bad = tmp_path / "bad.JPG"
    bad.write_bytes(b"this is not a JPEG at all")

    readable, skipped = readable_paths([good, bad])

    assert readable == [good]
    assert skipped == [{"name": "bad.JPG", "error": "UnidentifiedImageError"}]


def test_all_readable_files_survive(tmp_path):
    first = tmp_path / "a.jpg"
    second = tmp_path / "b.jpg"
    Image.new("RGB", (10, 10), (1, 2, 3)).save(first, format="JPEG")
    Image.new("RGB", (10, 10), (4, 5, 6)).save(second, format="JPEG")

    readable, skipped = readable_paths([first, second])

    assert readable == [first, second]
    assert skipped == []
