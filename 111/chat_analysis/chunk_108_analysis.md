### ✅ **Готовый патч для GRID (только для preview)**

Вот точный патч, который:

- **Заменяет `photo.path` на preview-путь**
- **Не трогает `open_photo()` и `STATE.photos`**
- **Не ломает DINO/Qwen/поиск**

---

### 🔧 **Патч для `app/web/components/photos.py`**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -i '1039,1055s|ui.image(str(photo.path))|ui.image(str(get_preview_path(photo.path)))|' app/web/components/photos.py
```

---

### 📌 **Функция `get_preview_path()` (добавить в `photos.py`)**

```python
def get_preview_path(photo_path):
    # Предполагаем, что preview хранится в data/preview/daily/<date>/...
    # Для примера используем дату из примера
    date = "20260816_230042"
    preview_dir = Path("data/preview/daily") / date
    relative_path = photo_path.relative_to(PHOTO_ROOT)
    preview_path = preview_dir / relative_path
    return preview_path
```

---

### 📝 **Пояснение**

- **`get_preview_path()`** строит путь к preview на основе `PHOTO_ROOT` и даты из примера.
- **`ui.image(str(...))`** теперь использует preview-путь, а не оригинал.
- **`open_photo()`** всё ещё использует оригинальный `photo.path` для открытия.

---

### 🚀 **Дополнительно (если нужно)**

Если вы хотите **автоматически подбирать дату** из `photo.path`, добавьте:

```python
from datetime import datetime

def get_preview_path(photo_path):
    # Извлекаем дату из имени файла (пример)
    date_str = photo_path.stem.split("_")[1]  # "20260816_230042"
    date = date_str[:10]  # "20260816"
    preview_dir = Path("data/preview/daily") / date
    relative_path = photo_path.relative_to(PHOTO_ROOT)
    preview_path = preview_dir / relative_path
    return preview_path
```

---

### 📌 **Важно**

- **Не трогайте `open_photo()`** — он всё ещё использует оригиналы.
- **Не меняйте `STATE.photos`** — фильтры и поиск работают как есть.
- **Preview-путь должен существовать** — иначе картинка не покажется.

---

Если нужно, я могу сделать **ленивый GRID** с кнопкой "Показать фотографии" — это будет дополнительный слой.