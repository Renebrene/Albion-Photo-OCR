#!/usr/bin/env python3
"""Пересборка CLIP-индекса кропов щитов (data/clip/).

    CUDA_VISIBLE_DEVICES="" .venv/bin/python scripts/clip_rebuild.py           # инкремент
    CUDA_VISIBLE_DEVICES="" .venv/bin/python scripts/clip_rebuild.py --full    # полный

Инкремент: эмбеддятся только регионы, отсутствующие в clip_meta.jsonl;
установленные на диске, но пропавшие из БД/файлов строки НЕ удаляются
(их чистит --full). Полный: всё заново, ~34 мс/изобр на CPU (~22 мин на
39 тыс. кропов). Записи атомарные: tmp → валидация → os.replace; сбой между
заменами оставляет пару рассогласованной — сервис это ловит и требует
пересборку, данные не теряются (старый .npy остаётся).

GPU не используется: скрипт требует CUDA_VISIBLE_DEVICES=""; GPU занят
QWEN-воркером (docs/clip_search.txt).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

assert os.environ.get("CUDA_VISIBLE_DEVICES") == "", (
    "set CUDA_VISIBLE_DEVICES='' before running: GPU is reserved for another job"
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import faiss  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from app.ingest.database import get_connection  # noqa: E402

CLIP_DIR = Path(os.getenv("SCENE_CLIP_ROOT", str(PROJECT_ROOT / "data" / "clip")))
EMB_FILE = CLIP_DIR / "clip_embeddings.npy"
META_FILE = CLIP_DIR / "clip_meta.jsonl"
INDEX_FILE = CLIP_DIR / "clip_index.faiss"
INFO_FILE = CLIP_DIR / "index_info.json"
MODEL_ID = "openai/clip-vit-base-patch32"


def fetch_crops() -> list[dict]:
    """Регионы с существующими файлами кропов (пути проект-относительные)."""

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
        {"region_id": int(r), "photo_id": str(p), "crop_path": str(c), "score": s}
        for r, p, c, s in rows
    ]
    existing = [cr for cr in crops if (PROJECT_ROOT / cr["crop_path"]).is_file()]
    print(
        f"DB rows: {len(crops)}; files on disk: {len(existing)}",
        flush=True,
    )
    return existing


def load_current() -> tuple[np.ndarray | None, dict[int, int]]:
    """Текущие эмбеддинги и маппинг region_id → строка меты."""

    if not EMB_FILE.is_file() or not META_FILE.is_file():
        return None, {}
    emb = np.load(EMB_FILE)
    known: dict[int, int] = {}
    with META_FILE.open(encoding="utf-8") as handle:
        for position, line in enumerate(handle):
            line = line.strip()
            if not line:
                continue
            known[int(json.loads(line)["region_id"])] = position
    if len(known) != emb.shape[0]:
        raise SystemExit(
            f"{EMB_FILE.name} ({emb.shape[0]}) и {META_FILE.name} "
            f"({len(known)}) рассогласованы — запустите --full"
        )
    return emb, known


def embed_batch(crops: list[dict], batch: int) -> np.ndarray:
    """CLIP-эмбеддинги списка кропов, L2-нормализованные (CPU)."""

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import torch
    from transformers import CLIPModel, CLIPProcessor

    model = CLIPModel.from_pretrained(MODEL_ID).to("cpu").eval()
    processor = CLIPProcessor.from_pretrained(MODEL_ID)
    vision_size = processor.image_processor.size.get(
        "shortest_edge", processor.image_processor.size.get("height", 224)
    )

    out = np.zeros((len(crops), model.config.projection_dim), dtype=np.float32)
    t_start = time.time()
    with torch.inference_mode():
        for start in range(0, len(crops), batch):
            chunk = crops[start : start + batch]
            images = []
            for item in chunk:
                with Image.open(PROJECT_ROOT / item["crop_path"]) as img:
                    img = img.convert("RGB")
                    if img.size != (vision_size, vision_size):
                        img = img.resize((vision_size, vision_size), Image.BICUBIC)
                    images.append(np.asarray(img, dtype=np.uint8))
            pixel_values = processor.image_processor(
                images=np.stack(images), return_tensors="pt"
            )["pixel_values"].to("cpu")
            feats = model.get_image_features(pixel_values=pixel_values)
            # transformers>=5 оборачивает проекцию в BaseModelOutputWithPooling.
            if hasattr(feats, "image_embeds"):
                feats = feats.image_embeds
            elif hasattr(feats, "pooler_output"):
                feats = feats.pooler_output
            feats = feats / feats.norm(dim=-1, keepdim=True)
            out[start : start + len(chunk)] = feats.float().numpy()
            done = start + len(chunk)
            dt = time.time() - t_start
            print(
                f"{done}/{len(crops)} embedded, {dt:.1f}s, "
                f"{done / dt:.1f} img/s, {dt / done * 1000:.0f} ms/img",
                flush=True,
            )
    return out


def publish(emb: np.ndarray, meta_rows: list[dict], stats: dict) -> None:
    """Атомарная запись: npy + мета + индекс + info (tmp → os.replace)."""

    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_emb = EMB_FILE.with_suffix(".npy.tmp")
    tmp_meta = META_FILE.with_suffix(".jsonl.tmp")
    tmp_index = INDEX_FILE.with_suffix(".faiss.tmp")
    tmp_info = INFO_FILE.with_suffix(".json.tmp")

    np.save(tmp_emb, emb)
    with tmp_meta.open("w", encoding="utf-8") as handle:
        for row in meta_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    faiss.write_index(index, str(tmp_index))

    info = {
        "model": MODEL_ID,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "vectors": int(emb.shape[0]),
        **stats,
    }
    tmp_info.write_text(
        json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    os.replace(tmp_emb, EMB_FILE)
    os.replace(tmp_meta, META_FILE)
    os.replace(tmp_index, INDEX_FILE)
    os.replace(tmp_info, INFO_FILE)
    print(f"published: {info['vectors']} vectors -> {CLIP_DIR}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="пересобрать всё заново")
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--json", action="store_true", help="итог одной JSON-строкой")
    args = parser.parse_args()

    crops = fetch_crops()
    if not crops:
        print("no crops found", file=sys.stderr)
        return 1

    current, known = load_current() if not args.full else (None, {})

    t_start = time.time()

    if args.full or current is None:
        targets = crops
        emb = embed_batch(targets, args.batch)
        meta_rows = targets
        mode = "full"
    else:
        disk_ids = {cr["region_id"] for cr in crops}
        targets = [cr for cr in crops if cr["region_id"] not in known]
        stale_on_disk = [rid for rid in known if rid not in disk_ids]
        print(
            f"known vectors: {len(known)}; new to embed: {len(targets)}; "
            f" disappeared from disk: {len(stale_on_disk)} (kept until --full)",
            flush=True,
        )
        if targets:
            emb_new = embed_batch(targets, args.batch)
            emb = np.concatenate([current, emb_new], axis=0)
            # Порядок строк меты = порядок строк эмбеддингов: старые строки
            # идут в исходном порядке файлов, новые — в порядке добавления.
            meta_rows = (
                sorted(
                    (cr for cr in crops if cr["region_id"] in known),
                    key=lambda cr: known[cr["region_id"]],
                )
                + targets
            )
        else:
            emb = current
            meta_rows = [cr for cr in crops if cr["region_id"] in known]
        mode = "increment"

    seconds = round(time.time() - t_start, 1)

    # Финальная валидация перед публикацией: индекс строится и по размеру
    # совпадает с метой — иначе ничего не заменяем.
    if emb.shape[0] != len(meta_rows):
        raise SystemExit(
            f"embeddings {emb.shape[0]} != meta rows {len(meta_rows)} — abort, nothing written"
        )

    publish(
        emb,
        meta_rows,
        {
            "mode": mode,
            "embedded_this_run": len(targets),
            "seconds": seconds,
        },
    )
    if args.json:
        print(json.dumps({"mode": mode, "vectors": int(emb.shape[0]), "embedded": len(targets)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
