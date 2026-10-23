#!/usr/bin/env python
"""
Замерный стенд: кропы двух щитов и варианты их сжатия.

Зачем. У части фото детектор находит два щита рядом. Сейчас QWEN читает
каждый кроп отдельно, а итоговые поля client/brand/category берутся с самого
крупного щита; второй остаётся только в tags/description. Кроме того, кропы
хранятся в q95 до 2048 px — нужно понять, не достаточно ли q90 или 1280 px.

Что делает стенд. Ничего не пишет в базу и не меняет исходники:
1. Берёт N фото, у которых на диске лежат два кропа.
2. Для каждого кропа делает варианты: исходный (2048/q95), 2048/q90,
   1280/q90 — во временном каталоге.
3. Прогоняет QWEN по каждому варианту и сравнивает client/brand/category с
   исходным кропом этого же фото (эталон — свежее чтение в этом запуске,
   не «правильный ответ»).
4. Отдельно проверяет два способа увидеть оба щита: два отдельных запроса
   (как сейчас) и оба изображения в одном запросе с общим промптом и с
   промптом-массивом `banners`.

Запуск (локальная модель, наружу ничего не уходит):
    python scripts/qwen_multicrop_stand.py --limit 10
    python scripts/qwen_multicrop_stand.py --limit 10 --variants 2048q95,1280q90

Отчёт: docs/qwen_multicrop_experiment.md и
docs/qwen_multicrop_experiment_result.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app.billboard.pipeline import BILLBOARD_PROMPT, CROPS_ROOT  # noqa: E402
from app.qwen import processor as qwen  # noqa: E402
from app.refine.logic import skeleton  # noqa: E402

FIELDS = ("client", "brand", "category")
BANNERS_PROMPT = (
    "На изображениях — рекламные щиты. Их может быть один или несколько, "
    "и они могут рекламировать разные компании. Верни СТРОГО JSON без "
    "пояснений: {\"banners\": [{\"description\": \"краткое описание\", "
    "\"client\": \"компания или null\", \"brand\": \"бренд или null\", "
    "\"category\": \"категория или null\", \"tags\": [\"до 10 коротких строк\"]}]}. "
    "Для каждого ЩИТА — отдельный объект; не объединяй разные щиты в один. "
    "Если щит один — массив из одного объекта. Мелкий текст используй в "
    "description и tags, дословно не переписывай. Не выдумывай данные."
)

# (ключ, max_side, quality); None = оставить исходный файл как есть.
VARIANTS = {
    "2048q95": (2048, 95),
    "2048q90": (2048, 90),
    "1280q90": (1280, 90),
}


def sample_photos(limit: int, photo_ids: list[str] | None = None) -> list[dict]:
    """
    Фото, у которых на диске лежат два кропа.

    Сохранённые ответы по кропам не используем: кропы живут ограниченное
    время и у части фото уже удалены. Эталоном для сравнения вариантов
    становится свежий прогон исходного кропа в этом же запуске.

    *photo_ids* ограничивает выборку конкретными фото (например, найденными
    по имени файла в одном адресе); порядок сохраняется.
    """

    root = CROPS_ROOT
    photos: list[dict] = []

    candidates = (
        [root / photo_id for photo_id in photo_ids]
        if photo_ids
        else sorted(root.iterdir()) if root.is_dir() else []
    )

    for directory in candidates:
        if not directory.is_dir():
            continue

        files = sorted(directory.glob("crop_*.jpg"))

        if len(files) < 2:
            continue

        photos.append(
            {
                "photo_id": directory.name,
                "crops": [str(path) for path in files[:2]],
            }
        )

        if len(photos) >= limit:
            break

    return photos


def make_variant(source: Path, target: Path, max_side: int, quality: int) -> Path:
    """Перекодировать кроп; исходник не трогаем."""

    with Image.open(source) as image:
        image = image.convert("RGB")
        width, height = image.size
        longest = max(width, height)

        if longest > max_side:
            scale = max_side / longest
            image = image.resize(
                (max(1, round(width * scale)), max(1, round(height * scale))),
                Image.Resampling.LANCZOS,
            )

        image.save(target, format="JPEG", quality=quality)

    return target


def contains(haystack: dict, value: object) -> bool:
    """Есть ли значение в полях/тегах/описании (с нормализацией имён)."""

    needle = skeleton(str(value or ""))

    if not needle:
        return False

    text = " ".join(
        [
            str(haystack.get("description") or ""),
            " ".join(str(tag) for tag in haystack.get("tags") or []),
            *(str(haystack.get(field) or "") for field in FIELDS),
        ]
    )

    return needle in skeleton(text)


def analyze_multi(paths: list[Path], config: dict, prompt: str, max_tokens: int):
    """Один запрос Ollama с несколькими изображениями."""

    images = [
        qwen.encode_image(
            str(path),
            max_side=int(config.get("max_image_side", 2048)),
        )
        for path in paths
    ]

    body = json.dumps(
        {
            "model": config["model"],
            "messages": [
                {"role": "user", "content": prompt, "images": images}
            ],
            "stream": False,
            "format": "json",
            "think": False,
            "keep_alive": config.get("keep_alive", "5m"),
            "options": {
                "temperature": 0,
                "num_predict": max_tokens,
                "repeat_penalty": 1.1,
            },
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        f"{config['ollama_url']}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    started = time.perf_counter()
    payload = qwen._post_json(request, config["timeout"])  # noqa: SLF001
    elapsed = time.perf_counter() - started

    content = (payload.get("message") or {}).get("content") or ""
    match = re.search(r"\{.*\}", content, re.S)

    if not match:
        return {}, payload, elapsed

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}, payload, elapsed

    return (data if isinstance(data, dict) else {}), payload, elapsed


def banners_of(fields: dict) -> list[dict]:
    return [item for item in fields.get("banners") or [] if isinstance(item, dict)]


def run_one(
    photo: dict,
    workdir: Path,
    variants: list[str],
    config: dict,
    *,
    repeat_baseline: bool = False,
) -> dict:
    report: dict = {"photo_id": photo["photo_id"], "crops": {}, "modes": {}}

    crop_paths: list[Path] = []
    references: list[dict] = []

    for index, source in enumerate(photo["crops"]):
        source_path = Path(source)

        # Эталон: свежее чтение исходного кропа в этом же запуске.
        reference, base_raw, base_time = qwen.analyze_image(
            str(source_path), config=config
        )
        references.append(reference)

        results = {
            "2048q95": {
                "fields": reference,
                "matched": {
                    field: True
                    for field in FIELDS
                    if (reference.get(field) or "").strip()
                },
                "time_sec": round(base_time, 2),
                "prompt_tokens": base_raw.get("prompt_eval_count"),
                "eval_count": base_raw.get("eval_count"),
            }
        }

        # Повтор исходного кропа: оценивает собственную вариативность модели,
        # иначе любое расхождение варианта легко принять за потерю от сжатия.
        if repeat_baseline:
            again, again_raw, again_time = qwen.analyze_image(
                str(source_path), config=config
            )
            results["2048q95_again"] = {
                "fields": again,
                "matched": {
                    field: contains(again, reference.get(field))
                    for field in FIELDS
                    if (reference.get(field) or "").strip()
                },
                "time_sec": round(again_time, 2),
                "prompt_tokens": again_raw.get("prompt_eval_count"),
                "eval_count": again_raw.get("eval_count"),
            }

        for name in variants:
            if name == "2048q95":
                continue

            max_side, quality = VARIANTS[name]
            target = workdir / f"{photo['photo_id']}_c{index + 1}_{name}.jpg"
            path = make_variant(source_path, target, max_side, quality)
            fields, raw, elapsed = qwen.analyze_image(str(path), config=config)
            results[name] = {
                "fields": fields,
                "matched": {
                    field: contains(fields, reference.get(field))
                    for field in FIELDS
                    if (reference.get(field) or "").strip()
                },
                "time_sec": round(elapsed, 2),
                "prompt_tokens": raw.get("prompt_eval_count"),
                "eval_count": raw.get("eval_count"),
            }

        report["crops"][f"crop_{index + 1}"] = {
            "reference": {field: reference.get(field) for field in FIELDS},
            "variants": results,
        }
        crop_paths.append(source_path)

    if len(references) > 1:
        second = references[1]
        first = references[0]
        report["second_banner_differs"] = bool(
            any((second.get(field) or "").strip() for field in ("client", "brand"))
            and skeleton(second.get("brand") or second.get("client"))
            != skeleton(first.get("brand") or first.get("client"))
        )

    # Оба щита в одном запросе: общий промпт и промпт-массив.
    for mode, prompt, limit in (
        ("combined_flat", BILLBOARD_PROMPT, 768),
        ("combined_banners", BANNERS_PROMPT, 1024),
    ):
        data, raw, elapsed = analyze_multi(crop_paths, config, prompt, limit)

        if mode == "combined_banners":
            banners = banners_of(data)
            fields = data
        else:
            try:
                fields = qwen.parse_result(data)
            except Exception:  # noqa: BLE001
                fields = {}
            banners = [fields]

        found = {
            f"crop_{i + 1}": {
                field: any(contains(banner, references[i].get(field)) for banner in banners)
                for field in FIELDS
                if (references[i].get(field) or "").strip()
            }
            for i in range(len(crop_paths))
        }
        report["modes"][mode] = {
            "fields": fields,
            "banners": len(banners),
            "matched": found,
            "time_sec": round(elapsed, 2),
            "prompt_tokens": raw.get("prompt_eval_count"),
            "eval_count": raw.get("eval_count"),
        }

    return report


def summarise(reports: list[dict], variants: list[str]) -> dict:
    """Сколько эталонных значений уцелело в каждом варианте/режиме."""

    totals: dict[str, dict[str, int]] = {}

    def tally(bucket: str, matched: dict, per_crop: bool = False):
        stats = totals.setdefault(bucket, {"checked": 0, "matched": 0})

        for value in matched.values():
            stats["checked"] += 1
            stats["matched"] += int(bool(value))

    for report in reports:
        for crop_name, crop in report["crops"].items():
            for name in crop["variants"]:
                tally(f"{name}", crop["variants"][name]["matched"], True)

        for mode, data in report["modes"].items():
            for crop_name, matched in data["matched"].items():
                tally(mode, matched)

    for bucket, stats in totals.items():
        stats["rate"] = (
            round(stats["matched"] / stats["checked"], 3) if stats["checked"] else None
        )

    return totals


def write_report(report: dict, path_md: Path, path_json: Path) -> None:
    path_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")

    lines = [
        "# Стенд: кропы двух щитов и сжатие",
        "",
        f"Фото: {report['photos']} · второй щит отличается: "
        f"{report['second_banner_differs']} · модель: `{report['model']}` · "
        f"варианты: {', '.join(report['variants'])}",
        "",
        "Эталон — свежее чтение исходного кропа в этом же запуске; "
        "проверяется, осталось ли значение в ответе варианта. Строка "
        "`2048q95_again`, если она есть, — повтор без сжатия: её доля "
        "показывает собственную вариативность модели.",
        "",
        "| Вариант/режим | Совпало | Проверено | Доля |",
        "|---|---:|---:|---:|",
    ]

    for bucket, stats in report["summary"].items():
        lines.append(
            f"| {bucket} | {stats['matched']} | {stats['checked']} | "
            f"{stats['rate'] if stats['rate'] is not None else '—'} |"
        )

    details = []

    for item in report["details"]:
        details.append(f"\n## {item['photo_id']}\n")

        for crop_name, crop in item["crops"].items():
            reference = ", ".join(
                f"{k}={v!r}" for k, v in crop["reference"].items() if v
            )
            details.append(f"- **{crop_name}**: {reference}")

            for name, data in crop["variants"].items():
                matched = ", ".join(
                    f"{k}={'да' if v else 'НЕТ'}"
                    for k, v in data["matched"].items()
                )
                details.append(
                    f"  - {name}: {matched}; {data['time_sec']} с, "
                    f"tokens={data['eval_count']}"
                )

        for mode, data in item["modes"].items():
            details.append(
                f"- **{mode}**: базирующихся щитов {data['banners']}; "
                f"{data['time_sec']} с, tokens={data['eval_count']}"
            )

            for crop_name, matched in data["matched"].items():
                text = ", ".join(
                    f"{k}={'да' if v else 'НЕТ'}" for k, v in matched.items()
                )
                details.append(f"  - {crop_name}: {text}")

    path_md.write_text("\n".join(lines + details) + "\n", "utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--photo-ids",
        default=None,
        help="через запятую: только эти фото (иначе — первые с двумя кропами)",
    )
    parser.add_argument(
        "--variants",
        default=",".join(VARIANTS),
        help="через запятую: 2048q95,2048q90,1280q90",
    )
    parser.add_argument(
        "--repeat-baseline",
        action="store_true",
        help="повторить исходный кроп, чтобы измерить вариативность модели",
    )
    parser.add_argument(
        "--md",
        default=str(ROOT / "docs" / "qwen_multicrop_experiment.md"),
    )
    parser.add_argument(
        "--json",
        default=str(ROOT / "docs" / "qwen_multicrop_experiment_result.json"),
    )
    args = parser.parse_args(argv)

    variants = [item.strip() for item in args.variants.split(",") if item.strip()]
    unknown = [item for item in variants if item not in VARIANTS]

    if unknown:
        raise SystemExit(f"неизвестные варианты: {', '.join(unknown)}")

    photo_ids = (
        [item.strip() for item in args.photo_ids.split(",") if item.strip()]
        if args.photo_ids
        else None
    )
    photos = sample_photos(args.limit, photo_ids)

    if not photos:
        raise SystemExit("нет фото с двумя кропами и разными брендами")

    config = qwen.resolve_settings()
    config = {
        **config,
        "prompt": BILLBOARD_PROMPT,
        "crop": {"mode": "off", "ratio": 1.0},
        "max_image_side": 2048,
        "max_output_tokens": 768,
        "repeat_penalty": 1.1,
    }

    reports = []

    with tempfile.TemporaryDirectory(prefix="qwen-crops-") as tmp:
        workdir = Path(tmp)

        for index, photo in enumerate(photos, start=1):
            print(f"[{index}/{len(photos)}] {photo['photo_id']}", flush=True)
            reports.append(
                run_one(
                    photo,
                    workdir,
                    variants,
                    config,
                    repeat_baseline=args.repeat_baseline,
                )
            )

    result = {
        "photos": len(reports),
        "second_banner_differs": sum(
            1 for item in reports if item.get("second_banner_differs")
        ),
        "model": config["model"],
        "variants": variants,
        "summary": summarise(reports, variants),
        "details": reports,
    }

    write_report(
        result,
        Path(args.md),
        Path(args.json),
    )

    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"\nОтчёт: {args.md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
