## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 🤖 **Assistant** — 2026-08-18 23:49:29

Да, файл полный и правильный. Делаем следующий слой — **контроллер состояния БД**. Пока он **не запускает DINO/Qwen**, а только надёжно управляет режимом и состоянием процесса. Это важно, чтобы не смешивать UI, БД и worker'ы.

Создай `app/pipeline/controller.py`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/pipeline/controller.py <<'PY'
from __future__ import annotations

import os
from datetime import datetime, time
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from app.pipeline.modes import (
    MODE_AUTOMATIC,
    MODE_MANUAL,
    MODE_WATCHER,
    PipelineMode,
    build_automatic_mode,
    build_manual_mode,
    build_watcher_mode,
    validate_mode,
)

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_row(conn):
    """
    Гарантирует существование единственной строки
    pipeline_control.
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_control (id)
            VALUES (1)
            ON CONFLICT (id) DO NOTHING
            """
        )

    conn.commit()

# ============================================================
# READ STATE
# ============================================================

def get_state() -> PipelineMode:
    """
    Читает текущее состояние pipeline из PostgreSQL.
    """

    with get_connection() as conn:

        ensure_row(conn)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT
                    mode,
                    auto_enabled,
                    auto_time,
                    watcher_enabled,
                    watcher_path,
                    running,
                    stop_requested
                FROM pipeline_control
                WHERE id = 1
                """
            )

            row = cur.fetchone()

    if row is None:
        return build_manual_mode()

    mode = validate_mode(
        row["mode"]
    )

    return PipelineMode(
        mode=mode,

        auto_enabled=bool(
            row["auto_enabled"]
        ),

        auto_time=row["auto_time"],

        watcher_enabled=bool(
            row["watcher_enabled"]
        ),

        watcher_path=row["watcher_path"],

        running=bool(
            row["running"]
        ),

        stop_requested=bool(
            row["stop_requested"]
        ),
    )

# ============================================================
# INTERNAL SAVE
# ============================================================

def _save_state(
    state: PipelineMode,
):
    """
    Полностью записывает состояние.

    Здесь же обеспечивается главное правило:

        manual
        automatic
        watcher

    никогда не смешиваются.
    """

    validate_mode(
        state.mode
    )

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    mode = %s,

                    auto_enabled = %s,
                    auto_time = %s,

                    watcher_enabled = %s,
                    watcher_path = %s,

                    running = %s,
                    stop_requested = %s,

                    updated_at = CURRENT_TIMESTAMP

                WHERE id = 1
                """,
                (
                    state.mode,

                    state.auto_enabled,
                    state.auto_time,

                    state.watcher_enabled,
                    state.watcher_path,

                    state.running,
                    state.stop_requested,
                ),
            )

        conn.commit()

# ============================================================
# MODE SELECTION
# ============================================================

def set_manual():
    """
    Переключает систему в ручной режим.

    После переключения процесс НЕ запускается.
    """

    state = build_manual_mode()

    _save_state(state)

    return state

def set_automatic(
    auto_time: time,
):
    """
    Включает автоматический режим.

    Кнопка ручного запуска после этого
    должна быть disabled.
    """

    state = build_automatic_mode(
        auto_time
    )

    _save_state(state)

    return state

def set_watcher(
    watcher_path: str,
):
    """
    Включает watcher.

    Автоматическое расписание отключается.
    Ручной запуск отключается.
    """

    state = build_watcher_mode(
        watcher_path
    )

    _save_state(state)

    return state

# ============================================================
# START
# ============================================================

def start_manual():
    """
    Запуск разрешён ТОЛЬКО в manual.

    В automatic/watcher запуск через UI
    запрещён.
    """

    state = get_state()

    if state.mode != MODE_MANUAL:
        raise RuntimeError(
            "Manual start is available only in manual mode"
        )

    if state.running:
        raise RuntimeError(
            "Pipeline is already running"
        )

    state.running = True
    state.stop_requested = False

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    return state

# ============================================================
# START BY AUTOMATION / WATCHER
# ============================================================

def start_automatic():
    """
    Используется scheduler'ом.

    Важно:
    UI-кнопка сюда не обращается.
    """

    state = get_state()

    if state.mode != MODE_AUTOMATIC:
        raise RuntimeError(
            "Automatic start requested while mode is not automatic"
        )

    if state.running:
        return state

    state.running = True
    state.stop_requested = False

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    return state

def start_watcher():
    """
    Запуск watcher-процесса.
    """

    state = get_state()

    if state.mode != MODE_WATCHER:
        raise RuntimeError(
            "Watcher start requested while mode is not watcher"
        )

    if state.running:
        return state

    state.running = True
    state.stop_requested = False

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    return state

# ============================================================
# STOP
# ============================================================

def request_stop():
    """
    Запрашивает остановку текущего процесса.

    После остановки режим автоматически
    возвращается в manual.

    Это соответствует UI-логике:

        STOP
          ↓
        manual
          ↓
        кнопка Запустить active
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    stop_requested = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

def finish_stop():
    """
    Финальное состояние после фактической
    остановки worker'ов.

    ВСЕГДА возвращает систему в manual.
    """

    state = build_manual_mode()

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    mode = 'manual',

                    auto_enabled = FALSE,
                    auto_time = NULL,

                    watcher_enabled = FALSE,
                    watcher_path = NULL,

                    running = FALSE,
                    stop_requested = FALSE,

                    stopped_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP

                WHERE id = 1
                """
            )

        conn.commit()

    return state

# ============================================================
# HELPERS
# ============================================================

def is_stop_requested() -> bool:
    """
    Используется worker/controller loop,
    чтобы понять, нажал ли пользователь STOP.
    """

    with get_connection() as conn:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT stop_requested
                FROM pipeline_control
                WHERE id = 1
                """
            )

            row = cur.fetchone()

    return bool(
        row and row[0]
    )

def is_running() -> bool:
    state = get_state()

    return state.running

def manual_start_allowed() -> bool:
    """
    Источник истины для UI-кнопки «Запустить».
    """

    state = get_state()

    return (
        state.mode == MODE_MANUAL
        and not state.running
    )

def get_mode() -> str:
    return get_state().mode
PY
```

Потом проверка:

```bash
uv run python -m py_compile \
    app/pipeline/modes.py \
    app/pipeline/controller.py
```

И затем проверим **не только синтаксис, а реальную работу с PostgreSQL**:

```bash
uv run python - <<'PY'
from app.pipeline.controller import get_state

state = get_state()

print("mode           =", state.mode)
print("auto_enabled   =", state.auto_enabled)
print("auto_time      =", state.auto_time)
print("watcher        =", state.watcher_enabled)
print("watcher_path   =", state.watcher_path)
print("running        =", state.running)
print("stop_requested =", state.stop_requested)
PY
```

На текущем состоянии ожидаем:

```text
mode           = manual
auto_enabled   = False
auto_time      = None
watcher        = False
watcher_path   = None
running        = False
stop_requested = False
```

**Пока больше ничего не меняй.** После этого подключим контроллер к существующему UI. Там уже сделаем именно твою логику: **ручной → активная кнопка «Запустить»; automatic/watcher → disabled; STOP → полный возврат в manual.**

---

### 👤 **User** — 2026-08-18 23:50:26

.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m py_compile \
    app/pipeline/modes.py \
    app/pipeline/controller.py
  File "app/pipeline/controller.py", line 1
    cd ~/projects/scene_fingerprint_mvp_v02
       ^
SyntaxError: invalid syntax
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:50:27

Да, здесь моя ошибка: в `controller.py` попала строка команды shell:

```text
cd ~/projects/scene_fingerprint_mvp_v02
```

Поэтому Python воспринимает её как код.

Исправим файл целиком. Выполни **один блок**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/pipeline/controller.py <<'PY'
from __future__ import annotations

import os
from datetime import time

import psycopg2
from psycopg2.extras import RealDictCursor

from app.pipeline.modes import (
    MODE_AUTOMATIC,
    MODE_MANUAL,
    MODE_WATCHER,
    PipelineMode,
    build_automatic_mode,
    build_manual_mode,
    build_watcher_mode,
    validate_mode,
)

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_row(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_control (id)
            VALUES (1)
            ON CONFLICT (id) DO NOTHING
            """
        )

    conn.commit()

def get_state() -> PipelineMode:
    with get_connection() as conn:
        ensure_row(conn)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    mode,
                    auto_enabled,
                    auto_time,
                    watcher_enabled,
                    watcher_path,
                    running,
                    stop_requested
                FROM pipeline_control
                WHERE id = 1
                """
            )

            row = cur.fetchone()

    if row is None:
        return build_manual_mode()

    mode = validate_mode(row["mode"])

    return PipelineMode(
        mode=mode,
        auto_enabled=bool(row["auto_enabled"]),
        auto_time=row["auto_time"],
        watcher_enabled=bool(row["watcher_enabled"]),
        watcher_path=row["watcher_path"],
        running=bool(row["running"]),
        stop_requested=bool(row["stop_requested"]),
    )

def _save_state(state: PipelineMode):
    validate_mode(state.mode)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    mode = %s,
                    auto_enabled = %s,
                    auto_time = %s,
                    watcher_enabled = %s,
                    watcher_path = %s,
                    running = %s,
                    stop_requested = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                (
                    state.mode,
                    state.auto_enabled,
                    state.auto_time,
                    state.watcher_enabled,
                    state.watcher_path,
                    state.running,
                    state.stop_requested,
                ),
            )

        conn.commit()

def set_manual():
    state = build_manual_mode()
    _save_state(state)
    return state

def set_automatic(auto_time: time):
    state = build_automatic_mode(auto_time)
    _save_state(state)
    return state

def set_watcher(watcher_path: str):
    state = build_watcher_mode(watcher_path)
    _save_state(state)
    return state

def start_manual():
    state = get_state()

    if state.mode != MODE_MANUAL:
        raise RuntimeError(
            "Manual start is available only in manual mode"
        )

    if state.running:
        raise RuntimeError(
            "Pipeline is already running"
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    state.running = True
    state.stop_requested = False

    return state

def start_automatic():
    state = get_state()

    if state.mode != MODE_AUTOMATIC:
        raise RuntimeError(
            "Automatic start requested while mode is not automatic"
        )

    if state.running:
        return state

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    state.running = True
    state.stop_requested = False

    return state

def start_watcher():
    state = get_state()

    if state.mode != MODE_WATCHER:
        raise RuntimeError(
            "Watcher start requested while mode is not watcher"
        )

    if state.running:
        return state

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    state.running = True
    state.stop_requested = False

    return state

def request_stop():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    stop_requested = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

def finish_stop():
    state = build_manual_mode()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    mode = 'manual',
                    auto_enabled = FALSE,
                    auto_time = NULL,
                    watcher_enabled = FALSE,
                    watcher_path = NULL,
                    running = FALSE,
                    stop_requested = FALSE,
                    stopped_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    return state

def is_stop_requested() -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT stop_requested
                FROM pipeline_control
                WHERE id = 1
                """
            )

            row = cur.fetchone()

    return bool(row and row[0])

def is_running() -> bool:
    return get_state().running

def manual_start_allowed() -> bool:
    state = get_state()

    return (
        state.mode == MODE_MANUAL
        and not state.running
    )

def get_mode() -> str:
    return get_state().mode
PY
```

Теперь:

```bash
uv run python -m py_compile \
    app/pipeline/modes.py \
    app/pipeline/controller.py
```

Если снова **нет вывода**, проверяем БД:

```bash
uv run python - <<'PY'
from app.pipeline.controller import get_state

state = get_state()

print("mode           =", state.mode)
print("auto_enabled   =", state.auto_enabled)
print("auto_time      =", state.auto_time)
print("watcher        =", state.watcher_enabled)
print("watcher_path   =", state.watcher_path)
print("running        =", state.running)
print("stop_requested =", state.stop_requested)
PY
```

Ожидаем:

```text
mode           = manual
auto_enabled   = False
auto_time      = None
watcher        = False
watcher_path   = None
running        = False
stop_requested = False
```

После этого уже **не будем добавлять новые абстрактные файлы вслепую** — следующим шагом посмотрим существующий `app/web/components/technical_modules/automation.py` и подключим этот контроллер непосредственно к твоему текущему UI.

---

### 👤 **User** — 2026-08-18 23:51:02

PY  return get_state().modengNUALl:olENT_TIMESTAMP,not watcher"tic"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m py_compile \
    app/pipeline/modes.py \
    app/pipeline/controller.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python - <<'PY'
from app.pipeline.controller import get_state

state = get_state()

print("mode           =", state.mode)
print("auto_enabled   =", state.auto_enabled)
print("auto_time      =", state.auto_time)
print("watcher        =", state.watcher_enabled)
print("watcher_path   =", state.watcher_path)
print("running        =", state.running)
print("stop_requested =", state.stop_requested)
PY
mode           = manual
auto_enabled   = False
auto_time      = None
watcher        = False
watcher_path   = None
running        = False
stop_requested = False
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:51:04

Отлично. **Слой состояния работает**: Python-компиляция проходит, PostgreSQL читается, начальное состояние корректно:

```text
manual
running = false
stop_requested = false
```

Теперь не добавляем новые файлы. Подключаем это к **существующему UI**.

Сначала покажи текущий модуль автоматизации:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,320p' app/web/components/technical_modules/automation.py
```

И ещё состояние UI:

```bash
sed -n '1,320p' app/web/state.py
```

И чтобы понять, как технический модуль подключён:

```bash
sed -n '1,260p' app/web/components/technical_modules/__init__.py
```

Пришли эти три вывода.

После этого прямо в существующий UI сделаем:

```text
┌─────────────────────────────────────┐
│ РЕЖИМ ЗАПУСКА                       │
│                                     │
│ ○ Ручной                            │
│ ○ Автоматический   [ 23:00 ]       │
│ ○ Watcher          [папка ...]     │
│                                     │
│              [ ЗАПУСТИТЬ ]          │
│              [ ОСТАНОВИТЬ ]         │
└─────────────────────────────────────┘
```

С tooltip:

- **Ручной** — запуск процесса выполняется кнопкой.
- **Автоматический** — процесс запускается автоматически в указанное время; ручная кнопка недоступна.
- **Watcher** — система постоянно наблюдает указанную папку и запускает обработку при появлении новых файлов; ручной и автоматический запуск недоступны.

И после `Остановить`:

```text
automatic/watcher
       ↓
    STOP
       ↓
   остановка
       ↓
    manual
       ↓
[ЗАПУСТИТЬ] активна
```

Причём **Watcher не будет просто переключателем UI** — позже он будет реально запускать ingest только для новых файлов.

---

### 👤 **User** — 2026-08-18 23:51:34

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,320p' app/web/components/technical_modules/automation.py
from nicegui import ui

def build_automation():
    with ui.card().classes("w-full"):
        ui.label("АВТОМАТИКА").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        ui.checkbox(
            "Автоматическая обработка",
            value=True,
        ).props("dense")

        with ui.row().classes("items-center gap-2"):
            ui.label("Время запуска:")

            ui.select(
                [f"{h:02d}:00" for h in range(24)],
                value="06:00",
            ).props("outlined dense")

        ui.label(
            "Если компьютер был выключен:"
        ).classes("text-sm")

        ui.radio(
            [
                "Запустить при следующем включении",
                "Пропустить пропущенный запуск",
            ],
            value="Запустить при следующем включении",
        ).props("dense")

        ui.label(
            "Основной режим: только новые фотографии"
        ).classes("text-xs text-grey-6")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '1,320p' app/web/state.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '1,260p' app/web/components/technical_modules/__init__.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:51:35

> **Inspecting Pipeline Controller Implementation**
>
>
> **Inspected the pipeline controller implementation**
>
> 
>
> Worked for a few seconds

Да. `modes.py` уже нормальный, и `controller.py` компилируется. Сейчас следующий слой — **подключить этот контроллер к реальному блоку «АВТОМАТИКА»**, потому что сейчас `automation.py` содержит только визуальные элементы: они ничего не меняют в `PipelineMode`.

Делаем без переписывания остального UI.

### 1. Сначала покажи текущий controller

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat app/pipeline/controller.py
```

И сразу ещё:

```bash
grep -R "build_automation" -n app
```

### 2. После этого заменим `automation.py`

Цель слоя такая:

```text
┌──────────────────────────────┐
│          АВТОМАТИКА          │
├──────────────────────────────┤
│ ☑ Автоматическая обработка   │
│                              │
│ Время запуска: [06:00 ▼]     │
│                              │
│ Если компьютер был выключен: │
│                              │
│ ○ Запустить при следующем    │
│   включении                  │
│                              │
│ ○ Пропустить                 │
│                              │
│ Режим: только новые фото     │
└──────────────────────────────┘
```

При этом:

- `☑ Автоматическая обработка` → `mode = automatic`
- время → `auto_time`
- выключили автоматизацию → `mode = manual`
- watcher пока **не трогаем**
- ручной `Запустить` остаётся доступен только при `manual`
- `Остановить` переводит состояние обратно в `manual`
- настройки сохраняются в `pipeline_control`
- UI берёт состояние из контроллера, а не держит собственные независимые значения.

То есть мы сейчас как раз переходим от **нарисованных настроек** к настоящему слою управления pipeline.

Пришли `controller.py` — и я дам **готовый файл целиком + команды установки и проверки**, без ручного редактирования по кускам.

---

### 👤 **User** — 2026-08-18 23:52:04

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat app/pipeline/controller.py
from __future__ import annotations

import os
from datetime import time

import psycopg2
from psycopg2.extras import RealDictCursor

from app.pipeline.modes import (
    MODE_AUTOMATIC,
    MODE_MANUAL,
    MODE_WATCHER,
    PipelineMode,
    build_automatic_mode,
    build_manual_mode,
    build_watcher_mode,
    validate_mode,
)

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_row(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_control (id)
            VALUES (1)
            ON CONFLICT (id) DO NOTHING
            """
        )

    conn.commit()

def get_state() -> PipelineMode:
    with get_connection() as conn:
        ensure_row(conn)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    mode,
                    auto_enabled,
                    auto_time,
                    watcher_enabled,
                    watcher_path,
                    running,
                    stop_requested
                FROM pipeline_control
                WHERE id = 1
                """
            )

            row = cur.fetchone()

    if row is None:
        return build_manual_mode()

    mode = validate_mode(row["mode"])

    return PipelineMode(
        mode=mode,
        auto_enabled=bool(row["auto_enabled"]),
        auto_time=row["auto_time"],
        watcher_enabled=bool(row["watcher_enabled"]),
        watcher_path=row["watcher_path"],
        running=bool(row["running"]),
        stop_requested=bool(row["stop_requested"]),
    )

def _save_state(state: PipelineMode):
    validate_mode(state.mode)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    mode = %s,
                    auto_enabled = %s,
                    auto_time = %s,
                    watcher_enabled = %s,
                    watcher_path = %s,
                    running = %s,
                    stop_requested = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                (
                    state.mode,
                    state.auto_enabled,
                    state.auto_time,
                    state.watcher_enabled,
                    state.watcher_path,
                    state.running,
                    state.stop_requested,
                ),
            )

        conn.commit()

def set_manual():
    state = build_manual_mode()
    _save_state(state)
    return state

def set_automatic(auto_time: time):
    state = build_automatic_mode(auto_time)
    _save_state(state)
    return state

def set_watcher(watcher_path: str):
    state = build_watcher_mode(watcher_path)
    _save_state(state)
    return state

def start_manual():
    state = get_state()

    if state.mode != MODE_MANUAL:
        raise RuntimeError(
            "Manual start is available only in manual mode"
        )

    if state.running:
        raise RuntimeError(
            "Pipeline is already running"
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    state.running = True
    state.stop_requested = False

    return state

def start_automatic():
    state = get_state()

    if state.mode != MODE_AUTOMATIC:
        raise RuntimeError(
            "Automatic start requested while mode is not automatic"
        )

    if state.running:
        return state

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    state.running = True
    state.stop_requested = False

    return state

def start_watcher():
    state = get_state()

    if state.mode != MODE_WATCHER:
        raise RuntimeError(
            "Watcher start requested while mode is not watcher"
        )

    if state.running:
        return state

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    running = TRUE,
                    stop_requested = FALSE,
                    started_at = CURRENT_TIMESTAMP,
                    stopped_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    state.running = True
    state.stop_requested = False

    return state

def request_stop():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    stop_requested = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

def finish_stop():
    state = build_manual_mode()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pipeline_control
                SET
                    mode = 'manual',
                    auto_enabled = FALSE,
                    auto_time = NULL,
                    watcher_enabled = FALSE,
                    watcher_path = NULL,
                    running = FALSE,
                    stop_requested = FALSE,
                    stopped_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """
            )

        conn.commit()

    return state

def is_stop_requested() -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT stop_requested
                FROM pipeline_control
                WHERE id = 1
                """
            )

            row = cur.fetchone()

    return bool(row and row[0])

def is_running() -> bool:
    return get_state().running

def manual_start_allowed() -> bool:
    state = get_state()

    return (
        state.mode == MODE_MANUAL
        and not state.running
    )

def get_mode() -> str:
    return get_state().mode
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -R "build_automation" -n app
app/web/components/technical_modules/automation.py:4:def build_automation():
grep: app/web/components/technical_modules/__pycache__/automation.cpython-312.pyc: binary file matches
grep: app/web/components/__pycache__/technical.cpython-312.pyc: binary file matches
app/web/components/technical.py:10:    build_automation,
app/web/components/technical.py:228:                        build_automation()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:52:06

Да. Теперь картина полная. `controller.py` уже достаточно хороший — **его пока не трогаем**. Следующий шаг: заменить только `automation.py`, чтобы UI начал реально управлять `pipeline_control`.

Причём я предлагаю сразу сделать это так, чтобы **при открытии страницы UI восстанавливал текущее состояние из PostgreSQL**, а не всегда показывал `value=True`.

### 1. Сделай backup

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp app/web/components/technical_modules/automation.py \
   app/web/components/technical_modules/automation.py.bak_v01
```

### 2. Полностью замени `automation.py`

```bash
cat > app/web/components/technical_modules/automation.py <<'PY'
from __future__ import annotations

from datetime import datetime, time

from nicegui import ui

from app.pipeline.controller import (
    get_state,
    set_automatic,
    set_manual,
)

def _parse_time(value: str) -> time:
    return datetime.strptime(
        value,
        "%H:%M",
    ).time()

def build_automation():
    state = get_state()

    with ui.card().classes("w-full"):
        ui.label("АВТОМАТИКА").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        # ----------------------------------------------------
        # AUTOMATIC MODE
        # ----------------------------------------------------

        automatic_checkbox = ui.checkbox(
            "Автоматическая обработка",
            value=state.auto_enabled,
        ).props("dense")

        # ----------------------------------------------------
        # TIME
        # ----------------------------------------------------

        with ui.row().classes(
            "items-center gap-2"
        ):
            ui.label("Время запуска:")

            time_select = ui.select(
                [
                    f"{h:02d}:00"
                    for h in range(24)
                ],
                value=(
                    state.auto_time.strftime("%H:%M")
                    if state.auto_time
                    else "06:00"
                ),
            ).props("outlined dense")

        # ----------------------------------------------------
        # MISSED START
        # ----------------------------------------------------

        ui.label(
            "Если компьютер был выключен:"
        ).classes("text-sm")

        missed_start = ui.radio(
            [
                "Запустить при следующем включении",
                "Пропустить пропущенный запуск",
            ],
            value="Запустить при следующем включении",
        ).props("dense")

        # ----------------------------------------------------
        # INFO
        # ----------------------------------------------------

        mode_label = ui.label().classes(
            "text-xs text-grey-6"
        )

        def refresh_mode_label():
            current = get_state()

            if current.mode == "automatic":
                if current.auto_time:
                    mode_label.text = (
                        "Режим: автоматический — "
                        f"запуск в {current.auto_time.strftime('%H:%M')}"
                    )
                else:
                    mode_label.text = (
                        "Режим: автоматический"
                    )

            elif current.mode == "manual":
                mode_label.text = (
                    "Режим: ручной"
                )

            elif current.mode == "watcher":
                mode_label.text = (
                    "Режим: наблюдение за папкой"
                )

        refresh_mode_label()

        # ----------------------------------------------------
        # EVENTS
        # ----------------------------------------------------

        def automatic_changed(event):
            enabled = bool(event.value)

            try:
                if enabled:
                    selected_time = _parse_time(
                        time_select.value
                    )

                    set_automatic(
                        selected_time
                    )

                else:
                    set_manual()

                refresh_mode_label()

            except Exception as exc:
                print(
                    "[AUTOMATION] ERROR:",
                    exc,
                )

                # Возвращаем UI к состоянию БД
                current = get_state()

                automatic_checkbox.value = (
                    current.auto_enabled
                )

                time_select.value = (
                    current.auto_time.strftime("%H:%M")
                    if current.auto_time
                    else "06:00"
                )

                refresh_mode_label()

                ui.notify(
                    f"Ошибка: {exc}",
                    type="negative",
                )

        automatic_checkbox.on(
            "update:model-value",
            automatic_changed,
        )

        def time_changed(event):
            # Если автоматизация выключена,
            # время само по себе режим не меняет.
            current = get_state()

            if current.mode != "automatic":
                return

            try:
                selected_time = _parse_time(
                    event.value
                )

                set_automatic(
                    selected_time
                )

                refresh_mode_label()

            except Exception as exc:
                print(
                    "[AUTOMATION] TIME ERROR:",
                    exc,
                )

                ui.notify(
                    f"Ошибка времени: {exc}",
                    type="negative",
                )

        time_select.on(
            "update:model-value",
            time_changed,
        )

        # ----------------------------------------------------
        # CURRENT STATE
        # ----------------------------------------------------

        if state.mode == "automatic":
            automatic_checkbox.value = True

        elif state.mode == "manual":
            automatic_checkbox.value = False

        # ----------------------------------------------------
        # MAIN MODE INFO
        # ----------------------------------------------------

        ui.label(
            "Основной режим: только новые фотографии"
        ).classes(
            "text-xs text-grey-6"
        )
PY
```

### 3. Проверяем синтаксис

```bash
uv run python -m py_compile \
    app/web/components/technical_modules/automation.py
```

Должно закончиться **без вывода**.

### 4. Проверяем, что UI действительно меняет PostgreSQL

Сначала:

```bash
uv run python - <<'PY'
from app.pipeline.controller import get_state

state = get_state()

print("BEFORE")
print("mode =", state.mode)
print("auto_enabled =", state.auto_enabled)
print("auto_time =", state.auto_time)
PY
```

Потом отдельно проверим сам механизм, **не через UI**:

```bash
uv run python - <<'PY'
from datetime import time

from app.pipeline.controller import (
    set_automatic,
    set_manual,
    get_state,
)

print("SET AUTOMATIC 07:00")
set_automatic(time(7, 0))

state = get_state()

print("mode =", state.mode)
print("auto_enabled =", state.auto_enabled)
print("auto_time =", state.auto_time)

print()
print("SET MANUAL")
set_manual()

state = get_state()

print("mode =", state.mode)
print("auto_enabled =", state.auto_enabled)
print("auto_time =", state.auto_time)
PY
```

Ожидаем:

```text
SET AUTOMATIC 07:00
mode = automatic
auto_enabled = True
auto_time = 07:00:00

SET MANUAL
mode = manual
auto_enabled = False
auto_time = None
```

---

### Важный момент

Сейчас мы **не запускаем сам pipeline по расписанию**.

Мы сделали только правильный слой:

```text
UI
 │
 ▼
automation.py
 │
 ▼
pipeline.controller
 │
 ▼
pipeline_control
 │
 ▼
PostgreSQL
```

То есть теперь галочка — это **реальное состояние системы**, а не декоративный checkbox.

Следующим слоем уже будет:

```text
automatic
    │
    ├── время наступило
    │
    ▼
start_automatic()
    │
    ▼
pipeline runner
    │
    ├── ingest
    ├── DINO
    ├── Qwen
    ├── sort
    └── preview
```

И отдельно:

```text
watcher
   │
   └── новая фотография
          ↓
       pipeline
```

**Сейчас сначала выполни команды 3–4.** Если они проходят, дальше подключим `start_automatic()` к реальному запуску pipeline, не смешивая это с UI.

---

### 👤 **User** — 2026-08-18 23:52:27

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cat > app/web/components/technical_modules/automation.py <<'PY'
from __future__ import annotations

from datetime import datetime, time

from nicegui import ui

from app.pipeline.controller import (
    get_state,
    set_automatic,
    set_manual,
)

def _parse_time(value: str) -> time:
    return datetime.strptime(
        value,
        "%H:%M",
    ).time()

def build_automation():
PY      )   "text-xs text-grey-6"ко новые фотографии"---------('%H:%M')}"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:52:28

Похоже, терминал **съел/исказил heredoc**: по выводу видно, что часть файла попала в одну строку и `PY` оказался не на отдельной строке. Поэтому сейчас не проверяем дальше — сначала убедимся, что файл целый.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,260p' app/web/components/technical_modules/automation.py
```

И затем:

```bash
uv run python -m py_compile \
    app/web/components/technical_modules/automation.py
```

**Пришли оба вывода.** Если файл действительно повреждён, я дам более надёжный способ записи через `cat`/Python, чтобы терминал больше не портил содержимое.

---

### 👤 **User** — 2026-08-18 23:52:59

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,260p' app/web/components/technical_modules/automation.py
from __future__ import annotations

from datetime import datetime, time

from nicegui import ui

from app.pipeline.controller import (
    get_state,
    set_automatic,
    set_manual,
)

def _parse_time(value: str) -> time:
    return datetime.strptime(
        value,
        "%H:%M",
    ).time()

def build_automation():
    state = get_state()

    with ui.card().classes("w-full"):
        ui.label("АВТОМАТИКА").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        # ----------------------------------------------------
        # AUTOMATIC MODE
        # ----------------------------------------------------

        automatic_checkbox = ui.checkbox(
            "Автоматическая обработка",
            value=state.auto_enabled,
        ).props("dense")

        # ----------------------------------------------------
        # TIME
        # ----------------------------------------------------

        with ui.row().classes(
            "items-center gap-2"
        ):
            ui.label("Время запуска:")

            time_select = ui.select(
                [
                    f"{h:02d}:00"
                    for h in range(24)
                ],
                value=(
                    state.auto_time.strftime("%H:%M")
                    if state.auto_time
                    else "06:00"
                ),
            ).props("outlined dense")

        # ----------------------------------------------------
        # MISSED START
        # ----------------------------------------------------

        ui.label(
            "Если компьютер был выключен:"
        ).classes("text-sm")

        missed_start = ui.radio(
            [
                "Запустить при следующем включении",
                "Пропустить пропущенный запуск",
            ],
            value="Запустить при следующем включении",
        ).props("dense")

        # ----------------------------------------------------
        # INFO
        # ----------------------------------------------------

        mode_label = ui.label().classes(
            "text-xs text-grey-6"
        )

        def refresh_mode_label():
            current = get_state()

            if current.mode == "automatic":
                if current.auto_time:
                    mode_label.text = (
                        "Режим: автоматический — "
                        f"запуск в {current.auto_time.strftime('%H:%M')}"
                    )
                else:
                    mode_label.text = (
                        "Режим: автоматический"
                    )

            elif current.mode == "manual":
                mode_label.text = (
                    "Режим: ручной"
                )

            elif current.mode == "watcher":
                mode_label.text = (
                    "Режим: наблюдение за папкой"
                )

        refresh_mode_label()

        # ----------------------------------------------------
        # EVENTS
        # ----------------------------------------------------

        def automatic_changed(event):
            enabled = bool(event.value)

            try:
                if enabled:
                    selected_time = _parse_time(
                        time_select.value
                    )

                    set_automatic(
                        selected_time
                    )

                else:
                    set_manual()

                refresh_mode_label()

            except Exception as exc:
                print(
                    "[AUTOMATION] ERROR:",
                    exc,
                )

                # Возвращаем UI к состоянию БД
                current = get_state()

                automatic_checkbox.value = (
                    current.auto_enabled
                )

                time_select.value = (
                    current.auto_time.strftime("%H:%M")
                    if current.auto_time
                    else "06:00"
                )

                refresh_mode_label()

                ui.notify(
                    f"Ошибка: {exc}",
                    type="negative",
                )

        automatic_checkbox.on(
            "update:model-value",
            automatic_changed,
        )

        def time_changed(event):
            # Если автоматизация выключена,
            # время само по себе режим не меняет.
            current = get_state()

            if current.mode != "automatic":
                return

            try:
                selected_time = _parse_time(
                    event.value
                )

                set_automatic(
                    selected_time
                )

                refresh_mode_label()

            except Exception as exc:
                print(
                    "[AUTOMATION] TIME ERROR:",
                    exc,
                )

                ui.notify(
                    f"Ошибка времени: {exc}",
                    type="negative",
                )

        time_select.on(
            "update:model-value",
            time_changed,
        )

        # ----------------------------------------------------
        # CURRENT STATE
        # ----------------------------------------------------

        if state.mode == "automatic":
            automatic_checkbox.value = True

        elif state.mode == "manual":
            automatic_checkbox.value = False

        # ----------------------------------------------------
        # MAIN MODE INFO
        # ----------------------------------------------------

        ui.label(
            "Основной режим: только новые фотографии"
        ).classes(
            "text-xs text-grey-6"
        )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m py_compile \
    app/web/components/technical_modules/automation.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:53:00

Отлично. Файл **целый и компилируется**. Значит слой UI → `controller` подключён корректно.

Теперь проверим самое важное: **изменение режима реально пишется в PostgreSQL**.

### 1. Тест controller

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
from datetime import time

from app.pipeline.controller import (
    get_state,
    set_automatic,
    set_manual,
)

print("=== INITIAL ===")
state = get_state()
print("mode         =", state.mode)
print("auto_enabled =", state.auto_enabled)
print("auto_time    =", state.auto_time)

print()
print("=== SET AUTOMATIC 07:00 ===")

set_automatic(time(7, 0))

state = get_state()
print("mode         =", state.mode)
print("auto_enabled =", state.auto_enabled)
print("auto_time    =", state.auto_time)

print()
print("=== SET MANUAL ===")

set_manual()

state = get_state()
print("mode         =", state.mode)
print("auto_enabled =", state.auto_enabled)
print("auto_time    =", state.auto_time)
PY
```

Ожидаем:

```text
=== SET AUTOMATIC 07:00 ===
mode         = automatic
auto_enabled = True
auto_time    = 07:00:00

=== SET MANUAL ===
mode         = manual
auto_enabled = False
auto_time    = None
```

### 2. Затем проверим непосредственно БД

```bash
psql -h localhost -U lora -d photobase -c \
"SELECT id, mode, auto_enabled, auto_time, watcher_enabled, watcher_path, running, stop_requested FROM pipeline_control;"
```

Должно быть примерно:

```text
 id | mode   | auto_enabled | auto_time | watcher_enabled | watcher_path | running | stop_requested
----+--------+--------------+-----------+-----------------+--------------+---------+----------------
  1 | manual | f            |           | f               |              | f       | f
```

Это хорошее состояние для продолжения.

### Что уже зафиксировано

Сейчас у нас есть:

```text
                    PostgreSQL
                        │
                        ▼
                pipeline_control
                        │
                        ▼
              pipeline.controller
                   /          \
                  /            \
             manual          automatic
                               │
                               ▼
                            07:00
```

А UI теперь **читает это состояние при создании блока**, вместо того чтобы всегда показывать:

```python
value=True
```

Следующий шаг — **не делать пока watcher и не трогать DINO/Qwen**.

Нужно сделать отдельный `pipeline runner`, который будет единообразно запускать:

```text
INGEST
  ↓
DINO
  ↓
QWEN
  ↓
SORT
  ↓
PREVIEW
```

и у которого `controller.is_stop_requested()` будет позволять корректно остановить процесс.

Но сначала пришли результат **двух проверок выше**.

---

### 👤 **User** — 2026-08-18 23:53:36

id |  mode  | auto_enabled | auto_time | watcher_enabled | watcher_path | running | stop_requested 
----+--------+--------------+-----------+-----------------+--------------+---------+----------------
  1 | manual | f            |           | f               |              | f       | f
(1 row)
    app/web/components/technical_modules/automation.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
from datetime import time

from app.pipeline.controller import (
    get_state,
    set_automatic,
    set_manual,
)

print("=== INITIAL ===")
state = get_state()
print("mode         =", state.mode)
print("auto_enabled =", state.auto_enabled)
print("auto_time    =", state.auto_time)

print()
print("=== SET AUTOMATIC 07:00 ===")

set_automatic(time(7, 0))

state = get_state()
PYint("auto_time    =", state.auto_time)ed)
=== INITIAL ===
mode         = manual
auto_enabled = False
auto_time    = None

=== SET AUTOMATIC 07:00 ===
mode         = automatic
auto_enabled = True
auto_time    = 07:00:00

=== SET MANUAL ===
mode         = manual
auto_enabled = False
auto_time    = None
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ psql -h localhost -U lora -d photobase -c \
"SELECT id, mode, auto_enabled, auto_time, watcher_enabled, watcher_path, running, stop_requested FROM pipeline_control;"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:53:37

Отлично. **Контроллер работает правильно.** По тесту видно:

```text
automatic → auto_enabled=True → 07:00
manual    → auto_enabled=False → NULL
```

И после теста состояние возвращено в:

```text
mode = manual
running = false
stop_requested = false
```

То есть БД сейчас чистая.

Но есть один важный момент: последний `psql` у тебя почему-то не показал таблицу. Возможно, команда не отработала/вывод потерялся. Это не критично, потому что `get_state()` успешно читает и пишет `pipeline_control`.

## Следующий слой: запуск pipeline

Теперь я бы **не стал сразу встраивать запуск в `automation.py`**.

Нужен отдельный файл:

```text
app/pipeline/runner.py
```

Он будет единственной точкой, которая знает порядок:

```text
                 ┌─────────────┐
                 │   RUNNER    │
                 └──────┬──────┘
                        │
                ┌───────▼───────┐
                │     INGEST     │
                └───────┬───────┘
                        │
                ┌───────▼───────┐
                │      DINO     │
                └───────┬───────┘
                        │
                ┌───────▼───────┐
                │      QWEN      │
                └───────┬───────┘
                        │
                ┌───────▼───────┐
                │      SORT      │
                └───────┬───────┘
                        │
                ┌───────▼───────┐
                │    PREVIEW     │
                └───────────────┘
```

При этом:

- `controller` отвечает **только за состояние**;
- `runner` отвечает **только за выполнение**;
- UI отвечает **только за управление и отображение**;
- DINO/Qwen остаются отдельными worker'ами.

Это важно, потому что потом автоматический режим и watcher смогут использовать **тот же самый runner**.

### Перед написанием runner

Мне нужно увидеть, **какими командами сейчас реально запускаются существующие этапы**, чтобы не придумать новые имена и не сломать уже рабочий pipeline.

Выполни одним блоком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== PIPELINE ====="
find app/pipeline -maxdepth 2 -type f -name "*.py" -print | sort

echo
echo "===== WORKERS ====="
find app/workers -maxdepth 2 -type f -name "*.py" -print | sort

echo
echo "===== SCRIPTS ====="
ls scripts/*.py 2>/dev/null | sort

echo
echo "===== DINO REFERENCES ====="
grep -R "dino_worker" -n \
    pyproject.toml \
    app scripts \
    2>/dev/null | head -50

echo
echo "===== QWEN REFERENCES ====="
grep -R "qwen4b_output_v01" -n \
    pyproject.toml \
    app scripts \
    2>/dev/null | head -50

echo
echo "===== SORT/PREVIEW REFERENCES ====="
grep -R -Ei "sort_worker|preview_worker|sort_status|preview_status" \
    app scripts \
    2>/dev/null | head -100
```

**Пришли вывод целиком.**

После этого я дам готовый `runner.py`, а затем подключим к нему кнопку **«Запустить»** и автоматический запуск по времени.

---

### 👤 **User** — 2026-08-18 23:54:02

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== PIPELINE ====="
find app/pipeline -maxdepth 2 -type f -name "*.py" -print | sort

echo
echo "===== WORKERS ====="
find app/workers -maxdepth 2 -type f -name "*.py" -print | sort

echo
echo "===== SCRIPTS ====="
ls scripts/*.py 2>/dev/null | sort

echo
echo "===== DINO REFERENCES ====="
grep -R "dino_worker" -n \
    pyproject.toml \
    app scripts \
    2>/dev/null | head -50

echo
echo "===== QWEN REFERENCES ====="
grep -R "qwen4b_output_v01" -n \
    2>/dev/null | head -100eview_worker|sort_status|preview_status" \
===== PIPELINE =====
app/pipeline/controller.py
app/pipeline/__init__.py
app/pipeline/modes.py
app/pipeline/queue.py
app/pipeline/recovery.py
app/pipeline/worker.py

===== WORKERS =====
app/workers/dino_worker.py
app/workers/qwen_worker.py

===== SCRIPTS =====
scripts/analyze_sequence_v38.py
scripts/analyze_subfingerprints.py
scripts/banner_candidates_v01.py
scripts/banner_crop_search_v01.py
scripts/banner_crop_search_v02.py
scripts/banner_database_v01.py
scripts/banner_database_v02.py
scripts/banner_llm_folder_search_v01.py
scripts/banner_llm_full_v01.py
scripts/banner_llm_full_v02.py
scripts/banner_model_compare_v01.py
scripts/banner_model_compare_v02.py
scripts/banner_model_compare_v03.py
scripts/banner_model_compare_v04.py
scripts/banner_model_compare_v05.py
scripts/banner_qwen25vl_test_v01.py
scripts/banner_qwen4b_test_v01.py
scripts/banner_search_v01.py
scripts/banner_search_v02.py
scripts/banner_search_v03_2.py
scripts/banner_search_v03_3.py
scripts/banner_search_v03.py
scripts/benchmark_hybrid_v01.py
scripts/benchmark_hybrid_v02.py
scripts/benchmark_hybrid_v03.py
scripts/benchmark_hybrid_v04.py
scripts/benchmark_hybrid_v05.py
scripts/benchmark_hybrid_v06.py
scripts/benchmark_hybrid_v07.py
scripts/benchmark_hybrid_v08.py
scripts/benchmark_hybrid_v09.py
scripts/benchmark_hybrid_v10_debug.py
scripts/benchmark_hybrid_v11.py
scripts/benchmark_hybrid_v12_full.py
scripts/benchmark_sub_rerank_v01.py
scripts/benchmark_sub_rerank_v02.py
scripts/benchmark_sub_rerank_v03.py
scripts/benchmark_sub_rerank_v04.py
scripts/benchmark_test_sub_exp.py
scripts/benchmark_test_v1.py
scripts/build_margin_best_from_benchmark.py
scripts/build_subfingerprint_database.py
scripts/build_subfingerprints_exp.py
scripts/compare_benchmark_sub.py
scripts/create_previews_v01.py
scripts/crop_test_banner.py
scripts/dry_run_best_sequence.py
scripts/export_subclusters.py
scripts/export_visual_compare.py
scripts/import_qwen_to_db.py
scripts/llm_resolver_v01.py
scripts/make_subcluster_contact.py
scripts/make_subfingerprints.py
scripts/make_subfingerprints_v2.py
scripts/migrate_sqlite_to_postgres.py
scripts/photo_ingest.py
scripts/qwen4b_output_v01_before_compact_prompt.py
scripts/qwen4b_output_v01.py
scripts/qwen_prompt_ablation.py
scripts/run_hybrid_v12.py
scripts/search_banners_v01.py
scripts/sort_baseline.py
scripts/sort_margin005_best.py
scripts/sort_neighbor_v34.py
scripts/sort_neighbor_v35_benchmark.py
scripts/sort_neighbor_v35.py
scripts/sort_neighbor_v36_img.py
scripts/sort_neighbor_v36.py
scripts/sort_neighbor_v37.py
scripts/sort_sequence_sub_v01.py
scripts/sort_sequence_v38_1.py
scripts/sort_sequence_v38_1_subtest.py
scripts/sort_sequence_v38.py
scripts/sort_sequence_v39.py
scripts/sort_test_and_report_hybrid_v12.py
scripts/sort_test_and_report.py
scripts/sort_test_and_report_v2.py

===== DINO REFERENCES =====

===== QWEN REFERENCES =====
app/web/components/technical_modules/qwen.py.bak_manual_run:27:    / "qwen4b_output_v01.py"
app/web/components/technical_modules/photo_processing.py:194:            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"
app/web/components/technical_modules/qwen.py.bak_before_safe_manual:27:    / "qwen4b_output_v01.py"
app/web/components/technical_modules/photo_processing.py.bak:194:            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"
app/web/components/technical_modules/qwen.py.bak_click_debug:27:    / "qwen4b_output_v01.py"
app/web/components/technical_modules/qwen.py:27:    / "qwen4b_output_v01.py"
app/web/components/technical_modules/qwen.py.bak_realtime_stop:27:    / "qwen4b_output_v01.py"

===== SORT/PREVIEW REFERENCES =====
scripts/photo_ingest.py:                sort_status,
scripts/photo_ingest.py:                preview_status
scripts/photo_ingest.py.bak_pipeline_v01:                sort_status,
scripts/photo_ingest.py.bak_pipeline_v01:                preview_status
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:54:03

> **Inspecting Pipeline Workers and Recovery**
>
>
> **Inspected pipeline workers and recovery mechanisms**
>
> 
>
> Worked for a couple of seconds

Да. Сейчас структура уже правильная: у нас есть отдельные `modes.py` и `controller.py`, а также реальные `dino_worker.py` и `qwen_worker.py`.

**Следующий слой — связать контроллер режима с реальным запуском пайплайна.** Не будем пока трогать DINO/Qwen.

Выполни одним блоком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== queue.py ====="
cat app/pipeline/queue.py

echo
echo "===== worker.py ====="
cat app/pipeline/worker.py

echo
echo "===== recovery.py ====="
cat app/pipeline/recovery.py

echo
echo "===== qwen_worker.py ====="
sed -n '1,420p' app/workers/qwen_worker.py
```

И ещё:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== PHOTO PROCESSING ====="
sed -n '1,280p' app/web/components/technical_modules/photo_processing.py

echo
echo "===== TECHNICAL ====="
sed -n '180,270p' app/web/components/technical.py
```

### Что делаем дальше

У нас должна получиться такая цепочка:

```text
                 pipeline_control
                       │
              ┌────────┴────────┐
              │                 │
           MANUAL           AUTOMATIC
              │                 │
        [Запустить]        время запуска
              │                 │
              └────────┬────────┘
                       ▼
                Pipeline Worker
                       │
              ┌────────┴────────┐
              ▼                 ▼
          DINO worker       QWEN worker
              │                 │
              ▼                 ▼
          address_id       client/brand/
                            description/...
              │                 │
              └────────┬────────┘
                       ▼
                 SORT / PREVIEW
                       │
                       ▼
                    Grid
```

И отдельно:

```text
WATCHER
   │
   └── новая фотография
           │
           ▼
        INGEST
           │
           ▼
      pipeline queue
```

При этом **`photo_id` остаётся постоянным ID фотографии**, а `address_id` — результатом DINO. Это уже правильно заложено в твоём текущем `dino_worker.py`.

После вывода этих файлов я дам следующий готовый файл/команду — **`app/pipeline/worker.py`**, который станет реальным диспетчером всего конвейера и будет уважать:

- ручной режим;
- автоматический режим;
- watcher;
- `stop_requested`;
- восстановление после перезапуска;
- независимые очереди DINO/Qwen;
- дальнейшее подключение сортировки и preview.

То есть пока **не меняем рабочие DINO и Qwen алгоритмы** — оборачиваем их новым управляющим слоем.

---

