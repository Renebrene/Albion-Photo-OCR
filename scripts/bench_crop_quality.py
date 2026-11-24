#!/usr/bin/env python
"""
Фильтр качества кадра: учится ли EfficientNet-B0 отличать «щит, который стоит
читать» от «детектор поймал не то».

Метки берутся из базы, руками ничего не размечается:

* **empty** — QWEN прочитал кроп и вернул пустой ответ (дефис, номер дома,
  элемент конструкции, ложное срабатывание детектора);
* **good** — QWEN вернул осмысленный ответ (описание/бренд/клиент).

Сюжет повторяется на разных кадрах, поэтому деление идёт по фото:
train / val / test — разные фото одного и того же адреса попадают в разные
наборы (примерный ключ — имя адреса, короткого кода кадра не хватает).

Замер модели: ImageNet-признаки EfficientNet-B0 двух способов —

1. **zero-shot**: mean/центроид классов в пространстве признаков без обучения;
2. **линейный слой** (logistic regression на тех же признаках), обученный на
   train.

Главная метрика — **точность на test в рабочей точке**: в какой доле «мусорных»
кропов фильтр откажется читать, при том что не более 1 % полезных кропов
ошибочно отсеется. Это ровно вопрос «сэкономит ли фильтр QWEN без потерь».

    .venv/bin/python scripts/bench_crop_quality.py --dry-run
    .venv/bin/python scripts/bench_crop_quality.py --limit 3000
    .venv/bin/python scripts/bench_crop_quality.py --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
CACHE_ROOT = PROJECT / "data/experiments/crop_quality"
NAME_RE = re.compile(r"^(?P<key>.+?)\s*\((?P<shot>\d+)\)\s*(?:\.[A-Za-z]+)?$")
KEY_PARTS = re.compile(r"[0-9a-zA-Zа-яА-ЯёЁ]+")
FALSE_POSITIVE_RATE = 0.01


def frame_key(filename: str) -> str | None:
    """Адресный ключ кадра без номера снимка: «Нагибина19а» из имени файла."""

    match = NAME_RE.match(" ".join(str(filename or "").split()))

    if not match:
        return None

    parts = "".join(KEY_PARTS.findall(match.group("key"))).casefold()

    return parts or None


def load_rows(limit: int) -> list[dict]:
    """Кропы с меткой из ответа QWEN (кроме архивных регионов)."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.region_id, r.photo_id, r.crop_path, p.filename,
                       r.crop_width, r.crop_height,
                       coalesce(r.qwen_fields ->> 'description', ''),
                       coalesce(r.qwen_fields ->> 'brand', ''),
                       coalesce(r.qwen_fields ->> 'client', '')
                FROM public.photo_regions AS r
                JOIN public.photos AS p ON p.photo_id = r.photo_id
                WHERE r.qwen_status = 'DONE'
                  AND r.kind = 'billboard'
                  AND r.crop_path IS NOT NULL
                ORDER BY r.region_id
                """
            )
            raw = cur.fetchall()

    rows: list[dict] = []
    seen: set[str] = set()

    for region_id, photo_id, crop_path, filename, width, height, desc, brand, client in raw:
        path = PROJECT / crop_path

        if not path.is_file():
            continue

        key = f"{photo_id}:{crop_path}"

        if key in seen:
            continue

        seen.add(key)
        good = bool(desc.strip() or brand.strip() or client.strip())

        rows.append(
            {
                "region_id": int(region_id),
                "photo_id": str(photo_id),
                "path": path,
                "address_key": frame_key(filename) or str(photo_id),
                "good": good,
                "width": int(width or 0),
                "height": int(height or 0),
            }
        )

        if limit and len(rows) >= limit:
            break

    return rows


def split_rows(rows: list[dict], seed: int = 0) -> dict[str, list[dict]]:
    """
    Деление по адресному ключу: 60/20/20 по адресам, чтобы ни один сюжет не
    был одновременно в train и test.
    """

    keys = sorted({row["address_key"] for row in rows})
    rng = np.random.default_rng(seed)
    rng.shuffle(keys)
    cut1 = int(len(keys) * 0.6)
    cut2 = int(len(keys) * 0.8)
    train_keys = set(keys[:cut1])
    val_keys = set(keys[cut1:cut2])
    splits = {"train": [], "val": [], "test": []}

    for row in rows:
        if row["address_key"] in train_keys:
            splits["train"].append(row)
        elif row["address_key"] in val_keys:
            splits["val"].append(row)
        else:
            splits["test"].append(row)

    return splits


def _cache_path(version: str, rows: list[dict]) -> Path:
    digest = hashlib.sha1(
        "|".join(f"{row['region_id']}" for row in rows).encode("utf-8")
    ).hexdigest()[:12]

    return CACHE_ROOT / f"b0_{version}_{digest}.npz"


def embed_crops(rows: list[dict], device: str = "cuda") -> np.ndarray:
    """ImageNet-признаки EfficientNet-B0 (1280-dim), с кэшем по набору строк."""

    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    cache = _cache_path("v1", rows)
    stored: dict[int, np.ndarray] = {}

    if cache.is_file():
        try:
            with np.load(cache, allow_pickle=False) as data:
                stored = {int(key): data[key] for key in data.files}
        except Exception:  # noqa: BLE001 — битый кэш пересчитаем
            stored = {}

    missing = [row for row in rows if row["region_id"] not in stored]

    if missing:
        import torch
        import torchvision
        from PIL import Image

        target = torch.device(device if torch.cuda.is_available() else "cpu")
        weights = torchvision.models.EfficientNet_B0_Weights.IMAGENET1K_V1
        model = torchvision.models.efficientnet_b0(weights=weights)
        model.classifier = torch.nn.Identity()
        model.eval().to(target)
        transform = weights.transforms()

        batch_size = 32

        for start in range(0, len(missing), batch_size):
            chunk = missing[start:start + batch_size]
            tensors = []
            keep = []

            for row in chunk:
                try:
                    with Image.open(row["path"]) as image:
                        tensors.append(transform(image.convert("RGB")))
                    keep.append(row)
                except Exception:  # noqa: BLE001 — битый кроп пропускаем
                    continue

            if not tensors:
                continue

            with torch.inference_mode():
                features = model(torch.stack(tensors).to(target))

            vectors = features.float().cpu().numpy()
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            vectors = np.round(vectors / norms, 4)

            for row, vector in zip(keep, vectors):
                stored[row["region_id"]] = vector

        try:
            np.savez_compressed(cache, **{str(key): value for key, value in stored.items()})
        except Exception:  # noqa: BLE001 — кэш не обязателен
            pass

    usable = [row for row in rows if row["region_id"] in stored]
    matrix = np.stack([stored[row["region_id"]] for row in usable])

    return usable, matrix


def _fit_logistic(x_train, y_train, epochs: int = 200, lr: float = 0.05):
    """
    Логистическая регрессия на numpy: одна модель, без зависимостей и
    без утечки через sklearn. Веса L2-регуляризованы — признаков 1280.
    """

    weights = np.zeros(x_train.shape[1], dtype=np.float64)
    bias = 0.0
    reg = 1e-3

    for _ in range(epochs):
        scores = x_train @ weights + bias
        probabilities = 1 / (1 + np.exp(-scores))
        error = probabilities - y_train
        weights -= lr * (x_train.T @ error / len(x_train) + reg * weights)
        bias -= lr * float(error.mean())

    return weights, bias


def _report_split(name: str, rows: list[dict], probabilities: np.ndarray, threshold: float) -> dict:
    labels = np.array([1 if row["good"] else 0 for row in rows])
    rejected = probabilities < threshold
    empty = labels == 0

    rejected_empty = int((rejected & empty).sum())
    rejected_good = int((rejected & ~empty).sum())
    total_empty = int(empty.sum())

    return {
        "name": name,
        "crops": len(rows),
        "good": int(labels.sum()),
        "empty": total_empty,
        "rejected_empty": rejected_empty,
        "rejected_good": rejected_good,
        "catch_rate": round(rejected_empty / total_empty, 3) if total_empty else None,
        "false_reject_rate": round(
            rejected_good / max(1, len(rows) - total_empty), 3
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Проверить, учится ли EfficientNet-B0 отличать пустые кропы"
    )
    parser.add_argument("--limit", type=int, default=0, help="не больше N кропов")
    parser.add_argument("--dry-run", action="store_true", help="только распределение")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    rows = load_rows(args.limit)

    if not rows:
        print("Кропов с ответом QWEN не найдено.")
        return 0

    splits = split_rows(rows)
    print(
        "кропов: %d (пустых %d); адресов: %d"
        % (len(rows), sum(1 for row in rows if not row["good"]), len({row["address_key"] for row in rows}))
    )
    for name, items in splits.items():
        empty = sum(1 for row in items if not row["good"])
        print(f"  {name}: {len(items)} кропов, пустых {empty}")

    if args.dry_run:
        print(f"dry-run: модель не загружалась ({time.perf_counter() - started:.2f} с)")
        return 0

    usable, matrix = embed_crops(rows, args.device)
    good_flag = {row["region_id"]: row["good"] for row in usable}
    hard = {row["region_id"]: (row["width"] < 200 or row["height"] < 120) for row in usable}

    by_split: dict[str, list[dict]] = {"train": [], "val": [], "test": []}
    split_of = {
        row["region_id"]: name for name, items in splits.items() for row in items
    }

    positions = {row["region_id"]: index for index, row in enumerate(usable)}

    for row in usable:
        by_split[split_of[row["region_id"]]].append(row)

    def take(name: str):
        ids = [row["region_id"] for row in by_split[name]]
        x = matrix[[positions[rid] for rid in ids]]
        y = np.array([1.0 if good_flag[rid] else 0.0 for rid in ids])

        return ids, x, y

    train_ids, x_train, y_train = take("train")
    val_ids, x_val, y_val = take("val")
    test_ids, x_test, y_test = take("test")

    results: dict = {
        "crops": len(usable),
        "good": int(y_train.sum() + y_val.sum() + y_test.sum()),
        "empty": int(len(usable) - (y_train.sum() + y_val.sum() + y_test.sum())),
        "zero_shot": {},
        "learned": {},
    }

    # 1) zero-shot: центроид «полезных» и «мусорных» кропов, косинус к ним.
    good_centroid = x_train[y_train == 1].mean(axis=0)
    empty_centroid = x_train[y_train == 0].mean(axis=0)
    good_centroid /= max(1e-9, np.linalg.norm(good_centroid))
    empty_centroid /= max(1e-9, np.linalg.norm(empty_centroid))

    def _threshold_from_val(probabilities: np.ndarray, labels: np.ndarray) -> float:
        """Порог при ошибочном отсеве полезных ≤ 1 % (по val)."""

        good_scores = np.sort(probabilities[labels == 1])

        if not len(good_scores):
            return 0.0

        cut = int(len(good_scores) * FALSE_POSITIVE_RATE)

        # Отсекаем самую низкую «хорошую» долю: порог — её верхняя граница.
        return float(good_scores[max(0, cut - 1)])

    zero_val = x_val @ good_centroid - x_val @ empty_centroid
    zero_threshold = _threshold_from_val(zero_val, y_val)

    for name, ids, x, labels in (
        ("val", val_ids, x_val, y_val),
        ("test", test_ids, x_test, y_test),
    ):
        margin = x @ good_centroid - x @ empty_centroid
        rows_split = [row for row in usable if row["region_id"] in set(ids)]
        # Больше близость к «полезному» центроиду — выше вероятность.
        results["zero_shot"][name] = _report_split(name, rows_split, margin, zero_threshold)

    results["zero_shot"]["threshold"] = round(zero_threshold, 4)

    # 2) линейный слой: логистическая регрессия на train, порог — по val.
    weights, bias = _fit_logistic(x_train, y_train)
    val_probabilities = 1 / (1 + np.exp(-(x_val @ weights + bias)))
    threshold = _threshold_from_val(val_probabilities, y_val)

    for name, ids, x in (("train", train_ids, x_train), ("val", val_ids, x_val), ("test", test_ids, x_test)):
        probabilities = 1 / (1 + np.exp(-(x @ weights + bias)))
        rows_split = [row for row in usable if row["region_id"] in set(ids)]
        results["learned"][name] = _report_split(name, rows_split, probabilities, threshold)
        results["learned"][name]["hard_crop_share"] = round(
            float(np.mean([hard[row["region_id"]] for row in rows_split])), 3
        )

    results["learned"]["threshold"] = round(threshold, 4)
    results["splits"] = {name: len(items) for name, items in splits.items()}
    results["seconds"] = round(time.perf_counter() - started, 1)

    for name, report in results["zero_shot"].items():
        if name == "threshold":
            continue
        print(
            f"zero-shot/{name}: отсеяно пустых {report['rejected_empty']} "
            f"({round((report['catch_rate'] or 0) * 100)}%), "
            f"ошибочно отсеяно полезных {report['rejected_good']} "
            f"({round(report['false_reject_rate'] * 100, 2)}%)"
        )

    for name, report in results["learned"].items():
        if name == "threshold":
            continue
        print(
            f"learned/{name}: кропов {report['crops']}, пустых {report['empty']}, "
            f"отсеяно пустых {report['rejected_empty']} "
            f"({round((report['catch_rate'] or 0) * 100)}%), "
            f"ошибочно отсеяно полезных {report['rejected_good']} "
            f"({round(report['false_reject_rate'] * 100, 2)}%)"
        )
    print(f"порог: {results['learned']['threshold']}")

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
