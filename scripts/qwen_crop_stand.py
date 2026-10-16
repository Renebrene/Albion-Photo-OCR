#!/usr/bin/env python
"""
Замерный стенд: помогает ли кроп распознаванию вывесок/щитов.

Зачем. Большой щит часто занимает лишь центр кадра: при лимите 1280 px по
длинной стороне щит получает мало пикселей. Центральный кроп убирает края, и
щит занимает их больше. Нужен честный замер: стало лучше или хуже, и чего это
стоит по времени и токенам.

Как считаем. Стенд ничего не пишет в базу: берёт фото, у которых уже есть
описание (эталон — текущие клиент/бренд/категория), прогоняет каждое фото в
нескольких режимах и сравнивает поля с эталоном. Это не «правильный ответ», а
«совпадает ли с тем, что уже принято в базе», поэтому режим с высоким
совпадением — кандидат, а не доказательство.

Запуск (локальная модель, ничего наружу):
    python scripts/qwen_crop_stand.py --limit 20 --modes off,center:0.6

Запуск с облачным провайдером (изображения уходят на внешний сервис!):
    python scripts/qwen_crop_stand.py --limit 20 --modes off,center:0.6 --cloud

Отчёт: docs/qwen_crop_experiment.md и docs/qwen_crop_experiment_result.json.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ingest.database import get_connection  # noqa: E402
from app.qwen import database as qwen_db  # noqa: E402
from app.qwen import processor as qwen  # noqa: E402

FIELDS = ("client", "brand", "category")


def parse_mode(spec: str) -> dict:
    """`off` или `center:0.6` → {"mode": …, "ratio": …}."""

    spec = spec.strip().lower()

    if spec in ("off", "full", "whole"):
        return {"mode": "off", "ratio": 1.0}

    if spec.startswith("center"):
        _, _, ratio = spec.partition(":")
        try:
            value = float(ratio) if ratio else 0.6
        except ValueError as exc:
            raise SystemExit(f"не понимаю режим: {spec}") from exc

        return {"mode": "center", "ratio": min(max(value, 0.2), 1.0)}

    raise SystemExit(f"не понимаю режим: {spec}")


def sample_photos(limit: int) -> list[dict]:
    """Фото с описанием и непустым хотя бы одним полем-эталоном."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, description, client, brand, category
                FROM public.photo_qwen
                WHERE status = 'DONE'
                  AND COALESCE(description, '') <> ''
                  AND (
                      COALESCE(client, '') <> ''
                      OR COALESCE(brand, '') <> ''
                      OR COALESCE(category, '') <> ''
                  )
                ORDER BY photo_id
                LIMIT %s
                """,
                (int(limit),),
            )
            rows = cur.fetchall()

    return [
        {
            "photo_id": row[0],
            "description": row[1],
            "client": row[2],
            "brand": row[3],
            "category": row[4],
        }
        for row in rows
    ]


def normalise(value: object) -> str:
    return str(value or "").strip().casefold()


def run_mode(photo: dict, mode: dict, config: dict) -> dict:
    source = qwen_db.get_photo_source(photo["photo_id"])

    if not source:
        return {"photo_id": photo["photo_id"], "error": "нет исходника"}

    path = qwen.analysis_input(photo["photo_id"], source)
    run_config = {**config, "crop": mode}

    started = time.perf_counter()

    try:
        fields, raw, _ = qwen.analyze_image(str(path), config=run_config)
    except Exception as exc:  # noqa: BLE001 - стенд должен доехать до отчёта
        return {
            "photo_id": photo["photo_id"],
            "seconds": round(time.perf_counter() - started, 2),
            "error": f"{type(exc).__name__}: {str(exc)[:200]}",
        }

    prompt, completion, total = qwen_db.token_usage(raw)

    return {
        "photo_id": photo["photo_id"],
        "seconds": round(time.perf_counter() - started, 2),
        "fields": {name: fields.get(name) for name in FIELDS},
        "tokens": total,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "matches": {
            name: (
                normalise(fields.get(name)) == normalise(photo.get(name))
                if normalise(photo.get(name))
                else None
            )
            for name in FIELDS
        },
    }


def summarise(runs: list[dict]) -> dict:
    ok = [run for run in runs if "error" not in run]
    errors = len(runs) - len(ok)

    def rate(field: str) -> float | None:
        judged = [
            run["matches"][field]
            for run in ok
            if run["matches"].get(field) is not None
        ]

        if not judged:
            return None

        return round(100.0 * sum(1 for value in judged if value) / len(judged), 1)

    return {
        "photos": len(ok),
        "errors": errors,
        "agreement": {field: rate(field) for field in FIELDS},
        "seconds_mean": (
            round(statistics.mean(run["seconds"] for run in ok), 2) if ok else None
        ),
        "tokens_total": sum(run.get("tokens") or 0 for run in ok) or None,
    }


def write_report(path: Path, payload: dict) -> None:
    lines = [
        "# Замер: кроп кадра для QWEN",
        "",
        f"Дата: {payload['run_at']}",
        f"Провайдер: **{payload['provider']}**, модель: `{payload['model']}`",
        f"Фото: {payload['photos']} (лимит {payload['limit']})",
        "",
        "| Режим | Совпало клиент | бренд | категория | Секунд (сред.) | Токенов | Ошибок |",
        "|---|---|---|---|---|---|---|",
    ]

    for mode, summary in payload["modes"].items():
        agreement = summary["agreement"]

        def cell(field: str) -> str:
            value = agreement.get(field)
            return "—" if value is None else f"{value} %"

        lines.append(
            f"| `{mode}` | {cell('client')} | {cell('brand')} | {cell('category')} "
            f"| {summary['seconds_mean']} | {summary['tokens_total'] or '—'} "
            f"| {summary['errors']} |"
        )

    lines += [
        "",
        "«Совпало» = ответ модели совпал с тем, что уже лежит в базе (эталон —",
        "принятые ранее значения), а не с ручной разметкой. Режим с высоким",
        "совпадением — кандидат на включение (`qwen_crop` / `qwen_crop_ratio` в",
        "настройках приложения), но решает владелец по своим фотографиям.",
        "",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--modes",
        default="off,center:0.6",
        help="через запятую: off, center:0.6, center:0.4",
    )
    parser.add_argument(
        "--cloud",
        action="store_true",
        help="разрешить облачный провайдер (изображения уйдут наружу)",
    )
    parser.add_argument(
        "--provider",
        choices=("ollama", "openai"),
        default=None,
        help="принудительный провайдер (по умолчанию — текущий из настроек)",
    )
    parser.add_argument("--model", default=None, help="переопределить модель")
    parser.add_argument(
        "--out",
        default=str(ROOT / "docs" / "qwen_crop_experiment.md"),
    )
    args = parser.parse_args()

    config = qwen.resolve_settings()

    if args.provider and args.provider != config["provider"]:
        config = {
            **config,
            "provider": args.provider,
            "model": args.model or qwen.model_for_provider(args.provider),
        }

    if config["provider"] != "ollama" and not args.cloud:
        print(
            "Провайдер облачный: изображения уйдут на внешний сервис. "
            "Добавьте --cloud, если это осознанное решение."
        )
        return 2

    if args.model:
        config = {**config, "model": args.model}

    modes = {}
    for spec in args.modes.split(","):
        if spec.strip():
            modes[spec.strip()] = parse_mode(spec)

    photos = sample_photos(args.limit)

    if not photos:
        print("нет фото с описанием — замер нечего делать")
        return 1

    print(
        f"фото: {len(photos)} · режимы: {', '.join(modes)} · "
        f"модель: {config['model']} ({config['provider']})"
    )

    # Прогрев: первый запрос к локальной модели включает загрузку (десятки
    # секунд), и без него среднее время первого режима несравнимо с остальными.
    print("прогрев модели…")
    run_mode(photos[0], {"mode": "off", "ratio": 1.0}, config)

    results: dict[str, list[dict]] = {}

    for name, mode in modes.items():
        print(f"\n--- режим {name} ---")
        runs = []

        for index, photo in enumerate(photos, start=1):
            run = run_mode(photo, mode, config)
            runs.append(run)
            mark = "ошибка" if "error" in run else "ок"
            print(f"  {index}/{len(photos)} {photo['photo_id']} — {mark}")

        results[name] = runs

    run_at = datetime.now().isoformat(timespec="seconds")
    summaries = {name: summarise(runs) for name, runs in results.items()}

    payload = {
        "run_at": run_at,
        "provider": config["provider"],
        "model": config["model"],
        "photos": len(photos),
        "limit": args.limit,
        "modes": summaries,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_report(out, payload)

    raw = out.with_name(out.stem + "_result.json")
    raw.write_text(
        json.dumps(
            {
                "run_at": run_at,
                "provider": config["provider"],
                "model": config["model"],
                "limit": args.limit,
                "modes": {
                    name: {"summary": summaries[name], "runs": results[name]}
                    for name in results
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nотчёт: {out}\nданные: {raw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
