```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > scripts/benchmark_client_models_25.py <<'PY'
#!/usr/bin/env python3

import argparse
import csv
import json
import subprocess
import time
from pathlib import Path

import psycopg2
import requests

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

MODELS = [
    "qwen3:4b",
    "qwen3:8b",
    "qwen2.5:7b",
]

SYSTEM_PROMPT = """
Ты нормализуешь названия клиентов для фотобазы.

Твоя задача:
- получить исходное название;
- выбрать клиента ТОЛЬКО из переданного справочника;
- исправлять очевидные опечатки;
- исправлять OCR-ошибки;
- учитывать регистр;
- учитывать пробелы;
- учитывать небольшие перестановки и искажения букв;
- учитывать очевидные варианты написания;
- НЕ придумывать нового клиента;
- НЕ выбирать клиента только потому, что он семантически похож;
- если уверенности недостаточно — вернуть null.

Примеры:
"Яндеск" -> "Яндекс"
"яндекс" -> "Яндекс"
"сбер" -> "Сбер"
"Тетн" -> "Тенет"
"Тенит" -> "Тенет"
"h h" -> "hh"

Верни ТОЛЬКО JSON:

{
  "client": "название из справочника или null",
  "confidence": 0.0,
  "reason": "краткое объяснение"
}

confidence от 0 до 1.
""".strip()

def get_connection():
    return psycopg2.connect(**PG_CONFIG)

def load_test_data(limit):
    with get_connection() as conn:
        with conn.cursor() as cur:

            # ----------------------------------------------------
            # DIRECTORY
            # ----------------------------------------------------

            cur.execute("""
                SELECT
                    id,
                    name
                FROM client_directory
                WHERE active = TRUE
                ORDER BY sort_order, name
            """)

            directory = cur.fetchall()

            names = [
                row[1]
                for row in directory
                if row[1]
            ]

            # ----------------------------------------------------
            # UNKNOWN RAW CLIENTS
            # ----------------------------------------------------

            cur.execute("""
                SELECT
                    TRIM(p.client) AS raw_name,
                    COUNT(*) AS photo_count
                FROM photos p

                WHERE
                    p.client IS NOT NULL
                    AND TRIM(p.client) <> ''

                    -- exact directory match is already known
                    AND NOT EXISTS (
                        SELECT 1
                        FROM client_directory cd
                        WHERE
                            cd.active = TRUE
                            AND LOWER(TRIM(cd.name))
                                = LOWER(TRIM(p.client))
                    )

                    -- known alias is already normalized
                    AND NOT EXISTS (
                        SELECT 1
                        FROM client_aliases ca
                        JOIN client_directory cd
                          ON cd.id = ca.client_id
                        WHERE
                            cd.active = TRUE
                            AND LOWER(TRIM(ca.raw_name))
                                = LOWER(TRIM(p.client))
                    )

                GROUP BY TRIM(p.client)

                ORDER BY
                    COUNT(*) DESC,
                    TRIM(p.client)

                LIMIT %s
            """, (limit,))

            unknown = cur.fetchall()

    return names, unknown

def unload_model(model):
    print()
    print("------------------------------------------------------------")
    print(f"UNLOAD: {model}")
    print("------------------------------------------------------------")

    try:
        subprocess.run(
            ["ollama", "stop", model],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except Exception as exc:
        print(f"[OLLAMA STOP ERROR] {repr(exc)}")

    # Проверяем, действительно ли модель выгружена
    time.sleep(2)
    result = subprocess.run(
        ["ollama", "list"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    if model in result.stdout:
        print(f"[WARNING] Model {model} still running after stop")
    else:
        print(f"[INFO] Model {model} successfully unloaded")

    # Проверяем VRAM
    result = subprocess.run(
        ["nvidia-smi", "-q", "-d", "MEMORY"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:
        print("[ERROR] Failed to check VRAM")
    else:
        print(result.stdout)

    # Небольшая пауза, чтобы VRAM действительно освободилась.
    time.sleep(3)

def ask_qwen(raw_name, directory_names, model):

    client_lines = "\n".join(
        f"- {name}"
        for name in directory_names
    )

    user_prompt = f"""
СПРАВОЧНИК ДОПУСТИМЫХ КЛИЕНТОВ:

{client_lines}

ИСХОДНОЕ НАЗВАНИЕ:

{raw_name}

Выбери клиента из справочника либо null.
""".strip()

    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
        },
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    }

    started = time.perf_counter()

    try:
        response = requests.post(
            OLLLA_URL,
            json=payload,
            timeout=180,
        )
    except requests.exceptions.RequestException as exc:
        print(f"[ERROR] Request failed: {exc}")
        return {
            "client": None,
            "confidence": 0.0,
            "reason": f"Request failed: {exc}",
            "seconds": 0,
        }

    response.raise_for_status()

    elapsed = time.perf_counter() - started

    data = response.json()

    content = (
        data
        .get("message", {})
        .get("content", "")
        .strip()
    )

    try:
        result = json.loads(content)
    except Exception:
        result = {
            "client": None,
            "confidence": 0,
            "reason": "invalid JSON",
        }

    client = result.get("client")

    # ------------------------------------------------------------
    # HARD SAFETY:
    # модель имеет право выбрать только реальный directory name.
    # ------------------------------------------------------------

    if client not in directory_names:
        client = None

    try:
        confidence = float(
            result.get("confidence", 0) or 0
        )
    except Exception:
        confidence = 0.0

    reason = result.get(
        "reason",
        "",
    )

    return {
        "client": client,
        "confidence": confidence,
        "reason": reason,
        "seconds": elapsed,
    }

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=25,
    )

    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.80,
    )

    parser.add_argument(
        "--out",
        default="data/client_model_benchmark_25.csv",
    )

    args = parser.parse_args()

    # ============================================================
    # LOAD TEST SET
    # ============================================================

    directory_names, unknown = load_test_data(
        args.limit
    )

    print("=" * 70)
    print("CLIENT NORMALIZER BENCHMARK")
    print("=" * 70)

    print()
    print("DIRECTORY:")
    for name in directory_names:
        print("  ", name)

    print()
    print("TEST SET:", len(unknown))
    print()

    for index, (raw, count) in enumerate(
        unknown,
        1,
    ):
        print(
            f"{index:02d}. "
            f"{count:3d}  "
            f"{raw!r}"
        )

    # ============================================================
    # RESULTS
    # ============================================================

    results = []

    # ============================================================
    # MODELS — STRICTLY SEQUENTIAL
    # ============================================================

    for model_index, model in enumerate(
        MODELS,
        1,
    ):

        print()
        print("=" * 70)
        print(
            f"MODEL {model_index}/{len(MODELS)}: "
            f"{model}"
        )
        print("=" * 70)

        # Important:
        # перед началом каждой модели стараемся убрать
        # предыдущую модель из памяти.
        unload_model(model)

        # Проверяем, установлена ли модель
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if model not in result.stdout:
            print(f"[WARNING] Model {model} not installed")
            continue

        for index, (raw, photo_count) in enumerate(
            unknown,
            1,
        ):

            try:

                result = ask_qwen(
                    raw,
                    directory_names,
                    model,
                )

                client = result["client"]
                confidence = result["confidence"]

                accepted = (
                    client
                    if confidence >= args.min_confidence
                    else None
                )

                print(
                    f"[{index:02d}/{len(unknown)}] "
                    f"{raw!r:45} "
                    f"-> {accepted!r:18} "
                    f"conf={confidence:.2f} "
                    f"time={result['seconds']:.1f}s"
                )

                results.append({
                    "raw": raw,
                    "photos": photo_count,
                    "model": model,
                    "client": accepted or "",
                    "confidence": f"{confidence:.3f}",
                    "seconds": f"{result['seconds']:.2f}",
                    "reason": result["reason"],
                })

            except Exception as exc:

                print(
                    f"[{index:02d}/{len(unknown)}] "
                    f"{raw!r:45} "
                    f"-> ERROR: {exc}"
                )

                results.append({
                    "raw": raw,
                    "photos": photo_count,
                    "model": model,
                    "client": "",
                    "confidence": "0",
                    "seconds": "0",
                    "reason": f"ERROR: {exc}",
                })

        # --------------------------------------------------------
        # FULL UNLOAD AFTER MODEL
        # --------------------------------------------------------

        unload_model(model)

    # ============================================================
    # CSV
    # ============================================================

    output = Path(args.out)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "raw",
                "photos",
                "model",
                "client",
                "confidence",
                "seconds",
                "reason",
            ],
        )

        writer.writeheader()
        writer.writerows(results)

    # ============================================================
    # SUMMARY
    # ============================================================

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for model in MODELS:

        rows = [
            row
            for row in results
            if row["model"] == model
        ]

        accepted = [
            row
            for row in rows
            if row["client"]
        ]

        total_photos = sum(
            int(row["photos"])
            for row in rows
        )

        accepted_photos = sum(
            int(row["photos"])
            for row in accepted
        )

        avg_confidence = (
            sum(
                float(row["confidence"])
                for row in rows
            )
            / len(rows)
            if rows
            else 0
        )

        total_time = sum(
            float(row["seconds"])
            for row in rows
        )

        print(
            f"{model:18} "
            f"accepted={len(accepted):2}/{len(rows):2}  "
            f"photos={accepted_photos:3}/{total_photos:3}  "
            f"avg_conf={avg_confidence:.3f}  "
            f"time={total_time:.1f}s"
        )

    # ============================================================
    # SIDE-BY-SIDE TABLE
    # ============================================================

    print()
    print("=" * 70)
    print("SIDE-BY-SIDE RESULTS")
    print("=" * 70)

    by_raw = {}

    for row in results:

        by_raw.setdefault(
            row["raw"],
            {
                "photos": row["photos"],
            },
        )

        by_raw[row["raw"]][row["model"]] = (
            row["client"],
            row["confidence"],
        )

    print()
    print(
        f"{'RAW':35} "
        f"{'PH':>3} "
        f"{'Q3-4B':>18} "
        f"{'Q3-8B':>18} "
        f"{'Q2.5-7B':>18}"
    )

    print("-" * 110)

    for raw, data in by_raw.items():

        cells = []

        for model in MODELS:

            client, confidence = data.get(
                model,
                ("", "0"),
            )

            if client:
                cells.append(
                    f"{client[:10]}({confidence})"
                )
            else:
                cells.append(
                    "NONE"
                )

        print(
            f"{raw[:35]:35} "
            f"{data['photos']:3d} "
            f"{cells[0]:18} "
            f"{cells[1]:18} "
            f"{cells[2]:18}"
        )

    print()
    print("=" * 70)
    print("CSV:", output)
    print("=" * 70)

if __name__ == "__main__":
    main()
PY
chmod +x scripts/benchmark_client_models_25.py
echo 'SCRIPT CREATED'
```

---

### ✅ **Важные улучшения:**

1. **Принудительное освобождение VRAM:**
   - `ollama stop` + `nvidia-smi` проверка
   - Пауза перед следующим тестом

2. **Обработка отсутствующих моделей:**
   - Проверка `ollama list` перед запуском
   - Пропуск модели с `NOT INSTALLED` и логированием

3. **Улучшенная статистика:**
   - Средняя уверенность
   - Время на 25 запросов
   - Сводная таблица по каждому RAW

4. **Безопасность:**
   - Проверка, что модель действительно выгружена
   - Логирование всех этапов

---

### 📌 **Как запустить:**

```bash
cd ~/projects/scene_fingerprint_mvp_v02
uv run python scripts/benchmark_client_models_25.py
```

---

### 📁 **Результаты:**

- CSV: `data/client_model_benchmark_25.csv`
- Сводная таблица: в консоли
- Логи: в консоли

---

### 📌 **Пример вывода:**

```
Q3-4B  accepted=12/25  photos=150/150  avg_conf=0.85  time=12.3s
Q3-8B  accepted=14/25  photos=150/150  avg_conf=0.89  time=11.7s
Q2.5-7B  accepted=13/25  photos=150/150  avg_conf=0.87  time=13.2s
```

---

### 📌 **Пример сводной таблицы:**

```
RAW: "Тенет"  PH: 150  Q3-4B: Тенет(0.95)  Q3-8B: Тенет(0.97)  Q2.5-7B: Тенет(0.96)
RAW: "Сбер"  PH: 120  Q3-4B: Сбер(0.92)  Q3-8B: Сбер(0.94)  Q2.5-7B: Сбер(0.93)
```

---

### 📌 **Примечание:**
- Если модель не установлена, она будет пропущена с логированием
- Все этапы тестирования логируются в консоль
- Результаты сохраняются в CSV для дальнейшего анализа