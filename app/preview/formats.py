"""
Формат файлов превью: расширение, MIME-тип и параметры кодирования.

Модуль намеренно ничего не импортирует из тяжёлых зависимостей (torch, faiss):
его читают и API (отдача файлов), и воркер (генерация), и скрипты
обслуживания. Формат задаётся `SCENE_PREVIEW_FORMAT`.

Почему WebP по умолчанию: замер на корпусе (24 реальных оригинала) дал
−46 % к JPEG q90 при том же разрешении 1280 px и без видимой разницы на
кропах 1:1; подробности — docs/preview_experiment_20261022.md.
"""

from __future__ import annotations

import os
from pathlib import Path

# Значения по умолчанию для каждого формата: у WebP шкала качества строже,
# поэтому 80 там соответствует примерно JPEG q85–90 по видимому результату.
DEFAULT_FORMAT = "webp"
DEFAULT_QUALITY = {"webp": 80, "jpeg": 90}

# Расширения файлов: первый вариант — тот, которым пишет генератор.
FORMATS: dict[str, tuple[str, str]] = {
    "jpeg": (".jpg", "image/jpeg"),
    "webp": (".webp", "image/webp"),
}

# Имена, которыми тот же формат называет Pillow (image.format).
PIL_NAMES = {"jpeg": "JPEG", "webp": "WEBP"}

# Все форматы, которые принимает валидатор превью: свои для текущего формата
# и прежние — чтобы уже сгенерированные файлы оставались валидными.
SUPPORTED_PIL_FORMATS = frozenset(PIL_NAMES.values())

# Алиасы, которые может написать человек в SCENE_PREVIEW_FORMAT.
ALIASES = {"jpg": "jpeg", "jpeg": "jpeg", "webp": "webp"}

# Форматы, которыми писали прежние версии: нужны, чтобы отдать уже
# сгенерированное превью во время перехода и чтобы найти старые файлы
# при очистке.
LEGACY_FORMATS = ("jpeg",)


def normalize_format(value: object) -> str:
    """Привести значение настройки к известному формату (иначе — умолчание)."""

    if isinstance(value, str):
        candidate = ALIASES.get(value.strip().lower())
        if candidate:
            return candidate
    return DEFAULT_FORMAT


def current_format() -> str:
    """Формат, которым пишутся новые превью (`SCENE_PREVIEW_FORMAT`)."""

    return normalize_format(os.getenv("SCENE_PREVIEW_FORMAT", DEFAULT_FORMAT))


def extension(image_format: str | None = None) -> str:
    fmt = normalize_format(image_format) if image_format else current_format()
    return FORMATS[fmt][0]


def media_type(image_format: str | None = None) -> str:
    fmt = normalize_format(image_format) if image_format else current_format()
    return FORMATS[fmt][1]


def quality_for(image_format: str | None = None, value: int | None = None) -> int:
    """
    Качество кодирования: явное значение важнее формата.

    `SCENE_PREVIEW_QUALITY` — общий переключатель; если он не задан, берётся
    умолчание формата (WebP 80, JPEG 90).
    """

    if value is not None:
        return int(value)

    raw = os.getenv("SCENE_PREVIEW_QUALITY")
    if raw is not None and str(raw).strip():
        try:
            parsed = int(raw)
        except ValueError:
            parsed = 0
        if 1 <= parsed <= 100:
            return parsed

    fmt = normalize_format(image_format) if image_format else current_format()
    return DEFAULT_QUALITY[fmt]


def candidate_paths(path: Path, image_format: str | None = None) -> list[Path]:
    """
    Пути, по которым может лежать превью этого размера.

    Первым идёт текущий формат, затем прежние (JPEG): во время перехода
    часть файлов ещё не пересоздана, и отдавать 404 было бы неверно.
    """

    bases = [path]
    for legacy in LEGACY_FORMATS:
        legacy_ext = FORMATS[legacy][0]
        if path.suffix != legacy_ext:
            bases.append(path.with_suffix(legacy_ext))

    return bases


def is_legacy(path: Path, image_format: str | None = None) -> bool:
    """True для файла прежнего формата, который вытеснен текущим."""

    current_ext = extension(image_format)
    return path.suffix.lower() != current_ext and path.suffix.lower() in {
        FORMATS[legacy][0] for legacy in LEGACY_FORMATS
    }


def save_preview(
    image,
    output_path: str | Path,
    *,
    image_format: str | None = None,
    quality: int | None = None,
) -> None:
    """
    Записать изображение в целевом формате с параметрами этого формата.

    WebP: method=4 — разумный компромисс скорости и плотности (замер:
    ~80 мс на кадр 1280 px против ~7 мс у JPEG; для фонового этапа
    несущественно).
    """

    fmt = normalize_format(image_format) if image_format else current_format()
    level = quality_for(fmt, quality)

    if fmt == "webp":
        image.save(output_path, format="WEBP", quality=level, method=4)
    else:
        image.save(output_path, format="JPEG", quality=level, optimize=True)
