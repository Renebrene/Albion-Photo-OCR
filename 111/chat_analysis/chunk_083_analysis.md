Отлично. Таблица `photos` в PostgreSQL создана. Теперь нужно **перенести данные из SQLite в PostgreSQL**, сохранив все 100 записей, включая `invalid_json`.

### ✅ Шаг 1. Миграция данных из SQLite → PostgreSQL

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sqlite3 data/metadata/photos.db ".dump" | psql -h localhost -U lora -d photobase
```

Это скопирует **все данные**, включая:

- `id`, `filename`, `path`, `client`, `brand`, `category`, `description`
- `confidence`, `qwen_status`, `qwen_time_sec`
- `text_json`, `colors_json`, `objects_json`, `environment_json`, `image_quality_json`, `camera_view_json`, `scene_objects_json`, `raw_json`

### ✅ Шаг 2. Проверяем количество записей

```bash
psql -h localhost -U lora -d photobase -c "SELECT COUNT(*) FROM photos;"
```

Должно вернуть:

```text
 count
-------
 100
```

Если всё нормально — **следующий шаг: настройка русского полнотекстового поиска**.

---

### 🚀 Шаг 3. Русский полнотекстовый поиск (PGTrgm + Russian)

Выполни:

```bash
sudo apt install -y postgresql-contrib-16
```

Затем в `psql`:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS russian;
```

Потом создадим индекс для поиска:

```sql
CREATE INDEX idx_photos_search
    ON photos
    USING gin (
        to_tsvector('russian', description) ||
        to_tsvector('russian', client) ||
        to_tsvector('russian', brand) ||
        to_tsvector('russian', category) ||
        to_tsvector('russian', text_json::text) ||
        to_tsvector('russian', colors_json::text) ||
        to_tsvector('russian', objects_json::text) ||
        to_tsvector('russian', environment_json::text)
    );
```

Теперь запросы вроде:

```sql
SELECT * FROM photos
WHERE to_tsvector('russian', description) @@ to_tsquery('russian', 'красный баннер & гамбургер');
```

будут работать **по смыслу русского текста**.

---

### 📌 Важно

- **SQLite оставляем как резервную копию**.
- **DINO и `data/fingerprints` не трогаем**.
- Поиск через PostgreSQL будет **быстрее и точнее**, чем через `LIKE` в SQLite.

Если всё прошло успешно — можем двигаться к **веб-интерфейсу** или **API**, где заменить SQLite-поиск на PostgreSQL-поиск.