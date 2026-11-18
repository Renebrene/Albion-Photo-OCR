"""CLIP pilot: search demo — top-10 similar crops by image and text queries.

Loads a FAISS IndexFlatIP + metadata sidecar built by clip_pilot_index.py.
- 5 random image queries: pick a crop, embed it on CPU, search nearest neighbors
  (excluding the query crop itself).
- 3 text queries (RU/EN): encode with the CLIP text encoder, search.

Writes results to data/experiments/clip_pilot/search_results_<tag>.md and .json.

Usage:
    CUDA_VISIBLE_DEVICES="" uv run --offline python scripts/clip_pilot_search.py \
        --tag full --queries 5
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

assert True  # noqa: E402  (env check below must come first)

import os

if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
    print("set CUDA_VISIBLE_DEVICES='' before running", file=sys.stderr)
    sys.exit(1)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import faiss
import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "openai/clip-vit-base-patch32"

TEXT_QUERIES = [
    ("red billboard with white text", "en"),
    ("outdoor advertising billboard on a building wall", "en"),
    ("вывеска магазина", "ru"),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tag", default="full")
    p.add_argument("--queries", type=int, default=5, help="number of image queries")
    p.add_argument("--topk", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--dir", type=Path, default=PROJECT_ROOT / "data/experiments/clip_pilot"
    )
    return p.parse_args()


def load_index(tag: str, out: Path):
    index = faiss.read_index(str(out / f"clip_index_{tag}.faiss"))
    meta = [
        json.loads(line)
        for line in (out / f"clip_index_{tag}.meta.jsonl").read_text().splitlines()
        if line
    ]
    emb = np.load(out / f"clip_embeddings_{tag}.npy")
    return index, meta, emb


def fmt_row(m: dict, score: float, rank: int) -> str:
    return (
        f"| {rank} | {m['region_id']} | {m['photo_id']} | "
        f"`{Path(m['crop_path']).name}` | {score:.4f} |"
    )


def main() -> int:
    args = parse_args()
    index, meta, emb = load_index(args.tag, args.dir)
    print(f"index: {index.ntotal} vectors, dim {index.d}", flush=True)

    t0 = time.time()
    model = CLIPModel.from_pretrained(MODEL_ID).eval().to("cpu")
    processor = CLIPProcessor.from_pretrained(MODEL_ID)
    print(f"model loaded in {time.time() - t0:.1f}s", flush=True)

    results = {"model": MODEL_ID, "n_vectors": int(index.ntotal), "queries": []}

    # --- image queries -----------------------------------------------------
    rng = random.Random(args.seed)
    for q in range(1, args.queries + 1):
        qi = rng.randrange(len(meta))
        qmeta = meta[qi]
        t = time.time()
        D, I = index.search(emb[qi : qi + 1], args.topk + 1)
        dt_ms = (time.time() - t) * 1000
        rows = []
        for rank, (score, idx) in enumerate(zip(D[0], I[0]), start=1):
            if idx == qi:
                continue  # skip the query itself
            if len(rows) >= args.topk:
                break
            rows.append(fmt_row(meta[int(idx)], float(score), len(rows) + 1))
        entry = {
            "type": "image",
            "query_region_id": qmeta["region_id"],
            "query_photo_id": qmeta["photo_id"],
            "query_crop_path": qmeta["crop_path"],
            "search_ms": round(dt_ms, 1),
            "hits": [
                {
                    "rank": r,
                    "region_id": meta[int(i)]["region_id"],
                    "photo_id": meta[int(i)]["photo_id"],
                    "crop_path": meta[int(i)]["crop_path"],
                    "score": float(s),
                }
                for r, (s, i) in enumerate(zip(D[0], I[0]), start=1)
                if int(i) != qi
            ][: args.topk],
        }
        results["queries"].append(entry)
        print(
            f"[image {q}] region_id={qmeta['region_id']} photo_id={qmeta['photo_id']} "
            f"({dt_ms:.1f} ms) top1: region {entry['hits'][0]['region_id']} "
            f"score {entry['hits'][0]['score']:.4f}",
            flush=True,
        )

    # --- text queries ------------------------------------------------------
    for text, lang in TEXT_QUERIES:
        t = time.time()
        inputs = processor(text=[text], return_tensors="pt", padding=True).to("cpu")
        with torch.inference_mode():
            feats = model.get_text_features(**inputs)
        if hasattr(feats, "pooler_output"):
            feats = feats.pooler_output
        feats = feats / feats.norm(dim=-1, keepdim=True)
        D, I = index.search(feats.numpy().astype(np.float32), args.topk)
        dt_ms = (time.time() - t) * 1000
        entry = {
            "type": "text",
            "query": text,
            "lang": lang,
            "search_ms": round(dt_ms, 1),
            "hits": [
                {
                    "rank": r,
                    "region_id": meta[int(i)]["region_id"],
                    "photo_id": meta[int(i)]["photo_id"],
                    "crop_path": meta[int(i)]["crop_path"],
                    "score": float(s),
                }
                for r, (s, i) in enumerate(zip(D[0], I[0]), start=1)
            ],
        }
        results["queries"].append(entry)
        print(
            f"[text:{lang}] '{text}' ({dt_ms:.1f} ms) top1: region "
            f"{entry['hits'][0]['region_id']} score {entry['hits'][0]['score']:.4f}",
            flush=True,
        )

    # --- write outputs -----------------------------------------------------
    out_json = args.dir / f"search_results_{args.tag}.json"
    out_json.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# CLIP пилот: примеры поиска",
        "",
        f"Модель: {MODEL_ID} (CPU) · векторов в индексе: {index.ntotal} · "
        f"dim: {index.d} · метрика: cosine (IndexFlatIP)",
        "",
        "## Запросы по изображению (top-10 похожих кропов)",
        "",
    ]
    for entry in results["queries"]:
        if entry["type"] != "image":
            continue
        lines += [
            f"### Запрос: region_id={entry['query_region_id']} "
            f"photo_id={entry['query_photo_id']} "
            f"({Path(entry['query_crop_path']).name}, {entry['search_ms']} мс)",
            "",
            "| # | region_id | photo_id | crop | score |",
            "|---|-----------|----------|------|-------|",
            *[
                fmt_row(h, h["score"], h["rank"])
                for h in entry["hits"]
            ],
            "",
        ]
    lines += ["## Текстовые запросы (top-10)", ""]
    for entry in results["queries"]:
        if entry["type"] != "text":
            continue
        lines += [
            f"### Запрос: \"{entry['query']}\" ({entry['lang']}, "
            f"{entry['search_ms']} мс)",
            "",
            "| # | region_id | photo_id | crop | score |",
            "|---|-----------|----------|------|-------|",
            *[fmt_row(h, h["score"], h["rank"]) for h in entry["hits"]],
            "",
        ]
    out_md = args.dir / f"search_results_{args.tag}.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_json} and {out_md}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
