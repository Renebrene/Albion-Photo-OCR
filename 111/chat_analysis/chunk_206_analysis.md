### 🚀 Следующий шаг: Создание справочников и интеграция нормализатора

#### 1. **Создание таблиц справочников**

Сначала создадим таблицы `address_directory` и `client_directory` в PostgreSQL:

```sql
-- address_directory
CREATE TABLE address_directory (
    address_id INTEGER PRIMARY KEY,
    legal_address TEXT NOT NULL,
    simple_address TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER
);

-- client_directory
CREATE TABLE client_directory (
    client_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    simple_name TEXT NOT NULL,
    active BOOLEAN DEFAULT TRUE
);
```

**Пример данных:**

```sql
-- address_directory
INSERT INTO address_directory (address_id, legal_address, simple_address)
VALUES
(85, 'Ростовская область, г. Ростов-на-Дону, ул. Комарова, д. 13', 'Комарова 13'),
(78, 'Московская область, г. Москва, ул. Тверская, д. 15', 'Тверская 15');

-- client_directory
INSERT INTO client_directory (client_id, name, simple_name)
VALUES
(1, 'Яндекс.Маркет', 'Яндекс Маркет'),
(2, 'Сбер', 'Сбер'),
(3, 'Озон', 'Озон');
```

#### 2. **Интеграция нормализатора**

Теперь создадим модуль `client_normalizer.py` в `app/normalization/`, который будет преобразовывать сырое значение `client` в `client_normalized`:

```python
# app/normalization/client_normalizer.py
import re

def normalize_client(raw_client):
    # Пример простой нормализации
    raw_client = raw_client.strip().lower()
    raw_client = re.sub(r'\s+', ' ', raw_client)
    raw_client = re.sub(r'[^a-z0-9\s]', '', raw_client)
    
    # Проверка на наличие в client_directory
    # (в реальности здесь будет логика поиска в БД)
    if raw_client in ['yandex', 'yandex market']:
        return 'Яндекс Маркет'
    elif raw_client in ['sber', 'sberbank']:
        return 'Сбер'
    elif raw_client in ['ozon', 'ozon market']:
        return 'Озон'
    else:
        return raw_client
```

#### 3. **Обновление логики обработки фотографий**

Измените логику обработки фотографий, чтобы включать нормализацию клиента:

```python
# app/processing/photo_processor.py
from app.normalization.client_normalizer import normalize_client

def process_photo(photo_data):
    # Получение данных от Qwen
    client = photo_data.get('client', '')
    
    # Нормализация клиента
    client_normalized = normalize_client(client)
    
    # Сохранение в БД
    photo_data['client_normalized'] = client_normalized
    save_to_database(photo_data)
```

#### 4. **Тестирование и настройка правил**

- **Тестирование:** Проверьте, как нормализатор обрабатывает различные варианты названий клиентов.
- **Настройка правил:** Добавьте более сложные правила для обработки нестандартных названий (например, с использованием fuzzy-поиска или машинного обучения).
- **Мониторинг:** Отслеживайте ошибки нормализации и корректируйте правила в реальном времени.

#### 5. **Интеграция с DINO/Hybrid**

- **Адреса:** Убедитесь, что `address_id` корректно сопоставляется с `address_directory`.
- **Клиенты:** Нормализованные значения `client_normalized` должны быть использованы для поиска в `client_directory`.

#### 6. **Дополнительные улучшения**

- **Алиасы клиентов:** Добавьте таблицу `client_aliases` для хранения альтернативных названий клиентов.
- **Алиасы адресов:** Если потребуется, создайте таблицу `address_aliases` для хранения альтернативных форм адресов.

---

### ✅ Итог

Следуя этим шагам, вы создадите структурированную систему для управления фотографиями, где:
- **DINO/Hybrid** отвечают за распознавание адресов.
- **Qwen** определяет клиентов.
- **Нормализатор** преобразует сырые данные в стандартизированные значения.
- **Справочники** обеспечивают единообразие и удобство поиска.

Эта архитектура позволяет легко масштабировать систему и вносить изменения без риска повредить существующие данные.