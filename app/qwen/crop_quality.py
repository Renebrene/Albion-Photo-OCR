"""
Фильтр качества кропа: отложить чтение кропа, который детектор поймал зря.

Детектор YOLO-World иногда вырезает не щит: дефис, номер дома, стойку, крышу
автобуса. QWEN такое читает и возвращает пустоту — это 2,2 % кропов (861 из
39 597) и сотни минут локальной модели. Замер
(`scripts/bench_crop_quality.py`, 39 597 кропов, деление по сюжетам):

    zero-shot EfficientNet-B0: отсекает 62 % пустых кропов,
    ошибочно отсекает 1,1 % полезных (порог −0.1543 по val).

Фильтр **не решает, что кроп мусор**, а откладывает его чтение: сначала
читаются кропы, которые выглядят как щит, отложенные — только если ни один
нормальный кроп не дал описания. Так реклама не теряется, даже если фильтр
ошибся: её просто прочитают последней. Полный кадр читается по-прежнему,
когда кропов несколько (правило `multi_crop_full_frame_enabled`).

Модель грузится при первом использовании и только если фильтр включён;
ошибка загрузки (нет весов, нет torch) выключает фильтр на процесс и не
ломает QWEN.
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

# Порог из замера: разность косинусов «полезный» минус «мусорный» центроид.
# Ниже — кроп откладывается.
DEFAULT_THRESHOLD = -0.1543

_lock = threading.Lock()
_model = None
_failed = False


def _load() -> bool:
    """Загрузить модель один раз; False — фильтр недоступен."""

    global _model, _failed

    if _model is not None:
        return True

    if _failed:
        return False

    with _lock:
        if _model is not None:
            return True

        if _failed:
            return False

        try:
            import torch
            import torchvision

            weights = torchvision.models.EfficientNet_B0_Weights.IMAGENET1K_V1
            model = torchvision.models.efficientnet_b0(weights=weights)
            model.classifier = torch.nn.Identity()
            model.eval()

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device)

            _model = (model, weights.transforms(), torch.device(device))
            logger.info("crop quality filter ready (efficientnet_b0 on %s)", device)

            return True
        except Exception as exc:  # noqa: BLE001 — без фильтра QWEN работает
            _failed = True
            logger.warning("crop quality filter disabled: %s", exc)

            return False


def score(paths: list[str]) -> list[float] | None:
    """
    Оценки кропов для фильтра: «похоже на рекламный щит» минус «похоже на
    мусор». None — фильтр недоступен, откладывать нечего.
    """

    if not paths or not _load():
        return None

    import numpy as np
    import torch
    from PIL import Image

    model, transform, device = _model
    vectors = []

    try:
        for start in range(0, len(paths), 32):
            chunk = paths[start:start + 32]
            tensors = []

            for path in chunk:
                try:
                    with Image.open(path) as image:
                        tensors.append(transform(image.convert("RGB")))
                except Exception:  # noqa: BLE001 — битый кроп откладывать не надо
                    tensors.append(None)

            usable = [tensor for tensor in tensors if tensor is not None]

            if not usable:
                vectors.extend([None] * len(chunk))
                continue

            with torch.inference_mode():
                features = model(torch.stack(usable).to(device))

            values = features.float().cpu().numpy()
            norms = np.linalg.norm(values, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            values = values / norms

            iterator = iter(values)
            vectors.extend(
                next(iterator) if tensor is not None else None for tensor in tensors
            )
    except Exception as exc:  # noqa: BLE001 — фильтр не должен ломать чтение
        logger.warning("crop quality scoring failed: %s", exc)
        return None

    good, empty = _centroids()

    if good is None:
        return None

    return [
        float(vector @ good - vector @ empty) if vector is not None else 0.0
        for vector in vectors
    ]


_CENTROIDS: tuple = (None, None)


def _centroids():
    """
    Центроиды «полезных» и «мусорных» кропов из признаков ImageNet.

    Значения выведены замером: смесь на 33 000 кропах с метками QWEN
    (описание есть / ответ пуст). Пересчитать — `scripts/bench_crop_quality.py
    --write-centroids`; в коде держим зафиксированные числа, чтобы фильтр не
    зависел от базы при старте.
    """

    global _CENTROIDS

    if _CENTROIDS[0] is None:
        try:
            _CENTROIDS = _load_centroids()
        except Exception:  # noqa: BLE001
            return None, None

    return _CENTROIDS


def _load_centroids():
    import numpy as np
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "data/models/crop_quality_centroids.npz"
    )

    if not path.is_file():
        return None, None

    with np.load(path, allow_pickle=False) as data:
        good = data["good"].astype("float32")
        empty = data["empty"].astype("float32")

    good /= max(1e-9, float(np.linalg.norm(good)))
    empty /= max(1e-9, float(np.linalg.norm(empty)))

    return good, empty


def order_crops(paths: list[str], threshold: float) -> tuple[list[str], list[str]]:
    """
    (кропы для чтения сразу, отложенные).

    Оценки считаются одинаковой моделью дважды? Нет: центроиды считаются на
    ImageNet-признаках, поэтому достаточно одного прохода `score()`. Ошибка
    фильтра возвращает (paths, []) — прежнее поведение.
    """

    if len(paths) <= 1:
        return list(paths), []

    scores = score(paths)

    if scores is None:
        return list(paths), []

    immediate: list[str] = []
    deferred: list[str] = []

    for path, value in zip(paths, scores):
        (immediate if value >= threshold else deferred).append(path)

    return immediate, deferred
