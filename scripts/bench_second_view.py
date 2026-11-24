#!/usr/bin/env python
"""
Второй взгляд на проблемные адреса: даёт ли EfficientNet-B0 приращение к DINO.

Скрипт только читает. Он отвечает на один вопрос с цифрами: если добавить
независимый голос (ImageNet-признаки EfficientNet-B0) к выбору адреса на
ПАРАХ одного кадра, станет ли пар «один адрес — другой» меньше?

Как устроен замер
-----------------

* Пара — два фото одного кадра на разных адресах:
  «Нагибина 19 А (10).JPG» и «Нагибина 19 Б (10).JPG». Картинки почти
  одинаковые, адрес разный — худший случай для модели.
* Для фото с адресом X и фото с адресом Y считается сходство каждой модели —
  DINOv2 из пайплайна и EfficientNet-B0 (ImageNet-веса, без дообучения).
  Два способа: только лучший кроп кадра и смесь кропов всех фото кадра
  («мульти») — соседний щит в кадре не должен перетягивать сходство.
* Ответ — **отрыв**: среднее сходство фото адреса X с другими фото X минус
  среднее сходство с фото Y. Больше — модель лучше разделяет адреса.

Кэширование эмбеддингов — файл в `data/experiments/second_view/<модель>.npz`:
повторный запуск не пересчитывает уже посчитанное.

    .venv/bin/python scripts/bench_second_view.py --dry-run
    .venv/bin/python scripts/bench_second_view.py --address Нагибина
    .venv/bin/python scripts/bench_second_view.py --json

Первый запуск EfficientNet-B0 скачивает веса (~21 МБ) в кэш torchvision; без
сети скрипт честно скажет, что модель недоступна.
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

from app.api.config import PREVIEW_ROOT  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from app.preview import formats  # noqa: E402
from app.preview.generator import build_preview_paths  # noqa: E402

# «Нагибина 19 А (10).JPG» → («нагибина19а», 10) — ключ кадра и номер снимка.
_NAME_RE = re.compile(r"^(?P<key>.+?)\s*\((?P<shot>\d+)\)\s*(?:\.[A-Za-z]+)?$")
_KEY_PARTS = re.compile(r"[0-9a-zA-Zа-яА-ЯёЁ]+")

CACHE_ROOT = Path(__file__).resolve().parents[1] / "data/experiments/second_view"

# Пары проблемных адресов: один кадр на двух сторонах, которые путаются.
# Заполняется в main() из найденных пар — используется для разделения.
CONFUSION_PAIRS: list[tuple[str, str]] = []


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def frame_key(filename: str) -> tuple[str, int] | None:
    match = _NAME_RE.match(_clean(filename))

    if not match:
        return None

    letters = "".join(_KEY_PARTS.findall(match.group("key"))).casefold()

    return (letters, int(match.group("shot"))) if letters else None


def _preview(photo_id: str) -> Path | None:
    paths = build_preview_paths(preview_root=PREVIEW_ROOT, photo_id=photo_id)

    for candidate in formats.candidate_paths(paths.middle):
        if candidate.is_file():
            return candidate

    return None


def _crops(photo_id: str) -> list[Path]:
    from app.billboard.pipeline import crop_dir

    directory = crop_dir(photo_id)

    if not directory.is_dir():
        return []

    return sorted(path for path in directory.glob("crop_*.jpg") if path.is_file())


def load_address_of_photo() -> dict[str, dict]:
    """Адрес каждого фото — как в гриде: переопределение важнее вердикта."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.photo_id, p.filename, p.source_path,
                       COALESCE(
                           (SELECT ov.address_id
                              FROM public.photo_address_overrides AS ov
                             WHERE ov.photo_id = p.photo_id),
                           (SELECT af.address_id
                              FROM public.hybrid_results AS h
                              JOIN public.address_fingerprints AS af
                                ON af.fingerprint_id = h.hybrid_final_id
                               AND af.active
                             WHERE h.photo_id = p.photo_id
                               AND h.status = 'DONE'
                             ORDER BY h.hybrid_run_id DESC
                             LIMIT 1)
                       ) AS address_id,
                       COALESCE(d.simple_address, d.legal_address) AS address_name
                FROM public.photos AS p
                LEFT JOIN public.address_directory AS d
                       ON d.address_id = COALESCE(
                           (SELECT ov.address_id
                              FROM public.photo_address_overrides AS ov
                             WHERE ov.photo_id = p.photo_id),
                           (SELECT af.address_id
                              FROM public.hybrid_results AS h
                              JOIN public.address_fingerprints AS af
                                ON af.fingerprint_id = h.hybrid_final_id
                               AND af.active
                             WHERE h.photo_id = p.photo_id
                               AND h.status = 'DONE'
                             ORDER BY h.hybrid_run_id DESC
                             LIMIT 1)
                       )
                ORDER BY p.filename
                """
            )
            rows = cur.fetchall()

    result: dict[str, dict] = {}

    for photo_id, filename, source_path, address_id, address_name in rows:
        if address_id is None:
            continue

        key = frame_key(filename)

        if key is None:
            continue

        result[str(photo_id)] = {
            "photo_id": str(photo_id),
            "filename": filename,
            "source_path": source_path,
            "address_id": int(address_id),
            "address_name": _clean(address_name),
            "key": key,
            "preview": _preview(str(photo_id)),
        }

    return result


def build_pairs(photos: dict[str, dict], address_filter: str | None) -> list[tuple[str, str]]:
    """
    Пары (X, Y) — один кадр, два РАЗНЫХ адреса.

    Каждый кадр даёт все сочетания своих адресов: если у кадра три адреса, это
    три пары, а не одна.
    """

    frames: dict[tuple[str, int], list[str]] = defaultdict(list)

    for photo_id, item in photos.items():
        if address_filter and address_filter.casefold() not in item["address_name"].casefold():
            continue

        frames[item["key"]].append(photo_id)

    pairs: list[tuple[str, str]] = []

    for ids in frames.values():
        for left_index, left in enumerate(ids):
            for right in ids[left_index + 1:]:
                if photos[left]["address_id"] != photos[right]["address_id"]:
                    pairs.append((left, right))

    return pairs


def limit_pairs(pairs: list[tuple[str, str]], limit: int) -> list[tuple[str, str]]:
    if not limit or len(pairs) <= limit:
        return pairs

    step = len(pairs) / limit

    return [pairs[int(index * step)] for index in range(limit)]


def _unit(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    norms[norms == 0] = 1.0

    return values / norms


class DinoBackend:
    name = "dinov2"

    def __init__(self, device: str):
        import dataclasses

        from app.core.config import Settings
        from app.core.embedder import SceneEmbedder

        # Settings заморожены: устройство подменяется новым экземпляром, а не
        # присваиванием поля.
        self.embedder = SceneEmbedder(dataclasses.replace(Settings(), device=device))

    def embed_paths(self, paths: list[Path]) -> np.ndarray:
        from app.core.image import load_image

        if not paths:
            return np.empty((0, 0), dtype=np.float32)

        return _unit(self.embedder.embed_images([load_image(path) for path in paths]))


class EfficientNetBackend:
    """
    EfficientNet-B0 из torchvision, ImageNet-веса, без дообучения.

    Это ровно «второй взгляд», который можно получить сейчас, не заводя
    разметку. Дообучение — отдельное решение по результатам замера.
    """

    name = "efficientnet_b0"

    def __init__(self, device: str):
        import torch
        import torchvision

        self.torch = torch
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        weights = torchvision.models.EfficientNet_B0_Weights.IMAGENET1K_V1
        self.model = torchvision.models.efficientnet_b0(weights=weights)
        # Классификатор не нужен: берём пул признаков (1280-dim).
        self.model.classifier = torch.nn.Identity()
        self.model.eval().to(self.device)
        self.transform = weights.transforms()

    def embed_paths(self, paths: list[Path]) -> np.ndarray:
        from PIL import Image

        torch = self.torch
        vectors = []
        batch = 16

        for start in range(0, len(paths), batch):
            chunk = paths[start:start + batch]
            images = []
            for path in chunk:
                try:
                    with Image.open(path) as image:
                        images.append(self.transform(image.convert("RGB")))
                except Exception:  # noqa: BLE001 — битый файл пропускаем
                    continue

            if not images:
                continue

            with torch.inference_mode():
                features = self.model(torch.stack(images).to(self.device))

            vectors.append(features.float().cpu().numpy())

        if not vectors:
            return np.empty((0, 1280), dtype=np.float32)

        return _unit(np.concatenate(vectors, axis=0))


def _cache_path(backend_name: str, photo_ids: list[str]) -> Path:
    digest = hashlib.sha1("|".join(sorted(photo_ids)).encode("utf-8")).hexdigest()[:12]
    return CACHE_ROOT / f"{backend_name}_{digest}.npz"


def embeddings_for(backend, photos: dict[str, dict], photo_ids: list[str]) -> dict[str, dict]:
    """
    Векторы фото: «full» — лучший кроп кадра (или сам кадр, если кропа нет) и
    «all» — все кропы фото. Матрицы кладутся в кэш npz: повторный запуск не
    пересчитывает уже посчитанное.
    """

    cache = _cache_path(backend.name, photo_ids)
    stored: dict[str, np.ndarray] = {}

    if cache.is_file():
        try:
            with np.load(cache, allow_pickle=False) as data:
                stored = {key: data[key] for key in data.files}
        except Exception:  # noqa: BLE001 — битый кэш просто пересчитаем
            stored = {}

    missing = [photo_id for photo_id in photo_ids if photo_id not in stored]

    if missing:
        CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        owners: list[str] = []

        for photo_id in missing:
            item = photos[photo_id]
            crops = _crops(photo_id)
            sources = crops or ([item["preview"]] if item["preview"] else [])

            for source in sources:
                paths.append(source)
                owners.append(photo_id)

        vectors = backend.embed_paths(paths) if paths else np.empty((0, 0), dtype=np.float32)
        grouped: dict[str, list[np.ndarray]] = defaultdict(list)

        for photo_id, vector in zip(owners, vectors):
            grouped[photo_id].append(vector)

        for photo_id, values in grouped.items():
            stored[photo_id] = np.round(np.stack(values), 4)

        try:
            np.savez_compressed(cache, **stored)
        except Exception:  # noqa: BLE001 — кэш не обязателен
            pass

    result: dict[str, dict] = {}

    for photo_id in photo_ids:
        matrix = stored.get(photo_id)

        if matrix is None or len(matrix) == 0:
            continue

        result[photo_id] = {"full": matrix[0], "all": matrix}

    return result


def pair_scores(pairs, embeddings, photos) -> list[dict]:
    """
    Для каждой пары: сходство X–Y, а также сходство X с другими фото своего
    адреса и Y со своими (без взаимных) — по ним считается отрыв.
    """

    by_address: dict[int, list[str]] = defaultdict(list)

    for photo_id, item in photos.items():
        if photo_id in embeddings:
            by_address[item["address_id"]].append(photo_id)

    rows: list[dict] = []

    for left, right in pairs:
        if left not in embeddings or right not in embeddings:
            continue

        a, b = embeddings[left], embeddings[right]
        left_address = photos[left]["address_id"]
        right_address = photos[right]["address_id"]

        left_own = [
            float(a["full"] @ embeddings[other]["full"])
            for other in by_address[left_address]
            if other not in (left, right)
        ]
        right_own = [
            float(b["full"] @ embeddings[other]["full"])
            for other in by_address[right_address]
            if other not in (left, right)
        ]

        rows.append(
            {
                "same": float(a["full"] @ b["full"]),
                "multi_same": float(a["all"].mean(axis=0) @ b["all"].mean(axis=0)),
                "left_own": left_own,
                "right_own": right_own,
            }
        )

    return rows


def _summary(values: list[float]) -> dict:
    if not values:
        return {"mean": None, "p10": None, "min": None}

    array = np.asarray(values, dtype=np.float64)

    return {
        "mean": round(float(array.mean()), 4),
        "p10": round(float(np.percentile(array, 10)), 4),
        "min": round(float(array.min()), 4),
    }


def address_separation(embeddings, photos, involved) -> dict:
    """
    Главная метрика для ответа «помогает или нет».

    Строятся образы адресов (среднее по их фото, по всем кропам). Затем
    сравниваются два набора пар адресов: пары, которые путаются на снимках
    (один кадр, два адреса), и случайные пары (фон). Разделение — разность
    средних: насколько путающиеся пары ближе фоновых. Больше — модель лучше
    отделяет именно проблемные адреса.
    """

    by_address: dict[int, list[str]] = defaultdict(list)

    for photo_id in involved:
        if photo_id in embeddings:
            by_address[photos[photo_id]["address_id"]].append(photo_id)

    centroids = {}

    for address_id, ids in by_address.items():
        if not ids:
            continue
        matrix = _unit(
            np.stack([embeddings[photo_id]["all"].mean(axis=0) for photo_id in ids])
        )
        centroids[address_id] = _unit(matrix.mean(axis=0, keepdims=True))[0]

    keys = sorted(centroids)

    if len(keys) < 3:
        return {}

    matrix = np.stack([centroids[key] for key in keys])
    similarity = matrix @ matrix.T
    positions = {key: index for index, key in enumerate(keys)}

    confusing = [
        float(similarity[positions[photos[left]["address_id"]], positions[photos[right]["address_id"]]])
        for left, right in CONFUSION_PAIRS
        if photos[left]["address_id"] in positions
        and photos[right]["address_id"] in positions
    ]

    rng = np.random.default_rng(0)
    index_left, index_right = np.triu_indices(len(keys), 1)
    sample = rng.choice(
        len(index_left),
        size=min(3000, len(index_left)),
        replace=False,
    )
    background = [
        float(similarity[index_left[index], index_right[index]])
        for index in sample
    ]

    return {
        "addresses": len(keys),
        "confusing_sim": round(float(np.mean(confusing)), 4) if confusing else None,
        "background_sim": round(float(np.mean(background)), 4),
        "separation": round(
            float(np.mean(background)) - float(np.mean(confusing)), 4
        )
        if confusing
        else None,
    }


def summarise(rows: list[dict]) -> dict:
    """
    Отрыв: своё сходство (с другими фото адреса) минус сходство с чужим.

    Своё считается как среднее по соседям своего адреса обеих сторон пары;
    если своих фото всего два, берётся сходство самой пары (кадр на адресе X
    бывает один раз).
    """

    gaps: list[float] = []
    multi_gaps: list[float] = []

    for row in rows:
        own = row["left_own"] + row["right_own"]
        own_mean = float(np.mean(own)) if own else row["same"]
        own_multi = row["multi_same"] if not own else (
            float(np.mean(own)) + row["multi_same"]
        ) / 2

        gaps.append(own_mean - row["same"])
        multi_gaps.append(own_multi - row["multi_same"])

    # Доля пар, где «своё» сходство ВЫШЕ сходства с чужим адресом: это и есть
    # «модель различает адрес на этом кадре». Средний отрыв от нуля почти не
    # отходит у обеих моделей, поэтому решает знак по каждой паре.
    positive = sum(
        1 for index in range(len(rows)) if row_own_mean(rows, index) > rows[index]["same"]
    )

    return {
        "pairs": len(rows),
        "same": _summary([row["same"] for row in rows]),
        "multi_same": _summary([row["multi_same"] for row in rows]),
        "gap": _summary(gaps),
        "multi_gap": _summary(multi_gaps),
        "positive_share": round(positive / len(rows), 3) if rows else None,
    }


def row_own_mean(rows: list[dict], index: int) -> float:
    own = rows[index]["left_own"] + rows[index]["right_own"]

    return float(np.mean(own)) if own else rows[index]["same"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Сравнить второй взгляд (EfficientNet-B0) с DINO на парах одного кадра"
    )
    parser.add_argument("--address", default=None, help="кадрам с этим текстом в адресе")
    parser.add_argument("--limit-pairs", type=int, default=200)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--dry-run", action="store_true", help="показать пары, модели не загружать"
    )
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    photos = load_address_of_photo()
    pairs = limit_pairs(build_pairs(photos, args.address), args.limit_pairs)

    if not pairs:
        print("Пар не найдено: нужны фото «Имя А (N).JPG» и «Имя Б (N).JPG» с адресами.")
        return 0

    involved = sorted({photo_id for pair in pairs for photo_id in pair})
    CONFUSION_PAIRS[:] = list(pairs)
    names: dict[str, int] = defaultdict(int)

    for photo_id in involved:
        names[photos[photo_id]["address_name"]] += 1

    print(f"Пар: {len(pairs)}; фото в них: {len(involved)}")
    for name, count in sorted(names.items(), key=lambda item: -item[1])[:10]:
        print(f"  {name}: {count}")

    if args.dry_run:
        for left, right in pairs[:5]:
            print(
                f"  {photos[left]['address_name']} ({left}) vs "
                f"{photos[right]['address_name']} ({right})"
            )
        print(f"dry-run: модели не загружались ({time.perf_counter() - started:.2f} с)")
        return 0

    results: dict[str, dict] = {}

    for backend_class in (DinoBackend, EfficientNetBackend):
        try:
            backend = backend_class(args.device)
        except Exception as exc:  # noqa: BLE001 — модель может быть недоступна
            print(f"{backend_class.name}: недоступна ({type(exc).__name__}: {exc})")
            continue

        began = time.perf_counter()
        name = backend.name

        try:
            embeddings = embeddings_for(backend, photos, involved)
        finally:
            del backend  # освобождаем GPU перед следующей моделью

        rows = pair_scores(pairs, embeddings, photos)
        summary = summarise(rows)
        summary["separation"] = address_separation(embeddings, photos, involved)
        summary["seconds"] = round(time.perf_counter() - began, 1)
        summary["covered"] = len(embeddings)
        results[name] = summary

        print(
            f"{name}: покрыто фото {summary['covered']}/{len(involved)}, "
            f"пар {summary['pairs']}, "
            f"сходство между кадрами {summary['same']['mean']}, "
            f"отрыв {summary['gap']['mean']}, "
            f"своё выше чужого {round(summary['positive_share'] * 100)}%; "
            f"разделение проблемных адресов "
            f"{summary['separation'].get('separation')} "
            f"({summary['seconds']} с)"
        )

    if args.json:
        print(json.dumps({"pairs": len(pairs), "results": results}, ensure_ascii=False, indent=2))

    print(
        "\nОтрыв = своё сходство минус сходство с чужим адресом того же кадра. "
        "Больше — модель лучше отделяет адрес. Сравниваются строки на одних и "
        "тех же парах: лучшая модель по отрыву — кандидат во второй взгляд."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
