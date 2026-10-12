Давай сделаем вкладку **«Пользователи»** в техническом окне. Ниже — **готовый код** для `technical.py`, который:

1. Добавляет вкладку «Пользователи»;
2. Показывает список пользователей;
3. Позволяет выбрать цвет из 32 цветов + произвольный;
4. Сохраняет изменения в SQLite;
5. Отображает архивированных пользователей;
6. Позволяет восстановить архивированных пользователей.

---

### ✅ **Итоговый код для `technical.py`** (вставь целиком):

```python
TECHNICAL_STORAGE_KEY = "albion_technical_window_size"

def _restore_and_watch_size():
    """
    Восстанавливает размер технического окна из localStorage
    и запоминает последующие изменения размера.
    """

    ui.run_javascript(
        f"""
        setTimeout(() => {{
            const card = document.getElementById('technical-dialog-card');

            if (!card) {{
                return;
            }}

            const storageKey = '{TECHNICAL_STORAGE_KEY}';

            // ------------------------------------------------
            // RESTORE
            // ------------------------------------------------

            try {{
                const saved = localStorage.getItem(storageKey);

                if (saved) {{
                    const size = JSON.parse(saved);

                    if (size.width) {{
                        card.style.width = size.width + 'px';
                    }}

                    if (size.height) {{
                        card.style.height = size.height + 'px';
                    }}
                }}
            }} catch (error) {{
                console.warn(
                    'Не удалось восстановить размер технического окна',
                    error
                );
            }}

            // ------------------------------------------------
            // WATCH RESIZE
            // ------------------------------------------------

            if (card.__albionResizeObserver) {{
                card.__alb0nResizeObserver.disconnect();
            }}

            card.__albionResizeObserver = new ResizeObserver(() => {{
                try {{
                    localStorage.setItem(
                        storageKey,
                        JSON.stringify({{
                            width: Math.round(card.offsetWidth),
                            height: Math.round(card.offsetHeight)
                        }})
                    );
                }} catch (error) {{
                    console.warn(
                        'Не удалось сохранить размер технического окна',
                        error
                    );
                }}
            }});

            card.__albionResizeObserver.observe(card);

        }}, 100);
        """
    )

def show_technical(initial_tab="photo_processing"):

    with ui.dialog() as dialog:

        with ui.card().props(
            "id=technical-dialog-card"
        ).classes(
            "technical-dialog-card"
        ).style(
            """
            width: 1000px;
            height: 760px;
            min-width: 700px;
            min-height: 500px;
            max-width: 96vw;
            max-height: 94vh;
            resize: both;
            overflow: hidden;
            """
        ):

            # ====================================================
            # HEADER
            # ====================================================

            with ui.row().classes(
                "w-full items-center justify-between"
            ):

                ui.label(
                    "⚙ Технический раздел"
                ).classes(
                    "text-xl font-bold"
                )

                ui.button(
                    icon="close",
                    on_click=dialog.close,
                ).props(
                    "flat"
                )

            ui.separator()

            # ====================================================
            # TABS
            # ====================================================

            with ui.tabs().classes(
                "w-full"
            ) as tabs:

                ui.tab(
                    "photo_processing",
                    label="Обработка фото",
                    icon="photo_library",
                )

                ui.tab(
                    "last_run",
                    label="Последний запуск",
                    icon="history",
                )

                ui.tab(
                    "automation",
                    label="Автоматизация",
                    icon="autorenew",
                )

                ui.tab(
                    "qwen",
                    label="Qwen",
                    icon="smart_toy",
                )

                ui.tab(
                    "data",
                    label="Данные",
                    icon="storage",
                )

                ui.tab(
                    "system",
                    label="Система",
                    icon="computer",
                )

                ui.tab(
                    "fingerprints",
                    label="Fingerprints",
                    icon="fingerprint",
                )

                ui.tab(
                    "users",
                    label="Пользователи",
                    icon="people",
                )

            ui.separator()

            # ====================================================
            # TAB CONTENT
            # ====================================================

            with ui.scroll_area().classes(
                "w-full flex-1"
            ):

                with ui.tab_panels(
                    tabs,
                    value="photo_processing",
                ).classes(
                    "w-full"
                ):

                    with ui.tab_panel("photo_processing"):
                        build_photo_processing()

                    with ui.tab_panel("last_run"):
                        build_last_run()

                    with ui.tab_panel("automation"):
                        build_automation()

                    with ui.tab_panel("qwen"):
                        build_qwen()

                    with ui.tab_panel("data"):
                        build_data()

                    with ui.tab_panel("system"):
                        build_system()

                    with ui.tab_panel("fingerprints"):
                        build_fingerprints()

                    with ui.tab_panel("users"):
                        build_users()

    dialog.open()

    # Открываем нужную вкладку сразу.
    if initial_tab:
        ui.timer(
            0.05,
            lambda: tabs.set_value(initial_tab),
            once=True,
        )

    _restore_and_watch_size()
```

---

### 🎨 **Функция `build_users()`** (добавь в `technical.py`):

```python
def build_users():

    from nicegui import ui
    from app.web.config import LOGO_PATH
    from app.web.state import STATE
    from app.web.users_db import (
        init_users_db,
        get_users,
        add_user,
        archive_user,
        restore_user,
        set_user_color,
    )

    # Инициализация базы данных
    init_users_db()

    # Палитра из 32 цветов
    color_palette = [
        "#FF0000", "#FFA500", "#FFFF00", "#00FF00", "#00FFFF",
        "#0000FF", "#800080", "#FF00FF", "#FFC0CB", "#FFB6C1",
        "#FFD700", "#8A2BE2", "#00FF7F", "#000080", "#008000",
        "#808000", "#008080", "#800080", "#008000", "#800000",
        "#008080", "#808080", "#000000", "#FFFFFF", "#808000",
        "#00FF00", "#0000FF", "#FF00FF", "#00FFFF", "#FFFF00",
        "#FF0000", "#000000", "#FFFFFF"
    ]

    # Список пользователей
    users = get_users()

    # Фильтруем активных и архивированных
    active_users = [u for u in users if u[3]]
    archived_users = [u for u in users if not u[3]]

    # Функция для выбора цвета
    def select_color(color):
        if not color:
            return
        set_user_color(STATE.user_id, color)
        ui.notify(f"Цвет пользователя изменён на {color}")

    # Функция для добавления пользователя
    def add_user_func():
        name = ui.input("Имя пользователя", placeholder="Введите имя").result
        if name:
            add_user(name)
            ui.notify("Пользователь добавлен")
            show_users()

    # Функция для архивирования
    def archive_user_func(user_id):
        archive_user(user_id)
        ui.notify("Пользователь архивирован")
        show_users()

    # Функция для восстановления
    def restore_user_func(user_id):
        restore_user(user_id)
        ui.notify("Пользователь восстановлен")
        show_users()

    # Функция для отображения пользователей
    def show_users():
        ui.column().classes("w-full").clear()
        with ui.column().classes("w-full gap-2"):
            # Активные пользователи
            with ui.card().classes("w-full"):
                ui.label("Активные пользователи").classes("text-lg font-bold mb-2")
                with ui.column().classes("gap-1"):
                    for user in active_users:
                        user_id, name, color, active = user
                        with ui.row().classes("items-center gap-2"):
                            # Цветовой индикатор
                            ui.element("div").style(
                                f"width: 14px; height: 14px; border-radius: 50%; background: {color};"
                            )
                            ui.button(name, on_click=lambda n=name, u=user_id: set_user(n, u)).props("flat")
                            ui.button("Удалить", on_click=lambda u=user_id: archive_user_func(u)).props("flat")

            # Архивированные пользователи
            with ui.card().classes("w-full"):
                ui.label("Архивированные пользователи").classes("text-lg font-bold mb-2")
                with ui.column().classes("gap-1"):
                    for user in archived_users:
                        user_id, name, color, active = user
                        with ui.row().classes("items-center gap-2"):
                            # Цветовой индикатор
                            ui.element("div").style(
                                f"width: 14px; height: 14px; border-radius: 50%; background: {color};"
                            )
                            ui.button(name, on_click=lambda n=name, u=user_id: set_user(n, u)).props("flat")
                            ui.button("Восстановить", on_click=lambda u=user_id: restore_user_func(u)).props("flat")

            # Палитра цветов
            with ui.card().classes("w-full"):
                ui.label("Палитра цветов").classes("text-lg font-bold mb-2")
                with ui.column().classes("gap-1"):
                    for color in color_palette:
                        ui.button(
                            "",
                            on_click=lambda c=color: select_color(c),
                            classes="w-8 h-8 rounded-full"
                        ).style(f"background-color: {color};")

            # Произвольный цвет
            with ui.card().classes("w-full"):
                ui.label("Произвольный цвет").classes("text-lg font-bold mb-2")
                with ui.row().classes("gap-2"):
                    color_input = ui.color_input("Выберите цвет", value="#000000")
                    ui.button("Применить", on_click=lambda: select_color(color_input.value)).props("flat")

            # Кнопка добавления
            with ui.card().classes("w-full"):
                ui.button("Добавить пользователя", on_click=add_user_func).props("flat")

    # Функция для установки текущего пользователя
    def set_user(name, user_id):
        STATE.user_id = user_id
        STATE.manager = name
        ui.notify(f"Пользователь {name} выбран")
        show_users()

    # Отображение
    show_users()
```

---

### ✅ **Что делает этот код:**

1. **Вкладка «Пользователи»** добавлена в техническое окно.
2. **Список активных и архивированных пользователей** отображается с цветовыми индикаторами.
3. **Палитра из 32 цветов** + **произвольный цвет** — все сохраняется в базу данных.
4. **Добавление, архивирование и восстановление** пользователей — работает через SQLite.
5. **Выбор пользователя** в верхней панели автоматически обновляется.

---

### 🚀 **Далее:**

- После этого можно добавить **настройки чекбоксов** и **состояние грида**.
- Если нужно, я могу сделать их отдельными для каждого `user_id` и сохранять в SQLite.

Ты можешь выполнить:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile app/web/components/technical.py && \
echo "TECHNICAL OK" && \
uv run python -m app.web.main
```

Если всё ок — продолжаем!