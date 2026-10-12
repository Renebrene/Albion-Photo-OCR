## СЕССИЯ: вторник

**Создано:** 2026-08-18 18:12:03
**Обновлено:** 2026-08-22 20:16:20
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1)

---

### 🤖 **Assistant** — 2026-08-18 22:49:08

Да. Тогда архитектура ещё точнее — **DINO и Qwen стартуют параллельно после получения `id` фотографии**, но дальше ветви разные.

```text
                         IMPORT
                           │
                           ▼
                  Создание записи photos
                           │
                           │
                           ▼
                  PH_00000001
                  source_path
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
          ВЕТКА DINO               ВЕТКА QWEN
          GPU                     GPU
              │                         │
              ▼                         ▼
       присвоение address          описание
              │                  brand / category
              │                  quality / objects
              │                         │
              ▼                         ▼
         SORT / COPY              запись в БД
              │
              ▼
          PREVIEW
              │
              ▼
        preview_path
              │
              ▼
            GRID
```

### То есть главное различие

**Qwen**:

```text
photos.id
   ↓
source_path
   ↓
Qwen
   ↓
qwen_* поля
```

Он **не участвует в сортировке и создании превью**.

**DINO**:

```text
photos.id
   ↓
source_path
   ↓
DINO
   ↓
address
   ↓
сортировка
   ↓
preview
   ↓
preview_path
   ↓
GRID
```

И вот это очень хорошая архитектура, потому что **грид не ждёт Qwen**.

Как только DINO определил адрес и фотография прошла сортировку:

> **она уже может появиться в гриде**, даже если Qwen ещё работает.

Qwen в это время просто дозаполняет карточку:

```text
описание
бренд
категория
качество
объекты
окружение
...
```

### Получается нужное нам поведение

Например, 526 фотографий:

```text
526 записей в photos
        │
        ├── DINO → 526 → сортировка → preview → GRID
        │
        └── Qwen → 526 → metadata
```

И грид начинает работать **не после завершения всего пайплайна**, а постепенно:

```text
DINO обработал 1
  ↓
сортировка
  ↓
preview
  ↓
БД preview_path
  ↓
GRID видит фото №1

DINO обработал 2
  ↓
preview
  ↓
GRID видит фото №2

...
```

При этом Qwen может быть, например:

```text
Qwen: 17 / 526
DINO: 526 / 526
GRID: 526
```

и это совершенно нормально.

**Вот эту схему я бы теперь заморозил.** Дальше уже имеет смысл править код именно под неё: сначала привести Qwen к очереди `photos`, затем сделать DINO → sort → preview → grid, не связывая отображение с завершением Qwen.

---

### 👤 **User** — 2026-08-18 22:49:36

квен нужен тольк о для текстового описания

---

### 🤖 **Assistant** — 2026-08-18 22:49:37

Да. Тогда ещё проще.

**Qwen у нас вообще не участвует в распознавании, сортировке или принятии решений.** Его единственная задача — получить **текстовое описание фотографии** и записать его в БД.

Итоговая схема:

```text id="f2v7cx"
                         IMPORT
                           │
                           ▼
                    photos.id
                    source_path
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
            DINO                      QWEN
              │                         │
              │                         ▼
              │                    description
              │                         │
              ▼                         ▼
           address                  PostgreSQL
              │
              ▼
         SORT / COPY
              │
              ▼
           PREVIEW
              │
              ▼
        preview_path
              │
              ▼
            GRID
```

То есть:

### DINO — основная рабочая ветка

```text id="g6pn5u"
photo
 ↓
DINO
 ↓
address
 ↓
сортировка
 ↓
preview
 ↓
grid
```

### Qwen — независимый обогатитель

```text id="v9p4aa"
photo
 ↓
Qwen
 ↓
description
 ↓
БД
```

Причём **Qwen может закончить намного позже**, а фотография уже будет:

- отсортирована;
- иметь превью;
- отображаться в гриде;
- скачиваться как оригинал.

Когда Qwen закончит — просто появится описание в карточке.

И я бы вообще оставил из Qwen в основной БД только то, что реально нужно для UI:

```text id="6i2jkt"
description
qwen_status
qwen_time_sec
```

А `brand`, `category`, `objects`, `environment` и прочее пока **не используем как логику системы**. Если Qwen их уже выдаёт, можно хранить в `raw_json`, но грид и сортировка от них не зависят.

**Это значительно чище архитектурно.**

---

### 👤 **User** — 2026-08-18 22:50:58

да , бренд - это фрейм клиенты,  а остальное нужны будут только для умного  поиска

---

### 🤖 **Assistant** — 2026-08-18 22:50:59

Да, тогда фиксируем окончательно.

### Роли данных

**DINO — структурная основа фотобазы**

```text id="3q0s5c"
source_path
    ↓
DINO
    ↓
address / ID
    ↓
сортировка
    ↓
preview
    ↓
GRID
```

**Qwen — текстовый слой**

```text id="xq7z0e"
source_path
    ↓
Qwen
    ↓
description
brand
client
прочая семантика
    ↓
БД
```

При этом:

- **`brand`** — это **фрейм клиента**;
- **`description`** — основное текстовое описание фотографии;
- остальные поля Qwen — пока просто **данные для будущего умного поиска**;
- ни один из этих Qwen-параметров **не участвует в присвоении адреса**;
- ни один из них **не блокирует появление фотографии в гриде**.

### В итоге БД становится центральной точкой

```text id="1w9g7v"
                    PH_00000017
                         │
                 ┌───────┴───────┐
                 │               │
               DINO             QWEN
                 │               │
              address       description
                 │              brand
                 │              client
                 │              ...
                 │               │
                 ▼               ▼
              SORT            SEARCH
                 │
              PREVIEW
                 │
                 ▼
                GRID
```

И это хорошо ложится на то, что мы обсуждали раньше: **грид вообще не должен знать, откуда первоначально приехала фотография**.

Он смотрит в БД:

```text
photos
 ├── id
 ├── address
 ├── path
 ├── preview_path
 ├── client
 ├── brand
 ├── description
 └── ...
```

и получает:

**что показывать → `preview_path`**  
**что скачать → `path`**  
**какой адрес → `address`**  
**какой клиент → `client`**  
**что написано на/про фото → `description`**

А потом поверх этого можно спокойно строить **умный поиск** по `description + brand + client + JSON-полям`, не меняя саму архитектуру фотобазы.

---

### 👤 **User** — 2026-08-18 22:51:29

ок

---

### 🤖 **Assistant** — 2026-08-18 22:51:35

Ок. **Эту архитектуру фиксируем.**

Следующий практический шаг — **гриду больше не нужен `DAILY_ROOT` как источник фотографий**: он должен брать список и метаданные из PostgreSQL, `preview_path` — для показа, `path` — для скачивания оригинала с именем `адрес_оригинальное_имя`.

После этого уже можно спокойно доводить автоматическую цепочку:

**ID → DINO → адрес → сортировка → preview → GRID**

параллельно:

**ID → Qwen → description / brand / client / данные для будущего поиска**.

---

### 👤 **User** — 2026-08-18 22:51:48

продолжаем

---

### 🤖 **Assistant** — 2026-08-18 22:51:50

Продолжаем. Сейчас я бы **не трогал сам грид**, пока не переведём Qwen на ту же модель данных.

У нас следующий шаг:

### 1. Qwen перестаёт сканировать `input`

Сейчас он, судя по интерфейсу:

```text
--input
--output
--limit
```

и обрабатывает файлы последовательно из каталога.

Нужно сделать:

```text
photos
  ↓
WHERE qwen_status = 'pending'
  ↓
берём id + source_path
  ↓
Qwen
  ↓
description
  ↓
UPDATE photos
```

То есть `--input` ему больше вообще не нужен.

### 2. DINO оставляем как есть

Он уже работает по правильной схеме:

```text
photos.id
source_path
   ↓
DINO
   ↓
address
```

### 3. После DINO

После определения адреса запускается:

```text
DINO
 ↓
address
 ↓
sort/copy
 ↓
preview
 ↓
UPDATE photos.preview_path
```

И **именно `preview_path` становится источником изображения для грида**.

### 4. Поэтому сейчас сделаем Qwen

Дай мне текущий файл целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,620p' scripts/qwen4b_output_v01.py
```

После этого я переделаю **только Qwen**, не затрагивая DINO и грид.

Цель будет такая:

```text
PH_00000018
source_path=/home/.../data/input/daily/Ашхабадский_18.JPG
        │
        ├──────────────► DINO
        │
        └──────────────► Qwen
                              │
                              ▼
                         description
                              │
                              ▼
                       photos.description
```

И тогда две ветки действительно будут независимыми.

---

### 👤 **User** — 2026-08-18 22:52:23

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,620p' scripts/qwen4b_output_v01.py
#!/usr/bin/env python3

import argparse
import base64
import json
import time
from pathlib import Path

import requests

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data" / "output" / "test_sorted_v2"
OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"

MODEL = "qwen3-vl:4b-instruct"
OLLAMA_URL = "http://localhost:11434/api/chat"

NUM_CTX = 16384
TEMPERATURE = 0

PROMPT = r"""
Ты анализируешь фотографию с улицы для базы наружной рекламы.

Найди рекламный баннер и верни ТОЛЬКО JSON.
Не добавляй пояснений вне JSON.
Не повторяй информацию.
Не придумывай отсутствующую информацию.

Формат:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "banner_type": "видеоэкран",

  "environment": {
    "weather": "",
    "precipitation": "",
    "lighting": ""
  },

  "image_quality": {
    "overall": "",
    "sharpness": "",
    "exposure": "",
    "visibility": "",
    "banner_visible": true,
    "banner_readability": "",
    "motion_blur": false,
    "occlusion": false
  },

  "camera_view": {
    "distance": "",
    "angle": ""
  },

  "analysis_quality": {
    "banner_analysis": "",
    "text_analysis": ""
  },

  "confidence": 0
}

БАННЕР:
client — компания, организация или заказчик.
brand — торговая марка, имя кандидата или рекламируемый бренд.
category — категория рекламы.
text — читаемые надписи на баннере.
colors — основные цвета самого баннера.
objects — основные изображения и предметы НА БАННЕРЕ.
description — краткое описание композиции баннера, максимум 300 символов.
banner_type — на данном этапе "видеоэкран".

ОКРУЖЕНИЕ:
Определи ТОЛЬКО:
weather — солнечно / пасмурно / облачно / туман / неизвестно.
precipitation — нет / дождь / снег / мокрый снег / неизвестно.
lighting — яркий день / дневной свет / сумерки / ночь / искусственное освещение / неизвестно.

Не описывай окружающую сцену.
Не описывай здания, дороги, автомобили, автобусы, людей,
дорожные знаки, провода или растительность.

КАЧЕСТВО:
Оцени только качество фотографии и видимость баннера.

overall — хорошее / удовлетворительное / плохое.
sharpness — резкое / слегка размыто / сильно размыто / неизвестно.
exposure — нормальная / пересвечено / недоэкспонировано / очень тёмное / неизвестно.
visibility — хорошо виден / частично виден / плохо виден / не виден.
banner_visible — true или false.
banner_readability — высокая / средняя / низкая / невозможно определить.
motion_blur — true или false.
occlusion — true или false.

КАМЕРА:
distance — далеко / средняя дистанция / близко / неизвестно.
angle — прямо / слева / справа / сверху / снизу / косой ракурс / неизвестно.

Если баннер не виден:
client = ""
brand = ""
category = ""
text = []
colors = []
objects = []
description = ""
banner_visible = false

Массивы должны содержать только действительно важные элементы.
Не более 10 элементов в каждом массиве.
Не повторяй элементы.

confidence — уверенность в анализе от 0 до 100.
"""

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

def image64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def ask(path: Path) -> dict:

    MAX_ATTEMPTS = 2

    for attempt in range(1, MAX_ATTEMPTS + 1):

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT,
                    "images": [image64(path)],
                }
            ],
            "stream": False,
            "options": {
                "num_ctx": NUM_CTX,
                "temperature": TEMPERATURE,
                "num_predict": 800,
            },
        }

        started = time.time()

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=1800,
        )

        elapsed = time.time() - started

        if response.status_code != 200:
            raise RuntimeError(response.text)

        data = response.json()

        stats = {
            "total_duration_sec": round(
                data.get("total_duration", 0) / 1e9, 2
            ),
            "load_duration_sec": round(
                data.get("load_duration", 0) / 1e9, 2
            ),
            "prompt_eval_duration_sec": round(
                data.get("prompt_eval_duration", 0) / 1e9, 2
            ),
            "eval_duration_sec": round(
                data.get("eval_duration", 0) / 1e9, 2
            ),
            "prompt_eval_count": data.get(
                "prompt_eval_count"
            ),
            "eval_count": data.get(
                "eval_count"
            ),
        }

        print(
            "[OLLAMA]",
            stats,
            flush=True,
        )

        answer = data["message"]["content"]

        cleaned = answer.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "", 1)
            cleaned = cleaned.replace("```", "").strip()

        try:
            result = json.loads(cleaned)

            # JSON есть, но описание пустое — пробуем ещё раз
            description = str(
                result.get("description") or ""
            ).strip()

            if description:
                result["_time_sec"] = round(elapsed, 2)
                return result

            if attempt < MAX_ATTEMPTS:
                print(
                    "[QWEN RETRY]",
                    "description empty",
                    "| attempt:",
                    attempt + 1,
                    flush=True,
                )
                continue

            result["_time_sec"] = round(elapsed, 2)
            return result

        except Exception as exc:

            print(
                "[QWEN JSON ERROR]",
                repr(exc),
                "| attempt:",
                attempt,
                flush=True,
            )

            if attempt < MAX_ATTEMPTS:
                continue

            result = {
                "raw_answer": answer
            }

            result["_time_sec"] = round(elapsed, 2)
            return result

def find_images():

    files = []

    for path in INPUT_DIR.rglob("*"):

        if (
            path.is_file()
            and path.suffix.lower() in IMAGE_EXTENSIONS
        ):
            files.append(path)

    return sorted(files, key=lambda p: str(p).lower())

def output_path(source: Path) -> Path:

    relative = source.relative_to(INPUT_DIR)

    address = relative.parts[0]

    return (
        OUTPUT_DIR
        / address
        / f"{source.stem}.json"
    )

def process(files):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    total_start = time.time()

    results = []

    for index, source in enumerate(files, 1):

        destination = output_path(source)

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        print()
        print("=" * 80)
        print(
            f"[{index}/{len(files)}] "
            f"{source.parent.name}/{source.name}"
        )

        if destination.exists():

            try:
                existing = json.loads(
                    destination.read_text(
                        encoding="utf-8"
                    )
                )

                description = str(
                    existing.get("description") or ""
                ).strip()

            except Exception:
                description = ""

            if description:
                print("SKIP — metadata already exists")

                results.append({
                    "file": source.name,
                    "address": source.parent.name,
                    "status": "skipped",
                })

                continue

            print(
                "REPROCESS — description empty"
            )

        try:

            result = ask(source)

            result["address"] = source.parent.name
            result["source_file"] = str(
                source.relative_to(PROJECT)
            )

            with open(
                destination,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    result,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            elapsed = result.get(
                "_time_sec",
                0
            )

            print(
                "OK",
                "| time:",
                elapsed,
                "sec",
                "| client:",
                result.get("client", ""),
                "| brand:",
                result.get("brand", ""),
                "| confidence:",
                result.get("confidence", "")
            )

            quality = result.get(
                "image_quality",
                {}
            )

            print(
                "QUALITY:",
                quality.get("overall", ""),
                "| sharpness:",
                quality.get("sharpness", ""),
                "| banner:",
                quality.get("banner_visible", "")
            )

            environment = result.get(
                "environment",
                {}
            )

            print(
                "ENV:",
                environment.get("season", ""),
                "|",
                environment.get("weather", ""),
                "|",
                environment.get("precipitation", "")
            )

            results.append({
                "file": source.name,
                "address": source.parent.name,
                "status": "ok",
                "time_sec": elapsed,
                "client": result.get("client", ""),
                "brand": result.get("brand", ""),
                "category": result.get("category", ""),
                "confidence": result.get("confidence", ""),
            })

        except Exception as error:

            print(
                "ERROR:",
                error
            )

            results.append({
                "file": source.name,
                "address": source.parent.name,
                "status": "error",
                "error": str(error),
            })

    total_elapsed = round(
        time.time() - total_start,
        2
    )

    summary = {
        "model": MODEL,
        "input": str(INPUT_DIR),
        "output": str(OUTPUT_DIR),
        "files_in_run": len(files),
        "elapsed_sec": total_elapsed,
        "results": results,
    }

    with open(
        OUTPUT_DIR / "summary.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)
    print(
        "Processed:",
        sum(
            1
            for x in results
            if x["status"] == "ok"
        )
    )
    print(
        "Skipped:",
        sum(
            1
            for x in results
            if x["status"] == "skipped"
        )
    )
    print(
        "Errors:",
        sum(
            1
            for x in results
            if x["status"] == "error"
        )
    )
    print(
        "Total time:",
        total_elapsed,
        "sec"
    )

def main():

    global INPUT_DIR, OUTPUT_DIR

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only N images"
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_DIR,
        help="Input directory with sorted photos"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Output directory for Qwen metadata"
    )

    args = parser.parse_args()

    INPUT_DIR = args.input.expanduser().resolve()
    OUTPUT_DIR = args.output.expanduser().resolve()

    files = find_images()

    print("=" * 80)
    print("QWEN3-VL 4B — OUTPUT ANALYSIS")
    print("=" * 80)
    print()
    print("MODEL:", MODEL)
    print("INPUT:", INPUT_DIR)
    print("OUTPUT:", OUTPUT_DIR)
    print("FOUND:", len(files))
    print("NUM_CTX:", NUM_CTX)
    print("TEMPERATURE:", TEMPERATURE)
    print()

    if args.limit is not None:
        files = files[:args.limit]
        print("LIMIT:", args.limit)
        print()

    if not files:
        print("No images found.")
        return

    process(files)

if __name__ == "__main__":
    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:52:31

> **Updating the processing flow**
>
> I’m treating Qwen as a description-only worker while keeping brand, client, category, and other fields in the existing database workflow. I’ll replace filesystem output with queued database records and retry failed descriptions.
>
> ****
>
> 
>
> **Updating Qwen OCR Worker for Database Storage**
>
>
> **Updating Qwen OCR Worker for Database Storage**
>
> 
>
> Worked for 23s

Да, файл у тебя полный — этого достаточно. Я бы сейчас **не менял промпт и не урезал Qwen**, а поменял только способ получения задания и сохранения результата.

Новая логика Qwen должна быть такой:

```text
photos
  │
  ├─ qwen_status = pending
  │
  ▼
берём id + source_path
  │
  ▼
Qwen читает source_path
  │
  ▼
description
client / brand
прочие JSON-поля
  │
  ▼
UPDATE photos
```

При этом **никаких `data/output/test_sorted_v2`, `OUTPUT_DIR` и отдельных JSON-файлов для работы Qwen больше не требуется**.

И важный момент: `source_path` у тебя уже правильный:

```text
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_01.JPG
```

То есть Qwen и DINO действительно будут брать **один и тот же оригинал**.

### Что я предлагаю сделать сейчас

Перед изменением сделаем резервную копию:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp scripts/qwen4b_output_v01.py \
   scripts/qwen4b_output_v01.py.bak
```

А затем перепишем worker.

После этого запуск будет просто:

```bash
uv run python scripts/qwen4b_output_v01.py --limit 1
```

Он должен показать примерно:

```text
QWEN3-VL 4B — DATABASE WORKER
DATABASE: photobase
PENDING: 526

[1] PH_00000001 Screenshot...
SOURCE: /home/alexice/.../data/input/daily/...

[OLLAMA] {...}

OK | time: 9.8 sec | client: ... | brand: ...
DESCRIPTION: ...
```

И главное — после обработки в PostgreSQL:

```text
qwen_status = done
description = ...
client = ...
brand = ...
qwen_time_sec = ...
...
```

**Никаких файлов в `data/metadata/qwen4b` для функционирования системы.**

А `raw_json` можно оставить как архив полного ответа Qwen — это как раз пригодится для будущего умного поиска.

Только один нюанс: моя попытка автоматически записать файл в твою рабочую директорию здесь не прошла, потому что твой проект находится на твоей машине, а не в доступной мне файловой среде. Поэтому **не запускай пока ничего из моего предыдущего ответа**.

Я дам тебе точную команду замены следующим сообщением, чтобы ты вставил её непосредственно в `NEURO`.

---

### 👤 **User** — 2026-08-18 22:53:16

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cp scripts/qwen4b_output_v01.py \
   scripts/qwen4b_output_v01.py.bak
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python scripts/qwen4b_output_v01.py --limit 1
================================================================================
QWEN3-VL 4B — OUTPUT ANALYSIS
================================================================================

MODEL: qwen3-vl:4b-instruct
INPUT: /home/alexice/projects/scene_fingerprint_mvp_v02/data/output/test_sorted_v2
OUTPUT: /home/alexice/projects/scene_fingerprint_mvp_v02/data/metadata/qwen4b
FOUND: 0
NUM_CTX: 16384
TEMPERATURE: 0

LIMIT: 1

No images found.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:53:18

Да, это ожидаемо: **мы пока только сделали backup, сам `qwen4b_output_v01.py` ещё не переделали**. Поэтому он всё ещё смотрит в старый:

```text
data/output/test_sorted_v2
```

Теперь меняем его на **DB worker**.

Сделай так:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/qwen4b_output_v01.py <<'PY'
#!/usr/bin/env python3

import argparse
import base64
import json
import os
import time

import psycopg2
from psycopg2.extras import RealDictCursor
import requests

# ============================================================
# CONFIG
# ============================================================

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

MODEL = "qwen3-vl:4b-instruct"
OLLAMA_URL = "http://localhost:11434/api/chat"

NUM_CTX = 16384
TEMPERATURE = 0

# ============================================================
# PROMPT
# ============================================================

PROMPT = r"""
Ты анализируешь фотографию с улицы для базы наружной рекламы.

Найди рекламный баннер и верни ТОЛЬКО JSON.
Не добавляй пояснений вне JSON.
Не повторяй информацию.
Не придумывай отсутствующую информацию.

Формат:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "banner_type": "видеоэкран",

  "environment": {
    "weather": "",
    "precipitation": "",
    "lighting": ""
  },

  "image_quality": {
    "overall": "",
    "sharpness": "",
    "exposure": "",
    "visibility": "",
    "banner_visible": true,
    "banner_readability": "",
    "motion_blur": false,
    "occlusion": false
  },

  "camera_view": {
    "distance": "",
    "angle": ""
  },

  "analysis_quality": {
    "banner_analysis": "",
    "text_analysis": ""
  },

  "confidence": 0
}

БАННЕР:
client — компания, организация или заказчик.
brand — торговая марка, имя кандидата или рекламируемый бренд.
category — категория рекламы.
text — читаемые надписи на баннере.
colors — основные цвета самого баннера.
objects — основные изображения и предметы НА БАННЕРЕ.
description — краткое описание композиции баннера, максимум 300 символов.
banner_type — на данном этапе "видеоэкран".

ОКРУЖЕНИЕ:
Определи ТОЛЬКО:
weather — солнечно / пасмурно / облачно / туман / неизвестно.
precipitation — нет / дождь / снег / мокрый снег / неизвестно.
lighting — яркий день / дневной свет / сумерки / ночь / искусственное освещение / неизвестно.

Не описывай окружающую сцену.
Не описывай здания, дороги, автомобили, автобусы, людей,
дорожные знаки, провода или растительность.

КАЧЕСТВО:
Оцени только качество фотографии и видимость баннера.

overall — хорошее / удовлетворительное / плохое.
sharpness — резкое / слегка размыто / сильно размыто / неизвестно.
exposure — нормальная / пересвечено / недоэкспонировано / очень тёмное / неизвестно.
visibility — хорошо виден / частично виден / плохо виден / не виден.
banner_visible — true или false.
banner_readability — высокая / средняя / низкая / невозможно определить.
motion_blur — true или false.
occlusion — true или false.

КАМЕРА:
distance — далеко / средняя дистанция / близко / неизвестно.
angle — прямо / слева / справа / сверху / снизу / косой ракурс / неизвестно.

Если баннер не виден:
client = ""
brand = ""
category = ""
text = []
colors = []
objects = []
description = ""
banner_visible = false

Массивы должны содержать только действительно важные элементы.
Не более 10 элементов в каждом массиве.
Не повторяй элементы.

confidence — уверенность в анализе от 0 до 100.
"""

# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def claim_photo(conn):
    """
    Берёт одну фотографию из очереди Qwen.

    Для Qwen источником всегда является source_path.
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:

        cur.execute(
            """
            SELECT
                id,
                photo_id,
                source_path,
                filename
            FROM photos
            WHERE qwen_status = 'pending'
              AND source_path IS NOT NULL
              AND source_path <> ''
            ORDER BY id
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )

        row = cur.fetchone()

        if row is None:
            conn.commit()
            return None

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (row["id"],),
        )

        conn.commit()

        return row

def mark_done(conn, photo_id, result, elapsed):
    """
    Сохраняет Qwen-результат непосредственно в PostgreSQL.
    """

    text_json = result.get("text", [])
    colors_json = result.get("colors", [])
    objects_json = result.get("objects", [])
    environment_json = result.get("environment", {})
    image_quality_json = result.get("image_quality", {})
    camera_view_json = result.get("camera_view", {})
    scene_objects_json = result.get("objects", [])
    analysis_quality_json = result.get("analysis_quality", {})

    raw_json = dict(result)

    # В БД служебное время отдельно.
    raw_json.pop("_time_sec", None)

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'done',

                client = %s,
                brand = %s,
                category = %s,
                description = %s,
                confidence = %s,

                qwen_time_sec = %s,

                text_json = %s::jsonb,
                colors_json = %s::jsonb,
                objects_json = %s::jsonb,
                environment_json = %s::jsonb,
                image_quality_json = %s::jsonb,
                camera_view_json = %s::jsonb,
                scene_objects_json = %s::jsonb,
                analysis_quality_json = %s::jsonb,
                raw_json = %s::jsonb,

                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = %s
            """,
            (
                result.get("client") or None,
                result.get("brand") or None,
                result.get("category") or None,
                result.get("description") or None,
                result.get("confidence"),

                elapsed,

                json.dumps(
                    text_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    colors_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    objects_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    environment_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    image_quality_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    camera_view_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    scene_objects_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    analysis_quality_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    raw_json,
                    ensure_ascii=False,
                ),

                photo_id,
            ),
        )

    conn.commit()

def mark_error(conn, photo_id, error):
    message = str(error)

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'error',
                error_message = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                message[:4000],
                photo_id,
            ),
        )

    conn.commit()

# ============================================================
# IMAGE
# ============================================================

def image64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ============================================================
# QWEN
# ============================================================

def ask(path):

    max_attempts = 2

    for attempt in range(1, max_attempts + 1):

        payload = {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": PROMPT,
                    "images": [image64(path)],
                }
            ],
            "stream": False,
            "options": {
                "num_ctx": NUM_CTX,
                "temperature": TEMPERATURE,
                "num_predict": 800,
            },
        }

        started = time.time()

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=1800,
        )

        elapsed = time.time() - started

        if response.status_code != 200:
            raise RuntimeError(response.text)

        data = response.json()

        stats = {
            "total_duration_sec": round(
                data.get("total_duration", 0) / 1e9,
                2,
            ),
            "load_duration_sec": round(
                data.get("load_duration", 0) / 1e9,
                2,
            ),
            "prompt_eval_duration_sec": round(
                data.get("prompt_eval_duration", 0) / 1e9,
                2,
            ),
            "eval_duration_sec": round(
                data.get("eval_duration", 0) / 1e9,
                2,
            ),
            "prompt_eval_count": data.get(
                "prompt_eval_count"
            ),
            "eval_count": data.get(
                "eval_count"
            ),
        }

        print(
            "[OLLAMA]",
            stats,
            flush=True,
        )

        answer = data["message"]["content"]

        cleaned = answer.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace(
                "```json",
                "",
                1,
            )
            cleaned = cleaned.replace(
                "```",
                "",
            ).strip()

        try:

            result = json.loads(cleaned)

            description = str(
                result.get("description") or ""
            ).strip()

            if description:
                result["_time_sec"] = round(
                    elapsed,
                    2,
                )
                return result

            if attempt < max_attempts:

                print(
                    "[QWEN RETRY]",
                    "description empty",
                    "| attempt:",
                    attempt + 1,
                    flush=True,
                )

                continue

            result["_time_sec"] = round(
                elapsed,
                2,
            )

            return result

        except Exception as exc:

            print(
                "[QWEN JSON ERROR]",
                repr(exc),
                "| attempt:",
                attempt,
                flush=True,
            )

            if attempt < max_attempts:
                continue

            result = {
                "raw_answer": answer,
            }

            result["_time_sec"] = round(
                elapsed,
                2,
            )

            return result

# ============================================================
# WORKER
# ============================================================

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only N pending photos",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("QWEN3-VL 4B — DATABASE WORKER")
    print("=" * 80)
    print("MODEL:", MODEL)
    print("DATABASE:", DB_CONFIG["dbname"])
    print()

    conn = get_connection()

    processed = 0
    errors = 0

    try:

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)
                FROM photos
                WHERE qwen_status = 'pending'
                """
            )

            pending = cur.fetchone()[0]

        print(
            "PENDING:",
            pending,
        )
        print()

        while True:

            if (
                args.limit is not None
                and processed >= args.limit
            ):
                print(
                    "LIMIT REACHED:",
                    args.limit,
                )
                break

            row = claim_photo(conn)

            if row is None:

                print(
                    "QWEN QUEUE EMPTY"
                )

                break

            db_id = row["id"]
            photo_id = row["photo_id"]
            source_path = row["source_path"]

            print("=" * 80)
            print(
                f"[{processed + 1}]",
                photo_id,
            )
            print(
                "SOURCE:",
                source_path,
            )

            started = time.time()

            try:

                path = Path(source_path)

                if not path.exists():
                    raise FileNotFoundError(
                        f"Photo not found: {path}"
                    )

                if not path.is_file():
                    raise FileNotFoundError(
                        f"Not a file: {path}"
                    )

                result = ask(path)

                elapsed = time.time() - started

                mark_done(
                    conn,
                    db_id,
                    result,
                    elapsed,
                )

                print(
                    "OK",
                    "| time:",
                    round(elapsed, 2),
                    "sec",
                    "| client:",
                    result.get("client", ""),
                    "| brand:",
                    result.get("brand", ""),
                    "| confidence:",
                    result.get("confidence", ""),
                )

                print(
                    "DESCRIPTION:",
                    result.get(
                        "description",
                        "",
                    ),
                )

                quality = result.get(
                    "image_quality",
                    {},
                )

                print(
                    "QUALITY:",
                    quality.get(
                        "overall",
                        "",
                    ),
                    "| sharpness:",
                    quality.get(
                        "sharpness",
                        "",
                    ),
                    "| banner:",
                    quality.get(
                        "banner_visible",
                        "",
                    ),
                )

                environment = result.get(
                    "environment",
                    {},
                )

                print(
                    "ENV:",
                    environment.get(
                        "weather",
                        "",
                    ),
                    "|",
                    environment.get(
                        "precipitation",
                        "",
                    ),
                )

                processed += 1

            except Exception as exc:

                errors += 1

                elapsed = time.time() - started

                print(
                    "ERROR:",
                    exc,
                    "| time:",
                    round(elapsed, 2),
                    "sec",
                )

                try:
                    mark_error(
                        conn,
                        db_id,
                        exc,
                    )
                except Exception as db_error:

                    print(
                        "DB ERROR:",
                        db_error,
                    )

    finally:

        conn.close()

        print()
        print("=" * 80)
        print("QWEN WORKER STOPPED")
        print("=" * 80)
        print(
            "PROCESSED:",
            processed,
        )
        print(
            "ERRORS:",
            errors,
        )

if __name__ == "__main__":
    main()
PY
```

После записи **пока не запускай 526 фотографий**. Сначала проверим синтаксис и очередь:

```bash
uv run python scripts/qwen4b_output_v01.py --help
```

а затем:

```bash
uv run python scripts/qwen4b_output_v01.py --limit 1
```

Если всё хорошо, он возьмёт **первую `qwen_status='pending'` запись из PostgreSQL**, прочитает именно её `source_path` и запишет результат обратно в эту же строку.

И после одного теста проверим:

```bash
psql -U lora -d photobase -c "
SELECT
    id,
    photo_id,
    filename,
    qwen_status,
    client,
    brand,
    description,
    qwen_time_sec
FROM photos
ORDER BY id
LIMIT 3;
"
```

**Пока не меняем DINO и `photos.py`.** Сначала убеждаемся, что эта ветка `ID → Qwen → БД` работает правильно.

---

### 👤 **User** — 2026-08-18 22:54:05

================================================================================
[1] PH_00000525
SOURCE: /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (8).JPG
ERROR: name 'Path' is not defined | time: 0.0 sec
================================================================================
[1] PH_00000526
SOURCE: /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (9).JPG
ERROR: name 'Path' is not defined | time: 0.0 sec
QWEN QUEUE EMPTY

================================================================================
QWEN WORKER STOPPED
================================================================================
PROCESSED: 0
ERRORS: 526
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:54:08

Да, ошибка моя: в новой версии я использовал `Path`, но не добавил импорт.

Из-за этого **все 526 фотографий получили `qwen_status='error'`**, поэтому перед повторным запуском нужно вернуть их в `pending`.

### 1. Исправляем импорт

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -i 's/^import time$/import time\nfrom pathlib import Path/' scripts/qwen4b_output_v01.py

head -15 scripts/qwen4b_output_v01.py
```

В начале должно быть:

```text
import argparse
import base64
import json
import os
import time
from pathlib import Path
```

### 2. Возвращаем ошибочные записи Qwen в очередь

```bash
psql -U lora -d photobase -c "
UPDATE photos
SET
    qwen_status = 'pending',
    error_message = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE qwen_status = 'error';
"
```

Проверяем:

```bash
psql -U lora -d photobase -c "
SELECT qwen_status, count(*)
FROM photos
GROUP BY qwen_status
ORDER BY qwen_status;
"
```

Должно быть примерно:

```text
 qwen_status | count
-------------+-------
 pending     | 526
```

### 3. Сначала только одна фотография

```bash
uv run python scripts/qwen4b_output_v01.py --limit 1
```

Если всё правильно, теперь должно быть примерно:

```text
[1] PH_00000525
SOURCE: /home/alexice/.../Шолохова 127 А (8).JPG

[OLLAMA] ...

OK | time: 10.xx sec | client: ... | brand: ...
DESCRIPTION: ...

QWEN WORKER STOPPED
PROCESSED: 1
ERRORS: 0
```

После этого сразу проверим запись:

```bash
psql -U lora -d photobase -c "
SELECT
    id,
    photo_id,
    filename,
    qwen_status,
    client,
    brand,
    description,
    qwen_time_sec
FROM photos
WHERE photo_id = 'PH_00000525';
"
```

**Пока 526 повторно не запускаем.** Сначала убеждаемся, что одна запись полностью прошла цепочку:

`photo_id → source_path → Qwen → PostgreSQL`.

---

### 👤 **User** — 2026-08-18 22:54:31

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ psql -U lora -d photobase -c "
UPDATE photos
SET
    qwen_status = 'pending',
    error_message = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE qwen_status = 'error';
"
psql: error: connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed: FATAL:  Peer authentication failed for user "lora"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:54:34

Да, это уже **не ошибка проекта**. PostgreSQL настроен так, что локальное подключение через Unix socket требует peer-аутентификацию, а системный пользователь `alexice` не может войти как PostgreSQL-пользователь `lora`.

Но сам Python worker подключается через `psycopg2`, и у него это уже работает.

Поэтому проще сделать сброс статусов **через Python**, используя тот же `DB_CONFIG`, что и worker.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import psycopg2
import os

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

conn = psycopg2.connect(**DB_CONFIG)

with conn.cursor() as cur:
    cur.execute("""
        UPDATE photos
        SET
            qwen_status = 'pending',
            error_message = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE qwen_status = 'error'
    """)

    print("RESET:", cur.rowcount)

conn.commit()
conn.close()
PY
```

Затем:

```bash
uv run python scripts/qwen4b_output_v01.py --limit 1
```

### Почему это произошло

Команда:

```bash
psql -U lora -d photobase
```

идёт через:

```text
/var/run/postgresql/.s.PGSQL.5432
```

и PostgreSQL отвечает:

```text
Peer authentication failed
```

А worker использует:

```python
psycopg2.connect(**DB_CONFIG)
```

с:

```text
host=localhost
user=lora
```

то есть подключается через TCP и использует другую схему аутентификации.

**После успешного теста Qwen уже не будем трогать.** Потом перейдём непосредственно к следующей части — **DINO → сортировка → preview → GRID**.

---

### 👤 **User** — 2026-08-18 22:55:12

[1] PH_00000001
SOURCE: /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Screenshot from 2026-08-16 00-38-11.png
[OLLAMA] {'total_duration_sec': 9.49, 'load_duration_sec': 2.73, 'prompt_eval_duration_sec': 1.11, 'eval_duration_sec': 5.58, 'prompt_eval_count': 1875, 'eval_count': 505}
OK | time: 9.49 sec | client: Единая Россия | brand: Дмитрий Сизякин | confidence: 95
DESCRIPTION: Политический рекламный баннер с изображением кандидата в думу Дмитрия Сизякина, главного врача ЦГБ им. Семашко. Баннер синий, с белыми и красными элементами. Вверху — логотип партии «Единая Россия». Надпись «Помогать каждому!».
QUALITY: удовлетворительное | sharpness: слегка размыто | banner: True
ENV: солнечно | нет
LIMIT REACHED: 1

================================================================================
QWEN WORKER STOPPED
================================================================================
PROCESSED: 1
ERRORS: 0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:55:14

Отлично. **Ветка Qwen теперь работает правильно.**

Получилось именно то, что мы хотели:

```text
photo_id
   ↓
source_path
   ↓
Qwen3-VL 4B
   ↓
PostgreSQL
```

Тестовая запись `PH_00000001` обработана за **9.49 с**, ошибок нет.

Причём результат уже нормально разделяется:

- `client` → **Единая Россия**
- `brand` → **Дмитрий Сизякин**
- `description` → текстовое описание для поиска
- `confidence` → 95
- `text_json`
- `colors_json`
- `objects_json`
- `environment_json`
- `image_quality_json`
- `camera_view_json`
- `analysis_quality_json`
- `raw_json`

То есть **отдельные JSON-файлы Qwen больше не нужны** — PostgreSQL теперь является источником этих данных.

### Теперь важное

У нас получается именно такая архитектура:

```text
                    PHOTO ID
                       │
                       ▼
              source_path / input
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
            DINO              QWEN
              │                 │
              │                 └──► описание
              │                      клиент
              │                      бренд
              │                      поиск
              ▼
          присвоение ID
              │
              ▼
           сортировка
              │
              ▼
           preview
              │
              ▼
             GRID
```

Но поскольку **ID уже присвоен до этих ветвей**, фактически DINO/Qwen могут работать параллельно.

И самое главное для грида:

```text
PostgreSQL
   │
   ├── photo_id
   ├── address
   ├── filename
   ├── source_path
   ├── preview_path
   ├── client
   ├── brand
   ├── description
   └── ...
        │
        ▼
       GRID
        │
        └── preview_path → показывает preview
```

А при скачивании:

```text
GRID
 ↓
выбрано фото
 ↓
DB → source_path
 ↓
оригинал
 ↓
скачивание
 ↓
имя: АДРЕС_оригинальное_имя.JPG
```

### Следующий шаг

Теперь я бы **не трогал Qwen вообще**.

Переходим к `photos.py` и делаем главное изменение, которое мы обсуждали:

> **Грид не должен сканировать `data/output/daily` и ждать кнопку. Он должен сразу строиться из PostgreSQL.**

При этом `preview_path` уже есть в таблице — значит, нам вообще не нужно вычислять:

```python
get_latest_daily_root()
get_latest_preview_root()
get_preview_path()
```

для нормальной работы грида.

Следующим шагом разберём `photos.py` и переведём его на схему:

**PostgreSQL → preview_path → GRID**,  
а **source_path → скачивание оригинала**.

---

### 👤 **User** — 2026-08-18 22:56:05

присвоение ID  должно быть самым первым этапом - с этим id будут рабоать дино и квен

---

### 🤖 **Assistant** — 2026-08-18 22:56:05

Да. Именно так и фиксируем архитектуру.

**ID присваивается один раз и является первичным идентификатором фотографии.** После этого ни DINO, ни Qwen не должны самостоятельно создавать/определять другой ID.

```text
                    ФОТО В INPUT
                         │
                         ▼
                ┌─────────────────┐
                │  1. IMPORT / ID  │
                │  PH_00000001     │
                │  PH_00000002     │
                │       ...        │
                └────────┬────────┘
                         │
                  photo_id = PH_...
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        ┌───────────┐         ┌───────────┐
        │   DINO    │         │   QWEN    │
        │           │         │           │
        │ source_path         │ source_path
        │ photo_id  │         │ photo_id  │
        └─────┬─────┘         └─────┬─────┘
              │                     │
              ▼                     ▼
          address ID            metadata
              │                 client
              │                 brand
              │                 description
              │
              ▼
          SORT / COPY
              │
              ▼
           PREVIEW
              │
              ▼
             GRID
```

### То есть у нас два разных понятия

**`photo_id`**

```text
PH_00000525
```

Это **постоянный ID фотографии**. Он появляется первым.

**`address` / `dino_fingerprint` / `dino_score`**

Это уже **результаты обработки фотографии**, которые появляются позже.

Например:

```text
id              = 525
photo_id        = PH_00000525
source_path     = /data/input/daily/Шолохова 127 А (8).JPG

dino_status     = done
dino_fingerprint = 78_v33
dino_score      = ...
address         = 78

qwen_status     = done
client          = ...
brand           = ...
description     = ...
```

И принципиально:

> **Qwen не знает и не должен знать ничего о присвоении ID. Он получает `photo_id` из БД и обрабатывает соответствующий `source_path`.**

То же самое DINO.

### Тогда порядок pipeline окончательно такой

**Этап 1 — Import**

```text
INPUT
 ↓
создать запись photos
 ↓
photo_id
 ↓
source_path
 ↓
dino_status = pending
qwen_status = pending
```

**Этап 2 — параллельная обработка**

```text
             photo_id
                │
        ┌───────┴───────┐
        ▼               ▼
      DINO             QWEN
        │               │
        ▼               ▼
   адрес/оценка      описание/метаданные
```

**Этап 3 — DINO**

```text
DINO
 ↓
определил адрес
 ↓
сортировка
 ↓
создание preview
 ↓
preview_path записывается в БД
```

**Этап 4 — GRID**

```text
PostgreSQL
 ↓
photo_id
address
preview_path
client
brand
description
...
 ↓
GRID
```

А **оригинал при скачивании всегда берётся по `source_path`**.

Это как раз решает твою предыдущую мысль: **input может меняться, а база и ID остаются стабильными**. Гриду вообще не важно, откуда первоначально приехала фотография — ему нужны запись БД и `preview_path`.

Следующим я бы проверил **какой код сейчас создаёт `PH_00000001` и когда именно создаётся запись `photos`**, чтобы первым этапом сделать именно этот импорт, а уже затем запускать два worker-а.

---

### 👤 **User** — 2026-08-18 22:57:16

давай

---

### 🤖 **Assistant** — 2026-08-18 22:57:18

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed scene fingerprint importer and photo ID pipeline stages**
>
> 
>
> Worked for 9s

Да. Начинаем именно с **первого этапа - Import → постоянный `photo_id`**.

У нас уже есть отдельный `scripts/photo_ingest.py`, который как раз должен отвечать за это. 

Сейчас не будем ничего переделывать вслепую. Посмотрим его текущую реализацию и SQL-структуру вокруг вставки записи.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,320p' scripts/photo_ingest.py
```

И одновременно найдем **все места, где создаётся `PH_...` или вставляется запись в `photos`**:

```bash
grep -RniE \
'PH_[0-9]|photo_id|INSERT INTO photos|next.*photo|MAX.*photo' \
scripts app \
--include="*.py" | head -200
```

И ещё посмотрим структуру самой таблицы:

```bash
python3 - <<'PY'
import psycopg2
import os

conn = psycopg2.connect(
    host=os.getenv("PHOTOBASE_HOST", "localhost"),
    port=int(os.getenv("PHOTOBASE_PORT", "5432")),
    user=os.getenv("PHOTOBASE_USER", "lora"),
    password=os.getenv("PHOTOBASE_PASSWORD", ""),
    dbname=os.getenv("PHOTOBASE_DB", "photobase"),
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'photos'
        ORDER BY ordinal_position
    """)

    for row in cur.fetchall():
        print(row)

conn.close()
PY
```

**Сейчас нас интересует только это:**

```text
INPUT
  ↓
photo_ingest.py
  ↓
создание записи photos
  ↓
photo_id = PH_XXXXXXXX
  ↓
dino_status = pending
qwen_status = pending
```

После этого уже:

```text
                 PH_XXXXXXXX
                     │
              source_path
                /       \
               /         \
            DINO         QWEN
```

И я отдельно проверю, чтобы **повторный запуск ingest не создавал новый `photo_id` для уже известного `source_path`**. Это важно, потому что именно `photo_id` у нас теперь является постоянным идентификатором фотографии.

---

### 👤 **User** — 2026-08-18 22:58:11

ERRORS: 0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,320p' scripts/photo_ingest.py
#!/usr/bin/env python3

import argparse
from pathlib import Path

import psycopg2

PROJECT = Path(__file__).resolve().parent.parent

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

def get_next_photo_number(conn):
    """
    Возвращает следующий числовой номер PHOTO_ID.

    Например:
        PH_00000100 -> 100
        следующий -> 101

    Если фотографий ещё нет:
        -> 1
    """

    with conn.cursor() as cur:

        cur.execute("""
            SELECT photo_id
            FROM photos
            WHERE photo_id LIKE 'PH_%'
        """)

        rows = cur.fetchall()

    max_number = 0

    for (photo_id,) in rows:

        if not photo_id:
            continue

        try:
            number = int(
                str(photo_id)
                .replace("PH_", "", 1)
            )
        except ValueError:
            continue

        max_number = max(
            max_number,
            number,
        )

    return max_number + 1

def make_photo_id(number):
    return f"PH_{number:08d}"

def normalize_path(path):
    return str(
        Path(path)
        .expanduser()
        .resolve()
    )

def get_existing_source_paths(conn):
    """
    Загружает уже зарегистрированные source_path.
    """

    with conn.cursor() as cur:

        cur.execute("""
            SELECT source_path
            FROM photos
            WHERE source_path IS NOT NULL
        """)

        return {
            normalize_path(row[0])
            for row in cur.fetchall()
            if row[0]
        }

def find_images(input_dir):
    """
    Берёт только файлы непосредственно из входной папки.
    Подкаталоги пока не сканируем.
    """

    return sorted(
        (
            p
            for p in input_dir.iterdir()
            if (
                p.is_file()
                and p.suffix.lower()
                in IMAGE_EXTENSIONS
            )
        ),
        key=lambda p: p.name.casefold(),
    )

def register_photo(
    conn,
    photo_id,
    source_path,
):
    """
    Создаёт первичную запись фотографии.

    Никаких DINO/Qwen/сортировок здесь нет.
    """

    filename = Path(source_path).name

    with conn.cursor() as cur:

        cur.execute("""
            INSERT INTO photos (
                photo_id,

                source_path,
                path,

                filename,
                original_filename,

                status,

                dino_status,
                qwen_status,
                sort_status,
                preview_status
            )
            VALUES (
                %s,

                %s,
                %s,

                %s,
                %s,

                'pending',

                'pending',
                'pending',
                'pending',
                'pending'
            )
        """, (
            photo_id,

            source_path,
            source_path,

            filename,
            filename,
        ))

def ingest(input_dir):

    input_dir = input_dir.expanduser().resolve()

    if not input_dir.exists():
        raise RuntimeError(
            f"Input directory does not exist:\n{input_dir}"
        )

    if not input_dir.is_dir():
        raise RuntimeError(
            f"Input path is not a directory:\n{input_dir}"
        )

    images = find_images(input_dir)

    print("=" * 80)
    print("PHOTO INGEST")
    print("=" * 80)
    print()
    print("INPUT :", input_dir)
    print("FILES :", len(images))
    print()

    if not images:
        print("No images found.")
        return

    with psycopg2.connect(**PG_CONFIG) as conn:

        existing_paths = get_existing_source_paths(conn)

        next_number = get_next_photo_number(conn)

        registered = 0
        skipped = 0

        for image in images:

            source_path = normalize_path(image)

            # ------------------------------------------------
            # Уже зарегистрировано
            # ------------------------------------------------

            if source_path in existing_paths:

                print(
                    f"[SKIP]     {image.name}"
                    f" — already registered"
                )

                skipped += 1

                continue

            # ------------------------------------------------
            # Новый photo_id
            # ------------------------------------------------

            photo_id = make_photo_id(
                next_number
            )

            register_photo(
                conn,
                photo_id,
                source_path,
            )

            existing_paths.add(
                source_path
            )

            print(
                f"[REGISTER] {photo_id}"
                f"  {image.name}"
            )

            registered += 1
            next_number += 1

        conn.commit()

    print()
    print("=" * 80)
    print("INGEST FINISHED")
    print("=" * 80)
    print()
    print("Found      :", len(images))
    print("Registered :", registered)
    print("Skipped    :", skipped)
    print()

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Register new photos and assign permanent photo_id"
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Directory with incoming photos",
    )

    args = parser.parse_args()

    ingest(
        args.input
    )

if __name__ == "__main__":
    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -RniE \
'PH_[0-9]|photo_id|INSERT INTO photos|next.*photo|MAX.*photo' \
scripts app \
--include="*.py" | head -200
scripts/photo_ingest.py:26:def get_next_photo_number(conn):
scripts/photo_ingest.py:28:    Возвращает следующий числовой номер PHOTO_ID.
scripts/photo_ingest.py:31:        PH_00000100 -> 100
scripts/photo_ingest.py:41:            SELECT photo_id
scripts/photo_ingest.py:43:            WHERE photo_id LIKE 'PH_%'
scripts/photo_ingest.py:50:    for (photo_id,) in rows:
scripts/photo_ingest.py:52:        if not photo_id:
scripts/photo_ingest.py:57:                str(photo_id)
scripts/photo_ingest.py:71:def make_photo_id(number):
scripts/photo_ingest.py:125:    photo_id,
scripts/photo_ingest.py:139:            INSERT INTO photos (
scripts/photo_ingest.py:140:                photo_id,
scripts/photo_ingest.py:172:            photo_id,
scripts/photo_ingest.py:214:        next_number = get_next_photo_number(conn)
scripts/photo_ingest.py:239:            # Новый photo_id
scripts/photo_ingest.py:242:            photo_id = make_photo_id(
scripts/photo_ingest.py:248:                photo_id,
scripts/photo_ingest.py:257:                f"[REGISTER] {photo_id}"
scripts/photo_ingest.py:281:            "Register new photos and assign permanent photo_id"
scripts/import_qwen_to_db.py:166:        INSERT INTO photos (
scripts/qwen4b_output_v01.py:163:                photo_id,
scripts/qwen4b_output_v01.py:198:def mark_done(conn, photo_id, result, elapsed):
scripts/qwen4b_output_v01.py:294:                photo_id,
scripts/qwen4b_output_v01.py:301:def mark_error(conn, photo_id, error):
scripts/qwen4b_output_v01.py:317:                photo_id,
scripts/qwen4b_output_v01.py:551:            photo_id = row["photo_id"]
scripts/qwen4b_output_v01.py:557:                photo_id,
scripts/migrate_sqlite_to_postgres.py:155:                INSERT INTO photos (
app/workers/dino_worker.py:35:                photo_id,
app/workers/dino_worker.py:69:    photo_id,
app/workers/dino_worker.py:94:                photo_id,
app/workers/dino_worker.py:103:    photo_id,
app/workers/dino_worker.py:120:                photo_id,
app/workers/dino_worker.py:171:            photo_id = row["id"]
app/workers/dino_worker.py:172:            photo_key = row["photo_id"]
app/workers/dino_worker.py:201:                    photo_id,
app/workers/dino_worker.py:228:                        photo_id,
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
import psycopg2
import os
conn = psycopg2.connect(
conn = psycopg2.connect(OBASE_HOST", "localhost"),
    host=os.getenv("PHOTOBASE_HOST", "localhost"),
    port=int(os.getenv("PHOTOBASE_PORT", "5432")),
    user=os.getenv("PHOTOBASE_USER", "lora"),""),
    password=os.getenv("PHOTOBASE_PASSWORD", ""),,
    dbname=os.getenv("PHOTOBASE_DB", "photobase"),
)
with conn.cursor() as cur:
with conn.cursor() as cur:
    cur.execute("""mn_name, data_type, is_nullable
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'photos'
        ORDER BY ordinal_position
    """)
    for row in cur.fetchall():
    for row in cur.fetchall():
        print(row)
conn.close()
conn.close()
PY
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ModuleNotFoundError: No module named 'psycopg2'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:58:16

Да. Здесь ошибка только в окружении: `python3` запускает системный Python, где `psycopg2` не установлен. В проекте зависимости уже есть в `.venv`, поэтому используем `uv run`.

Но **сейчас ничего в схему менять не надо**. `photo_ingest.py` уже делает именно то, что нам нужно:

`input → присвоение PH_ID → запись в PostgreSQL`

А дальше уже две независимые ветви:

```text
                         INPUT
                           │
                           ▼
                    ┌─────────────┐
                    │ PHOTO INGEST│
                    │ PH_000xxxxx │
                    └──────┬──────┘
                           │
                 ┌─────────┴─────────┐
                 │                   │
                 ▼                   ▼
              DINO               QWEN 4B
                 │                   │
                 ▼                   ▼
             результат           описание
                 │                   │
                 ▼                   │
             сортировка              │
                 │                   │
                 ▼                   │
              preview                │
                 │                   │
                 └─────────┬─────────┘
                           ▼
                         PostgreSQL
                           │
                           ▼
                         GRID
```

И важный момент: **ID является главным ключом**, а не путь к файлу.

Сейчас сначала проверим, что `photo_ingest.py` действительно нормально работает с текущей БД.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/photo_ingest.py \
  --input /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily
```

Если он покажет примерно:

```text
FILES : 526

[SKIP]     ...
...
Registered : 0
Skipped    : 526
```

— это нормально: эти 526 уже получили `PH_00000001 ... PH_00000526`.

Если появятся новые фотографии:

```text
[REGISTER] PH_00000527  ...
[REGISTER] PH_00000528  ...
```

— значит первый этап работает как надо.

### А вот следующая важная проверка

Нужно посмотреть, **какие записи сейчас имеют ID, source_path и статусы**, не подключаясь через системный `python3`.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="photobase",
    user="lora",
)

with conn.cursor() as cur:
    cur.execute("""
        SELECT
            photo_id,
            filename,
            source_path,
            dino_status,
            qwen_status,
            sort_status,
            preview_status
        FROM photos
        ORDER BY id
        LIMIT 10
    """)

    for row in cur.fetchall():
        print(row)

conn.close()
PY
```

После этого мы уже можем **не трогать ingest**, а привести DINO и Qwen к одной логике:

- `photo_id` — идентификатор фотографии;
- `source_path` — **одинаковый исходный файл из `input`** для DINO и Qwen;
- DINO пишет свой результат в эту же запись;
- Qwen пишет своё описание в эту же запись;
- DINO после распознавания меняет `path` на отсортированный файл;
- `preview_path` появляется **только после сортировки**;
- GRID вообще не занимается распознаванием и не ищет фотографии по input;
- GRID читает PostgreSQL → получает `photo_id`, `path`, `preview_path`, описание и прочие поля → показывает preview;
- скачивание по `photo_id`/записи берёт **оригинал**, причём имя при скачивании формируем как `АДРЕС_оригинальное_имя.JPG`.

Это уже получается правильная архитектура: **БД — центральный реестр фотографий, `photo_id` — постоянная связь между всеми ветками.**

---

### 👤 **User** — 2026-08-18 22:58:56

PYnn.close()t(row).fetchall():
('PH_00000001', 'Screenshot from 2026-08-16 00-38-11.png', '/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Screenshot from 2026-08-16 00-38-11.png', 'done', 'done', 'pending', 'pending')
('PH_00000002', 'Ашхабадский_01.JPG', '/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_01.JPG', 'done', 'pending', 'pending', 'pending')
('PH_00000003', 'Ашхабадский_02.JPG', '/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_02.JPG', 'done', 'pending', 'pending', 'pending')
('PH_00000004', 'Ашхабадский_03.JPG', '/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_03.JPG', 'done', 'pending', 'pending', 'pending')
('PH_00000005', 'Ашхабадский_04.JPG', '/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_04.JPG', 'done', 'pending', 'pending', 'pending')
('PH_00000006', 'Ашхабадский_05.JPG', '/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_05.JPG', 'done', 'pending', 'pending', 'pending')
('PH_00000007', 'Ашхабадский_06.JPG', '/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_06.JPG', 'done', 'pending', 'pending', 'pending')
('PH_00000008', 'Ашхабадский_07.JPG', '/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_07.JPG', 'done', 'pending', 'pending', 'pending')
('PH_00000009', 'Ашхабадский_08.JPG', '/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_08.JPG', 'done', 'pending', 'pending', 'pending')
('PH_00000010', 'Ашхабадский_09.JPG', '/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Ашхабадский_09.JPG', 'processing', 'pending', 'pending', 'pending')
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:58:57

Да, теперь картина правильная.

Сейчас у нас уже есть именно нужная **центральная модель данных**:

```text
PH_00000001
 ├── source_path  → input/daily/...
 ├── DINO         → done
 ├── Qwen         → done
 ├── sort         → pending
 └── preview      → pending
```

То есть **ID действительно создан первым**, и обе нейросетевые ветки работают с одной и той же фотографией.

### Что вижу по выводу

`PH_00000001`:

```text
DINO     done
Qwen     done
sort     pending
preview  pending
```

Это идеально соответствует новой схеме.

`PH_00000002–09`:

```text
DINO     done
Qwen     pending
sort     pending
preview  pending
```

Тоже нормально — Qwen ещё не обработал их.

`PH_00000010`:

```text
DINO     processing
Qwen     pending
```

Значит DINO сейчас ещё работает с этой фотографией.

---

### Теперь важный следующий этап

Я бы **не трогал DINO и Qwen**, пока они уже работают по `photo_id`.

Нам надо сделать третью ветку:

```text
DINO done
   ↓
sort_status = pending
   ↓
присвоен address / выбран fingerprint
   ↓
копирование/перемещение в:
data/output/daily/<address>_v33/
   ↓
path = новый путь
   ↓
sort_status = done
   ↓
создание preview
   ↓
preview_path = ...
preview_status = done
```

И только после этого GRID получает:

```text
photo_id
address
path
preview_path
client
brand
description
...
```

Причём **`source_path` не меняем никогда**.

Это особенно важно:

```text
source_path = оригинал в input
path        = рабочий отсортированный оригинал
preview_path = маленькая копия для GRID
```

Таким образом, если завтра `input/daily` будет полностью заменён новым набором фотографий, старые записи в БД не потеряются, а новые получат новые `PH_...`.

### Ещё один момент

У тебя сейчас `PH_00000010` имеет `dino_status='processing'`. Если worker был остановлен аварийно, такая запись может зависнуть навсегда.

Позже добавим механизм восстановления:

```text
processing слишком долго
        ↓
автоматически → pending
```

Но **сейчас это не надо делать**, пока мы не закончим основную цепочку.

---

Следующим шагом предлагаю посмотреть **текущий код сортировки DINO**, который должен переводить:

```text
dino_fingerprint
        ↓
address
        ↓
path
        ↓
sort_status
```

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
'sort_status|source_path|dino_fingerprint|hybrid_final_id|output/daily|_v33' \
scripts app \
--include="*.py" | head -250
```

И по этому уже соберём **SORT → PREVIEW** без ломки работающего DINO/Qwen.

---

