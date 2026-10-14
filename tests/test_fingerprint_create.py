"""
Unit tests for atomic fingerprint publication in FingerprintManager.create().

No DINO model is loaded: a stub embedder returns fixed 768-D vectors, and a
failing embedder simulates a mid-build error. Real JPEG files are used only so
the CPU compact descriptors can be computed.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from PIL import Image

from app.core.config import settings as base_settings
from app.core.fingerprint import FingerprintManager


class _StubEmbedder:
    def embed_paths(self, paths, on_batch=None):
        count = len(list(paths))

        # The builder reports progress through on_batch; a double must accept
        # it the same way the real embedder does.
        if on_batch is not None:
            on_batch(count, count)

        return np.random.default_rng(0).random((count, 768), dtype=np.float32)


class _FailingEmbedder:
    def embed_paths(self, paths, on_batch=None):
        raise RuntimeError("embedding failed")


def _make_images(root):
    source = root / "src"
    source.mkdir()
    for index in range(3):
        Image.new("RGB", (48, 32), (index * 50, 10, 10)).save(
            source / f"{index}.jpg", format="JPEG"
        )
    return source


def _manager(tmp_path, embedder):
    settings = replace(base_settings, data_dir=tmp_path)
    return settings, FingerprintManager(settings, embedder)


def test_failed_create_leaves_no_fingerprint(tmp_path):
    settings, manager = _manager(tmp_path, _FailingEmbedder())
    source = _make_images(tmp_path)

    with pytest.raises(RuntimeError):
        manager.create("fp_fail", source)

    assert not (settings.fingerprints_dir / "fp_fail").exists()
    leftovers = [
        path
        for path in settings.fingerprints_dir.iterdir()
        if path.name.startswith(".fp_fail.tmp-")
    ]
    assert leftovers == []


def test_successful_create_publishes_complete_fingerprint(tmp_path):
    settings, manager = _manager(tmp_path, _StubEmbedder())
    source = _make_images(tmp_path)

    metadata = manager.create("fp_ok", source)

    output = settings.fingerprints_dir / "fp_ok"
    for name in (
        "embeddings.npy",
        "centroid.npy",
        "representatives.npy",
        "faiss.index",
        "metadata.json",
    ):
        assert (output / name).exists()

    assert metadata["id"] == "fp_ok"
    assert metadata["version"] == "3.3"
    # The configured model name is recorded, not a hardcoded label.
    assert metadata["model"] == settings.model_name

    data = manager.load("fp_ok")
    assert data["embeddings"].shape == (3, 768)


def test_existing_fingerprint_is_not_overwritten(tmp_path):
    settings, manager = _manager(tmp_path, _StubEmbedder())
    source = _make_images(tmp_path)

    manager.create("fp_dup", source)

    with pytest.raises(FileExistsError):
        manager.create("fp_dup", source)


def test_retry_after_failure_succeeds(tmp_path):
    settings, _ = _manager(tmp_path, _StubEmbedder())
    source = _make_images(tmp_path)

    with pytest.raises(RuntimeError):
        FingerprintManager(
            settings, _FailingEmbedder()
        ).create("fp_retry", source)

    FingerprintManager(settings, _StubEmbedder()).create("fp_retry", source)

    assert (settings.fingerprints_dir / "fp_retry" / "metadata.json").exists()
