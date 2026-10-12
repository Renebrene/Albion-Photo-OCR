### 🧠 Анализ `photo_db.py` и переход к новой архитектуре

---

## 🔍 Что делает `photo_db.py` сейчас

Файл `photo_db.py` содержит две ключевые функции:

### 1. `get_photo_records()`
- Загружает **все записи из таблицы `photos`** в PostgreSQL.
- Возвращает список словарей с полями:
  - `id`, `address`, `filename`, `path`, `source_path`, `original_filename`, `preview_path`, `client`, `brand`, `category`, `description`, `confidence`, `qwen_status`, `qwen_time_sec`, `text_json`, `colors_json`, `objects_json`, `environment_json`, `image_quality_json`, `camera_view_json`, `scene_objects_json`, `analysis_quality_json`, `raw_json`, `imported_at`

### 2. `build_photo_record_index(project_root)`
- Строит **индекс по абсолютным путям** файлов.
- Использует `project_root` для преобразования относительных путей в абсолютные.
- Добавляет **дополнительный индекс** по `address + filename`.

---

## 🔄 Как это работает в текущей системе

### 📁 Физическая структура
```text
data/input/
├── 2026-08/
│   └── 18/
│       ├── Шолохова 127 А (7).JPG
│       ├── Шолохова 127 А (8).JPG
│       └── Шолохова 127 А (9).JPG
├── 2026-09/
│   └── 19/
│       └── ...
└── ...
```

### 📄 База данных
```text
photos
├── id
├── address
├── filename
├── path
├── source_path
├── original_filename
├── preview_path
├── client
├── brand
├── category
├── description
├── confidence
├── qwen_status
├── qwen_time_sec
├── text_json
├── colors_json
├── objects_json
├── environment_json
├── image_quality_json
├── camera_view_json
├── scene_objects_json
├── analysis_quality_json
├── raw_json
└── imported_at
```

### 🔍 `build_photo_record_index()`
- Строит индекс по **абсолютным путям** и `address + filename`.
- Использует `project_root` для преобразования относительных путей.

---

## 🔄 Как это будет работать в новой архитектуре

### 📁 Новая физическая структура
```text
data/input/
└── 2026-08/
    └── 18/
        ├── Шолохова 127 А (7).JPG
        ├── Шолохова 127 А (8).JPG
        └── Шолохова 127 А (9).JPG
```

### 📄 Новая структура БД
```text
photos
├── id
├── source_path
├── filename
├── address_id
├── hybrid_final_id
├── dino_score
├── dino_margin
├── hybrid_score
├── hybrid_margin
├── hybrid_neighbors
├── client
├── brand
├── category
├── description
├── confidence
├── qwen_status
├── qwen_time_sec
├── text_json
├── colors_json
├── objects_json
├── environment_json
├── image_quality_json
├── camera_view_json
├── scene_objects_json
├── analysis_quality_json
├── raw_json
└── imported_at
```

### 🔍 Новая `build_photo_record_index()`
- **Не использует физические пути**.
- **Зависит только от данных в PostgreSQL**.
- Строит индекс по `address_id` и `filename`.

---

## ✅ Что нужно изменить

### 1. Удалить зависимость от `project_root`
- В текущей реализации `build_photo_record_index()` использует `project_root` для преобразования относительных путей в абсолютные.
- В новой архитектуре **не нужно больше этого**.

### 2. Убрать физические пути
- В текущей реализации `build_photo_record_index()` использует `path` и `source_path` из БД.
- В новой архитектуре **не нужно больше этого**.

### 3. Использовать `address_id` вместо `address`
- В текущей реализации `build_photo_record_index()` использует `address` для построения индекса.
- В новой архитектуре **нужно использовать `address_id`**.

### 4. Убрать `filename` из индекса
- В текущей реализации `build_photo_record_index()` использует `filename` для построения индекса.
- В новой архитектуре **можно убрать `filename`** из индекса, так как он уже содержится в `source_path`.

---

## 🧠 Как это будет выглядеть в коде

### 🔧 Обновленная `build_photo_record_index()`

```python
def build_photo_record_index():
    """
    Создаёт индекс PostgreSQL-записей по `address_id` и `filename`.
    """

    records = get_photo_records()

    index = {}

    for record in records:

        address_id = record.get("address_id")
        filename = record.get("filename")

        if not address_id or not filename:
            continue

        # Основной индекс: address_id + filename
        index[f"{address_id}:{filename}"] = record

    return index
```

---

## 📌 Итог

### ✅ Что изменилось
- Убрана зависимость от `project_root`.
- Убраны физические пути.
- Используется `address_id` вместо `address`.
- Убран `filename` из индекса.

### ❌ Что осталось
- `get_photo_records()` остался без изменений.
- `build_photo_record_index()` теперь строит индекс только по `address_id` и `filename`.

---

## 🚀 Следующий шаг

Теперь можно **переписать `build_photo_record_index()`**, чтобы он использовал только данные из PostgreSQL, а не физические пути. Это позволит индексу корректно отражать структуру данных в новой архитектуре.