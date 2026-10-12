### 🛠️ **Решение проблемы: `refresh_photos` не определён**

Ошибка `NameError: name 'refresh_photos' is not defined` возникает потому, что **функция `refresh_photos` не передаётся в `build_clients_panel()`**. В `clients.py` используется `refresh_photos()`, но она не определена в текущей области видимости.

---

### ✅ **Как исправить**

#### 1. **Проверьте `main.py`**  
Убедитесь, что `refresh_photos` передаётся в `build_clients_panel()`.

```python
# app/web/main.py
from nicegui import ui
from app.web.state import STATE
from app.web.components.clients import build_clients_panel
from app.web.components.photos import build_photo_grid

def main():
    # ... (остальной код)

    # Передаём refresh_photos в build_clients_panel
    build_clients_panel(STATE.refresh_photos)

    # ... (остальной код)
```

---

#### 2. **Проверьте `photos.py`**  
Убедитесь, что `refresh_photos` определён и привязан к `STATE`.

```python
# app/web/components/photos.py
def refresh_photos():
    print(
        "[PHOTO REFRESH CALL]",
        "search_query=", repr(STATE.search_query),
        "results=", len(STATE.search_results),
        flush=True,
    )
    photo_grid.refresh()

STATE.refresh_photos = refresh_photos
```

---

#### 3. **Проверьте `clients.py`**  
Убедитесь, что `refresh_photos` используется корректно.

```python
# app/web/components/clients.py
def build_clients_panel(refresh_photos):
    # ... (остальной код)
```

---

### 🧪 **Проверка**

После исправления:

```bash
uv run python -m app.web.main
```

Если всё сделано правильно, ошибок `NameError` больше не будет, и фильтрация клиентов будет работать корректно.