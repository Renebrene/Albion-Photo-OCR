## СЕССИЯ: вторник

**Создано:** 2026-08-18 18:12:03
**Обновлено:** 2026-08-22 20:16:20
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1)

---

### 👤 **User** — 2026-08-18 20:09:15

alexice@NEURO:~$ cd ~/projects/scene_fingerprint_mvp_v02 && \
for f in \
app/web/main.py \
app/web/state.py \
app/web/components/addresses.py \
app/web/components/clients.py \
app/web/components/collections.py \
app/web/components/filters.py \
app/web/components/photos.py \
app/web/photo_db.py \
app/web/users_db.py \
app/web/config.py
do
    echo
    echo "==================== $f ===================="
    cat "$f"
done

==================== app/web/main.py ====================
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
        # CENTER — PHOTOS
        # Сначала создаём photo grid и получаем настоящий
        # callback refresh_photos.
        # ====================================================

        with ui.column().classes(
            "flex-1 min-w-0 h-full order-2"
        ).style(
            "overflow: hidden;"
        ):

            refresh_photos = build_photos()

        # ====================================================
        # LEFT — CLIENTS
        # ====================================================

        with ui.column().classes(
            "w-[280px] min-w-[280px] h-full order-1"
        ).style(
            "overflow-y: auto;"
        ):

            build_clients_panel(
                refresh_photos
            )

        # ====================================================
        # RIGHT — ADDRESSES
        # ====================================================

        with ui.column().classes(
            "w-[280px] min-w-[280px] h-full order-3"
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

==================== app/web/state.py ====================
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Photo:
    path: Path
    selected: bool = False
    db_record: dict | None = None

@dataclass
class Collection:
    name: str
    kind: str = "Моя"
    client: str = ""

@dataclass
class AppState:
    manager: str = "Вихляева Алена"
    user_id: int | None = None

    manager_colors: dict[str, str] = field(default_factory=lambda: {
        "Вихляева Алена": "#1976D2",
        "Пятницына Диана": "#2E7D32",
        "Аннин Илья": "#7B1FA2",
        "Иванова Елена": "#C62828",
        "Марышева Елена": "#00838F",
        "Бутовченко Ольга": "#6A1B9A",
        "Кривошлыкова Ангелина": "#1565C0",
        "Теплинская Наталья": "#2E7D32",
        "Папикян Эля": "#AD1457",
        "Путилина Татьяна": "#4E342E",
    })

    dark_mode: bool = False

    clients: list[str] = field(default_factory=lambda: [
        "Все клиенты",
        "Единая Россия",
        "Яндекс",
        "Самокат",
        "Сбер",
        "Ozon",
        "Бетсити",
        "Альбион-Тур",
    ])

    addresses: list[str] = field(default_factory=lambda: [
        "78",
        "79",
        "80",
        "81",
        "82",
        "83",
        "84",
        "85",
        "86",
        "87",
        "88",
        "89",
        "90",
        "91",
        "92",
        "93",
        "94",
        "95",
    ])

    collections: list[Collection] = field(default_factory=lambda: [
        Collection("Важное"),
        Collection("На согласование"),
        Collection("Для клиента"),
        Collection("Самокат — август", "Клиентская", "Самокат"),
        Collection("Яндекс — Москва", "Клиентская", "Яндекс"),
    ])

    # None = все клиенты, set() = ничего не выбрано
    selected_clients: set[str] | None = None
    selected_addresses: set[str] = field(default_factory=set)

    # SQLite / поиск
    search_query: str = ""
    search_results: list[dict] = field(default_factory=list)

    photos: list[Photo] = field(default_factory=list)
    selected_photos: set[str] = field(default_factory=set)

    refresh_photos: object = None

STATE = AppState()

==================== app/web/components/addresses.py ====================
from nicegui import ui

from app.web.components.photos import get_latest_daily_root
from app.web.state import STATE

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

def address_folder(address):
    daily_root = get_latest_daily_root()

    if daily_root is None:
        return None

    return daily_root / f"{address}_v33"

def address_photo_count(address):

    folder = address_folder(address)

    if folder is None or not folder.exists():
        return 0

    return sum(
        1
        for path in folder.iterdir()
        if (
            path.is_file()
            and path.suffix.lower()
            in IMAGE_EXTENSIONS
        )
    )

def build_addresses(refresh_photos):

    with ui.card().classes(
        "w-full"
    ):

        ui.label(
            "Адреса"
        ).classes(
            "text-lg font-bold"
        )

        ui.label(
            "Фильтр по адресам"
        ).classes(
            "text-sm text-grey-6"
        )

        with ui.row().classes(
            "w-full gap-1 mt-2"
        ):

            address_checkboxes = {}

            def select_all():

                STATE.selected_addresses = set(
                    STATE.addresses
                )

                for address, checkbox in (
                    address_checkboxes.items()
                ):
                    checkbox.value = True

                refresh_photos()

            def clear_all():

                STATE.selected_addresses.clear()

                for address, checkbox in (
                    address_checkboxes.items()
                ):
                    checkbox.value = False

                refresh_photos()

            ui.button(
                "Все",
                on_click=select_all,
            ).props(
                "flat dense"
            )

            ui.button(
                "Снять",
                on_click=clear_all,
            ).props(
                "flat dense"
            )

        ui.separator().classes(
            "my-2"
        )

        for address in STATE.addresses:

            count = address_photo_count(
                address
            )

            with ui.row().classes(
                "w-full items-center "
                "justify-between"
            ):

                def change_address(
                    e,
                    address=address,
                ):

                    if e.value:
                        STATE.selected_addresses.add(
                            address
                        )
                    else:
                        STATE.selected_addresses.discard(
                            address
                        )

                    print(
                        "[UI] selected:",
                        sorted(
                            STATE.selected_addresses
                        ),
                        flush=True,
                    )

                    refresh_photos()

                checkbox = ui.checkbox(
                    address,
                    value=(
                        address
                        in STATE.selected_addresses
                    ),
                    on_change=change_address,
                ).props(
                    "dense"
                ).classes(
                    "cursor-pointer"
                )

                address_checkboxes[
                    address
                ] = checkbox

                ui.label(
                    str(count)
                ).classes(
                    "text-xs text-grey-6 mr-1"
                )

==================== app/web/components/clients.py ====================
from nicegui import ui

from app.web.state import STATE
from app.web.components.collections import build_collections
from app.web.client_db import get_clients_with_address_counts

def build_clients_panel(refresh_photos):

    # --------------------------------------------------------
    # LOAD CLIENTS
    # --------------------------------------------------------

    try:
        clients = get_clients_with_address_counts()

    except Exception as exc:

        print(
            "[CLIENT DB ERROR]",
            repr(exc),
            flush=True,
        )

        clients = []

    # --------------------------------------------------------
    # CHECKBOX REFERENCES
    # --------------------------------------------------------

    client_checkboxes = {}

    # --------------------------------------------------------
    # CLIENT ACTIONS
    # --------------------------------------------------------

    def select_all_clients():

        STATE.selected_clients = None

        print(
            "[CLIENT SELECT ALL]",
            flush=True,
        )

        for checkbox in client_checkboxes.values():
            checkbox.value = True

        refresh_photos()

    def clear_clients():

        STATE.selected_clients = set()

        print(
            "[CLIENT CLEAR]",
            flush=True,
        )

        for checkbox in client_checkboxes.values():
            checkbox.value = False

        refresh_photos()

    def select_client(e, name):

        all_clients = {
            client
            for client, _ in clients
        }

        # ----------------------------------------------------
        # Был режим "Все"
        # ----------------------------------------------------

        if STATE.selected_clients is None:

            STATE.selected_clients = set(
                all_clients
            )

        # ----------------------------------------------------
        # Реальное состояние checkbox
        # ----------------------------------------------------

        if e.value:
            STATE.selected_clients.add(name)
        else:
            STATE.selected_clients.discard(name)

        # ----------------------------------------------------
        # Если снова выбраны все —
        # возвращаем компактное состояние "Все"
        # ----------------------------------------------------

        if STATE.selected_clients == all_clients:
            STATE.selected_clients = None

        print(
            "[CLIENT SELECT]",
            repr(name),
            "checked=",
            e.value,
            "STATE.selected_clients=",
            repr(STATE.selected_clients),
            flush=True,
        )

        refresh_photos()

    # --------------------------------------------------------
    # PANEL
    # --------------------------------------------------------

    with ui.card().classes(
        "w-full"
    ):

        ui.label(
            "Клиенты"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator()

        # ----------------------------------------------------
        # CONTROLS
        # ----------------------------------------------------

        with ui.row().classes(
            "w-full items-center justify-between "
            "px-1 py-1 gap-1"
        ):

            ui.label(
                "Выбор клиентов"
            ).classes(
                "text-sm font-medium"
            )

            with ui.row().classes(
                "items-center gap-1"
            ):

                ui.button(
                    "Все",
                    icon="done_all",
                    on_click=select_all_clients,
                ).props(
                    "flat dense"
                )

                ui.button(
                    "Снять",
                    icon="remove_done",
                    on_click=clear_clients,
                ).props(
                    "flat dense"
                )

        ui.separator()

        # ----------------------------------------------------
        # CLIENT LIST
        # ----------------------------------------------------

        for name, address_count in clients:

            with ui.row().classes(
                "w-full items-center gap-1 px-1 py-1"
            ):

                checkbox = ui.checkbox(
                    value=(
                        STATE.selected_clients is None
                        or name in STATE.selected_clients
                    ),
                    on_change=lambda e, n=name:
                        select_client(e, n),
                ).props(
                    "dense"
                )

                client_checkboxes[name] = checkbox

                ui.label(
                    name
                ).classes(
                    "cursor-pointer flex-grow"
                ).on(
                    "click",
                    lambda e, cb=checkbox:
                        setattr(cb, "value", not cb.value),
                )

                ui.label(
                    f"({address_count})"
                ).classes(
                    "text-xs text-grey-6"
                )

        build_collections()

==================== app/web/components/collections.py ====================
from nicegui import ui

from app.web.state import STATE

def add_collection():

    with ui.dialog() as dialog, ui.card().classes("w-96"):

        ui.label(
            "Новая подборка"
        ).classes(
            "text-lg font-bold"
        )

        name = ui.input(
            "Название"
        ).props(
            "outlined autofocus"
        ).classes(
            "w-full"
        )

        kind = ui.select(
            ["Моя", "Клиентская"],
            value="Моя",
            label="Тип",
        ).props(
            "outlined"
        ).classes(
            "w-full"
        )

        client = ui.select(
            [
                "Единая Россия",
                "Яндекс",
                "Самокат",
                "Сбер",
                "Ozon",
                "Бетсити",
                "Альбион-Тур",
            ],
            label="Клиент",
        ).props(
            "outlined"
        ).classes(
            "w-full"
        )

        with ui.row().classes("justify-end w-full"):

            ui.button(
                "Отмена",
                on_click=dialog.close,
            ).props("flat")

            def save():
                if not name.value:
                    ui.notify(
                        "Введите название",
                        type="warning",
                    )
                    return

                STATE.collections.append(
                    type(STATE.collections[0])(
                        name.value,
                        kind.value,
                        client.value or "",
                    )
                )

                ui.notify(
                    f"Подборка «{name.value}» создана",
                    type="positive",
                )

                dialog.close()

                # Пока перезагружаем страницу.
                # Позже сделаем обновление компонента без reload.
                ui.navigate.reload()

            ui.button(
                "Создать",
                on_click=save,
            ).props("unelevated")

    dialog.open()

def build_collections():

    ui.separator().classes("my-3")

    with ui.row().classes(
        "w-full items-center justify-between"
    ):

        ui.label(
            "Подборки"
        ).classes(
            "text-lg font-bold"
        )

        ui.button(
            "Добавить подборку",
            icon="add",
            on_click=add_collection,
        ).props(
            "flat dense"
        )

    with ui.expansion(
        "Мои подборки",
        icon="person",
        value=True,
    ).classes("w-full"):

        for collection in STATE.collections:

            if collection.kind == "Моя":

                with ui.row().classes(
                    "w-full items-center"
                ):

                    ui.checkbox().props("dense")

                    ui.label(
                        collection.name
                    ).classes(
                        "truncate"
                    )

    with ui.expansion(
        "Клиентские подборки",
        icon="folder",
        value=True,
    ).classes("w-full"):

        for collection in STATE.collections:

            if collection.kind == "Клиентская":

                with ui.row().classes(
                    "w-full items-center"
                ):

                    ui.checkbox().props("dense")

                    ui.label(
                        collection.name
                    ).classes(
                        "truncate"
                    )

==================== app/web/components/filters.py ====================
from nicegui import ui

def build_filters():

    with ui.row().classes(
        "w-full items-center justify-between px-4 py-2"
    ):

        with ui.row().classes("items-center gap-2"):

            ui.label("Дата:")

            ui.select(
                ["Все", "Сегодня", "Этот месяц", "Период"],
                value="Все",
            ).props("dense outlined")

            ui.button(
                icon="event",
            ).props("flat")

        with ui.row().classes("items-center gap-1"):

            ui.label("Вид:")

            ui.button(
                icon="grid_view",
            ).props("flat")

            ui.button(
                icon="view_list",
            ).props("flat")

            ui.separator().props("vertical")

            ui.label("Размер:")

            ui.button(
                icon="remove",
            ).props("flat")

            ui.button(
                icon="add",
            ).props("flat")

            ui.separator().props("vertical")

            ui.button(
                icon="sort",
            ).props("flat")

==================== app/web/components/photos.py ====================
from pathlib import Path
import json
import sqlite3
import zipfile
import tempfile

from nicegui import ui

from app.web.config import PHOTO_ROOT, DB_PATH, PROJECT_ROOT

# ============================================================
# PHOTO PREVIEWS
# ============================================================

PREVIEW_ROOT = (
    PROJECT_ROOT
    / "data"
    / "preview"
    / "daily"
)

DAILY_ROOT = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "daily"
)

def get_latest_daily_root():
    """Return the newest daily output directory."""
    if not DAILY_ROOT.exists():
        return None

    runs = [
        path
        for path in DAILY_ROOT.iterdir()
        if path.is_dir()
    ]

    if not runs:
        return None

    return max(
        runs,
        key=lambda path: path.name,
    )

def get_latest_preview_root():
    """Return the newest daily preview directory."""
    if not PREVIEW_ROOT.exists():
        return None

    runs = [
        path
        for path in PREVIEW_ROOT.iterdir()
        if path.is_dir()
    ]

    if not runs:
        return None

    return max(
        runs,
        key=lambda path: path.name,
    )

def get_preview_path(photo_path):
    """Map daily output photo to its preview image."""
    preview_root = get_latest_preview_root()
    daily_root = get_latest_daily_root()

    if preview_root is None or daily_root is None:
        return None

    try:
        relative = photo_path.relative_to(daily_root)
    except ValueError:
        return None

    preview_path = preview_root / relative

    if preview_path.exists():
        return preview_path

    return None
from app.web.state import STATE, Photo
from app.web.photo_db import build_photo_record_index

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

# ============================================================
# PHOTO INDEX
# ============================================================

PHOTO_INDEX: dict[str, list[Path]] = {}

PHOTO_RECORD_INDEX: dict[str, dict] = {}

def build_photo_index():

    PHOTO_INDEX.clear()
    PHOTO_RECORD_INDEX.clear()

    try:
        PHOTO_RECORD_INDEX.update(
            build_photo_record_index(PROJECT_ROOT)
        )

        print(
            "[PHOTO RECORD INDEX]",
            "records=",
            len(PHOTO_RECORD_INDEX),
            flush=True,
        )

    except Exception as exc:

        print(
            "[PHOTO RECORD INDEX ERROR]",
            repr(exc),
            flush=True,
        )

    daily_root = get_latest_daily_root()

    if daily_root is None:
        print(
            "[DAILY PHOTO ROOT] not found",
            flush=True,
        )
        return

    print(
        "[DAILY PHOTO ROOT]",
        daily_root,
        flush=True,
    )

    # --------------------------------------------------------
    # ADDRESSES FROM CURRENT DAILY RUN
    # --------------------------------------------------------

    daily_addresses = sorted(
        (
            path.name[:-4]
            for path in daily_root.iterdir()
            if (
                path.is_dir()
                and path.name.endswith("_v33")
                and path.name[:-4].isdigit()
            )
        ),
        key=lambda value: int(value),
    )

    STATE.addresses = daily_addresses

    # Сбрасываем выбранные адреса, которых больше нет
    STATE.selected_addresses.intersection_update(
        STATE.addresses
    )

    print(
        "[DAILY ADDRESSES]",
        STATE.addresses,
        flush=True,
    )

    for address in STATE.addresses:

        folder = daily_root / f"{address}_v33"

        if not folder.exists():
            PHOTO_INDEX[address] = []
            continue

        files = [
            path
            for path in folder.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                in IMAGE_EXTENSIONS
            )
        ]

        files.sort(
            key=lambda p: p.name.lower()
        )

        PHOTO_INDEX[address] = files

def get_all_indexed_photos():

    result = []

    for address in STATE.addresses:
        result.extend(
            PHOTO_INDEX.get(
                address,
                [],
            )
        )

    return result

def get_db_search_photos():

    if not STATE.search_query:
        return []

    result = []

    for record in STATE.search_results:

        db_path = record.get("path")

        if not db_path:
            continue

        path = Path(db_path)

        if not path.is_absolute():
            path = PROJECT_ROOT / path

        if not path.exists():
            path = PROJECT_ROOT / db_path

        if not path.exists():
            continue

        if STATE.selected_addresses:
            db_address = str(
                record.get("address") or ""
            ).replace("_v33", "")

            if db_address not in STATE.selected_addresses:
                continue

        # photo_grid() ожидает именно Path
        result.append(path)

    return result

def get_filtered_photos():

    # ========================================================
    # SEARCH
    # ========================================================

    if STATE.search_query:
        files = get_db_search_photos()

    else:
        selected_addresses = STATE.selected_addresses

        if not selected_addresses:
            files = get_all_indexed_photos()

        else:
            files = []

            for address in STATE.addresses:

                if address not in selected_addresses:
                    continue

                files.extend(
                    PHOTO_INDEX.get(
                        address,
                        [],
                    )
                )

    # ========================================================
    # CLIENT FILTER
    # ========================================================

    selected_clients = STATE.selected_clients

    # None = все клиенты
    if selected_clients is None:
        return files

    # set() = ничего не выбрано
    if not selected_clients:
        return []

    selected_normalized = {
        str(client).strip().casefold()
        for client in selected_clients
    }

    result = []

    for path in files:

        record = PHOTO_RECORD_INDEX.get(
            str(path.resolve())
        )

        if not record:
            continue

        client = str(
            record.get("client") or ""
        ).strip().casefold()

        if client in selected_normalized:
            result.append(path)

    return result

def get_address_count(address):

    return len(
        PHOTO_INDEX.get(
            address,
            [],
        )
    )

# ============================================================
# PHOTO VIEWER
# ============================================================

def open_photo(photo):

    record = photo.db_record or {}

    print(
        "[PHOTO OPEN]",
        "file=", photo.path.name,
        "has_db_record=", bool(photo.db_record),
        "db_id=", record.get("id"),
        "brand=", record.get("brand"),
        "client=", record.get("client"),
        flush=True,
    )

    def value(name, default="—"):
        value = record.get(name)

        if value is None or value == "":
            return default

        return str(value)

    def json_text(name, default="—"):
        value = record.get(name)

        if value is None:
            return default

        if isinstance(value, list):
            return ", ".join(str(x) for x in value)

        if isinstance(value, dict):
            return " · ".join(
                f"{k}: {v}"
                for k, v in value.items()
            )

        return str(value)

    with ui.dialog() as dialog:

        with ui.card().classes(
            "w-[94vw] h-[94vh] "
            "max-w-[1700px] "
            "bg-black p-2 "
            "overflow-hidden"
        ):

            # =================================================
            # LARGE PHOTO
            # =================================================

            with ui.element("div").classes(
                "w-full flex-1 min-h-0 "
                "flex items-center justify-center "
                "overflow-hidden"
            ):

                ui.image(
                    str(photo.path)
                ).classes(
                    "max-w-full max-h-full "
                    "object-contain"
                )

            # =================================================
            # COMPACT INFORMATION PANEL
            # =================================================

            with ui.card().classes(
                "w-full shrink-0 "
                "bg-white text-black "
                "rounded-lg "
                "p-3 gap-1"
            ):

                # -------------------------------------------------
                # HEADER
                # -------------------------------------------------

                with ui.row().classes(
                    "w-full items-center "
                    "justify-between gap-2"
                ):

                    with ui.row().classes(
                        "items-center gap-2 min-w-0"
                    ):

                        ui.label(
                            photo.path.name
                        ).classes(
                            "font-bold text-sm truncate"
                        )

                        ui.badge(
                            value("address")
                        ).props(
                            "outline dense"
                        )

                        if value("qwen_status") != "—":

                            ui.badge(
                                f"Qwen: {value('qwen_status')}"
                            ).props(
                                "outline dense"
                            )

                    ui.button(
                        icon="close",
                        on_click=dialog.close,
                    ).props(
                        "flat round dense"
                    )

                # -------------------------------------------------
                # BASIC INFORMATION
                # -------------------------------------------------

                with ui.row().classes(
                    "w-full items-center "
                    "gap-5 text-xs"
                ):

                    with ui.row().classes("items-center gap-1"):

                        ui.label("Клиент").classes(
                            "text-grey-6"
                        )

                        ui.label(
                            value("client")
                        ).classes(
                            "font-medium"
                        )

                    with ui.row().classes("items-center gap-1"):

                        ui.label("Бренд").classes(
                            "text-grey-6"
                        )

                        ui.label(
                            value("brand")
                        ).classes(
                            "font-medium"
                        )

                    with ui.row().classes("items-center gap-1"):

                        ui.label("Категория").classes(
                            "text-grey-6"
                        )

                        ui.label(
                            value("category")
                        ).classes(
                            "font-medium"
                        )

                # -------------------------------------------------
                # DESCRIPTION
                # -------------------------------------------------

                description = value("description")

                if description != "—":

                    with ui.row().classes(
                        "w-full items-start gap-1 text-xs"
                    ):

                        ui.label("Описание").classes(
                            "text-grey-6 shrink-0"
                        )

                        ui.label(
                            description
                        ).classes(
                            "text-grey-9 "
                            "leading-tight "
                            "line-clamp-2"
                        )

                # -------------------------------------------------
                # RECOGNIZED INFORMATION
                # -------------------------------------------------

                with ui.row().classes(
                    "w-full items-center "
                    "gap-5 text-xs"
                ):

                    ui.label(
                        f"Текст: {json_text('text_json')}"
                    ).classes(
                        "truncate"
                    )

                    ui.label(
                        f"Объекты: {json_text('objects_json')}"
                    ).classes(
                        "truncate"
                    )

                    ui.label(
                        f"Цвета: {json_text('colors_json')}"
                    ).classes(
                        "truncate"
                    )

                # -------------------------------------------------
                # ENVIRONMENT
                # -------------------------------------------------

                environment = json_text(
                    "environment_json"
                )

                if environment != "—":

                    ui.label(
                        f"Окружение: {environment}"
                    ).classes(
                        "w-full text-xs "
                        "text-grey-7 truncate"
                    )

    dialog.open()

def photo_menu(photo):

    with ui.dialog() as dialog:

        with ui.card().classes(
            "min-w-[260px]"
        ):

            with ui.row().classes(
                "w-full items-center "
                "justify-between"
            ):

                ui.label(
                    "Действия с фотографией"
                ).classes(
                    "font-bold"
                )

                ui.button(
                    icon="close",
                    on_click=dialog.close,
                ).props(
                    "flat round dense"
                )

            ui.separator()

            ui.button(
                "Открыть",
                icon="visibility",
                on_click=lambda: (
                    dialog.close(),
                    open_photo(photo),
                ),
            ).props(
                "flat align-left w-full"
            )

            ui.button(
                "Сохранить фото",
                icon="download",
                on_click=lambda: (
                    dialog.close(),
                    ui.notify(
                        "Экспорт будет подключён позже"
                    ),
                ),
            ).props(
                "flat align-left w-full"
            )

            ui.button(
                "Добавить в подборку",
                icon="folder",
                on_click=lambda: (
                    dialog.close(),
                    ui.notify(
                        "Подборки будут подключены позже"
                    ),
                ),
            ).props(
                "flat align-left w-full"
            )

    dialog.open()

# ============================================================
# BUILD PHOTOS
# ============================================================

def build_photos():

    # --------------------------------------------------------
    # Сканируем базу ОДИН РАЗ
    # --------------------------------------------------------

    build_photo_index()

    # ========================================================
    # LAZY GRID
    # ========================================================

    GRID_PAGE_SIZE = 40
    grid_loaded = 0

    total_photos = len(
        get_all_indexed_photos()
    )

    print(
        "[PHOTO INDEX]",
        f"addresses={len(PHOTO_INDEX)}",
        f"photos={total_photos}",
        flush=True,
    )

    with ui.column().classes(
        "w-full h-full min-w-0"
    ):

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        with ui.row().classes(
            "w-full items-center "
            "justify-between px-3 py-2"
        ):

            with ui.column().classes(
                "gap-0"
            ):

                ui.label(
                    "Фотографии"
                ).classes(
                    "text-lg font-bold"
                )

                count_label = ui.label().classes(
                    "text-sm text-grey-6"
                )

            with ui.row().classes(
                "items-center gap-1"
            ):

                ui.button(
                    icon="view_module"
                ).props(
                    "flat round"
                )

                ui.button(
                    icon="view_list"
                ).props(
                    "flat round"
                )

                ui.separator().props(
                    "vertical"
                )

                ui.button(
                    icon="sort"
                ).props(
                    "flat round"
                )

                ui.button(
                    icon="filter_list"
                ).props(
                    "flat round"
                )

        ui.separator()

        # ----------------------------------------------------
        # PHOTO SELECTION
        # ----------------------------------------------------

        def photo_key(photo):
            return str(photo.path.resolve())

photo_checkboxes = {}

def select_all_photos():

            files = get_filtered_photos()

            STATE.selected_photos = {
                str(path.resolve())
                for path in files
            }

            for path_key, checkbox in photo_checkboxes.items():
                checkbox.value = (
                    path_key in STATE.selected_photos
                )

            selected_count_label.text = (
                f"Выбрано: {len(STATE.selected_photos)}"
            )

            print(
                "[PHOTO SELECT ALL]",
                "count=",
                len(STATE.selected_photos),
                flush=True,
            )

def clear_selected_photos():

            STATE.selected_photos.clear()

            for checkbox in photo_checkboxes.values():
                checkbox.value = False

            selected_count_label.text = "Выбрано: 0"

            print(
                "[PHOTO SELECT CLEAR]",
                flush=True,
            )

def download_selected_zip():

            files = [
                Path(path)
                for path in STATE.selected_photos
                if Path(path).is_file()
            ]

            if not files:
                ui.notify(
                    "Нет выбранных фотографий",
                    type="warning",
                )
                return

            temp_dir = Path(tempfile.gettempdir()) / "albion_photo_downloads"
            temp_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            zip_path = (
                temp_dir
                / "albion_selected_photos.zip"
            )

            with zipfile.ZipFile(
                zip_path,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:

                used_names = set()

                for path in files:

                    name = path.name

                    # Защита от одинаковых имён
                    # из разных адресов.
                    if name in used_names:
                        parent = path.parent.name.replace(
                            "_v33",
                            "",
                        )
                        name = f"{parent}_{name}"

                    used_names.add(name)

                    archive.write(
                        path,
                        arcname=name,
                    )

            print(
                "[PHOTO DOWNLOAD ZIP]",
                "files=",
                len(files),
                "zip=",
                str(zip_path),
                flush=True,
            )

            ui.download(
                str(zip_path),
                "albion_selected_photos.zip",
            )

async def download_selected_files():

            files = [
                Path(path)
                for path in STATE.selected_photos
                if Path(path).is_file()
            ]

            if not files:
                ui.notify(
                    "Нет выбранных фотографий",
                    type="warning",
                )
                return

            print(
                "[PHOTO DOWNLOAD FILES]",
                "files=",
                len(files),
                flush=True,
            )

            for path in files:

                ui.download(
                    str(path),
                    path.name,
                )

                # Небольшая пауза между запросами,
                # чтобы браузер успевал их обработать.
                import asyncio
                await asyncio.sleep(0.08)

# ----------------------------------------------------
        # TOOLBAR
        # ----------------------------------------------------

        with ui.row().classes(
            "w-full items-center "
            "px-3 py-2 gap-2"
        ):

            ui.label(
                "Фильтрация по адресам"
            ).classes(
                "text-sm text-grey-7"
            )

selected_count_label = ui.label(
                "Выбрано: 0"
            ).classes(
                "text-sm text-grey-6"
            )

ui.separator().props(
                "vertical"
            )

            ui.button(
                "Выбрать все",
                icon="done_all",
                on_click=select_all_photos,
            ).props(
                "flat dense"
            )

            ui.button(
                "Снять",
                icon="remove_done",
                on_click=clear_selected_photos,
            ).props(
                "flat dense"
            )

            ui.separator().props(
                "vertical"
            )

            ui.button(
                "Скачать выбранные",
                icon="archive",
                on_click=download_selected_zip,
            ).props(
                "flat dense"
            )

            ui.button(
                "Скачать без архива",
                icon="download",
                on_click=download_selected_files,
            ).props(
                "flat dense"
            )

            ui.button(
                "В подборку",
                icon="folder",
            ).props(
                "flat dense"
            )

            ui.button(
                "Сохранить поиск",
                icon="bookmark",
            ).props(
                "flat dense"
            )

        ui.separator()

        # ----------------------------------------------------
        # LAZY GRID
        # ----------------------------------------------------

        grid_requested = False

        with ui.row().classes(
            "w-full items-center px-3 py-2"
        ):

            show_grid_button = ui.button(
                "Показать фотографии",
                icon="photo_library",
            ).props(
                "unelevated"
            )

            grid_status_label = ui.label(
                "Фотографии пока не загружены"
            ).classes(
                "text-sm text-grey-6"
            )

        # ----------------------------------------------------
        # SCROLL AREA
        # ----------------------------------------------------

        with ui.scroll_area().classes(
            "w-full flex-grow"
        ) as photo_scroll_area:

            # Контейнер грида.
            # Никаких @ui.refreshable.
            with ui.column().classes(
                "w-full"
            ) as photo_grid_container:
                pass

            def photo_key(photo):
                return str(photo.path.resolve())

            # ------------------------------------------------
            # BUILD GRID
            # ------------------------------------------------

            def render_photo_grid():

                nonlocal grid_requested
                nonlocal grid_loaded

                if not grid_requested:
                    return

                all_files = get_filtered_photos()

                files = all_files[:grid_loaded]

                print(
                    "[PHOTO GRID EXECUTED]",
                    "loaded=", len(files),
                    "total=", len(all_files),
                    flush=True,
                )

                # ------------------------------------------------
                # CLEAR PREVIOUS GRID
                # ------------------------------------------------

                photo_grid_container.clear()

                record_by_path = PHOTO_RECORD_INDEX

                STATE.photos = []

                for path in files:

                    record = record_by_path.get(
                        str(path.resolve())
                    )

                    # Fallback: daily-фото может иметь другой
                    # корневой путь, чем запись PostgreSQL.
                    if not record:
                        address = path.parent.name
                        filename = path.name

                        record = record_by_path.get(
                            f"__ADDR_FILE__:{address}:{filename}"
                        )

                    STATE.photos.append(
                        Photo(
                            path=path,
                            db_record=record,
                        )
                    )

                print(
                    "[PHOTO RECORD LINK]",
                    "linked=",
                    sum(
                        1
                        for photo in STATE.photos
                        if photo.db_record is not None
                    ),
                    "total=",
                    len(STATE.photos),
                    flush=True,
                )

                count_label.text = (
                    f"{len(files)} "
                    f"фотографий в текущем запуске"
                )

                if not files:

                    with photo_grid_container:

                        with ui.column().classes(
                            "w-full "
                            "items-center "
                            "justify-center "
                            "p-12"
                        ):

                            ui.icon(
                                "photo_library",
                                size="64px",
                            ).classes(
                                "text-grey-5"
                            )

                            ui.label(
                                "Фотографий нет"
                            ).classes(
                                "text-grey-6"
                            )

                    return

                # ------------------------------------------------
                # GRID
                # ------------------------------------------------

                with photo_grid_container:

                    with ui.grid(
                        columns=4
                    ).classes(
                        "w-full p-3 gap-3"
                    ):

                        for photo in STATE.photos:

                            with ui.card().classes(
                                "overflow-hidden "
                                "cursor-pointer "
                                "hover:shadow-lg"
                            ):

                                # ----------------------------
                                # IMAGE
                                # ----------------------------

                                with ui.element(
                                    "div"
                                ).classes(
                                    "relative "
                                    "w-full h-44 "
                                    "bg-grey-2 "
                                    "flex items-center "
                                    "justify-center"
                                ).on(
                                    "contextmenu.prevent",
                                    lambda e, p=photo:
                                        photo_menu(p),
                                ):

                                    # В ГРИДЕ показываем PREVIEW.
                                    # Оригинал открывается только
                                    # после клика.
                                    preview_path = (
                                        get_preview_path(
                                            photo.path
                                        )
                                    )

                                    display_path = (
                                        preview_path
                                        if preview_path
                                        else photo.path
                                    )

                                    ui.image(
                                        str(display_path)
                                    ).classes(
                                        "w-full h-full "
                                        "object-contain"
                                    ).on(
                                        "click",
                                        lambda e, p=photo:
                                            open_photo(p),
                                    )

                                # ----------------------------
                                # NAME
                                # ----------------------------

                                with ui.row().classes(
                                    "w-full "
                                    "items-center "
                                    "px-2 pt-1"
                                ):

                                    checkbox = ui.checkbox(
                                        value=(
                                            photo_key(photo)
                                            in STATE.selected_photos
                                        ),
                                        on_change=lambda e, p=photo:
                                            (
                                                STATE.selected_photos.add(
                                                    photo_key(p)
                                                )
                                                if e.value
                                                else STATE.selected_photos.discard(
                                                    photo_key(p)
                                                ),
                                                setattr(
                                                    selected_count_label,
                                                    "text",
                                                    f"Выбрано: {len(STATE.selected_photos)}",
                                                ),
                                            ),
                                    ).props(
                                        "dense"
                                    )

                                    photo_checkboxes[
                                        photo_key(photo)
                                    ] = checkbox

                                    ui.label(
                                        photo.path.name
                                    ).classes(
                                        "font-medium "
                                        "text-sm truncate"
                                    )

                                # ----------------------------
                                # ADDRESS
                                # ----------------------------

                                ui.label(
                                    photo.path.parent.name.replace(
                                        "_v33",
                                        "",
                                    )
                                ).classes(
                                    "px-2 pb-1 "
                                    "text-xs text-grey-6"
                                )

                                # ----------------------------
                                # QWEN DESCRIPTION
                                # ----------------------------

                                description = (
                                    photo.db_record.get("description")
                                    if photo.db_record
                                    else None
                                )

                                if description:
                                    ui.label(
                                        str(description)
                                    ).classes(
                                        "px-2 pb-2 "
                                        "text-xs text-grey-8 "
                                        "leading-tight "
                                        "line-clamp-2"
                                    )

                    # ----------------------------
                    # LOADING STATUS
                    # ----------------------------

                    if len(files) < len(all_files):

                        ui.label(
                            f"Показано {len(files)} из "
                            f"{len(all_files)}"
                        ).classes(
                            "w-full text-center "
                            "text-sm text-grey-6 p-4"
                        )

                    else:

                        ui.label(
                            f"Показаны все {len(files)} фотографий"
                        ).classes(
                            "w-full text-center "
                            "text-sm text-grey-6 p-4"
                        )

                grid_status_label.text = (
                    f"Показано {len(files)} из "
                    f"{len(all_files)}"
                )

            # ------------------------------------------------
            # LOAD MORE
            # ------------------------------------------------

            def load_more_photos():

                nonlocal grid_loaded

                if not grid_requested:
                    return

                all_files = get_filtered_photos()

                if grid_loaded >= len(all_files):
                    return

                old_loaded = grid_loaded

                grid_loaded = min(
                    grid_loaded + GRID_PAGE_SIZE,
                    len(all_files),
                )

                print(
                    "[PHOTO GRID LOAD MORE]",
                    "from=", old_loaded,
                    "to=", grid_loaded,
                    "total=", len(all_files),
                    flush=True,
                )

                render_photo_grid()

            # ------------------------------------------------
            # FIRST REQUEST
            # ------------------------------------------------

            def request_photo_grid():

                nonlocal grid_requested
                nonlocal grid_loaded

                print(
                    "[PHOTO GRID BUTTON CLICK]",
                    flush=True,
                )

                grid_requested = True

                grid_loaded = min(
                    GRID_PAGE_SIZE,
                    len(get_filtered_photos()),
                )

                grid_status_label.text = (
                    "Фотографии загружаются..."
                )

                render_photo_grid()

                print(
                    "[PHOTO GRID RENDERED]",
                    "loaded=",
                    grid_loaded,
                    flush=True,
                )

            show_grid_button.on_click(
                request_photo_grid,
            )

            # ------------------------------------------------
            # AUTO LOAD ON SCROLL
            # ------------------------------------------------

            def handle_grid_scroll(e):

                if not grid_requested:
                    return

                if e.vertical_percentage >= 0.80:

                    load_more_photos()

            photo_scroll_area.on(
                "scroll",
                handle_grid_scroll,
            )

    # --------------------------------------------------------
    # CALLBACK FOR ADDRESS FILTER
    # --------------------------------------------------------

    def refresh_photos():

        print(
            "[PHOTO REFRESH CALL]",
            "search_query=", repr(STATE.search_query),
            "results=", len(STATE.search_results),
            flush=True,
        )

        # GRID строится только после явного запроса пользователя.
        if not grid_requested:
            print(
                "[PHOTO GRID SKIPPED] "
                "waiting for user request",
                flush=True,
            )
            return

        photo_grid.refresh()

    STATE.refresh_photos = refresh_photos

    return refresh_photos

==================== app/web/photo_db.py ====================
import psycopg2

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

def get_photo_records() -> list[dict]:
    """
    Загружает все записи фотографий из PostgreSQL.
    """

    sql = """
        SELECT
            id,
            address,
            filename,
            path,
            client,
            brand,
            category,
            description,
            confidence,
            qwen_status,
            qwen_time_sec,
            text_json,
            colors_json,
            objects_json,
            environment_json,
            image_quality_json,
            camera_view_json,
            scene_objects_json,
            analysis_quality_json,
            raw_json,
            imported_at
        FROM photos
        ORDER BY id
    """

    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:

            cur.execute(sql)

            columns = [
                desc[0]
                for desc in cur.description
            ]

            rows = cur.fetchall()

    return [
        dict(zip(columns, row))
        for row in rows
    ]

def build_photo_record_index(project_root):
    """
    Создаёт индекс PostgreSQL-записей по абсолютному пути файла.
    """

    records = get_photo_records()

    index = {}

    for record in records:

        path = record.get("path")

        if not path:
            continue

        from pathlib import Path

        db_path = Path(path)

        if not db_path.is_absolute():
            db_path = project_root / db_path

        # Основной индекс: полный абсолютный путь
        index[str(db_path.resolve())] = record

        # Fallback для daily/test_sorted_v2 и других
        # запусков, где один и тот же файл имеет разные
        # корневые каталоги.
        #
        # Ключ: адрес + имя файла
        address = str(record.get("address") or "").strip()
        filename = db_path.name

        if address and filename:
            index[f"__ADDR_FILE__:{address}:{filename}"] = record

    return index

==================== app/web/users_db.py ====================
import sqlite3

from app.web.config import DB_PATH

DEFAULT_USERS = [
    ("Вихляева Алена", "#E53935"),
    ("Пятницына Диана", "#D81B60"),
    ("Аннин Илья", "#8E24AA"),
    ("Иванова Елена", "#5E35B1"),
    ("Марышева Елена", "#3949AB"),
    ("Бутовченко Ольга", "#1E88E5"),
    ("Кривошлыкова Ангелина", "#039BE5"),
    ("Теплинская Наталья", "#00ACC1"),
    ("Папикян Эля", "#00897B"),
    ("Путилина Татьяна", "#43A047"),
]

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_users_db():

    with get_connection() as con:

        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                archived_at TEXT
            )
        """)

        count = con.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        if count == 0:
            con.executemany(
                """
                INSERT INTO users (name, color, active)
                VALUES (?, ?, 1)
                """,
                DEFAULT_USERS,
            )

        con.commit()

def get_users(active_only=True):

    init_users_db()

    with get_connection() as con:

        if active_only:
            rows = con.execute("""
                SELECT id, name, color, active
                FROM users
                WHERE active = 1
                ORDER BY name COLLATE NOCASE
            """).fetchall()
        else:
            rows = con.execute("""
                SELECT id, name, color, active
                FROM users
                ORDER BY active DESC, name COLLATE NOCASE
            """).fetchall()

    return rows

def add_user(name, color):

    name = str(name).strip()

    if not name:
        return False

    init_users_db()

    try:
        with get_connection() as con:
            con.execute(
                """
                INSERT INTO users (name, color, active)
                VALUES (?, ?, 1)
                """,
                (name, color),
            )
            con.commit()

        return True

    except sqlite3.IntegrityError:
        return False

def update_user_name(user_id, name):

    name = str(name).strip()

    if not name:
        return False

    init_users_db()

    try:
        with get_connection() as con:
            con.execute(
                """
                UPDATE users
                SET name = ?
                WHERE id = ?
                """,
                (name, user_id),
            )
            con.commit()

        return True

    except sqlite3.IntegrityError:
        return False

def update_user_color(user_id, color):

    if not color:
        return False

    with get_connection() as con:
        con.execute(
            """
            UPDATE users
            SET color = ?
            WHERE id = ?
            """,
            (color, user_id),
        )
        con.commit()

    return True

def archive_user(user_id):

    with get_connection() as con:
        con.execute(
            """
            UPDATE users
            SET active = 0,
                archived_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (user_id,),
        )
        con.commit()

def restore_user(user_id):

    with get_connection() as con:
        con.execute(
            """
            UPDATE users
            SET active = 1,
                archived_at = NULL
            WHERE id = ?
            """,
            (user_id,),
        )
        con.commit()

==================== app/web/config.py ====================
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ============================================================
# PHOTO DATABASE
# ============================================================

# Результат тестового распознавания v33.
# Исходный data/input/test НЕ трогаем.
PHOTO_ROOT = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "test_sorted_v2"
)

# 0 = без ограничения
PHOTO_LIMIT = 0

# ============================================================
# UI
# ============================================================

LOGO_PATH = (
    PROJECT_ROOT
    / "app"
    / "web"
    / "assets"
    / "logo.png"
)

HOST = "0.0.0.0"
PORT = 8081

# ============================================================
# SQLITE METADATA DATABASE
# ============================================================

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "metadata"
    / "photos.db"
)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:09:16

> **Checking Project Directory Availability**
>
>
> **Checking Project Directory Availability**
>
> 
>
> Worked for a couple of seconds

Да. Теперь код перед глазами, и можно начинать **с реального текущего состояния**, не затрагивая старые `.bak`.

Я бы не пытался сейчас сделать всё одним патчем. У нас уже есть важная база: `STATE.selected_addresses`, `STATE.selected_clients`, PostgreSQL-индекс фото и lazy-grid.

### Первый этап делаем таким

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Период: [ Август 2026 ▼ ]                              Вид / Размер / Сортировка │
├────────────────┬────────────────┬────────────────────────────────────────┤
│    АДРЕСА      │    КЛИЕНТЫ     │                 ФОТО                    │
│                │                │                                        │
│ ☑ 78           │ ☐ Все/клиенты  │                                        │
│ ☑ 79           │ ☐ Яндекс       │          текущий grid                  │
│ ☑ 80           │ ☐ Сбер         │                                        │
│ ☑ 81           │ ☐ Самокат      │                                        │
│ ...            │ ...            │                                        │
│ ↕ прокрутка    │ ↕ прокрутка    │                                        │
│                │                │                                        │
│ [Все] [Снять]  │ [Все] [Снять] │                                        │
│ [Подборка ▼]   │ [Подборка ▼]  │                                        │
└────────────────┴────────────────┴────────────────────────────────────────┘
```

Но есть **один важный момент**, который надо исправить до перестройки.

### Сейчас в `photos.py` есть старый остаток

В `refresh_photos()` вызывается:

```python
photo_grid.refresh()
```

но в показанном коде объекта `photo_grid` уже нет — используется:

```python
photo_grid_container
```

и обычный `render_photo_grid()`.

То есть текущую систему обновления грида лучше сначала привести к нормальному единому callback-механизму. Это как раз позволит сделать требуемое:

> изменился адрес → грид сразу обновился  
> изменился клиент → грид сразу обновился  
> изменился период → грид сразу обновился.

### И ещё важнее — период

Сейчас `PHOTO_INDEX` строится из:

```text
data/output/daily/<последний запуск>/<адрес>_v33/
```

То есть **период пока вообще не является фильтром данных**.

Поэтому не будем просто рисовать красивый `select "Август"` поверх старой логики. Сначала нужно понять, какое поле в PostgreSQL является датой фотографии (`imported_at`, дата файла или другое), и фильтровать **на уровне фото**, а не папки.

---

## Предлагаю начать с правильного фундамента

### Этап 1 — состояние фильтров

Добавим в `AppState`:

```python
selected_period
```

и, например:

```python
period_mode
period_year
period_month
```

Но я бы сделал ещё проще:

```python
selected_period: str | None = None
```

где `None` означает первый запуск → текущий месяц.

После первого выбора сохраняем значение.

### Этап 2 — единый фильтр

Сделаем одну функцию примерно такого уровня:

```python
get_filtered_photos()
```

которая последовательно применяет:

```text
ПЕРИОД
   И
АДРЕСА
   И
КЛИЕНТЫ
   И
ТЕКУЩИЙ ПОИСК
```

При этом внутри выбранного множества:

```text
адрес 78 ИЛИ адрес 82 ИЛИ адрес 91
```

и:

```text
Яндекс ИЛИ Сбер ИЛИ Самокат
```

То есть итоговая логика:

```text
(period)
AND
(address ∈ selected_addresses)
AND
(client ∈ selected_clients)
AND
(search ...)
```

Это очень важно заложить сейчас, потому что потом сюда естественно добавятся:

```text
текстовый поиск
        AND/OR
поиск по изображению
        AND/OR
поиск по видео
```

---

## Этап 3 — UI

После этого перестроим `main.py`:

сейчас:

```text
Клиенты | ФОТО | Адреса
```

сделаем:

```text
Адреса | Клиенты | ФОТО
```

и обе левые панели будут:

```text
fixed width
max-height
overflow-y: auto
```

примерно 10–15 строк на экране.

Сортировку и остальные настройки **уберём из верхнего общего `build_filters()`** и перенесём в панель фотографий, как ты и предложил.

---

## Этап 4 — подборки

Для адресов и клиентов сделаем одинаковую модель:

```text
Все
Снять
────────────
Подборка 1
Подборка 2
Подборка 3
────────────
+ Создать подборку
```

Причём подборка должна сохранять **не фотографии**, а именно набор фильтров:

```text
Подборка «Москва центр»:

addresses = {"78", "82", "91"}
```

или:

```text
Подборка «Яндекс»:

clients = {"Яндекс"}
```

Это намного правильнее для будущего умного поиска.

---

## И только после этого

Добавим переключатель:

```text
Основная панель:

[ Адреса ▼ ]
```

и:

```text
Адреса | Клиенты | Фото
```

либо:

```text
Клиенты | Адреса | Фото
```

То есть **один и тот же механизм фильтрации**, меняется только порядок/роль панелей.

---

### Сейчас следующий конкретный шаг

Нужно посмотреть `client_db.py` и особенно структуру PostgreSQL `photos`, чтобы правильно сделать **фильтр периода** и не гадать, какую дату использовать.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ client_db.py ================" && \
cat app/web/client_db.py && \
echo && \
echo "================ PostgreSQL columns ================" && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c '\d photos' && \
echo && \
echo "================ sample dates ================" && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT id, address, filename, imported_at FROM photos ORDER BY imported_at DESC LIMIT 10;"
```

**После этого уже можно писать первый настоящий патч.** Я предлагаю не трогать пока авторизацию менеджеров и цвета — это отдельный следующий блок. Сначала сделаем правильный механизм `период → адреса → клиенты → фото`, потому что на него потом завяжутся и авторизация, и сохранение настроек конкретного менеджера.

---

### 👤 **User** — 2026-08-18 20:09:38

[Все] [Снять]  │ [Все] [Снять] │                                        │
│ [Подборка ▼]   наверх до списка

---

### 🤖 **Assistant** — 2026-08-18 20:09:38

Да, согласен. **`Все / Снять` и выпадающий список подборок должны находиться сверху, непосредственно перед списком чекбоксов.**

То есть обе панели:

```text
┌──────────────────┐
│ АДРЕСА           │
├──────────────────┤
│ [Все] [Снять]    │
│ [Подборка ▼]     │
├──────────────────┤
│ ☑ 78             │
│ ☑ 79             │
│ ☑ 80             │
│ ☑ 81             │
│ ...              │
│      ↕           │
└──────────────────┘
```

и:

```text
┌──────────────────┐
│ КЛИЕНТЫ          │
├──────────────────┤
│ [Все] [Снять]    │
│ [Подборка ▼]     │
├──────────────────┤
│ ☐ Яндекс         │
│ ☐ Сбер           │
│ ☐ Самокат        │
│ ☐ Ozon           │
│ ...              │
│      ↕           │
└──────────────────┘
```

### Причём я бы зафиксировал порядок именно такой:

1. Заголовок панели
2. **Все / Снять**
3. **Подборка ▼**
4. Разделитель
5. Список чекбоксов
6. Прокрутка списка

И **подборки будут относиться именно к соответствующей панели**:

- в `Адресах` → подборки адресов;
- в `Клиентах` → подборки клиентов.

Создание/удаление подборок тоже потом разместим там же, чтобы управление фильтрами было полностью локальным.

Это фиксируем в дорожной карте.

---

### 👤 **User** — 2026-08-18 20:09:56

прокрутку боковую

---

### 🤖 **Assistant** — 2026-08-18 20:09:57

Да. **Прокрутка должна быть только у списка внутри панели**, а не у всей панели.

То есть:

```text
┌────────────────────┐
│ АДРЕСА             │  ← фиксировано
├────────────────────┤
│ [Все] [Снять]      │  ← фиксировано
│ [Подборка ▼]       │  ← фиксировано
├────────────────────┤
│ ☑ 78               │
│ ☑ 79               │
│ ☑ 80               │
│ ☑ 81               │
│ ☑ 82               │
│ ☑ 83               │
│ ☑ 84               │
│ ☑ 85               │
│ ☑ 86               │
│ ☑ 87               │
│ ☑ 88               │
│       ↕ scrollbar  │  ← прокручивается только это
└────────────────────┘
```

То же самое для **Клиентов**.

Иными словами:

```text
ПАНЕЛЬ
 ├── заголовок              fixed
 ├── Все / Снять            fixed
 ├── Подборка               fixed
 └── СПИСОК                  ← overflow-y: auto
       ├── checkbox
       ├── checkbox
       ├── checkbox
       └── ...
```

При этом **сама страница и фрейм фотографий не должны прыгать при прокрутке бокового списка**.

Это даже лучше для нашей будущей логики: адреса и клиенты остаются постоянно перед глазами, а длинные списки независимо прокручиваются.

---

### 👤 **User** — 2026-08-18 20:10:22

да

---

### 🤖 **Assistant** — 2026-08-18 20:10:23

Да, фиксируем.

### Дорожная карта UI - текущая версия

**1. Верхняя панель**
- Период - по умолчанию текущий месяц.
- Выбранный период запоминается.
- Сортировка, вид, размер и т.п. → **в панель фотографий**.

**2. Основная область**
```text
┌──────────────┬──────────────┬───────────────────────────────┐
│   АДРЕСА     │   КЛИЕНТЫ    │           ФОТО                │
│              │              │                               │
│ [Все] [Снять]│ [Все] [Снять]│ сортировка / вид / размер    │
│ [Подборка ▼] │ [Подборка ▼] │                               │
│──────────────│──────────────│                               │
│ ☑ 78         │ ☑ Яндекс     │                               │
│ ☑ 79         │ ☑ Сбер       │          GRID                 │
│ ☑ 80         │ ☑ Самокат    │                               │
│ ...          │ ...          │                               │
│      ↕       │      ↕       │                               │
└──────────────┴──────────────┴───────────────────────────────┘
```

**3. Боковые списки**
- Фиксированная высота.
- Прокручивается **только список чекбоксов**.
- Заголовок, `Все`, `Снять`, `Подборка` остаются неподвижными.
- Ориентировочно показываем 10-15 элементов одновременно.

**4. Фильтрация**
Все активные фильтры работают по принципу **И**:

```text
ПЕРИОД
  И
АДРЕСА
  И
КЛИЕНТЫ
  И
ПОИСК
```

При этом внутри одного фильтра возможен множественный выбор:

```text
Адреса: 78 ИЛИ 82 ИЛИ 91
Клиенты: Яндекс ИЛИ Сбер
```

Итого:

```text
Период
AND
(78 OR 82 OR 91)
AND
(Яндекс OR Сбер)
```

**5. Связь адресов ↔ клиентов**
Пока фиксируем выбранную нами схему:
- по умолчанию все адреса отмечены;
- показываются все клиенты;
- изменение фильтров обновляет грид;
- позже отдельно проверим варианты автоматической подсветки/выставления чекбоксов связанных адресов и клиентов.

**6. Подборки**
В каждой панели:

```text
[Все] [Снять]
[Подборка ▼]
─────────────
чекбоксы
```

Подборки можно:
- создать;
- выбрать;
- удалить.

Причём подборка адресов хранит набор адресов, а подборка клиентов - набор клиентов.

**7. Позже**
На этот же механизм навешиваем:
- умный текстовый поиск;
- поиск по изображению;
- поиск по видео;
- комбинирование этих критериев.

И отдельно следующим блоком:
- авторизация менеджеров;
- простой пароль из настроек;
- cookie/local persistence, чтобы не вводить пароль каждый раз;
- 32 фиксированных цвета вместо множественного выбора цвета.

**Следующий технический шаг - период и единый механизм фильтрации.** После него уже перестраиваем `main.py`, `addresses.py` и `clients.py` под эту схему.

---

### 👤 **User** — 2026-08-18 20:10:41

приступаем

---

### 🤖 **Assistant** — 2026-08-18 20:10:42

> ****
>
> 
>
> **Used personal_context tool**
>
> 
>
> Worked for 7s

Приступаем. Делаем **первый технический этап — период + единый фильтр**, не трогая пока авторизацию, цвета и подборки.

Сейчас критично выяснить, **какая дата реально есть у фотографий в PostgreSQL**, потому что именно от неё будет зависеть фильтр «месяц / период».

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PHOTOS TABLE ================" && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c '\d photos' && \
echo && \
echo "================ LAST 20 RECORDS ================" && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT id, address, filename, client, imported_at FROM photos ORDER BY imported_at DESC LIMIT 20;"
```

После этого я дам **конкретный первый патч**:

1. добавим период в `STATE`;
2. по умолчанию — текущий месяц;
3. сохраним выбранный период;
4. переделаем `get_filtered_photos()` на:
   ```text
   ПЕРИОД
   AND
   АДРЕСА
   AND
   КЛИЕНТЫ
   ```
5. сделаем так, чтобы изменение любого фильтра сразу обновляло грид;
6. пока сохраним существующую механику lazy-load на 40 фотографий.

**Боковые панели пока не перестраиваем**, чтобы не смешивать две задачи. Сначала правильно закладываем фильтрацию данных, затем физически переставим панели в `main.py` и сделаем отдельную прокрутку списков.

---

### 👤 **User** — 2026-08-18 20:11:05

Table "public.photos"
        Column         |            Type             | Collation | Nullable |      Default      
-----------------------+-----------------------------+-----------+----------+-------------------
 id                    | integer                     |           | not null | 
 address               | text                        |           |          | 
 filename              | text                        |           | not null | 
 path                  | text                        |           | not null | 
 client                | text                        |           |          | 
 brand                 | text                        |           |          | 
 category              | text                        |           |          | 
 description           | text                        |           |          | 
 confidence            | integer                     |           |          | 
 qwen_status           | text                        |           |          | 
 qwen_time_sec         | double precision            |           |          | 
 text_json             | jsonb                       |           |          | 
 colors_json           | jsonb                       |           |          | 
 objects_json          | jsonb                       |           |          | 
 environment_json      | jsonb                       |           |          | 
 image_quality_json    | jsonb                       |           |          | 
 camera_view_json      | jsonb                       |           |          | 
 scene_objects_json    | jsonb                       |           |          | 
:

---

### 🤖 **Assistant** — 2026-08-18 20:11:07

Отлично. Уже видно важное: в таблице есть `address`, `client`, `path`, `filename`, но вывод обрезался на `scene_objects_json`, поэтому **мы пока не видим, есть ли поле даты**.

И здесь лучше не гадать: период должен фильтровать реальные даты фотографий.

Выполни только эту команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT column_name, data_type
 FROM information_schema.columns
 WHERE table_name = 'photos'
 ORDER BY ordinal_position;"
```

Она покажет полный список колонок.

### Почему это важно

Нам нужно определить источник:

```text
дата фотографии
     ↓
фильтр периода
     ↓
адреса
     ↓
клиенты
     ↓
грид
```

Если в БД есть `imported_at`, это **не обязательно дата фотографии** — это дата загрузки записи в базу. Если реальной даты фото там нет, посмотрим на имя файла/структуру `daily` и выберем правильный источник.

После этого уже начнём менять код. **Пока ничего в файлах не меняем.**

---

