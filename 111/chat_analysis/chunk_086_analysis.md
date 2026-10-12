### 🛠️ **Решение проблемы: Связь `Photo.path ↔ photos.path`**

---

## 🔍 **Причина проблемы**

1. **Два разных хранилища данных**:
   - **PostgreSQL `photobase`** — содержит данные от Qwen (например, `Комарова13_01.JPG`).
   - **SQLite `data/metadata/photos.db`** — используется для UI, но не содержит данных от Qwen.

2. **Неправильная индексация**:
   - В `photos.py` используется SQLite, но PostgreSQL не индексируется корректно.
   - `PHOTO_RECORD_LINK linked=0` — это означает, что пути в `photos.py` не сопоставляются с записями в `photobase`.

---

## ✅ **Что нужно сделать**

### 1. **Убедимся, что PostgreSQL содержит данные**

Выполни:

```bash
uv run python - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="photobase",
    user="lora",
)

cur = conn.cursor()

cur.execute("""
    SELECT
        id,
        filename,
        address,
        client,
        brand,
        category,
        description,
        qwen_status
    FROM photos
    WHERE filename IN (
        'Комарова13_01',
        'Комарова13_02',
        'Комарова13_03',
        'Комарова13_04'
    )
    ORDER BY id
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
PY
```

Если выводит 4 строки — данные в PostgreSQL есть.

---

### 2. **Проверим пути в `config.py`**

```python
# config.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PHOTO_ROOT = PROJECT_ROOT / "data" / "output" / "test_sorted_v2"
```

Убедись, что `PHOTO_ROOT` указывает на директорию с фотографиями (например, `data/output/test_sorted_v2`).

---

### 3. **Исправим связь `Photo.path ↔ photos.path`**

#### ✅ **Изменения в `photos.py`**

1. **Используем PostgreSQL для индексации**:
   - Убедись, что `build_photo_db_index()` вызывается **до** `build_photo_index()`.

2. **Исправим логику сопоставления путей**:
   - Путь в `Photo.path` должен быть **абсолютным** и совпадать с `photos.path`.

#### 📄 **Изменённый код `photos.py`**

```python
# app/web/components/photos.py

import json
import sqlite3
import psycopg2
from pathlib import Path
from nicegui import ui

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PHOTO_DB_INDEX: dict[str, dict] = {}

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

def build_photo_db_index():
    PHOTO_DB_INDEX.clear()

    sql = """
        SELECT
            id,
            address,
            filename,
            path,
            client,
            brand,
            category,
            description,
            qwen_status,
            qwen_time_sec,
            text_json,
            colors_json,
            objects_json,
            environment_json,
            image_quality_json,
            camera_view_json,
            scene_objects_json,
            analysis_quality_json,
            raw_json,
            imported_at
        FROM photos
    """

    try:
        with psycopg2.connect(**PG_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

        for row in rows:
            record = dict(zip(columns, row))
            db_path = record.get("path")
            if not db_path:
                continue
            path = Path(db_path)
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            key = str(path.resolve())
            PHOTO_DB_INDEX[key] = record

        print(
            "[PHOTO DB INDEX]",
            "records=", len(PHOTO_DB_INDEX),
            flush=True,
        )

    except Exception as exc:
        print(
            "[PHOTO DB INDEX ERROR]",
            repr(exc),
            flush=True,
        )

def get_photo_db_record(path: Path):
    return PHOTO_DB_INDEX.get(str(path.resolve()))

def build_photo_index():
    # ... (оставляем как есть)
```

---

### 4. **Проверим связь в `photos.py`**

```python
# app/web/components/photos.py

# ... (оставляем как есть)

def build_photos():
    build_photo_index()
    build_photo_db_index()  # ← вызываем сначала PostgreSQL

    total_photos = len(
        # ... (оставляем как есть)
    )
```

---

## 📌 **Итог**

После этих изменений:

- При открытии `Комарова13_01.JPG` будет:
  ```
  [PHOTO OPEN] file= Комарова13_01.JPG has_db_record= True db_id= 1 ...
  ```
- Панель под фото будет отображать данные из PostgreSQL.
- Поиск `магнит` продолжит работать без изменений.

---

### ✅ **Дополнительно**

Если всё работает, можно добавить **компактную панель под фото**:

```python
# app/web/components/photos.py

class Photo:
    def __init__(self, path: Path, db_record: dict | None = None):
        self.path = path
        self.db_record = db_record
        self.panel = ui.html(
            f"""
            <div style="position: absolute; bottom: 0; width: 100%; background: rgba(255, 255, 255, 0.9); padding: 10px; border-top: 1px solid #ccc;">
                <strong>Магнит</strong><br>
                <span style="color: #555;">Реклама</span><br>
                <span style="color: #777;">78_v33</span>
            </div>
            """,
            style="position: absolute; bottom: 0; width: 100%; background: rgba(255, 255, 255, 0.9); padding: 10px; border-top: 1px solid #ccc;"
        )
```

---

### 🚀 **Итоговая цель**

- **Большое фото** + **компактная панель под фото**.
- **Поиск `магнит`** работает как раньше.
- **Связь `Photo.path ↔ photos.path`** исправлена через PostgreSQL.

Если всё работает — можно двигаться к следующему этапу.