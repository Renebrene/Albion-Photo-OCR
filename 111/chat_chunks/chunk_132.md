## СЕССИЯ: вторник

**Создано:** 2026-08-18 18:12:03
**Обновлено:** 2026-08-22 20:16:20
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1)

---

### 🤖 **Assistant** — 2026-08-18 21:49:09

Да. Сейчас база в нормальном состоянии для запуска:

- `PH_00000001` → `done`
- `PH_00000002` → `pending`
- `PH_00000003` → `pending`
- зависший `processing` мы сбросили.
- Первый DINO уже реально отработал: `0.4969`, margin `0.0733`, время `0.263 сек`.

**Следующий шаг — не менять recognizer.** Он уже проверен отдельно. Теперь проверяем именно **DINO worker**, который берет `pending` из PostgreSQL и пишет результат обратно.

Запусти worker в первом терминале:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/dino_worker.py
```

И **не останавливай его сразу**. Пусть обработает хотя бы 5–10 фотографий.

Потом во втором терминале:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT photo_id, dino_status, dino_fingerprint, ROUND(dino_score::numeric,4) AS score, ROUND(dino_second_score::numeric,4) AS second, ROUND(dino_margin::numeric,4) AS margin, ROUND(dino_time_sec::numeric,3) AS sec, error_message FROM photos ORDER BY id LIMIT 10;"
```

И отдельно сводку:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT dino_status, COUNT(*) FROM photos GROUP BY dino_status ORDER BY dino_status;"
```

### Что сейчас проверяем

Нам нужно увидеть примерно такую цепочку:

```text
pending
   ↓
processing
   ↓
done
```

и при `done` должны заполняться:

```text
dino_fingerprint
dino_score
dino_second_score
dino_margin
dino_time_sec
```

Причём `dino_fingerprint` должен стать чем-то вроде:

```text
94_v33
```

а не остаться пустым.

**Qwen пока не запускаем.** Сначала доводим DINO worker до стабильной схемы. После этого подключим Qwen параллельной независимой очередью:

```text
                    ┌── DINO worker ──→ dino_*
photos ──→ PostgreSQL
                    └── Qwen worker ──→ qwen_*
```

Именно такая архитектура здесь правильная: **одна запись фотографии → несколько независимых обработчиков → каждый пишет только свои поля/статус**.

---

### 👤 **User** — 2026-08-18 21:49:59

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/dino_worker.py
/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/python3: can't open file '/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/dino_worker.py': [Errno 2] No such file or directory
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:50:01

> **Used container tool**
>
> 
>
> Worked for a couple of seconds

Да, моя ошибка — я предположил имя `scripts/dino_worker.py`, не проверив, где именно мы его создали.

Сейчас **ничего не создаём и не меняем**. Сначала найдём фактический worker.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== WORKER FILES ====="
find app scripts -type f -name "*.py" -print | sort | grep -Ei 'worker|queue|dino|photo|postgres|db'

echo
echo "===== DINO STATUS REFERENCES ====="
grep -RniE "dino_status|FOR UPDATE|SKIP LOCKED|processing|pending" \
  app scripts --include="*.py" | head -200
```

Пришли вывод.

По нему я дам **точную команду запуска существующего worker**, а если окажется, что worker ещё не создан — тогда уже аккуратно создадим его.

---

### 👤 **User** — 2026-08-18 21:50:16

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/dino_worker.py
/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/python3: can't open file '/home/alexice/projects/scene_fingerprint_mvp_v02/scripts/dino_worker.py': [Errno 2] No such file or directory
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== WORKER FILES ====="
find app scripts -type f -name "*.py" -print | sort | grep -Ei 'worker|queue|dino|photo|postgres|db'

echo
echo "===== DINO STATUS REFERENCES ====="
grep -RniE "dino_status|FOR UPDATE|SKIP LOCKED|processing|pending" \
  app scripts --include="*.py" | head -200
===== WORKER FILES =====
app/pipeline/queue.py
app/pipeline/worker.py
app/web/client_db.py
app/web/components/photos_before_cache_20260816_145128.py
app/web/components/photos.py
app/web/components/technical_modules/photo_processing.py
app/web/photo_db.py
app/web/users_db.py
app/web_v01_backup_20260816_142053/components/photos.py
app/workers/dino_worker.py
scripts/import_qwen_to_db.py
scripts/migrate_sqlite_to_postgres.py
scripts/photo_ingest.py

===== DINO STATUS REFERENCES =====
app/web/components/technical_modules/photo_processing.py:12:def build_photo_processing():
app/web/components/technical.py:3:from app.web.components.technical_modules.photo_processing import (
app/web/components/technical.py:4:    build_photo_processing,
app/web/components/technical.py:104:def show_technical(initial_tab="photo_processing"):
app/web/components/technical.py:157:                    "photo_processing",
app/web/components/technical.py:216:                    value="photo_processing",
app/web/components/technical.py:221:                    with ui.tab_panel("photo_processing"):
app/web/components/technical.py:222:                        build_photo_processing()
app/core/recognizer.py:495:        Intended for queue/worker processing.
app/core/fingerprint.py:271:        # One image load per worker + parallel processing.
app/pipeline/worker.py:79:        print("[Worker] Starting batch processing")
app/pipeline/queue.py:13:        PENDING
app/pipeline/queue.py:14:        PROCESSING
app/pipeline/queue.py:56:                        DEFAULT 'PENDING',
app/pipeline/queue.py:100:                VALUES (?, ?, 'PENDING', ?, 0, ?)
app/pipeline/queue.py:148:        Atomically take the next PENDING job.
app/pipeline/queue.py:162:                WHERE status = 'PENDING'
app/pipeline/queue.py:183:                    status = 'PROCESSING',
app/pipeline/queue.py:189:                    AND status = 'PENDING'
app/pipeline/queue.py:212:        Mark a processing job as DONE.
app/pipeline/queue.py:227:                    AND status = 'PROCESSING'
app/pipeline/queue.py:242:        Mark a processing job as FAILED.
app/pipeline/queue.py:257:                    AND status = 'PROCESSING'
app/workers/dino_worker.py:38:            WHERE dino_status = 'pending'
app/workers/dino_worker.py:40:            FOR UPDATE SKIP LOCKED
app/workers/dino_worker.py:55:                dino_status = 'processing',
app/workers/dino_worker.py:78:                dino_status = 'done',
app/workers/dino_worker.py:113:                dino_status = 'error',
app/cli.py:375:            "[Queue] status=PENDING"
app/cli.py:504:                    "PENDING",
app/cli.py:505:                    "PROCESSING",
app/ocr/grid_ocr.py:4:import multiprocessing as mp
app/ocr/grid_ocr.py:344:    # multiprocessing
scripts/photo_ingest.py:150:                dino_status,
scripts/photo_ingest.py:164:                'pending',
scripts/photo_ingest.py:166:                'pending',
scripts/photo_ingest.py:167:                'pending',
scripts/photo_ingest.py:168:                'pending',
scripts/photo_ingest.py:169:                'pending'
scripts/llm_resolver_v01.py:135:You are a post-processing judge for an image recognition system.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:50:19

Вот он: **`app/workers/dino_worker.py`**. Значит, запускаем именно его.

Сначала покажи его целиком, чтобы проверить текущую логику перед запуском — особенно потому, что у нас уже есть `PH_00000001 = done`, а остальные `pending`.

```bash id="x8k2mw"
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,220p' app/workers/dino_worker.py
```

И сразу отдельно посмотрим, как он подключается к БД и как выбирает fingerprint:

```bash id="p7v4qn"
cd ~/projects/scene_fingerprint_mvp_v02

grep -nE "FingerprintManager|SceneEmbedder|SceneRecognizer|psycopg|connect|recognize_one|dino_fingerprint|dino_score" \
  app/workers/dino_worker.py
```

**Пока worker не запускаем.** После этого я проверю, что он действительно делает именно то, что нам нужно:

`PostgreSQL → pending → DINO → лучший fingerprint + score/margin → done`

и не затрагивает Qwen, сортировку и preview.

---

### 👤 **User** — 2026-08-18 21:50:54

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,220p' app/workers/dino_worker.py
from __future__ import annotations

import os
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def claim_photo(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                id,
                photo_id,
                source_path
            FROM photos
            WHERE dino_status = 'pending'
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
                dino_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (row["id"],),
        )

        conn.commit()

        return row

def mark_done(
    conn,
    photo_id,
    result,
    elapsed,
):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'done',
                dino_fingerprint = %s,
                dino_score = %s,
                dino_second_score = %s,
                dino_margin = %s,
                dino_time_sec = %s,
                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                result.get("best_id"),
                result.get("score"),
                result.get("second_score"),
                result.get("margin"),
                elapsed,
                photo_id,
            ),
        )

    conn.commit()

def mark_error(
    conn,
    photo_id,
    error,
):
    message = str(error)

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'error',
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

def main():
    settings = Settings()

    print("=" * 70)
    print("DINO WORKER")
    print("=" * 70)
    print("device:", settings.device)
    print("database:", DB_CONFIG["dbname"])
    print("=" * 70)

    embedder = SceneEmbedder(settings)

    manager = FingerprintManager(
        settings,
        embedder,
    )

    recognizer = SceneRecognizer(
        settings,
        embedder,
        manager,
    )

    conn = get_connection()

    print("[DINO] Worker ready.")

    max_items = int(os.getenv("DINO_MAX_ITEMS", "0"))
    processed = 0

    try:
        while True:
            row = claim_photo(conn)

            if row is None:
                print("[DINO] Queue empty.")
                break

            if max_items > 0 and processed >= max_items:
                print(
                    f"[DINO] Reached max_items={max_items}."
                )
                break

            photo_id = row["id"]
            photo_key = row["photo_id"]
            source_path = Path(row["source_path"])

            print()
            print("-" * 70)
            print(
                f"[DINO] "
                f"{photo_key} "
                f"{source_path.name}"
            )

            started = time.perf_counter()

            try:
                if not source_path.exists():
                    raise FileNotFoundError(
                        f"Photo not found: {source_path}"
                    )

                result = recognizer.recognize_one(
                    source_path,
                    top_k=5,
                    threshold=0.65,
                )

                elapsed = time.perf_counter() - started

                mark_done(
                    conn,
                    photo_id,
                    result,
                    elapsed,
                )

                print(
                    f"[DINO] DONE "
                    f"{photo_key} "
                    f"-> {result.get('best_id')} "
                    f"score={result.get('score', 0):.6f} "
                    f"margin={result.get('margin', 0):.6f} "
                    f"time={elapsed:.2f}s"
                )

                processed += 1

            except Exception as exc:
                elapsed = time.perf_counter() - started

                print(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -nE "FingerprintManager|SceneEmbedder|SceneRecognizer|psycopg|connect|recognize_one|dino_fingerprint|dino_score" \
  app/workers/dino_worker.py
7:import psycopg2
8:from psycopg2.extras import RealDictCursor
11:from app.core.embedder import SceneEmbedder
12:from app.core.fingerprint import FingerprintManager
13:from app.core.recognizer import SceneRecognizer
25:def get_connection():
26:    return psycopg2.connect(**DB_CONFIG)
79:                dino_fingerprint = %s,
80:                dino_score = %s,
137:    embedder = SceneEmbedder(settings)
139:    manager = FingerprintManager(
144:    recognizer = SceneRecognizer(
150:    conn = get_connection()
191:                result = recognizer.recognize_one(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:50:58

Да. Теперь картина ясна. **Worker правильный и уже подключен именно к нашей схеме PostgreSQL.** Главное — есть один небольшой баг, который лучше исправить до массового запуска.

### Что сейчас делает `dino_worker`

Цепочка такая:

`photos.dino_status = pending`  
→ `FOR UPDATE SKIP LOCKED` забирает одну фотографию  
→ `processing`  
→ `recognizer.recognize_one()`  
→ DINOv2 + v3.3 recognizer  
→ записывает:

- `dino_fingerprint`
- `dino_score`
- `dino_second_score`
- `dino_margin`
- `dino_time_sec`
- `dino_status = done`

То есть **ровно тот результат, который мы получили вручную для «Шолохова 127 А»**.

### Единственное, что исправляем

Вот этот участок:

```python
row = claim_photo(conn)

if row is None:
    ...

if max_items > 0 and processed >= max_items:
    ...
```

При `DINO_MAX_ITEMS=1` worker после первой фотографии успеет **захватить вторую**, перевести её в `processing`, а потом выйти. Это нам не нужно.

Сейчас массовый запуск можно делать без `DINO_MAX_ITEMS`, потому что по умолчанию он `0`, но я бы сразу исправил.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python3 - <<'PY'
from pathlib import Path

p = Path("app/workers/dino_worker.py")
s = p.read_text()

old = '''        while True:
            row = claim_photo(conn)

            if row is None:
                print("[DINO] Queue empty.")
                break

            if max_items > 0 and processed >= max_items:
                print(
                    f"[DINO] Reached max_items={max_items}."
                )
                break
'''

new = '''        while True:
            if max_items > 0 and processed >= max_items:
                print(
                    f"[DINO] Reached max_items={max_items}."
                )
                break

            row = claim_photo(conn)

            if row is None:
                print("[DINO] Queue empty.")
                break
'''

if old not in s:
    raise SystemExit("TARGET BLOCK NOT FOUND")

p.write_text(s.replace(old, new))
print("PATCH: OK")
PY

python3 -m py_compile app/workers/dino_worker.py
```

Если получим:

```text
PATCH: OK
```

и без ошибок после `py_compile` — **запускаем один DINO worker на всю очередь**.

Но перед этим я предлагаю сделать контрольный запрос:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "
SELECT
    dino_status,
    COUNT(*) AS count
FROM photos
GROUP BY dino_status
ORDER BY dino_status;
"
```

Сейчас ожидаем примерно:

```text
 done       | 1
 pending    | 525
```

После этого уже запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python app/workers/dino_worker.py
```

**И важный момент:** Qwen пока не запускаем. Сначала дадим DINO пройти очередь и убедимся, что PostgreSQL стабильно получает результаты. Затем поставим **Qwen worker параллельно с DINO**, и они будут независимо обрабатывать одни и те же 526 фото через свои `*_status`. Это как раз та архитектура, которую мы хотели получить.

---

### 👤 **User** — 2026-08-18 21:53:15

gpu 6% 1.6 VRAM, а cpu вообще отдыхает

---

### 🤖 **Assistant** — 2026-08-18 21:53:16

Да — и это **ожидаемо для текущего worker'а**, но для массовой обработки это значит, что мы сейчас используем RTX 3060 далеко не на полную.

Причина видна из архитектуры:

- `recognize_one()` обрабатывает **одно фото за вызов**;
- DINO получает одно изображение;
- между изображениями GPU простаивает;
- `recognize_one()` ещё делает CPU-дескрипторы;
- при этом у worker'а нет GPU batch;
- поэтому получается примерно **GPU 6%, 1.6 GB VRAM**, а CPU тоже почти ничего не делает большую часть времени.

### Я бы сейчас НЕ трогал recognizer

У нас есть гораздо более правильный вариант для 526 фото:

```text
                 PostgreSQL
                     │
              ┌──────┴──────┐
              │             │
          DINO queue     QWEN queue
              │             │
         DINO worker    Qwen worker
              │             │
           GPU batch     GPU/CPU
              │             │
              └──────┬──────┘
                     ↓
                  photos
```

Для DINO сделать **batch-обработку**, например:

```text
1 фото  → GPU почти простаивает
8 фото  → GPU начинает работать
16 фото → нормально
32 фото → возможно оптимум
```

У тебя уже в `Settings` есть:

```python
batch_size = 16
```

но текущий `recognize_one()` этот механизм фактически не использует.

### Причём есть ещё важный момент

Сейчас каждый снимок проходит:

```text
загрузить фото
    ↓
DINO
    ↓
CPU descriptors
    ↓
сравнить со всеми fingerprint
    ↓
PostgreSQL
    ↓
следующее фото
```

То есть GPU постоянно получает маленькие порции работы.

Для массовой очереди лучше:

```text
берём 16 pending
        ↓
загружаем 16 изображений
        ↓
          DINO
        ↓
16 embeddings
        ↓
CPU сравнение
        ↓
16 UPDATE
        ↓
следующие 16
```

Тогда **RTX 3060 будет работать гораздо плотнее**, а CPU получит нормальную параллельную работу на сравнении/дескрипторах.

---

### Но сейчас предлагаю простой тест

Не будем пока переписывать worker.

Открой второй терминал и запусти:

```bash
watch -n 1 nvidia-smi
```

В первом worker пусть продолжает работать.

Если увидишь примерно:

```text
GPU-Util  5-15%
Memory    1600 MiB
```

и при этом одна фотография обрабатывается, например:

```text
time=0.25s
time=0.30s
time=0.27s
```

— всё подтверждается.

**После этого я бы переделал именно DINO worker на batch=16**, не ломая текущий `recognize_one()` и не меняя алгоритм v3.3.

Это даст нам производительность без изменения качества распознавания.

---

### 👤 **User** — 2026-08-18 21:54:32

так и есть

---

### 🤖 **Assistant** — 2026-08-18 21:54:32

Да, тогда всё сходится. **Сам DINO у нас работает нормально, просто worker подаёт ему работу слишком мелкими порциями.**

И это как раз хороший момент: **алгоритм распознавания не трогаем вообще**. Меняем только способ подачи фотографий на GPU.

Сейчас:

```text
фото 1 → DINO → результат
фото 2 → DINO → результат
фото 3 → DINO → результат
...
```

Нужно:

```text
16 фото
   ↓
DINO batch
   ↓
16 embedding'ов
   ↓
существующий recognizer / сравнение
   ↓
16 результатов PostgreSQL
```

При этом Qwen потом сделаем **отдельным worker'ом**, и оба процесса смогут идти параллельно.

### Но есть нюанс

Я бы **не пытался просто засунуть `recognize_one()` в ThreadPoolExecutor**. Это даст несколько одновременных обращений к DINO и может наоборот ухудшить ситуацию на 12 GB VRAM.

Правильнее использовать уже существующий:

```python
settings.batch_size = 16
```

и добавить в worker пакетную обработку.

То есть архитектуру оставляем:

```text
                    ┌── DINO batch worker ──→ dino_*
                    │
photos PostgreSQL ──┤
                    │
                    └── Qwen worker ───────→ qwen_*
```

А существующий `SceneRecognizer` и **v3.3 scoring остаются без изменений**.

### Следующий шаг

Я предлагаю сначала сделать **отдельный batch-путь только для DINO embedding**, не ломая проверенный `recognize_one()`:

1. worker забирает 16 `pending`;
2. одним вызовом `embed_paths()` получает `(16, 768)`;
3. для каждой фотографии используются уже готовые embedding;
4. существующий `SceneAnalyzer.compare()` считает итоговый score;
5. 16 результатов одной транзакцией записываются в PostgreSQL;
6. `dino_status` → `done`.

Так мы одновременно получим:

- **качество текущего v3.3**;
- значительно более высокую загрузку GPU;
- сохранение всей диагностической информации `score / second / margin`;
- нормальную основу для параллельного Qwen;
- возможность потом увеличить batch с `16` до `24/32`, если RTX 3060 позволит.

**Сейчас worker можно остановить `Ctrl+C` — данные уже сохраняются корректно.** Затем переделаем именно его на batch, а не весь recognizer.

---

### 👤 **User** — 2026-08-18 21:54:57

проверим вермя выполнения сейчас и батчем

---

### 🤖 **Assistant** — 2026-08-18 21:54:57

Да. И лучше сделать **честный A/B-тест на одной и той же выборке**, не трогая базовый алгоритм.

### Тест №1 — текущий worker

Возьмём, например, **32 фотографии**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

DINO_MAX_ITEMS=32 \
/usr/bin/time -f '\nREAL_TIME=%e sec' \
uv run python app/workers/dino_worker.py
```

Перед этим верни первые 32 записи в `pending`, если worker уже что-то обработал:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "
UPDATE photos
SET dino_status='pending',
    dino_fingerprint=NULL,
    dino_score=NULL,
    dino_second_score=NULL,
    dino_margin=NULL,
    dino_time_sec=NULL,
    error_message=NULL,
    updated_at=CURRENT_TIMESTAMP
WHERE id IN (
    SELECT id FROM photos
    ORDER BY id
    LIMIT 32
);
"
```

Потом:

```bash
DINO_MAX_ITEMS=32 \
/usr/bin/time -f '\nREAL_TIME=%e sec' \
uv run python app/workers/dino_worker.py
```

В конце получим примерно:

```text
REAL_TIME=12.34 sec
```

и можно посчитать:

**32 / 12.34 = 2.59 фото/сек**

---

### Но есть важный момент

Текущий worker уже грузит DINO на CUDA, поэтому `dino_time_sec` и общий `REAL_TIME` — разные вещи.

Нам нужны оба показателя:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "
SELECT
    COUNT(*) AS n,
    ROUND(AVG(dino_time_sec)::numeric, 3) AS avg_sec,
    ROUND(MIN(dino_time_sec)::numeric, 3) AS min_sec,
    ROUND(MAX(dino_time_sec)::numeric, 3) AS max_sec
FROM photos
WHERE dino_status='done'
  AND id <= 32;
"
```

---

### Затем делаем batch=16

**Не меняем recognizer.** Меняем только способ получения DINO embeddings.

Тогда для тех же 32 фотографий сравним:

| Режим | Фото | Batch | Время |
|---|---:|---:|---:|
| Сейчас | 32 | 1 | измеряем |
| Batch | 32 | 16 | измеряем |

И самое интересное — посмотрим `nvidia-smi` в обоих случаях.

Если сейчас у нас:

```text
GPU Util ≈ 5–10%
VRAM ≈ 1.6 GB
```

а batch даст, например:

```text
GPU Util ≈ 50–90%
VRAM ≈ 3–5 GB
```

и общее время заметно уменьшится — тогда **batch однозначно оставляем**.

Я бы именно **32 фото** взял для первого сравнения: достаточно, чтобы разница проявилась, но не жалко времени на эксперимент.

---

### 👤 **User** — 2026-08-18 21:56:34

uv run python app/workers/dino_worker.py
======================================================================
DINO WORKER
======================================================================
device: cuda
database: photobase
======================================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8460.16it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[DINO] Worker ready.
[DINO] Queue empty.

[DINO] Worker stopped.

REAL_TIME=5.79 sec
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
 надо очистить результаты и потренироваться на 526 - замерить время дино гпу, дино гпу батчи дино цпу онли

---

### 🤖 **Assistant** — 2026-08-18 21:56:37

Да. Сделаем **нормальный A/B/C benchmark на всех 526 фотографиях**:

1. **DINO GPU, batch=1** — текущая реализация.
2. **DINO GPU, batch=16** — новая реализация.
3. **DINO CPU only** — batch=1/текущий CPU-путь.

И главное: **перед каждым тестом полностью очищаем результаты DINO**, чтобы все три режима обрабатывали абсолютно одинаковые 526 фото.

Но есть важный момент: текущий `dino_worker.py` **не имеет batch-режима**. Поэтому сначала замерим GPU и CPU на текущем worker, а затем сделаем batch-worker и повторим.

### 1. Сначала очистить результаты DINO

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "
UPDATE photos
SET
    dino_status = 'pending',
    dino_fingerprint = NULL,
    dino_score = NULL,
    dino_second_score = NULL,
    dino_margin = NULL,
    dino_time_sec = NULL,
    error_message = NULL,
    updated_at = CURRENT_TIMESTAMP;
"

psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE dino_status='pending') AS pending
FROM photos;
"
```

Должно быть:

```text
 total | pending
-------+---------
 526   | 526
```

---

## 2. Тест №1 — DINO GPU, текущий режим

В одном терминале:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

watch -n 1 nvidia-smi
```

Во втором:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

/usr/bin/time -f '\nREAL_TIME=%e sec' \
uv run python app/workers/dino_worker.py
```

**Не прерываем**, ждём все 526.

В конце пришли мне:

```text
REAL_TIME=...
```

и последние строки вида:

```text
[DINO] DONE ...
```

После завершения сразу:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE dino_status='done') AS done,
    COUNT(*) FILTER (WHERE dino_status='error') AS errors,
    ROUND(AVG(dino_time_sec)::numeric,3) AS avg_sec,
    ROUND(MIN(dino_time_sec)::numeric,3) AS min_sec,
    ROUND(MAX(dino_time_sec)::numeric,3) AS max_sec
FROM photos;
"
```

---

## 3. Потом CPU-only

Снова **очищаем 526**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "
UPDATE photos
SET
    dino_status = 'pending',
    dino_fingerprint = NULL,
    dino_score = NULL,
    dino_second_score = NULL,
    dino_margin = NULL,
    dino_time_sec = NULL,
    error_message = NULL,
    updated_at = CURRENT_TIMESTAMP;
"
```

И запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

SCENE_DEVICE=cpu \
/usr/bin/time -f '\nREAL_TIME=%e sec' \
uv run python app/workers/dino_worker.py
```

Это **может быть существенно дольше**, поэтому здесь уже имеет смысл следить за прогрессом.

---

## 4. После этого делаем GPU batch=16

Вот здесь будет самое интересное.

Сделаем отдельный:

```text
dino_worker_batch.py
```

который будет брать:

```text
16 pending
    ↓
DINO batch
    ↓
16 × 768 embeddings
    ↓
существующий v3.3 scoring
    ↓
PostgreSQL
```

**Алгоритм распознавания не меняем.** Меняем только подачу изображений в DINO.

И затем снова:

```text
526 фото
GPU batch=16
```

---

### В итоге получим реальную таблицу

| Режим | 526 фото | GPU | Среднее |
|---|---:|---:|---:|
| DINO GPU batch=1 | ? сек | ? % | ? сек/фото |
| DINO GPU batch=16 | ? сек | ? % | ? сек/фото |
| DINO CPU | ? сек | 0% | ? сек/фото |

И уже **по фактическим цифрам**, а не по предположениям, решим, какой worker оставлять.

**Сейчас запускай пункт №1.** 526 фото — это правильный тест, потому что на 5–10 фотографиях накладные расходы загрузки модели сильно искажают картину.

---

### 👤 **User** — 2026-08-18 22:00:31

[DINO] PH_00000526 Шолохова 127 А (9).JPG
[DINO] DONE PH_00000526 -> 94_v33 score=0.884367 margin=0.031779 time=0.36s
[DINO] Queue empty.

[DINO] Worker stopped.

REAL_TIME=189.76 sec
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:00:33

Да. Первый замер уже есть:

- **526 фото**
- GPU DINO, текущий режим: **189.76 сек**
- среднее: **0.361 сек/фото**
- теоретически ~**10.7 мин / 1000 фото**
- при этом GPU загрузка всего ~6%, VRAM ~1.6 ГБ — значит, **GPU явно недогружена**.
- Сейчас главное узкое место, скорее всего, не сам DINO, а схема `1 фото → 1 inference → CPU/загрузка/сравнение`.

Следующий эксперимент я бы сделал строго так, чтобы цифры были сопоставимы:

### 1. Зафиксировать текущий результат

**GPU single: 189.76 сек / 526**

### 2. Потом GPU batch

Нужно посмотреть, как сейчас устроен `SceneEmbedder.embed_paths()` и есть ли там `batch_size`. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,320p' app/core/embedder.py
```

И одновременно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE "batch_size|batch|embed_paths|model\(" \
app/core/embedder.py app/core --include="*.py" | head -100
```

После этого сделаем **отдельный benchmark**, не трогая рабочий worker:

1. **DINO GPU single** — уже есть: 189.76 с.
2. **DINO GPU batch 8**
3. **DINO GPU batch 16**
4. **DINO GPU batch 32**
5. **DINO CPU single/batch** — для сравнения.

И очень важно: в benchmark будем измерять отдельно:

- загрузку/декодирование JPEG;
- собственно DINO inference;
- полный цикл.

Тогда станет видно, почему у тебя RTX 3060 практически отдыхает.

Пока **ничего в worker не меняем**. Сначала получаем чистые цифры.

---

### 👤 **User** — 2026-08-18 22:06:33

[DINO] PH_00000526 Шолохова 127 А (9).JPG
[DINO] DONE PH_00000526 -> 94_v33 score=0.884367 margin=0.031779 time=0.53s
[DINO] Queue empty.

[DINO] Worker stopped.

REAL_TIME=272.92 sec
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$   

ЦПУ 20%   ГПУ ВРАМ 1,1

---

### 🤖 **Assistant** — 2026-08-18 22:06:34

Вот это уже интересный результат.

### Второй замер

| Режим | 526 фото | Среднее |
|---|---:|---:|
| предыдущий GPU | **189.76 с** | **0.361 с/фото** |
| текущий GPU | **272.92 с** | **0.519 с/фото** |

При этом:

- **CPU ~20%**
- **VRAM ~1.1 ГБ**
- GPU практически не загружена.

То есть **мы пока вообще не получили нормальной загрузки RTX 3060**. Более того, второй прогон медленнее первого примерно на **44%**. Это очень похоже на то, что значительная часть времени уходит не на вычисление DINO, а на окружающий pipeline: открытие JPEG → подготовка изображения → CPU-дескрипторы → сравнение с fingerprint → обращения к диску и т. д.

И поэтому сейчас **нельзя считать 0.52 с временем DINO inference**.

### Делаем правильно

Нам нужно разделить тест на две части:

**A. Чистый DINO**

526 изображений → загрузили → сформировали batch → `model(pixel_values)` → следующий batch.

Без:

- PostgreSQL
- fingerprint comparison
- `SceneAnalyzer`
- `CompactDescriptor`
- `recognize_one`
- записи результатов.

Там мы увидим настоящую скорость RTX 3060.

**B. Полный текущий worker**

Оставляем как есть — уже имеем:

`189.76 с` и `272.92 с`.

После этого сравним:

```text
ЧИСТЫЙ DINO GPU batch 16       ?
ЧИСТЫЙ DINO GPU batch 32       ?
ЧИСТЫЙ DINO GPU batch 64       ?

ТЕКУЩИЙ PIPELINE               189–273 сек
```

И тогда станет понятно, **сколько реально можно выиграть батчированием**.

Сейчас я бы **не трогал worker и не менял архитектуру**. Сначала покажи мне `embedder.py`, как я просил выше:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,320p' app/core/embedder.py
```

По нему сразу определим, как именно у тебя сейчас выполняется DINO и где можно сделать чистый batch benchmark.

---

### 👤 **User** — 2026-08-18 22:07:41

int_mvp_v02 && \
sed -n '1,320p' app/core/embedder.py
from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel

class SceneEmbedder:
    """DINOv2 ViT-B/14 global embedding service.

    Uses Hugging Face Transformers instead of torch.hub.

    Output:
        global embedding: [N, 768]
    """

    def __init__(self, settings):
        self.settings = settings
        self.device = torch.device(settings.device)

        print(f"[SceneEmbedder] device={self.device}")

        if self.device.type == "cuda":
            print(
                f"[SceneEmbedder] GPU="
                f"{torch.cuda.get_device_name(0)}"
            )
            print(
                f"[SceneEmbedder] VRAM="
                f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
            )

        self.model_name = settings.model_name

        print(
            f"[SceneEmbedder] Loading DINOv2: "
            f"{self.model_name}"
        )

        self.processor = AutoImageProcessor.from_pretrained(
            self.model_name
        )

        self.model = AutoModel.from_pretrained(
            self.model_name
        )

        self.model = self.model.to(self.device)
        self.model.eval()

        self.dimension = 768

        print(
            f"[SceneEmbedder] embedding dimension="
            f"{self.dimension}"
        )
        print(
            "[SceneEmbedder] patch extraction=DISABLED "
            "(compact)"
        )
        print("[SceneEmbedder] Ready.")

    @torch.inference_mode()
    def embed_images(
        self,
        images: list[Image.Image],
        batch_size=None,
    ):
        batch_size = (
            batch_size
            or self.settings.batch_size
        )

        vectors = []

        for i in range(
            0,
            len(images),
            batch_size,
        ):
            batch_images = images[
                i:i + batch_size
            ]

            inputs = self.processor(
                images=batch_images,
                return_tensors="pt",
            )

            inputs = {
                key: value.to(
                    self.device,
                    non_blocking=True,
                )
                for key, value in inputs.items()
            }

            outputs = self.model(**inputs)

            # DINOv2 CLS token.
            features = outputs.last_hidden_state[:, 0, :]

            features = torch.nn.functional.normalize(
                features,
                dim=1,
            )

            vectors.append(
                features.float()
                .cpu()
                .numpy()
            )

        if not vectors:
            return np.empty(
                (0, self.dimension),
                dtype=np.float32,
            )

        return np.concatenate(
            vectors,
            axis=0,
        ).astype("float32")

    def embed_paths(self, paths):
        from .image import load_image

        images = [
            load_image(path)
            for path in paths
        ]

        return self.embed_images(images)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE "batch_size|batch|embed_paths|model\(" \
app/core/embedder.py app/core --include="*.py" | head -100
app/core/embedder.py:68:        batch_size=None,
app/core/embedder.py:70:        batch_size = (
app/core/embedder.py:71:            batch_size
app/core/embedder.py:72:            or self.settings.batch_size
app/core/embedder.py:80:            batch_size,
app/core/embedder.py:82:            batch_images = images[
app/core/embedder.py:83:                i:i + batch_size
app/core/embedder.py:87:                images=batch_images,
app/core/embedder.py:99:            outputs = self.model(**inputs)
app/core/embedder.py:126:    def embed_paths(self, paths):
app/core/scene_analyzer.py:393:                self.embedder.embed_paths(
app/core/recognizer.py:205:        queries = self.embedder.embed_paths(
app/core/recognizer.py:574:        queries = self.embedder.embed_paths(
app/core/config.py:20:    batch_size: int = int(
app/core/config.py:22:            "SCENE_BATCH",
app/core/embedder.py:68:        batch_size=None,
app/core/embedder.py:70:        batch_size = (
app/core/embedder.py:71:            batch_size
app/core/embedder.py:72:            or self.settings.batch_size
app/core/embedder.py:80:            batch_size,
app/core/embedder.py:82:            batch_images = images[
app/core/embedder.py:83:                i:i + batch_size
app/core/embedder.py:87:                images=batch_images,
app/core/embedder.py:99:            outputs = self.model(**inputs)
app/core/embedder.py:126:    def embed_paths(self, paths):
app/core/fingerprint.py:212:        embeddings = embedder.embed_paths(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:07:42

Да. Теперь картина понятна.

У тебя **batch уже есть**. По умолчанию:

```text
SCENE_BATCH = 16
```

и `embed_images()` реально делает:

```text
16 изображений
→ processor
→ GPU
→ model(**inputs)
→ следующий batch
```

Но текущий worker **не является чистым тестом DINO**. Он вызывает `recognize_one()` для каждого фото, а там кроме embedding выполняется весь поиск по fingerprint и CPU-анализ.

И ещё важный момент: `embed_paths()` сначала **загружает все 526 JPEG в RAM**, а потом запускает batch inference:

```text
526 × load_image()
        ↓
526 PIL images
        ↓
batch 16 → DINO
```

Поэтому предлагаю сейчас вообще не менять код.

## Следующий тест — чистый DINO

Сделаем отдельный benchmark, который:

1. берёт те же 526 фото;
2. один раз загружает их;
3. прогоняет **batch 1**;
4. затем **batch 8**;
5. **batch 16**;
6. **batch 32**;
7. измеряет именно `model()` + GPU synchronization;
8. отдельно покажет время preprocessing.

Но сначала проверим память, чтобы batch 32/64 не начал душить 12-ГБ карту.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import torch

print("GPU:", torch.cuda.get_device_name(0))
print("VRAM total:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2), "GB")
print("VRAM allocated:", round(torch.cuda.memory_allocated() / 1024**3, 3), "GB")
print("VRAM reserved :", round(torch.cuda.memory_reserved() / 1024**3, 3), "GB")
PY
```

А затем я дам **один чистый benchmark-командник**, который прогонит 526 фото на GPU с batch `1/8/16/32/64` и выдаст примерно:

```text
BATCH   LOAD     PROCESS     TOTAL     IMG/sec
1       ...
8       ...
16      ...
32      ...
64      ...
```

Вот это будет уже настоящий ответ на вопрос, **насколько RTX 3060 можно загрузить батчем**.

И после этого сделаем третий контрольный замер — **CPU-only DINO**, чтобы получить честное:

**CPU vs GPU single vs GPU batch.**

---

### 👤 **User** — 2026-08-18 22:08:39

CPU batch ?

---

### 🤖 **Assistant** — 2026-08-18 22:08:41

Да. **CPU batch тоже обязательно проверим** — иначе сравнение будет неполным.

Причём я бы сделал 4 режима:

| Режим | Batch |
|---|---:|
| CPU | 1 |
| CPU | 16 |
| GPU | 1 |
| GPU | 16 / 32 / 64 |

Но есть важный нюанс: **CPU batch ≠ обязательно быстрее CPU single**. Для DINO большая часть выигрыша на CPU может быть от уменьшения накладных расходов, но вычислений всё равно очень много.

И ещё лучше разделить:

```text
LOAD JPEG
   ↓
PROCESSOR / resize / normalize
   ↓
DINO inference
   ↓
embedding
```

Так мы увидим, где именно теряем время.

**Предлагаю сначала сделать один benchmark, который автоматически прогонит CPU batch 1/8/16/32 и GPU batch 1/8/16/32**, на тех же 526 фотографиях. Тогда получим одну нормальную таблицу сравнения.

Не будем пока менять рабочий `dino_worker.py`.

---

### 👤 **User** — 2026-08-18 22:09:21

2-4 процесса дино?

---

### 🤖 **Assistant** — 2026-08-18 22:09:22

Да, **можно**, но тут есть важное различие.

Если ты имеешь в виду **2–4 независимых DINO-процесса**, которые одновременно работают на одной RTX 3060, то я бы **не начинал с 4**.

Сейчас у нас:

- 1 процесс DINO → GPU почти не загружена;
- VRAM всего ~1.1–1.6 ГБ;
- CPU ~20%;
- 526 фото → 190–273 сек.

Это говорит о том, что **2 процесса вполне стоит проверить**. Они могут перекрыть ожидание CPU/PIL/processor одного процесса другим.

### Я бы протестировал так

```text
1 процесс × batch 16
2 процесса × batch 16
3 процесса × batch 16
4 процесса × batch 16
```

И отдельно:

```text
1 процесс × batch 1
2 процесса × batch 1
4 процесса × batch 1
```

Но есть риск: если каждый процесс одновременно вызывает DINO на GPU, они начнут конкурировать за CUDA-контекст и могут оказаться **медленнее одного хорошо настроенного batch**.

Поэтому наша цель — найти максимум:

```text
                 526 фото
                    │
        ┌───────────┼───────────┐
        ↓           ↓           ↓
      CPU         GPU          GPU
     batch       batch        processes
        │           │           │
        │        16/32/64    2/3/4
        └───────────┴───────────┘
                    ↓
              IMG/sec
```

### И ещё важнее

Для твоей задачи я подозреваю, что **лучший вариант окажется не 4 DINO-процесса**, а:

**1 DINO GPU-процесс + большой batch + параллельная CPU-подготовка изображений.**

То есть не:

`процесс → взять фото → DINO → сравнить → следующий`

а:

`CPU workers → готовят изображения → очередь → один GPU DINO batch → результаты`.

Это гораздо правильнее загружает RTX 3060.

Поэтому **2–4 процесса DINO — хороший эксперимент**, но не финальная архитектура. Сначала замерим.

---

### 👤 **User** — 2026-08-18 22:09:59

alexice@NEURO:~$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import torch

print("GPU:", torch.cuda.get_device_name(0))
print("VRAM total:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2), "GB")
print("VRAM allocated:", round(torch.cuda.memory_allocated() / 1024**3, 3), "GB")
print("VRAM reserved :", round(torch.cuda.memory_reserved() / 1024**3, 3), "GB") 
PY
GPU: NVIDIA GeForce RTX 3060
VRAM total: 11.63 GB
VRAM allocated: 0.0 GB
VRAM reserved : 0.0 GB
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:10:00

Отлично. Сейчас карта **полностью свободна**:

- RTX 3060 — **11.63 GB**
- allocated — **0 GB**
- reserved — **0 GB**

Значит, можно делать чистый эксперимент без влияния других CUDA-процессов.

Я бы сейчас **не трогал рабочий worker**. Следующий тест — CPU/GPU batch и затем 2–4 процесса.

Для начала давай проверим **CPU batch** на тех же 526 фото. Это даст нам базовую точку, с которой потом сравним GPU.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
SCENE_DEVICE=cpu uv run python - <<'PY'
import time
from pathlib import Path

from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.image import image_files
from app.core.config import settings

paths = image_files(Path("data/input/daily"))

print("=" * 70)
print("DINO CPU BATCH BENCHMARK")
print("=" * 70)
print("images:", len(paths))

settings = Settings()

embedder = SceneEmbedder(settings)

images = []
t0 = time.perf_counter()

from app.core.image import load_image

for p in paths:
    images.append(load_image(p))

load_time = time.perf_counter() - t0

print(f"LOAD_TIME={load_time:.2f} sec")

for batch in (1, 8, 16, 32):
    print()
    print("-" * 70)
    print(f"BATCH={batch}")

    t0 = time.perf_counter()

    result = embedder.embed_images(
        images,
        batch_size=batch,
    )

    elapsed = time.perf_counter() - t0

    print(f"RESULT_SHAPE={result.shape}")
    print(f"DINO_TIME={elapsed:.2f} sec")
    print(f"IMG_PER_SEC={len(images) / elapsed:.2f}")
    print(f"SEC_PER_IMAGE={elapsed / len(images):.4f}")

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY
```

### Что нас особенно интересует

Например, если получится:

```text
CPU batch 1   500 sec
CPU batch 8   300 sec
CPU batch 16  280 sec
CPU batch 32  275 sec
```

то дальше бессмысленно увеличивать CPU batch.

А если:

```text
CPU batch 1   500 sec
CPU batch 16  200 sec
CPU batch 32  150 sec
```

— тогда CPU тоже имеет смысл хорошо распараллелить.

**После этого сразу сделаем точно такой же GPU-тест.** Затем уже проверим 2 и 4 параллельных DINO-процесса.

---

### 👤 **User** — 2026-08-18 22:15:07

цпу максимум на 50% загружен, гпу и врам отдыхают 

BATCH=1
RESULT_SHAPE=(526, 768)
DINO_TIME=83.26 sec
IMG_PER_SEC=6.32
SEC_PER_IMAGE=0.1583

----------------------------------------------------------------------
BATCH=8
RESULT_SHAPE=(526, 768)
DINO_TIME=76.68 sec
IMG_PER_SEC=6.86
SEC_PER_IMAGE=0.1458

----------------------------------------------------------------------
BATCH=16
RESULT_SHAPE=(526, 768)
DINO_TIME=82.47 sec
IMG_PER_SEC=6.38
SEC_PER_IMAGE=0.1568

---

### 🤖 **Assistant** — 2026-08-18 22:15:07

Вот теперь очень показательный результат.

### CPU DINO

| Batch | Время | Фото/сек |
|---:|---:|---:|
| 1 | 83.26 с | 6.32 |
| 8 | **76.68 с** | **6.86** |
| 16 | 82.47 с | 6.38 |

То есть **batch практически ничего не даёт**. Значит узкое место сейчас не в размере batch.

И главное наблюдение:

> CPU загружен максимум примерно на 50%, GPU практически простаивает.

Это очень похоже на ситуацию, когда **один поток/несколько внутренних потоков PyTorch не способны нормально загрузить CPU**, а сама модель работает последовательно.

### Но здесь есть ещё один важный момент

Ты запускал:

```text
SCENE_DEVICE=cpu
```

поэтому GPU **и должна была отдыхать**. 😄

А CPU 50% при 12 потоках означает, что DINO сейчас использует примерно половину доступного процессорного ресурса.

---

## Теперь самое интересное — GPU

Нам надо сделать **абсолютно такой же тест**, но:

```text
SCENE_DEVICE=cuda
```

и batches:

```text
1
8
16
32
64
```

Причём я бы уже ожидал, что **batch 16/32 резко ускорит ситуацию** и наконец начнёт нормально загружать RTX 3060.

Запусти:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
SCENE_DEVICE=cuda uv run python - <<'PY'
import time
import torch
from pathlib import Path

from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.image import image_files, load_image

paths = image_files(Path("data/input/daily"))

print("=" * 70)
print("DINO GPU BATCH BENCHMARK")
print("=" * 70)
print("images:", len(paths))
print("GPU:", torch.cuda.get_device_name(0))

settings = Settings()
embedder = SceneEmbedder(settings)

t0 = time.perf_counter()

images = [load_image(p) for p in paths]

load_time = time.perf_counter() - t0

print(f"LOAD_TIME={load_time:.2f} sec")

for batch in (1, 8, 16, 32, 64):

    print()
    print("-" * 70)
    print(f"BATCH={batch}")

    torch.cuda.empty_cache()
    torch.cuda.synchronize()

    t0 = time.perf_counter()

    result = embedder.embed_images(
        images,
        batch_size=batch,
    )

    torch.cuda.synchronize()

    elapsed = time.perf_counter() - t0

    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3

    print(f"RESULT_SHAPE={result.shape}")
    print(f"DINO_TIME={elapsed:.2f} sec")
    print(f"IMG_PER_SEC={len(images) / elapsed:.2f}")
    print(f"SEC_PER_IMAGE={elapsed / len(images):.4f}")
    print(f"VRAM_ALLOCATED={allocated:.3f} GB")
    print(f"VRAM_RESERVED={reserved:.3f} GB")

print()
print("=" * 70)
print("DONE")
print("=" * 70)
PY
```

### И пока **не запускаем 2–4 процесса**.

Сначала узнаем, сколько выдаёт **один GPU-процесс**.

Потому что если окажется, например:

```text
CPU batch 8       76.7 sec

GPU batch 1       35 sec
GPU batch 8       12 sec
GPU batch 16       8 sec
GPU batch 32       6 sec
```

тогда 2–4 процесса вообще могут быть не нужны.

А если GPU покажет:

```text
GPU batch 16      40 sec
GPU utilization  10%
```

— **тогда уже имеет смысл экспериментировать с 2–4 процессами**.

Сейчас мы как раз подходим к правильной архитектуре: сначала найдём **реальную производительность чистого DINO**, а потом вернём сверху PostgreSQL + recognition.

---

### 👤 **User** — 2026-08-18 22:15:56

мне не столько нужно ускорить процесс, сколько распраллелить - дино на цпу, а квен на ГПУ

---

### 🤖 **Assistant** — 2026-08-18 22:15:57

А, тогда да — **это совсем другая задача**, и в твоём случае она даже логичнее.

Ты хочешь не максимальную скорость одного DINO, а **разнести пайплайн по разным ресурсам**:

```text
                 526 фотографий
                       │
                       ▼
                PostgreSQL queue
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
       DINO WORKER          QWEN WORKER
          CPU                  GPU
       2–4 процесса        1 процесс
             │                   │
             ▼                   ▼
       dino_* поля           qwen_* поля
             │                   │
             └─────────┬─────────┘
                       ▼
                 SORT WORKER
```

И это **хорошая архитектура**.

### Почему это подходит

Сейчас мы увидели:

- DINO CPU: ~6.5 фото/сек;
- CPU при этом загружен только примерно до 50%;
- DINO GPU практически не использует RTX;
- Qwen, наоборот, является GPU-heavy задачей.

Поэтому нет смысла заставлять DINO занимать GPU.

Можно сделать:

**DINO:**

```text
CPU
├── dino worker #1
├── dino worker #2
├── dino worker #3
└── dino worker #4
```

а:

**Qwen:**

```text
RTX 3060
└── qwen worker
```

Они будут работать **одновременно**, поскольку практически не конкурируют за один и тот же ресурс.

---

### Но я бы начал с 2 DINO процессов

Не сразу 4.

У нас 12 CPU threads. Один DINO сейчас потребляет около 50% общей загрузки, поэтому теоретически:

```text
1 DINO → ~50%
2 DINO → ~100%
```

Но реальная загрузка может быть ниже/выше из-за конкуренции за RAM, JPEG decode и PyTorch threads.

Поэтому тест:

```text
2 DINO CPU workers
```

Если получим условно:

```text
1 worker → 83 сек
2 workers → 43–50 сек
```

— отлично.

Если:

```text
1 worker → 83 сек
2 workers → 75 сек
```

— значит каждый процесс надо ограничить по внутренним CPU threads.

---

### И главное — Qwen при этом можно запускать одновременно

Например:

```text
CPU                         GPU
────────────────────        ─────────────────
DINO #1 ────────┐
DINO #2 ────────┤
DINO #3 ────────┤
                │
                │            Qwen
                │             │
                └──── DB ─────┤
                              │
                         RTX 3060
```

То есть **526 фотографий не проходят последовательно DINO → Qwen → Sort**.

Они превращаются в независимые очереди:

```text
photos
  │
  ├── dino_status
  ├── qwen_status
  ├── sort_status
  └── preview_status
```

И это как раз то, что у тебя уже заложено в PostgreSQL.

---

### Более того, это позволит нам сделать красивую схему

Например, одна фотография:

```text
PH_00000123

DINO:
pending → processing → done
                    ↓
              94_v33 / 0.884

QWEN:
pending → processing → done
                    ↓
              text / objects / colors

SORT:
pending → processing → done
                    ↓
              адресная папка

PREVIEW:
pending → processing → done
                    ↓
              preview.jpg
```

Причём **Qwen совершенно не обязан ждать DINO**, если его анализ независим.

А если позже решим, что Qwen должен использовать результат DINO, тогда просто зададим зависимость:

```text
DINO done
    ↓
QWEN
    ↓
SORT
```

---

**И я бы именно так и строил твою фотобазу:** не один огромный последовательный worker, а несколько специализированных workers, которые используют PostgreSQL как диспетчер очередей.

Следующий эксперимент тогда имеет смысл не `GPU batch`, а **2 DINO CPU workers одновременно** и посмотреть реальную загрузку CPU и время на 526 фото.

---

### 👤 **User** — 2026-08-18 22:18:13

----------------------------------------------------------------------
BATCH=1
RESULT_SHAPE=(526, 768)
DINO_TIME=28.16 sec
IMG_PER_SEC=18.68
SEC_PER_IMAGE=0.0535
VRAM_ALLOCATED=0.331 GB
VRAM_RESERVED=0.381 GB

----------------------------------------------------------------------
BATCH=8
RESULT_SHAPE=(526, 768)
DINO_TIME=26.30 sec
IMG_PER_SEC=20.00
SEC_PER_IMAGE=0.0500
VRAM_ALLOCATED=0.331 GB
VRAM_RESERVED=0.484 GB

----------------------------------------------------------------------
BATCH=16
RESULT_SHAPE=(526, 768)
DINO_TIME=26.71 sec
IMG_PER_SEC=19.69
SEC_PER_IMAGE=0.0508
VRAM_ALLOCATED=0.331 GB
VRAM_RESERVED=0.635 GB

---

### 🤖 **Assistant** — 2026-08-18 22:18:14

Да, теперь картина стала очень ясной.

### Чистый DINO на RTX 3060

| Batch | 526 фото | Фото/с | VRAM |
|---:|---:|---:|---:|
| 1 | 28.16 с | 18.68 | 0.33 GB |
| **8** | **26.30 с** | **20.00** | 0.33 GB |
| 16 | 26.71 с | 19.69 | 0.33 GB |

**Вывод:** GPU DINO работает примерно в **3 раза быстрее CPU**:

- CPU batch 8: **6.86 фото/с**
- GPU batch 8: **20.00 фото/с**

Но для нашей архитектуры это даже не главный плюс.

### Самое интересное — GPU почти пустой

DINO занимает всего:

```text
VRAM allocated: 0.331 GB
VRAM reserved : 0.484–0.635 GB
```

из **11.63 GB**.

То есть RTX 3060 спокойно может одновременно обслуживать **Qwen**, если Qwen не забирает всю GPU.

Но здесь есть нюанс: **CUDA DINO и Qwen будут конкурировать за вычислительные ресурсы GPU**, даже если VRAM хватает. Поэтому вариант

```text
DINO CPU  ────────────────┐
                          ├── параллельно
Qwen GPU ─────────────────┘
```

по-прежнему выглядит правильнее.

### Я бы сейчас зафиксировал архитектуру так

```text
                 PostgreSQL
                     │
             ┌───────┴───────┐
             │               │
             ▼               ▼
       DINO CPU queue     QWEN GPU queue
             │               │
       2 CPU workers      1 GPU worker
             │               │
             └───────┬───────┘
                     ▼
                 PostgreSQL
                     │
              ┌──────┴──────┐
              ▼             ▼
           SORT          PREVIEW
```

И **DINO на CPU не потому, что GPU слабый**, а потому что мы хотим освободить RTX 3060 для Qwen.

---

### Следующий тест я бы сделал именно такой

Не надо сейчас гонять все 526 ещё раз.

Сделаем **2 экземпляра `dino_worker` одновременно** на CPU и посмотрим:

1. сколько реально займёт обработка;
2. загрузку CPU;
3. не начнут ли workers мешать друг другу;
4. сколько останется CPU для остальных процессов.

Если 2 worker-а дадут примерно:

```text
1 worker → 76–83 с
2 worker → ~40–45 с
```

то **2 DINO workers — оптимальный вариант**.

Если CPU при этом будет около 80–90%, оставим два.

Если будет только 60–70% и скорость почти удвоится — можно попробовать **3**.

**4 я пока не ставил бы.** Нам нужно оставить запас CPU для PostgreSQL, файловой системы, preview и Qwen-инфраструктуры.

И ещё важный момент: в текущем `dino_worker.py` есть небольшая архитектурная проблема — `max_items` проверяется **после claim**, поэтому при тестах это надо учитывать. Но для нормальной очереди это не критично.

Сейчас мы уже получили главное: **GPU DINO ≈20 фото/с, CPU DINO ≈6.5–7 фото/с, а задача у нас не "выжать максимум DINO", а освободить GPU под Qwen. Поэтому CPU DINO + GPU Qwen — правильное направление.**

---

### 👤 **User** — 2026-08-18 22:18:52

проверяем

---

### 🤖 **Assistant** — 2026-08-18 22:18:52

Да. Проверяем **2 DINO worker-а одновременно на CPU**.

Сначала очистим только тестовую очередь и запустим два процесса. Чтобы результаты не смешивались с предыдущими.

### 1. Сбросить DINO для всех 526

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "UPDATE photos SET dino_status='pending', dino_fingerprint=NULL, dino_score=NULL, dino_second_score=NULL, dino_margin=NULL, dino_time_sec=NULL, error_message=NULL, updated_at=CURRENT_TIMESTAMP;"
```

Проверяем:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT dino_status, COUNT(*) FROM photos GROUP BY dino_status ORDER BY dino_status;"
```

Должно быть:

```text
 pending | 526
```

### 2. Первый worker

Терминал №1:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
SCENE_DEVICE=cpu /usr/bin/time -f 'REAL_TIME=%e sec' \
uv run python app/workers/dino_worker.py
```

### 3. Второй worker

Сразу во втором терминале:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
SCENE_DEVICE=cpu /usr/bin/time -f 'REAL_TIME=%e sec' \
uv run python app/workers/dino_worker.py
```

Они будут брать разные строки благодаря:

```sql
FOR UPDATE SKIP LOCKED
```

То есть **одну фотографию два worker-а не возьмут**.

### 4. После окончания обоих

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT dino_status, COUNT(*) FROM photos GROUP BY dino_status ORDER BY dino_status;"
```

И ещё:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT COUNT(*) AS done, ROUND(AVG(dino_time_sec)::numeric,3) AS avg_sec, MIN(dino_time_sec) AS min_sec, MAX(dino_time_sec) AS max_sec FROM photos WHERE dino_status='done';"
```

**Пришли вывод двух worker-ов + эти два SQL результата.** По ним решим, оставляем **2**, пробуем **3**, или сразу фиксируем 2 как оптимальный режим.

---

### 👤 **User** — 2026-08-18 22:22:37

Дино на ЦПУ распознает адреса, записывает в базу, отсортировывает виртуально, грид готов отображать, в этом время квен на гпу постепенно описывает фото и по мере готвнойсти описание видно в гриде

---

### 🤖 **Assistant** — 2026-08-18 22:22:38

Да. **Именно такую схему я бы сейчас и зафиксировал как целевую.**

Причём здесь важна мысль: **DINO и Qwen — два независимых конвейера одной фотографии**, а PostgreSQL является их общей шиной состояния.

```text
                         ФОТОБАЗА
                            │
                            ▼
                     PostgreSQL photos
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
       DINO — CPU                     QWEN — GPU
       2 worker-а                     1 worker
              │                           │
              │                           │
       распознаёт адрес              описывает фото
              │                           │
              ▼                           ▼
       dino_fingerprint             text_json
       dino_score                   objects_json
       dino_margin                  colors_json
              │                     environment_json
              │                     ...
              ▼                           │
        ВИРТУАЛЬНАЯ                       │
        СОРТИРОВКА                         │
              │                           │
              └─────────────┬─────────────┘
                            ▼
                         GRID
```

### Что пользователь видит

Фото **не ждёт окончания всего анализа**.

Сразу после появления записи:

```text
Фото
 ├─ превью
 ├─ имя
 └─ статус
```

DINO быстро определяет:

```text
94_v33
score 0.884
margin 0.032
```

и грид уже может показать:

> **Шолохова 127 А**

То есть фотография **виртуально оказывается в нужном адресе**, без физического копирования.

Параллельно Qwen продолжает работу:

```text
Qwen: processing...
```

а затем в БД появляются:

```text
description
objects
colors
environment
camera_view
quality
```

и **грид автоматически получает эти данные**.

Например:

```text
┌──────────────────────────────┐
│           ФОТО               │
│                              │
│                              │
├──────────────────────────────┤
│ Шолохова 127 А               │ ← DINO уже готов
│                              │
│ Qwen: анализ...              │
└──────────────────────────────┘
```

через некоторое время:

```text
┌──────────────────────────────┐
│           ФОТО               │
│                              │
├──────────────────────────────┤
│ Шолохова 127 А               │
│                              │
│ Серый фасад, вывеска...      │ ← Qwen готов
│ Объекты: здание, вывеска     │
│ Цвета: серый, белый          │
└──────────────────────────────┘
```

### И физически ничего сортировать не надо

Это особенно хорошо сочетается с твоей текущей БД.

`source_path` остаётся исходным:

```text
data/input/daily/Шолохова 127 А (9).JPG
```

а принадлежность определяется полями:

```text
dino_fingerprint = 94_v33
dino_score       = 0.884
```

И уже UI говорит:

```text
94_v33 → Шолохова 127 А
```

То есть **виртуальная сортировка**, без копирования 526 фотографий по папкам.

---

### Поэтому я бы разделил систему на 4 независимых состояния

```text
DINO
pending → processing → done/error

QWEN
pending → processing → done/error

SORT
pending → processing → done/error

PREVIEW
pending → processing → done/error
```

Причём **DINO не должен ждать Qwen**, и **Qwen не должен ждать DINO**, если для его анализа адрес не нужен.

Это даст именно тот эффект, который ты описал:

> **DINO постепенно раскладывает фотографии по адресам → грид сразу показывает результат → Qwen в фоне постепенно дополняет каждую карточку информацией.**

И это уже гораздо лучше, чем наша первоначальная последовательная схема `DINO → Qwen → сортировка → отображение`.

---

### 👤 **User** — 2026-08-18 22:23:10

[DINO] PH_00000525 Шолохова 127 А (8).JPG
[DINO] DONE PH_00000525 -> 94_v33 score=0.897045 margin=0.016224 time=0.59s
[DINO] Queue empty.

[DINO] Worker stopped.
REAL_TIME=168.62 sec
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:23:11

Вот это уже полезный замер.

**Один CPU DINO worker:**

- 526 фото
- `REAL_TIME = 168.62 с`
- ≈ **3.12 фото/с**
- среднее время отдельного фото по последнему примеру: `0.59 с`

Это заметно медленнее нашего отдельного теста `embed_images()` (~6.8 фото/с), потому что worker делает не только DINO embedding, но и **полное сравнение с fingerprint-ами + CPU-дескрипторы + работу с БД**.

И главное: это подтверждает, что **не надо пытаться ускорять именно DINO любой ценой**.

### Следующий эксперимент

Теперь запускаем **2 `dino_worker` одновременно** на тех же 526 фото.

Если получим примерно:

- **80–100 с** → отлично, 2 worker-а почти идеально масштабируются;
- **100–120 с** → всё равно хорошо;
- **150+ с** → CPU/диск/модель начинают конфликтовать, и два worker-а мало что дают.

После этого уже можно зафиксировать:

**2 CPU DINO workers + 1 GPU Qwen worker.**

И тогда получится именно нужный нам поток:

```text
526 фото
   │
   ├── DINO CPU #1 ──┐
   │                 ├── PostgreSQL ──→ GRID
   └── DINO CPU #2 ──┘       │
                             │
                             └── Qwen GPU ──→ дополняет GRID
```

Причём **GRID начинает работать сразу**, не дожидаясь окончания 526 фотографий.

---

### 👤 **User** — 2026-08-18 22:23:15

[DINO] PH_00000526 Шолохова 127 А (9).JPG
[DINO] DONE PH_00000526 -> 94_v33 score=0.884367 margin=0.031779 time=0.54s
[DINO] Queue empty.

[DINO] Worker stopped.
REAL_TIME=160.50 sec

---

### 🤖 **Assistant** — 2026-08-18 22:23:18

Да, **160.5 с против 168.6 с** — небольшое улучшение (~5%), то есть один запуск сам по себе уже довольно стабилен.

Но важный момент: **это ещё не тест параллельных DINO**. Сейчас был один worker.

Следующий эксперимент имеет смысл именно такой:

1. Сбросить `dino_status` для всех 526:
   - `pending`
   - очистить результаты DINO.
2. Запустить **два процесса `dino_worker.py` одновременно**.
3. Замерить общее время до `Queue empty`.
4. Проверить после окончания:
   - `done = 526`
   - `processing = 0`
   - `pending = 0`
   - `error = 0`
5. Сравнить с базой **160.5 с**.

Если два процесса дадут, например, **85–100 с**, то я бы оставлял именно **2 DINO CPU worker-а**. Больше пока не нужно: нам важнее освободить RTX 3060 под Qwen.

И архитектурно тогда получаем нужную нам схему:

**CPU → 2× DINO → PostgreSQL → виртуальная сортировка/GRID**

одновременно:

**GPU → Qwen → PostgreSQL → постепенное дополнение карточек GRID**

Это уже правильная архитектура для нашей фотобазы.

---

### 👤 **User** — 2026-08-18 22:23:27

цпу не более 50%

---

### 🤖 **Assistant** — 2026-08-18 22:23:28

Да. Это как раз важный результат.

При текущем **одном DINO worker** CPU максимум около **50%**, а GPU практически простаивает. Значит, у нас есть запас по CPU.

Я бы сейчас проверял **2 DINO worker-а**:

- ожидаем загрузку CPU примерно до **70–100%**, но не обязательно;
- GPU остаётся свободным для Qwen;
- если два worker-а дают существенное ускорение — оставляем 2;
- если CPU всё равно держится около 50%, можно проверить **3 worker-а**.

Но есть нюанс: у каждого процесса свой экземпляр DINO, поэтому **2–3 процесса будут одновременно держать модель в RAM**, а GPU здесь не участвует, если DINO действительно работает на CPU.

Для нашей цели оптимальная конфигурация сейчас выглядит так:

**DINO: 2 CPU процесса → БД → GRID**  
**Qwen: 1 GPU процесс → БД → GRID**

То есть мы не стремимся загрузить CPU на 100%. Нам нужно **использовать свободный CPU, пока RTX 3060 занимается Qwen**.

---

### 👤 **User** — 2026-08-18 22:24:06

да

---

### 🤖 **Assistant** — 2026-08-18 22:24:07

Да. Тогда следующий тест — **2 DINO worker-а параллельно**, без изменения кода.

Сначала сбрасываем 526 записей:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "UPDATE photos
      SET dino_status='pending',
          dino_fingerprint=NULL,
          dino_score=NULL,
          dino_second_score=NULL,
          dino_margin=NULL,
          dino_time_sec=NULL,
          error_message=NULL,
          updated_at=CURRENT_TIMESTAMP;"
```

Проверяем:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT dino_status, COUNT(*) FROM photos GROUP BY dino_status ORDER BY dino_status;"
```

Должно быть:

```text
pending | 526
```

### Запускаем два worker-а

Открой **два терминала**.

**Терминал 1:**

```bash
cd ~/projects/scene_fingerprint_mvp_v02
time uv run python app/workers/dino_worker.py
```

**Терминал 2 сразу после старта первого:**

```bash
cd ~/projects/scene_fingerprint_mvp_v02
time uv run python app/workers/dino_worker.py
```

Они используют:

```sql
FOR UPDATE SKIP LOCKED
```

поэтому **одно и то же фото дважды обрабатывать не должны**. Один worker забирает одну запись, второй — следующую.

Во время работы смотри:

```bash
watch -n 1 nvidia-smi
```

и в другом терминале:

```bash
top
```

Нас особенно интересуют:

- CPU — насколько поднимется выше прежних ~50%;
- GPU utilization — должен оставаться практически свободным;
- VRAM — DINO на CPU не должен занимать VRAM;
- итоговое время двух worker-ов.

После окончания:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT dino_status, COUNT(*) FROM photos GROUP BY dino_status ORDER BY dino_status;"
```

И отдельно:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT COUNT(*) AS done,
             COUNT(dino_fingerprint) AS with_fp,
             AVG(dino_time_sec) AS avg_sec
      FROM photos
      WHERE dino_status='done';"
```

**Главный показатель:** сравним общее время **160.5 с → время двух worker-ов**.

Если получим около **80–100 секунд**, я бы практически зафиксировал **2 DINO CPU worker-а** и дальше уже подключал Qwen на GPU параллельно.

---

### 👤 **User** — 2026-08-18 22:26:47

[DINO] PH_00000526 Шолохова 127 А (9).JPG
[DINO] DONE PH_00000526 -> 94_v33 score=0.884367 margin=0.031779 time=0.37s
[DINO] Queue empty.

[DINO] Worker stopped.

real	1m42.746s
user	1m46.773s
sys	0m15.036s   [DINO] PH_00000525 Шолохова 127 А (8).JPG
[DINO] DONE PH_00000525 -> 94_v33 score=0.897045 margin=0.016224 time=0.35s
[DINO] Queue empty.

[DINO] Worker stopped.

real	1m41.935s
user	1m45.168s
sys	0m16.945s
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:26:47

Вот теперь картина понятна.

### 2 DINO-процесса

Получили:

| | 1 процесс | 2 процесса |
|---|---:|---:|
| Real | **160.5 с** | **~102 с** |
| На 526 фото | 3.28 фото/с | **~5.15 фото/с** |
| Среднее на фото | 0.305 с | **~0.194 с** |
| Ускорение | 1× | **~1.57×** |

При этом два процесса практически одинаково завершились: **101.94 и 102.75 с**. Это хороший признак — очередь и `SKIP LOCKED` работают нормально.

И самое интересное: отдельный `DINO DONE` теперь около **0.35–0.37 с**, против ~0.54 с в предыдущем запуске. То есть параллельная работа действительно помогает.

### Я бы пока зафиксировал 2 процесса

Не стал бы сейчас переходить на 3–4. Наша задача не сделать DINO максимально быстрым, а получить:

**CPU**
→ 2 × DINO  
→ адрес + score + margin  
→ PostgreSQL  
→ виртуальная сортировка  
→ GRID сразу показывает фото

**GPU**
→ Qwen  
→ анализ фото  
→ PostgreSQL  
→ GRID постепенно дополняется описанием.

И это уже очень хорошее разделение ресурсов.

Следующий действительно полезный тест — **запустить DINO ×2 и Qwen одновременно на всех 526 фото**. Тогда проверим именно конечную архитектуру: насколько Qwen занимает RTX 3060 и не мешает ли ему DINO.

---

### 👤 **User** — 2026-08-18 22:26:55

ЦПУ 25%.ВРАМ 2ГБ

---

### 🤖 **Assistant** — 2026-08-18 22:26:56

Отлично. Тогда это ещё лучше, чем мы ожидали.

При **2 DINO-процессах**:

- **CPU ~25%** — процессор практически свободен.
- **VRAM ~2 ГБ** — GPU тоже имеет огромный запас.
- DINO: ~**102 с / 526 фото**.
- Qwen можно спокойно запускать параллельно на GPU.

То есть сейчас у нас **нет необходимости оптимизировать DINO ради загрузки CPU**. Мы получили именно то, чего хотели: DINO работает независимо и быстро, не отбирая ресурсы у Qwen.

Я бы следующую конфигурацию уже тестировал как боевую:

```text
                    526 фото
                       │
             ┌─────────┴─────────┐
             │                   │
        2 × DINO CPU          Qwen GPU
             │                   │
       ~102 сек                 │
             │                   │
      адрес + score              │
      + margin                   │
             │                   │
             └───────┬───────────┘
                     ↓
                 PostgreSQL
                     ↓
              виртуальный GRID
                     ↓
       фото появляются сразу
       Qwen дописывает данные
       по мере готовности
```

**Следующий тест я бы уже не делал отдельно DINO.** Запускаем DINO ×2 + Qwen одновременно и смотрим:

1. CPU;
2. GPU utilization;
3. VRAM;
4. время DINO;
5. скорость Qwen;
6. появляются ли результаты в БД постепенно;
7. обновляется ли GRID без ожидания завершения всей очереди.

Если это проходит — **архитектуру распараллеливания можно считать практически зафиксированной.**

---

### 👤 **User** — 2026-08-18 22:27:17

давай

---

### 🤖 **Assistant** — 2026-08-18 22:27:17

Да. Тогда запускаем **реальный параллельный тест: 2× DINO на CPU + Qwen на GPU**.

Но сначала важно не запускать старые `processing` записи. Сделаем аккуратный сброс только очередей анализа.

### 1. Сброс DINO и Qwen

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "UPDATE photos
      SET
        dino_status='pending',
        dino_fingerprint=NULL,
        dino_score=NULL,
        dino_second_score=NULL,
        dino_margin=NULL,
        dino_time_sec=NULL,
        qwen_status='pending',
        text_json=NULL,
        colors_json=NULL,
        objects_json=NULL,
        environment_json=NULL,
        image_quality_json=NULL,
        camera_view_json=NULL,
        scene_objects_json=NULL,
        analysis_quality_json=NULL,
        raw_json=NULL,
        error_message=NULL,
        updated_at=CURRENT_TIMESTAMP;"
```

Проверяем:

```bash
psql -X -P pager=off \
  -h localhost -p 5432 -U lora -d photobase \
  -c "SELECT
        dino_status,
        qwen_status,
        COUNT(*)
      FROM photos
      GROUP BY dino_status, qwen_status
      ORDER BY dino_status, qwen_status;"
```

Должно быть:

```text
pending | pending | 526
```

### 2. Запускаем DINO ×2

**Терминал №1:**

```bash
cd ~/projects/scene_fingerprint_mvp_v02
time uv run python app/workers/dino_worker.py
```

**Терминал №2:**

```bash
cd ~/projects/scene_fingerprint_mvp_v02
time uv run python app/workers/dino_worker.py
```

### 3. Qwen

В **третьем терминале** запускаем именно тот Qwen-worker, который сейчас есть в проекте. Сначала найдём его, чтобы случайно не запустить старую версию:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find app scripts -type f -name "*.py" -print | sort | \
grep -Ei 'qwen|worker'
```

Пришли вывод этой команды.

**Пока Qwen не запускай.** Сначала определим точный worker, чтобы одновременно не запустить неправильный вариант.

После этого будем смотреть уже настоящую картину:

**2× DINO CPU + 1× Qwen GPU → PostgreSQL → GRID.**

---

### 👤 **User** — 2026-08-18 22:28:00

find app scripts -type f -name "*.py" -print | sort | \
grep -Ei 'qwen|worker'
app/pipeline/worker.py
app/web/components/technical_modules/qwen.py
app/workers/dino_worker.py
scripts/banner_qwen25vl_test_v01.py
scripts/banner_qwen4b_test_v01.py
scripts/import_qwen_to_db.py
scripts/qwen4b_output_v01_before_compact_prompt.py
scripts/qwen4b_output_v01.py
scripts/qwen_prompt_ablation.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 22:28:01

Да. Здесь **Qwen-worker пока отдельным файлом не выделен**. Судя по структуре, `app/workers/dino_worker.py` — готовый worker, а Qwen сейчас, вероятно, ещё вызывается из pipeline/технического модуля.

Нам сейчас важно **не переделывать архитектуру**, а сначала понять, где реально запускается Qwen.

Дай вывод:

```bash id="9xj2qk"
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,280p' app/pipeline/worker.py

echo
echo "================ QWEN MODULE ================"

sed -n '1,260p' app/web/components/technical_modules/qwen.py

echo
echo "================ QWEN REFERENCES ================"

grep -RniE "qwen_status|qwen4b|qwen3|ollama|Qwen|qwen" \
  app scripts \
  --include="*.py" | head -250
```

После этого я скажу **конкретно какую команду запускать в третьем терминале**.

Пока два DINO можно оставить работающими. Их как раз и хотим параллельно нагрузить Qwen.

---

### 👤 **User** — 2026-08-18 22:28:48

отдельный квен привящан к кнопке в технастройках веб интерфейса

---

### 🤖 **Assistant** — 2026-08-18 22:28:49

Да, тогда всё сходится. **Qwen сейчас не worker, а ручной запуск через кнопку в технических настройках веб-интерфейса.**

И это даже удобно для нашего теста: **не надо сейчас делать отдельный Qwen worker**.

Схема теста:

```text
                 PostgreSQL
                 /        \
                /          \
       DINO ×2 CPU       Qwen GPU
           │                 │
           │                 │
      адрес / score      описание /
      margin             объекты /
           │              цвета /
           │                 │
           └───────┬─────────┘
                   ↓
             виртуальный GRID
```

### Что делаем сейчас

1. **Оставляем 526 записей `pending/pending`.**
2. Запускаем **два DINO worker-а**.
3. Открываем веб-интерфейс.
4. В технических настройках нажимаем **Qwen**.
5. Qwen начинает обрабатывать свою очередь на GPU.
6. Смотрим одновременно:
   - CPU;
   - GPU %;
   - VRAM;
   - скорость DINO;
   - скорость Qwen;
   - заполнение PostgreSQL;
   - появление результатов в GRID.

И главное — **не ждём окончания DINO**, чтобы запускать Qwen. Именно это и проверяем: Qwen должен работать **одновременно** с DINO.

### Очень важный момент

Сейчас у нас DINO уже показывает:

**CPU ≈25%**  
**VRAM ≈2 GB**

Поэтому RTX 3060 практически свободна для Qwen.

После запуска Qwen я бы ожидал примерно такую картину:

```text
CPU
█████░░░░░░░░░░░░░░░  ~25%

GPU
████████████░░░░░░░░  высокая загрузка

VRAM
████████░░░░░░░░░░░░  несколько GB
```

Если при этом **DINO останется около 100–110 секунд на 526 фото**, а Qwen будет нормально обрабатывать очередь — всё, **распределение CPU/GPU получилось именно таким, как мы хотели**.

**Запускай два DINO и нажимай Qwen в технастройках.** Затем пришли текущие `CPU / GPU / VRAM` и пару строк из обоих процессов.

---

