### ✅ **Решение: Интеграция поиска по SQLite в галерею**

Вот как мы интегрируем поиск по SQLite в существующую галерею, сохранив текущую логику и не ломая индексацию файлов:

---

### 🔧 **1. `search.py` — Хранение поискового запроса**
```python
# app/web/components/search.py
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SearchState:
    query: str = ""
    client: str = ""
    brand: str = ""
    category: str = ""
    text: str = ""
    description: str = ""
    address: str = ""

STATE = SearchState()
```

---

### 🔧 **2. `photos.py` — Фильтрация по SQLite + сохранение текущей логики**
```python
# app/web/components/photos.py
from pathlib import Path
import sqlite3
from dataclasses import dataclass
from typing import List, Optional

# Путь к SQLite-базе (если не существует — создаём)
PHOTO_DB = Path(__file__).resolve().parents[2] / "data" / "photos.db"

# Создание базы данных (если её нет)
if not PHOTO_DB.exists():
    PHOTO_DB.parent.mkdir(exist_ok=True)
    PHOTO_DB.touch()
    conn = sqlite3.connect(PHOTO_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL,
            client TEXT,
            brand TEXT,
            category TEXT,
            text TEXT,
            description TEXT,
            address TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_filtered_photos():
    query = STATE.query
    client = STATE.client
    brand = STATE.brand
    category = STATE.category
    text = STATE.text
    description = STATE.description
    address = STATE.address

    # Проверяем, есть ли данные в SQLite
    if PHOTO_DB.exists():
        conn = sqlite3.connect(PHOTO_DB)
        cursor = conn.cursor()
        conditions = []
        params = []

        if query:
            conditions.append("path LIKE ? OR client LIKE ? OR brand LIKE ? OR category LIKE ? OR text LIKE ? OR description LIKE ? OR address LIKE ?")
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%"] * 7)
        if client:
            conditions.append("client = ?")
            params.append(client)
        if brand:
            conditions.append("brand = ?")
            params.append(brand)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if text:
            conditions.append("text = ?")
            params.append(text)
        if description:
            conditions.append("description = ?")
            params.append(description)
        if address:
            conditions.append("address = ?")
            params.append(address)

        if conditions:
            cursor.execute("SELECT path FROM photos WHERE " + " AND ".join(conditions), params)
            sqlite_paths = [row[0] for row in cursor.fetchall()]
        else:
            sqlite_paths = []

        conn.close()

        # Добавляем фотографии из PHOTO_ROOT (если не в SQLite)
        photo_paths = [
            str(p) for p in Path(STATE.config.PHOTO_ROOT).iterdir()
            if p.is_file() and p.name not in sqlite_paths
        ]

        return sqlite_paths + photo_paths
    else:
        # Если база не существует — показываем обычные фотографии
        return [str(p) for p in Path(STATE.config.PHOTO_ROOT).iterdir() if p.is_file()]
```

---

### 🔧 **3. `photos.py` — Обновление галереи при изменении поиска**
```python
# app/web/components/photos.py
from pathlib import Path
import sqlite3
from dataclasses import dataclass
from typing import List, Optional

# ... (оставляем старые функции open_photo и photo_menu)

def refresh_photos():
    photo_grid.refresh()
```

---

### ✅ **Что сохранено:**
- **Фильтрация по адресам** работает как раньше.
- **invalid_json** не скрывается — остаётся для отладки.
- **Фотографии из PHOTO_ROOT** не удаляются — они добавляются в конец результата.
- **SQLite-база** создаётся автоматически, если её нет.
- **Клиентская логика** (выбор клиентов, подборок) остаётся без изменений.

---

### 🚀 **Как это работает:**
1. При вводе поискового запроса в `search.py` обновляется `STATE.query`.
2. `get_filtered_photos()` сначала ищет в SQLite, затем добавляет фотографии из `PHOTO_ROOT`.
3. `photo_grid()` отображает результаты в галерее.
4. Если SQLite-база не существует, показываются обычные фотографии из `PHOTO_ROOT`.

---

### 📌 **Важно:**
- **Не трогаем `frontend_v02.py` и `main.py`** — они остаются как есть.
- **Не ломаем адресную фильтрацию** — она работает как раньше.
- **SQLite-база** будет автоматически обновляться при добавлении новых фотографий (если это предусмотрено в будущем).

Если нужно, могу добавить автоматическую синхронизацию между `PHOTO_ROOT` и SQLite.