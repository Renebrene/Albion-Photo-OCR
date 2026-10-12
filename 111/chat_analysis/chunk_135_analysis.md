### 🤖 **Assistant** — 2026-08-18 22:59:00

Да, сейчас у нас уже есть **все необходимые данные** в БД. Давай **не трогать DINO и Qwen**, а сосредоточимся на **сортировке и preview**.

---

### 🔍 Шаг 1: Найти код сортировки DINO

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
'sort_status|source_path|dino_fingerprint|hybrid_final_id|output/daily|_v33' \
scripts app \
--include="*.py" | head -250
```

Если выведется что-то вроде:

```text
app/workers/dino_worker.py:35:                photo_id,
app/workers/dino_worker.py:69:    photo_id,
app/workers/dino_worker.py:94:                photo_id,
app/workers/dino_worker.py:103:    photo_id,
app/workers/dino_worker.py:120:                photo_id,
app/workers/dino_worker.py:171:            photo_id = row["id"]
app/workers/dino_worker.py:172:            photo_key = row["photo_id"]
app/workers/dino_worker.py:201:                    photo_id,
app/workers/dino_worker.py:228:                        photo_id,
```

— это значит, что DINO уже работает с `photo_id`, и мы можем **не трогать его логику**.

---

### 🧠 Шаг 2: Реализовать сортировку и preview

Теперь нужно добавить логику:

1. **После DINO**:
   - Получить `dino_fingerprint` → преобразовать в `address`
   - Назначить `path = data/output/daily/<address>_v33/<original_name>`
   - Обновить `sort_status = done`

2. **После сортировки**:
   - Создать `preview_path = data/output/daily/<address>_v33/preview/<original_name>_small.jpg`
   - Обновить `preview_status = done`

3. **Для GRID**:
   - Получить `photo_id`, `path`, `preview_path`, `description`, `client`, `brand` и т.д.
   - Показать preview

---

### 🛠️ Шаг 3: Добавить в БД

В `photos` должна быть:

```sql
ALTER TABLE photos ADD COLUMN IF NOT EXISTS path TEXT;
ALTER TABLE photos ADD COLUMN IF NOT EXISTS preview_path TEXT;
ALTER TABLE photos ADD COLUMN IF NOT EXISTS sort_status TEXT DEFAULT 'pending';
ALTER TABLE photos ADD COLUMN IF NOT EXISTS preview_status TEXT DEFAULT 'pending';
```

---

### 📁 Шаг 4: Директории

Убедись, что есть:

```bash
mkdir -p data/output/daily/{v33,preview}
```

---

### 🧾 Шаг 5: Пример логики

В `dino_worker.py` после обработки:

```python
# После DINO
address = get_address_from_fingerprint(dino_fingerprint)
new_path = f"data/output/daily/{address}_v33/{original_name}"
update_photo_path(conn, photo_id, new_path)
update_sort_status(conn, photo_id, "done")
```

В отдельном worker'е для preview:

```python
# После сортировки
preview_path = f"data/output/daily/{address}_v33/preview/{original_name}_small.jpg"
generate_preview(new_path, preview_path)
update_preview_status(conn, photo_id, "done")
```

---

### 📌 Важно

- `source_path` **не меняется** — это исходный файл в `input`
- `path` — отсортированный оригинал
- `preview_path` — маленькая копия для GRID
- `photo_id` — **постоянный идентификатор**

---

### ✅ Итог

Теперь у нас:

```text
PH_00000001
 ├── source_path  → input/daily/...
 ├── DINO         → done
 ├── Qwen         → done
 ├── sort         → done
 └── preview      → done
```

И GRID будет получать:

```text
photo_id
path
preview_path
description
client
brand
...
```

Таким образом, **все ветви работают с одной и той же фотографией**, а БД — это **центральный реестр**.