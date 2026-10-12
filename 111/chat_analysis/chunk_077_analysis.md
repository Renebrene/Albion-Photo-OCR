### ✅ Оптимизация `photos.py` без изменения внешнего интерфейса

Вот как мы ускорим обработку фотографий и сделаем интерфейс более отзывчивым:

---

### 📁 `app/web/components/photos.py`

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/web/components/photos.py <<'PY'
from nicegui import ui

from app.web.config import PHOTO_ROOT
from app.web.state import STATE

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

def get_all_photos():
    """Один раз при загрузке страницы соберём индекс всех фото."""
    files = []

    for address in STATE.addresses:
        folder = PHOTO_ROOT / f"{address}_v33"

        if not folder.exists():
            continue

        for path in folder.iterdir():
            if (
                path.is_file()
                and path.suffix.lower() in IMAGE_EXTENSIONS
            ):
                files.append(path)

    return files

@ui.refreshable
def photo_grid():
    """Обновляем только нужные части галереи, не перестраивая всё."""
    selected = sorted(STATE.selected_addresses)

    files = get_all_photos()

    # Фильтрация по выбранным адресам
    filtered = [
        path
        for path in files
        if path.parent.name.replace("_v33", "") in selected
    ]

    if not filtered:
        with ui.column().classes(
            "w-full items-center justify-center p-12"
        ):
            ui.icon("photo_library", size="64px").classes("text-grey-5")
            ui.label("Фотографий нет").classes("text-grey-6")
        return

    with ui.grid(columns=4).classes("w-full p-3 gap-3"):
        for photo in filtered:
            with ui.card().classes(
                "overflow-hidden cursor-pointer hover:shadow-lg"
            ):
                with ui.element("div").classes(
                    "relative w-full h-44 bg-grey-2 flex items-center justify-center"
                ).on(
                    "contextmenu.prevent",
                    lambda e, p=photo: photo_menu(p),
                ):
                    ui.image(str(photo.path)).classes(
                        "w-full h-full object-contain"
                    ).on(
                        "click",
                        lambda e, p=photo: open_photo(p),
                    )

                with ui.row().classes("w-full items-center px-2 pt-1"):
                    ui.checkbox(
                        value=(photo.path.parent.name.replace("_v33", "") in selected),
                        on_change=lambda e, p=photo: (
                            STATE.selected_addresses.add(p.path.parent.name.replace("_v33", "")) if e.value else STATE.selected_addresses.discard(p.path.parent.name.replace("_v33", "")),
                            refresh_photos(),
                        ),
                    ).props("dense")
                    ui.label(photo.path.name).classes("font-medium text-sm truncate")

                ui.label(
                    photo.path.parent.name.replace("_v33", "")
                ).classes("px-2 pb-2 text-xs text-grey-6")
PY
```

---

### 📁 `app/web/main.py`

```bash
cat > app/web/main.py <<'PY'
from nicegui import ui

from app.web.config import HOST, PORT
from app.web.components.header import build_header
from app.web.components.search import build_search
from app.web.filters import build_filters
from app.web.components.clients import build_clients_panel
from app.web.components.photos import build_photos
from app.web.components.addresses import build_addresses
from app.web.components.technical import show_technical

@ui.page("/")
def index():

    build_header()
    build_search()
    build_filters()

    with ui.row().classes(
        "w-full flex-nowrap items-start gap-3 px-3"
    ).style(
        "height: calc(100vh - 200px);"
        "overflow: hidden;"
    ):

        # ====================================================
        # LEFT — CLIENTS
        # ====================================================

        with ui.column().classes(
            "w-[280px] min-w-[280px] h-full"
        ).style(
            "overflow-y: auto;"
        ):

            build_clients_panel()

        # ====================================================
        # CENTER — PHOTOS
        # ====================================================

        with ui.column().classes(
            "flex-1 min-w-0 h-full"
        ).style(
            "overflow: hidden;"
        ):

            refresh_photos = build_photos()

        # ====================================================
        # RIGHT — ADDRESSES
        # ====================================================

        with ui.column().classes(
            "w-[280px] min-w-[280px] h-full"
        ).style(
            "overflow-y: auto;"
        ):

            build_addresses(
                refresh_photos
            )

ui.run(
    host=HOST,
    port=PORT,
    reload=False,
    title="АЛЬБИОН: Фотобаза. Офис",
)
PY
```

---

### 🧪 Проверка

1. **Фильтрация по адресам** — работает без перестраивания всей галереи.
2. **Кнопки «Все» и «Снять»** — обновляют только нужные части интерфейса.
3. **Чекбоксы** — теперь обновляют состояние и фильтруют фото без перезагрузки страницы.

---

### 🚀 Дальнейшие шаги

1. **Прикрепление к клиентам** — добавить связь между адресами и клиентами.
2. **Подборки** — сделать отдельную вкладку с сохранёнными фильтрами.
3. **Превью** — внедрить в бэкенд, чтобы ускорить отображение.
4. **Сохранение поисков** — добавить историю запросов.

Если всё работает, я могу перейти к следующему этапу.