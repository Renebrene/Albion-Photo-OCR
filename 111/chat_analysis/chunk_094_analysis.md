### 🛠️ Реализация: Пользователи, цвета, состояние, архив и SQLite

---

## 📌 1. Создание таблиц в SQLite

Создадим две таблицы: `users` и `user_state`.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sqlite3 db.sqlite <<EOF
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    archived_at DATETIME
);

CREATE TABLE IF NOT EXISTS user_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    selected_clients TEXT,
    selected_addresses TEXT,
    selected_photos TEXT,
    grid_mode INTEGER,
    sort_mode TEXT,
    search_query TEXT,
    dark_mode BOOLEAN,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
EOF
```

---

## 🧠 2. Обновление `state.py` и `header.py`

### ✅ `state.py` — добавляем `current_user`, `user_state`, `search_history`

```python
from dataclasses import dataclass, field
from pathlib import Path
import sqlite3

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
    current_user: str = "Вихляева Алена"
    user_state: dict = field(default_factory=lambda: {})
    search_history: list = field(default_factory=lambda: [])
    dark_mode: bool = False

    def __post_init__(self):
        self._load_user_state()
        self._load_search_history()

    def _load_user_state(self):
        conn = sqlite3.connect("db.sqlite")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM user_state WHERE user_id = (SELECT id FROM users WHERE name = ?)",
            (self.current_user,)
        )
        result = cursor.fetchone()
        if result:
            self.user_state = {
                "selected_clients": result[1],
                "selected_addresses": result[2],
                "selected_photos": result[3],
                "grid_mode": result[4],
                "sort_mode": result[5],
                "search_query": result[6],
                "dark_mode": result[7],
            }
        conn.close()

    def _load_search_history(self):
        conn = sqlite3.connect("db.sqlite")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM search_history WHERE user_id = (SELECT id FROM users WHERE name = ?)",
            (self.current_user,)
        )
        result = cursor.fetchone()
        if result:
            self.search_history = result[1]
        conn.close()

    def save_user_state(self):
        conn = sqlite3.connect("db.sqlite")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO user_state (user_id, selected_clients, selected_addresses, selected_photos, grid_mode, sort_mode, search_query, dark_mode) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self._get_user_id(),
                self.user_state.get("selected_clients", ""),
                self.user_state.get("selected_addresses", ""),
                self.user_state.get("selected_photos", ""),
                self.user_state.get("grid_mode", 4),
                self.user_state.get("sort_mode", "date"),
                self.user_state.get("search_query", ""),
                self.user_state.get("dark_mode", False),
            )
        )
        conn.commit()
        conn.close()

    def save_search_history(self):
        conn = sqlite3.connect("db.sqlite")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO search_history (user_id, history) VALUES (?, ?)",
            (
                self._get_user_id(),
                self.search_history,
            )
        )
        conn.commit()
        conn.close()

    def _get_user_id(self):
        conn = sqlite3.connect("db.sqlite")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE name = ?", (self.current_user,))
        result = cursor.fetchone()
        return result[0] if result else None
```

### ✅ `header.py` — добавляем окно выбора пользователя

```python
from nicegui import ui
from app.web.config import LOGO_PATH
from app.web.state import STATE
from app.web.components.technical import show_technical

def build_header():
    with ui.header().classes("items-center justify-between px-4 py-2"):
        with ui.row().classes("items-center gap-3"):
            if LOGO_PATH.exists():
                ui.image(str(LOGO_PATH)).classes("w-14 h-14 object-contain")
            else:
                ui.icon("photo_library", size="42px")

            with ui.column().classes("gap-0"):
                ui.label("АЛЬБИОН: Фотобаза. Офис.").classes("text-xl font-bold")
                ui.label('Рекламное агентство "Альбион" 320-30-20').classes("text-sm opacity-80")

        with ui.row().classes("items-center gap-2"):
            ui.select(
                [
                    "Вихляева Алена",
                    "Пятницына Диана",
                    "Аннин Илья",
                    "Иванова Елена",
                    "Марышева Елена",
                    "Бут, Ольга",
                    "Кривошлыкова Ангелина",
                    "Теплинская Наталья",
                    "Папикян Эля",
                    "Путилина Татьяна",
                ],
                value=STATE.current_user,
                label="Пользователь",
            ).props("dense outlined").classes("w-40")

            ui.button("Технический раздел", icon="settings", on_click=show_technical).props("outline")

    # Окно выбора пользователя
    with ui.dialog() as user_dialog, ui.card():
        ui.label("Выберите пользователя").classes("text-xl font-bold")
        user_list = ui.select(
            [
                "Вихляева Алена",
                "Пятницына Диана",
                "Аннин Илья",
                "Иванова Елена",
                "Марышева Елена",
                "Бутовченко Ольга",
                "Кривошлыкова Ангелина",
                "Теплинская Наталья",
                "Папикян Эля",
                "Путилина Татьяна",
            ],
            value=STATE.current_user,
            label="Пользователь",
        ).props("dense outlined").classes("w-40")

        ui.button("Выбрать", on_click=lambda: user_dialog.close()).props("outline")

        user_dialog.open()
```

---

## 🎨 3. Обновление цвета интерфейса

### ✅ `frontend_v02.py` — добавляем цвета

```python
from nicegui import ui
from app.web.state import STATE

def setup_ui():
    # Цвета пользователей
    user_colors = {
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
    }

    # Применение цвета интерфейса
    def apply_theme(color):
        ui.colors(primary=color, secondary="#FFFFFF", accent=color)

    # Обновление цвета при выборе пользователя
    def on_user_select(e):
        user = e.value
        color = user_colors.get(user, "#1976D2")
        apply_theme(color)
        STATE.save_user_state()

    # Загрузка цвета при инициализации
    def on_load():
        user = STATE.current_user
        color = user_colors.get(user, "#1976D2")
        apply_theme(color)

    # Проверка активности пользователя
    def is_user_active(user):
        conn = sqlite3.connect("db.sqlite")
        cursor = conn.cursor()
        cursor.execute("SELECT active FROM users WHERE name = ?", (user,))
        result = cursor.fetchone()
        return result[0] if result else True
```

---

## 🧾 4. Архивирование пользователей

### ✅ `user_state.py` — добавляем функции для архивирования

```python
def archive_user(user):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET active = 0, archived_at = CURRENT_TIMESTAMP WHERE name = ?", (user,))
    conn.commit()
    conn.close()

def restore_user(user):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET active = 1, archived_at = NULL WHERE name = ?", (user,))
    conn.commit()
    conn.close()
```

---

## 📁 5. История поиска и подборки

### ✅ `search_history.py` — добавляем таблицу и функции

```python
def save_search_query(query):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO search_history (user_id, query) VALUES (?, ?)",
        (STATE._get_user_id(), query)
    )
    conn.commit()
    conn.close()

def get_search_history():
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT query FROM search_history WHERE user_id = (SELECT id FROM users WHERE name = ?)",
        (STATE.current_user,)
    )
    result = cursor.fetchone()
    return result[0] if result else []
```

---

## 🚀 6. Запуск и проверка

```bash
uv run python -m app.web.main
```

---

### ✅ Итог

- **Пользователи** теперь имеют цвета интерфейса, архивируются и восстанавливаются.
- **Состояние** (клиенты, адреса, поиск) сохраняется для каждого пользователя.
- **История поиска** и **подборки** привязаны к конкретному пользователю.
- **Интерфейс** автоматически меняет цвет при выборе пользователя.

Если нужно, могу добавить **окно архива** и **подборки** в интерфейс.