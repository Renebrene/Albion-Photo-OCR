#!/usr/bin/env python
"""
Оценка сортировки без QWEN: насколько автоматика попадает в правильный адрес.

Для большого корпуса, где файлы подписаны названием, похожим на юридический
адрес («40 лет Победы 154 А (10).JPG»), можно проверить **только**
INSPECT → DINO → HYBRID, не тратя время на QWEN: адрес фото даёт гибрид, а
эталон известен из имени файла.

Скрипт только читает и отвечает на вопросы:

- сколько фото распознано верно, сколько отнесено к другому адресу;
- сколько попало в «Требуют проверки» (слабое совпадение или почти равный
  выбор) — это ожидаемая защита, а не ошибка;
- у каких адресов вообще нет активного слепка: такие фото распознать нечем,
  и они не должны считаться ошибкой модели.

    .venv/bin/python scripts/evaluate_sorting.py
    .venv/bin/python scripts/evaluate_sorting.py --folder "/mnt/photos/тест"
    .venv/bin/python scripts/evaluate_sorting.py --json --limit 5000

Правила сопоставления имени файла с адресом: имя нормализуется так же, как в
«Уточнении» (регистр, пробелы, пунктуация, юридические формы, латиница и
кириллица), затем ищется самый длинный адрес, с которого начинается имя файла.
Фото, в имени которого адрес не найден, в оценку не входят — их эталон
неизвестен.
"""

from __future__ import annotations

import argparse
import json
import sys
import re
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api import repository  # noqa: E402
from app.hybrid import config as hybrid_config  # noqa: E402
from app.ingest.database import get_connection  # noqa: E402
from app.refine.logic import skeleton  # noqa: E402

# Имена адресов для читаемого отчёта заполняет load_addresses().
ADDRESS_NAMES: dict[int, str] = {}


def load_addresses() -> list[tuple[int, str]]:
    """Активные адреса: (address_id, нормализованное имя)."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT address_id, simple_address, legal_address
                FROM public.address_directory
                WHERE active
                """
            )
            rows = cur.fetchall()

    result = []

    for address_id, simple, legal in rows:
        name = skeleton(simple or legal or "")

        if name:
            result.append((int(address_id), name))

        ADDRESS_NAMES[int(address_id)] = (simple or legal or "").strip()

    return result


def expected_address(filename: str, addresses: list[tuple[int, str]]) -> int | None:
    """
    Адрес по имени файла: самый длинный однозначный вариант.

    Имена бывают сокращёнными: «буденновский (1).JPG» при адресе
    «Буденновский / Нансена», «Комарова13_11.JPG» при «Комарова 13».
    Поэтому имя и адрес сравниваются в обе стороны, но короткая сторона
    должна быть не короче 5 символов, а при двух равных вариантах адрес не
    угадывается — фото просто не входит в оценку.
    """

    # «буденновский (1)», «Комарова13_11», «Зорге46_02»: хвостовой номер —
    # это индекс копии, а не часть адреса.
    stem = re.sub(r"[\s_\-]*\(?\d{1,4}\)?$", "", Path(filename).stem)
    name = skeleton(stem or Path(filename).stem)

    if len(name) < 4:
        return None

    candidates: list[tuple[int, int]] = []

    for address_id, normalized in addresses:
        if not normalized or len(normalized) < 4:
            continue

        if name.startswith(normalized):
            candidates.append((len(normalized), address_id))
        elif normalized.startswith(name) and len(name) >= 5:
            candidates.append((len(name), address_id))

    if not candidates:
        return None

    candidates.sort(reverse=True)

    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        return None  # одинаково длинные совпадения: не угадываем

    return candidates[0][1]


def load_photos(
    folder: str | None,
    limit: int | None,
    low_score: float | None = None,
    min_margin: float | None = None,
):
    address_sql = repository._address_sql("p", low_score, min_margin)
    margin_sql = repository._latest_margin_sql("p")
    confidence_sql = repository._latest_confidence_sql("p")

    where = "TRUE"
    params: list[object] = []

    if folder:
        where = "p.source_path LIKE %s"
        params.append(f"{folder.rstrip('/')}%")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT p.photo_id, p.filename,
                       {address_sql} AS fingerprint,
                       {margin_sql} AS margin,
                       {confidence_sql} AS confidence
                FROM public.photos AS p
                WHERE {where}
                ORDER BY p.photo_id
                """ + ("LIMIT %s" if limit else ""),
                params + ([limit] if limit else []),
            )
            return cur.fetchall()


def fingerprint_addresses() -> dict[str, int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT af.fingerprint_id, af.address_id
                FROM public.address_fingerprints AS af
                JOIN public.fingerprints AS f
                  ON f.fingerprint_id = af.fingerprint_id AND f.active
                WHERE af.active
                """
            )
            return {row[0]: int(row[1]) for row in cur.fetchall()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Оценить сортировку без QWEN")
    parser.add_argument("--folder", default=None, help="только фото из этой папки")
    parser.add_argument("--limit", type=int, default=0, help="не больше N фото")
    parser.add_argument("--json", action="store_true", help="машиночитаемый вывод")
    parser.add_argument(
        "--show", type=int, default=10, help="сколько ошибок показать (по умолчанию 10)"
    )
    parser.add_argument(
        "--low-score", type=float, default=None,
        help="оценить при таком пороге сходства (по умолчанию — из настроек)",
    )
    parser.add_argument(
        "--min-margin", type=float, default=None,
        help="оценить при таком пороге отрыва (по умолчанию — из настроек)",
    )
    args = parser.parse_args(argv)

    addresses = load_addresses()
    fp_to_address = fingerprint_addresses()
    photos = load_photos(
        args.folder, args.limit or None, args.low_score, args.min_margin
    )

    low = hybrid_config.low_score() if args.low_score is None else args.low_score
    margin = hybrid_config.min_margin() if args.min_margin is None else args.min_margin

    stats = defaultdict(int)
    wrong_samples: list[dict] = []
    labelled_addresses: set[int] = set()

    for photo_id, filename, fingerprint, photo_margin, confidence in photos:
        expected = expected_address(filename, addresses)

        if expected is None:
            stats["no_label"] += 1
            continue

        stats["labelled"] += 1
        labelled_addresses.add(expected)

        if fingerprint is None:
            # Адреса нет: либо слабое совпадение, либо нет вердикта — фото
            # ждёт проверки, а не отнесено неверно.
            if confidence is not None or photo_margin is not None:
                stats["review"] += 1
            else:
                stats["no_verdict"] += 1
            continue

        predicted = fp_to_address.get(fingerprint)

        if predicted is None:
            stats["unmapped_fingerprint"] += 1
            continue

        if predicted == expected:
            stats["correct"] += 1
        else:
            stats["wrong"] += 1
            if len(wrong_samples) < args.show:
                wrong_samples.append(
                    {
                        "photo_id": photo_id,
                        "filename": filename,
                        "expected_address": expected,
                        "expected_name": ADDRESS_NAMES.get(expected, ""),
                        "predicted_address": predicted,
                        "predicted_name": ADDRESS_NAMES.get(predicted, ""),
                        "confidence": round(float(confidence), 3) if confidence is not None else None,
                        "margin": round(float(photo_margin), 5) if photo_margin is not None else None,
                    }
                )

    # Адреса из эталона, у которых нет активного слепка: их распознать нечем,
    # и ошибкой модели это не является.
    covered = set(fp_to_address.values())
    uncovered = sorted(labelled_addresses - covered)

    report = {
        "low_score": low,
        "min_margin": margin,
        "photos": len(photos),
        "labelled": stats["labelled"],
        "correct": stats["correct"],
        "wrong": stats["wrong"],
        "review": stats["review"],
        "no_verdict": stats["no_verdict"],
        "unmapped_fingerprint": stats["unmapped_fingerprint"],
        "no_label": stats["no_label"],
        "accuracy": (
            round(stats["correct"] / stats["labelled"], 4) if stats["labelled"] else None
        ),
        "addresses_with_fingerprint": len(covered),
        "wrong_samples": wrong_samples,
        "uncovered_addresses": uncovered,
        "uncovered_names": [ADDRESS_NAMES.get(item, "") for item in uncovered],
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(f"фото в выборке: {len(photos)}")
    print(f"  с известным адресом по имени файла: {stats['labelled']}")
    print(f"    верно:              {stats['correct']}")
    print(f"    другой адрес:       {stats['wrong']}")
    print(f"    в «Требуют проверки»: {stats['review']}  (слабое совпадение)")
    print(f"    без вердикта:       {stats['no_verdict']}")
    print(f"    слепок без адреса:  {stats['unmapped_fingerprint']}")
    print(f"  без адреса в имени:   {stats['no_label']}")
    if report["accuracy"] is not None:
        print(f"\nточность среди распознанных в адрес: {100 * report['accuracy']:.1f} %")
    print(f"пороги: сходство ≥ {low}, отрыв ≥ {margin}")

    if uncovered:
        print(f"\nадресов из эталона без активного слепка: {len(uncovered)}")
        for address_id in uncovered[:10]:
            print(f"  {address_id}: {ADDRESS_NAMES.get(address_id, '')}")

    if wrong_samples:
        print("\nошибки:")
        for sample in wrong_samples:
            print(
                f"  {sample['filename']}: ожидался «{sample['expected_name']}», "
                f"получен «{sample['predicted_name']}» "
                f"(сходство {sample['confidence']}, отрыв {sample['margin']})"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
