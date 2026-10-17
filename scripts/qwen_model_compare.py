"""Сравнение Qwen3-VL 4B и Qwen2.5-VL 7B на кропах щитов.

Один и тот же промпт, одна и та же подборка кропов, одинаковые параметры
(num_ctx=8192, num_predict=600). Пишет JSON и markdown-сводку в
data/output/qwen_model_compare/.

Запуск:
    .venv/bin/python scripts/qwen_model_compare.py --limit 20
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "data/output/qwen_model_compare"
OLLAMA = "http://127.0.0.1:11434"

DEFAULT_MODELS = ["qwen3-vl:4b-instruct", "qwen2.5vl:7b"]

PROMPT = (
    "Ты анализируешь вырезанный рекламный щит (баннер). "
    "Верни СТРОГО JSON без пояснений со следующими ключами: "
    "description (краткое описание рекламы, строка), "
    "client (компания/клиент, строка или null), "
    "brand (бренд, строка или null), "
    "category (категория рекламы, строка или null), "
    "tags (массив не более 10 коротких строк). "
    "Мелкий текст (условия акции, сроки, цены) используй для description "
    "и tags, но НЕ переписывай его дословно и не повторяй длинные строки. "
    "Ответ должен быть коротким и полностью закрытым JSON. "
    "Если данных нет — используй null, не выдумывай."
)

MAX_SIDE = 2048


def encode(path: Path) -> str:
    with Image.open(path) as image:
        image = image.convert("RGB")
        width, height = image.size
        longest = max(width, height)

        if longest > MAX_SIDE:
            scale = MAX_SIDE / longest
            image = image.resize(
                (max(1, round(width * scale)), max(1, round(height * scale))),
                Image.Resampling.LANCZOS,
            )

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)

    return base64.b64encode(buffer.getvalue()).decode("ascii")


def post(url: str, body: dict, timeout: float = 300) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def unload(model: str) -> None:
    try:
        post(
            f"{OLLAMA}/api/generate",
            {"model": model, "keep_alive": 0, "prompt": ""},
            timeout=60,
        )
    except Exception:  # noqa: BLE001
        pass


def parse_fields(content: str) -> dict | None:
    text = str(content or "").strip()

    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end <= start:
            return None

        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None


def run_model(model: str, crops: list[dict]) -> dict:
    rows = []

    for index, crop in enumerate(crops, start=1):
        started = time.perf_counter()

        try:
            payload = post(
                f"{OLLAMA}/api/chat",
                {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": PROMPT,
                            "images": [encode(Path(crop["crop_path"]))],
                        }
                    ],
                    "stream": False,
                    "format": "json",
                    "think": False,
                    "keep_alive": "10m",
                    "options": {
                        "temperature": 0,
                        "num_ctx": 8192,
                        "num_predict": 600,
                        "repeat_penalty": 1.1,
                    },
                },
            )
            elapsed = time.perf_counter() - started
            message = payload.get("message") or {}
            content = message.get("content") or ""
            fields = parse_fields(content)
            done_reason = payload.get("done_reason")

            rows.append(
                {
                    "photo_id": crop["photo_id"],
                    "seconds": round(elapsed, 2),
                    "prompt_tokens": payload.get("prompt_eval_count"),
                    "output_tokens": payload.get("eval_count"),
                    "done_reason": done_reason,
                    "parsed": fields is not None,
                    "brand": (fields or {}).get("brand"),
                    "client": (fields or {}).get("client"),
                    "has_description": bool(
                        str((fields or {}).get("description") or "").strip()
                    ),
                    "tags": len((fields or {}).get("tags") or [])
                    if isinstance((fields or {}).get("tags"), list)
                    else 0,
                    "content_chars": len(content),
                    "error": None,
                }
            )
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "photo_id": crop["photo_id"],
                    "seconds": round(time.perf_counter() - started, 2),
                    "prompt_tokens": None,
                    "output_tokens": None,
                    "done_reason": None,
                    "parsed": False,
                    "brand": None,
                    "client": None,
                    "has_description": False,
                    "tags": 0,
                    "content_chars": 0,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

        print(
            f"{model} [{index}/{len(crops)}] {crop['photo_id']}: "
            f"{rows[-1]['seconds']}s parsed={rows[-1]['parsed']} "
            f"brand={rows[-1]['brand']}",
            flush=True,
        )

    unload(model)

    parsed = [row for row in rows if row["parsed"]]
    total_seconds = sum(row["seconds"] for row in rows)

    return {
        "model": model,
        "photos": len(rows),
        "parsed": len(parsed),
        "parse_rate": round(len(parsed) / len(rows), 3) if rows else 0,
        "with_brand": sum(1 for row in parsed if row["brand"]),
        "with_client": sum(1 for row in parsed if row["client"]),
        "with_description": sum(1 for row in parsed if row["has_description"]),
        "errors": sum(1 for row in rows if row["error"]),
        "avg_seconds": round(total_seconds / len(rows), 2) if rows else 0,
        "total_seconds": round(total_seconds, 1),
        "rows": rows,
    }


def load_crops(limit: int) -> list[dict]:
    import sys

    sys.path.insert(0, str(REPO))

    from app.ingest.database import get_connection

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id, crop_path
                FROM public.photo_regions
                WHERE qwen_status = 'DONE'
                ORDER BY region_id
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    crops = []

    for photo_id, crop_path in rows:
        path = Path(crop_path)

        if path.is_file():
            crops.append({"photo_id": str(photo_id), "crop_path": str(path)})

    return crops


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS))
    args = parser.parse_args()

    models = [item.strip() for item in args.models.split(",") if item.strip()]
    crops = load_crops(args.limit)

    if not crops:
        raise SystemExit("no crops found")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [run_model(model, crops) for model in models]

    stamp = time.strftime("%Y%m%d_%H%M%S")
    (OUT_DIR / f"compare_{stamp}.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1)
    )

    lines = [
        "# Сравнение моделей QWEN",
        "",
        f"Кропов: {len(crops)} · параметры: num_ctx=8192, num_predict=600",
        "",
        "| Модель | JSON OK | Бренд | Клиент | Описание | Ошибки | Ср. сек |",
        "|---|---|---|---|---|---|---|",
    ]

    for item in results:
        lines.append(
            f"| {item['model']} | {item['parsed']}/{item['photos']} | "
            f"{item['with_brand']} | {item['with_client']} | "
            f"{item['with_description']} | {item['errors']} | "
            f"{item['avg_seconds']} |"
        )

    report = "\n".join(lines) + "\n"
    (OUT_DIR / f"compare_{stamp}.md").write_text(report)
    print("\n" + report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
