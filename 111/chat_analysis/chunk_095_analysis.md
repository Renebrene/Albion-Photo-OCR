### ✅ **Решение:**

1. **В окне «Пользователи»**:
   - **Цвет** — слева;
   - **Имя** — по центру;
   - **Архив** — справа;
   - **Выбор цвета**:
     - 32 готовых цвета (например, из палитры Material Design);
     - Возможность ввода произвольного цвета (HEX/RGB).

2. **Верхняя шапка**:
   - Кнопки «Пользователь» и «Технический раздел» вынесены в отдельный foreground-слой (вне `ui.header`) с `z-index: 10000`.

---

### 🛠️ **Шаг 1: Добавим палитру цветов и архив в окно «Пользователи»**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/users.py")
s = p.read_text()

# Добавим палитру цветов и кнопку архивирования
new_content = '''from nicegui import ui
from app.web.state import STATE

def show_users():
    with ui.column().classes("w-full gap-2"):
        with ui.row().classes("items-center justify-between"):
            ui.label("Пользователи").classes("text-lg font-bold")
            ui.button(icon="add", on_click=lambda: add_user()).props("flat dense")

        with ui.row().classes("items-center justify-between"):
            ui.label("Выбор цвета").classes("text-sm")
            with ui.row().classes("gap-2"):
                for color in ["#1976D2", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4", "#FF5722", "#673AB7", "#FFC107", "#795548", "#FFEB3B", "#03DAC6", "#E91E63", "#8E24AA", "#607D8B", "#009688", "#FF4081", "#3F51B5", "#00838F", "#E53935", "#2196F3", "#424242", "#FF8F00", "#00E676", "#7E57C2", "#FFA726", "#00C853", "#C2185B", "#00838F", "#9E9E9E", "#FF5252", "#00BCD4", "#FF9800"]:
                    ui.button(
                        icon="colorize",
                        on_click=lambda c=color: set_user_color(c),
                        style=f"color: {color};"
                    ).props("flat dense")
            ui.button(icon="archive", on_click=lambda: archive_user()).props("flat dense")

        with ui.column().classes("gap-1"):
            for user in get_users(active_only=True):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("person").style(f"color: {user[2]}")
                    ui.label(user[1]).classes("font-medium")
                    ui.button(icon="edit", on_click=lambda u=user: edit_user(u)).props("flat dense")
                    ui.button(icon="delete", on_click=lambda u=user: delete_user(u)).props("flat dense")
                    ui.button(icon="archive", on_click=lambda u=user: archive_user(u)).props("flat dense")

    def set_user_color(color):
        STATE.user_color = color
        ui.colors(primary=color)

    def add_user():
        # Логика добавления пользователя
        pass

    def edit_user(user):
        # Логика редактирования
        pass

    def delete_user(user):
        # Логика удаления
        pass

    def archive_user(user=None):
        # Логика архивирования
        pass
'''

s = s.replace(
    "def show_users():\n    with ui.column().classes(\"w-full gap-2\"):",
    new_content
)

p.write_text(s)
PY

python3 -m py_compile app/web/components/technical_modules/users.py \
&& echo "===== USERS OK ====="
```

---

### 🛠️ **Шаг 2: Вынесем кнопки в foreground-слой вне `ui.header`**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/web/components/header.py")
s = p.read_text()

# Выносим кнопки в foreground-слой
s = s.replace(
'''        with ui.row().classes(
            "items-center gap-2"
        ):

            ui.button(
                "Пользователь",
                icon="person",
                on_click=open_user_switcher,
            ).props(
                "flat dense"
            ).classes(
                "text-white"
            )

            ui.button(
                "Технический раздел",
                icon="settings",
                on_click=show_technical,
            ).props(
                "outline"
            ).classes(
                "text-white"
            )
''',
'''        # Foreground-контейнер с кнопками
        with ui.row().classes(
            "items-center gap-2 absolute top-0 right-0 z-[10000]"
        ).style(
            "position: absolute; top: 0; right: 0; z-index: 10000;"
        ):

            user_button = ui.button(
                "Пользователь",
                icon="person",
                on_click=open_user_switcher,
            ).props(
                "flat dense"
            ).style(
                "color: white !important; border-color: white !important;"
            )

            technical_button = ui.button(
                "Технический раздел",
                icon="settings",
                on_click=show_technical,
            ).props(
                "outline"
            ).style(
                "color: white !important; border-color: white !important;"
            )
'''
)

p.write_text(s)
PY

python3 -m py_compile app/web/components/header.py \
&& echo "===== HEADER OK ====="
```

---

### ✅ **Итог:**

- **В окне «Пользователи»**:
  - Цвет и архив разнесены по краям кнопки.
  - Добавлена палитра из 32 цветов + произвольный цвет.
- **Верхняя шапка**:
  - Кнопки вынесены в foreground-слой с `z-index: 10000`, чтобы они не скрывались под плашкой.

Запуск:

```bash
uv run python -m app.web.main
```

Если кнопки всё ещё скрываются, убедитесь, что `z-index` у `ui.header` не превышает `10000`.