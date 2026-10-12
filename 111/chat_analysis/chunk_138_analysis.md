### ✅ **Анализ текущей структуры `photos`**

Из вывода команды:

```text
Column         |            Type             | Collation | Nullable |              Default               | Storage  | Compression | Stats target | Description 
-----------------------+-----------------------------+-----------+----------+------------------------------------+----------+-------------+--------------+-------------
 id                    | bigint                      |           | not null | nextval('photos_id_seq'::regclass) | plain    |             |              | 
 photo_id              | text                        |           | not null |                                    | extended |             |              | 
 source_path           | text                        |           | not null |                                    | extended |             |              | 
 path                  | text                        |           | not null |                                    | extended |             |              | 
 filename              | text                        |           | not null |                                    | extended |             |              | 
 original_filename     | text                        |           |          |                                    | extended |             |              | 
 address               | text                        |           |          |                                    | extended |             |              | 
 client                | text
```

### 🔧 **Что уже есть:**

- `photo_id` ✅
- `source_path` ✅
- `filename` ✅
- `original_filename` ✅
- `address` (возможно, это `address_id`) ✅
- `client` (может быть частью Qwen-результатов) ✅

### ❌ **Что отсутствует:**

- `dino_status`, `dino_score`, `dino_address_id`, `dino_started_at`, `dino_finished_at`, `dino_error` ❌
- `qwen_status`, `qwen_started_at`, `qwen_finished_at`, `qwen_time_sec`, `qwen_error` ❌
- `qwen_client`, `qwen_brand`, `qwen_category`, `qwen_description`, `qwen_confidence` ❌
- `qwen_text_json`, `qwen_colors_json`, `qwen_objects_json`, `qwen_environment_json`, `qwen_image_quality_json`, `qwen_camera_view_json`, `qwen_analysis_quality_json`, `qwen_raw_json` ❌

---

### 🛠 **Точная миграция `photos` в новую структуру**

Выполни:

```sql
ALTER TABLE photos
ADD COLUMN dino_status TEXT NOT NULL DEFAULT 'pending',
ADD COLUMN dino_score REAL,
ADD COLUMN dino_second_score REAL,
ADD COLUMN dino_margin REAL,
ADD COLUMN dino_confidence REAL,
ADD COLUMN dino_fingerprint_id TEXT,
ADD COLUMN dino_started_at TIMESTAMP,
ADD COLUMN dino_finished_at TIMESTAMP,
ADD COLUMN dino_error TEXT,

ADD COLUMN qwen_status TEXT NOT NULL DEFAULT 'pending',
ADD COLUMN qwen_started_at TIMESTAMP,
ADD COLUMN qwen_finished_at TIMESTAMP,
ADD COLUMN qwen_time_sec REAL,
ADD COLUMN qwen_error TEXT,

ADD COLUMN qwen_client TEXT,
ADD COLUMN qwen_brand TEXT,
ADD COLUMN qwen_category TEXT,
ADD COLUMN qwen_description TEXT,
ADD COLUMN qwen_confidence REAL,

ADD COLUMN qwen_text_json JSONB,
ADD COLUMN qwen_colors_json JSONB,
ADD COLUMN qwen_objects_json JSONB,
ADD COLUMN qwen_environment_json JSONB,
ADD COLUMN qwen_image_quality_json JSONB,
ADD COLUMN qwen_camera_view_json JSONB,
ADD COLUMN qwen_analysis_quality_json JSONB,
ADD COLUMN qwen_raw_json JSONB;
```

---

### 📌 **Обновление `address` → `address_id`**

Если `address` — это `address_id`, обнови:

```sql
ALTER TABLE photos
RENAME COLUMN address TO address_id;
```

---

### 📌 **Индекс для `photo_id` (если не существует)**

```sql
CREATE INDEX idx_photos_photo_id
ON photos(photo_id);
```

---

### 📌 **Индекс для `dino_status` и `qwen_status` (если не существует)**

```sql
CREATE INDEX idx_photos_dino_status
ON photos(dino_status);

CREATE INDEX idx_photos_qwen_status
ON photos(qwen_status);
```

---

### 📌 **Индекс для `address_id` (если не существует)**

```sql
CREATE INDEX idx_photos_address_id
ON photos(address_id);
```

---

### 📌 **Индекс для `client` (если не существует)**

```sql
CREATE INDEX idx_photos_client
ON photos(client);
```

---

### 📌 **Проверка миграции**

```sql
SELECT * FROM photos LIMIT 10;
```

---

### 🚀 **Далее:**

Теперь можно:

1. **Создать `processing_jobs`** (очередь обработки)  
2. **Создать `processing_runs`** (режимы запуска)  
3. **Создать `system_settings`** (настройки режима)  
4. **Создать `processing_events`** (журнал событий)  
5. **Интегрировать UI** с новой архитектурой

---

### 📌 **Следующий шаг:**

Выполни команды выше, и я предоставлю **точную структуру `processing_jobs`**, чтобы не ломать текущий Qwen.