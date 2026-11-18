"""CLIP pilot: build FAISS IndexFlatIP over precomputed crop embeddings.

Reads embeddings (.npy) + metadata (.jsonl) produced by clip_pilot_embed.py,
L2-normalizes (embeddings are already normalized, re-check defensively),
builds an IndexFlatIP (exact inner product == cosine on unit vectors),
saves index and metadata sidecar to data/experiments/clip_pilot/.

Usage:
    uv run --offline python scripts/clip_pilot_index.py \
        --emb data/experiments/clip_pilot/clip_embeddings_full.npy \
        --tag full
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import faiss
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--emb", type=Path, required=True, help="embeddings .npy")
    p.add_argument(
        "--meta",
        type=Path,
        default=None,
        help="metadata .jsonl (default: derived from --emb name)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "data/experiments/clip_pilot",
    )
    p.add_argument("--tag", required=True, help="output filename tag")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    meta_path = args.meta or args.emb.with_name(
        args.emb.name.replace("clip_embeddings", "clip_meta").replace(".npy", ".jsonl")
    )

    t0 = time.time()
    emb = np.load(args.emb).astype(np.float32)
    norms = np.linalg.norm(emb, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-3):
        emb = emb / norms[:, None]
    meta = [json.loads(line) for line in meta_path.read_text().splitlines() if line]
    assert len(meta) == emb.shape[0], f"meta {len(meta)} != emb {emb.shape[0]}"

    dim = emb.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(emb)
    dt = time.time() - t0

    index_path = args.out / f"clip_index_{args.tag}.faiss"
    meta_out = args.out / f"clip_index_{args.tag}.meta.jsonl"
    faiss.write_index(index, str(index_path))
    meta_out.write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in meta) + "\n",
        encoding="utf-8",
    )

    size_kb = index_path.stat().st_size / 1024
    info = {
        "index_type": "IndexFlatIP (exact cosine, unit vectors)",
        "n_vectors": int(index.ntotal),
        "dim": dim,
        "build_seconds": round(dt, 2),
        "index_size_kb": round(size_kb, 1),
        "bytes_per_vector": round(size_kb * 1024 / index.ntotal, 1),
        "index_file": index_path.name,
        "meta_file": meta_out.name,
    }
    (args.out / f"index_info_{args.tag}.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(info, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
