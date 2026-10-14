"""
Отбор кадров в слепок по сценам (условиям съёмки).

Задача: из папки с десятками похожих снимков одного адреса выбрать 20–30
непохожих кадров, чтобы слепок описывал объект, а не серию с одной точки.

Как это делается:

1. Каждый кадр описывается составным признаком: pHash (композиция), dHash
   (направление градиента), цветовая подпись (температура, насыщенность) и
   яркость (свет). Биты приводятся к ±1, яркость — отдельная ось с весом.
2. Почти одинаковые кадры («щелчок за щелчком») схлопываются в серии по
   расстоянию Хэмминга pHash.
3. Оставшиеся (по одному на серию) кластеризуются k-means по составному
   признаку; число сцен подбирается по силуэту, а затем приводится к рабочему
   диапазону 20–30: мало условий съёмки — кластеры дробятся мельче, много —
   схлопываются.
4. Из каждого кластера берётся один кадр — ближайший к центру (медоид). Это и
   есть выборка для слепка.

Модуль ничего не пишет и не строит: только читает файлы картинок и возвращает
список выбранных путей. Тяжёлых зависимостей (torch) здесь нет — считается
только декодирование картинок и k-means.
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# Кадры ближе этого расстояния Хэмминга (из 64 бит) считаются одной серией.
DEFAULT_DEDUP = 6

# Автоподбор числа сцен идёт по этому диапазону.
DEFAULT_K_MIN = 2
DEFAULT_K_MAX = 40

# Рабочий размер выборки для слепка: столько разных кадров нужно с папки.
# Владелец замерил 20–30 фото на слепок (docs/fingerprint_size_experiment.md),
# поэтому число сцен приводится к этому диапазону.
DEFAULT_SELECT_MIN = 20
DEFAULT_SELECT_MAX = 30

# Выбор k: берём наибольшее k, чей силуэт не хуже этой доли от лучшего.
# Силуэт почти всегда максимален при k=2 (две «кучки» — светлое/тёмное,
# близкое/дальнее), но такой ответ бесполезен: нужны 20–30 разных сцен.
K_SCORE_TOLERANCE = 0.9

# Масштаб яркости в составном признаке.
#
# Каждый бит хранится как ±1, поэтому вклад блока из N бит в евклидово
# расстояние — порядка 2*sqrt(N): pHash и dHash (по 64 бита) дают до ~16,
# цветовая подпись (42 бита) — до ~13. Блоки почти сбалансированы без
# множителей, поэтому идут «как есть», побитово.
#
# Яркость — единственная скалярная ось: при равном весе она вносила бы ~2, то
# есть в 6–8 раз меньше блоков, и утонула бы в них. Поэтому умножаем её на 6:
# размах день/ночь (Δ≈0.5) весит ~3 — как блок из 2–3 бит. Проверял множители
# 3…20 — итоговое число сцен менялось не больше чем на одну.
BRIGHTNESS_WEIGHT = 6.0

# dHash по умолчанию включён: замер показал, что он меняет примерно половину
# выборки, но явного выигрыша не дал (docs/scene_selection.md). Переключатель
# оставлен, чтобы можно было сравнить.
USE_DHASH = True


def frame_features(path: str) -> dict | None:
    """
    Признаки одного кадра; None, если файл не читается.

    Кроме отпечатка pHash («как выглядит кадр») считаются dHash, цветовая
    подпись и яркость: именно они отличают условия съёмки — день от ночи,
    зиму от лета, солнце от пасмурности.
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


def features_for(photos: list[Path], workers: int) -> list[dict]:
    """Признаки всех кадров папки (порядок сохраняется)."""

    if not photos:
        return []

    if workers <= 1 or len(photos) == 1:
        rows = [frame_features(str(path)) for path in photos]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(frame_features, [str(path) for path in photos]))

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


def packed_bits(values: list[int], index: np.ndarray) -> np.ndarray:
    """Распаковать 64-битные отпечатки в вектор ±1 (строки — кадры)."""

    packed = np.array([values[i] for i in index], dtype=np.uint64)
    bits = np.unpackbits(
        packed.view(np.uint8).reshape(len(index), 8), axis=1
    ).astype(np.float32)

    return (bits * 2.0) - 1.0


def scene_features(
    rows: list[dict], keep: list[int], use_dhash: bool = USE_DHASH
) -> np.ndarray:
    """
    Составной признак сцены для выбранных кадров (по одному на серию).

    Все биты приводятся к ±1: тогда евклидово расстояние по битовым блокам —
    это половина расстояния Хэмминга, и k-means работает «по похожести».
    """

    index = np.array(keep, dtype=int)

    parts = [packed_bits([row["phash"] for row in rows], index)]

    if use_dhash:
        parts.append(packed_bits([row["dhash"] for row in rows], index))

    color_bits = np.array([rows[i]["color"] for i in index], dtype=np.float32)
    parts.append((color_bits * 2.0) - 1.0)

    parts.append(
        np.array(
            [[rows[i]["brightness"] * BRIGHTNESS_WEIGHT] for i in index],
            dtype=np.float32,
        )
    )

    return np.hstack(parts)


def cluster(
    features: np.ndarray, k: int, *, seed: int = 0
) -> list[int]:
    """Метки k-means ровно на k кластеров."""

    from sklearn.cluster import KMeans

    labels = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(features)

    return [int(item) for item in labels]


def choose_k(
    features: np.ndarray,
    k_min: int = DEFAULT_K_MIN,
    k_max: int = DEFAULT_K_MAX,
    forced: int | None = None,
) -> tuple[int, list[dict], list[int], float | None]:
    """
    Подобрать число сцен по силуэту на составном признаке.

    Автовыбор: перебираем k от k_min до k_max, находим лучший силуэт и берём
    НАИБОЛЬШЕЕ k, чей силуэт не хуже K_SCORE_TOLERANCE от лучшего. Так
    разбиение не проигрывает по качеству, но сцен в нём больше.

    forced задаёт число сцен вручную (тогда перебор пропускается).

    Возвращает (k, оценки по всем k, метки, силуэт выбранного k).
    """

    from sklearn.metrics import silhouette_score

    count = len(features)

    if count < 3:
        return 1, [{"k": 1, "silhouette": None}], [0] * count, None

    top = min(k_max, count - 1)

    if forced is not None:
        k = max(2, min(forced, top))
        labels = cluster(features, k)

        if len(set(labels)) < 2:
            return 1, [{"k": 1, "silhouette": None}], [0] * count, None

        score = round(float(silhouette_score(features, labels)), 4)

        return k, [{"k": k, "silhouette": score}], labels, score

    scores: list[dict] = []
    labels_by_k: dict[int, list[int]] = {}

    for k in range(max(2, k_min), top + 1):
        labels = cluster(features, k)

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

    return chosen, scores, labels_by_k[chosen], float(silhouette)


def target_scenes(
    natural: int,
    representatives: int,
    select_min: int = DEFAULT_SELECT_MIN,
    select_max: int = DEFAULT_SELECT_MAX,
    forced: int | None = None,
) -> int:
    """
    Сколько сцен взять в работу.

    Правило владельца: в слепок идут 20–30 разных кадров. Поэтому
      * нашли меньше 20 условий съёмки — берём 20 (кластеры дробим мельче,
        выборка равномерно добирается по папке);
      * нашли больше 30 — берём 30 (лишние схлопываются);
      * нашли в диапазоне — берём как есть.
    Больше, чем есть серий, сцен не бывает.
    """

    if forced is not None:
        return max(1, min(forced, representatives))

    return max(1, min(max(natural, select_min), select_max, representatives))


def pick_representatives(
    features: np.ndarray,
    labels: list[int],
    rows: list[dict],
    keep: list[int],
) -> list[str]:
    """
    По одному кадру на кластер: ближайший к центру кластера (медоид).

    Это и есть выборка для слепка: каждая сцена представлена своим, самым
    «типичным» кадром. Кластер из одного кадра даёт этот же кадр.
    """

    labels_array = np.array(labels, dtype=int)
    picks: list[str] = []

    if not len(labels_array):
        return picks

    for cluster_id in range(int(labels_array.max()) + 1):
        members = np.flatnonzero(labels_array == cluster_id)

        if not members.size:
            continue

        centre = features[members].mean(axis=0)
        distances = np.linalg.norm(features[members] - centre, axis=1)
        picks.append(rows[keep[int(members[int(distances.argmin())])]]["path"])

    return picks


def select_scene_photos(
    photos: list[Path],
    *,
    workers: int = 1,
    dedup: int = DEFAULT_DEDUP,
    k_min: int = DEFAULT_K_MIN,
    k_max: int = DEFAULT_K_MAX,
    select_min: int = DEFAULT_SELECT_MIN,
    select_max: int = DEFAULT_SELECT_MAX,
    use_dhash: bool = USE_DHASH,
    forced_k: int | None = None,
) -> dict:
    """
    Выборка кадров по сценам: 20–30 непохожих снимков из папки.

    Возвращает словарь с выбранными путями (`picked`) и диагностикой: сколько
    кадров прочитано, сколько серий, сколько сцен нашлось до приведения к
    диапазону, сколько взято и силуэт.
    """

    rows = features_for(photos, workers)

    result = {
        "photos": len(photos),
        "hashed": len(rows),
        "series": 0,
        "natural_scenes": 0,
        "scenes": 0,
        "silhouette": None,
        "scores": [],
        "picked": [],
        "shots_files": [],
        "shots_scene": [],
    }

    if not rows:
        return result

    hashes = np.array([row["phash"] for row in rows], dtype=np.uint64)
    groups = dedup_groups(hamming_matrix(hashes), dedup)

    # Кластеризуем по одному представителю на серию: снимки из одной серии
    # («щелчок за щелчком») не должны попадать в разные сцены.
    keep = [group[0] for group in groups]
    features = scene_features(rows, keep, use_dhash)

    natural, scores, labels, silhouette = choose_k(features, k_min, k_max, forced_k)
    scenes = target_scenes(natural, len(keep), select_min, select_max, forced_k)

    if scenes != natural and len(keep) >= 2:
        labels = cluster(features, scenes)

    result.update(
        {
            "series": len(groups),
            "natural_scenes": natural,
            "scenes": scenes,
            "silhouette": silhouette,
            "scores": scores,
            "picked": pick_representatives(features, labels, rows, keep),
            "shots_files": [
                [rows[index]["path"] for index in group] for group in groups
            ],
            "shots_scene": labels,
        }
    )

    return result


def default_workers() -> int:
    """Процессов на декодирование по умолчанию (все ядра)."""

    return max(1, os.cpu_count() or 1)
