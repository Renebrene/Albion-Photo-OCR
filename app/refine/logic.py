"""
Правила «Уточнения»: какие кадры считать одной серией и что с ними делать.

Серия — кадры одного экрана, снятые подряд, на которых одно и то же
изображение. Признаки подобраны по замерам (docs/series_merge.md):

- интервал ≤ 30 с: ролики обычно пятисекундные, поэтому одно время без
  картинки ничего не гарантирует;
- хеш кропа с разницей ≤ 6: разница ≤ 6 → бренд совпадает в 82 % случаев,
  ≥ 15 → в 14 %.

Внутри группы правила намеренно осторожные:

1. **Дополнить пустое** значение можно, только если все непустые значения
   группы — одно и то же имя (совпадают с точностью до регистра, пробелов и
   латиницы/кириллицы). Иначе группа спорная и не трогается.
2. **Заменить** можно только редкое короткое чтение, которое является началом
   общего: «Ян» → «Яндекс». Замены глобально по префиксу запрещены — «Яндекс»
   является префиксом «Яндекс Лавка», «Яндекс Маркет» и «Яндекс.Еда», а это
   разные бренды.
3. **Спорные** группы (разные имена внутри одной картинки) не меняются, а
   попадают в отчёт: их решает человек или повторное чтение моделью.

Модуль ничего не знает про базу: на вход кадры, на выход предложения.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# Латинские буквы, неотличимые на вид от кириллических: MTC ↔ МТС.
_HOMOGLYPHS = str.maketrans(
    {
        "a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у",
        "k": "к", "m": "м", "t": "т", "h": "н", "b": "в", "n": "п", "r": "г",
        "A": "А", "C": "С", "E": "Е", "O": "О", "P": "Р", "X": "Х", "Y": "У",
        "K": "К", "M": "М", "T": "Т", "H": "Н", "B": "В", "N": "П", "R": "Г",
    }
)

# Юридические формы в начале названия: «ООО «Лента»» и «Лента» — одно имя.
_LEGAL_FORMS = (
    "ооо", "оао", "зао", "пао", "ао", "ип", "ано", "нко", "мкп", "гуп", "муп",
)

DEFAULT_GAP_SECONDS = 30.0
DEFAULT_MAX_DISTANCE = 6
DEFAULT_FIELDS = ("client", "brand")


@dataclass(frozen=True)
class Frame:
    """Один кадр: что нужно, чтобы отнести его к серии и сравнить значения."""

    photo_id: str
    screen: str | None
    taken_at: datetime | None
    phash: int | None
    client: str | None = None
    brand: str | None = None

    def value(self, field: str) -> str:
        return (getattr(self, field) or "").strip()


def skeleton(value: object) -> str:
    """
    Имя без регистра, пробелов, пунктуации, юридической формы и «ё».

    «ООО «ЛЕНТА»» и «Лента» дают одно и то же: иначе одна и та же сеть в
    группе считается двумя разными брендами и группа становится спорной.
    """

    text = str(value or "").strip().lower().translate(_HOMOGLYPHS)
    text = text.replace("ё", "е")
    words = "".join(char if char.isalnum() else " " for char in text).split()

    if len(words) > 1 and words[0] in _LEGAL_FORMS:
        words = words[1:]

    return "".join(words)


def is_variant(short: str, long: str) -> bool:
    """`short` — усечённое или иначе набранное `long` (но не наоборот)."""

    short_key = skeleton(short)
    long_key = skeleton(long)

    if not short_key or not long_key or short_key == long_key:
        return False

    return long_key.startswith(short_key)


def _same_name(left: str, right: str) -> bool:
    left_key, right_key = skeleton(left), skeleton(right)

    return bool(left_key) and left_key == right_key


def _distance(left: int | None, right: int | None) -> int | None:
    if left is None or right is None:
        return None

    return int(left ^ right).bit_count()


def build_groups(
    frames: list[Frame],
    *,
    gap_seconds: float = DEFAULT_GAP_SECONDS,
    max_distance: int = DEFAULT_MAX_DISTANCE,
) -> list[list[Frame]]:
    """
    Разбить кадры на серии: один экран, короткий интервал, тот же кадр.

    Кадры без времени съёмки в серии не попадают: связать их не с чем.
    Если у кадра нет хеша (кроп не создавался), остаётся только время — это
    допущение явно слабее, поэтому такие кадры всё равно группируются по
    времени, но правило замены для них то же.
    """

    ordered = sorted(
        (frame for frame in frames if frame.taken_at is not None),
        key=lambda frame: (str(frame.screen or ""), frame.taken_at, frame.photo_id),
    )

    groups: list[list[Frame]] = []
    current: list[Frame] = []
    previous: Frame | None = None

    for frame in ordered:
        new_group = False

        if previous is not None:
            if frame.screen != previous.screen:
                new_group = True
            elif (frame.taken_at - previous.taken_at).total_seconds() > gap_seconds:
                new_group = True
            else:
                distance = _distance(frame.phash, previous.phash)
                new_group = distance is not None and distance > max_distance

        if new_group and current:
            groups.append(current)
            current = []

        current.append(frame)
        previous = frame

    if current:
        groups.append(current)

    return groups


def _canonical(values: list[str]) -> tuple[str, int]:
    """Самое частое значение; при равенстве — более длинное (полнее)."""

    counts: dict[str, int] = {}

    for value in values:
        counts[value] = counts.get(value, 0) + 1

    return max(counts.items(), key=lambda item: (item[1], len(item[0])))


def propose(group: list[Frame], field: str) -> dict:
    """
    Что сделать с одним полем одной группы.

    Возвращает `{"fill": {...}, "replace": {...}, "disputed": [...]}`.
    Пустые словари и список — обычный случай: менять нечего.
    """

    if len(group) < 2:
        return {"fill": {}, "replace": {}, "disputed": []}

    values = [frame.value(field) for frame in group]
    nonempty = [value for value in values if value]

    if not nonempty:
        return {"fill": {}, "replace": {}, "disputed": []}

    canonical, _ = _canonical(nonempty)

    # Группа спорная, если непустые значения — не варианты одного имени.
    for value in nonempty:
        if value != canonical and not (
            _same_name(value, canonical) or is_variant(value, canonical)
        ):
            return {
                "fill": {},
                "replace": {},
                "disputed": sorted(set(nonempty)),
            }

    fill: dict[str, str] = {}
    replace: dict[str, tuple[str, str]] = {}

    for frame in group:
        value = frame.value(field)

        if not value:
            fill[frame.photo_id] = canonical
        elif value != canonical:
            # Здесь значение — вариант canonical (проверено выше): чаще всего
            # короткое чтение того же имени.
            replace[frame.photo_id] = (value, canonical)

    return {"fill": fill, "replace": replace, "disputed": []}
