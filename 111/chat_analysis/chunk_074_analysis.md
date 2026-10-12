### 📌 **Итог: Модульный фронтенд с подборками в левой колонке**

Вот итоговая структура интерфейса:

---

### 📁 **Структура интерфейса (UI v01)**

```
┌──────────────────────────────────────────────────────────────┐
│ LOGO  АЛЬБИОН: Фотобаза. Офис       Менеджер   ⚙ Техника     │
├──────────────────────────────────────────────────────────────┤
│ 🔎 Поиск / загрузка фото                                     │
├───────────────┬──────────────────────────────┬───────────────┤
│ КЛИЕНТЫ       │                              │ АДРЕСА        │
│               │                              │               │
│ ☑ Все         │                              │ ☐ 78          │
│ ☐ Ozon        │                              │ ☐ 79          │
│ ☐ Самокат     │                              │ ☐ 80          │
│ ☐ Яндекс      │       ФОТОГРАФИИ             │ ...           │
│ ☐ Сбер        │                              │ ☐ 95          │
│               │                              │               │
│ ПОДБОРКИ      │                              │               │
│               │                              │               │
│ ▾ Мои         │                              │               │
│   ☐ Важное    │                              │               │
│   ☐ Согласов. │                              │               │
│               │                              │               │
│ ▾ Клиентские  │                              │               │
│   ☐ Ozon      │                              │               │
│   ☐ Яндекс    │                              │               │
│               │                              │               │
│ + Создать     │                              │               │
└───────────────┴──────────────────────────────┴───────────────┘
```

---

### 🧩 **Изменения в коде**

#### ✅ **1. Перемещение `collections.py` в левую колонку**

В `main.py` убираем вызов `build_collections()` из нижнего блока и добавляем его в ту же область, где находятся `clients.py` и `addresses.py`.

```python
# app/web/main.py
from nicegui import ui

from app.web.components.header import build_header
from app.web.components.search import build_search
from app.web.components.clients import build_clients_panel
from app.web.components.addresses import build_addresses
from app.web.components.filters import build_filters
from app.web.components.photos import build_photos
from app.web.components.collections import build_collections

@ui.page("/")
def index():

    build_header()
    build_search()
    build_filters()

    with ui.row().classes(
        "w-full items-start gap-3 px-3"
    ):

        build_clients_panel()
        build_collections()  # ← Перемещено в левую колонку
        build_photos()

        build_addresses()

    with ui.column().classes(
        "w-full px-3 pb-4"
    ):
        # Убрано
```

#### ✅ **2. Обновление `collections.py`**

Добавляем разделы "мои" и "клиентские" подборки, а также кнопку "Создать".

```python
# app/web/components/collections.py
from nicegui import ui

def build_collections():

    with ui.card().classes("w-full"):

        with ui.row().classes(
            "items-center justify-between w-full"
        ):
            ui.label(
                "Подборки"
            ).classes("text-lg font-bold")

            ui.button(
                "Создать",
                icon="add",
            ).props("flat")

        ui.separator()

        with ui.column().classes("gap-2"):
            # Мои подборки
            with ui.row().classes("items-center gap-2"):
                ui.label("Мои подборки").classes("font-medium")
                ui.icon("folder_open")

            with ui.column().classes("gap-0"):
                ui.checkbox("Важное")
                ui.checkbox("На согласовании")
                ui.checkbox("Для клиента")

            # Клиентские подборки
            with ui.row().classes("items-center gap-2"):
                ui.label("Клиентские подборки").classes("font-medium")
                ui.icon("folder_open")

            with ui.column().classes("gap-0"):
                ui.checkbox("Ozon — наружка")
                ui.checkbox("Яндекс — Москва")
                ui.checkbox("Сбер — 2026")

        ui.separator().classes("mt-4")

        ui.label(
            "Технический backend будет подключён на следующем этапе."
        ).classes("text-sm text-grey-6")
```

---

### 📌 **Итог**

- Подборки теперь в левой колонке, рядом с клиентами и адресами.
- Структура интерфейса стала более логичной и удобной для работы.
- `collections.py` остался отдельным модулем, но теперь интегрирован в основную логику.

---

### 🚀 **Далее:**

- Добавить поддержку фильтрации по подборкам.
- Реализовать сохранение/загрузку подборок.
- Добавить отображение фотографий в контексте подборок.

Если нужно, могу продолжить с этими шагами.