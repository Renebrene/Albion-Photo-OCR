#!/usr/bin/env python3
"""
Сравнение облачных VLM на кропах рекламных щитов — независимо от стенда.

Скрипт не трогает PostgreSQL, очередь и рабочие настройки: он читает
manifest.json (см. scripts/cloud_vlm_crops.py), отправляет каждый кроп в
OpenAI-совместимый /chat/completions и записывает латентность, токены и
стоимость в отдельный каталог.

Ключ и адрес передаются аргументами или переменными окружения:
    CLOUD_VLM_BASE_URL, CLOUD_VLM_API_KEY

Пример:
    python scripts/cloud_vlm_bench.py \\
        --manifest /tmp/cloud_vlm_sample/manifest.json \\
        --models ling-3.0-flash-vl,qwen3.8-flash,gemini-2.5-flash-lite

Стоимость берётся из публичного прайса bothub (/api/v1/pricing/models);
для другого провайдера передайте свой JSON через --pricing или отключите
расчёт через --no-pricing.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PRICING_URL = "https://bothub.ru/api/v1/pricing/models"

# Тот же промпт, что в рабочем пайплайне для кропа щита.
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

DEFAULT_MODELS = (
    "ling-3.0-flash-vl,ling-3.0-flash,gemini-2.5-flash-lite,"
    "gpt-5-nano,gpt-4.1-nano,mistral-small-3.2-24b-instruct,"
    "qwen3.8-flash,deepseek-v4-flash-vision-exp,nemotron-3.5-super-vl,"
    "gemma-4-31b-it"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default="/tmp/cloud_vlm_sample/manifest.json",
        help="manifest.json из scripts/cloud_vlm_crops.py",
    )
    parser.add_argument(
        "--models",
        default=os.getenv("CLOUD_VLM_MODELS", DEFAULT_MODELS),
        help="список моделей через запятую",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("CLOUD_VLM_BASE_URL", ""),
        help="OpenAI-совместимый base URL (…/v1)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("CLOUD_VLM_API_KEY", ""),
        help="API key (по умолчанию из CLOUD_VLM_API_KEY)",
    )
    parser.add_argument("--pricing", default="", help="локальный JSON с ценами")
    parser.add_argument(
        "--no-pricing",
        action="store_true",
        help="не считать деньги (токены и время всё равно запишутся)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=768,
        help="лимит ответа (как у кропа в рабочем пайплайне)",
    )
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument(
        "--limit-images",
        type=int,
        default=0,
        help="взять только первые N кропов",
    )
    parser.add_argument(
        "--out",
        default="",
        help="каталог результата (по умолчанию data/output/cloud_vlm_bench/<ts>)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ничего не отправлять: показать план и цены",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items") or []
    return [
        item
        for item in items
        if item.get("crop") and Path(item["crop"]).is_file()
    ]


def load_pricing(path: str) -> dict[str, dict]:
    if path:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        with urllib.request.urlopen(PRICING_URL, timeout=30) as response:
            raw = json.loads(response.read().decode("utf-8"))

    prices: dict[str, dict] = {}

    for model in raw.get("models", []):
        entry = {"features": model.get("features") or [], "plan": model.get("allowedPlanType")}
        for price in model.get("prices", []):
            if price.get("key") in ("input", "output"):
                entry[price["key"]] = {
                    "usd": float(price.get("usd") or 0.0),
                    "rub": float(price.get("rub") or 0.0),
                }
        if "input" in entry or "output" in entry:
            prices[model["id"]] = entry

    return prices


def call_model(
    *,
    base_url: str,
    api_key: str,
    model: str,
    image_b64: str,
    prompt: str,
    max_tokens: int,
    timeout: float,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                    },
                ],
            }
        ],
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = base_url.rstrip("/") + "/chat/completions"
    started = time.perf_counter()
    attempt = 0
    response_data = None

    while True:
        attempt += 1
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response_data = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            elapsed = time.perf_counter() - started

            # Совместимость: новые OpenAI-модели не принимают max_tokens и
            # часть провайдеров не умеет response_format.
            if exc.code == 400 and "max_completion_tokens" in body:
                payload["max_completion_tokens"] = payload.pop("max_tokens")
                continue
            if exc.code == 400 and "max_tokens" in body and "max_tokens" in payload:
                payload.pop("max_tokens", None)
                continue
            if exc.code == 400 and "response_format" in body:
                payload.pop("response_format", None)
                continue
            if exc.code == 429 and attempt <= 3:
                time.sleep(5 * attempt)
                continue

            return {
                "ok": False,
                "status": exc.code,
                "error": body[:800],
                "elapsed": elapsed,
            }
        except Exception as exc:  # noqa: BLE001 - сеть/таймаут: записываем как есть
            return {
                "ok": False,
                "status": None,
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed": time.perf_counter() - started,
            }

    elapsed = time.perf_counter() - started
    choices = response_data.get("choices") or [{}]
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    usage = response_data.get("usage") or {}

    return {
        "ok": True,
        "status": 200,
        "elapsed": elapsed,
        "content": content,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
    }


def parse_json(content: str) -> tuple[bool, dict | None]:
    text = content.strip()

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return False, None

    return isinstance(value, dict), value if isinstance(value, dict) else None


def cost_of(usage: dict, price: dict) -> tuple[float | None, float | None]:
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")

    if prompt is None or completion is None:
        return None, None
    if "input" not in price or "output" not in price:
        return None, None

    usd = (
        prompt / 1_000_000 * price["input"]["usd"]
        + completion / 1_000_000 * price["output"]["usd"]
    )
    rub = (
        prompt / 1_000_000 * price["input"]["rub"]
        + completion / 1_000_000 * price["output"]["rub"]
    )
    return usd, rub


def p95(values: list[float]) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(0.95 * len(ordered)) - 1))
    return ordered[index]


def main() -> int:
    args = parse_args()

    manifest_path = Path(args.manifest)
    items = load_manifest(manifest_path)

    if args.limit_images:
        items = items[: args.limit_images]

    if not items:
        raise SystemExit(f"в манифесте нет кропов: {manifest_path}")

    models = [item.strip() for item in args.models.split(",") if item.strip()]

    if not models:
        raise SystemExit("не заданы модели")

    prices = {} if args.no_pricing else load_pricing(args.pricing)

    if not args.no_pricing and not prices:
        print("прайс пуст: стоимость не посчитается", file=sys.stderr)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out or f"data/output/cloud_vlm_bench/{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"кропов: {len(items)}, моделей: {len(models)}, вывод: {out_dir}")

    if args.dry_run:
        for model in models:
            price = prices.get(model) or {}
            input_price = price.get("input", {}).get("usd", "—")
            output_price = price.get("output", {}).get("usd", "—")
            print(f"  {model:40} in ${input_price} out ${output_price} /1M")
        print(f"dry-run: будет {len(items) * len(models)} запросов")
        return 0

    if not args.base_url:
        raise SystemExit("не задан --base-url (или CLOUD_VLM_BASE_URL)")

    results_path = out_dir / "results.jsonl"
    summary: dict[str, dict] = {model: {"latencies": [], "prompt": [], "completion": [], "usd": [], "rub": [], "ok": 0, "failed": 0, "valid": 0} for model in models}

    with results_path.open("w", encoding="utf-8") as sink:
        for model in models:
            price = prices.get(model) or {}

            for item in items:
                image_path = Path(item["crop"])
                image_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")

                result = call_model(
                    base_url=args.base_url,
                    api_key=args.api_key,
                    model=model,
                    image_b64=image_b64,
                    prompt=PROMPT,
                    max_tokens=args.max_tokens,
                    timeout=args.timeout,
                )

                record = {
                    "model": model,
                    "crop": item["crop"],
                    "index": item.get("index"),
                    "billboard": item.get("billboard"),
                    **result,
                }

                if result["ok"]:
                    valid, parsed = parse_json(result.get("content", ""))
                    usd, rub = cost_of(result.get("usage") or {}, price)
                    record["json_valid"] = valid
                    record["parsed"] = parsed
                    record["cost_usd"] = usd
                    record["cost_rub"] = rub

                    bucket = summary[model]
                    bucket["ok"] += 1
                    bucket["valid"] += int(valid)
                    bucket["latencies"].append(result["elapsed"])
                    if result["usage"].get("prompt_tokens") is not None:
                        bucket["prompt"].append(result["usage"]["prompt_tokens"])
                    if result["usage"].get("completion_tokens") is not None:
                        bucket["completion"].append(result["usage"]["completion_tokens"])
                    if usd is not None:
                        bucket["usd"].append(usd)
                    if rub is not None:
                        bucket["rub"].append(rub)
                else:
                    summary[model]["failed"] += 1

                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                status = "OK" if result["ok"] else f"FAIL {result.get('status')}"
                print(
                    f"{model:40} {item.get('index') or '?':>2} "
                    f"{result['elapsed']:6.2f} s  {status}",
                    flush=True,
                )

    markdown = ["# Сравнение облачных VLM на кропах", ""]
    markdown.append(f"- Кропов: {len(items)}")
    markdown.append(f"- Моделей: {len(models)}")
    markdown.append(f"- Промпт: рабочий промпт кропа, ответ ≤ {args.max_tokens} токенов")
    markdown.append(f"- Стоимость: прайс bothub, RUB и USD за 1M токенов")
    markdown.append("")
    markdown.append(
        "| модель | in $/1M | out $/1M | ok | ср. с | p95 с | in ток. | out ток. | 10 кропов, ₽ | 1000 фото, ₽ | JSON |"
    )
    markdown.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for model in models:
        bucket = summary[model]
        price = prices.get(model) or {}
        in_price = price.get("input", {}).get("usd")
        out_price = price.get("output", {}).get("usd")
        count = len(bucket["latencies"])
        avg_latency = statistics.mean(bucket["latencies"]) if count else 0.0
        avg_prompt = statistics.mean(bucket["prompt"]) if bucket["prompt"] else 0.0
        avg_completion = statistics.mean(bucket["completion"]) if bucket["completion"] else 0.0
        total_rub = sum(bucket["rub"]) if bucket["rub"] else None
        per_1000 = (
            (sum(bucket["rub"]) / count * 1000) if count and bucket["rub"] else None
        )
        valid_pct = (bucket["valid"] / count * 100) if count else 0.0

        markdown.append(
            "| {model} | {inp} | {out} | {ok} | {lat:.2f} | {p95:.2f} | {pt:.0f} | {ct:.0f} | {rub} | {k} | {jsonpct:.0f}% |".format(
                model=model,
                inp=f"{in_price:.3f}" if in_price is not None else "—",
                out=f"{out_price:.3f}" if out_price is not None else "—",
                ok=f"{bucket['ok']}/{bucket['ok'] + bucket['failed']}",
                lat=avg_latency,
                p95=p95(bucket["latencies"]),
                pt=avg_prompt,
                ct=avg_completion,
                rub=f"{total_rub:.4f}" if total_rub is not None else "—",
                k=f"{per_1000:.2f}" if per_1000 is not None else "—",
                jsonpct=valid_pct,
            )
        )

    markdown.append("")
    markdown.append("Сырые ответы — `results.jsonl` в этом же каталоге.")

    (out_dir / "summary.md").write_text("\n".join(markdown), encoding="utf-8")
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "items": len(items),
                "models": {
                    model: {
                        "ok": summary[model]["ok"],
                        "failed": summary[model]["failed"],
                        "avg_latency": statistics.mean(summary[model]["latencies"])
                        if summary[model]["latencies"]
                        else None,
                        "p95_latency": p95(summary[model]["latencies"]),
                        "avg_prompt_tokens": statistics.mean(summary[model]["prompt"])
                        if summary[model]["prompt"]
                        else None,
                        "avg_completion_tokens": statistics.mean(summary[model]["completion"])
                        if summary[model]["completion"]
                        else None,
                        "total_cost_rub": sum(summary[model]["rub"])
                        if summary[model]["rub"]
                        else None,
                    }
                    for model in models
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n" + "\n".join(markdown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
