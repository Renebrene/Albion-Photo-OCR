"""
Сцены в папках со снимками: отпечатки кадров и выборка 20–30 разных кадров.

    python scripts/scene_clusters.py --root data/input
    python scripts/scene_clusters.py --root data/input --json data/output/selection.json

Что делает по каждой папке (адресу):

1. Считает признаки кадров — параллельно, в несколько процессов:
   декодирование и есть основная стоимость.
2. Схлопывает почти одинаковые кадры: расстояние Хэмминга pHash меньше порога —
   это одна серия («щелчок за щелчком») или дубль, в выборке он не нужен.
3. Кластеризует по одному представителю каждой серии по СОСТАВНОМУ признаку
   (pHash + [dHash] + цветовая подпись + яркость) и подбирает число сцен по
   силуэту.
4. Приводит число сцен к рабочему диапазону 20–30 (`--select-min/--select-max`):
   если условий съёмки мало (2–3), кластеров всё равно столько, сколько нужно
   кадров — выборка добирается равномерно по папке; если сцен слишком много,
   лишние схлопываются порогом.
5. Берёт по одному кадру на кластер — ближайший к центру кластера. Это и есть
   готовая выборка для слепка: непохожие кадры из разных условий съёмки.
6. Печатает для каждой папки хвост кривой «k: силуэт», выбранное k и список
   отобранных файлов (в JSON по `--select-json`).

Скрипт ничего не меняет: он читает папки и рассказывает, что из них выбрал.
Сборка слепков — следующий шаг, отдельной командой.
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

# Рабочий размер выборки для слепка: столько разных кадров нужно с папки.
# Владелец замерил 20–30 фото на слепок (docs/fingerprint_size_experiment.md),
# поэтому число сцен приводится к этому диапазону: меньше 20 — добираем
# кластеры, больше 30 — схлопываем.
DEFAULT_SELECT_MIN = 20
DEFAULT_SELECT_MAX = 30

# dHash в составном признаке: он ловит направление градиента (pHash — крупные
# блоки DCT после сглаживания), то есть ракурс и «куда смотрит» кадр. Блок
# ±1-бит, как pHash, — веса сопоставимы.
USE_DHASH = True

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

    Блоки в одном векторе:
      * pHash (64 бита) — композиция/ракурс;
      * dHash (64 бита, если включён) — разность соседних пикселей, то есть
        направление градиента; pHash это низкочастотная DCT уменьшенного
        кадра. Блоки считают разное (контур/деталь против общей композиции),
        поэтому вместе они разделяют кадры чуть точнее, чем один pHash;
      * цветовая подпись (42 бита) — температура и насыщенность, то есть
        погода и время суток;
      * яркость (одна ось, ×BRIGHTNESS_WEIGHT) — прямая подсказка о свете.

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


def target_scenes(
    natural: int,
    representatives: int,
    select_min: int,
    select_max: int,
    forced: int | None = None,
) -> int:
    """
    Сколько сцен взять в работу.

    Правило владельца: в слепок идут 20–30 разных кадров. Поэтому
      * нашли меньше 20 условий съёмки — берём 20 (кластеры дробим мельче,
        выборка равномерно добирается по папке);
      * нашли больше 30 — берём 30 (лишние схлопываются);
      * нашли в диапазоне — берём как есть.
    Больше, чем есть серий, сцен не бывает: кластер из одного кадра — норма.
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

    for cluster in range(int(labels_array.max()) + 1 if len(labels_array) else 0):
        members = np.flatnonzero(labels_array == cluster)

        if not members.size:
            continue

        centre = features[members].mean(axis=0)
        distances = np.linalg.norm(features[members] - centre, axis=1)
        picks.append(rows[keep[int(members[int(distances.argmin())])]]["path"])

    return picks


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
    select_min: int = DEFAULT_SELECT_MIN,
    select_max: int = DEFAULT_SELECT_MAX,
    use_dhash: bool = USE_DHASH,
) -> dict:
    """Признаки, серии дублей, число сцен и выборка кадров для одной папки."""

    started = time.perf_counter()
    rows = hash_folder(photos, workers)

    if not rows:
        return {
            "address": folder.name,
            "photos": len(photos),
            "hashed": 0,
            "shots": 0,
            "scenes": 0,
            "selected": 0,
            "selected_files": [],
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
    features = scene_features(rows, keep, use_dhash)

    natural, scores, labels, silhouette = choose_k(
        features, k_min, k_max, forced_k
    )

    # Рабочий диапазон 20–30: мало сцен — дробим мельче, много — схлопываем.
    scenes = target_scenes(natural, len(keep), select_min, select_max, forced_k)

    if scenes != natural and len(keep) >= 2:
        from sklearn.cluster import KMeans

        labels = [
            int(item)
            for item in KMeans(
                n_clusters=scenes, n_init=10, random_state=0
            ).fit_predict(features)
        ]

    selected = pick_representatives(features, labels, rows, keep)

    return {
        "address": folder.name,
        "folder": str(folder),
        "photos": len(photos),
        "hashed": len(rows),
        "shots": len(groups),
        "natural_scenes": natural,
        "scenes": scenes,
        "selected": len(selected),
        "selected_files": selected,
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
        f"  {result['address']:>4}  сцен={result['scenes']:>3} "
        f"(нашлось {result.get('natural_scenes', result['scenes'])})  "
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
        "--select-min",
        type=int,
        default=DEFAULT_SELECT_MIN,
        help="минимум кадров в выборке (меньше сцен — дробим мельче)",
    )
    parser.add_argument(
        "--select-max",
        type=int,
        default=DEFAULT_SELECT_MAX,
        help="максимум кадров в выборке (больше сцен — схлопываем)",
    )
    parser.add_argument(
        "--no-dhash",
        action="store_true",
        help="считать признак без dHash (pHash + цвет + яркость)",
    )
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
        f"выборка: {args.select_min}–{args.select_max} кадров, "
        f"dHash: {'нет' if args.no_dhash else 'да'}, "
        f"k={'авто' if args.k is None else args.k}\n"
    )

    print(
        f"{'адрес':>8} {'фото':>5} {'кадров':>7} {'серий':>6} {'сцен':>5} "
        f"{'выборка':>7}  {'силуэт':>7}  сек"
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
            args.select_min,
            args.select_max,
            not args.no_dhash,
        )

        results.append(result)

        best = result.get("silhouette")

        print(
            f"{result['address']:>8} {result['photos']:>5} {result['hashed']:>7} "
            f"{result.get('shots', 0):>6} {result['scenes']:>5} "
            f"{result.get('selected', 0):>7}  "
            f"{f'{best:.3f}' if best is not None else '—':>7}  {result['seconds']:>4}"
        )

    print("\nподбор числа сцен (хвост кривой «k: силуэт», последние 8 k):")

    for result in results:
        print_k_curve(result)

    scenes = [result["scenes"] for result in results if result["scenes"]]
    selected = [result.get("selected", 0) for result in results]
    grown = [
        result["address"]
        for result in results
        if result.get("scenes", 0) > result.get("natural_scenes", 0)
    ]
    shrunk = [
        result["address"]
        for result in results
        if result.get("scenes", 0) < result.get("natural_scenes", 0)
    ]

    if scenes:
        print(
            f"\nсцен на папку: мин {min(scenes)}, среднее "
            f"{sum(scenes) / len(scenes):.1f}, макс {max(scenes)}; "
            f"кадров в выборке: мин {min(selected)}, "
            f"среднее {sum(selected) / len(selected):.1f}, макс {max(selected)}"
        )

    if grown:
        print(f"дроблено до {args.select_min}: {', '.join(grown)}")

    if shrunk:
        print(f"схлопнуто до {args.select_max}: {', '.join(shrunk)}")

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
