#!/usr/bin/env python
"""
Серии кадров: где распознавание прочитало один и тот же бренд по-разному.

Фото снимают сериями (ролики на видеоэкранах): соседние кадры — один и тот же
рекламодатель. Но кадр бывает неполным (надпись не успела появиться), смазанным
или перекрытым машиной, и QWEN читает «Ян» вместо «Яндекс». В базу попадают
разные клиент и бренд — и это разные ошибки в фильтрах и статистике.

Скрипт **только читает** и ничего не меняет:

1. собирает серии — кадры одного экрана (тот же адрес/слепок), идущие подряд
   по времени съёмки с разрывом не больше `--gap-minutes`;
2. внутри каждой серии ищет пары значений, которые являются одним и тем же
   именем: одно — префикс другого (`Ян` ⊂ `Яндекс`), либо совпадают с точностью
   до регистра, пробелов и латиница/кириллица (`MTC` ↔ `МТС`);
3. складывает находки по всему корпусу и показывает, сколько фото затронуто.

Важно, почему сравнение идёт **внутри серии**, а не по всей базе: глобально
`Яндекс` — префикс `Яндекс Лавка`, `Яндекс Маркет` и `Яндекс.Еда`, но это разные
бренды, и склеивать их нельзя. Внутри одной серии рекламодатель один, поэтому
короткое чтение там — действительно обрезанное длинное.

Замер на корпусе 1518 кадров (2026-10-23): интервал между соседними кадрами
одного экрана — медиана 41 с, 39 % в пределах 15 с. Но **времени мало**:
видеоэкран крутит плейлист, и в пределах получаса соседи могут быть разными
роликами. Признак «тот же ролик» — похожесть описаний QWEN (пересечение слов):

    схожесть   пар   клиент совпал   бренд совпал
    ≥0.6       106        90 %           87 %
    0.3–0.6    140        79 %           82 %
    <0.3       416        56 %           17 %

Поэтому `--gaps` ниже — **черновая оценка по времени**: она завышает
возможности (сосед по времени может рекламировать другой бренд). Точный отбор
требует сравнения описаний; это следующий шаг.

Использование:

    .venv/bin/python scripts/series_check.py
    .venv/bin/python scripts/series_check.py --gap-seconds 30 --json
    .venv/bin/python scripts/series_check.py --limit 2000

Найденные пары — кандидаты в алиасы (`client_aliases`): это неразрушающая
нормализация, которая уже используется фильтрами, панелями и статистикой
(см. docs/hybrid.txt и docs/frontend_quasar.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ingest.database import get_connection  # noqa: E402

# Латинские буквы, неотличимые на вид от кириллических: MTC ↔ МТС, Ozon ↔ Оzon.
HOMOGLYPHS = str.maketrans(
    {
        "a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у",
        "k": "к", "m": "м", "t": "т", "h": "н", "b": "в", "n": "п", "r": "г",
        "A": "А", "C": "С", "E": "Е", "O": "О", "P": "Р", "X": "Х", "Y": "У",
        "K": "К", "M": "М", "T": "Т", "H": "Н", "B": "В", "N": "П", "R": "Г",
    }
)

SAMPLE_LIMIT = 8


def skeleton(value: str) -> str:
    """Имя без регистра, пробелов, пунктуации и различий латиница/кириллица."""

    text = str(value).strip().lower().translate(HOMOGLYPHS)

    return "".join(char for char in text if char.isalnum())


def _moment(row) -> datetime | None:
    return row[2] or row[1]


def load_frames(limit: int | None):
    """
    Кадры в порядке съёмки: экран (адрес или каталог), время, клиент, бренд.

    Адрес — это слепок, выбранный распознаванием; для кадров без адреса
    ключом экрана остаётся каталог съёмки, иначе серия рассыпалась бы.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.photo_id,
                       p.created_at,
                       p.taken_at,
                       COALESCE(
                           (SELECT h.hybrid_final_id FROM public.hybrid_results AS h
                             WHERE h.photo_id = p.photo_id AND h.status = 'DONE'
                             ORDER BY h.finished_at DESC NULLS LAST,
                                      h.hybrid_run_id DESC LIMIT 1),
                           p.source_path
                       ) AS screen,
                       q.client,
                       q.brand
                FROM public.photos AS p
                LEFT JOIN public.photo_qwen AS q ON q.photo_id = p.photo_id
                ORDER BY screen, COALESCE(p.taken_at, p.created_at), p.photo_id
                """ + ("LIMIT %s" if limit else ""),
                (limit,) if limit else (),
            )
            return cur.fetchall()


def build_series(rows, gap_minutes: float):
    """Резать последовательность на серии там, где пауза больше порога."""

    series = []
    current = []
    previous_screen = None
    previous_moment = None

    for row in rows:
        screen = row[3]
        moment = _moment(row)

        if current and (
            screen != previous_screen
            or moment is None
            or previous_moment is None
            or (moment - previous_moment).total_seconds() > gap_minutes * 60
        ):
            series.append(current)
            current = []

        current.append(row)
        previous_screen = screen
        previous_moment = moment

    if current:
        series.append(current)

    return series


def find_pairs(series, field_index: int):
    """
    Пары «одно чтение — часть другого» внутри серии.

    Возвращает (короткое, длинное, серия) — короткое считается обрезанным
    чтением длинного.
    """

    found = []

    for frames in series:
        values = defaultdict(int)

        for row in frames:
            value = (row[field_index] or "").strip()

            if value:
                values[value] += 1

        names = sorted(values, key=len)

        for index, short in enumerate(names):
            for long in names[index + 1:]:
                short_lower = short.lower().strip()
                long_lower = long.lower().strip()

                same_prefix = (
                    len(long_lower) > len(short_lower)
                    and long_lower.startswith(short_lower)
                )
                same_skeleton = skeleton(short) == skeleton(long)

                if same_prefix or same_skeleton:
                    found.append(
                        {
                            "short": short,
                            "long": long,
                            "photos_short": values[short],
                            "photos_long": values[long],
                            "reason": "префикс" if same_prefix else "написание",
                            "screen": frames[0][3],
                            "sample_short": [
                                row[0] for row in frames if (row[field_index] or "").strip() == short
                            ][:2],
                        }
                    )

    return found


def find_gaps(series, field_index: int):
    """
    Кадры без значения, у которых сосед по серии это значение знает.

    Это вторая половина задачи: неудачный кадр (перекрыт, не успел появиться)
    не должен терять клиента и бренд, если соседние кадры того же экрана их
    прочитали.
    """

    gaps = []

    for frames in series:
        known = defaultdict(int)

        for row in frames:
            value = (row[field_index] or "").strip()

            if value:
                known[value] += 1

        if not known:
            continue

        best = max(known.items(), key=lambda item: item[1])[0]

        for row in frames:
            if (row[field_index] or "").strip():
                continue

            gaps.append({"photo_id": row[0], "would_be": best, "screen": frames[0][3]})

    return gaps


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Найти кадры, где один бренд прочитан по-разному",
    )
    parser.add_argument("--gap-seconds", type=float, default=30.0,
                        help="разрыв между кадрами, после которого начинается "
                             "новая серия (по умолчанию 30 с — один ролик)")
    parser.add_argument("--json", action="store_true", help="машиночитаемый вывод")
    parser.add_argument("--limit", type=int, default=0, help="обработать не больше N кадров")
    parser.add_argument("--field", choices=["client", "brand", "both"], default="both")
    parser.add_argument("--gaps", action="store_true",
                        help="черновая оценка: кадры без значения, которые можно "
                             "дополнить от соседей по серии (только по времени — "
                             "на вращающемся экране может ошибаться)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    rows = load_frames(args.limit or None)
    series = build_series(rows, args.gap_seconds / 60.0)

    report: dict = {
        "frames": len(rows),
        "series": len(series),
        "gap_seconds": args.gap_seconds,
        "fields": {},
    }

    fields = [("client", 4), ("brand", 5)]

    if args.field != "both":
        fields = [item for item in fields if item[0] == args.field]

    for name, index in fields:
        pairs = find_pairs(series, index)
        by_pair = defaultdict(lambda: {"photos": 0, "series": 0, "reason": "", "samples": []})

        for pair in pairs:
            key = (pair["short"], pair["long"])
            entry = by_pair[key]
            entry["photos"] += pair["photos_short"]
            entry["series"] += 1
            entry["reason"] = pair["reason"]

            if len(entry["samples"]) < 2:
                entry["samples"].extend(pair["sample_short"])

        report["fields"][name] = {
            "pairs": len(by_pair),
            "photos_affected": sum(item["photos"] for item in by_pair.values()),
            "items": [
                {
                    "short": key[0],
                    "long": key[1],
                    "photos": value["photos"],
                    "series": value["series"],
                    "reason": value["reason"],
                    "samples": value["samples"],
                }
                for key, value in sorted(by_pair.items(), key=lambda item: -item[1]["photos"])
            ],
        }

    if args.gaps:
        report["gaps"] = {}

        for name, index in fields:
            gaps = find_gaps(series, index)
            report["gaps"][name] = {
                "photos": len(gaps),
                "samples": gaps[:5],
                "screens": len({item["screen"] for item in gaps}),
            }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"кадров: {len(rows)}, серий: {len(series)} (разрыв > {args.gap_seconds:g} с)")
    for name, data in report["fields"].items():
        print(f"\n=== {name}: пар {data['pairs']}, фото затронуто {data['photos_affected']} ===")
        for item in data["items"][:SAMPLE_LIMIT]:
            print(
                f"  {item['short']!r} ({item['photos']}) → {item['long']!r}"
                f"  [{item['reason']}, серий {item['series']}]"
            )
            print(f"      например: {', '.join(item['samples'][:2])}")
        if len(data["items"]) > SAMPLE_LIMIT:
            print(f"  … ещё {len(data['items']) - SAMPLE_LIMIT} пар")

    for name, data in (report.get("gaps") or {}).items():
        print(f"\n=== {name}: пустых {data['photos']} фото на {data['screens']} экранах ===")
        for item in data["samples"]:
            print(f"  {item['photo_id']} → можно подставить {item['would_be']!r}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
