"""CLIP pilot: compute image embeddings for billboard crops on CPU.

Read-only pipeline: SELECT from public.photo_regions (kind='billboard'),
embed existing crop files with openai/clip-vit-base-patch32 on CPU,
write embeddings (.npy) + metadata (jsonl) into data/experiments/clip_pilot/.

Usage:
    CUDA_VISIBLE_DEVICES="" uv run --offline python scripts/clip_pilot_embed.py \
        [--limit 1000] [--batch 32] [--all] [--out data/experiments/clip_pilot]

Everything runs on CPU: model.to("cpu"), CUDA is disabled via env.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

assert os.environ.get("CUDA_VISIBLE_DEVICES") == "", (
    "set CUDA_VISIBLE_DEVICES='' before running: GPU is reserved for another job"
)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import torch
from PIL import Image, ImageFile
from transformers import CLIPModel, CLIPProcessor

from app.ingest.database import get_connection

ImageFile.LOAD_TRUNCATED_IMAGES = True
MODEL_ID = "openai/clip-vit-base-patch32"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=1000, help="max crops to embed")
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--all", action="store_true", help="embed every crop that exists on disk")
    p.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "data/experiments/clip_pilot",
    )
    p.add_argument("--tag", default="pilot1000", help="filename tag for outputs")
    p.add_argument("--workers", type=int, default=4, help="dataloader decode workers")
    return p.parse_args()


def fetch_crops(limit: int | None) -> list[dict]:
    """SELECT billboard crops whose files exist on disk (paths are project-relative)."""
    sql = (
        "SELECT region_id, photo_id, crop_path, score "
        "FROM public.photo_regions "
        "WHERE kind='billboard' AND crop_path IS NOT NULL "
        "ORDER BY region_id"
    )
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    crops = [
        {"region_id": r, "photo_id": p, "crop_path": c, "score": s}
        for r, p, c, s in rows
    ]
    # Only ~5.5k of ~39k crop files exist on disk (older rows were cleaned up),
    # so filter by existence first and apply the limit to what is actually usable.
    existing = [cr for cr in crops if (PROJECT_ROOT / cr["crop_path"]).exists()]
    if limit:
        existing = existing[:limit]
    print(
        f"DB rows fetched: {len(crops)}; files existing on disk: "
        f"{len(existing) if not limit else 'first ' + str(len(existing))}",
        flush=True,
    )
    return existing


def main() -> int:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    limit = None if args.all else args.limit

    crops = fetch_crops(limit)
    if not crops:
        print("No crops found — aborting.", file=sys.stderr)
        return 1

    t0 = time.time()
    model = CLIPModel.from_pretrained(MODEL_ID)
    processor = CLIPProcessor.from_pretrained(MODEL_ID)
    model.eval().to("cpu")
    print(f"model loaded on cpu in {time.time() - t0:.1f}s", flush=True)
    assert next(model.parameters()).device.type == "cpu"

    from torch.utils.data import DataLoader, Dataset

    class CropDataset(Dataset):
        def __init__(self, items: list[dict], size: int):
            self.items = items
            self.size = size

        def __len__(self) -> int:
            return len(self.items)

        def __getitem__(self, i: int):
            path = PROJECT_ROOT / self.items[i]["crop_path"]
            img = Image.open(path)
            img = img.convert("RGB")
            if img.size != (self.size, self.size):
                img = img.resize((self.size, self.size), Image.BICUBIC)
            return i, np.asarray(img, dtype=np.uint8)

    def collate(batch):
        idxs, imgs = zip(*batch)
        return list(idxs), np.stack(imgs)

    vision_size = processor.image_processor.size.get(
        "shortest_edge", processor.image_processor.size.get("height", 224)
    )
    ds = CropDataset(crops, vision_size)
    dl = DataLoader(
        ds,
        batch_size=args.batch,
        num_workers=args.workers,
        collate_fn=collate,
        prefetch_factor=4 if args.workers else None,
    )

    all_emb = np.zeros((len(crops), model.config.projection_dim), dtype=np.float32)
    done = 0
    t_start = time.time()

    def to_features(out):
        """transformers>=5 wraps projected embeds in BaseModelOutputWithPooling."""
        if hasattr(out, "image_embeds"):
            return out.image_embeds
        if hasattr(out, "pooler_output"):
            return out.pooler_output
        return out

    with torch.inference_mode():
        for idxs, arr in dl:
            pixel_values = processor.image_processor(
                images=arr, return_tensors="pt"
            )["pixel_values"].to("cpu")
            feats = to_features(model.get_image_features(pixel_values=pixel_values))
            feats = feats / feats.norm(dim=-1, keepdim=True)
            all_emb[np.asarray(idxs)] = feats.float().numpy()
            done += len(idxs)
            if done % (args.batch * 20) < args.batch:
                dt = time.time() - t_start
                print(
                    f"{done}/{len(crops)} embedded, {dt:.1f}s, "
                    f"{done / dt:.1f} img/s, {dt / done * 1000:.0f} ms/img",
                    flush=True,
                )

    dt = time.time() - t_start
    ms_per_img = dt / len(crops) * 1000
    print(f"DONE: {len(crops)} crops in {dt:.1f}s ({ms_per_img:.1f} ms/img)", flush=True)

    emb_path = args.out / f"clip_embeddings_{args.tag}.npy"
    meta_path = args.out / f"clip_meta_{args.tag}.jsonl"
    np.save(emb_path, all_emb)
    with meta_path.open("w", encoding="utf-8") as f:
        for cr in crops:
            f.write(json.dumps(cr, ensure_ascii=False) + "\n")

    stats = {
        "model": MODEL_ID,
        "device": "cpu",
        "torch": torch.__version__,
        "n_crops": len(crops),
        "batch": args.batch,
        "workers": args.workers,
        "seconds": round(dt, 1),
        "ms_per_image": round(ms_per_img, 1),
        "emb_dim": int(all_emb.shape[1]),
        "emb_file": emb_path.name,
        "meta_file": meta_path.name,
        "normalized": True,
    }
    (args.out / f"embed_stats_{args.tag}.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(stats, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
