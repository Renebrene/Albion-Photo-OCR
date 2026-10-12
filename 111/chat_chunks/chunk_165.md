## СЕССИЯ: 19-2

**Создано:** 2026-08-19 14:18:36
**Обновлено:** 2026-08-20 00:17:26
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a859109-7218-83ea-9de2-3480a4713401](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a859109-7218-83ea-9de2-3480a4713401)

---

### 🤖 **Assistant** — 2026-08-19 15:41:43

Да. Делаем сейчас. **`users_db.py` уже мигрирован и цвета сохранены**, его больше не трогаем.

Ниже — один патч для `users.py` и `header.py`.

### 1. `users.py` — заменить целиком

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > app/web/components/technical_modules/users.py <<'PY'
from nicegui import ui

from app.web.state import STATE
from app.web.users_db import (
    get_users,
    add_user,
    update_user_name,
    update_user_color,
    update_user_password,
    archive_user,
    restore_user,
)

# ============================================================
# FIXED 32-COLOR PALETTE
# ============================================================

USER_COLORS = [
    ("Красный", "#E53935"),
    ("Розовый", "#D81B60"),
    ("Фиолетовый", "#8E24AA"),
    ("Тёмно-фиолетовый", "#5E35B1"),
    ("Индиго", "#3949AB"),
    ("Синий", "#1E88E5"),
    ("Голубой", "#039BE5"),
    ("Циан", "#00ACC1"),
    ("Бирюзовый", "#00897B"),
    ("Зелёный", "#43A047"),
    ("Светло-зелёный", "#7CB342"),
    ("Лайм", "#C0CA33"),
    ("Жёлтый", "#FDD835"),
    ("Янтарный", "#FFB300"),
    ("Оранжевый", "#FB8C00"),
    ("Глубокий оранжевый", "#F4511E"),
    ("Коричневый", "#6D4C41"),
    ("Серо-коричневый", "#8D6E63"),
    ("Серый", "#757575"),
    ("Сине-серый", "#546E7A"),
    ("Бордовый", "#B71C1C"),
    ("Тёмно-красный", "#C62828"),
    ("Малиновый", "#AD1457"),
    ("Тёмно-фиолетовый", "#6A1B9A"),
    ("Тёмно-синий", "#283593"),
    ("Тёмно-голубой", "#1565C0"),
    ("Тёмный циан", "#006064"),
    ("Тёмно-зелёный", "#2E7D32"),
    ("Тёмно-бирюзовый", "#00695C"),
    ("Тёмно-оранжевый", "#EF6C00"),
    ("Тёмно-коричневый", "#4E342E"),
    ("Тёмно-серый", "#263238"),
]

COLOR_BY_HEX = {
    color.upper(): name
    for name, color in USER_COLORS
}

def color_label(color):
    return COLOR_BY_HEX.get(
        str(color or "").upper(),
        str(color or ""),
    )

def build_users():

    show_archived = {"value": False}

    root = ui.column().classes(
        "w-full gap-2 px-6 py-3"
    )

    with root:

        # ====================================================
        # HEADER
        # ====================================================

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            with ui.column().classes("gap-0"):

                ui.label(
                    "Пользователи"
                ).classes(
                    "text-lg font-bold"
                )

                ui.label(
                    "Имя, пароль и цвет интерфейса"
                ).classes(
                    "text-xs text-grey-6"
                )

            with ui.row().classes(
                "items-center gap-2"
            ):

                ui.checkbox(
                    "Архив",
                    value=False,
                    on_change=lambda e:
                        toggle_archived(e.value),
                ).props(
                    "dense"
                )

                ui.button(
                    "Добавить",
                    icon="person_add",
                    on_click=lambda: add_user_dialog(),
                ).props(
                    "outline dense"
                )

        ui.separator()

        user_list = ui.column().classes(
            "w-full gap-1"
        )

        # ====================================================
        # ADD USER
        # ====================================================

        def add_user_dialog():

            with ui.dialog() as dialog:

                with ui.card().classes(
                    "w-[420px] max-w-[92vw]"
                ):

                    ui.label(
                        "Добавить пользователя"
                    ).classes(
                        "text-lg font-bold"
                    )

                    name_input = ui.input(
                        "Имя пользователя"
                    ).classes(
                        "w-full"
                    )

                    password_input = ui.input(
                        "Пароль",
                        password=True,
                        password_toggle_button=True,
                    ).classes(
                        "w-full"
                    )

                    # Для нового пользователя
                    selected_color = {
                        "value": USER_COLORS[0][1]
                    }

                    color_select = ui.select(
                        options={
                            color: name
                            for name, color in USER_COLORS
                        },
                        value=selected_color["value"],
                        label="Цвет",
                    ).classes(
                        "w-full"
                    )

                    def save():

                        name = (
                            name_input.value or ""
                        ).strip()

                        password = (
                            password_input.value or ""
                        ).strip()

                        color = (
                            color_select.value
                            or selected_color["value"]
                        )

                        if not name:
                            ui.notify(
                                "Введите имя пользователя",
                                type="warning",
                            )
                            return

                        if not password:
                            ui.notify(
                                "Введите пароль",
                                type="warning",
                            )
                            return

                        if not add_user(
                            name,
                            color,
                            password,
                        ):
                            ui.notify(
                                "Такой пользователь уже существует",
                                type="warning",
                            )
                            return

                        dialog.close()
                        rebuild()

                    with ui.row().classes(
                        "w-full justify-end gap-2 mt-2"
                    ):

                        ui.button(
                            "Отмена",
                            on_click=dialog.close,
                        ).props(
                            "flat dense"
                        )

                        ui.button(
                            "Добавить",
                            icon="person_add",
                            on_click=save,
                        ).props(
                            "dense"
                        )

            dialog.open()

        # ====================================================
        # EDIT USER
        # ====================================================

        def edit_user(
            user_id,
            old_name,
            old_color,
        ):

            with ui.dialog() as dialog:

                with ui.card().classes(
                    "w-[420px] max-w-[92vw]"
                ):

                    ui.label(
                        "Настройки пользователя"
                    ).classes(
                        "text-lg font-bold"
                    )

                    name_input = ui.input(
                        "Имя",
                        value=old_name,
                    ).classes(
                        "w-full"
                    )

                    password_input = ui.input(
                        "Новый пароль",
                        password=True,
                        password_toggle_button=True,
                    ).props(
                        "hint='Оставьте пустым, чтобы сохранить текущий пароль'"
                    ).classes(
                        "w-full"
                    )

                    color_select = ui.select(
                        options={
                            color: name
                            for name, color in USER_COLORS
                        },
                        value=old_color,
                        label="Цвет",
                    ).classes(
                        "w-full"
                    )

                    def save():

                        name = (
                            name_input.value or ""
                        ).strip()

                        color = (
                            color_select.value
                            or old_color
                        )

                        password = (
                            password_input.value or ""
                        ).strip()

                        if not name:
                            ui.notify(
                                "Имя не может быть пустым",
                                type="warning",
                            )
                            return

                        if not update_user_name(
                            user_id,
                            name,
                        ):
                            ui.notify(
                                "Такой пользователь уже существует",
                                type="warning",
                            )
                            return

                        if color != old_color:
                            update_user_color(
                                user_id,
                                color,
                            )

                        if password:
                            update_user_password(
                                user_id,
                                password,
                            )

                        if STATE.user_id == user_id:
                            STATE.manager = name

                        dialog.close()
                        rebuild()

                    with ui.row().classes(
                        "w-full justify-end gap-2 mt-2"
                    ):

                        ui.button(
                            "Отмена",
                            on_click=dialog.close,
                        ).props(
                            "flat dense"
                        )

                        ui.button(
                            "Сохранить",
                            icon="save",
                            on_click=save,
                        ).props(
                            "dense"
                        )

            dialog.open()

        # ====================================================
        # ARCHIVE CONFIRMATION
        # ====================================================

        def confirm_archive(
            user_id,
            name,
        ):

            if STATE.user_id == user_id:

                ui.notify(
                    "Нельзя архивировать текущего пользователя",
                    type="warning",
                )

                return

            with ui.dialog() as dialog:

                with ui.card().classes(
                    "w-[400px] max-w-[92vw]"
                ):

                    ui.label(
                        "Архивировать пользователя?"
                    ).classes(
                        "text-lg font-bold"
                    )

                    ui.label(
                        f"Пользователь «{name}» будет перемещён в архив."
                    ).classes(
                        "text-sm text-grey-7"
                    )

                    with ui.row().classes(
                        "w-full justify-end gap-2 mt-3"
                    ):

                        ui.button(
                            "Отмена",
                            on_click=dialog.close,
                        ).props(
                            "flat"
                        )

                        def confirm():

                            archive_user(
                                user_id
                            )

                            dialog.close()
                            rebuild()

                        ui.button(
                            "Архивировать",
                            icon="archive",
                            on_click=confirm,
                        ).props(
                            "color=negative"
                        )

            dialog.open()

        # ====================================================
        # RESTORE
        # ====================================================

        def restore_user_action(user_id):

            restore_user(
                user_id
            )

            rebuild()

        # ====================================================
        # ARCHIVE FILTER
        # ====================================================

        def toggle_archived(value):

            show_archived["value"] = bool(value)

            rebuild()

        # ====================================================
        # REBUILD
        # ====================================================

        def rebuild():

            user_list.clear()

            users = get_users(
                active_only=not show_archived["value"]
            )

            with user_list:

                if not users:

                    ui.label(
                        "Нет пользователей"
                    ).classes(
                        "text-grey-6 p-3"
                    )

                    return

                for (
                    user_id,
                    name,
                    color,
                    active,
                ) in users:

                    is_current = (
                        STATE.user_id == user_id
                    )

                    with ui.row().classes(
                        "w-full items-center "
                        "gap-2 px-2 py-1 "
                        "rounded-lg"
                    ).style(
                        f"""
                        border-left:4px solid {color};
                        background:
                        {
                            'rgba(0,0,0,0.04)'
                            if is_current
                            else 'transparent'
                        };
                        """
                    ):

                        # ====================================
                        # EDIT
                        # ====================================

                        ui.button(
                            icon="edit",
                            on_click=lambda e,
                            uid=user_id,
                            n=name,
                            c=color:
                                edit_user(
                                    uid,
                                    n,
                                    c,
                                ),
                        ).props(
                            "flat round dense"
                        )

                        # ====================================
                        # NAME
                        # ====================================

                        with ui.column().classes(
                            "gap-0"
                        ):

                            ui.label(
                                name
                            ).classes(
                                "text-sm font-medium"
                            )

                            if is_current:

                                ui.label(
                                    "Текущий пользователь"
                                ).classes(
                                    "text-[10px] text-primary"
                                )

                            elif not active:

                                ui.label(
                                    "Архив"
                                ).classes(
                                    "text-[10px] text-grey-6"
                                )

                        # ====================================
                        # COLOR
                        # ====================================

                        if active:

                            with ui.row().classes(
                                "items-center gap-2 ml-3"
                            ):

                                ui.element(
                                    "div"
                                ).style(
                                    f"""
                                    width:18px;
                                    height:18px;
                                    min-width:18px;
                                    border-radius:50%;
                                    background:{color};
                                    border:1px solid rgba(0,0,0,.25);
                                    """
                                )

                                ui.label(
                                    color_label(color)
                                ).classes(
                                    "text-xs text-grey-7"
                                )

                        # ====================================
                        # RIGHT: ARCHIVE
                        # ====================================

                        with ui.element(
                            "div"
                        ).classes(
                            "ml-auto"
                        ):

                            if active:

                                ui.button(
                                    icon="archive",
                                    on_click=lambda e,
                                    uid=user_id,
                                    n=name:
                                        confirm_archive(
                                            uid,
                                            n,
                                        ),
                                ).props(
                                    "flat round dense"
                                )

                            else:

                                ui.button(
                                    icon="unarchive",
                                    on_click=lambda e,
                                    uid=user_id:
                                        restore_user_action(
                                            uid
                                        ),
                                ).props(
                                    "flat round dense"
                                )

        rebuild()
PY
```

### 2. Теперь `header.py`

Здесь меняем только импорт и механизм переключения пользователя.

```bash id="0q3v1a"
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/web/components/header.py")
s = p.read_text()

s = s.replace(
    "from app.web.users_db import (\n"
    "    init_users_db,\n"
    "    get_users,\n"
    ")",
    "from app.web.users_db import (\n"
    "    init_users_db,\n"
    "    get_users,\n"
    "    check_user_password,\n"
    ")",
)

old = '''        def open_user_switcher():

            dialog = ui.dialog()

            with dialog:

                with ui.card().classes(
                    "w-[360px] max-w-[90vw]"
                ):
                    ui.label(
                        "Выбор пользователя"
                    ).classes(
                        "text-lg font-bold mb-2"
                    )

                    user_list = ui.column().classes(
                        "w-full gap-1"
                    )

                    def select_user(
                        user_id,
                        name,
                        color,
                    ):

                        STATE.user_id = user_id
                        STATE.manager = name

                        user_button.text = name

                        apply_user_color(
                            color
                        )

                        print(
                            "[USER SELECT]",
                            user_id,
                            repr(name),
                            color,
                            flush=True,
                        )

                        dialog.close()

                    users = get_users()

                    with user_list:

                        for (
                            user_id,
                            name,
                            color,
                            active,
                        ) in users:

                            with ui.row().classes(
                                "w-full items-center"
                            ):

                                # цветовой индикатор
                                ui.element(
                                    "div"
                                ).style(
                                    f"""
                                    width: 14px;
                                    height: 14px;
                                    min-width: 14px;
                                    border-radius: 50%;
                                    background: {color};
                                    border: 1px solid rgba(0,0,0,.2);
                                    """
                                )

                                ui.button(
                                    name,
                                    on_click=lambda e,
                                    uid=user_id,
                                    n=name,
                                    c=color:
                                        select_user(
                                            uid,
                                            n,
                                            c,
                                        ),
                                ).props(
                                    "flat"
                                ).classes(
                                    "flex-grow justify-start"
                                )

                    ui.separator().classes(
                        "my-2"
                    )

                    ui.button(
                        "Закрыть",
                        on_click=dialog.close,
                    ).props(
                        "flat"
                    )

            dialog.open()
'''

new = '''        def open_user_switcher():

            dialog = ui.dialog()

            with dialog:

                with ui.card().classes(
                    "w-[380px] max-w-[92vw]"
                ):

                    ui.label(
                        "Выбор пользователя"
                    ).classes(
                        "text-lg font-bold mb-2"
                    )

                    user_list = ui.column().classes(
                        "w-full gap-1"
                    )

                    # ------------------------------------------------
                    # PASSWORD DIALOG
                    # ------------------------------------------------

                    def request_password(
                        user_id,
                        name,
                        color,
                    ):

                        with ui.dialog() as password_dialog:

                            with ui.card().classes(
                                "w-[360px] max-w-[90vw]"
                            ):

                                ui.label(
                                    f"Вход: {name}"
                                ).classes(
                                    "text-lg font-bold"
                                )

                                ui.label(
                                    "Введите пароль менеджера"
                                ).classes(
                                    "text-sm text-grey-7"
                                )

                                password_input = ui.input(
                                    "Пароль",
                                    password=True,
                                    password_toggle_button=True,
                                ).classes(
                                    "w-full"
                                )

                                def confirm():

                                    password = (
                                        password_input.value
                                        or ""
                                    )

                                    if not check_user_password(
                                        user_id,
                                        password,
                                    ):

                                        ui.notify(
                                            "Неверный пароль",
                                            type="negative",
                                        )

                                        return

                                    # --------------------------------
                                    # ONLY HERE DO WE CHANGE STATE
                                    # --------------------------------

                                    STATE.user_id = user_id
                                    STATE.manager = name

                                    user_button.text = name

                                    apply_user_color(
                                        color
                                    )

                                    print(
                                        "[USER SELECT]",
                                        user_id,
                                        repr(name),
                                        color,
                                        flush=True,
                                    )

                                    password_dialog.close()
                                    dialog.close()

                                with ui.row().classes(
                                    "w-full justify-end gap-2 mt-3"
                                ):

                                    ui.button(
                                        "Отмена",
                                        on_click=password_dialog.close,
                                    ).props(
                                        "flat"
                                    )

                                    ui.button(
                                        "Войти",
                                        icon="login",
                                        on_click=confirm,
                                    ).props(
                                        "dense"
                                    )

                        password_dialog.open()

                    users = get_users()

                    with user_list:

                        for (
                            user_id,
                            name,
                            color,
                            active,
                        ) in users:

                            with ui.row().classes(
                                "w-full items-center"
                            ):

                                ui.element(
                                    "div"
                                ).style(
                                    f"""
                                    width:14px;
                                    height:14px;
                                    min-width:14px;
                                    border-radius:50%;
                                    background:{color};
                                    border:1px solid rgba(0,0,0,.2);
                                    """
                                )

                                ui.button(
                                    name,
                                    on_click=lambda e,
                                    uid=user_id,
                                    n=name,
                                    c=color:
                                        request_password(
                                            uid,
                                            n,
                                            c,
                                        ),
                                ).props(
                                    "flat"
                                ).classes(
                                    "flex-grow justify-start"
                                )

                    ui.separator().classes(
                        "my-2"
                    )

                    ui.button(
                        "Закрыть",
                        on_click=dialog.close,
                    ).props(
                        "flat"
                    )

            dialog.open()
'''

if old not in s:
    raise SystemExit(
        "Не найден старый блок open_user_switcher(). "
        "Файл header.py не изменён."
    )

s = s.replace(old, new)

p.write_text(s)
print("header.py patched")
PY
```

### 3. Убираем старый `manager_colors`

Он уже не нужен. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/web/state.py")
s = p.read_text()

start = s.find(
    '    manager_colors: dict[str, str] = field(default_factory=lambda: {'
)

if start == -1:
    print("manager_colors: already absent")
else:
    end = s.find(
        '    })\n',
        start,
    )

    if end == -1:
        raise SystemExit("Не удалось найти конец manager_colors")

    end += len('    })\n')

    s = s[:start] + s[end:]
    p.write_text(s)

    print("state.py: manager_colors removed")
PY
```

### 4. Проверка синтаксиса

**Сервис пока не перезапускаем.**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
    app/web/users_db.py \
    app/web/components/technical_modules/users.py \
    app/web/components/header.py \
    app/web/state.py
```

Если команда ничего не выведет — синтаксис всех четырёх файлов корректный.

После этого:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
git diff -- \
    app/web/users_db.py \
    app/web/components/technical_modules/users.py \
    app/web/components/header.py \
    app/web/state.py
```

**Пришли вывод `py_compile` и `git diff`.** Сначала проверим патч, и только потом перезапустим `lora.service`.

---

### 👤 **User** — 2026-08-19 15:44:04

PYint("header.py patched") изменён."user_switcher(). "-start",0,.2);se,
Не найден старый блок open_user_switcher(). Файл header.py не изменён.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 15:44:07

Да, патч не применился — причина именно в том, что искали старый блок `open_user_switcher()` по тексту, а он у тебя уже отличается.

**Ничего пока не меняем повторно.** Сначала возьмём точные текущие блоки, чтобы сделать один надёжный патч без риска затронуть остальное.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \

echo "================ HEADER CURRENT ================" && \
nl -ba app/web/components/header.py | sed -n '105,225p' && \

echo "================ USERS CURRENT 1-140 ================" && \
nl -ba app/web/components/technical_modules/users.py | sed -n '1,140p' && \

echo "================ USERS CURRENT 140-335 ================" && \
nl -ba app/web/components/technical_modules/users.py | sed -n '140,335p' && \

echo "================ USERS DB CURRENT ================" && \
nl -ba app/web/users_db.py | sed -n '1,190p'
```

После этого я дам **один патч сразу для трёх файлов**:

- `app/web/users_db.py`
  - пароль уже существующий оставляем `1234`;
  - `password TEXT`;
  - функции проверки/изменения пароля;
  - существующие цвета **не трогаем**.

- `app/web/components/header.py`
  - клик по текущему менеджеру → список менеджеров;
  - выбор другого → диалог `Введите пароль`;
  - правильный пароль → переключение;
  - неправильный → **STATE.manager и текущий интерфейс остаются без изменений**.

- `app/web/components/technical_modules/users.py`
  - вместо россыпи цветных кнопок → **один выпадающий список на 32 цвета**;
  - сохранение выбранного цвета;
  - существующие цвета сохраняются при первом запуске;
  - новые менеджеры получают цвет из палитры;
  - пароль менеджера будет редактироваться в настройках.

И отдельно важный момент: **`STATE.manager_colors` больше не должен быть источником истины.** Источник — таблица `users` в `photos.db`; иначе цвета могут расходиться между настройками и переключателем менеджера.

---

### 👤 **User** — 2026-08-19 15:54:11

echo "================ HEADER CURRENT ================" && \
nl -ba app/web/components/header.py | sed -n '105,225p' && \

echo "================ USERS CURRENT 1-140 ================" && \
nl -ba app/web/components/technical_modules/users.py | sed -n '1,140p' && \

echo "================ USERS CURRENT 140-335 ================" && \
nl -ba app/web/components/technical_modules/users.py | sed -n '140,335p' && \

echo "================ USERS DB CURRENT ================" && \
nl -ba app/web/users_db.py | sed -n '1,190p'
================ HEADER CURRENT ================
   105                  z-index: 100000 !important;
   106                  """
   107              )
   108
   109          # ----------------------------------------------------
   110          # USER SWITCHER
   111          # ----------------------------------------------------
   112
   113          def open_user_switcher():
   114
   115              dialog = ui.dialog()
   116
   117              with dialog:
   118
   119                  with ui.card().classes(
   120                      "w-[360px] max-w-[90vw]"
   121                  ):
   122
   123                      ui.label(
   124                          "Выбор пользователя"
   125                      ).classes(
   126                          "text-lg font-bold mb-2"
   127                      )
   128
   129                      user_list = ui.column().classes(
   130                          "w-full gap-1"
   131                      )
   132
   133                      def select_user(
   134                          user_id,
   135                          name,
   136                          color,
   137                      ):
   138
   139                          STATE.user_id = user_id
   140                          STATE.manager = name
   141
   142                          user_button.text = name
   143
   144                          apply_user_color(
   145                              color
   146                          )
   147
   148                          print(
   149                              "[USER SELECT]",
   150                              user_id,
   151                              repr(name),
   152                              color,
   153                              flush=True,
   154                          )
   155
   156                          dialog.close()
   157
   158                      users = get_users()
   159
   160                      with user_list:
   161
   162                          for (
   163                              user_id,
   164                              name,
   165                              color,
   166                              active,
   167                          ) in users:
   168
   169                              with ui.row().classes(
   170                                  "w-full items-center"
   171                              ):
   172
   173                                  # цветовой индикатор
   174                                  ui.element(
   175                                      "div"
   176                                  ).style(
   177                                      f"""
   178                                      width: 14px;
   179                                      height: 14px;
   180                                      min-width: 14px;
   181                                      border-radius: 50%;
   182                                      background: {color};
   183                                      border: 1px solid rgba(0,0,0,.2);
   184                                      """
   185                                  )
   186
   187                                  ui.button(
   188                                      name,
   189                                      on_click=lambda e,
   190                                      uid=user_id,
   191                                      n=name,
   192                                      c=color:
   193                                          select_user(
   194                                              uid,
   195                                              n,
   196                                              c,
   197                                          ),
   198                                  ).props(
   199                                      "flat"
   200                                  ).classes(
   201                                      "flex-grow justify-start"
   202                                  )
   203
   204                      ui.separator().classes(
   205                          "my-2"
   206                      )
   207
   208                      ui.button(
   209                          "Закрыть",
   210                          on_click=dialog.close,
   211                      ).props(
   212                          "flat"
   213                      )
   214
   215              dialog.open()
   216
   217          user_button.on(
   218              "click",
   219              open_user_switcher,
   220          )
   221
   222          # ----------------------------------------------------
   223          # TECHNICAL
   224          # ----------------------------------------------------
   225
================ USERS CURRENT 1-140 ================
     1  from nicegui import ui
     2
     3  from app.web.state import STATE
     4  from app.web.users_db import (
     5      get_users,
     6      add_user,
     7      update_user_name,
     8      update_user_color,
     9      update_user_password,
    10      archive_user,
    11      restore_user,
    12  )
    13
    14
    15  # ============================================================
    16  # FIXED 32-COLOR PALETTE
    17  # ============================================================
    18
    19  USER_COLORS = [
    20      ("Красный", "#E53935"),
    21      ("Розовый", "#D81B60"),
    22      ("Фиолетовый", "#8E24AA"),
    23      ("Тёмно-фиолетовый", "#5E35B1"),
    24      ("Индиго", "#3949AB"),
    25      ("Синий", "#1E88E5"),
    26      ("Голубой", "#039BE5"),
    27      ("Циан", "#00ACC1"),
    28      ("Бирюзовый", "#00897B"),
    29      ("Зелёный", "#43A047"),
    30      ("Светло-зелёный", "#7CB342"),
    31      ("Лайм", "#C0CA33"),
    32      ("Жёлтый", "#FDD835"),
    33      ("Янтарный", "#FFB300"),
    34      ("Оранжевый", "#FB8C00"),
    35      ("Глубокий оранжевый", "#F4511E"),
    36      ("Коричневый", "#6D4C41"),
    37      ("Серо-коричневый", "#8D6E63"),
    38      ("Серый", "#757575"),
    39      ("Сине-серый", "#546E7A"),
    40      ("Бордовый", "#B71C1C"),
    41      ("Тёмно-красный", "#C62828"),
    42      ("Малиновый", "#AD1457"),
    43      ("Тёмно-фиолетовый", "#6A1B9A"),
    44      ("Тёмно-синий", "#283593"),
    45      ("Тёмно-голубой", "#1565C0"),
    46      ("Тёмный циан", "#006064"),
    47      ("Тёмно-зелёный", "#2E7D32"),
    48      ("Тёмно-бирюзовый", "#00695C"),
    49      ("Тёмно-оранжевый", "#EF6C00"),
    50      ("Тёмно-коричневый", "#4E342E"),
    51      ("Тёмно-серый", "#263238"),
    52  ]
    53
    54  COLOR_BY_HEX = {
    55      color.upper(): name
    56      for name, color in USER_COLORS
    57  }
    58
    59
    60  def color_label(color):
    61      return COLOR_BY_HEX.get(
    62          str(color or "").upper(),
    63          str(color or ""),
    64      )
    65
    66
    67  def build_users():
    68
    69      show_archived = {"value": False}
    70
    71      root = ui.column().classes(
    72          "w-full gap-2 px-6 py-3"
    73      )
    74
    75      with root:
    76
    77          # ====================================================
    78          # HEADER
    79          # ====================================================
    80
    81          with ui.row().classes(
    82              "w-full items-center justify-between"
    83          ):
    84
    85              with ui.column().classes("gap-0"):
    86
    87                  ui.label(
    88                      "Пользователи"
    89                  ).classes(
    90                      "text-lg font-bold"
    91                  )
    92
    93                  ui.label(
    94                      "Имя, пароль и цвет интерфейса"
    95                  ).classes(
    96                      "text-xs text-grey-6"
    97                  )
    98
    99              with ui.row().classes(
   100                  "items-center gap-2"
   101              ):
   102
   103                  ui.checkbox(
   104                      "Архив",
   105                      value=False,
   106                      on_change=lambda e:
   107                          toggle_archived(e.value),
   108                  ).props(
   109                      "dense"
   110                  )
   111
   112                  ui.button(
   113                      "Добавить",
   114                      icon="person_add",
   115                      on_click=lambda: add_user_dialog(),
   116                  ).props(
   117                      "outline dense"
   118                  )
   119
   120          ui.separator()
   121
   122          user_list = ui.column().classes(
   123              "w-full gap-1"
   124          )
   125
   126          # ====================================================
   127          # ADD USER
   128          # ====================================================
   129
   130          def add_user_dialog():
   131
   132              with ui.dialog() as dialog:
   133
   134                  with ui.card().classes(
   135                      "w-[420px] max-w-[92vw]"
   136                  ):
   137
   138                      ui.label(
   139                          "Добавить пользователя"
   140                      ).classes(
================ USERS CURRENT 140-335 ================
   140                      ).classes(
   141                          "text-lg font-bold"
   142                      )
   143
   144                      name_input = ui.input(
   145                          "Имя пользователя"
   146                      ).classes(
   147                          "w-full"
   148                      )
   149
   150                      password_input = ui.input(
   151                          "Пароль",
   152                          password=True,
   153                          password_toggle_button=True,
   154                      ).classes(
   155                          "w-full"
   156                      )
   157
   158                      # Для нового пользователя
   159                      selected_color = {
   160                          "value": USER_COLORS[0][1]
   161                      }
   162
   163                      color_select = ui.select(
   164                          options={
   165                              color: name
   166                              for name, color in USER_COLORS
   167                          },
   168                          value=selected_color["value"],
   169                          label="Цвет",
   170                      ).classes(
   171                          "w-full"
   172                      )
   173
   174                      def save():
   175
   176                          name = (
   177                              name_input.value or ""
   178                          ).strip()
   179
   180                          password = (
   181                              password_input.value or ""
   182                          ).strip()
   183
   184                          color = (
   185                              color_select.value
   186                              or selected_color["value"]
   187                          )
   188
   189                          if not name:
   190                              ui.notify(
   191                                  "Введите имя пользователя",
   192                                  type="warning",
   193                              )
   194                              return
   195
   196                          if not password:
   197                              ui.notify(
   198                                  "Введите пароль",
   199                                  type="warning",
   200                              )
   201                              return
   202
   203                          if not add_user(
   204                              name,
   205                              color,
   206                              password,
   207                          ):
   208                              ui.notify(
   209                                  "Такой пользователь уже существует",
   210                                  type="warning",
   211                              )
   212                              return
   213
   214                          dialog.close()
   215                          rebuild()
   216
   217                      with ui.row().classes(
   218                          "w-full justify-end gap-2 mt-2"
   219                      ):
   220
   221                          ui.button(
   222                              "Отмена",
   223                              on_click=dialog.close,
   224                          ).props(
   225                              "flat dense"
   226                          )
   227
   228                          ui.button(
   229                              "Добавить",
   230                              icon="person_add",
   231                              on_click=save,
   232                          ).props(
   233                              "dense"
   234                          )
   235
   236              dialog.open()
   237
   238          # ====================================================
   239          # EDIT USER
   240          # ====================================================
   241
   242          def edit_user(
   243              user_id,
   244              old_name,
   245              old_color,
   246          ):
   247
   248              with ui.dialog() as dialog:
   249
   250                  with ui.card().classes(
   251                      "w-[420px] max-w-[92vw]"
   252                  ):
   253
   254                      ui.label(
   255                          "Настройки пользователя"
   256                      ).classes(
   257                          "text-lg font-bold"
   258                      )
   259
   260                      name_input = ui.input(
   261                          "Имя",
   262                          value=old_name,
   263                      ).classes(
   264                          "w-full"
   265                      )
   266
   267                      password_input = ui.input(
   268                          "Новый пароль",
   269                          password=True,
   270                          password_toggle_button=True,
   271                      ).props(
   272                          "hint='Оставьте пустым, чтобы сохранить текущий пароль'"
   273                      ).classes(
   274                          "w-full"
   275                      )
   276
   277                      color_select = ui.select(
   278                          options={
   279                              color: name
   280                              for name, color in USER_COLORS
   281                          },
   282                          value=old_color,
   283                          label="Цвет",
   284                      ).classes(
   285                          "w-full"
   286                      )
   287
   288                      def save():
   289
   290                          name = (
   291                              name_input.value or ""
   292                          ).strip()
   293
   294                          color = (
   295                              color_select.value
   296                              or old_color
   297                          )
   298
   299                          password = (
   300                              password_input.value or ""
   301                          ).strip()
   302
   303                          if not name:
   304                              ui.notify(
   305                                  "Имя не может быть пустым",
   306                                  type="warning",
   307                              )
   308                              return
   309
   310                          if not update_user_name(
   311                              user_id,
   312                              name,
   313                          ):
   314                              ui.notify(
   315                                  "Такой пользователь уже существует",
   316                                  type="warning",
   317                              )
   318                              return
   319
   320                          if color != old_color:
   321                              update_user_color(
   322                                  user_id,
   323                                  color,
   324                              )
   325
   326                          if password:
   327                              update_user_password(
   328                                  user_id,
   329                                  password,
   330                              )
   331
   332                          if STATE.user_id == user_id:
   333                              STATE.manager = name
   334
   335                          dialog.close()
================ USERS DB CURRENT ================
     1  import sqlite3
     2
     3  from app.web.config import DB_PATH
     4
     5
     6  DEFAULT_USERS = [
     7      ("Вихляева Алена", "#E53935"),
     8      ("Пятницына Диана", "#D81B60"),
     9      ("Аннин Илья", "#8E24AA"),
    10      ("Иванова Елена", "#5E35B1"),
    11      ("Марышева Елена", "#3949AB"),
    12      ("Бутовченко Ольга", "#1E88E5"),
    13      ("Кривошлыкова Ангелина", "#039BE5"),
    14      ("Теплинская Наталья", "#00ACC1"),
    15      ("Папикян Эля", "#00897B"),
    16      ("Путилина Татьяна", "#43A047"),
    17  ]
    18
    19  # Временный пароль для уже существующих пользователей.
    20  # После первого входа его можно изменить в настройках.
    21  INITIAL_PASSWORD = "1234"
    22
    23
    24  def get_connection():
    25      DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    26      return sqlite3.connect(DB_PATH)
    27
    28
    29  def init_users_db():
    30
    31      with get_connection() as con:
    32
    33          con.execute("""
    34              CREATE TABLE IF NOT EXISTS users (
    35                  id INTEGER PRIMARY KEY AUTOINCREMENT,
    36                  name TEXT NOT NULL UNIQUE,
    37                  color TEXT NOT NULL,
    38                  password TEXT NOT NULL DEFAULT '',
    39                  active INTEGER NOT NULL DEFAULT 1,
    40                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    41                  archived_at TEXT
    42              )
    43          """)
    44
    45          # --------------------------------------------------------
    46          # MIGRATION
    47          # --------------------------------------------------------
    48
    49          columns = {
    50              row[1]
    51              for row in con.execute(
    52                  "PRAGMA table_info(users)"
    53              ).fetchall()
    54          }
    55
    56          if "password" not in columns:
    57              con.execute("""
    58                  ALTER TABLE users
    59                  ADD COLUMN password TEXT NOT NULL DEFAULT ''
    60              """)
    61
    62              # Существующие менеджеры получают временный пароль.
    63              con.execute(
    64                  """
    65                  UPDATE users
    66                  SET password = ?
    67                  WHERE password = ''
    68                  """,
    69                  (INITIAL_PASSWORD,),
    70              )
    71
    72          # --------------------------------------------------------
    73          # INITIAL DATA
    74          # --------------------------------------------------------
    75
    76          count = con.execute(
    77              "SELECT COUNT(*) FROM users"
    78          ).fetchone()[0]
    79
    80          if count == 0:
    81              con.executemany(
    82                  """
    83                  INSERT INTO users
    84                      (name, color, password, active)
    85                  VALUES (?, ?, ?, 1)
    86                  """,
    87                  [
    88                      (
    89                          name,
    90                          color,
    91                          INITIAL_PASSWORD,
    92                      )
    93                      for name, color in DEFAULT_USERS
    94                  ],
    95              )
    96
    97          con.commit()
    98
    99
   100  def get_users(active_only=True):
   101
   102      init_users_db()
   103
   104      with get_connection() as con:
   105
   106          if active_only:
   107              rows = con.execute("""
   108                  SELECT id, name, color, active
   109                  FROM users
   110                  WHERE active = 1
   111                  ORDER BY name COLLATE NOCASE
   112              """).fetchall()
   113
   114          else:
   115              rows = con.execute("""
   116                  SELECT id, name, color, active
   117                  FROM users
   118                  ORDER BY active DESC, name COLLATE NOCASE
   119              """).fetchall()
   120
   121      return rows
   122
   123
   124  def get_user_password(user_id):
   125
   126      init_users_db()
   127
   128      with get_connection() as con:
   129          row = con.execute(
   130              """
   131              SELECT password
   132              FROM users
   133              WHERE id = ?
   134              """,
   135              (user_id,),
   136          ).fetchone()
   137
   138      return row[0] if row else None
   139
   140
   141  def check_user_password(user_id, password):
   142
   143      stored = get_user_password(user_id)
   144
   145      if stored is None:
   146          return False
   147
   148      return str(password or "") == str(stored)
   149
   150
   151  def update_user_password(user_id, password):
   152
   153      password = str(password or "")
   154
   155      if not password:
   156          return False
   157
   158      init_users_db()
   159
   160      with get_connection() as con:
   161          con.execute(
   162              """
   163              UPDATE users
   164              SET password = ?
   165              WHERE id = ?
   166              """,
   167              (password, user_id),
   168          )
   169          con.commit()
   170
   171      return True
   172
   173
   174  def add_user(name, color, password=INITIAL_PASSWORD):
   175
   176      name = str(name).strip()
   177      color = str(color or "").strip()
   178      password = str(password or "").strip()
   179
   180      if not name or not color or not password:
   181          return False
   182
   183      init_users_db()
   184
   185      try:
   186          with get_connection() as con:
   187              con.execute(
   188                  """
   189                  INSERT INTO users
   190                      (name, color, password, active)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 15:54:13

> **Вспоминаем**
>
>
> ****
>
> 
>
> **Продолжили Scene Fingerprint, проверили пользователей, импорты и сохранили данные**
>
> 
>
> Обработка заняла 7s

Да. По текущему состоянию база уже **правильно мигрирована**: `users.password` есть, у всех 10 существующих менеджеров сейчас `1234`, а их сохранённые цвета остались прежними.

Но предыдущий патч `header.py` не применился. Поэтому сейчас лучше **не делать ещё один поиск/замену вслепую**, а внести патч по фактическим блокам.

Нужно проверить ещё хвост `users.py`, `users_db.py` и импорты `header.py`. Выполни на `NEURO`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HEADER IMPORTS ================" && \
nl -ba app/web/components/header.py | sed -n '1,35p' && \

echo "================ USERS 330-365 ================" && \
nl -ba app/web/components/technical_modules/users.py | sed -n '330,365p' && \

echo "================ USERS DB 185-260 ================" && \
nl -ba app/web/users_db.py | sed -n '185,260p'
```

После этого я дам **один точный патч**, который сделает сразу всё:

- `password` остаётся обычным текстом в SQLite;
- при выборе другого менеджера появляется окно пароля;
- без правильного пароля `STATE.user_id` и `STATE.manager` **вообще не изменяются**;
- текущий менеджер может сменить себя только после проверки текущего пароля;
- в настройках будет один `select` из 32 цветов;
- старые цвета `#1976D2`, `#2E7D32`, `#263238` и т. д. **не будут перезаписаны**;
- старые менеджеры сохранятся;
- новые менеджеры получат выбранный цвет;
- уберём старый набор из 32 маленьких кнопок и `color_input`, чтобы у менеджера был **ровно один цвет**.

---

### 👤 **User** — 2026-08-19 15:54:42

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HEADER IMPORTS ================" && \
nl -ba app/web/components/header.py | sed -n '1,35p' && \

echo "================ USERS 330-365 ================" && \
nl -ba app/web/components/technical_modules/users.py | sed -n '330,365p' && \

echo "================ USERS DB 185-260 ================" && \
nl -ba app/web/users_db.py | sed -n '185,260p'
================ HEADER IMPORTS ================
     1  from nicegui import ui
     2
     3  from app.web.config import LOGO_PATH
     4  from app.web.state import STATE
     5  from app.web.users_db import (
     6      init_users_db,
     7      get_users,
     8  )
     9  from app.web.components.technical import show_technical
    10
    11
    12  def build_header():
    13
    14      init_users_db()
    15
    16      # ========================================================
    17      # HEADER
    18      # ========================================================
    19
    20      with ui.header().classes(
    21          "items-center justify-between px-4 py-2"
    22      ).style(
    23          "position: relative; z-index: 1000;"
    24      ):
    25
    26          # ----------------------------------------------------
    27          # LEFT
    28          # ----------------------------------------------------
    29
    30          with ui.row().classes(
    31              "items-center gap-3"
    32          ):
    33
    34              if LOGO_PATH.exists():
    35
================ USERS 330-365 ================
   330                              )
   331
   332                          if STATE.user_id == user_id:
   333                              STATE.manager = name
   334
   335                          dialog.close()
   336                          rebuild()
   337
   338                      with ui.row().classes(
   339                          "w-full justify-end gap-2 mt-2"
   340                      ):
   341
   342                          ui.button(
   343                              "Отмена",
   344                              on_click=dialog.close,
   345                          ).props(
   346                              "flat dense"
   347                          )
   348
   349                          ui.button(
   350                              "Сохранить",
   351                              icon="save",
   352                              on_click=save,
   353                          ).props(
   354                              "dense"
   355                          )
   356
   357              dialog.open()
   358
   359          # ====================================================
   360          # ARCHIVE CONFIRMATION
   361          # ====================================================
   362
   363          def confirm_archive(
   364              user_id,
   365              name,
================ USERS DB 185-260 ================
   185      try:
   186          with get_connection() as con:
   187              con.execute(
   188                  """
   189                  INSERT INTO users
   190                      (name, color, password, active)
   191                  VALUES (?, ?, ?, 1)
   192                  """,
   193                  (
   194                      name,
   195                      color,
   196                      password,
   197                  ),
   198              )
   199              con.commit()
   200
   201          return True
   202
   203      except sqlite3.IntegrityError:
   204          return False
   205
   206
   207  def update_user_name(user_id, name):
   208
   209      name = str(name).strip()
   210
   211      if not name:
   212          return False
   213
   214      init_users_db()
   215
   216      try:
   217          with get_connection() as con:
   218              con.execute(
   219                  """
   220                  UPDATE users
   221                  SET name = ?
   222                  WHERE id = ?
   223                  """,
   224                  (name, user_id),
   225              )
   226              con.commit()
   227
   228          return True
   229
   230      except sqlite3.IntegrityError:
   231          return False
   232
   233
   234  def update_user_color(user_id, color):
   235
   236      if not color:
   237          return False
   238
   239      init_users_db()
   240
   241      with get_connection() as con:
   242          con.execute(
   243              """
   244              UPDATE users
   245              SET color = ?
   246              WHERE id = ?
   247              """,
   248              (color, user_id),
   249          )
   250          con.commit()
   251
   252      return True
   253
   254
   255  def archive_user(user_id):
   256
   257      with get_connection() as con:
   258          con.execute(
   259              """
   260              UPDATE users
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

