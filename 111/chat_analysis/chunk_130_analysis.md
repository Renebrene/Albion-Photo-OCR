### ✅ **DINO Worker (Python)**

```python
import os
import time
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging

# Настройки
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'lora',
    'password': 'your_password',  # Замените на реальный пароль
    'dbname': 'photobase'
}

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def connect_db():
    return psycopg2.connect(**DB_CONFIG)

def get_lock_timeout():
    return 30  # Время ожидания блокировки в секундах

def get_dino_worker():
    """Загрузка модели DINO (ваша логика)"""
    # Замените на реальную загрузку модели
    return "DINOv2_model_instance"

def process_photo(photo_id, source_path):
    """Обработка фотографии с помощью DINO"""
    try:
        # Загрузка модели (если не загружена)
        model = get_dino_worker()
        
        # Имитация обработки (ваша логика)
        time.sleep(2)  # Имитация времени обработки
        
        # Пример результатов
        dino_fingerprint = "FP_00000001"
        dino_score = 0.95
        dino_second_score = 0.88
        dino_margin = 0.07
        dino_time_sec = 2.14
        
        return {
            "dino_fingerprint": dino_fingerprint,
            "dino_score": dino_score,
            "dino_second_score": dino_second
        }
    except Exception as e:
        logger.error(f"Ошибка обработки {photo_id}: {str(e)}")
        return None

def main():
    conn = None
    try:
        conn = connect_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        while True:
            # Получаем 100 записей из очереди
            cur.execute("""
                SELECT *
                FROM photos
                WHERE dino_status = 'pending'
                ORDER BY id
                LIMIT 100
                FOR UPDATE SKIP LOCKED
            """)
            
            rows = cur.fetchall()
            
            if not rows:
                logger.info("Нет заданий в очереди. Ожидание...")
                time.sleep(10)
                continue
                
            for row in rows:
                photo_id = row['photo_id']
                source_path = row['source_path']
                
                logger.info(f"Обработка {photo_id} ({source_path})")
                
                # Имитация проверки файла
                if not os.path.exists(source_path):
                    logger.warning(f"Файл {source_path} отсутствует!")
                    cur.execute("""
                        UPDATE photos
                        SET dino_status = 'error',
                            error_message = 'Файл отсутствует'
                        WHERE photo_id = %s
                    """, (photo_id,))
                    conn.commit()
                    continue
                
                # Обработка
                result = process_photo(photo_id, source_path)
                
                if result:
                    cur.execute("""
                        UPDATE photos
                        SET 
                            dino_status = 'ok',
                            dino_fingerprint = %s,
                            dino_score = %s,
                            dino_second_score = %s,
                            dino_margin = %s,
                            dino_time_sec = %s,
                            updated_at = %s
                        WHERE photo_id = %s
                    """, (
                        result['dino_fingerprint'],
                        result['dino_score'],
                        result['dino_second_score'],
                        result['dino_margin'],
                        result['dino_time_sec'],
                        datetime.now(),
                        photo_id
                    ))
                else:
                    cur.execute("""
                        UPDATE photos
                        SET dino_status = 'error',
                            error_message = 'Неизвестная ошибка'
                        WHERE photo_id = %s
                    """, (photo_id,))
                
                conn.commit()
            
            time.sleep(1)  # Оптимизация производительности
            
    except Exception as e:
        logger.error(f"Ошибка в worker: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
```

---

### 🔍 **Объяснение**

1. **Блокировка записей**:
   - Используется `FOR UPDATE SKIP LOCKED` для предотвращения конфликтов
   - Максимум 100 фотографий обрабатывается за один проход

2. **Обработка ошибок**:
   - Если файл отсутствует → статус `error`
   - Если модель не может обработать → статус `error`

3. **Оптимизация**:
   - Периодический сон (1 секунда) для снижения нагрузки
   - Обработка по 100 фотографий за раз

4. **Результаты**:
   - `dino_fingerprint` - основной результат
   - `dino_score` и `dino_second_score` - оценки
   - `dino_margin` - разница между оценками
   - `dino_time_sec` - время обработки

---

### 🚀 **Дополнительные рекомендации**

1. **Мониторинг**:
   ```sql
   SELECT 
       dino_status, 
       COUNT(*) AS count
   FROM photos
   GROUP BY dino_status;
   ```

2. **Расширение**:
   - Добавьте логирование в отдельную таблицу
   - Реализуйте обработку ошибок с retry-логикой
   - Добавьте очередь для Qwen через `qwen_status`

3. **Производительность**:
   - Рассмотрите использование `pgBouncer` для оптимизации подключения
   - Добавьте индекс на `dino_status` (уже есть)

4. **Модель DINO**:
   - Убедитесь, что модель загружается один раз
   - Добавьте кэширование результатов

---

### 📌 **Важно**

- Замените `your_password` на реальный пароль
- Добавьте обработку исключений для сложных ошибок
- Рассмотрите использование `pg_notify` для асинхронного уведомления
- Добавьте логирование в отдельную таблицу `dino_logs`

Этот worker будет обрабатывать фотографии по мере появления в очереди, не создавая лишних процессов и корректно обновляя статусы в базе.