#!/usr/bin/env python3
"""Isolated OCR/VLM benchmark for PhotoBAse.

Downloads candidate models through Ollama, runs the same prompt on a sample of
photos, and compares the parsed fields with the existing photo_qwen rows.

The benchmark is read-only for the application database:
  * the SQL transaction is explicitly READ ONLY;
  * nothing is written to photo_qwen, job_queue or any other app table;
  * the backend and frontend are not called;
  * all results go to a separate directory under data/reports/.

Typical use:
    .venv/bin/python scripts/ocr_model_benchmark.py list
    .venv/bin/python scripts/ocr_model_benchmark.py pull
    .venv/bin/python scripts/ocr_model_benchmark.py run --limit 50
    .venv/bin/python scripts/ocr_model_benchmark.py all --limit 50

Only the Python standard library and psycopg (already in the venv) are used.
"""

from __future__ import annotations

import argparse
import base64
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = Path.home() / ".config" / "scene-fingerprint.env"
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")

PROMPT = (
    "Ты анализируешь фотографию городской застройки/вывески. "
    "Верни СТРОГО JSON без пояснений со следующими ключами: "
    "description (краткое описание сцены, строка), "
    "address (видимый адрес или ориентир, строка или null), "
    "client (компания/клиент с вывески, строка или null), "
    "brand (бренд, строка или null), "
    "category (категория объекта, строка или null), "
    "tags (массив не более 10 коротких строк). "
    "Ответ должен быть коротким и полностью закрытым JSON. "
    "Если данных нет — используй null, не выдумывай."
)

# key, label, ollama reference, family, default, note
CATALOG: list[dict] = [
    {
        "key": "xiaomi-ocr-0",
        "label": "Xiaomi-OCR-0 0.8B",
        "ollama": "hf.co/prithivMLmods/Xiaomi-OCR-0-GGUF:Q4_K_M",
        "family": "OCR",
        "default": True,
        "note": "GGUF + mmproj; лучший OmniDocBench в таблице",
    },
    {
        "key": "teleocr",
        "label": "TeleOCR 1.2B",
        "ollama": "hf.co/rleo/TeleOCR-GGUF:q8_0",
        "family": "OCR",
        "default": True,
        "note": "GGUF без отдельного mmproj; зрение может не подняться",
    },
    {
        "key": "ovisocr2",
        "label": "OvisOCR2 0.8B",
        "ollama": "hf.co/Abiray/OvisOCR2-GGUF:Q4_K_M",
        "family": "OCR",
        "default": True,
        "note": "GGUF + mmproj",
    },
    {
        "key": "paddleocr-vl-1.6",
        "label": "PaddleOCR-VL-1.6 0.9B",
        "ollama": "hf.co/PaddlePaddle/PaddleOCR-VL-1.6-GGUF:latest",
        "family": "OCR",
        "default": True,
        "note": "официальный GGUF + mmproj",
    },
    {
        "key": "mineru2.5-pro",
        "label": "MinerU2.5-Pro 1.2B",
        "ollama": "hf.co/mradermacher/MinerU2.5-Pro-2605-1.2B-GGUF:Q4_K_M",
        "family": "OCR",
        "default": True,
        "note": "GGUF + mmproj",
    },
    {
        "key": "glm-ocr",
        "label": "GLM-OCR 0.9B",
        "ollama": "glm-ocr:latest",
        "family": "OCR",
        "default": True,
        "note": "официальная библиотека Ollama",
    },
    {
        "key": "qwen3.5-0.8b",
        "label": "Qwen3.5 0.8B",
        "ollama": "qwen3.5:0.8b",
        "family": "VLM",
        "default": True,
        "note": "мультимодальная, официальная библиотека",
    },
    {
        "key": "qwen3.5-2b",
        "label": "Qwen3.5 2B",
        "ollama": "qwen3.5:2b",
        "family": "VLM",
        "default": True,
        "note": "мультимодальная, официальная библиотека",
    },
    {
        "key": "qwen3.5-4b",
        "label": "Qwen3.5 4B",
        "ollama": "qwen3.5:4b",
        "family": "VLM",
        "default": True,
        "note": "мультимодальная, официальная библиотека",
    },
    {
        "key": "minicpm-v-4.5",
        "label": "MiniCPM-V 8B (4.5 GGUF нет)",
        "ollama": "minicpm-v:8b",
        "family": "VLM",
        "default": True,
        "note": "в Ollama доступна 2.6; 4.5 GGUF не опубликован",
    },
    {
        "key": "baseline-qwen3-vl-4b",
        "label": "Qwen3-VL 4B (текущая)",
        "ollama": "qwen3-vl:4b-instruct",
        "family": "baseline",
        "default": True,
        "note": "текущая модель PhotoBAse для сравнения",
    },
    # Похожие альтернативы: не входят в прогон по умолчанию.
    {
        "key": "deepseek-ocr",
        "label": "DeepSeek-OCR",
        "ollama": "hf.co/NexaAI/DeepSeek-OCR-GGUF:Q4_K_M",
        "family": "OCR alt",
        "default": False,
        "note": "сильный OCR, но тяжёлый; квант уточнить в репозитории",
    },
    {
        "key": "dots-ocr",
        "label": "dots.ocr",
        "ollama": "hf.co/ggml-org/dots.ocr-GGUF:Q4_K_M",
        "family": "OCR alt",
        "default": False,
        "note": "документный OCR",
    },
    {
        "key": "olmocr-7b",
        "label": "olmOCR 7B",
        "ollama": "hf.co/lmstudio-community/olmOCR-7B-0225-preview-GGUF:Q4_K_M",
        "family": "OCR alt",
        "default": False,
        "note": "документы/страницы, не вывески",
    },
    {
        "key": "nanonets-ocr-s",
        "label": "Nanonets-OCR-s",
        "ollama": "hf.co/Mungert/Nanonets-OCR-s-GGUF:Q4_K_M",
        "family": "OCR alt",
        "default": False,
        "note": "компактный OCR",
    },
    {
        "key": "got-ocr2",
        "label": "GOT-OCR2 0.7B",
        "ollama": "hf.co/Jerry666/GOT-OCR2_0-716M-BF16-GGUF",
        "family": "OCR alt",
        "default": False,
        "note": "старый, но лёгкий OCR",
    },
    {
        "key": "smoldocling",
        "label": "SmolDocling 256M",
        "ollama": "hf.co/Mungert/SmolDocling-256M-preview-GGUF:Q8_0",
        "family": "OCR alt",
        "default": False,
        "note": "очень лёгкий, для документов",
    },
]

BY_KEY = {item["key"]: item for item in CATALOG}
DEFAULT_KEYS = [item["key"] for item in CATALOG if item.get("default")]

# Ollama's multi-part downloader stalls on this network, while direct
# HuggingFace downloads work. These entries are fetched with urllib and
# imported with `ollama create`; the local name is what the benchmark uses.
MANUAL_PULL: dict[str, dict] = {
    "xiaomi-ocr-0": {
        "repo": "prithivMLmods/Xiaomi-OCR-0-GGUF",
        "file": "Xiaomi-OCR-0.Q4_K_M.gguf",
        "mmproj": "Xiaomi-OCR-0.mmproj-bf16.gguf",
        "local": "bench-xiaomi-ocr-0:latest",
    },
    "teleocr": {
        "repo": "rleo/TeleOCR-GGUF",
        "file": "teleocr-q8_0.gguf",
        "mmproj": None,
        "local": "bench-teleocr:latest",
    },
    "ovisocr2": {
        "repo": "Abiray/OvisOCR2-GGUF",
        "file": "OvisOCR2-Q4_K_M.gguf",
        "mmproj": "mmproj-F16.gguf",
        "local": "bench-ovisocr2:latest",
    },
    "paddleocr-vl-1.6": {
        "repo": "PaddlePaddle/PaddleOCR-VL-1.6-GGUF",
        "file": "PaddleOCR-VL-1.6-GGUF.gguf",
        "mmproj": "PaddleOCR-VL-1.6-GGUF-mmproj.gguf",
        "local": "bench-paddleocr-vl-1.6:latest",
    },
    "mineru2.5-pro": {
        "repo": "mradermacher/MinerU2.5-Pro-2605-1.2B-GGUF",
        "file": "MinerU2.5-Pro-2605-1.2B.Q4_K_M.gguf",
        "mmproj": "MinerU2.5-Pro-2605-1.2B.mmproj-f16.gguf",
        "local": "bench-mineru2.5-pro:latest",
    },
    "glm-ocr": {
        "repo": "ggml-org/GLM-OCR-GGUF",
        "file": "GLM-OCR-Q8_0.gguf",
        "mmproj": "mmproj-GLM-OCR-Q8_0.gguf",
        "local": "bench-glm-ocr:latest",
    },
    "qwen3.5-0.8b": {
        "repo": "unsloth/Qwen3.5-0.8B-GGUF",
        "file": "Qwen3.5-0.8B-Q4_K_M.gguf",
        "mmproj": "mmproj-F16.gguf",
        "local": "bench-qwen3.5-0.8b:latest",
        "renderer": "qwen3.5",
        "parser": "qwen3.5",
    },
    "qwen3.5-2b": {
        "repo": "unsloth/Qwen3.5-2B-GGUF",
        "file": "Qwen3.5-2B-Q4_K_M.gguf",
        "mmproj": "mmproj-F16.gguf",
        "local": "bench-qwen3.5-2b:latest",
        "renderer": "qwen3.5",
        "parser": "qwen3.5",
    },
    "qwen3.5-4b": {
        "repo": "unsloth/Qwen3.5-4B-GGUF",
        "file": "Qwen3.5-4B-Q4_K_M.gguf",
        "mmproj": "mmproj-F16.gguf",
        "local": "bench-qwen3.5-4b:latest",
        "renderer": "qwen3.5",
        "parser": "qwen3.5",
    },
    "minicpm-v-4.5": {
        "repo": "openbmb/MiniCPM-V-4_5-gguf",
        "file": "MiniCPM-V-4_5-Q4_K_M.gguf",
        "mmproj": "mmproj-model-f16.gguf",
        "local": "bench-minicpm-v-4.5:latest",
    },
}

FIELD_NAMES = ("client", "brand", "category")


# --------------------------------------------------------------------------- #
# Environment / database (read-only)
# --------------------------------------------------------------------------- #


def load_env(path: Path = ENV_FILE) -> None:
    """Load KEY=VALUE lines from the project env without overriding the shell."""

    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _db_params() -> dict:
    return {
        "host": os.getenv("INGEST_DB_HOST", "localhost"),
        "port": os.getenv("INGEST_DB_PORT", "5432"),
        "dbname": os.getenv("INGEST_DB_NAME", "photobase_ingest_test"),
        "user": os.getenv("INGEST_DB_USER", "lora_ingest"),
        "password": os.environ["INGEST_DB_PASSWORD"],
    }


def _norm(value: object) -> str:
    text = str(value or "").casefold().replace("ё", "е")
    text = re.sub(r"\b(ооо|оао|пао|зао|ао|ип)\b", " ", text)
    text = re.sub(r"[^\w\s]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def load_sample_crops(limit: int) -> list[dict]:
    """Read billboard crops with saved per-crop QWEN fields. Never writes."""

    import psycopg

    sql = """
        SELECT p.photo_id,
               r.region_id,
               r.crop_index,
               r.crop_path,
               r.qwen_fields
        FROM public.photo_regions AS r
        JOIN public.photos AS p ON p.photo_id = r.photo_id
        WHERE r.kind = 'billboard'
          AND r.qwen_status = 'DONE'
          AND r.qwen_fields IS NOT NULL
        ORDER BY md5(r.region_id::text)
        LIMIT %s
    """

    wanted = max(limit * 4, limit)
    rows: list[dict] = []

    with psycopg.connect(**_db_params()) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(sql, (wanted,))
            fetched = cur.fetchall()

    for photo_id, region_id, crop_index, crop_path, fields in fetched:
        path = Path(str(crop_path or ""))
        if not path.is_file():
            continue
        values = fields if isinstance(fields, dict) else {}
        rows.append(
            {
                "photo_id": str(photo_id),
                "region_id": int(region_id),
                "crop_index": int(crop_index),
                "source_path": str(path),
                "expected": {
                    "client": values.get("client"),
                    "brand": values.get("brand"),
                    "category": values.get("category"),
                    "description": values.get("description"),
                    "tags": list(values.get("tags") or []),
                },
                "regions": 1,
            }
        )
        if len(rows) >= limit:
            break

    if len(rows) < limit:
        raise SystemExit(
            f"Удалось выбрать только {len(rows)} кропов с qwen_fields "
            f"из {limit} требуемых"
        )
    return rows


def load_sample(limit: int) -> list[dict]:
    """Read a deterministic, multi-crop-heavy sample. Never writes."""

    import psycopg

    sql = """
        SELECT p.photo_id,
               p.source_path,
               q.client,
               q.brand,
               q.category,
               q.description,
               q.tags,
               (SELECT count(*) FROM public.photo_regions r
                 WHERE r.photo_id = p.photo_id AND r.kind = 'billboard') AS regions
        FROM public.photos AS p
        JOIN public.photo_qwen AS q
          ON q.photo_id = p.photo_id AND q.status = 'DONE'
        WHERE q.description IS NOT NULL
        ORDER BY regions DESC, md5(p.photo_id)
        LIMIT %s
    """

    wanted = max(limit * 4, limit)
    rows: list[dict] = []

    with psycopg.connect(**_db_params()) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute(sql, (wanted,))
            fetched = cur.fetchall()

    for row in fetched:
        photo_id, source_path, client, brand, category, description, tags, regions = row
        path = Path(str(source_path or ""))
        if not path.is_file():
            continue
        rows.append(
            {
                "photo_id": str(photo_id),
                "source_path": str(path),
                "expected": {
                    "client": client,
                    "brand": brand,
                    "category": category,
                    "description": description,
                    "tags": list(tags or []),
                },
                "regions": int(regions or 0),
            }
        )
        if len(rows) >= limit:
            break

    if len(rows) < limit:
        raise SystemExit(
            f"Удалось выбрать только {len(rows)} фото с существующими файлами "
            f"из {limit} требуемых"
        )

    return rows


# --------------------------------------------------------------------------- #
# Ollama
# --------------------------------------------------------------------------- #


def ollama_show(model: str) -> bool:
    result = subprocess.run(
        ["ollama", "show", model],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def ollama_pull(model: str) -> bool:
    print(f"  pull {model} ...", flush=True)
    started = time.perf_counter()
    result = subprocess.run(["ollama", "pull", model])
    elapsed = time.perf_counter() - started
    ok = result.returncode == 0
    print(f"  {'ok' if ok else 'FAILED'} {model} ({elapsed:.1f}s)", flush=True)
    return ok


def _post_json(model: str, image_path: str, timeout: int, use_format: bool) -> dict:
    image = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
    payload = {
        "model": model,
        "prompt": PROMPT,
        "images": [image],
        "stream": False,
        # Qwen3.5 is a thinking model; the answer must land in `response`.
        "think": False,
        "options": {"temperature": 0, "num_predict": 512},
    }
    if use_format:
        payload["format"] = "json"

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def prepare_images(sample: list[dict], out_dir: Path) -> None:
    """Downscale originals to 1280 px, like the production analysis input."""

    from PIL import Image, ImageOps

    cache_dir = out_dir / "images"
    cache_dir.mkdir(parents=True, exist_ok=True)

    for photo in sample:
        source = Path(photo["source_path"])
        key = base64.urlsafe_b64encode(
            hashlib.md5(str(source).encode()).digest()
        ).decode().rstrip("=")
        target = cache_dir / f"{key}.jpg"
        if not target.is_file():
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((1280, 1280))
                image.convert("RGB").save(target, "JPEG", quality=90)
        photo["bench_image"] = str(target)


def call_model(model: str, image_path: str, timeout: int) -> tuple[str, float]:
    started = time.perf_counter()

    try:
        data = _post_json(model, image_path, timeout, use_format=True)
    except urllib.error.HTTPError as exc:
        if exc.code not in {400, 422}:
            raise
        body = exc.read().decode("utf-8", "replace")[:500]
        try:
            # Some OCR models reject the JSON grammar; retry without it.
            data = _post_json(model, image_path, timeout, use_format=False)
        except urllib.error.HTTPError as retry_exc:
            retry_body = retry_exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"HTTP {retry_exc.code}: {retry_body or body}"
            ) from retry_exc

    elapsed = time.perf_counter() - started
    return str(data.get("response") or ""), elapsed


def _json_candidates(text: str):
    cleaned = re.sub(r"```(?:json)?", "", text or "", flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "").strip()
    yield cleaned

    start = cleaned.find("{")
    if start < 0:
        return

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                yield cleaned[start:index + 1]
                return


def parse_answer(text: str) -> dict | None:
    for candidate in _json_candidates(text):
        try:
            value = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            tags = value.get("tags")
            if isinstance(tags, str):
                tags = [item.strip() for item in tags.split(",") if item.strip()]
            elif not isinstance(tags, list):
                tags = []
            return {
                "client": value.get("client"),
                "brand": value.get("brand"),
                "category": value.get("category"),
                "description": value.get("description"),
                "tags": [str(item) for item in tags],
            }
    return None


# --------------------------------------------------------------------------- #
# Comparison
# --------------------------------------------------------------------------- #


def _field_match(expected: object, actual: object) -> bool:
    left, right = _norm(expected), _norm(actual)
    if not left and not right:
        return True
    return bool(left) and left == right


def _tag_jaccard(expected: list, actual: list) -> float:
    left = {_norm(item) for item in expected if _norm(item)}
    right = {_norm(item) for item in actual if _norm(item)}
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _similarity(expected: object, actual: object) -> float:
    left, right = _norm(expected), _norm(actual)
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return difflib.SequenceMatcher(None, left, right).ratio()


def _cyrillic_share(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for ch in letters if "а" <= ch.casefold() <= "я" or ch.casefold() == "ё") / len(letters)


def score(parsed: dict | None, expected: dict) -> dict:
    if parsed is None:
        return {
            "json_ok": False,
            "field_matches": {name: False for name in FIELD_NAMES},
            "tag_jaccard": 0.0,
            "description_similarity": 0.0,
            "cyrillic_share": 0.0,
        }

    text = " ".join(
        str(parsed.get(name) or "") for name in ("client", "brand", "description")
    ) + " " + " ".join(parsed.get("tags") or [])

    return {
        "json_ok": True,
        "field_matches": {
            name: _field_match(expected.get(name), parsed.get(name))
            for name in FIELD_NAMES
        },
        "tag_jaccard": round(_tag_jaccard(expected.get("tags") or [], parsed.get("tags") or []), 4),
        "description_similarity": round(
            _similarity(expected.get("description"), parsed.get("description")), 4
        ),
        "cyrillic_share": round(_cyrillic_share(text), 4),
    }


def summarize(records: list[dict]) -> dict:
    by_model: dict[str, list[dict]] = {}
    for record in records:
        by_model.setdefault(record["model"], []).append(record)

    summary: dict[str, dict] = {}
    for model, items in by_model.items():
        latencies = sorted(item["latency_sec"] for item in items)
        count = len(items)
        json_ok = sum(1 for item in items if item["scores"]["json_ok"])
        field_rates = {
            name: round(
                sum(1 for item in items if item["scores"]["field_matches"][name]) / count,
                4,
            )
            for name in FIELD_NAMES
        }
        summary[model] = {
            "photos": count,
            "json_ok_rate": round(json_ok / count, 4) if count else 0.0,
            "field_match": field_rates,
            "tag_jaccard": round(
                sum(item["scores"]["tag_jaccard"] for item in items) / count, 4
            ) if count else 0.0,
            "description_similarity": round(
                sum(item["scores"]["description_similarity"] for item in items) / count,
                4,
            ) if count else 0.0,
            "cyrillic_share": round(
                sum(item["scores"]["cyrillic_share"] for item in items) / count, 4
            ) if count else 0.0,
            "latency_sec": {
                "avg": round(sum(latencies) / count, 3) if count else 0.0,
                "p50": round(latencies[len(latencies) // 2], 3) if count else 0.0,
                "max": round(latencies[-1], 3) if count else 0.0,
            },
            "errors": sum(1 for item in items if item.get("error")),
        }
    return summary


def write_summary(out_dir: Path, summary: dict, sample_size: int) -> None:
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sample_photos": sample_size,
                "writes_to_app_database": False,
                "models": summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# OCR/VLM benchmark",
        "",
        f"Фото в выборке: {sample_size}. База приложения не изменялась.",
        "",
        "| Модель | JSON | client | brand | category | tags Jaccard | desc sim | кириллица | ср. сек | p50 | ошибок |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model, item in sorted(
        summary.items(), key=lambda pair: pair[1]["field_match"]["brand"], reverse=True
    ):
        lines.append(
            "| {model} | {json} | {client} | {brand} | {category} | {tags} | {desc} | {cyr} | {avg} | {p50} | {errors} |".format(
                model=model,
                json=item["json_ok_rate"],
                client=item["field_match"]["client"],
                brand=item["field_match"]["brand"],
                category=item["field_match"]["category"],
                tags=item["tag_jaccard"],
                desc=item["description_similarity"],
                cyr=item["cyrillic_share"],
                avg=item["latency_sec"]["avg"],
                p50=item["latency_sec"]["p50"],
                errors=item["errors"],
            )
        )
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def select_models(value: str | None) -> list[dict]:
    if not value:
        return [BY_KEY[key] for key in DEFAULT_KEYS]

    keys = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [key for key in keys if key not in BY_KEY]
    if unknown:
        raise SystemExit(f"Неизвестные модели: {', '.join(unknown)}")
    return [BY_KEY[key] for key in keys]


def cmd_list() -> None:
    print(f"{'key':22} {'default':8} {'family':10} ollama")
    for item in CATALOG:
        print(
            f"{item['key']:22} {str(item['default']):8} {item['family']:10} "
            f"{item['ollama']}"
        )
        print(f"{'':22} {item['note']}")


def model_name(item: dict) -> str:
    return MANUAL_PULL.get(item["key"], {}).get("local") or item["ollama"]


def _download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and target.stat().st_size > 0:
        print(f"  present {target.name}")
        return

    print(f"  download {target.name} ...", flush=True)
    temporary = target.with_suffix(target.suffix + ".part")
    started = time.perf_counter()
    last_report = 0.0

    with urllib.request.urlopen(url, timeout=120) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with temporary.open("wb") as sink:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                sink.write(chunk)
                done += len(chunk)
                now = time.perf_counter()
                if now - last_report >= 5:
                    share = f"{done / total * 100:5.1f}%" if total else "?"
                    print(f"    {share} {done / 1024 / 1024:.0f} MB", flush=True)
                    last_report = now

    temporary.replace(target)
    elapsed = time.perf_counter() - started
    size = target.stat().st_size / 1024 / 1024
    print(f"  ok {target.name} ({size:.0f} MB, {elapsed:.0f}s)", flush=True)


def create_from_hf(item: dict) -> bool:
    meta = MANUAL_PULL[item["key"]]
    target_dir = ROOT / "data" / "models" / "gguf" / item["key"]
    model_path = target_dir / meta["file"]
    base = f"https://huggingface.co/{meta['repo']}/resolve/main/"

    try:
        _download(base + meta["file"], model_path)
        mmproj_path = None
        if meta.get("mmproj"):
            mmproj_path = target_dir / meta["mmproj"]
            _download(base + meta["mmproj"], mmproj_path)

        modelfile = target_dir / "Modelfile"
        lines = [f"FROM {model_path}"]
        if mmproj_path is not None:
            lines.append(f"FROM {mmproj_path}")
        if meta.get("renderer"):
            lines.append(f"RENDERER {meta['renderer']}")
        if meta.get("parser"):
            lines.append(f"PARSER {meta['parser']}")
        lines.append("PARAMETER temperature 0")
        modelfile.write_text("\n".join(lines) + "\n", encoding="utf-8")

        local = meta["local"]
        print(f"  create {local} ...", flush=True)
        result = subprocess.run(["ollama", "create", local, "-f", str(modelfile)])
        if result.returncode != 0:
            return False
        return ollama_show(local)
    except Exception as exc:  # noqa: BLE001 - report and continue with others
        print(f"  FAILED {item['key']}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


def cmd_pull(models: list[dict]) -> int:
    failed = 0
    for item in models:
        name = model_name(item)
        if ollama_show(name):
            print(f"  already present: {name}")
            continue

        if item["key"] in MANUAL_PULL:
            ok = create_from_hf(item)
        else:
            ok = ollama_pull(item["ollama"])

        if not ok:
            failed += 1
    return failed


def cmd_run(
    models: list[dict],
    limit: int,
    out_dir: Path,
    timeout: int,
    input_kind: str = "photos",
) -> None:
    load_env()
    sample = load_sample_crops(limit) if input_kind == "crops" else load_sample(limit)
    out_dir.mkdir(parents=True, exist_ok=True)
    prepare_images(sample, out_dir)
    results_path = out_dir / "results.jsonl"

    done: set[tuple[str, str]] = set()
    if results_path.is_file():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            done.add((item.get("model"), item.get("photo_id")))

    total = len(models) * len(sample)
    finished = 0
    errors = 0

    with results_path.open("a", encoding="utf-8") as sink:
        for item in models:
            model = model_name(item)
            if not ollama_show(model):
                print(f"skip {model}: not pulled (run `pull` first)", flush=True)
                continue

            print(f"\n== {item['label']} ({model})", flush=True)
            for index, photo in enumerate(sample, start=1):
                if (model, photo["photo_id"]) in done:
                    finished += 1
                    continue

                try:
                    text, latency = call_model(model, photo["bench_image"], timeout)
                    parsed = parse_answer(text)
                    scores = score(parsed, photo["expected"])
                    error = None
                except Exception as exc:  # noqa: BLE001 - benchmark must continue
                    text = ""
                    parsed = None
                    scores = score(None, photo["expected"])
                    latency = 0.0
                    error = f"{type(exc).__name__}: {exc}"
                    errors += 1

                record = {
                    "model": model,
                    "model_key": item["key"],
                    "photo_id": photo["photo_id"],
                    "region_id": photo.get("region_id"),
                    "crop_index": photo.get("crop_index"),
                    "regions": photo["regions"],
                    "latency_sec": round(latency, 3),
                    "expected": photo["expected"],
                    "parsed": parsed,
                    "raw": text[:4000],
                    "scores": scores,
                    "error": error,
                }
                sink.write(json.dumps(record, ensure_ascii=False) + "\n")
                sink.flush()
                finished += 1

                if index % 10 == 0 or index == len(sample):
                    print(
                        f"  {index}/{len(sample)}  {latency:.1f}s  "
                        f"json={'y' if scores['json_ok'] else 'n'}  "
                        f"brand={scores['field_matches']['brand']}",
                        flush=True,
                    )

    records = [
        json.loads(line)
        for line in results_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    summary = summarize(records)
    write_summary(out_dir, summary, len(sample))

    print(f"\nГотово: {finished}/{total} прогонов, ошибок: {errors}")
    print(f"Результаты: {out_dir}")
    print(f"Сводка:    {out_dir / 'summary.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="показать каталог моделей")

    pull = sub.add_parser("pull", help="скачать модели через ollama")
    pull.add_argument("--models", help="ключи через запятую (по умолчанию core)")

    run = sub.add_parser("run", help="прогнать выборку и сравнить с photo_qwen")
    run.add_argument("--models", help="ключи через запятую (по умолчанию core)")
    run.add_argument("--limit", type=int, default=50, help="сколько фото (по умолчанию 50)")
    run.add_argument("--timeout", type=int, default=600, help="таймаут одного запроса, сек")
    run.add_argument("--input", choices=("photos", "crops"), default="photos")
    run.add_argument("--out", help="папка результатов (по умолчанию data/reports/...)")

    all_cmd = sub.add_parser("all", help="pull + run")
    all_cmd.add_argument("--models", help="ключи через запятую (по умолчанию core)")
    all_cmd.add_argument("--limit", type=int, default=50)
    all_cmd.add_argument("--timeout", type=int, default=600)
    all_cmd.add_argument("--input", choices=("photos", "crops"), default="photos")
    all_cmd.add_argument("--out")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
        return

    models = select_models(getattr(args, "models", None))

    if args.command in {"pull", "all"}:
        failed = cmd_pull(models)
        if failed:
            print(f"\nНе удалось скачать моделей: {failed}", file=sys.stderr)
        if args.command == "pull":
            return

    out_dir = Path(args.out) if getattr(args, "out", None) else (
        ROOT / "data" / "reports"
        / f"ocr_benchmark_{args.input}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    cmd_run(models, args.limit, out_dir, args.timeout, args.input)


if __name__ == "__main__":
    main()
