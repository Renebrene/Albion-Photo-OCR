"""
Сцены в папках со снимками: отпечатки кадров и разбиение на условия съёмки.

    python scripts/scene_clusters.py --root data/input
    python scripts/scene_clusters.py --root data/input --json data/output/scenes.json

Что делает по каждой папке (адресу):

1. Считает признаки кадров — параллельно, в несколько процессов:
   декодирование и есть основная стоимость.
2. Схлопывает почти одинаковые кадры: расстояние Хэмминга pHash меньше порога —
   это одна серия («щелчок за щелчком») или дубль, в выборке он не нужен.
3. Кластеризует по одному представителю каждой серии по СОСТАВНОМУ признаку
   (pHash + цветовая подпись + яркость) и подбирает число сцен автоматически.
4. Печатает для каждой папки хвост кривой «k: силуэт» и выбранное k, чтобы
   выбор был виден, а не «на глаз».

Скрипт ничего не меняет и не собирает: он только показывает, из скольких сцен
состоит папка. Выбор кадров и сборка слепков — следующий шаг.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# Кадры ближе этого расстояния Хэмминга (из 64 бит) считаются одной серией.
DEFAULT_DEDUP = 6

# Автоподбор числа сцен идёт по этому диапазону.
DEFAULT_K_MIN = 2
DEFAULT_K_MAX = 40

# Выбор k: берём наибольшее k, чей силуэт не хуже этой доли от лучшего.
# Силуэт почти всегда максимален при k=2 (две «кучки» — светлое/тёмное,
# близкое/дальнее), но такой ответ бесполезен: владельцу нужны 20–25 разных
# сцен-кадров. Допуск 0.9 означает: разбиение не хуже лучшего по силуэту
# более чем на 10%, но сцен в нём заметно больше.
K_SCORE_TOLERANCE = 0.9

# Масштаб блоков составного признака.
#
# Каждый бит хранится как ±1, поэтому вклад блока из N бит в евклидово
# расстояние — порядка 2*sqrt(N): pHash (64 бита) даёт до ~16, цветовая
# подпись (42 бита) — до ~13. Блоки почти сбалансированы без множителей
# (64/42 ≈ 1.5), поэтому оба идут «как есть», побитово.
#
# Яркость — единственная скалярная ось: при равном весе она вносила бы ~2,
# то есть в 6–8 раз меньше блоков и утонула бы в них. Поэтому умножаем её на
# 6: тогда размах день/ночь (Δ≈0.5) весит ~3 — как блок из 2–3 бит, а полный
# размах 0…1 даёт 6, то есть «как несколько бит». Так яркость заметна, но не
# подавляет 106 битовых осей. Проверял множители 3…20 — итоговое число сцен
# менялось не больше чем на одну, так что точное значение не критично.
BRIGHTNESS_WEIGHT = 6.0


def hash_one(path: str) -> dict | None:
    """
    Признаки одного кадра; None, если файл не читается.

    Кроме отпечатка pHash («как выглядит кадр») считаются цветовая подпись и
    яркость: именно они отличают условия съёмки — день от ночи, зиму от лета,
    солнце от пасмурности. Без них pHash почти всегда делит папку на две
    большие группы «похожая картинка / непохожая».
    """

    import imagehash
    from PIL import Image, ImageStat

    try:
        with Image.open(path) as image:
            if getattr(image, "n_frames", 1) > 1:
                image.seek(0)

            image = image.convert("RGB")

            phash = imagehash.phash(image)
            dhash = imagehash.dhash(image)
            colorhash = imagehash.colorhash(image, binbits=3)
            brightness = float(ImageStat.Stat(image.convert("L")).mean[0]) / 255.0
    except Exception:  # noqa: BLE001 - битый кадр пропускаем, не роняем скан
        return None

    def pack(hash_value) -> int:
        bits = hash_value.hash.flatten()

        if len(bits) % 8:
            bits = np.append(bits, np.zeros(8 - len(bits) % 8, dtype=bool))

        return int.from_bytes(np.packbits(bits).tobytes(), "big")

    def bits_of(hash_value, size: int) -> list[int]:
        values = hash_value.hash.flatten().astype(np.float32)

        return ((values * 2.0) - 1.0).tolist()[:size]

    return {
        "path": path,
        "phash": pack(phash),
        "dhash": pack(dhash),
        "brightness": round(brightness, 4),
        # Цветовая подпись (3 бита на канал), длина фиксирована — 42 бита.
        "color": bits_of(colorhash, 48),
    }


def hash_folder(photos: list[Path], workers: int) -> list[dict]:
    """Признаки всех кадров папки (порядок сохраняется)."""

    if not photos:
        return []

    if workers <= 1 or len(photos) == 1:
        rows = [hash_one(str(path)) for path in photos]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(hash_one, [str(path) for path in photos]))

    return [row for row in rows if row is not None]


def hamming_matrix(hashes: np.ndarray) -> np.ndarray:
    """Попарные расстояния Хэмминга (n×n, float32)."""

    xor = hashes[:, None] ^ hashes[None, :]

    return np.bitwise_count(xor).astype(np.float32)


def dedup_groups(dist: np.ndarray, threshold: int) -> list[list[int]]:
    """
    Серии почти одинаковых кадров: сначала жадное слияние по порогу.

    Возвращает список групп (индексы кадров); каждая группа — один «щелчок».
    """

    count = len(dist)
    groups: list[list[int]] = []
    used = np.zeros(count, dtype=bool)

    for index in range(count):
        if used[index]:
            continue

        members = [
            other
            for other in range(index, count)
            if not used[other] and dist[index, other] <= threshold
        ]

        for member in members:
            used[member] = True

        groups.append(members)

    return groups


def scene_features(rows: list[dict], keep: list[int]) -> np.ndarray:
    """
    Составной признак сцены для выбранных кадров (по одному на серию).

    Три блока в одном векторе:
      * pHash (64 бита) — композиция/ракурс;
      * цветовая подпись (42 бита) — температура и насыщенность, то есть
        погода и время суток;
      * яркость (одна ось, ×BRIGHTNESS_WEIGHT) — прямая подсказка о свете.

    Все биты приводятся к ±1: тогда евклидово расстояние по битовым блокам —
    это половина расстояния Хэмминга, и k-means работает «по похожести».
    """

    index = np.array(keep, dtype=int)

    packed = np.array([rows[i]["phash"] for i in index], dtype=np.uint64)
    phash_bits = np.unpackbits(
        packed.view(np.uint8).reshape(len(index), 8), axis=1
    ).astype(np.float32)
    phash_part = (phash_bits * 2.0) - 1.0

    color_bits = np.array([rows[i]["color"] for i in index], dtype=np.float32)
    color_part = (color_bits * 2.0) - 1.0

    brightness = np.array(
        [[rows[i]["brightness"] * BRIGHTNESS_WEIGHT] for i in index],
        dtype=np.float32,
    )

    return np.hstack([phash_part, color_part, brightness])


def choose_k(
    features: np.ndarray,
    k_min: int,
    k_max: int,
    forced: int | None = None,
) -> tuple[int, list[dict], list[int], float | None]:
    """
    Подобрать число сцен по силуэту на составном признаке.

    Кластеризация — k-means по векторам признаков; силуэт считается по
    евклидову расстоянию на тех же векторах (метрика, согласованная с k-means).

    Автовыбор: перебираем k от k_min до k_max, находим лучший силуэт и берём
    НАИБОЛЬШЕЕ k, чей силуэт не хуже K_SCORE_TOLERANCE от лучшего. Так
    разбиение не проигрывает по качеству, но сцен в нём больше.

    forced задаёт число сцен вручную (тогда перебор пропускается).

    Возвращает (k, оценки по всем k, метки, силуэт выбранного k).
    """

    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    count = len(features)

    if count < 3:
        return 1, [{"k": 1, "silhouette": None}], [0] * count, None

    top = min(k_max, count - 1)

    def fit(k: int) -> np.ndarray:
        return KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(features)

    if forced is not None:
        k = max(2, min(forced, top))
        labels = fit(k)

        if len(set(labels)) < 2:
            return 1, [{"k": 1, "silhouette": None}], [0] * count, None

        score = round(float(silhouette_score(features, labels)), 4)

        return k, [{"k": k, "silhouette": score}], [int(item) for item in labels], score

    scores: list[dict] = []
    labels_by_k: dict[int, np.ndarray] = {}

    for k in range(max(2, k_min), top + 1):
        labels = fit(k)

        if len(set(labels)) < 2:
            continue

        score = round(float(silhouette_score(features, labels)), 4)

        scores.append({"k": k, "silhouette": score})
        labels_by_k[k] = labels

    if not scores:
        return 1, [{"k": 1, "silhouette": None}], [0] * count, None

    best = max(item["silhouette"] for item in scores)
    floor = best * K_SCORE_TOLERANCE
    chosen = max(item["k"] for item in scores if item["silhouette"] >= floor)
    silhouette = next(item["silhouette"] for item in scores if item["k"] == chosen)

    return chosen, scores, [int(item) for item in labels_by_k[chosen]], float(silhouette)


def scenes_for_folder(
    folder: Path,
    photos: list[Path],
    workers: int,
    dedup: int,
    k_min: int,
    k_max: int,
    forced_k: int | None,
) -> dict:
    """Признаки, серии дублей и найденное число сцен для одной папки."""

    started = time.perf_counter()
    rows = hash_folder(photos, workers)

    if not rows:
        return {
            "address": folder.name,
            "photos": len(photos),
            "hashed": 0,
            "shots": 0,
            "scenes": 0,
            "scores": [],
            "seconds": round(time.perf_counter() - started, 2),
            "error": "нет читаемых кадров",
        }

    # Серии схлопываем по pHash: «щелчок за щелчком» — это одна и та же картинка.
    hashes = np.array([row["phash"] for row in rows], dtype=np.uint64)
    dist = hamming_matrix(hashes)

    groups = dedup_groups(dist, dedup)

    # Кластеризуем по одному представителю на серию, но уже по составному
    # признаку — иначе сцены не отделяются от «просто похожих картинок».
    keep = [group[0] for group in groups]
    features = scene_features(rows, keep)

    best_k, scores, labels, silhouette = choose_k(
        features, k_min, k_max, forced_k
    )

    return {
        "address": folder.name,
        "folder": str(folder),
        "photos": len(photos),
        "hashed": len(rows),
        "shots": len(groups),
        "scenes": best_k,
        "silhouette": silhouette,
        "scores": scores,
        "seconds": round(time.perf_counter() - started, 2),
        # Одна серия = один кадр выборки; метка говорит, к какой сцене он отнесён.
        "shots_files": [[rows[index]["path"] for index in group] for group in groups],
        "shots_scene": labels,
    }


def print_k_curve(result: dict, tail: int = 8) -> None:
    """Хвост кривой «k: силуэт» и выбранное k для одной папки."""

    scores = result.get("scores") or []

    if not scores:
        return

    tail_items = scores[-tail:]
    curve = "  ".join(
        f"{item['k']}:{item['silhouette']:.3f}" for item in tail_items
    )

    print(
        f"  {result['address']:>4}  k*={result['scenes']:>3}  "
        f"силуэт={result.get('silhouette') if result.get('silhouette') is not None else '—'}  "
        f"хвост k→силуэт: {curve}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="сцены в папках со снимками")
    parser.add_argument("--root", type=Path, default=Path("data/input"))
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, (os.cpu_count() or 1)),
        help="процессов на декодирование (по умолчанию все ядра)",
    )
    parser.add_argument("--dedup", type=int, default=DEFAULT_DEDUP)
    parser.add_argument("--k-min", type=int, default=DEFAULT_K_MIN)
    parser.add_argument("--k-max", type=int, default=DEFAULT_K_MAX)
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="принудительное число сцен (иначе автовыбор)",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="только эти папки (через запятую), например 78,79",
    )
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"нет папки: {args.root}", file=sys.stderr)
        return 2

    wanted = None

    if args.only:
        wanted = {item.strip() for item in args.only.split(",") if item.strip()}

    folders = [
        folder
        for folder in sorted(args.root.iterdir())
        if folder.is_dir() and (wanted is None or folder.name in wanted)
    ]

    if not folders:
        print(f"в {args.root} нет подпапок", file=sys.stderr)
        return 2

    results = []

    print(
        f"папок: {len(folders)}, процессов: {args.workers}, "
        f"порог серии: {args.dedup}, диапазон сцен: {args.k_min}–{args.k_max}, "
        f"k={'авто' if args.k is None else args.k}\n"
    )

    print(
        f"{'адрес':>8} {'фото':>5} {'кадров':>7} {'серий':>6} {'сцен':>5}  "
        f"{'силуэт':>7}  сек"
    )

    for folder in folders:
        photos = sorted(
            path
            for path in folder.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED
        )

        result = scenes_for_folder(
            folder,
            photos,
            args.workers,
            args.dedup,
            args.k_min,
            args.k_max,
            args.k,
        )

        results.append(result)

        best = result.get("silhouette")

        print(
            f"{result['address']:>8} {result['photos']:>5} {result['hashed']:>7} "
            f"{result.get('shots', 0):>6} {result['scenes']:>5}  "
            f"{f'{best:.3f}' if best is not None else '—':>7}  {result['seconds']:>4}"
        )

    print("\nподбор числа сцен (хвост кривой «k: силуэт», последние 8 k):")

    for result in results:
        print_k_curve(result)

    scenes = [result["scenes"] for result in results if result["scenes"]]
    shots = [result.get("shots", 0) for result in results]
    two = [result["address"] for result in results if result["scenes"] == 2]

    if scenes:
        print(
            f"\nсцен на папку: мин {min(scenes)}, среднее "
            f"{sum(scenes) / len(scenes):.1f}, макс {max(scenes)}; "
            f"кадров после схлопывания серий: {sum(shots)}"
        )

    if two:
        print(f"ровно 2 сцены: {', '.join(two)}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"записано: {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
