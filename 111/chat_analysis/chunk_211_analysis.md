### ✅ **Решение: Добавление адресов в PHOTO_RECORD_INDEX**

Вот как мы можем интегрировать адреса в `PHOTO_RECORD_INDEX` без изменений в БД и с минимальным вмешательством в код:

---

### 🔧 **Шаг 1: Расширение `build_photo_record_index`**

Измените `app/web/photo_db.py` и добавьте логику поиска адреса по `dino_fingerprint`:

```python
# app/web/photo_db.py

from typing import List, Dict, Any
from app.web.state import STATE
from app.web.config import DB_PATH
import psycopg2
from psycopg2 import sql

def get_photo_records() -> List[Dict[str, Any]]:
    """Получает все фото из БД с адресами, если они есть."""
    conn = psycopg2.connect(dbname=DB_PATH, user="postgres", password="your_password")
    cur = conn.cursor()

    query = """
        SELECT
            p.path,
            p.dino_fingerprint,
            p.client,
            ad.simple_address,
            ad.legal_address,
            ad.id AS address_id
        FROM photos p
        LEFT JOIN address_fingerprints af
            ON p.dino_fingerprint = af.fingerprint_id
        LEFT JOIN address_directory ad
            ON af.address_id = ad.id
        ORDER BY p.path;
    """
    cur.execute(query)
    records = cur.fetchall()

    photo_records = []
    for row in records:
        path, fingerprint, client, simple_address, legal_address, address_id = row
        photo_records.append({
            "path": path,
            "fingerprint": fingerprint,
            "client": client,
            "simple_address": simple_address,
            "legal_address": legal_address,
            "address_id": address_id,
        })

    cur.close()
    conn.close()
    return photo_records
```

---

### 🔧 **Шаг 2: Обновление `build_photo_record_index`**

Измените `app/web/components/photos.py`, чтобы включить адреса:

```python
# app/web/components/photos.py

from app.web.photo_db import build_photo_record_index

def build_photo_record_index(project_root):
    """Построение индекса фото с адресами."""
    PHOTO_RECORD_INDEX.clear()
    records = get_photo_records()  # Новый метод, возвращающий фото с адресами

    for record in records:
        path = record["path"]
        PHOTO_RECORD_INDEX[path] = {
            "path": path,
            "fingerprint": record["fingerprint"],
            "client": record["client"],
            "simple_address": record["simple_address"],
            "legal_address": record["legal_address"],
            "address_id": record["address_id"],
        }
```

---

### 📌 **Что это даёт?**

- **Фото с адресом** будут отображаться в `PHOTO_RECORD_INDEX` с полем `simple_address` и `legal_address`.
- **Фото без адреса** будут иметь `simple_address` и `legal_address` как `None` или пустые строки.
- **Фильтрация и сортировка** по адресу теперь возможны через `PHOTO_RECORD_INDEX`.

---

### 🧪 **Проверка**

1. **Проверьте, что `PHOTO_RECORD_INDEX` теперь содержит адреса:**
   ```python
   print(PHOTO_RECORD_INDEX["path/to/photo.jpg"]["simple_address"])
   ```

2. **Убедитесь, что UI использует эти данные:**
   - В гриде фото отображаются адреса.
   - Фильтрация по адресу работает.

3. **Проверьте, что не пропущены фото:**
   - Убедитесь, что `build_photo_record_index` обрабатывает все `dino_fingerprint` из `photos`.

---

### 🚀 **Дополнительные шаги (если нужно)**

Если вы хотите автоматически заполнять `address_fingerprints` для всех `dino_fingerprint`, это можно сделать через скрипт, но это уже задача на другую итерацию. Сейчас мы просто интегрируем данные, которые уже есть.

---

### 📌 **Вывод**

Теперь адреса будут отображаться в фото-карточках и использоваться в фильтрах, **без изменений в БД и без добавления новых полей в `photos`**. Это минимальное вмешательство, которое решает задачу.