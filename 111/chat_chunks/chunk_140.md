## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 🤖 **Assistant** — 2026-08-18 23:39:03

Да, теперь видно точную точку входа. `photo_ingest.py` уже делает главное правильно: **`photo_id` создаётся до разделения на DINO/Qwen**. `Pasted text.txt`

Я бы сейчас сделал так:

```text
                 INGEST
                    │
                    ▼
              ┌───────────┐
              │  PHOTOS DB │
              └─────┬─────┘
                    │
       photo_id + initial_id
                    │
             ┌──────┴──────┐
             ▼             ▼
           DINO           QWEN
             │             │
         address_id     описание
             │             │
             └──────┬──────┘
                    ▼
                  GRID
```

Причём:

- `photo_id` - **главный постоянный идентификатор фотографии**;
- `initial_id` - **идентификатор поступления/исходной записи**, не зависит от будущего адреса;
- `address_id` - появляется **только после DINO**;
- Qwen вообще не использует `address_id`;
- Qwen связывает результат исключительно по `photo_id`;
- GRID показывает фото только когда `address_id IS NOT NULL`.

### 1. Как сделаем `initial_id`

Я предлагаю:

```text
IN_20260818_193012_000001
IN_20260818_193012_000002
IN_20260818_193012_000003
```

Это идентификатор **конкретного запуска ingest** + порядковый номер.

А:

```text
PH_00000123
```

остаётся постоянным `photo_id`.

То есть:

```text
initial_id = IN_20260818_193012_000001
photo_id   = PH_00000123
```

Если потом фотография получит:

```text
address_id = 78
```

Qwen всё равно работает с:

```text
photo_id = PH_00000123
```

и ему совершенно не нужен `78`.

---

# 2. Меняем `photo_ingest.py`

В начало файла после импортов добавь:

```python
from datetime import datetime
```

Было:

```python
import argparse
from pathlib import Path

import psycopg2
```

Сделай:

```python
import argparse
from datetime import datetime
from pathlib import Path

import psycopg2
```

---

### 3. Добавляем генератор initial_id

После:

```python
def make_photo_id(number):
    return f"PH_{number:08d}"
```

добавь:

```python
def make_initial_id(timestamp, number):
    return f"IN_{timestamp}_{number:06d}"
```

---

# 4. Меняем `register_photo()`

Полностью замени текущую функцию:

```python
def register_photo(
    conn,
    photo_id,
    source_path,
):
    ...
```

на:

```python
def register_photo(
    conn,
    photo_id,
    initial_id,
    source_path,
):
    """
    Создаёт первичную запись фотографии.

    photo_id:
        постоянный идентификатор фотографии.

    initial_id:
        идентификатор исходного поступления.
        Не зависит от DINO, Qwen и address_id.

    После этой записи фотография одновременно
    становится доступной двум независимым очередям:
        DINO
        Qwen
    """

    filename = Path(source_path).name

    with conn.cursor() as cur:

        cur.execute("""
            INSERT INTO photos (
                photo_id,
                initial_id,

                source_path,
                path,

                filename,
                original_filename,

                status,

                dino_status,
                qwen_status,
                sort_status,
                preview_status,

                address_id
            )
            VALUES (
                %s,
                %s,

                %s,
                %s,

                %s,
                %s,

                'pending',

                'pending',
                'pending',
                'pending',
                'pending',

                NULL
            )
        """, (
            photo_id,
            initial_id,

            source_path,
            source_path,

            filename,
            filename,
        ))
```

---

# 5. Меняем цикл ingest

Внутри:

```python
with psycopg2.connect(**PG_CONFIG) as conn:
```

после:

```python
next_number = get_next_photo_number(conn)
```

добавь:

```python
ingest_timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)
```

Получится:

```python
with psycopg2.connect(**PG_CONFIG) as conn:

    existing_paths = get_existing_source_paths(conn)

    next_number = get_next_photo_number(conn)

    ingest_timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    registered = 0
    skipped = 0
```

---

Затем вместо:

```python
photo_id = make_photo_id(
    next_number
)

register_photo(
    conn,
    photo_id,
    source_path,
)
```

делаем:

```python
photo_id = make_photo_id(
    next_number
)

initial_id = make_initial_id(
    ingest_timestamp,
    registered + 1,
)

register_photo(
    conn,
    photo_id,
    initial_id,
    source_path,
)
```

И вывод:

```python
print(
    f"[REGISTER] {photo_id}"
    f"  {initial_id}"
    f"  {image.name}"
)
```

---

# 6. В результате новая фотография сразу будет выглядеть в БД так

```text
photo_id       PH_00000123
initial_id     IN_20260818_193012_000001
source_path    /.../INPUT/photo.jpg

dino_status    pending
qwen_status    pending

address_id     NULL
```

И это **важнейший момент архитектуры**:

### DINO

Берёт:

```sql
WHERE dino_status = 'pending'
```

и после обработки делает:

```text
dino_status = done
address_id  = 78
```

### Qwen

Одновременно может взять:

```sql
WHERE qwen_status = 'pending'
```

и сделать:

```text
qwen_status = done
description = ...
```

При этом:

```text
address_id
```

ему вообще не нужен.

---

# 7. GRID

Для грида потом будет принципиально простой запрос:

```sql
SELECT *
FROM photos
WHERE address_id IS NOT NULL
ORDER BY id;
```

То есть фотография **не появляется в гриде просто потому, что её зарегистрировали**.

Она появляется после:

```text
DINO
 ↓
address_id
 ↓
GRID
```

А данные Qwen могут прийти:

```text
до DINO
после DINO
одновременно с DINO
```

и всё равно автоматически подтянутся к той же записи:

```text
photo_id
```

---

## 8. Но есть ещё одна важная вещь

Сейчас у нас `initial_id` уже есть в таблице, но **его нет в unique constraint**.

Я бы пока **не делал его UNIQUE**.

Потому что его задача - служебный идентификатор поступления, а настоящим ключом фотографии остаётся:

```text
photo_id
```

У тебя уже есть:

```text
PRIMARY KEY (photo_id)
UNIQUE (id)
UNIQUE (source_path)
```

Это хорошо.

---

## 9. Проверка после изменения

После внесения изменений:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python -m py_compile scripts/photo_ingest.py
```

Потом:

```bash
grep -nE \
'initial_id|make_initial_id|register_photo|dino_status|qwen_status|address_id' \
scripts/photo_ingest.py
```

И затем **не запускаем ingest на настоящей папке**.

Сначала я предлагаю проверить на маленькой тестовой папке, чтобы не засорять production-базу.

Следующим шагом уже делаем **DINO worker**, чтобы он писал именно:

```text
photo_id
    ↓
dino
    ↓
address_id
```

и одновременно добавим механизм:

```text
PENDING
PROCESSING
DONE
ERROR
PAUSED
```

с возможностью **продолжить / пропустить / обработать заново**, который потом напрямую подключим к кнопкам `ЗАПУСТИТЬ / ПАУЗА / ОСТАНОВИТЬ`.

---

### 👤 **User** — 2026-08-18 23:39:22

давай файлы

---

### 🤖 **Assistant** — 2026-08-18 23:39:22

Да. Давай сделаем **готовые файлы**, а не по кускам.

Сейчас нужны три файла:

1. `scripts/photo_ingest.py` — новый `initial_id` + общий `photo_id`.
2. `app/workers/dino_worker.py` — DINO работает по `photo_id`, результат пишет в `address_id`.
3. `scripts/qwen4b_output_v01.py` — Qwen работает по тому же `photo_id`, независимо от DINO.

Но чтобы я дал их **точно совместимыми с твоей текущей версией**, сначала пришли текущий `dino_worker.py` целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02
cat app/workers/dino_worker.py
```

`photo_ingest.py` и Qwen у нас уже есть из текущего контекста. После `dino_worker.py` я дам **три готовых файла целиком**, которые можно будет заменить через `cat > файл <<'PY' ... PY`.

---

### 👤 **User** — 2026-08-18 23:39:40

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02
cat app/workers/dino_worker.py
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
            if max_items > 0 and processed >= max_items:
                print(
                    f"[DINO] Reached max_items={max_items}."
                )
                break

            row = claim_photo(conn)

            if row is None:
                print("[DINO] Queue empty.")
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
                    f"[DINO] ERROR "
                    f"{photo_key}: {exc}"
                )

                try:
                    mark_error(
                        conn,
                        photo_id,
                        exc,
                    )
                except Exception as db_error:
                    print(
                        "[DINO] "
                        f"DB ERROR while marking error: "
                        f"{db_error}"
                    )

    finally:
        conn.close()
        print()
        print("[DINO] Worker stopped.")

if __name__ == "__main__":
    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:39:45

> **Preparing dino files**
>
> I’m treating this as a request to provide implementation files next. I’ll focus first on the DINO worker, preserving stable photo IDs, branching status, idempotent retries, and the existing project structure.
>
> **Prepared dino files**
>
> 
>
> Worked for 4s

Да. Тогда первым делом фиксируем **`dino_worker.py`** под новую схему:

- `photo_id` уже существует до запуска DINO/Qwen.
- `initial_id` — внутренний неизменяемый идентификатор партии/источника.
- DINO работает независимо от Qwen.
- Qwen работает независимо от DINO.
- результат DINO записывается в `address_id`.
- `dino_fingerprint` пока сохраняем для совместимости со старым кодом.
- после перезапуска зависший `processing` можно вернуть в `pending`, чтобы продолжить.
- **никакой физической сортировки здесь нет**.
- физическая папка/сортировка будет отдельным последующим слоем.
- `photo_id` остаётся главным ключом связи с Grid.

### Новый `app/workers/dino_worker.py`

```python
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

# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def reset_processing(conn):
    """
    Возвращает зависшие DINO-задачи обратно в очередь.

    Это позволяет продолжить работу после:
        - остановки процесса
        - перезагрузки
        - падения Python
        - аварии машины
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'pending',
                updated_at = CURRENT_TIMESTAMP
            WHERE dino_status = 'processing'
            """
        )

        count = cur.rowcount

    conn.commit()

    if count:
        print(
            f"[DINO] Reset stale processing jobs: {count}"
        )

def claim_photo(conn):
    """
    Забирает следующую фотографию из DINO-очереди.

    ВАЖНО:

    Qwen здесь вообще не учитывается.

    DINO получает фотографию только потому,
    что у неё уже существует photo_id и
    dino_status = pending.
    """

    with conn.cursor(
        cursor_factory=RealDictCursor
    ) as cur:

        cur.execute(
            """
            SELECT
                id,
                photo_id,
                initial_id,
                source_path,
                filename
            FROM photos
            WHERE
                dino_status = 'pending'
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
                dino_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE
                id = %s
                AND dino_status = 'pending'
            """,
            (row["id"],),
        )

        conn.commit()

        return row

# ============================================================
# RESULT
# ============================================================

def mark_done(
    conn,
    db_id,
    result,
    elapsed,
):
    """
    Сохраняет результат DINO.

    Главный результат нового слоя:

        address_id = адрес, определённый DINO.

    photo_id остаётся независимым идентификатором фотографии.
    """

    address_id = result.get("best_id")

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'done',

                address_id = %s,

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
                address_id,

                # Старое поле оставляем для совместимости
                # со старым кодом и статистикой.
                address_id,

                result.get("score"),
                result.get("second_score"),
                result.get("margin"),

                elapsed,

                db_id,
            ),
        )

    conn.commit()

def mark_error(
    conn,
    db_id,
    error,
):
    """
    Фиксирует ошибку конкретной фотографии.

    Qwen-status при этом НЕ меняется.
    """

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
                db_id,
            ),
        )

    conn.commit()

# ============================================================
# WORKER
# ============================================================

def main():

    settings = Settings()

    print("=" * 70)
    print("DINO WORKER")
    print("=" * 70)
    print("device  :", settings.device)
    print("database:", DB_CONFIG["dbname"])
    print("=" * 70)

    # --------------------------------------------------------
    # MODEL
    # --------------------------------------------------------

    print("[DINO] Loading SceneEmbedder...")

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

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    conn = get_connection()

    print("[DINO] Database connected.")

    # --------------------------------------------------------
    # RECOVERY
    # --------------------------------------------------------

    reset_processing(conn)

    print("[DINO] Worker ready.")

    max_items = int(
        os.getenv(
            "DINO_MAX_ITEMS",
            "0",
        )
    )

    processed = 0
    errors = 0

    try:

        while True:

            # ------------------------------------------------
            # LIMIT
            # ------------------------------------------------

            if (
                max_items > 0
                and processed >= max_items
            ):
                print(
                    f"[DINO] "
                    f"Reached max_items={max_items}."
                )
                break

            # ------------------------------------------------
            # CLAIM
            # ------------------------------------------------

            row = claim_photo(conn)

            if row is None:

                print(
                    "[DINO] Queue empty."
                )

                break

            db_id = row["id"]
            photo_id = row["photo_id"]
            initial_id = row["initial_id"]
            source_path = Path(
                row["source_path"]
            )

            print()
            print("-" * 70)

            print(
                "[DINO]",
                photo_id,
                "| initial_id:",
                initial_id,
                "| file:",
                source_path.name,
            )

            started = time.perf_counter()

            # ------------------------------------------------
            # PROCESS
            # ------------------------------------------------

            try:

                if not source_path.exists():
                    raise FileNotFoundError(
                        f"Photo not found: {source_path}"
                    )

                if not source_path.is_file():
                    raise FileNotFoundError(
                        f"Not a file: {source_path}"
                    )

                result = recognizer.recognize_one(
                    source_path,
                    top_k=5,
                    threshold=0.65,
                )

                elapsed = (
                    time.perf_counter()
                    - started
                )

                # ------------------------------------------------
                # SAVE
                # ------------------------------------------------

                mark_done(
                    conn,
                    db_id,
                    result,
                    elapsed,
                )

                address_id = result.get(
                    "best_id"
                )

                print(
                    f"[DINO] DONE "
                    f"{photo_id}"
                    f" -> address_id={address_id}"
                    f" score={result.get('score', 0):.6f}"
                    f" margin={result.get('margin', 0):.6f}"
                    f" time={elapsed:.2f}s"
                )

                processed += 1

            # ------------------------------------------------
            # ERROR
            # ------------------------------------------------

            except Exception as exc:

                errors += 1

                elapsed = (
                    time.perf_counter()
                    - started
                )

                print(
                    f"[DINO] ERROR "
                    f"{photo_id}: {exc}"
                    f" time={elapsed:.2f}s"
                )

                try:

                    mark_error(
                        conn,
                        db_id,
                        exc,
                    )

                except Exception as db_error:

                    print(
                        "[DINO] "
                        "DB ERROR while marking error:",
                        db_error,
                    )

    finally:

        conn.close()

        print()
        print("=" * 70)
        print("DINO WORKER STOPPED")
        print("=" * 70)

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
```

### Что теперь получается

Для каждой новой фотографии:

```text
INPUT FILE
    │
    ▼
PHOTO INGEST
    │
    ├── photo_id = PH_00000123
    │
    ├── initial_id = ...
    │
    ├── source_path = ...
    │
    ├── dino_status = pending
    │
    └── qwen_status = pending
             │
             ├──────────────────────┐
             ▼                      ▼
           DINO                    QWEN
             │                      │
             ▼                      ▼
        address_id              description
             │                      │
             └──────────┬───────────┘
                        │
                     photo_id
                        │
                        ▼
                       GRID
```

То есть **DINO и Qwen вообще не ждут друг друга**.

Например, Qwen может закончить:

```text
PH_00000123
qwen_status = done
description = ...
```

а DINO в этот момент ещё:

```text
PH_00000123
dino_status = processing
address_id = NULL
```

И наоборот.

**Grid при этом показывает фотографию только когда `address_id IS NOT NULL`**, а описание Qwen просто подтягивается по тому же `photo_id`.

И ещё важный момент: сейчас `sort_status` и `preview_status` остаются отдельными очередями — их **не надо связывать с DINO/Qwen**. Это следующий слой.

Следующим файлом логично сделать **`photo_ingest.py`**, чтобы он при регистрации сразу правильно создавал `photo_id + initial_id` и одновременно ставил обе независимые очереди `DINO/Qwen` в `pending`.

---

### 👤 **User** — 2026-08-18 23:41:15

далее

---

### 🤖 **Assistant** — 2026-08-18 23:41:17

Да. Следующий слой — **`scripts/photo_ingest.py`**. Здесь фиксируем главное правило:

> `photo_id` и `initial_id` создаются **до разделения потока на DINO и Qwen**.

При этом `initial_id` — внутренний рабочий идентификатор, а `photo_id` — постоянный идентификатор фотографии, по которому потом сводятся все результаты.

### Замени `scripts/photo_ingest.py` целиком

```python
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg2

PROJECT = Path(__file__).resolve().parent.parent

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

# ============================================================
# ID
# ============================================================

def get_next_photo_number(conn):
    """
    Следующий постоянный PHOTO_ID.

    PH_00000001
    PH_00000002
    ...
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT photo_id
            FROM photos
            WHERE photo_id LIKE 'PH_%'
            """
        )

        rows = cur.fetchall()

    max_number = 0

    for (photo_id,) in rows:

        if not photo_id:
            continue

        value = str(photo_id)

        if not value.startswith("PH_"):
            continue

        try:
            number = int(
                value[3:]
            )
        except ValueError:
            continue

        max_number = max(
            max_number,
            number,
        )

    return max_number + 1

def get_next_initial_number(conn):
    """
    Следующий внутренний INITIAL_ID.

    IN_00000001
    IN_00000002
    ...

    INITIAL_ID не зависит от адреса,
    DINO и Qwen.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT initial_id
            FROM photos
            WHERE initial_id LIKE 'IN_%'
            """
        )

        rows = cur.fetchall()

    max_number = 0

    for (initial_id,) in rows:

        if not initial_id:
            continue

        value = str(initial_id)

        if not value.startswith("IN_"):
            continue

        try:
            number = int(
                value[3:]
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

def make_initial_id(number):
    return f"IN_{number:08d}"

# ============================================================
# PATHS
# ============================================================

def normalize_path(path):
    return str(
        Path(path)
        .expanduser()
        .resolve()
    )

def get_existing_source_paths(conn):
    """
    Уже зарегистрированные source_path.

    Используется для безопасного продолжения
    после прерывания ingest.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT source_path
            FROM photos
            WHERE source_path IS NOT NULL
              AND source_path <> ''
            """
        )

        return {
            normalize_path(row[0])
            for row in cur.fetchall()
            if row[0]
        }

def find_images(input_dir):
    """
    Сканирует только файлы непосредственно
    во входной папке.

    Подкаталоги пока не трогаем.
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

# ============================================================
# REGISTER
# ============================================================

def register_photo(
    conn,
    photo_id,
    initial_id,
    source_path,
):
    """
    Создаёт единую первичную запись фотографии.

    На этом этапе НЕ происходит:

        - DINO
        - Qwen
        - сортировка
        - определение адреса
        - создание превью

    Здесь только создаётся объект PHOTО.
    """

    source = Path(source_path)

    filename = source.name

    with conn.cursor() as cur:

        cur.execute(
            """
            INSERT INTO photos (
                photo_id,
                initial_id,

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
                %s,

                'pending',

                'pending',
                'pending',
                'pending',
                'pending'
            )
            """,
            (
                photo_id,
                initial_id,

                source_path,
                source_path,

                filename,
                filename,
            ),
        )

# ============================================================
# INGEST
# ============================================================

def ingest(input_dir):

    input_dir = (
        input_dir
        .expanduser()
        .resolve()
    )

    if not input_dir.exists():

        raise RuntimeError(
            "Input directory does not exist:\n"
            f"{input_dir}"
        )

    if not input_dir.is_dir():

        raise RuntimeError(
            "Input path is not a directory:\n"
            f"{input_dir}"
        )

    images = find_images(
        input_dir
    )

    print("=" * 80)
    print("PHOTO INGEST")
    print("=" * 80)
    print()
    print("INPUT :", input_dir)
    print("FILES :", len(images))
    print()

    if not images:

        print(
            "No images found."
        )

        return

    with psycopg2.connect(
        **DB_CONFIG
    ) as conn:

        # ----------------------------------------------------
        # Existing
        # ----------------------------------------------------

        existing_paths = (
            get_existing_source_paths(
                conn
            )
        )

        # ----------------------------------------------------
        # Next IDs
        # ----------------------------------------------------

        next_photo_number = (
            get_next_photo_number(
                conn
            )
        )

        next_initial_number = (
            get_next_initial_number(
                conn
            )
        )

        registered = 0
        skipped = 0

        # ----------------------------------------------------
        # REGISTER
        # ----------------------------------------------------

        for image in images:

            source_path = (
                normalize_path(
                    image
                )
            )

            # -----------------------------------------------
            # Already registered
            # -----------------------------------------------

            if source_path in existing_paths:

                print(
                    f"[SKIP]      {image.name}"
                    " — already registered"
                )

                skipped += 1

                continue

            # -----------------------------------------------
            # Create IDs
            # -----------------------------------------------

            photo_id = make_photo_id(
                next_photo_number
            )

            initial_id = make_initial_id(
                next_initial_number
            )

            # -----------------------------------------------
            # DB record
            # -----------------------------------------------

            register_photo(
                conn,
                photo_id,
                initial_id,
                source_path,
            )

            existing_paths.add(
                source_path
            )

            print(
                f"[REGISTER] "
                f"{photo_id}"
                f" | initial={initial_id}"
                f" | {image.name}"
            )

            registered += 1

            next_photo_number += 1
            next_initial_number += 1

        conn.commit()

    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("=" * 80)
    print("INGEST FINISHED")
    print("=" * 80)
    print()

    print(
        "Found      :",
        len(images),
    )

    print(
        "Registered :",
        registered,
    )

    print(
        "Skipped    :",
        skipped,
    )

    print()

    print(
        "New photos are now available to:"
    )

    print(
        "  DINO : dino_status = pending"
    )

    print(
        "  QWEN : qwen_status = pending"
    )

    print()

    print(
        "No address has been assigned yet."
    )

# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Register new photos, "
            "assign photo_id and initial_id, "
            "and put them into independent "
            "DINO/Qwen queues."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help=(
            "Directory with incoming photos"
        ),
    )

    args = parser.parse_args()

    ingest(
        args.input
    )

if __name__ == "__main__":
    main()
```

### Теперь цепочка именно такая

```text
                     НОВЫЙ ФАЙЛ
                         │
                         ▼
                    PHOTO INGEST
                         │
              ┌──────────┴──────────┐
              │                     │
          photo_id              initial_id
        PH_00000123             IN_00000123
              │                     │
              └──────────┬──────────┘
                         │
                   ЕДИНАЯ ЗАПИСЬ
                      photos
                         │
             ┌───────────┴───────────┐
             │                       │
       dino_status              qwen_status
        pending                   pending
             │                       │
             ▼                       ▼
           DINO                     QWEN
             │                       │
             ▼                       ▼
        address_id              description
             │                       │
             └───────────┬───────────┘
                         │
                      photo_id
                         │
                         ▼
                        GRID
```

При этом **`initial_id` не меняется после DINO**.

Например:

```text
photo_id   = PH_00000123
initial_id = IN_00000123

DINO:
address_id = 78_v33

QWEN:
description = "..."

GRID:
PH_00000123
        ├── address_id = 78_v33
        └── Qwen description = ...
```

И самое важное: **адрес больше не является идентификатором фотографии**.

`78_v33` — это результат распознавания DINO, а не ключ фотографии.

Следующим я бы уже переделал **`qwen4b_output_v01.py`**, потому что там сейчас есть одна важная ошибка относительно нашей новой архитектуры: `mark_done()` принимает `photo_id`, но затем делает `WHERE id = %s`. Это сейчас потенциально путает внутренний PostgreSQL `id` и постоянный `photo_id`. Надо привести Qwen к той же строгой схеме, что и DINO.

---

### 👤 **User** — 2026-08-18 23:42:19

далее

---

### 🤖 **Assistant** — 2026-08-18 23:42:20

Да. Теперь **Qwen**. Его задача максимально простая: взять любую фотографию, у которой уже есть `photo_id`, обработать её независимо от DINO и записать результат **строго в эту же строку `photos`**.

Ключевое изменение: Qwen **не смотрит на `address_id`, `dino_status`, `sort_status` или `preview_status`**.

### `scripts/qwen4b_output_v01.py`

У тебя текущий файл уже почти подходит. Главную часть можно оставить, но я бы заменил его целиком на этот вариант:

```python
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import json
import os
import time
from pathlib import Path

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

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

OLLAMA_URL = (
    "http://localhost:11434/api/chat"
)

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
    return psycopg2.connect(
        **DB_CONFIG
    )

def reset_processing(conn):
    """
    Восстановление после прерывания.

    Если Qwen был processing во время:
        - Ctrl+C
        - падения процесса
        - перезагрузки
        - отключения машины

    фотография снова становится pending.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'pending',
                updated_at = CURRENT_TIMESTAMP
            WHERE qwen_status = 'processing'
            """
        )

        count = cur.rowcount

    conn.commit()

    if count:
        print(
            "[QWEN] Reset stale processing:",
            count,
        )

def claim_photo(conn):
    """
    Берёт следующую фотографию Qwen.

    ВАЖНО:

    Qwen не зависит от DINO.

    Условия только:

        qwen_status = pending
        source_path существует в БД
    """

    with conn.cursor(
        cursor_factory=RealDictCursor
    ) as cur:

        cur.execute(
            """
            SELECT
                id,
                photo_id,
                initial_id,
                source_path,
                filename
            FROM photos
            WHERE
                qwen_status = 'pending'
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
            WHERE
                id = %s
                AND qwen_status = 'pending'
            """,
            (
                row["id"],
            ),
        )

        conn.commit()

        return row

# ============================================================
# SAVE RESULT
# ============================================================

def mark_done(
    conn,
    db_id,
    result,
    elapsed,
):
    """
    Записывает результат Qwen в ту же запись photos.

    Связь:
        PostgreSQL id
            ↓
        photo_id
            ↓
        Grid

    Qwen никогда не создаёт новый объект фотографии.
    """

    text_json = result.get(
        "text",
        [],
    )

    colors_json = result.get(
        "colors",
        [],
    )

    objects_json = result.get(
        "objects",
        [],
    )

    environment_json = result.get(
        "environment",
        {},
    )

    image_quality_json = result.get(
        "image_quality",
        {},
    )

    camera_view_json = result.get(
        "camera_view",
        {},
    )

    scene_objects_json = result.get(
        "objects",
        [],
    )

    analysis_quality_json = result.get(
        "analysis_quality",
        {},
    )

    raw_json = dict(
        result
    )

    raw_json.pop(
        "_time_sec",
        None,
    )

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

            WHERE
                id = %s
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

                db_id,
            ),
        )

    conn.commit()

def mark_error(
    conn,
    db_id,
    error,
):
    """
    Ошибка Qwen меняет только qwen_status.
    """

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
                db_id,
            ),
        )

    conn.commit()

# ============================================================
# IMAGE
# ============================================================

def image64(path):
    with open(
        path,
        "rb",
    ) as f:

        return base64.b64encode(
            f.read()
        ).decode()

# ============================================================
# QWEN
# ============================================================

def ask(path):

    max_attempts = 2

    for attempt in range(
        1,
        max_attempts + 1,
    ):

        payload = {
            "model": MODEL,

            "messages": [
                {
                    "role": "user",
                    "content": PROMPT,
                    "images": [
                        image64(path)
                    ],
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

        elapsed = (
            time.time()
            - started
        )

        if response.status_code != 200:

            raise RuntimeError(
                response.text
            )

        data = response.json()

        stats = {
            "total_duration_sec": round(
                data.get(
                    "total_duration",
                    0,
                ) / 1e9,
                2,
            ),

            "load_duration_sec": round(
                data.get(
                    "load_duration",
                    0,
                ) / 1e9,
                2,
            ),

            "prompt_eval_duration_sec": round(
                data.get(
                    "prompt_eval_duration",
                    0,
                ) / 1e9,
                2,
            ),

            "eval_duration_sec": round(
                data.get(
                    "eval_duration",
                    0,
                ) / 1e9,
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

        answer = data[
            "message"
        ][
            "content"
        ]

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

            result = json.loads(
                cleaned
            )

            description = str(
                result.get(
                    "description",
                    "",
                )
                or ""
            ).strip()

            if description:

                result["_time_sec"] = round(
                    elapsed,
                    2,
                )

                return result

            if attempt < max_attempts:

                print(
                    "[QWEN RETRY]"
                    " description empty"
                    " | attempt:",
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
        help=(
            "Process only N pending photos"
        ),
    )

    args = parser.parse_args()

    print("=" * 80)
    print(
        "QWEN3-VL 4B — DATABASE WORKER"
    )
    print("=" * 80)

    print(
        "MODEL:",
        MODEL,
    )

    print(
        "DATABASE:",
        DB_CONFIG["dbname"],
    )

    print()

    conn = get_connection()

    reset_processing(
        conn
    )

    processed = 0
    errors = 0

    try:

        # ----------------------------------------------------
        # QUEUE INFO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # LOOP
        # ----------------------------------------------------

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

            row = claim_photo(
                conn
            )

            if row is None:

                print(
                    "QWEN QUEUE EMPTY"
                )

                break

            db_id = row["id"]

            photo_id = row[
                "photo_id"
            ]

            initial_id = row[
                "initial_id"
            ]

            source_path = row[
                "source_path"
            ]

            print(
                "=" * 80
            )

            print(
                f"[{processed + 1}]",
                photo_id,
            )

            print(
                "INITIAL:",
                initial_id,
            )

            print(
                "SOURCE:",
                source_path,
            )

            started = time.time()

            try:

                path = Path(
                    source_path
                )

                if not path.exists():

                    raise FileNotFoundError(
                        f"Photo not found: {path}"
                    )

                if not path.is_file():

                    raise FileNotFoundError(
                        f"Not a file: {path}"
                    )

                result = ask(
                    path
                )

                elapsed = (
                    time.time()
                    - started
                )

                mark_done(
                    conn,
                    db_id,
                    result,
                    elapsed,
                )

                print(
                    "OK",
                    "| photo_id:",
                    photo_id,
                    "| time:",
                    round(
                        elapsed,
                        2,
                    ),
                    "sec",
                )

                print(
                    "CLIENT:",
                    result.get(
                        "client",
                        "",
                    ),
                )

                print(
                    "BRAND:",
                    result.get(
                        "brand",
                        "",
                    ),
                )

                print(
                    "CONFIDENCE:",
                    result.get(
                        "confidence",
                        "",
                    ),
                )

                print(
                    "DESCRIPTION:",
                    result.get(
                        "description",
                        "",
                    ),
                )

                processed += 1

            except Exception as exc:

                errors += 1

                elapsed = (
                    time.time()
                    - started
                )

                print(
                    "ERROR:",
                    exc,
                    "| time:",
                    round(
                        elapsed,
                        2,
                    ),
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
        print(
            "QWEN WORKER STOPPED"
        )
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
```

### Теперь у нас две полностью независимые очереди

```text
                         photos
                           │
                  ┌────────┴────────┐
                  │                 │
             dino_status        qwen_status
                  │                 │
               pending           pending
                  │                 │
                  ▼                 ▼
                DINO              QWEN
                  │                 │
                  ▼                 ▼
             address_id         description
```

И главное:

```text
photo_id = PH_00000123
```

создан **один раз на входе**.

DINO:

```text
PH_00000123
    ↓
address_id = 78_v33
```

Qwen:

```text
PH_00000123
    ↓
description = "..."
```

Они не знают результатов друг друга.

---

### Важная поправка

Сейчас `error_message` общий для DINO и Qwen:

```text
error_message
```

Это потенциально плохо: если DINO получил ошибку, а потом Qwen успешно обработал фотографию, Qwen её сотрёт.

**Я бы следующим шагом разделил ошибки:**

```text
dino_error
qwen_error
sort_error
preview_error
```

И заодно введём нормальные состояния:

```text
pending
processing
done
error
skipped
```

Тогда механизм **«пропустить / обработать заново / для всех»**, о котором мы договорились, будет реализовываться чисто и без костылей.

---

### 👤 **User** — 2026-08-18 23:44:38

lfktt

---

### 🤖 **Assistant** — 2026-08-18 23:44:41

Да. Следующий слой — **Qwen**. Здесь принцип тот же:

- `photo_id` уже существует до запуска Qwen;
- Qwen вообще **не смотрит на `address_id` / адрес**;
- источник — `source_path`;
- результат привязывается строго к `photo_id`;
- Qwen может работать независимо от DINO;
- `qwen_status` позволяет продолжать после остановки;
- `done` пропускается обычным запуском;
- отдельным режимом позже добавим **«обработать заново / пропустить / для всех»**;
- адрес и появление в Grid остаются исключительно зоной DINO.

### Сейчас делаем `qwen_worker.py`

Я бы **не продолжал использовать `scripts/qwen4b_output_v01.py` как основной worker**. Лучше вынести его в нормальный `app/workers/qwen_worker.py`, аналогично DINO.

Сначала создаём копию:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp scripts/qwen4b_output_v01.py \
   scripts/qwen4b_output_v01.py.bak_pipeline_v02

cp /dev/null app/workers/qwen_worker.py
```

И затем:

```bash
cat > app/workers/qwen_worker.py <<'PY'
from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

# ============================================================
# DATABASE
# ============================================================

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

# ============================================================
# QWEN
# ============================================================

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
    Берём следующую фотографию, которая ещё не обработана Qwen.

    ВАЖНО:
        Qwen работает независимо от DINO.

    Единственная связь:
        photo_id -> результат Qwen

    address_id здесь НЕ используется.
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
              AND qwen_status = 'pending'
            """,
            (row["id"],),
        )

        conn.commit()

        return row

def mark_done(
    conn,
    db_id,
    result,
    elapsed,
):
    """
    Сохраняет результат Qwen.

    db_id — внутренний bigint photos.id.

    photo_id остаётся постоянным идентификатором
    фотографии и не зависит от адреса.
    """

    text_json = result.get("text", [])
    colors_json = result.get("colors", [])
    objects_json = result.get("objects", [])
    environment_json = result.get("environment", {})
    image_quality_json = result.get("image_quality", {})
    camera_view_json = result.get("camera_view", {})
    analysis_quality_json = result.get(
        "analysis_quality",
        {},
    )

    raw_json = dict(result)
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
                    analysis_quality_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    raw_json,
                    ensure_ascii=False,
                ),

                db_id,
            ),
        )

    conn.commit()

def mark_error(
    conn,
    db_id,
    error,
):
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
                db_id,
            ),
        )

    conn.commit()

# ============================================================
# IMAGE
# ============================================================

def image64(path: Path):
    with open(path, "rb") as f:
        return base64.b64encode(
            f.read()
        ).decode()

# ============================================================
# QWEN REQUEST
# ============================================================

def ask(path: Path):

    max_attempts = 2

    for attempt in range(
        1,
        max_attempts + 1,
    ):

        payload = {
            "model": MODEL,

            "messages": [
                {
                    "role": "user",
                    "content": PROMPT,
                    "images": [
                        image64(path)
                    ],
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
            raise RuntimeError(
                response.text
            )

        data = response.json()

        print(
            "[OLLAMA]",
            {
                "total_duration_sec":
                    round(
                        data.get(
                            "total_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "load_duration_sec":
                    round(
                        data.get(
                            "load_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "prompt_eval_duration_sec":
                    round(
                        data.get(
                            "prompt_eval_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "eval_duration_sec":
                    round(
                        data.get(
                            "eval_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "prompt_eval_count":
                    data.get(
                        "prompt_eval_count"
                    ),
                "eval_count":
                    data.get(
                        "eval_count"
                    ),
            },
            flush=True,
        )

        answer = data[
            "message"
        ][
            "content"
        ]

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

            result = json.loads(
                cleaned
            )

            description = str(
                result.get(
                    "description"
                ) or ""
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

    print("=" * 80)
    print("QWEN3-VL 4B — DATABASE WORKER")
    print("=" * 80)
    print("MODEL   :", MODEL)
    print("DATABASE:", DB_CONFIG["dbname"])
    print()
    print(
        "[QWEN] Works independently from DINO."
    )
    print(
        "[QWEN] Source: photos.source_path"
    )
    print(
        "[QWEN] Identity: photos.photo_id"
    )
    print()

    conn = get_connection()

    processed = 0
    errors = 0

    max_items = int(
        os.getenv(
            "QWEN_MAX_ITEMS",
            "0",
        )
    )

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
                max_items > 0
                and processed >= max_items
            ):

                print(
                    "[QWEN] Reached "
                    f"max_items={max_items}."
                )

                break

            row = claim_photo(
                conn
            )

            if row is None:

                print(
                    "[QWEN] Queue empty."
                )

                break

            db_id = row["id"]
            photo_id = row["photo_id"]
            source_path = Path(
                row["source_path"]
            )

            print("=" * 80)
            print(
                f"[QWEN] {photo_id}"
            )
            print(
                "SOURCE:",
                source_path,
            )

            started = time.time()

            try:

                if not source_path.exists():
                    raise FileNotFoundError(
                        f"Photo not found: "
                        f"{source_path}"
                    )

                if not source_path.is_file():
                    raise FileNotFoundError(
                        f"Not a file: "
                        f"{source_path}"
                    )

                result = ask(
                    source_path
                )

                elapsed = (
                    time.time()
                    - started
                )

                mark_done(
                    conn,
                    db_id,
                    result,
                    elapsed,
                )

                print(
                    "[QWEN] DONE",
                    photo_id,
                    "| time:",
                    round(
                        elapsed,
                        2,
                    ),
                    "sec",
                    "| client:",
                    result.get(
                        "client",
                        "",
                    ),
                    "| brand:",
                    result.get(
                        "brand",
                        "",
                    ),
                    "| confidence:",
                    result.get(
                        "confidence",
                        "",
                    ),
                )

                print(
                    "DESCRIPTION:",
                    result.get(
                        "description",
                        "",
                    ),
                )

                processed += 1

            except Exception as exc:

                errors += 1

                elapsed = (
                    time.time()
                    - started
                )

                print(
                    "[QWEN] ERROR",
                    photo_id,
                    ":",
                    exc,
                    "| time:",
                    round(
                        elapsed,
                        2,
                    ),
                )

                try:

                    mark_error(
                        conn,
                        db_id,
                        exc,
                    )

                except Exception as db_error:

                    print(
                        "[QWEN] DB ERROR:",
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

Проверяем синтаксис:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python -m py_compile \
    app/workers/qwen_worker.py

echo $?
```

Должно быть:

```text
0
```

### И важный момент

После этого архитектура уже получается именно такая:

```text
                    НОВЫЙ ФАЙЛ
                         │
                         ▼
                  PHOTO INGEST
                         │
                         ▼
                    photo_id
                 (PH_00000001)
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
            DINO                  QWEN
              │                     │
              │                     └── description
              │                         brand
              │                         client
              │                         ...
              ▼
          address_id
              │
              ▼
             GRID
              │
              └──────────────┐
                             ▼
                         photo_id
                             │
                   подтягиваем Qwen
                         описание
```

То есть **Qwen вообще не должен ждать DINO**.

И наоборот: DINO не должен ждать Qwen.

А `address_id` появляется только в ветке DINO. **До появления `address_id` фотография существует в БД, Qwen уже может её обработать, но Grid её ещё не показывает.**

Следующим файлом логично сделать **`photo_ingest` + общий диспетчер**, который будет создавать `photo_id` и сразу ставить **две независимые очереди DINO/Qwen**, а затем уже перейдём к режимам **ручной / watcher / автоматический** и кнопкам UI.

---

### 👤 **User** — 2026-08-18 23:45:27

да

---

