"""v3.3 remains the default; v3.5 is accepted as an optional profile."""

from __future__ import annotations

from types import SimpleNamespace

import faiss
import numpy as np
import pytest

from app.core.fingerprint import FingerprintManager


def _write_fingerprint(root, fingerprint_id: str, version: str) -> None:
    directory = root / fingerprint_id
    directory.mkdir()
    np.save(directory / "embeddings.npy", np.zeros((1, 768), dtype=np.float32))
    np.save(directory / "centroid.npy", np.zeros(768, dtype=np.float32))
    np.save(directory / "representatives.npy", np.zeros((1, 768), dtype=np.float32))
    np.save(directory / "representative_indices.npy", np.zeros(1, dtype=np.int32))
    np.save(directory / "environment_embeddings.npy", np.zeros((1, 640), dtype=np.float32))
    np.save(directory / "color_embeddings.npy", np.zeros((1, 48), dtype=np.float32))
    np.save(directory / "spatial_embeddings.npy", np.zeros((1, 32), dtype=np.float32))
    faiss.write_index(faiss.IndexFlatIP(768), str(directory / "faiss.index"))
    (directory / "metadata.json").write_text(
        '{"id": "%s", "version": "%s", "images": 1, "dimension": 768}'
        % (fingerprint_id, version),
        encoding="utf-8",
    )


def test_v35_fingerprint_loads_without_new_embedding_dimension(tmp_path):
    _write_fingerprint(tmp_path, "51_v35", "3.5")
    manager = FingerprintManager(
        SimpleNamespace(fingerprints_dir=tmp_path),
        embedder=None,
    )

    data = manager.load("51_v35")

    assert data["metadata"]["version"] == "3.5"
    assert data["embeddings"].shape == (1, 768)


def test_unknown_fingerprint_version_is_rejected(tmp_path):
    _write_fingerprint(tmp_path, "bad_v34", "3.4")
    manager = FingerprintManager(
        SimpleNamespace(fingerprints_dir=tmp_path),
        embedder=None,
    )

    with pytest.raises(ValueError, match="supported"):
        manager.load("bad_v34")


def test_default_build_version_stays_v33():
    assert FingerprintManager.VERSION == "3.3"
    assert FingerprintManager.SUPPORTED_VERSIONS == ("3.3", "3.5")
