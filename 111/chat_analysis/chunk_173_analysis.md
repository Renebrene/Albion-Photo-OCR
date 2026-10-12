Вот текущий фрагмент `main.py` (строки 1–180):

```python
1  from nicegui import ui
2  from datetime import datetime
3  from app.web.state import STATE
4  from app.web.components import build_header, build_search, build_filters, build_addresses, build_clients, build_photos
5  
6  def index():
7      ui.title("Scene Fingerprint")
8      ui.query("html, body").classes("h-screen w-screen bg-slate-50")
9      ui.query("body").style("margin: 0")
10     ui.query("html").style("scroll-behavior: smooth")
11  
12     with ui.column().classes("w-full h-full flex flex-col"):
13         build_header()
14         build_search()
15         build_filters()
16         build_addresses()
17         build_clients()
18         build_photos()
19  
20     ui.run()
```

---

### ✅ **Что нужно изменить**

1. **Переставить порядок создания компонентов**:
   - `build_photos()` должен вызываться **до** `build_filters()`, `build_addresses()` и `build_clients()`.
   - Это важно, потому что `build_filters()` должен получать `refresh_photos` из `build_photos()`.

2. **Передать `refresh_photos` в `build_filters()`**:
   - `build_filters()` должен получать callback `refresh_photos` из `build_photos()`.

3. **Убедиться, что `build_filters()` вызывает `refresh_photos` при изменении фильтров**.

---

### 🔧 **Исправленный код `main.py`**

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > app/web/main.py <<'PY'
from nicegui import ui
from datetime import datetime
from app.web.state import STATE
from app.web.components import build_header, build_search, build_filters, build_addresses, build_clients, build_photos

def index():
    ui.title("Scene Fingerprint")
    ui.query("html, body").classes("h-screen w-screen bg-slate-50")
    ui.query("body").style("margin: 0")
    ui.query("html").style("scroll-behavior: smooth")

    with ui.column().classes("w-full h-full flex flex-col"):
        build_header()
        build_search()

        # 1. Сначала создаем GRID и получаем refresh_photos
        refresh_photos = build_photos()

        # 2. Затем передаем refresh_photos в build_filters
        build_filters(refresh_photos)

        build_addresses(refresh_photos)
        build_clients(refresh_photos)

    ui.run()
PY

echo "MAIN.PY UPDATED"
uv run python -m py_compile app/web/main.py && \
echo "PY_COMPILE=OK"
```

---

### ✅ **Итог**

Теперь:

1. `build_photos()` создаёт GRID и возвращает `refresh_photos`.
2. `build_filters()` получает `refresh_photos` и вызывает его при изменении фильтров.
3. `build_addresses()` и `build_clients()` тоже получают `refresh_photos` для автоматического обновления.
4. Фильтры **над** адресами/клиентами, как и было.

---

### 🚀 Следующий шаг

Теперь можно **проверить в браузере**, что:
- При изменении даты съёмки/загрузки GRID обновляется.
- Фильтры работают **без кнопки «Применить»**.
- Если EXIF отсутствует, фото **не попадает в выборку** при фильтрации по дате съёмки.

Если всё работает, можно перейти к **оптимизации EXIF-кэша** и **автоматическому обновлению GRID** при изменении фильтров.