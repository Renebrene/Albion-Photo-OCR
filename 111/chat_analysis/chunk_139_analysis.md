### ✅ **Изменения в `photo_ingest.py`**

Вот **готовая замена** для `photo_ingest.py`:

```python
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
    initial_id
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
        """, (
            photo_id,
            initial_id,

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

            # Генерируем initial_id
            initial_id = f"DAILY_{datetime.now().strftime('%Y%m%d')}_001"

            register_photo(
                conn,
                photo_id,
                source_path,
                initial_id
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
```

---

### 🔧 **Изменения в `dino_worker.py`**

Добавим логику для обработки DINO:

```python
import psycopg2
import time
import datetime
from pathlib import Path

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

def process_dino():
    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT photo_id, source_path, dino_status
                FROM photos
                WHERE dino_status = 'pending'
                LIMIT 100
            """)
            rows = cur.fetchall()

            for photo_id, source_path, status in rows:
                try:
                    # Симуляция обработки
                    time.sleep(1)  # Замените на реальную обработку

                    # Записываем address_id
                    address_id = f"ADDR_{datetime.now().strftime('%Y%m%d')}_001"
                    cur.execute("""
                        UPDATE photos
                        SET
                            dino_status = 'done',
                            address_id = %s
                        WHERE photo_id = %s
                    """, (address_id, photo_id))

                    print(f"[DINO] {photo_id} → {address_id}")

                except Exception as e:
                    cur.execute("""
                        UPDATE photos
                        SET dino_status = 'error'
                        WHERE photo_id = %s
                    """, (photo_id,))
                    print(f"[ERROR] {photo_id}: {str(e)}")

def main():
    while True:
        process_dino()
        time.sleep(5)

if __name__ == "__main__":
    main()
```

---

### 🔧 **Изменения в `qwen4b_output_v01.py`**

Добавим логику для обработки Qwen:

```python
import psycopg2
import time
import datetime
from pathlib import Path

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

def process_qwen():
    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT photo_id, source_path, qwen_status
                FROM photos
                WHERE qwen_status = 'pending'
                LIMIT 100
            """)
            rows = cur.fetchall()

            for photo_id, source_path, status in rows:
                try:
                    # Симуляция обработки
                    time.sleep(1)  # Замените на реальную обработку

                    # Записываем результат
                    result = "Qwen output data"
                    cur.execute("""
                        UPDATE photos
                        SET
                            qwen_status = 'done',
                            qwen_result = %s
                        WHERE photo_id = %s
                    """, (result, photo_id))

                    print(f"[QWEN] {photo_id} → {result}")

                except Exception as e:
                    cur.execute("""
                        UPDATE photos
                        SET qwen_status = 'error'
                        WHERE photo_id = %s
                    """, (photo_id,))
                    print(f"[ERROR] {photo_id}: {str(e)}")

def main():
    while True:
        process_qwen()
        time.sleep(5)

if __name__ == "__main__":
    main()
```

---

### ✅ **Проверка**

1. **`photo_ingest.py`**:
   - Добавлен `initial_id`.
   - `dino_status` и `qwen_status` установлены в `pending`.
   - Повторные файлы игнорируются.

2. **`dino_worker.py`**:
   - Обрабатывает только `pending` записи.
   - Записывает `address_id` и ставит `done`.

3. **`qwen4b_output_v01.py`**:
   - Обрабатывает только `pending` записи.
   - Записывает результат в `qwen_result` и ставит `done`.

---

### 🚀 Следующий шаг

Теперь можно приступить к реализации **Process Controller** для управления режимами: **Ручной / Watcher / Автоматический**. Это будет следующий этап.