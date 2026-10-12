### 🧠 **План действий: Переход на единую папку превью + связь с `photos.id`**

---

### ✅ **1. Создание новой папки превью**
Создадим единую папку для всех превью:

```bash
mkdir -p data/preview/photos
```

---

### ✅ **2. Обновление `create_previews_v01.py`**
Теперь `create_previews_v01.py` будет сохранять превью в `data/preview/photos/`, используя `photos.id` как имя файла.

**Изменения:**
- Получаем `photos.id` из БД.
- Сохраняем превью в `data/preview/photos/<id>.jpg`.

**Пример:**
```python
# scripts/create_previews_v01.py
def create_preview(source: Path, photo_id: str):
    destination = Path("data/preview/photos") / f"{photo_id}.jpg"
    image.thumbnail((250, 180))
    image.save(destination)
```

---

### ✅ **3. Обновление `photo_ingest.py`**
Изменяем логику сохранения превью, чтобы использовать `photos.id`:

```python
# scripts/photo_ingest.py
def process_photo(photo_id, source_path):
    # ... обработка ...
    create_preview(source_path, photo_id)
```

---

### ✅ **4. Обновление `app/web/main.py`**
Изменяем логику получения превью, чтобы использовать `preview_path` из БД:

```python
# app/web/main.py
@app.get("/api/v2/photos/<photo_id>/preview")
def get_preview(photo_id: str):
    photo = db.get_photo(photo_id)
    if photo and photo.preview_path:
        return FileResponse(photo.preview_path)
    return JSONResponse({"error": "Preview not found"}, status_code=404)
```

---

### ✅ **5. Обновление `app/web/components/photos.py`**
Изменяем логику отображения превью в гриде:

```python
# app/web/components/photos.py
def get_preview_path(photo_id: str):
    photo = db.get_photo(photo_id)
    if photo and photo.preview_path:
        return photo.preview_path
    return None
```

---

### ✅ **6. Обновление БД**
Добавляем поле `preview_path` в таблицу `photos` и заполняем его:

```sql
ALTER TABLE photos ADD COLUMN preview_path TEXT;
```

После этого запускаем обновление превью для всех фотографий:

```bash
python scripts/update_previews.py
```

---

### ✅ **7. Проверка и тестирование**
Проверяем, что все превью корректно сохраняются и отображаются:

```bash
curl http://localhost:8000/api/v2/photos/1/preview
```

Если всё работает, можно удалить старую структуру с `fingerprint` и `daily`.

---

### ✅ **8. Удаление старой структуры**
После проверки удаляем старую структуру:

```bash
rm -rf data/preview/daily/*
```

---

### 🧪 **Итог**
Теперь у нас:
- Единая папка `data/preview/photos/` для всех превью.
- Каждая фотография связана с `photos.id` и `preview_path`.
- Система устойчива к изменениям в структуре папок и именах файлов.

Если нужно, могу предоставить готовый патч для `main.py` и `components/photos.py`.