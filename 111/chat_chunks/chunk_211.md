## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 🤖 **Assistant** — 2026-08-20 22:27:29

Да. Делаем. Сначала заменим benchmark на версию с **принудительным освобождением VRAM перед каждым тестом** и проверкой через `nvidia-smi`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > scripts/benchmark_client_models_25.py <<'PY'
#!/usr/bin/env python3

import csv
import json
import shutil
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

TEST_LIMIT = 25
MIN_CONFIDENCE = 0.80

SYSTEM_PROMPT = """
Ты нормализуешь названия клиентов для фотобазы.

Выбери клиента ТОЛЬКО из переданного справочника.

Можно исправлять:
- очевидные опечатки;
- OCR-ошибки;
- регистр;
- пропущенные или лишние пробелы;
- небольшие перестановки букв;
- очевидные варианты написания.

Нельзя:
- придумывать нового клиента;
- выбирать семантически похожего клиента без достаточного
  основания;
- объединять разные организации только потому, что они похожи.

Если уверенности недостаточно — client должен быть null.

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

def pg():
    return psycopg2.connect(**PG_CONFIG)

def get_directory():
    with pg() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name
                FROM client_directory
                WHERE active = TRUE
                ORDER BY sort_order, name
            """)

            return [
                (int(row[0]), row[1])
                for row in cur.fetchall()
                if row[1]
            ]

def get_unknown_clients(limit=25):
    with pg() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    TRIM(p.client) AS raw_name,
                    COUNT(*) AS photo_count
                FROM photos p
                WHERE
                    p.client IS NOT NULL
                    AND TRIM(p.client) <> ''

                    AND NOT EXISTS (
                        SELECT 1
                        FROM client_directory cd
                        WHERE cd.active = TRUE
                          AND LOWER(TRIM(cd.name))
                              = LOWER(TRIM(p.client))
                    )

                    AND NOT EXISTS (
                        SELECT 1
                        FROM client_aliases ca
                        JOIN client_directory cd
                          ON cd.id = ca.client_id
                        WHERE cd.active = TRUE
                          AND LOWER(TRIM(ca.raw_name))
                              = LOWER(TRIM(p.client))
                    )

                GROUP BY TRIM(p.client)
                ORDER BY COUNT(*) DESC, TRIM(p.client)
                LIMIT %s
            """, (limit,))

            return [
                (row[0], int(row[1]))
                for row in cur.fetchall()
            ]

def ollama_models():
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=20,
        )

        installed = set()

        for line in result.stdout.splitlines()[1:]:
            parts = line.split()

            if parts:
                installed.add(parts[0])

        return installed

    except Exception:
        return set()

def gpu_status(label):
    print()
    print(f"================ VRAM {label} ================")

    if not shutil.which("nvidia-smi"):
        print("nvidia-smi: NOT FOUND")
        return

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )

        print(result.stdout.strip())

    except Exception as exc:
        print("nvidia-smi ERROR:", exc)

def unload_model(model):
    print()
    print("============================================================")
    print("UNLOADING:", model)
    print("============================================================")

    # Сначала обычная остановка.
    try:
        result = subprocess.run(
            ["ollama", "stop", model],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.stdout.strip():
            print(result.stdout.strip())

        if result.stderr.strip():
            print(result.stderr.strip())

    except Exception as exc:
        print("ollama stop:", repr(exc))

    # Даём Ollama время освободить CUDA context.
    time.sleep(3)

    gpu_status("AFTER STOP")

def unload_all_models(installed):
    print()
    print("============================================================")
    print("FREE VRAM BEFORE TEST")
    print("============================================================")

    for model in installed:
        try:
            subprocess.run(
                ["ollama", "stop", model],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=20,
            )
        except Exception:
            pass

    time.sleep(4)

    gpu_status("BEFORE MODEL LOAD")

def ask_qwen(raw, directory_names, model):

    directory_text = "\n".join(
        f"- {name}"
        for name in directory_names
    )

    user_prompt = f"""
СПРАВОЧНИК:

{directory_text}

ИСХОДНОЕ НАЗВАНИЕ:

{raw}

Выбери одного клиента из справочника либо null.
""".strip()

    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "keep_alive": "0",
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

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=180,
    )

    response.raise_for_status()

    elapsed = time.perf_counter() - started

    data = response.json()

    content = (
        data.get("message", {})
        .get("content", "")
        .strip()
    )

    try:
        result = json.loads(content)
    except Exception:
        result = {}

    client = result.get("client")

    if client not in directory_names:
        client = None

    try:
        confidence = float(
            result.get("confidence", 0) or 0
        )
    except Exception:
        confidence = 0.0

    reason = result.get("reason", "")

    if confidence < MIN_CONFIDENCE:
        accepted = None
    else:
        accepted = client

    return {
        "client": accepted,
        "raw_client": client,
        "confidence": confidence,
        "reason": reason,
        "seconds": elapsed,
    }

def main():

    print("=" * 70)
    print("CLIENT NORMALIZER — 25 PHOTO/CLIENT BENCHMARK")
    print("=" * 70)

    directory = get_directory()

    if not directory:
        print("ERROR: CLIENT DIRECTORY EMPTY")
        return 1

    directory_names = [
        name
        for _, name in directory
    ]

    unknown = get_unknown_clients(TEST_LIMIT)

    print()
    print("CLIENT DIRECTORY:", len(directory_names))
    print("UNKNOWN TEST SET:", len(unknown))

    print()
    print("TEST SET")
    print("-" * 70)

    for i, (raw, count) in enumerate(unknown, 1):
        print(
            f"{i:02d}. {count:3d}  {raw!r}"
        )

    installed = ollama_models()

    print()
    print("INSTALLED MODELS")
    for model in MODELS:
        print(
            f"{model:20} "
            f"{'YES' if model in installed else 'NO'}"
        )

    results = []

    # ============================================================
    # EACH MODEL
    # ============================================================

    for model_no, model in enumerate(MODELS, 1):

        if model not in installed:
            print()
            print("=" * 70)
            print("SKIP:", model)
            print("MODEL IS NOT INSTALLED")
            print("=" * 70)

            for raw, photos in unknown:
                results.append({
                    "raw": raw,
                    "photos": photos,
                    "model": model,
                    "client": "",
                    "confidence": "",
                    "seconds": "",
                    "reason": "MODEL NOT INSTALLED",
                })

            continue

        # --------------------------------------------------------
        # CRITICAL:
        # FULL VRAM CLEANUP BEFORE EACH MODEL
        # --------------------------------------------------------

        unload_all_models(installed)

        print()
        print("=" * 70)
        print(f"MODEL {model_no}/{len(MODELS)}: {model}")
        print("=" * 70)

        gpu_status("JUST BEFORE TEST")

        # --------------------------------------------------------
        # TEST 25
        # --------------------------------------------------------

        for i, (raw, photos) in enumerate(
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

                print(
                    f"[{i:02d}/{len(unknown)}] "
                    f"{raw!r:42} -> "
                    f"{client or 'NONE':15} "
                    f"conf={result['confidence']:.3f} "
                    f"time={result['seconds']:.1f}s"
                )

                results.append({
                    "raw": raw,
                    "photos": photos,
                    "model": model,
                    "client": client or "",
                    "confidence": f"{result['confidence']:.3f}",
                    "seconds": f"{result['seconds']:.2f}",
                    "reason": result["reason"],
                })

            except Exception as exc:

                print(
                    f"[{i:02d}/{len(unknown)}] "
                    f"{raw!r:42} -> ERROR {exc}"
                )

                results.append({
                    "raw": raw,
                    "photos": photos,
                    "model": model,
                    "client": "",
                    "confidence": "",
                    "seconds": "",
                    "reason": f"ERROR: {exc}",
                })

        # --------------------------------------------------------
        # UNLOAD IMMEDIATELY AFTER TEST
        # --------------------------------------------------------

        unload_model(model)

    # ============================================================
    # SAVE CSV
    # ============================================================

    out = Path(
        "data/client_normalizer_benchmark_25.csv"
    )

    out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with out.open(
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
    print("MODEL SUMMARY")
    print("=" * 70)

    for model in MODELS:

        rows = [
            r
            for r in results
            if r["model"] == model
        ]

        valid = [
            r
            for r in rows
            if r["client"]
        ]

        total_time = sum(
            float(r["seconds"])
            for r in rows
            if r["seconds"]
        )

        avg_conf = (
            sum(
                float(r["confidence"])
                for r in rows
                if r["confidence"]
            )
            /
            len([
                r for r in rows
                if r["confidence"]
            ])
            if any(r["confidence"] for r in rows)
            else 0
        )

        print(
            f"{model:20} "
            f"matches={len(valid):2}/{len(rows):2} "
            f"avg_conf={avg_conf:.3f} "
            f"time={total_time:.1f}s"
        )

    # ============================================================
    # SIDE BY SIDE
    # ============================================================

    print()
    print("=" * 70)
    print("SIDE-BY-SIDE")
    print("=" * 70)

    indexed = {}

    for raw, photos in unknown:
        indexed[raw] = {
            "photos": photos
        }

    for row in results:
        indexed[row["raw"]][row["model"]] = row

    print()

    header = (
        f"{'RAW':35} "
        f"{'PH':>3} "
        f"{'Q3:4B':>16} "
        f"{'Q3:8B':>16} "
        f"{'Q2.5:7B':>16}"
    )

    print(header)
    print("-" * len(header))

    for raw, data in indexed.items():

        cells = []

        for model in MODELS:

            row = data.get(model)

            if not row:
                cells.append("NOT RUN")
                continue

            if row["client"]:
                cells.append(
                    f"{row['client'][:9]} "
                    f"({row['confidence']})"
                )
            elif row["reason"] == "MODEL NOT INSTALLED":
                cells.append("NOT INST.")
            else:
                cells.append("NONE")

        print(
            f"{raw[:35]:35} "
            f"{data['photos']:3d} "
            f"{cells[0]:16} "
            f"{cells[1]:16} "
            f"{cells[2]:16}"
        )

    print()
    print("=" * 70)
    print("RESULT FILE:")
    print(out)
    print("=" * 70)

    # Финальная проверка — VRAM должна быть освобождена.
    unload_all_models(installed)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY
chmod +x scripts/benchmark_client_models_25.py
```

### Перед запуском

Проверим, что зависимости есть именно в `uv`-окружении:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -c "import psycopg2, requests; print('DEPENDENCIES OK')"
```

Потом:

```bash
ollama list | grep -E '^qwen(2\.5:7b|3:(4b|8b))'
```

Если `qwen2.5:7b` отсутствует, **пока не устанавливаем автоматически** — сначала увидим, какие две модели реально готовы к тесту.

И сам benchmark:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/benchmark_client_models_25.py
```

Важный момент: я специально поставил в API:

```text
keep_alive: "0"
```

плюс перед каждым тестом:

```text
ollama stop
```

плюс паузу и `nvidia-smi`.

То есть переход будет именно:

**Qwen 4B → выгрузка → проверка VRAM → Qwen 8B → выгрузка → проверка VRAM → Qwen 2.5 7B → выгрузка → итог.**

Это даст нам намного более честное сравнение моделей по качеству и времени.

---

### 👤 **User** — 2026-08-20 22:28:45

оочистить врам сейчас

---

### 🤖 **Assistant** — 2026-08-20 22:28:46

Да. Для твоего теста с Ollama лучше **перед каждым запуском модели очищать VRAM**, а после теста выгружать модель.

Сейчас выполни:

```bash
ollama ps
```

Если там будет загруженная модель, выгрузи её:

```bash
ollama stop qwen3:8b
```

Проверка:

```bash
ollama ps
nvidia-smi
```

В `ollama ps` должно быть пусто, а занятая VRAM — минимальной.

Если нужно **жёстко освободить именно CUDA-кэш**, можно дополнительно посмотреть процессы:

```bash
nvidia-smi
```

Но обычно для Ollama достаточно `ollama stop`.

### Для нашего последовательного теста

Сделаем так:

1. очистить VRAM;
2. `qwen3:4b` → первые 25 неизвестных клиентов;
3. `ollama stop qwen3:4b`;
4. снова проверить VRAM;
5. `qwen3:8b` → те же 25;
6. `ollama stop qwen3:8b`;
7. `qwen2.5:7b` → те же 25;
8. итоговая таблица:
   - клиент;
   - количество фото;
   - результат 4B;
   - confidence;
   - результат 8B;
   - confidence;
   - результат 2.5 7B;
   - confidence;
   - совпадение/расхождение.

И главное — **одинаковый набор из 25 клиентов и одинаковый prompt**, чтобы сравнение было честным.

Сейчас VRAM можно очистить командой:

```bash
ollama stop qwen3:8b 2>/dev/null || true
ollama stop qwen3:4b 2>/dev/null || true
ollama stop qwen2.5:7b 2>/dev/null || true

echo "================ OLLAMA ================"
ollama ps

echo "================ GPU ================"
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
```

После этого можно запускать первый 25-клиентный прогон.

---

### 👤 **User** — 2026-08-20 22:43:39

кажется, это на данном этапе - бесполезное занятие. подумаем об этом потом. пока продолжаем с базой и отображением. клиентов не трогаем - используем пока юез нейро нормализацииSUMMARY
======================================================================
qwen3:4b           accepted= 3/25  photos= 17/207  avg_conf=0.116  time=609.4s
qwen3:8b           accepted= 1/25  photos=  5/207  avg_conf=0.064  time=190.2s
qwen2.5:7b         accepted= 3/25  photos= 17/207  avg_conf=0.114  time=31.4s

======================================================================
SIDE-BY-SIDE RESULTS
======================================================================

RAW                                  PH              Q3-4B              Q3-8B            Q2.5-7B
--------------------------------------------------------------------------------------------------------------
EMBARGO                              43 NONE               NONE               NONE              
Единая Россия                        30 NONE               NONE               NONE              
Сила России                          18 NONE               NONE               NONE              
Вольный Дон                          14 NONE               NONE               NONE              
БЕТСИТИ                              10 NONE               NONE               NONE              
Пятёрочка                             9 NONE               NONE               NONE              
Яндекс Маркет                         9 Яндекс(0.950)      NONE               Яндекс(0.950)     
Магнит                                8 NONE               NONE               NONE              
МТС                                   8 NONE               NONE               NONE              
Волный Дон                            7 NONE               NONE               NONE              
ozon fresh                            5 Ozon(0.950)        Ozon(0.900)        Ozon(1.000)       
Государственная Дума                  5 NONE               NONE               NONE              
Купер                                 5 NONE               NONE               NONE              
Московский Цирк Никулина              5 NONE               NONE               NONE              
контракт61.рф                         4 NONE               NONE               NONE              
Волынский Дон                         3 NONE               NONE               NONE              
Дон                                   3 NONE               NONE               NONE              
Максидом                              3 NONE               NONE               NONE              
ОКЕЙ                                  3 NONE               NONE               NONE              
ООО «Интернет Решений»                3 NONE               NONE               NONE              
Ростов-на-Дону                        3 NONE               NONE               NONE              
Яндекс Лавка                          3 Яндекс(1.000)      NONE               Яндекс(0.900)     
EMBAYGO                               2 NONE               NONE               NONE              
WINLINE                               2 NONE               NONE               NONE              
Бронницкий Ювелир                     2 NONE               NONE               NONE              

======================================================================
CSV: data/client_model_benchmark_25.csv
======================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:43:40

Да, согласен. Результат теста как раз показал, что **нейронная нормализация сейчас не окупает сложность**: на 25 значениях она уверенно взяла только 1–3 случая, а время у `qwen3:4b/8b` огромное. Оставляем это как отдельную будущую функцию.

### Фиксируем решение

**Клиентов пока вообще не меняем.**

Работаем с текущим `photos.client` **как есть**, без:

- Qwen;
- fuzzy matching;
- `normalize_client()` для отображения;
- автоматического создания aliases;
- изменения существующих клиентских данных.

То есть база и UI пока используют **RAW client**.

---

### А вот адреса продолжаем

По адресам у нас уже нормальная схема:

```text
address_directory
    id
    legal_address
    simple_address
    active
    sort_order

address_fingerprints
    fingerprint_id
    address_id
    active
```

И здесь как раз имеет смысл довести отображение до конца.

Ошибка, которую мы обнаружили ранее:

```text
relation "fingerprint_addresses" does not exist
```

уже понятна — старое имя таблицы осталось в функции. Правильное:

```text
address_fingerprints
```

---

### Следующий этап

Я бы сейчас не трогал алгоритм распознавания вообще.

Двигаемся по цепочке:

```text
PHOTOS
  │
  ├── client → RAW client
  │
  └── fingerprint
          │
          ▼
   address_fingerprints
          │
          ▼
   address_directory
          │
          ├── simple_address
          └── legal_address
```

И уже эту информацию правильно подключаем к **гридy отображения**.

Особенно важно сохранить наше прежнее требование:

> **Грид должен начинать показывать фотографии сразу**, а настройки отображения брать из положения чекбоксов/текущего пользователя.

То есть сначала добиваемся, чтобы для каждой фотографии backend стабильно отдавал примерно:

```json
{
    "photo": "...",
    "client": "Яндекс",
    "fingerprint_id": "78_v33",
    "address_id": 78,
    "address": "Комарова, 13"
}
```

А уже UI решает, **показывать адрес или нет**.

Это правильнее, чем сейчас пытаться встроить нормализацию клиентов в основной поток.

**Клиентов замораживаем в текущем RAW-виде и возвращаемся к ним позже.**

---

### 👤 **User** — 2026-08-20 22:44:04

да

---

### 🤖 **Assistant** — 2026-08-20 22:44:06

Да. Тогда **фиксируем клиентов в RAW-виде и больше их пока не трогаем**.

Следующий шаг — **адреса → фото → грид**.

Предлагаю идти безопасно: сначала проверить, что backend правильно связывает `fingerprint_id → address_id → simple_address`, и только потом менять отображение.

Выполни в проекте:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ ADDRESS DB ================" && \
grep -RniE \
'get_address_for_fingerprint|get_address_by_fingerprint|address_fingerprints|address_directory' \
app/web \
--include="*.py"
```

И затем:

```bash
echo "================ PHOTO DATA ================" && \
grep -RniE \
'fingerprint_id|client|address_id|simple_address|legal_address' \
app/web/components \
app/web \
--include="*.py" | head -n 250
```

**Пока ничего не исправляем.** Покажи вывод — по нему определим, где сейчас формируется объект фотографии для грида и вставим адрес туда, не ломая существующую логику.

---

### 👤 **User** — 2026-08-20 22:44:39

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ ADDRESS DB ================" && \
grep -RniE \
'get_address_for_fingerprint|get_address_by_fingerprint|address_fingerprints|address_directory' \
app/web \
--include="*.py"
================ ADDRESS DB ================
app/web/directory_db.py:16:def get_address_directory():
app/web/directory_db.py:34:        FROM address_directory
app/web/directory_db.py:52:def get_address_by_fingerprint(fingerprint_id):
app/web/directory_db.py:63:        FROM address_fingerprints
app/web/directory_db.py:80:def get_address_for_fingerprint(fingerprint_id):
app/web/directory_db.py:85:    address_id = get_address_by_fingerprint(
app/web/directory_db.py:92:    directory = get_address_directory()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo "================ PHOTO DATA ================" && \
grep -RniE \
'fingerprint_id|client|address_id|simple_address|legal_address' \
app/web/components \
app/web \
--include="*.py" | head -n 250
================ PHOTO DATA ================
app/web/components/search.py:29:        client
app/web/components/search.py:54:            client,
app/web/components/search.py:75:            OR client ILIKE %s
app/web/components/collections.py:34:        client = ui.select(
app/web/components/collections.py:79:                        client=client.value or "",
app/web/components/photos.py:744:    # CLIENT FILTER
app/web/components/photos.py:754:        "clients",
app/web/components/photos.py:759:    selected_clients = STATE.selected_clients
app/web/components/photos.py:762:    if selected_clients is None:
app/web/components/photos.py:766:    if not selected_clients:
app/web/components/photos.py:770:        str(client).strip().casefold()
app/web/components/photos.py:771:        for client in selected_clients
app/web/components/photos.py:785:        client = str(
app/web/components/photos.py:786:            record.get("client") or ""
app/web/components/photos.py:789:        if client in selected_normalized:
app/web/components/photos.py:819:        "client=", record.get("client"),
app/web/components/photos.py:941:                            value("client")
app/web/components/clients.py:5:from app.web.client_db import get_clients_with_address_counts
app/web/components/clients.py:8:def build_clients_panel(refresh_photos):
app/web/components/clients.py:11:    # LOAD CLIENTS
app/web/components/clients.py:15:        clients = get_clients_with_address_counts()
app/web/components/clients.py:20:            "[CLIENT DB ERROR]",
app/web/components/clients.py:25:        clients = []
app/web/components/clients.py:31:    client_checkboxes = {}
app/web/components/clients.py:34:    # CLIENT ACTIONS
app/web/components/clients.py:37:    def select_all_clients():
app/web/components/clients.py:39:        STATE.selected_clients = None
app/web/components/clients.py:42:            "[CLIENT SELECT ALL]",
app/web/components/clients.py:46:        for checkbox in client_checkboxes.values():
app/web/components/clients.py:51:    def clear_clients():
app/web/components/clients.py:53:        STATE.selected_clients = set()
app/web/components/clients.py:56:            "[CLIENT CLEAR]",
app/web/components/clients.py:60:        for checkbox in client_checkboxes.values():
app/web/components/clients.py:65:    def select_client(e, name):
app/web/components/clients.py:67:        all_clients = {
app/web/components/clients.py:68:            client
app/web/components/clients.py:69:            for client, _ in clients
app/web/components/clients.py:76:        if STATE.selected_clients is None:
app/web/components/clients.py:78:            STATE.selected_clients = set(
app/web/components/clients.py:79:                all_clients
app/web/components/clients.py:87:            STATE.selected_clients.add(name)
app/web/components/clients.py:89:            STATE.selected_clients.discard(name)
app/web/components/clients.py:96:        if STATE.selected_clients == all_clients:
app/web/components/clients.py:97:            STATE.selected_clients = None
app/web/components/clients.py:100:            "[CLIENT SELECT]",
app/web/components/clients.py:104:            "STATE.selected_clients=",
app/web/components/clients.py:105:            repr(STATE.selected_clients),
app/web/components/clients.py:111:    def toggle_client(name, checkbox):
app/web/components/clients.py:126:        select_client(event, name)
app/web/components/clients.py:171:                    on_click=select_all_clients,
app/web/components/clients.py:179:                    on_click=clear_clients,
app/web/components/clients.py:187:        # CLIENT LIST
app/web/components/clients.py:196:            for name, address_count in clients:
app/web/components/clients.py:204:                            STATE.selected_clients is None
app/web/components/clients.py:205:                            or name in STATE.selected_clients
app/web/components/clients.py:208:                            select_client(e, n),
app/web/components/clients.py:213:                    client_checkboxes[name] = checkbox
app/web/components/clients.py:222:                            toggle_client(n, cb),
app/web/components/clients.py:231:        build_collections("clients")
app/web/components/search.py:29:        client
app/web/components/search.py:54:            client,
app/web/components/search.py:75:            OR client ILIKE %s
app/web/components/collections.py:34:        client = ui.select(
app/web/components/collections.py:79:                        client=client.value or "",
app/web/components/photos.py:744:    # CLIENT FILTER
app/web/components/photos.py:754:        "clients",
app/web/components/photos.py:759:    selected_clients = STATE.selected_clients
app/web/components/photos.py:762:    if selected_clients is None:
app/web/components/photos.py:766:    if not selected_clients:
app/web/components/photos.py:770:        str(client).strip().casefold()
app/web/components/photos.py:771:        for client in selected_clients
app/web/components/photos.py:785:        client = str(
app/web/components/photos.py:786:            record.get("client") or ""
app/web/components/photos.py:789:        if client in selected_normalized:
app/web/components/photos.py:819:        "client=", record.get("client"),
app/web/components/photos.py:941:                            value("client")
app/web/components/clients.py:5:from app.web.client_db import get_clients_with_address_counts
app/web/components/clients.py:8:def build_clients_panel(refresh_photos):
app/web/components/clients.py:11:    # LOAD CLIENTS
app/web/components/clients.py:15:        clients = get_clients_with_address_counts()
app/web/components/clients.py:20:            "[CLIENT DB ERROR]",
app/web/components/clients.py:25:        clients = []
app/web/components/clients.py:31:    client_checkboxes = {}
app/web/components/clients.py:34:    # CLIENT ACTIONS
app/web/components/clients.py:37:    def select_all_clients():
app/web/components/clients.py:39:        STATE.selected_clients = None
app/web/components/clients.py:42:            "[CLIENT SELECT ALL]",
app/web/components/clients.py:46:        for checkbox in client_checkboxes.values():
app/web/components/clients.py:51:    def clear_clients():
app/web/components/clients.py:53:        STATE.selected_clients = set()
app/web/components/clients.py:56:            "[CLIENT CLEAR]",
app/web/components/clients.py:60:        for checkbox in client_checkboxes.values():
app/web/components/clients.py:65:    def select_client(e, name):
app/web/components/clients.py:67:        all_clients = {
app/web/components/clients.py:68:            client
app/web/components/clients.py:69:            for client, _ in clients
app/web/components/clients.py:76:        if STATE.selected_clients is None:
app/web/components/clients.py:78:            STATE.selected_clients = set(
app/web/components/clients.py:79:                all_clients
app/web/components/clients.py:87:            STATE.selected_clients.add(name)
app/web/components/clients.py:89:            STATE.selected_clients.discard(name)
app/web/components/clients.py:96:        if STATE.selected_clients == all_clients:
app/web/components/clients.py:97:            STATE.selected_clients = None
app/web/components/clients.py:100:            "[CLIENT SELECT]",
app/web/components/clients.py:104:            "STATE.selected_clients=",
app/web/components/clients.py:105:            repr(STATE.selected_clients),
app/web/components/clients.py:111:    def toggle_client(name, checkbox):
app/web/components/clients.py:126:        select_client(event, name)
app/web/components/clients.py:171:                    on_click=select_all_clients,
app/web/components/clients.py:179:                    on_click=clear_clients,
app/web/components/clients.py:187:        # CLIENT LIST
app/web/components/clients.py:196:            for name, address_count in clients:
app/web/components/clients.py:204:                            STATE.selected_clients is None
app/web/components/clients.py:205:                            or name in STATE.selected_clients
app/web/components/clients.py:208:                            select_client(e, n),
app/web/components/clients.py:213:                    client_checkboxes[name] = checkbox
app/web/components/clients.py:222:                            toggle_client(n, cb),
app/web/components/clients.py:231:        build_collections("clients")
app/web/client_aliases.py:11:CLIENT_ALIASES = {
app/web/client_aliases.py:54:def normalize_client(value: str | None) -> str:
app/web/client_aliases.py:65:    for canonical, aliases in CLIENT_ALIASES.items():
app/web/client_aliases.py:75:def get_client_aliases() -> dict[str, list[str]]:
app/web/client_aliases.py:76:    return CLIENT_ALIASES.copy()
app/web/photo_db.py:27:            client,
app/web/frontend_v02.py:26:CLIENTS = [
app/web/frontend_v02.py:196:current_client = {"value": "Все клиенты"}
app/web/frontend_v02.py:281:    # LEFT — CLIENTS
app/web/frontend_v02.py:295:        for name, icon in CLIENTS:
app/web/frontend_v02.py:297:            def select_client(
app/web/frontend_v02.py:299:                client=name,
app/web/frontend_v02.py:301:                current_client["value"] = client
app/web/frontend_v02.py:325:                    select_client
app/web/frontend_v02.py:489:        for client_name, groups in ADDRESS_GROUPS.items():
app/web/frontend_v02.py:492:                client_name,
app/web/client_normalizer.py:12:def normalize_client(raw_name):
app/web/client_normalizer.py:41:                FROM client_directory
app/web/client_normalizer.py:61:                FROM client_aliases ca
app/web/client_normalizer.py:62:                JOIN client_directory cd
app/web/client_normalizer.py:63:                  ON cd.id = ca.client_id
app/web/main.py:9:from app.web.components.clients import build_clients_panel
app/web/main.py:324:        # CLIENTS + PHOTOS + ADDRESSES
app/web/main.py:341:            # CLIENTS
app/web/main.py:355:                build_clients_panel(
app/web/frontend_v01_backup_before_modular.py:15:CLIENTS = [
app/web/frontend_v01_backup_before_modular.py:271:    # LEFT PANEL — CLIENTS
app/web/frontend_v01_backup_before_modular.py:285:        for name, icon in CLIENTS:
app/web/frontend_v01.py:15:CLIENTS = [
app/web/frontend_v01.py:271:    # LEFT PANEL — CLIENTS
app/web/frontend_v01.py:285:        for name, icon in CLIENTS:
app/web/state.py:23:    client: str = ""
app/web/state.py:27:    # "clients"   — клиенты
app/web/state.py:44:    clients: list[str] = field(default_factory=lambda: [
app/web/state.py:105:            "clients",
app/web/state.py:112:            "clients",
app/web/state.py:118:    selected_clients: set[str] | None = None
app/web/state.py:125:    # clients   = только клиенты
app/web/client_dictionary.py:15:def import_client_dictionary(csv_path):
app/web/client_dictionary.py:25:    Исходное photos.client НЕ изменяется.
app/web/client_dictionary.py:33:    imported_clients = 0
app/web/client_dictionary.py:82:                    # CLIENT
app/web/client_dictionary.py:87:                        INSERT INTO client_directory (
app/web/client_dictionary.py:108:                    client_id = cur.fetchone()[0]
app/web/client_dictionary.py:110:                    imported_clients += 1
app/web/client_dictionary.py:129:                            INSERT INTO client_aliases (
app/web/client_dictionary.py:130:                                client_id,
app/web/client_dictionary.py:135:                                client_id,
app/web/client_dictionary.py:141:                                client_id,
app/web/client_dictionary.py:149:        "clients": imported_clients,
app/web/directory_db.py:32:            simple_address,
app/web/directory_db.py:33:            legal_address
app/web/directory_db.py:52:def get_address_by_fingerprint(fingerprint_id):
app/web/directory_db.py:54:    Возвращает address_id для fingerprint.
app/web/directory_db.py:62:        SELECT address_id
app/web/directory_db.py:64:        WHERE fingerprint_id = %s
app/web/directory_db.py:71:            cur.execute(sql, (fingerprint_id,))
app/web/directory_db.py:80:def get_address_for_fingerprint(fingerprint_id):
app/web/directory_db.py:85:    address_id = get_address_by_fingerprint(
app/web/directory_db.py:86:        fingerprint_id
app/web/directory_db.py:89:    if address_id is None:
app/web/directory_db.py:94:    data = directory.get(address_id)
app/web/directory_db.py:100:        "id": address_id,
app/web/directory_db.py:110:def get_clients():
app/web/directory_db.py:120:        FROM client_directory
app/web/directory_db.py:139:def normalize_client(raw_client):
app/web/directory_db.py:141:    Возвращает client_id по точному имени
app/web/directory_db.py:147:    if not raw_client:
app/web/directory_db.py:150:    raw = raw_client.strip()
app/web/directory_db.py:157:        FROM client_directory
app/web/directory_db.py:162:        SELECT client_id
app/web/directory_db.py:163:        FROM client_aliases
app/web/directory_db.py:184:def get_client_name(client_id):
app/web/directory_db.py:189:    if client_id is None:
app/web/directory_db.py:195:        FROM client_directory
app/web/directory_db.py:203:            cur.execute(sql, (client_id,))
app/web/client_db.py:12:def get_clients_with_address_counts() -> list[tuple[str, int]]:
app/web/client_db.py:22:            MIN(TRIM(client)) AS client,
app/web/client_db.py:26:            client IS NOT NULL
app/web/client_db.py:27:            AND TRIM(client) <> ''
app/web/client_db.py:28:        GROUP BY LOWER(TRIM(client))
app/web/client_db.py:29:        ORDER BY LOWER(MIN(TRIM(client)))
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:44:42

Отлично. Теперь видно главное: **адресный справочник сам по себе уже готов**, но он пока практически изолирован от основного потока фотографий.

И ещё важный момент: `photos.py` уже работает с `record`, поэтому нам нужно найти **место, где этот `record` формируется**. Там и надо один раз добавить адрес.

Сейчас выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PHOTO DB ================" && \
nl -ba app/web/photo_db.py | sed -n '1,260p' && \
echo "================ PHOTOS RECORD USAGE ================" && \
nl -ba app/web/components/photos.py | sed -n '700,980p'
```

И отдельно:

```bash
echo "================ PHOTO LOADERS ================" && \
grep -RniE \
'get_photos|SELECT .*FROM photos|FROM photos|fetchall\(\)|records|photo_records' \
app/web \
--include="*.py" | head -n 300
```

### Что мы сейчас ищем

Нам нужна конкретно цепочка:

```text
PostgreSQL photos
       ↓
photo_db / loader
       ↓
record = {...}
       ↓
photos.py
       ↓
GRID
```

После этого сделаем **минимальную правку**, примерно такого характера:

```text
record["address_id"]
record["address"]
record["legal_address"]
```

при этом:

- `photos.client` остаётся **RAW**;
- существующая фильтрация клиентов не меняется;
- распознавание не меняется;
- DINO не меняется;
- БД фотографий не меняется;
- `address_directory` остаётся источником названия адреса;
- UI получает уже готовый адрес.

И только **после проверки backend** решим, где именно адрес показывать в карточке фото.

---

### 👤 **User** — 2026-08-20 22:45:12

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PHOTO DB ================" && \
nl -ba app/web/photo_db.py | sed -n '1,260p' && \
echo "================ PHOTOS RECORD USAGE ================" && \
nl -ba app/web/components/photos.py | sed -n '700,980p'
================ PHOTO DB ================
     1	import psycopg2
     2	
     3	
     4	PG_CONFIG = {
     5	    "host": "localhost",
     6	    "port": 5432,
     7	    "dbname": "photobase",
     8	    "user": "lora",
     9	}
    10	
    11	
    12	def get_photo_records() -> list[dict]:
    13	    """
    14	    Загружает все записи фотографий из PostgreSQL.
    15	    """
    16	
    17	    sql = """
    18	        SELECT
    19	            id,
    20	            photo_id,
    21	            address,
    22	            filename,
    23	            path,
    24	            source_path,
    25	            original_filename,
    26	            preview_path,
    27	            client,
    28	            brand,
    29	            category,
    30	            description,
    31	            confidence,
    32	            qwen_status,
    33	            qwen_time_sec,
    34	            text_json,
    35	            colors_json,
    36	            objects_json,
    37	            environment_json,
    38	            image_quality_json,
    39	            camera_view_json,
    40	            scene_objects_json,
    41	            analysis_quality_json,
    42	            raw_json,
    43	            created_at,
    44	            dino_fingerprint,
    45	            dino_score,
    46	            dino_second_score,
    47	            dino_margin,
    48	            hybrid_original_id,
    49	            hybrid_final_id,
    50	            hybrid_changed,
    51	            hybrid_old_score,
    52	            hybrid_score,
    53	            hybrid_margin,
    54	            hybrid_neighbors,
    55	            status,
    56	            dino_status,
    57	            sort_status
    58	        FROM photos
    59	        ORDER BY id
    60	    """
    61	
    62	    with psycopg2.connect(**PG_CONFIG) as conn:
    63	        with conn.cursor() as cur:
    64	            cur.execute(sql)
    65	
    66	            columns = [
    67	                desc[0]
    68	                for desc in cur.description
    69	            ]
    70	
    71	            rows = cur.fetchall()
    72	
    73	    return [
    74	        dict(zip(columns, row))
    75	        for row in rows
    76	    ]
    77	
    78	
    79	def get_processing_stats() -> dict:
    80	    """
    81	    Быстрая статистика независимых веток DINO и Qwen.
    82	    Источник истины — PostgreSQL таблица photos.
    83	    """
    84	
    85	    sql = """
    86	        SELECT
    87	            COUNT(*) AS total,
    88	
    89	            COUNT(*) FILTER (
    90	                WHERE dino_status = 'done'
    91	            ) AS dino_done,
    92	
    93	            COUNT(*) FILTER (
    94	                WHERE dino_status = 'processing'
    95	            ) AS dino_processing,
    96	
    97	            COUNT(*) FILTER (
    98	                WHERE dino_status = 'pending'
    99	            ) AS dino_pending,
   100	
   101	            COUNT(*) FILTER (
   102	                WHERE dino_status = 'error'
   103	            ) AS dino_error,
   104	
   105	            COUNT(*) FILTER (
   106	                WHERE qwen_status = 'done'
   107	            ) AS qwen_done,
   108	
   109	            COUNT(*) FILTER (
   110	                WHERE qwen_status = 'processing'
   111	            ) AS qwen_processing,
   112	
   113	            COUNT(*) FILTER (
   114	                WHERE qwen_status = 'pending'
   115	            ) AS qwen_pending,
   116	
   117	            COUNT(*) FILTER (
   118	                WHERE qwen_status = 'error'
   119	            ) AS qwen_error
   120	
   121	        FROM photos
   122	    """
   123	
   124	    with psycopg2.connect(**PG_CONFIG) as conn:
   125	        with conn.cursor() as cur:
   126	            cur.execute(sql)
   127	            row = cur.fetchone()
   128	
   129	    return {
   130	        "total": row[0] or 0,
   131	
   132	        "dino": {
   133	            "done": row[1] or 0,
   134	            "processing": row[2] or 0,
   135	            "pending": row[3] or 0,
   136	            "error": row[4] or 0,
   137	        },
   138	
   139	        "qwen": {
   140	            "done": row[5] or 0,
   141	            "processing": row[6] or 0,
   142	            "pending": row[7] or 0,
   143	            "error": row[8] or 0,
   144	        },
   145	    }
   146	
   147	
   148	def build_photo_record_index(project_root):
   149	    """
   150	    Создаёт индекс PostgreSQL-записей по абсолютному пути файла.
   151	    """
   152	
   153	    records = get_photo_records()
   154	
   155	    index = {}
   156	
   157	    for record in records:
   158	
   159	        path = record.get("path")
   160	
   161	        if not path:
   162	            continue
   163	
   164	        from pathlib import Path
   165	
   166	        db_path = Path(path)
   167	
   168	        if not db_path.is_absolute():
   169	            db_path = project_root / db_path
   170	
   171	        # Основной индекс: полный абсолютный путь
   172	        index[str(db_path.resolve())] = record
   173	
   174	        # Fallback для daily/test_sorted_v2 и других
   175	        # запусков, где один и тот же файл имеет разные
   176	        # корневые каталоги.
   177	        #
   178	        # Ключ: адрес + имя файла
   179	        address = str(record.get("address") or "").strip()
   180	        filename = db_path.name
   181	
   182	        if address and filename:
   183	            index[f"__ADDR_FILE__:{address}:{filename}"] = record
   184	
   185	    return index
================ PHOTOS RECORD USAGE ================
   700	                files = []
   701	
   702	                for address in STATE.addresses:
   703	
   704	                    if address not in selected_addresses:
   705	                        continue
   706	
   707	                    files.extend(
   708	                        PHOTO_INDEX.get(
   709	                            address,
   710	                            [],
   711	                        )
   712	                    )
   713	
   714	        else:
   715	
   716	            # Режим "только клиенты":
   717	            # адреса полностью игнорируются.
   718	            files = get_all_indexed_photos()
   719	
   720	    # ========================================================
   721	    # DATE FILTER
   722	    # ========================================================
   723	
   724	    date_files = []
   725	
   726	    for path in files:
   727	
   728	        record = PHOTO_RECORD_INDEX.get(
   729	            str(path.resolve())
   730	        )
   731	
   732	        if not record:
   733	            continue
   734	
   735	        if photo_matches_date_filter(
   736	            record,
   737	            path,
   738	        ):
   739	            date_files.append(path)
   740	
   741	    files = date_files
   742	
   743	    # ========================================================
   744	    # CLIENT FILTER
   745	    # ========================================================
   746	
   747	    filter_priority = getattr(
   748	        STATE,
   749	        "filter_priority",
   750	        "both",
   751	    )
   752	
   753	    if filter_priority not in (
   754	        "clients",
   755	        "both",
   756	    ):
   757	        return files
   758	
   759	    selected_clients = STATE.selected_clients
   760	
   761	    # None = все клиенты.
   762	    if selected_clients is None:
   763	        return files
   764	
   765	    # set() = ничего не выбрано.
   766	    if not selected_clients:
   767	        return []
   768	
   769	    selected_normalized = {
   770	        str(client).strip().casefold()
   771	        for client in selected_clients
   772	    }
   773	
   774	    result = []
   775	
   776	    for path in files:
   777	
   778	        record = PHOTO_RECORD_INDEX.get(
   779	            str(path.resolve())
   780	        )
   781	
   782	        if not record:
   783	            continue
   784	
   785	        client = str(
   786	            record.get("client") or ""
   787	        ).strip().casefold()
   788	
   789	        if client in selected_normalized:
   790	            result.append(path)
   791	
   792	    return result
   793	
   794	
   795	def get_address_count(address):
   796	
   797	    return len(
   798	        PHOTO_INDEX.get(
   799	            address,
   800	            [],
   801	        )
   802	    )
   803	
   804	
   805	# ============================================================
   806	# PHOTO VIEWER
   807	# ============================================================
   808	
   809	def open_photo(photo):
   810	
   811	    record = photo.db_record or {}
   812	
   813	    print(
   814	        "[PHOTO OPEN]",
   815	        "file=", photo.path.name,
   816	        "has_db_record=", bool(photo.db_record),
   817	        "db_id=", record.get("id"),
   818	        "brand=", record.get("brand"),
   819	        "client=", record.get("client"),
   820	        flush=True,
   821	    )
   822	
   823	    def value(name, default="—"):
   824	        value = record.get(name)
   825	
   826	        if value is None or value == "":
   827	            return default
   828	
   829	        return str(value)
   830	
   831	    def json_text(name, default="—"):
   832	        value = record.get(name)
   833	
   834	        if value is None:
   835	            return default
   836	
   837	        if isinstance(value, list):
   838	            return ", ".join(str(x) for x in value)
   839	
   840	        if isinstance(value, dict):
   841	            return " · ".join(
   842	                f"{k}: {v}"
   843	                for k, v in value.items()
   844	            )
   845	
   846	        return str(value)
   847	
   848	    with ui.dialog() as dialog:
   849	
   850	        with ui.card().classes(
   851	            "w-[94vw] h-[94vh] "
   852	            "max-w-[1700px] "
   853	            "bg-black p-2 "
   854	            "overflow-hidden"
   855	        ):
   856	
   857	            # =================================================
   858	            # LARGE PHOTO
   859	            # =================================================
   860	
   861	            with ui.element("div").classes(
   862	                "w-full flex-1 min-h-0 "
   863	                "flex items-center justify-center "
   864	                "overflow-hidden"
   865	            ):
   866	
   867	                ui.image(
   868	                    str(photo.path)
   869	                ).classes(
   870	                    "max-w-full max-h-full "
   871	                    "object-contain"
   872	                )
   873	
   874	            # =================================================
   875	            # COMPACT INFORMATION PANEL
   876	            # =================================================
   877	
   878	            with ui.card().classes(
   879	                "w-full shrink-0 "
   880	                "bg-white text-black "
   881	                "rounded-lg "
   882	                "p-3 gap-1"
   883	            ):
   884	
   885	                # -------------------------------------------------
   886	                # HEADER
   887	                # -------------------------------------------------
   888	
   889	                with ui.row().classes(
   890	                    "w-full items-center "
   891	                    "justify-between gap-2"
   892	                ):
   893	
   894	                    with ui.row().classes(
   895	                        "items-center gap-2 min-w-0"
   896	                    ):
   897	
   898	                        ui.label(
   899	                            photo.path.name
   900	                        ).classes(
   901	                            "font-bold text-sm truncate"
   902	                        )
   903	
   904	                        ui.badge(
   905	                            value("address")
   906	                        ).props(
   907	                            "outline dense"
   908	                        )
   909	
   910	                        if value("qwen_status") != "—":
   911	
   912	                            ui.badge(
   913	                                f"Qwen: {value('qwen_status')}"
   914	                            ).props(
   915	                                "outline dense"
   916	                            )
   917	
   918	                    ui.button(
   919	                        icon="close",
   920	                        on_click=dialog.close,
   921	                    ).props(
   922	                        "flat round dense"
   923	                    )
   924	
   925	                # -------------------------------------------------
   926	                # BASIC INFORMATION
   927	                # -------------------------------------------------
   928	
   929	                with ui.row().classes(
   930	                    "w-full items-center "
   931	                    "gap-5 text-xs"
   932	                ):
   933	
   934	                    with ui.row().classes("items-center gap-1"):
   935	
   936	                        ui.label("Клиент").classes(
   937	                            "text-grey-6"
   938	                        )
   939	
   940	                        ui.label(
   941	                            value("client")
   942	                        ).classes(
   943	                            "font-medium"
   944	                        )
   945	
   946	                    with ui.row().classes("items-center gap-1"):
   947	
   948	                        ui.label("Бренд").classes(
   949	                            "text-grey-6"
   950	                        )
   951	
   952	                        ui.label(
   953	                            value("brand")
   954	                        ).classes(
   955	                            "font-medium"
   956	                        )
   957	
   958	                    with ui.row().classes("items-center gap-1"):
   959	
   960	                        ui.label("Категория").classes(
   961	                            "text-grey-6"
   962	                        )
   963	
   964	                        ui.label(
   965	                            value("category")
   966	                        ).classes(
   967	                            "font-medium"
   968	                        )
   969	
   970	                # -------------------------------------------------
   971	                # DESCRIPTION
   972	                # -------------------------------------------------
   973	
   974	                description = value("description")
   975	
   976	                if description != "—":
   977	
   978	                    with ui.row().classes(
   979	                        "w-full items-start gap-1 text-xs"
   980	                    ):
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo "================ PHOTO LOADERS ================" && \
grep -RniE \
'get_photos|SELECT .*FROM photos|FROM photos|fetchall$$|records|photo_records' \
app/web \
--include="*.py" | head -n 300
================ PHOTO LOADERS ================
app/web/components/search.py:71:        FROM photos
app/web/components/search.py:100:            rows = cur.fetchall()
app/web/components/technical_modules/data.py:7:from app.web.photo_db import get_photo_records
app/web/components/technical_modules/data.py:246:        db_records = get_photo_records()
app/web/components/technical_modules/data.py:247:        db_count = len(db_records)
app/web/components/photos.py:275:            "records=",
app/web/photo_db.py:12:def get_photo_records() -> list[dict]:
app/web/photo_db.py:58:        FROM photos
app/web/photo_db.py:71:            rows = cur.fetchall()
app/web/photo_db.py:121:        FROM photos
app/web/photo_db.py:153:    records = get_photo_records()
app/web/photo_db.py:157:    for record in records:
app/web/users_db.py:101:            return cur.fetchall()
app/web/directory_db.py:48:                for row in cur.fetchall()
app/web/directory_db.py:135:                for row in cur.fetchall()
app/web/client_db.py:24:        FROM photos
app/web/client_db.py:42:                for row in cur.fetchall()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:45:14

Да. Теперь картина понятна.

**Нейро-нормализацию клиентов пока полностью откладываем.** Текущий `photos.client` оставляем как есть. Не меняем БД, aliases и клиентскую логику.

По текущему коду я бы следующим шагом занялся **адресом → фотографиями → отображением**, потому что здесь уже есть нормальная основа:

- `photos.address` уже присутствует непосредственно в записи фото;
- `address_directory` содержит `id`, `simple_address`, `legal_address`;
- `address_fingerprints` связывает `fingerprint_id → address_id`;
- `photo_db.get_photo_records()` уже загружает все записи;
- `build_photo_record_index()` уже строит индекс `path → DB record`;
- фильтр адресов работает через `PHOTO_INDEX`;
- клиентский фильтр можно пока оставить старым, без какой-либо нейросети.

### Что я предлагаю сделать сейчас

Не трогая распознавание и клиентов, привести отображение к одной схеме:

```text
PostgreSQL
    │
    ├── photos
    │     ├── address
    │     ├── client       ← пока используем как есть
    │     ├── filename
    │     ├── preview_path
    │     └── ...
    │
    ├── address_directory
    │     ├── id
    │     ├── simple_address
    │     └── legal_address
    │
    └── address_fingerprints
          └── fingerprint_id → address_id
```

И UI должен брать **адрес непосредственно из записи `photos`**, а справочник использовать только для расшифровки/отображения.

То есть не надо сейчас строить дополнительную нейросетевую цепочку:

```text
OCR/Qwen → client normalization → aliases → photos
```

Оставляем:

```text
photos.client → UI
photos.address → UI
address_directory → красивое название адреса
```

Это гораздо безопаснее.

---

### Но есть один важный момент

Сейчас у нас есть потенциальная путаница:

```python
record["address"]
```

и

```python
address_fingerprints.address_id
```

Это **не обязательно одно и то же поле по смыслу**.

Поэтому перед изменениями я бы сделал один диагностический SQL-прогон и посмотрел фактические значения.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
PGPASSWORD="" psql -h localhost -p 5432 -U lora -d photobase -c "
SELECT
    id,
    photo_id,
    address,
    dino_fingerprint,
    client,
    filename
FROM photos
ORDER BY id
LIMIT 30;
"
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -h localhost -p 5432 -U lora -d photobase -c "
SELECT
    af.fingerprint_id,
    af.address_id,
    ad.simple_address,
    ad.legal_address
FROM address_fingerprints af
LEFT JOIN address_directory ad
    ON ad.id = af.address_id
WHERE af.active = TRUE
ORDER BY af.address_id
LIMIT 50;
"
```

И самое полезное — проверить соответствие:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -h localhost -p 5432 -U lora -d photobase -c "
SELECT
    p.address,
    p.dino_fingerprint,
    COUNT(*) AS photos
FROM photos p
GROUP BY p.address, p.dino_fingerprint
ORDER BY p.address, photos DESC
LIMIT 100;
"
```

**После этого уже можно точно решить, откуда UI должен получать адрес**, не ломая нынешнюю работающую систему.

И да — результат benchmark это подтверждает: тратить сейчас по 30–600 секунд на 25 клиентов ради 1–3 сомнительных совпадений **не имеет практического смысла**. Qwen-нормализацию замораживаем как отдельный эксперимент, а основную фотобазу продолжаем развивать без неё.

---

### 👤 **User** — 2026-08-20 22:46:06

id |  photo_id   | address | dino_fingerprint |          client          |                filename                 
----+-------------+---------+------------------+--------------------------+-----------------------------------------
  1 | PH_00000001 |         |                  | Единая Россия            | Screenshot from 2026-08-16 00-38-11.png
  2 | PH_00000002 |         | 85_v33           | Единая Россия            | Ашхабадский_01.JPG
  3 | PH_00000003 |         | 85_v33           |                          | Ашхабадский_02.JPG
  4 | PH_00000004 |         | 85_v33           | Сила России              | Ашхабадский_03.JPG
  5 | PH_00000005 |         | 85_v33           |                          | Ашхабадский_04.JPG
  6 | PH_00000006 |         | 85_v33           | АЛЬБИОН-ТУР              | Ашхабадский_05.JPG
  7 | PH_00000007 |         | 85_v33           |                          | Ашхабадский_06.JPG
  8 | PH_00000008 |         | 85_v33           |                          | Ашхабадский_07.JPG
  9 | PH_00000009 |         |                  |                          | Ашхабадский_08.JPG
 10 | PH_00000010 |         | 85_v33           |                          | Ашха:fingerprint_id | address_id |         simple_address         |                        legal_address                         
----------------+------------+--------------------------------+--------------------------------------------------------------
 78_v33         |         78 | Комарова, 13                   | бул. Комарова, 13 В / пр. Космонавтов, сторона Б
 79_v33         |         79 | Комарова-Добровольского, поз.1 | бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б
(2 rows)
---------+------------------+--------
         | 94_v33           |    119
         | 78_v33           |     84
         | 92_v33           |     36
         | 89_v33           |     34
         | 79_v33           |     31
         | 93_v33           |     30
         | 85_v33           |     23
         | 86_v33           |     22
         | 87_v33           |     19
         | 95_v33           |     18
         | 83_v33           |     17
         | 84_v33           |     16
         | 81_v33           |     16
         | 91_v33           |     15
         | 88_v33           |     14
         | 82_v33           |     12
         | 80_v33           |     10
         |                  |      7
         | 90_v33           |      3
(19 rows)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:46:07

> **Remembering**
>
>
> **Reviewed photo address mappings and preserved paused normalization decisions**
>
> 
>
> Worked for 6s

Да. Здесь уже видно правильную схему, и **клиентов пока вообще не трогаем**.

Сейчас данные устроены так:

```text
photos
  dino_fingerprint = 78_v33
          │
          ▼
address_fingerprints
  78_v33 → address_id 78
          │
          ▼
address_directory
  78 → "Комарова, 13"
```

То есть **`photos.address` сейчас пустой - это не проблема**. Адрес надо получать виртуально при загрузке записи, используя `dino_fingerprint`.

Именно эту архитектуру мы уже зафиксировали: `photos.dino_fingerprint → address_fingerprints → address_directory`, без изменения `photos.address_id`. 

При этом сейчас есть важный момент: `85_v33` присутствует у 23 фотографий, но в показанном `address_fingerprints` его нет. Значит для них адрес пока будет `-`, пока fingerprint не появится в справочнике.

### Что я предлагаю сделать сейчас

В `photo_db.py` при загрузке `photos` один раз подтягивать справочник:

```text
fingerprint_id → {
    id,
    simple_address,
    legal_address
}
```

и каждому `record` добавлять виртуальные поля:

```python
record["address_id"]
record["simple_address"]
record["legal_address"]
```

Например:

```text
PH_00000002
dino_fingerprint = 85_v33
address_id       = ?
simple_address   = ?
```

а для:

```text
dino_fingerprint = 78_v33
```

получим:

```text
address_id       = 78
simple_address   = Комарова, 13
legal_address    = бул. Комарова, 13 В / пр. Космонавтов, сторона Б
```

**Физически ничего перемещать и переписывать в `photos.address` не будем.**

После этого уже можно спокойно исправлять отображение грида и карточки фотографии, чтобы они показывали адрес из этого виртуального lookup.

Следующий шаг я бы сделал именно такой: **патчим `photo_db.py`**, чтобы весь UI автоматически получал адрес вместе с `PHOTO_RECORD_INDEX`.

---

### 👤 **User** — 2026-08-20 22:46:59

яне весь вывод показад

---

### 🤖 **Assistant** — 2026-08-20 22:47:00

Понял. Ты показал вывод не целиком, а только фрагменты. Тогда **не делаем выводов по неполному результату**.

Особенно важно не считать, что `85_v33` отсутствует в `address_fingerprints` — по приведённому фрагменту это просто не видно.

Давай сначала получим **полную картину связки фото → fingerprint → адрес**, ничего не меняя в коде.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PHOTO → FINGERPRINT ================" && \
sudo -u postgres psql -d photobase -c "
SELECT
    dino_fingerprint,
    COUNT(*) AS photos
FROM photos
GROUP BY dino_fingerprint
ORDER BY dino_fingerprint;
" && \
echo "================ FINGERPRINT → ADDRESS ================" && \
sudo -u postgres psql -d photobase -c "
SELECT
    af.fingerprint_id,
    af.address_id,
    ad.simple_address,
    ad.legal_address
FROM address_fingerprints af
LEFT JOIN address_directory ad
    ON ad.id = af.address_id
WHERE af.active = TRUE
ORDER BY af.address_id, af.fingerprint_id;
" && \
echo "================ JOIN RESULT ================" && \
sudo -u postgres psql -d photobase -c "
SELECT
    p.dino_fingerprint,
    COUNT(*) AS photos,
    af.address_id,
    ad.simple_address,
    ad.legal_address
FROM photos p
LEFT JOIN address_fingerprints af
    ON af.fingerprint_id = p.dino_fingerprint
   AND af.active = TRUE
LEFT JOIN address_directory ad
    ON ad.id = af.address_id
GROUP BY
    p.dino_fingerprint,
    af.address_id,
    ad.simple_address,
    ad.legal_address
ORDER BY
    p.dino_fingerprint;
"
```

Третий блок для нас самый важный: он покажет **фактическую связь текущих фотографий с адресным справочником**.

После него уже решим, как лучше подключить адрес к отображению, **не трогая клиентов и не меняя данные в `photos`**.

---

### 👤 **User** — 2026-08-20 22:47:20

fingerprint_id | address_id |         simple_address         |                        legal_address                         
----------------+------------+--------------------------------+--------------------------------------------------------------
 78_v33         |         78 | Комарова, 13                   | бул. Комарова, 13 В / пр. Космонавтов, сторона Б
 79_v33         |         79 | Комарова-Добровольского, поз.1 | бул. Комарова, 20В / ул. Добровольского, 9А, п. 1, сторона Б
(2 rows)

(END)

---

### 🤖 **Assistant** — 2026-08-20 22:47:21

Да, теперь понятно: **в `address_fingerprints` сейчас действительно только 2 записи**:

- `78_v33 → 78 → Комарова, 13`
- `79_v33 → 79 → Комарова-Добровольского, поз.1`

Это хорошо объясняет текущую ситуацию. Но прежде чем что-либо менять, я бы **не стал автоматически считать остальные fingerprints потерянными**. Нужно понять, почему справочник адресов содержит только эти два соответствия.

У нас, судя по предыдущему выводу, в `photos` есть много fingerprints:

```text
78_v33
79_v33
80_v33
81_v33
82_v33
83_v33
84_v33
85_v33
...
95_v33
```

А `address_fingerprints` знает только 78 и 79.

### Следующий шаг — просто посмотреть весь `address_directory`

Не меняем ничего. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sudo -u postgres psql -d photobase -c "
SELECT
    id,
    simple_address,
    legal_address,
    active,
    sort_order
FROM address_directory
ORDER BY sort_order, id;
"
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sudo -u postgres psql -d photobase -c "
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE active) AS active
FROM address_directory;
"
```

Мне сейчас важно увидеть, **сколько адресов вообще заведено в справочнике**.

Если там, например, 18–20 адресов, а `address_fingerprints` только 2 — тогда проблема очевидна: **справочник адресов уже загружен, но таблица связей fingerprint → address заполнена только частично**.

И тогда правильное решение будет не в `photo_db.py`, а сначала в восстановлении/заполнении `address_fingerprints`.

---

### 👤 **User** — 2026-08-20 22:47:44

остальные поля просто еще не присвоены

---

### 🤖 **Assistant** — 2026-08-20 22:47:45

Да, тогда всё сходится.

То есть структура **уже правильная**, просто заполнение пока частичное:

```text
address_directory
    ↓
справочник всех адресов

address_fingerprints
    ↓
назначенные fingerprint → address
    ↓
сейчас назначены только 78_v33 и 79_v33

photos
    ↓
dino_fingerprint
    ↓
по нему в будущем определяется адрес
```

И это как раз хороший вариант.

### Тогда ничего в структуре БД не меняем

Не надо:

- заполнять `photos.address`;
- добавлять `address_id` в `photos`;
- делать fuzzy matching;
- подключать Qwen;
- менять существующую схему адресного справочника.

Нужно только сделать **отображение через существующую связь**.

Например, когда у фото:

```text
dino_fingerprint = 78_v33
```

UI получает:

```text
address_id = 78
simple_address = Комарова, 13
legal_address = бул. Комарова, 13 В / пр. Космонавтов, сторона Б
```

А когда fingerprint ещё не присвоен адресу:

```text
dino_fingerprint = 85_v33
```

получаем:

```text
address = —
```

и всё.

### Причём `directory_db.py` уже почти всё умеет

У нас есть:

```python
get_address_directory()
get_address_by_fingerprint()
get_address_for_fingerprint()
```

И запрос уже правильный:

```sql
FROM address_fingerprints
WHERE fingerprint_id = %s
  AND active = TRUE
```

Поэтому я бы **не переписывал `directory_db.py`**.

Следующий небольшой патч — подключить `get_address_for_fingerprint()` к `get_photo_records()` и добавить адрес в `record`.

Тогда вся остальная система — грид, просмотр фото, фильтрация — сможет использовать его без отдельного обращения к БД для каждой фотографии.

**Это сейчас логичный следующий шаг.**

---

### 👤 **User** — 2026-08-20 22:47:54

далее

---

### 🤖 **Assistant** — 2026-08-20 22:47:54

Да. Идём дальше — **делаем адрес виртуальным полем записи фото**, не меняя БД.

Но сначала лучше посмотреть, где формируется `PHOTO_RECORD_INDEX`, чтобы патч был точным и не задеть уже работающий грид.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PHOTO INDEX INIT ================" && \
grep -RniE \
'PHOTO_RECORD_INDEX|build_photo_record_index|get_photo_records' \
app/web/components/photos.py \
app/web/main.py \
app/web \
--include="*.py" | head -n 120
```

И затем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba app/web/components/photos.py | sed -n '1,180p'
```

Покажи вывод.

После этого сделаем **один аккуратный патч**:

```text
PostgreSQL photos
       │
       ▼
get_photo_records()
       │
       ├── client        ← оставляем как есть
       ├── dino_fingerprint
       └── ...
              │
              ▼
      fingerprint lookup
              │
              ▼
       address_id
       simple_address
       legal_address
              │
              ▼
       PHOTO_RECORD_INDEX
              │
              ▼
             UI
```

То есть адрес будет автоматически появляться в карточке фото и дальше его можно будет использовать в гриде/фильтрах, **а неприсвоенные fingerprints просто останутся без адреса**.

---

### 👤 **User** — 2026-08-20 22:48:22

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PHOTO INDEX INIT ================" && \
grep -RniE \
'PHOTO_RECORD_INDEX|build_photo_record_index|get_photo_records' \
app/web/components/photos.py \
app/web/main.py \
app/web \
--include="*.py" | head -n 120
================ PHOTO INDEX INIT ================
app/web/components/photos.py:92:from app.web.photo_db import build_photo_record_index
app/web/components/photos.py:109:PHOTO_RECORD_INDEX: dict[str, dict] = {}
app/web/components/photos.py:267:        PHOTO_RECORD_INDEX.clear()
app/web/components/photos.py:269:        PHOTO_RECORD_INDEX.update(
app/web/components/photos.py:270:            build_photo_record_index(PROJECT_ROOT)
app/web/components/photos.py:276:            len(PHOTO_RECORD_INDEX),
app/web/components/photos.py:301:    for record in PHOTO_RECORD_INDEX.values():
app/web/components/photos.py:728:        record = PHOTO_RECORD_INDEX.get(
app/web/components/photos.py:778:        record = PHOTO_RECORD_INDEX.get(
app/web/components/photos.py:1425:                record_by_path = PHOTO_RECORD_INDEX
app/web/components/technical_modules/data.py:7:from app.web.photo_db import get_photo_records
app/web/components/technical_modules/data.py:246:        db_records = get_photo_records()
app/web/components/photos.py:92:from app.web.photo_db import build_photo_record_index
app/web/components/photos.py:109:PHOTO_RECORD_INDEX: dict[str, dict] = {}
app/web/components/photos.py:267:        PHOTO_RECORD_INDEX.clear()
app/web/components/photos.py:269:        PHOTO_RECORD_INDEX.update(
app/web/components/photos.py:270:            build_photo_record_index(PROJECT_ROOT)
app/web/components/photos.py:276:            len(PHOTO_RECORD_INDEX),
app/web/components/photos.py:301:    for record in PHOTO_RECORD_INDEX.values():
app/web/components/photos.py:728:        record = PHOTO_RECORD_INDEX.get(
app/web/components/photos.py:778:        record = PHOTO_RECORD_INDEX.get(
app/web/components/photos.py:1425:                record_by_path = PHOTO_RECORD_INDEX
app/web/photo_db.py:12:def get_photo_records() -> list[dict]:
app/web/photo_db.py:148:def build_photo_record_index(project_root):
app/web/photo_db.py:153:    records = get_photo_records()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba app/web/components/photos.py | sed -n '1,180p'
     1	from pathlib import Path
     2	from datetime import datetime
     3	import json
     4	import sqlite3
     5	import zipfile
     6	import tempfile
     7	
     8	from nicegui import ui
     9	
    10	from app.web.config import PHOTO_ROOT, DB_PATH, PROJECT_ROOT
    11	
    12	
    13	# ============================================================
    14	# PHOTO PREVIEWS
    15	# ============================================================
    16	
    17	PREVIEW_ROOT = (
    18	    PROJECT_ROOT
    19	    / "data"
    20	    / "preview"
    21	    / "daily"
    22	)
    23	
    24	DAILY_ROOT = (
    25	    PROJECT_ROOT
    26	    / "data"
    27	    / "output"
    28	    / "daily"
    29	)
    30	
    31	
    32	def get_latest_daily_root():
    33	    """Return the newest daily output directory."""
    34	    if not DAILY_ROOT.exists():
    35	        return None
    36	
    37	    runs = [
    38	        path
    39	        for path in DAILY_ROOT.iterdir()
    40	        if path.is_dir()
    41	    ]
    42	
    43	    if not runs:
    44	        return None
    45	
    46	    return max(
    47	        runs,
    48	        key=lambda path: path.name,
    49	    )
    50	
    51	
    52	def get_latest_preview_root():
    53	    """Return the newest daily preview directory."""
    54	    if not PREVIEW_ROOT.exists():
    55	        return None
    56	
    57	    runs = [
    58	        path
    59	        for path in PREVIEW_ROOT.iterdir()
    60	        if path.is_dir()
    61	    ]
    62	
    63	    if not runs:
    64	        return None
    65	
    66	    return max(
    67	        runs,
    68	        key=lambda path: path.name,
    69	    )
    70	
    71	
    72	def get_preview_path(photo_path):
    73	    """Map daily output photo to its preview image."""
    74	    preview_root = get_latest_preview_root()
    75	    daily_root = get_latest_daily_root()
    76	
    77	    if preview_root is None or daily_root is None:
    78	        return None
    79	
    80	    try:
    81	        relative = photo_path.relative_to(daily_root)
    82	    except ValueError:
    83	        return None
    84	
    85	    preview_path = preview_root / relative
    86	
    87	    if preview_path.exists():
    88	        return preview_path
    89	
    90	    return None
    91	from app.web.state import STATE, Photo
    92	from app.web.photo_db import build_photo_record_index
    93	
    94	
    95	IMAGE_EXTENSIONS = {
    96	    ".jpg",
    97	    ".jpeg",
    98	    ".png",
    99	    ".webp",
   100	}
   101	
   102	
   103	# ============================================================
   104	# PHOTO INDEX
   105	# ============================================================
   106	
   107	PHOTO_INDEX: dict[str, list[Path]] = {}
   108	
   109	PHOTO_RECORD_INDEX: dict[str, dict] = {}
   110	
   111	
   112	# ============================================================
   113	# EXIF DATE CACHE
   114	# ============================================================
   115	
   116	PHOTO_TAKEN_DATE_CACHE: dict[str, str | None] = {}
   117	
   118	
   119	def get_photo_taken_date(path):
   120	    """
   121	    Возвращает дату съёмки из EXIF DateTimeOriginal.
   122	
   123	    Результат:
   124	        YYYY-MM-DD
   125	        или None.
   126	
   127	    Значение кэшируется по абсолютному пути.
   128	    """
   129	
   130	    key = str(path.resolve())
   131	
   132	    if key in PHOTO_TAKEN_DATE_CACHE:
   133	        return PHOTO_TAKEN_DATE_CACHE[key]
   134	
   135	    result = None
   136	
   137	    try:
   138	        from PIL import Image
   139	        from PIL.ExifTags import TAGS
   140	
   141	        with Image.open(path) as image:
   142	            exif = image.getexif()
   143	
   144	            if not exif:
   145	                PHOTO_TAKEN_DATE_CACHE[key] = None
   146	                return None
   147	
   148	            date_value = None
   149	
   150	            for tag_id, value in exif.items():
   151	                tag_name = TAGS.get(tag_id, tag_id)
   152	
   153	                if tag_name == "DateTimeOriginal":
   154	                    date_value = value
   155	                    break
   156	
   157	            if date_value:
   158	                value = str(date_value).strip()
   159	
   160	                # EXIF:
   161	                # YYYY:MM:DD HH:MM:SS
   162	                try:
   163	                    dt = datetime.strptime(
   164	                        value[:19],
   165	                        "%Y:%m:%d %H:%M:%S",
   166	                    )
   167	
   168	                    result = dt.strftime("%Y-%m-%d")
   169	
   170	                except ValueError:
   171	                    result = None
   172	
   173	    except Exception as exc:
   174	        print(
   175	            "[EXIF DATE ERROR]",
   176	            path,
   177	            repr(exc),
   178	            flush=True,
   179	        )
   180	
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

