### 🧠 **Итоговая архитектура с PostgreSQL и Qwen**

---

## 🔧 **1. База данных (PostgreSQL)**

### 📁 **Таблицы**

#### `photos`
```sql
CREATE TABLE photos (
    photo_id TEXT PRIMARY KEY,
    original_path TEXT NOT NULL,
    original_name TEXT NOT NULL,
    file_size BIGINT,
    file_mtime TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dino_status TEXT,
    dino_address TEXT,
    dino_score NUMERIC(10, 2),
    dino_margin NUMERIC(10, 2),
    dino_confidence NUMERIC(10, 2),
    qwen_status TEXT,
    qwen_description TEXT,
    qwen_client TEXT,
    qwen_brand TEXT,
    qwen_category TEXT,
    qwen_confidence NUMERIC(10, 2),
    preview_status TEXT,
    preview_path TEXT,
    hash TEXT,
    fingerprint TEXT,
    subfingerprint TEXT,
    ocr TEXT,
    banners JSONB,
    technical_params JSONB,
    history JSONB
);
```

#### `previews`
```sql
CREATE TABLE previews (
    preview_id TEXT PRIMARY KEY,
    photo_id TEXT NOT NULL,
    preview_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (photo_id) REFERENCES photos(photo_id)
);
```

#### `dino_results`
```sql
CREATE TABLE dino_results (
    result_id SERIAL PRIMARY KEY,
    photo_id TEXT NOT NULL,
    best_id TEXT,
    score NUMERIC(10, 2),
    confidence NUMERIC(10, 2),
    margin NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (photo_id) REFERENCES photos(photo_id)
);
```

#### `qwen_results`
```sql
CREATE TABLE qwen_results (
    result_id SERIAL PRIMARY KEY,
    photo_id TEXT NOT NULL,
    description TEXT,
    client TEXT,
    brand TEXT,
    category TEXT,
    confidence NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (photo_id) REFERENCES photos(photo_id)
);
```

---

## 🔄 **2. Интеграция с Qwen**

### 📌 **API для Qwen**
Создайте REST API (например, с помощью FastAPI или Flask), чтобы Qwen мог получать данные из PostgreSQL и возвращать результаты:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import psycopg2

app = FastAPI()

class PhotoRequest(BaseModel):
    photo_id: str

class QwenResult(BaseModel):
    description: str
    client: str
    brand: str
    category: str
    confidence: float

@app.post("/process_qwen")
async def process_qwen(request: PhotoRequest):
    conn = psycopg2.connect(
        dbname="your_db",
        user="your_user",
        password="your_password",
        host="your_host",
        port="your_port"
    )
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM photos WHERE photo_id = %s", (request.photo_id,))
    photo = cur.fetchone()
    
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    # Вызов Qwen (ваша модель)
    result = call_qwen_model(photo_id=request.photo_id)
    
    # Сохранение в qwen_results
    cur.execute("""
        INSERT INTO qwen_results (photo_id, description, client, brand, category, confidence)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        request.photo_id,
        result.description,
        result.client,
        result.brand,
        result.category,
        result.confidence
    ))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {"status": "success", "result": result}
```

---

## 📁 **3. Регистрация фотографий**

### 📌 **Формирование photo_id**
Используйте UUID или хронологический идентификатор (например, `20260818_000001`) для уникальности:

```python
import uuid

def generate_photo_id():
    return str(uuid.uuid4())
```

### 📌 **Запись в PostgreSQL**
После получения оригинального файла:

```python
def register_photo(original_path, original_name):
    photo_id = generate_photo_id()
    
    conn = psycopg2.connect(
        dbname="your_db",
        user="your_user",
        password="your_password",
        host="your_host",
        port="your_port"
    )
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO photos (
            photo_id, original_path, original_name
        ) VALUES (%s, %s, %s)
    """, (photo_id, original_path, original_name))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return photo_id
```

---

## 🚀 **4. Параллельная обработка**

### 📌 **Workers для DINO и Qwen**
Используйте `multiprocessing` или `concurrent.futures` для параллельной обработки:

```python
from concurrent.futures import ThreadPoolExecutor

def process_photos(photo_ids):
    with ThreadPoolExecutor(max_workers=6) as executor:
        dino_futures = [executor.submit(process_dino, photo_id) for photo_id in photo_ids]
        qwen_futures = [executor.submit(process_qwen, photo_id) for photo_id in photo_ids]
        
        for future in concurrent.futures.as_completed(dino_futures + qwen_futures):
            result = future.result()
            # Обновление в PostgreSQL
```

---

## 📈 **5. Оптимизация PostgreSQL**

### 📌 **Индексы**
Добавьте индексы для ускорения поиска:

```sql
CREATE INDEX idx_photos_photo_id ON photos(photo_id);
CREATE INDEX idx_photos_original_path ON photos(original_path);
```

### 📌 **Кэширование**
Используйте кэширование для часто запрашиваемых данных (например, через Redis).

---

## 📌 **6. Виртуальная сортировка**

### 📌 **UI-слой**
Создайте интерфейс, который будет отображать фотографии по `photo_id`, используя данные из PostgreSQL:

```python
def get_grouped_photos(group_id):
    conn = psycopg2.connect(
        dbname="your_db",
        user="your_user",
        password="your_password",
        host="your_host",
        port="your_port"
    )
    cur = conn.cursor()
    
    cur.execute("""
        SELECT p.photo_id, p.original_name, d.best_id, q.description
        FROM photos p
        LEFT JOIN dino_results d ON p.photo_id = d.photo_id
        LEFT JOIN qwen_results q ON p.photo_id = q.photo_id
        WHERE p.dino_status = 'COMPLETED' AND p.qwen_status = 'COMPLETED'
    """)
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return results
```

---

## ✅ **Итог**

- **PostgreSQL** используется для хранения всех данных, включая оригинальные файлы, результаты DINO, Qwen и превью.
- **Qwen** интегрирован через REST API, который взаимодействует с PostgreSQL.
- **photo_id** является основным ключом, связывающим все данные.
- **Параллельная обработка** обеспечивает высокую производительность.
- **Виртуальная сортировка** реализуется через UI-слой, который использует данные из PostgreSQL.

Если у тебя есть конкретные скрипты или код, который нужно адаптировать, я могу помочь с их модификацией.