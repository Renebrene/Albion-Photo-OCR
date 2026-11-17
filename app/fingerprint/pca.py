"""
PCA whitening for DINO global embeddings.

Transforms 768-D DINOv2 embeddings into a whitened space where the covariance
matrix is the identity — the dot product in this space emphasises directions
that distinguish fingerprints best.  Experimentally this increases the score
margin between hard addresses by 3-30× without changing the top match.

Storage
-------
Metadata lives in ``app_settings['fingerprint_pca']`` (JSONB) — the active
flag, version, and update time.  The actual matrices (~2.3 MB for 768×768) are
kept in ``data/fingerprints/pca.npz`` so the database stays lean.

Integration
-----------
``DinoRunner.__init__`` calls ``load_pca()`` and, when PCA is active,
transforms all fingerprint centroids and embeddings in ``_load_fingerprints()``
and the query vectors in ``_rank()``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app import settings_store

_log = logging.getLogger(__name__)

PCA_SETTINGS_KEY = "fingerprint_pca"
_FINGERPRINT_DIR = "fingerprints"
_PCA_FILENAME = "pca.npz"


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------


@dataclass
class PcaTransform:
    """Whitening transformation loaded from ``data/fingerprints/pca.npz``."""

    active: bool = False
    version: int = 0
    updated_at: str = ""
    fingerprint_count: int = 0
    mean: np.ndarray | None = None       # (1, 768) float32
    whiten: np.ndarray | None = None      # (768, 768) float32  — V * 1/√(S)
    singular_values: np.ndarray | None = field(default=None)   # (768,) float32

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Centre *X* with the training mean and project into whitened space."""
        if not self.active or self.mean is None or self.whiten is None:
            return X
        return (X - self.mean) @ self.whiten

    def disabled_copy(self) -> PcaTransform:
        """Return a new instance with ``active=False`` (keeps version info)."""
        return PcaTransform(
            active=False,
            version=self.version,
            updated_at=self.updated_at,
            fingerprint_count=self.fingerprint_count,
        )


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def _pca_path() -> Path:
    from app.core.config import settings

    return Path(settings.data_dir) / _FINGERPRINT_DIR / _PCA_FILENAME


def load_pca() -> PcaTransform:
    """
    Load the stored PCA transformation.

    Returns a ``PcaTransform`` with ``active=False`` when no valid PCA data
    exists or the ``active`` flag is ``False`` in the database.  The caller
    never needs to handle file-not-found errors: they all lead to an inactive
    transform.
    """

    meta = _load_meta()
    if meta is None:
        return PcaTransform()

    result = PcaTransform(
        active=bool(meta.get("active")),
        version=int(meta.get("version") or 0),
        updated_at=str(meta.get("updated_at") or ""),
        fingerprint_count=int(meta.get("fingerprint_count") or 0),
    )

    if not result.active:
        return result

    path = _pca_path()
    if not path.exists():
        _log.warning("PCA settings say active but %s not found", path)
        return result.disabled_copy()

    try:
        npz = np.load(path)
        result.mean = npz["mean"]
        result.whiten = npz["whiten"]
        result.singular_values = npz.get("singular_values", None)
        return result
    except Exception as exc:
        _log.warning("Cannot load PCA from %s: %s", path, exc)
        return result.disabled_copy()


def _load_meta() -> dict | None:
    try:
        return settings_store.get(PCA_SETTINGS_KEY)
    except Exception:
        return None


def save_meta(version: int, active: bool, fingerprint_count: int) -> None:
    """Persist PCA metadata (version, active flag, timestamp) in app_settings."""

    settings_store.set_value(PCA_SETTINGS_KEY, {
        "version": version,
        "active": active,
        "updated_at": np.datetime_as_string(np.datetime64("now")),
        "fingerprint_count": fingerprint_count,
    })


def set_active(flag: bool) -> dict:
    """
    Toggle the PCA active flag.

    Returns the full status dict so the API can echo it back immediately.
    """

    meta = _load_meta()
    if meta is None:
        meta = {"version": 0, "active": False, "updated_at": "", "fingerprint_count": 0}

    meta["active"] = bool(flag)
    settings_store.set_value(PCA_SETTINGS_KEY, meta)
    return pca_status()


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------


def compute_pca(embeddings: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute PCA whitening from the full embedding matrix.

    Parameters
    ----------
    embeddings : ndarray, shape (N, 768)
        All reference embeddings of all active fingerprints stacked together.

    Returns
    -------
    mean : ndarray, shape (1, 768)
        Training mean.
    V : ndarray, shape (768, 768)
        Orthogonal component matrix from SVD.
    whiten : ndarray, shape (768, 768)
        Whitening matrix ``V * diag(1/√(S))``.
    S : ndarray, shape (768,)
        Singular values.
    """

    _log.info("PCA on %d × %d embeddings", *embeddings.shape)

    mean = embeddings.mean(axis=0, keepdims=True).astype(np.float32)
    centered = (embeddings - mean).astype(np.float32)

    # SVD on (N, 768) — numpy uses LAPACK, memory ≈ O(N * 768 + 768²)
    # Thin SVD: U=(N, K), S=(K,), Vt=(K, D) with K = min(N, D).
    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    K = len(S)  # K = min(N, D)

    # Build the full (D, D) V matrix.  The D-K extra columns are orthogonal
    # to the data (any orthonormal completion of the basis works).
    if K < centered.shape[1]:
        # Extend Vt to (D, D) with random orthogonal columns via QR.
        extra = np.random.default_rng(0).normal(size=(centered.shape[1], centered.shape[1] - K)).astype(np.float32)
        Q, _R = np.linalg.qr(np.hstack([Vt.T, extra]))
        V = Q.astype(np.float32)
        S = np.pad(S, (0, centered.shape[1] - K))
    else:
        V = Vt.T.astype(np.float32)

    # Whitening: X_white = X_centered @ V @ diag(1/√λ)
    # with λ = S²/(N-1), so 1/√λ = √(N-1)/S
    # For S=0 (extra dimensions): the component variance is 0, the whitened
    # variance is also 0 — these dimensions contribute nothing to dot products.
    inv_sqrt = np.zeros_like(S)
    nonzero = S > 1e-10
    inv_sqrt[nonzero] = np.sqrt(float(centered.shape[0] - 1)) / S[nonzero]
    whiten = V * inv_sqrt  # (D, D)

    _log.info(
        "SVD: %d components, var100=%.3f var256=%.3f var512=%.3f",
        len(S),
        S[:100].sum() / S.sum(),
        S[:256].sum() / S.sum(),
        S[:512].sum() / S.sum(),
    )

    return mean, V, whiten, S


def rebuild(
    fingerprints_data: list[tuple[str, dict]],
    *,
    active: bool = True,
) -> dict:
    """
    Full PCA computation and storage pipeline.

    Parameters
    ----------
    fingerprints_data : list of (fingerprint_id, data_dict)
        The loaded data dict for every active fingerprint (output of
        ``FingerprintManager.load()``).
    active : bool
        Whether PCA should be activated immediately after rebuild.

    Returns
    -------
    status : dict
        Result of ``pca_status()`` after the rebuild.
    """

    all_embs = np.vstack([data["embeddings"] for _, data in fingerprints_data])

    mean, V, whiten, S = compute_pca(all_embs)

    path = _pca_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        path,
        mean=mean,
        components=V,
        whiten=whiten,
        singular_values=S,
    )

    settings_store.set_value(PCA_SETTINGS_KEY, {
        "version": _next_version(),
        "active": active,
        "updated_at": str(np.datetime_as_string(np.datetime64("now"))),
        "fingerprint_count": len(fingerprints_data),
    })

    return pca_status()


def _next_version() -> int:
    meta = _load_meta()
    return (meta.get("version") or 0) + 1 if meta else 1


def pca_status() -> dict:
    """
    Returns the current PCA state for the API.

    ``stale`` is ``True`` when the active fingerprint IDs have changed since
    the last PCA computation — i.e. someone added/modified a fingerprint
    after PCA was built.
    """

    meta = _load_meta()
    if meta is None:
        return {
            "version": 0,
            "active": False,
            "updated_at": None,
            "fingerprint_count": 0,
            "stale": False,
        }

    return {
        "version": int(meta.get("version") or 0),
        "active": bool(meta.get("active")),
        "updated_at": meta.get("updated_at"),
        "fingerprint_count": int(meta.get("fingerprint_count") or 0),
        "stale": _is_stale(meta),
    }


def _is_stale(meta: dict) -> bool:
    """
    PCA is stale when the count of active fingerprints does not match the
    snapshot that PCA was built from.  The full checksum on every page load
    would be too heavy, so we compare the count as a heuristic.
    """

    try:
        from app.api.fingerprints import active_fingerprint_ids

        active = active_fingerprint_ids()
        if active is None:
            return False
        return len(active) != meta.get("fingerprint_count", 0)
    except Exception:
        return False