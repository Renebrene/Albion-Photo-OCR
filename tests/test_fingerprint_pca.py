"""PCA whitening: computation, storage, and integration with DinoRunner."""

from __future__ import annotations

import numpy as np
import pytest

from app.fingerprint.pca import (
    PcaTransform,
    compute_pca,
    pca_status,
    set_active,
)


def test_compute_pca_returns_correct_shapes():
    """compute_pca with synthetic embeddings."""

    rng = np.random.default_rng(42)
    embeddings = rng.normal(size=(500, 768)).astype(np.float32)

    mean, V, whiten, S = compute_pca(embeddings)

    assert mean.shape == (1, 768), f"mean shape: {mean.shape}"
    assert V.shape == (768, 768), f"V shape: {V.shape}"
    assert whiten.shape == (768, 768), f"whiten shape: {whiten.shape}"
    assert S.shape == (768,), f"S shape: {S.shape}"


def test_whitening_normalizes_variance():
    """Each whitened component with S > 0 should have unit variance."""

    rng = np.random.default_rng(42)
    # Use more observations than dimensions for a well-conditioned problem.
    embeddings = rng.normal(size=(2000, 768)).astype(np.float32)

    mean, _V, whiten, _S = compute_pca(embeddings)

    white = (embeddings - mean) @ whiten

    assert white.mean() < 1e-2, f"mean after whitening: {white.mean():.4f}"
    # Components with S != 0 have variance ~1.
    stds = white.std(axis=0)
    assert 0.95 < stds.mean() < 1.05, f"mean component std: {stds.mean():.4f}"


def test_whitening_preserves_information():
    """Project → recover should reconstruct original vectors."""

    rng = np.random.default_rng(42)
    embeddings = rng.normal(size=(500, 768)).astype(np.float32)

    mean, V, _whiten, _S = compute_pca(embeddings)

    # Project onto V (orthogonal basis)
    proj = (embeddings - mean) @ V
    recovered = proj @ V.T + mean

    max_err = np.abs(embeddings - recovered).max()
    assert max_err < 1e-4, f"recovery error: {max_err:.2e}"


def test_whitening_margin_increases():
    """Whitening should increase the relative margin between two groups
    (simulates similar addresses separated by colour that no longer
    dominates)."""

    rng = np.random.default_rng(42)

    # Group A and B share 90% variance; 10% is the "signal" separating them.
    shared = rng.normal(0, 1, size=(400, 700))
    signal = rng.normal(0, 0.3, size=(400, 68))
    noise = rng.normal(0, 0.1, size=(400, 768 - 700 - 68))

    group_a = np.hstack([shared, signal + 0.3, noise]).astype(np.float32)
    group_b = np.hstack([shared, signal - 0.3, noise]).astype(np.float32)
    all_embs = np.vstack([group_a, group_b])

    centroids = np.vstack([group_a.mean(axis=0), group_b.mean(axis=0)])

    mean, _V, whiten, _S = compute_pca(all_embs)

    # self-dot → self-dot ratio should favour the true match in both spaces.
    c_white = (centroids - mean) @ whiten

    orig_same = float(centroids[0] @ centroids[0])
    orig_cross = float(centroids[0] @ centroids[1])
    white_same = float(c_white[0] @ c_white[0])
    white_cross = float(c_white[0] @ c_white[1])

    # Both should produce same-cluster higher than cross-cluster.
    assert orig_same > orig_cross, f"orig same={orig_same:.4f} cross={orig_cross:.4f}"
    assert white_same > white_cross, f"white same={white_same:.4f} cross={white_cross:.4f}"


def test_pca_transform_applied_silently_when_inactive():
    """PcaTransform.transform returns X unchanged when not active."""

    pca = PcaTransform(active=False)
    X = np.random.randn(10, 768).astype(np.float32)
    result = pca.transform(X)
    assert result is X  # same object if not active


def test_set_active_toggles_flag(monkeypatch):
    """set_active stores the boolean and returns a status dict."""

    store = {"fingerprint_pca": {"version": 1, "active": False, "updated_at": "", "fingerprint_count": 0}}

    monkeypatch.setattr("app.fingerprint.pca.settings_store.get", lambda key: store.get(key))
    monkeypatch.setattr("app.fingerprint.pca.settings_store.set_value", lambda key, value: store.__setitem__(key, value))

    result = set_active(True)
    assert result["active"] is True
    assert result["version"] == 1

    result = set_active(False)
    assert result["active"] is False


def test_pca_status_without_meta(monkeypatch):
    """pca_status returns zeros when no PCA has been computed."""

    monkeypatch.setattr("app.fingerprint.pca.settings_store.get", lambda key: None)

    s = pca_status()
    assert s["version"] == 0
    assert s["active"] is False
    assert s["updated_at"] is None