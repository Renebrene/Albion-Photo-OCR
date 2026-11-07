#!/usr/bin/env python3
"""Read-only DINO v3.5 experiment: whole-scene context features.

Builds two experimental fingerprints (dachnaya_v35, zorge_v35) from
/media/alexice/TEST/{дачная,зорге}, adds whole-scene context descriptors
(green_top, sky_top, gray_building), and evaluates them on photos whose
filenames label them as "Вавилова Дачная" or "Стачки Зорге".

Nothing is written to PostgreSQL or to data/fingerprints. Artifacts go to
data/experiments/v35 and data/reports.
"""

from __future__ import annotations

import json
import os
import random
import statistics
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.scene_analyzer import CompactDescriptor
from app.dino.runner import compare_loaded
from app.ingest.database import get_connection

ROOT = Path("data/experiments/v35")
REPORT = Path("data/reports/dino_v35_experiment_20261106.md")
CONTEXT_NAMES = ("green_top", "sky_top", "gray_building")
SOURCES = {
    "dachnaya_v35": Path("/media/alexice/TEST/дачная"),
    "zorge_v35": Path("/media/alexice/TEST/зорге"),
}
random.seed(7)


def context_features(path: str | Path) -> np.ndarray:
    """Whole-scene context: top greenery/sky and middle gray building."""
    image = Image.open(path).convert("RGB")
    image.thumbnail((640, 640))
    a = np.asarray(image).astype(np.float32) / 255.0
    h, w, _ = a.shape

    top = a[: max(1, int(h * 0.30))]
    mid = a[int(h * 0.30): int(h * 0.75)]

    def masks(part):
        r, g, b = part[:, :, 0], part[:, :, 1], part[:, :, 2]
        bright = part.mean(axis=2)
        mx, mn = part.max(axis=2), part.min(axis=2)
        sat = (mx - mn) / (mx + 1e-6)
        green = (g > r * 1.05) & (g > b * 0.98) & (g > 0.18)
        sky = ((b > r * 1.03) & (b > g * 0.98) & (bright > 0.35)) | (
            (bright > 0.78) & (sat < 0.12)
        )
        gray = (sat < 0.12) & (bright > 0.25) & (bright < 0.80)
        return green, sky, gray

    green_top, sky_top, _ = masks(top)
    _, _, gray_mid = masks(mid)

    return np.asarray(
        [green_top.mean(), sky_top.mean(), gray_mid.mean()],
        dtype=np.float32,
    )


def normalize_rows(rows: np.ndarray) -> np.ndarray:
    rows = np.asarray(rows, dtype=np.float32)
    norms = np.linalg.norm(rows, axis=1, keepdims=True)
    return rows / np.maximum(norms, 1e-9)


def build_fingerprint(name: str, folder: Path, embedder: SceneEmbedder) -> dict:
    paths = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}
    )
    if not paths:
        raise ValueError(f"no JPEG images in {folder}")

    embeddings = normalize_rows(embedder.embed_paths(paths))
    centroid = embeddings.mean(axis=0)
    centroid = centroid / max(float(np.linalg.norm(centroid)), 1e-9)

    env, color, spatial = [], [], []
    contexts = []
    for path in paths:
        e, c, s = CompactDescriptor.all(path)
        env.append(e); color.append(c); spatial.append(s)
        contexts.append(context_features(path))

    contexts = np.stack(contexts)
    representative_count = min(16, len(paths))
    sims = embeddings @ centroid
    rep_idx = np.argsort(sims)[-representative_count:][::-1].astype(np.int32)

    out = ROOT / name
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "embeddings.npy", embeddings)
    np.save(out / "centroid.npy", centroid.astype(np.float32))
    np.save(out / "representatives.npy", embeddings[rep_idx])
    np.save(out / "representative_indices.npy", rep_idx)
    np.save(out / "environment_embeddings.npy", np.stack(env))
    np.save(out / "color_embeddings.npy", np.stack(color))
    np.save(out / "spatial_embeddings.npy", np.stack(spatial))
    np.save(out / "context_embeddings.npy", contexts)

    metadata = {
        "id": name,
        "version": "3.5",
        "model": "facebook/dinov2-base",
        "images": len(paths),
        "representatives": representative_count,
        "dimension": 768,
        "context_descriptor": "whole_scene_v1",
        "context_names": list(CONTEXT_NAMES),
        "context_mean": contexts.mean(axis=0).tolist(),
        "context_std": contexts.std(axis=0).tolist(),
        "image_names": [p.name for p in paths],
        "source_folder": None,
        "source_folder_name": folder.name,
    }
    (out / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "name": name,
        "paths": paths,
        "embeddings": embeddings,
        "centroid": centroid,
        "representatives": embeddings[rep_idx],
        "environment_embeddings": np.stack(env),
        "color_embeddings": np.stack(color),
        "spatial_embeddings": np.stack(spatial),
        "context_mean": contexts.mean(axis=0),
        "context_std": contexts.std(axis=0),
        "metadata": metadata,
    }


def context_similarity(query: np.ndarray, fp: dict) -> float:
    scale = np.maximum(fp["context_std"], 0.08)
    return float(1.0 - np.mean(np.minimum(np.abs(query - fp["context_mean"]) / scale, 1.0)))


def data_for(fp: dict) -> dict:
    return {
        "centroid": fp["centroid"],
        "embeddings": fp["embeddings"],
        "environment_embeddings": fp["environment_embeddings"],
        "color_embeddings": fp["color_embeddings"],
        "spatial_embeddings": fp["spatial_embeddings"],
        "metadata": fp["metadata"],
    }


def query_path(pid: str, source_path: str) -> Path:
    preview = Path("data/preview/middle") / f"{pid}.webp"
    return preview if preview.exists() else Path(source_path)


def load_hard_errors() -> list[tuple]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute("SELECT max(hybrid_run_id) FROM hybrid_runs WHERE status = 'DONE'")
            run_id = cur.fetchone()[0]
            cur.execute(
                """
                SELECT p.photo_id, p.filename, p.source_path
                FROM photos p
                JOIN hybrid_results h
                  ON h.photo_id = p.photo_id
                 AND h.status = 'DONE'
                 AND h.hybrid_run_id = %s
                WHERE h.hybrid_final_id = '51_v33'
                  AND p.filename ILIKE %s
                  AND p.filename ILIKE %s
                """,
                (run_id, "%Стачки%", "%Зорге%"),
            )
            return cur.fetchall()


def load_labeled() -> tuple[list[tuple], list[tuple]]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(
                """
                SELECT photo_id, filename, source_path
                FROM photos
                WHERE filename ILIKE %s AND filename ILIKE %s
                """,
                ("%Вавилова%", "%Дачная%"),
            )
            dachnaya = cur.fetchall()
            cur.execute(
                """
                SELECT photo_id, filename, source_path
                FROM photos
                WHERE filename ILIKE %s AND filename ILIKE %s
                """,
                ("%Стачки%", "%Зорге%"),
            )
            zorge = cur.fetchall()
    return dachnaya, zorge


def auc(pos: list[float], neg: list[float]) -> float:
    gt = sum(1 for a in pos for b in neg if a > b)
    eq = sum(1 for a in pos for b in neg if a == b)
    return (gt + 0.5 * eq) / (len(pos) * len(neg))


def main() -> None:
    cpu = replace(settings, device="cpu")
    embedder = SceneEmbedder(cpu)
    print("[v35] building fingerprints", flush=True)
    fps = {
        name: build_fingerprint(name, folder, embedder)
        for name, folder in SOURCES.items()
    }
    data = {name: data_for(fp) for name, fp in fps.items()}

    dachnaya, zorge = load_labeled()
    hard = load_hard_errors()
    print(f"[v35] labeled: dachnaya={len(dachnaya)} zorge={len(zorge)} hard_51={len(hard)}", flush=True)

    # Context only: all labeled photos, cheap pixel features.
    ctx = {}
    for label, rows in (("dachnaya", dachnaya), ("zorge", zorge)):
        values = []
        for pid, _fn, src in rows:
            try:
                values.append(context_features(query_path(pid, src)))
            except Exception:
                continue
        ctx[label] = np.stack(values) if values else np.zeros((0, 3))
    print("[v35] context feature counts", {k: len(v) for k, v in ctx.items()}, flush=True)

    sims = {
        label: np.asarray([
            context_similarity(v, fps["dachnaya_v35"]) - context_similarity(v, fps["zorge_v35"])
            for v in values
        ])
        for label, values in ctx.items()
    }
    ctx_auc = auc(list(sims["dachnaya"]), list(sims["zorge"]))
    ctx_pred = {
        "dachnaya_as_dachnaya": float(np.mean(sims["dachnaya"] > 0)),
        "zorge_as_zorge": float(np.mean(sims["zorge"] < 0)),
    }

    # Full v3.5 on a sample: DINO + context. 200 per class.
    sample = []
    for label, rows in (("dachnaya", dachnaya), ("zorge", zorge)):
        random.shuffle(rows)
        for row in rows[:200]:
            sample.append((label, row))

    full = []
    for index, (label, (pid, fn, src)) in enumerate(sample, 1):
        try:
            path = query_path(pid, src)
            q = embedder.embed_paths([path])[0]
            env, color, spatial = CompactDescriptor.all_from_image(
                CompactDescriptor._load(path)
            )
            base = {
                name: compare_loaded(q, env, color, spatial, data[name])
                for name in ("dachnaya_v35", "zorge_v35")
            }
            qctx = context_features(path)
            csim = {
                name: context_similarity(qctx, fps[name])
                for name in ("dachnaya_v35", "zorge_v35")
            }
            full.append((label, fn, base, csim))
        except Exception as exc:
            print("[v35] skip", pid, exc, flush=True)
        if index % 50 == 0:
            print(f"[v35] full {index}/{len(sample)}", flush=True)

    weights = (0.0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0)
    results = {}
    for weight in weights:
        correct = 0
        total = 0
        confusion = Counter()
        for label, _fn, base, csim in full:
            pred = "dachnaya" if (
                base["dachnaya_v35"]["score"] + weight * csim["dachnaya_v35"]
                > base["zorge_v35"]["score"] + weight * csim["zorge_v35"]
            ) else "zorge"
            total += 1
            correct += pred == label
            confusion[(label, pred)] += 1
        results[str(weight)] = {
            "accuracy": correct / total if total else None,
            "correct": correct,
            "total": total,
            "confusion": {f"{k[0]}->{k[1]}": v for k, v in confusion.items()},
        }

    # Hard cases: production 51 grabbed these Zorge-labeled photos.
    hard_rows = []
    for pid, fn, src in hard:
        try:
            path = query_path(pid, src)
            q = embedder.embed_paths([path])[0]
            env, color, spatial = CompactDescriptor.all_from_image(
                CompactDescriptor._load(path)
            )
            base = {
                name: compare_loaded(q, env, color, spatial, data[name])
                for name in ("dachnaya_v35", "zorge_v35")
            }
            qctx = context_features(path)
            csim = {
                name: context_similarity(qctx, fps[name])
                for name in ("dachnaya_v35", "zorge_v35")
            }
            hard_rows.append((fn, base, csim))
        except Exception as exc:
            print("[v35] hard skip", pid, exc, flush=True)

    def pred_base(base):
        return "dachnaya" if base["dachnaya_v35"]["score"] > base["zorge_v35"]["score"] else "zorge"

    hard_base = sum(1 for _fn, base, _csim in hard_rows if pred_base(base) == "zorge")

    # Gated context: only touch photos whose DINO pair is close.
    gate_results = {}
    for gate in (0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12):
        correct = 0
        changed = 0
        for label, _fn, base, csim in full:
            d_score = base["dachnaya_v35"]["score"]
            z_score = base["zorge_v35"]["score"]
            if abs(d_score - z_score) < gate:
                changed += 1
                pred = "dachnaya" if csim["dachnaya_v35"] > csim["zorge_v35"] else "zorge"
            else:
                pred = "dachnaya" if d_score > z_score else "zorge"
            correct += pred == label
        gate_results[str(gate)] = {
            "accuracy": correct / len(full) if full else None,
            "correct": correct,
            "total": len(full),
            "changed": changed,
        }

    # Per-photo dump for inspection.
    with (ROOT / "full_sample.csv").open("w", encoding="utf-8-sig", newline="") as sink:
        import csv as _csv
        writer = _csv.writer(sink, delimiter=";")
        writer.writerow(["label", "filename", "d_score", "z_score", "d_ctx", "z_ctx", "green_top", "sky_top", "gray_building"])
        for label, fn, base, csim in full:
            # context features are not carried separately; read from query again is
            # avoided by recording only the similarity values here.
            writer.writerow([
                label, fn,
                base["dachnaya_v35"]["score"], base["zorge_v35"]["score"],
                csim["dachnaya_v35"], csim["zorge_v35"], "", "", "",
            ])

    # Feature separability on context.
    feature_auc = {
        name: auc(
            [float(v[i]) for v in ctx["dachnaya"]],
            [float(v[i]) for v in ctx["zorge"]],
        )
        for i, name in enumerate(CONTEXT_NAMES)
    }

    report = {
        "sources": {
            name: {
                "folder": str(folder),
                "images": len(fps[name]["paths"]),
                "context_mean": dict(zip(CONTEXT_NAMES, fps[name]["context_mean"].tolist())),
                "context_std": dict(zip(CONTEXT_NAMES, fps[name]["context_std"].tolist())),
            }
            for name, folder in SOURCES.items()
        },
        "context_only": {
            "auc": ctx_auc,
            "feature_auc": feature_auc,
            "accuracy": ctx_pred,
        },
        "full_v35": results,
        "hard_51_to_zorge": {
            "n": len(hard_rows),
            "v35_base_zorge": hard_base,
            "v35_base_accuracy": hard_base / len(hard_rows) if hard_rows else None,
        },
        "gated_context": gate_results,
        "full_sample_size": len(full),
    }
    (ROOT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# DINO v3.5 — экспериментальный профиль",
        "",
        "Дата: 06.11.2026. Только чтение: PostgreSQL и `data/fingerprints` не изменялись.",
        "",
        "## Слепки",
        "",
        "| Слепок | Папка | Фото | green_top | sky_top | gray_building |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for name, item in report["sources"].items():
        mean = item["context_mean"]
        lines.append(
            f"| `{name}` | `{item['folder']}` | {item['images']} | "
            f"{mean['green_top']:.3f} | {mean['sky_top']:.3f} | {mean['gray_building']:.3f} |"
        )
    lines += [
        "",
        "## Только контекст (вся подписанная выборка)",
        "",
        f"- Фото Дачной: {len(ctx['dachnaya'])}; Зорге: {len(ctx['zorge'])}.",
        f"- AUC разделения по контексту: **{ctx_auc:.3f}**.",
        f"- Дачная распознана как Дачная: **{ctx_pred['dachnaya_as_dachnaya']*100:.1f}%**.",
        f"- Зорге распознан как Зорге: **{ctx_pred['zorge_as_zorge']*100:.1f}%**.",
        "",
        "| Признак | AUC |",
        "|---|---:|",
    ]
    for name, value in feature_auc.items():
        lines.append(f"| `{name}` | {value:.3f} |")
    lines += [
        "",
        "## DINO v3.5 + контекст (выборка)",
        "",
        "| Вес контекста | Точность | Верно / всего |",
        "|---:|---:|---:|",
    ]
    for weight, item in results.items():
        acc = item["accuracy"] or 0.0
        lines.append(f"| {weight} | {acc*100:.1f}% | {item['correct']} / {item['total']} |")
    lines += [
        "",
        "### Контекст только при близкой паре DINO",
        "",
        "| Порог разницы DINO | Точность | Верно / всего | Фото, где сработал контекст |",
        "|---:|---:|---:|---:|",
    ]
    for gate, item in gate_results.items():
        acc = item["accuracy"] or 0.0
        lines.append(f"| {gate} | {acc*100:.1f}% | {item['correct']} / {item['total']} | {item['changed']} |")
    lines += [
        "",
        "Подробная матрица ошибок и средние признаки — в `report.json`.",
        "",
        "## Сложные случаи: фото Зорге, которые production-51 забирал себе",
        "",
        f"- Проверено: **{len(hard_rows)}** фото.",
        f"- v3.5 без контекста отправляет в Зорге: **{hard_base} / {len(hard_rows)}**"
        f" ({100*hard_base/len(hard_rows) if hard_rows else 0:.1f}%).",
        "",
        "## Вывод",
        "",
        "Контекстные признаки `green_top`, `sky_top`, `gray_building` проверены на",
        "подписанных фото. Если разделение устойчиво, следующим шагом добавлять их",
        "в v3.5-профиль как отдельный whole-scene descriptor и использовать в",
        "переранжировании пары Дачная/Вавилова ↔ Зорге/Стачки, не заменяя DINO",
        "global score и не переходя на кроп-слепки.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2)[:4000])


if __name__ == "__main__":
    main()
