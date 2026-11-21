"""
Запрещённые к выдаче слова: не пускать их в карточку фото.

Список ведёт владелец в техразделе («Запрещённые к выдаче слова»). Это не
цензура модели, а защита карточки: QWEN иногда «читает» на щите случайный
мат или обрывок распознавания, и слово попадает в клиента, бренд, теги или
описание. Такие слова не выводятся ни в одном из этих полей.

Правила простые и предсказуемые:

* client/brand — значение с запрещённым словом отбрасывается целиком
  (частично «почищенный» бренд выглядел бы как новый клиент);
* tags — тег с запрещённым словом удаляется;
* description — запрещённые слова вырезаются из текста, лишние пробелы и
  знаки по краям убираются; пустое описание становится None.

Сравнение — **целое слово** без учёта регистра: «педо» ловится в «педо-щит»
и «вот педо», но не в «торпедо». Границей считается и смена регистра внутри
слипшегося слова: QWEN иногда склеивает «Система ПЕДО» в «СистемаПедо» —
такое вхождение тоже ловится, а «Торпедо» остаётся. Раньше сравнивалась
подстрока, и такой список резал нормальные слова; морфологию («слова» →
«словом») покрывают добавлением нужных форм в список. Список может быть
пустым — тогда ничего не меняется.
"""

from __future__ import annotations

import re
from typing import Any


def _words(forbidden: list[str] | None) -> list[str]:
    return [str(word).strip().casefold() for word in (forbidden or []) if str(word).strip()]


def _is_word_char(char: str) -> bool:
    return char.isalnum() or char == "_"


def _starts_word(text: str, start: int) -> bool:
    """Совпадение начинается с границы слова."""

    if start == 0:
        return True

    previous, current = text[start - 1], text[start]

    if not _is_word_char(previous):
        return True

    # Слипшиеся слова QWEN: «СистемаПедо» — «Педо» начинается с заглавной
    # после строчной. «Торпедо» одним словом так не распадается.
    return previous.islower() and current.isupper()


def _ends_word(text: str, end: int) -> bool:
    """Совпадение заканчивается на границе слова."""

    if end >= len(text):
        return True

    previous, following = text[end - 1], text[end]

    if not _is_word_char(following):
        return True

    return previous.islower() and following.isupper()


def _spans(text: str, words: list[str]) -> list[tuple[int, int]]:
    """Границы всех вхождений запрещённых слов как отдельных слов."""

    spans: list[tuple[int, int]] = []

    for word in words:
        for match in re.finditer(re.escape(word), text, re.IGNORECASE):
            start, end = match.span()

            if _starts_word(text, start) and _ends_word(text, end):
                spans.append((start, end))

    return spans


def contains_forbidden(text: Any, words: list[str]) -> bool:
    """Есть ли в тексте хоть одно запрещённое слово отдельным словом."""

    if not words:
        return False

    return bool(_spans(str(text), words))


def _strip_forbidden(text: str, words: list[str]) -> str:
    """Вырезать запрещённые слова и привести пробелы/края в порядок."""

    result = text

    # Вырезаем с конца: индексы вхождений не сдвигаются.
    for start, end in sorted(_spans(text, words), reverse=True):
        result = result[:start] + " " + result[end:]

    # Опустевшие парные знаки (« », (), []) после вырезания слова убираем
    # целиком, иначе в описании остаётся «в сети « » до 1 ноября».
    # Дефис, оставшийся от составного слова («педо-щит» → «-щит»), убираем,
    # только когда он слит со словом: диапазоны вида «1 - 5» не трогаем.
    result = re.sub(r"(?<!\w)[-–—](?=\w)", "", result)
    result = re.sub(r"«\s*»|\(\s*\)|\[\s*\]|\"\s*\"", "", result)
    result = re.sub(r"\s{2,}", " ", result)
    result = re.sub(r"\s+([,.;:!?])", r"\1", result)
    result = re.sub(r"([«(\[])\s+", r"\1", result)

    return result.strip(" \t\n,.;:-|")


def forbidden_hits(fields: dict, forbidden: list[str] | None) -> list[dict]:
    """
    Какие поля карточки содержат запрещённые слова.

    Нужно ручной правке (`PUT /v1/photos/{id}/qwen-text`): обработка QWEN
    чистит поля сама, а ручная запись должна быть отвергнута с понятной
    причиной, а не сохранена молча.
    """

    words = _words(forbidden)

    if not words:
        return []

    hits: list[dict] = []

    for key in ("description", "client", "brand"):
        value = fields.get(key)

        if not value:
            continue

        word = next(
            (item for item in words if contains_forbidden(value, [item])), None
        )

        if word is not None:
            hits.append({"field": key, "value": str(value), "word": word})

    for tag in fields.get("tags") or []:
        word = next(
            (item for item in words if contains_forbidden(tag, [item])), None
        )

        if word is not None:
            hits.append({"field": "tags", "value": str(tag), "word": word})

    return hits


def find_forbidden(fields: dict, forbidden: list[str] | None) -> bool:
    """
    Есть ли в карточке (description/client/brand/tags) запрещённое слово.

    Для обслуживающих проходов по уже сохранённым строкам: важно, что это
    ровно те поля, которые чистит `sanitize_fields`, иначе строка попадёт в
    отчёт, а менять в ней будет нечего.
    """

    return bool(forbidden_hits(fields, forbidden))


def sanitize_fields(fields: dict, forbidden: list[str] | None) -> dict:
    """
    Вернуть копию полей без запрещённых слов (client/brand/tags/description).

    Остальные ключи не трогаются: правило касается только того, что видно в
    карточке фото.
    """

    words = _words(forbidden)

    if not words:
        return dict(fields or {})

    result = dict(fields or {})

    for key in ("client", "brand"):
        value = result.get(key)

        if value and contains_forbidden(value, words):
            result[key] = None

    description = result.get("description")

    if description and contains_forbidden(description, words):
        cleaned = _strip_forbidden(str(description), words)
        result["description"] = cleaned or None

    tags = result.get("tags")

    if isinstance(tags, list):
        result["tags"] = [
            tag for tag in tags if not contains_forbidden(tag, words)
        ]

    return result
