### 🛠️ Далее: Реализация и интеграция

#### 1. **Обновление `run_daily_hybrid_v12.sh`**
Сейчас это скрипт, который запускает daily-обработку. Теперь его можно адаптировать под новую архитектуру:

```bash
#!/bin/bash

# Путь к каталогу с фотографиями
CATALOG="/path/to/ФОТОАРХИВ"

# Путь к БД
DB="dbname=photos user=postgres password=secret host=localhost"

# Путь к скриптам обработки
DINO_SCRIPT="/path/to/dino_processor.py"
QWEN_SCRIPT="/path/to/qwen_processor.py"

# Путь к логам
LOG="/path/to/logs/$(date +'%Y-%m-%d')_auto_process.log"

# Сканирование каталога и обработка новых файлов
find "$CATALOG" -type f -name "*.jpg" | while read -r file; do
    # Получение уникального идентификатора файла
    PHOTO_ID=$(calculate_photo_id "$file")
    
    # Проверка, существует ли запись в БД
    if ! check_in_db "$PHOTO_ID"; then
        # Добавление в БД
        insert_into_db "$PHOTO_ID" "$file"
        
        # Запуск DINO
        python3 "$DINO_SCRIPT" "$PHOTO_ID" >> "$LOG" 2>&1
        
        # Запуск Qwen
        python3 "$QWEN_SCRIPT" "$PHOTO_ID" >> "$LOG" 2>&1
    fi
done
```

#### 2. **Реализация `calculate_photo_id`**
Функция для вычисления уникального идентификатора файла. Например, можно использовать хэш файла:

```python
import hashlib

def calculate_photo_id(file_path):
    with open(file_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    return file_hash
```

#### 3. **Обновление `check_in_db`**
Функция для проверки наличия файла в БД:

```python
import psycopg2

def check_in_db(photo_id):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("SELECT * FROM photos WHERE photo_id = %s", (photo_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None
```

#### 4. **Обновление `insert_into_db`**
Функция для добавления новой фотографии в БД:

```python
def insert_into_db(photo_id, file_path):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO photos (photo_id, source_path, filename)
        VALUES (%s, %s, %s)
    """, (photo_id, file_path, os.path.basename(file_path)))
    conn.commit()
    cur.close()
    conn.close()
```

#### 5. **Реализация `dino_processor.py`**
Скрипт для обработки DINO:

```python
import psycopg2
import os

def process_dino(photo_id):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("UPDATE photos SET dino_status = 'processing' WHERE photo_id = %s", (photo_id,))
    conn.commit()
    
    # Здесь логика обработки DINO
    # Например, вызов API или модель
    result = {"status": "done", "data": "..."}

    cur.execute("UPDATE photos SET dino_status = %s, dino_result = %s WHERE photo_id = %s", 
                (result["status"], str(result), photo_id))
    conn.commit()
    cur.close()
    conn.close()
```

#### 6. **Реализация `qwen_processor.py`**
Скрипт для обработки Qwen:

```python
import psycopg2
import os

def process_qwen(photo_id):
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("UPDATE photos SET qwen_status = 'processing' WHERE photo_id = %s", (photo_id,))
    conn.commit()
    
    # Здесь логика обработки Qwen
    # Например, вызов API или модель
    result = {"status": "done", "data": "..."}

    cur.execute("UPDATE photos SET qwen_status = %s, qwen_result = %s WHERE photo_id = %s", 
                (result["status"], str(result), photo_id))
    conn.commit()
    cur.close()
    conn.close()
```

#### 7. **Интеграция с Гридом**
Грид должен читать данные из БД. Пример запроса:

```sql
SELECT 
    id, 
    photo_id, 
    source_path, 
    filename, 
    dino_status, 
    qwen_status, 
    client, 
    brand, 
    category, 
    description, 
    confidence, 
    text_json, 
    colors_json, 
    objects_json, 
    environment_json, 
    image_quality_json, 
    camera_view_json, 
    analysis_quality_json, 
    raw_json
FROM 
    photos
WHERE 
    dino_status = 'done' AND qwen_status = 'done'
```

#### 8. **Обработка ошибок**
Добавьте логику для обработки ошибок в каждом модуле. Например, в `process_dino`:

```python
except Exception as e:
    cur.execute("UPDATE photos SET dino_status = 'error', dino_result = %s WHERE photo_id = %s", 
                (str(e), photo_id))
    conn.commit()
    log_error(f"Error processing DINO for {photo_id}: {e}")
```

#### 9. **Реализация `recovery.py`**
Скрипт для восстановления обработки после сбоя:

```python
def recover_processing():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        SELECT photo_id 
        FROM photos 
        WHERE dino_status = 'pending' OR qwen_status = 'pending'
    """)
    pending_photos = cur.fetchall()
    cur.close()
    conn.close()
    
    for photo_id in pending_photos:
        # Запуск обработки
        process_dino(photo_id)
        process_qwen(photo_id)
```

#### 10. **Автоматический режим**
Настройте cron-задачу для запуска `run_daily_hybrid_v12.sh` в определенное время:

```bash
0 6 * * * /path/to/run_daily_hybrid_v12.sh
```

---

### ✅ Итог
Эта архитектура позволяет:
- **Избежать дублирования обработки** фотографий.
- **Обеспечить постоянную синхронизацию** между файловой системой и БД.
- **Упростить масштабирование** и поддержку.
- **Повысить надежность** за счет отслеживания статусов и восстановления после сбоев.

Теперь вы можете перейти к внедрению этой архитектуры, начиная с обновления скриптов и настройки интеграции с PostgreSQL.