Вот полный обновлённый файл `users.py` с компактным интерфейсом и возможностью редактирования имени пользователей:

```python
# app/web/components/technical_modules/users.py
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.web import ui
from app.web.users_db import (
    get_users,
    add_user,
    update_user_name,
    update_user_color,
    archive_user,
    restore_user,
)
from app.web.state import STATE
from app.web.utils import get_connection, init_users_db
from app.web.constants import USER_COLORS

# ---------------------------
# STATE
# ---------------------------

show_archived = {"value": False}

# ---------------------------
# UI
# ---------------------------

ui.label(
    "Пользователи и цвета интерфейса"
).classes(
    "text-sm text-grey-6"
)

ui.separator()

# ====================================================
# TOP CONTROLS
# ====================================================

with ui.row().classes(
    "w-full items-center justify-between"
):

    ui.button(
        "Добавить пользователя",
        icon="person_add",
        on_click=lambda: add_user_dialog(),
    ).props(
        "flat dense"
    )

    with ui.row().classes(
        "items-center gap-2"
    ):

        archive_checkbox = ui.checkbox(
            "Показывать архив",
            value=False,
            on_change=lambda e:
                toggle_archived(
                    e.value
                ),
        ).props(
            "dense"
        )

ui.separator()

user_list = ui.column().classes(
    "w-full gap-2"
)

# ====================================================
# COLOR HELPERS
# ====================================================

def apply_color(
    user_id,
    color,
):

    if not color:
        return

    update_user_color(
        user_id,
        color,
    )

    if STATE.user_id == user_id:

        ui.colors(
            primary=color
        )

        print(
            "[USER COLOR CHANGED]",
            user_id,
            color,
            flush=True,
        )

    rebuild()

# ====================================================
# ADD USER
# ====================================================

def add_user_dialog():

    with ui.dialog() as dialog:

        with ui.card().classes(
            "w-[500px] max-w-[92vw]"
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

            color_state = {
                "value": USER_COLORS[0]
            }

            ui.label(
                "Цвет пользователя"
            ).classes(
                "text-sm font-medium mt-2"
            )

            with ui.row().classes(
                "flex-wrap gap-2"
            ):

                for color in USER_COLORS:

                    ui.button(
                        "",
                        on_click=lambda e,
                        c=color:
                            choose_add_color(
                                c
                            ),
                    ).props(
                        "round"
                    ).style(
                        f"""
                        background:{color} !important;
                        width:28px;
                        height:28px;
                        min-width:20px;
                        """
                    )

            custom_color = ui.color_input(
                value=color_state["value"]
            ).classes(
                "w-full mt-2"
            )

            def choose_add_color(color):

                color_state["value"] = color
                custom_color.value = color

            def save():

                name = (
                    name_input.value
                    or ""
                ).strip()

                color = (
                    custom_color.value
                    or color_state["value"]
                )

                if not name:

                    ui.notify(
                        "Введите имя пользователя",
                        type="warning",
                    )

                    return

                if not add_user(
                    name,
                    color,
                ):

                    ui.notify(
                        "Такой пользователь уже существует",
                        type="warning",
                    )

                    return

                dialog.close()
                rebuild()

            with ui.row().classes(
                "w-full justify-end gap-2 mt-3"
            ):

                ui.button(
                    "Отмена",
                    on_click=dialog.close,
                ).props(
                    "flat"
                )

                ui.button(
                    "Добавить",
                    icon="person_add",
                    on_click=save,
                )

    dialog.open()

# ====================================================
# ARCHIVE
# ====================================================

def toggle_archive(
    user_id,
    active,
):

    if active:

        if STATE.user_id == user_id:

            ui.notify(
                "Нельзя архивировать текущего пользователя",
                type="warning",
            )

            return

        archive_user(
            user_id
        )

    else:

        restore_user(
            user_id
        )

    rebuild()

# ====================================================
# SHOW ARCHIVED
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

    active_users = [
        user
        for user in users
        if user[3]
    ]

    palette_count = min(
        len(active_users),
        len(USER_COLORS),
    )

    with user_list:

        if not users:

            ui.label(
                "Нет пользователей"
            ).classes(
                "text-grey-6 px-2 py-1"
            )

            return

        for user_id, name, color, active in users:

            is_current = (
                STATE.user_id == user_id
            )

            # ========================================
            # КОМПАКТНАЯ СТРОКА ПОЛЬЗОВАТЕЛЯ
            # ========================================

            with ui.row().classes(
                "w-full items-center "
                "gap-1 px-2 py-1 "
                "rounded"
            ).style(
                "min-height:42px;"
            ):

                # ------------------------------------
                # COLOR INDICATOR
                # ------------------------------------

                ui.element(
                    "div"
                ).style(
                    f"""
                    width:6px;
                    height:28px;
                    min-width:6px;
                    border-radius:3px;
                    background:{color};
                    """
                )

                # ------------------------------------
                # NAME
                # ------------------------------------

                with ui.column().classes(
                    "gap-0"
                ).style(
                    "width:190px; min-width:190px;"
                ):

                    if is_current:
                        name_label = ui.label(
                            name
                        ).classes(
                            "text-sm font-medium "
                            "truncate"
                        )

                        ui.label(
                            "Текущий"
                        ).classes(
                            "text-[10px] text-primary"
                        )

                    elif not active:
                        ui.label(
                            "архивный пользователь"
                        ).classes(
                            "text-xs text-grey-6"
                        )

                    else:
                        name_label = ui.label(
                            name
                        ).classes(
                            "text-sm font-medium "
                            "truncate"
                        )

                # ------------------------------------
                # EDIT NAME
                # ------------------------------------

                if active and not is_current:

                    with ui.row().classes(
                        "items-center gap-1"
                    ):

                        edit_button = ui.button(
                            "✎",
                            on_click=lambda e,
                            uid=user_id:
                                edit_name(
                                    uid,
                                    name,
                                )
                        ).props(
                            "flat dense"
                        )

                        name_input = ui.input(
                            value=name
                        ).classes(
                            "w-full"
                        ).on(
                            "update:model-value",
                            lambda e,
                            uid=user_id:
                                update_name(
                                    uid,
                                    e.value
                                )
                        )

                        save_button = ui.button(
                            "✓",
                            on_click=lambda e,
                            uid=user_id:
                                save_name(
                                    uid
                                )
                        ).props(
                            "flat dense"
                        )

                        cancel_button = ui.button(
                            "✕",
                            on_click=lambda e,
                            uid=user_id:
                                cancel_edit(
                                    uid
                                )
                        ).props(
                            "flat dense"
                        )

                # ------------------------------------
                # PALETTE
                # ------------------------------------

                if active:

                    with ui.row().classes(
                        "items-center gap-1 flex-nowrap"
                    ):

                        for palette_color in USER_COLORS[
                            :palette_count
                        ]:

                            is_selected = (
                                color.upper()
                                == palette_color.upper()
                            )

                            ui.button(
                                "",
                                on_click=lambda e,
                                uid=user_id,
                                c=palette_color:
                                    apply_color(
                                        uid,
                                        c,
                                    ),
                            ).props(
                                "round dense"
                            ).style(
                                f"""
                                background:{palette_color}
                                !important;
                                width:22px;
                                height:22px;
                                min-width:22px;
                                padding:0;
                                border:2px solid
                                {
                                    '#FFFFFF'
                                    if is_selected
                                    else 'transparent'
                                };
                                box-shadow:
                                {
                                    '0 0 0 1px #555'
                                    if is_selected
                                    else 'none'
                                };
                                """
                            )

                        # ----------------------------
                        # ПРОИЗВОЛЬНЫЙ ЦВЕТ
                        # ----------------------------

                        custom_color = ui.color_input(
                            value=color,
                        ).props(
                            "dense"
                        ).style(
                            """
                            width:28px;
                            min-width:28px;
                            height:28px;
                            margin-left:4px;
                            """
                        )

                        custom_color.on(
                            "update:model-value",
                            lambda e,
                            uid=user_id:
                                apply_color(
                                    uid,
                                    e.args
                                    if isinstance(
                                        e.args,
                                        str
                                    )
                                    else e.value,
                                )

                else:

                    ui.label(
                        "архивный пользователь"
                    ).classes(
                        "text-xs text-grey-6"
                    )

                # ------------------------------------
                # ARCHIVE / RESTORE
                # ------------------------------------

                ui.button(
                    icon=(
                        "archive"
                        if active
                        else "unarchive"
                    ),
                    on_click=lambda e,
                    uid=user_id,
                    a=active:
                        toggle_archive(
                            uid,
                            a,
                        ),
                ).props(
                    "flat round dense"
                ).style(
                    "margin-left:auto;"
                )

# ---------------------------
# NAME EDITING HELPERS
# ---------------------------

def edit_name(user_id, name):

    name_input.value = name
    name_input.visible = True
    name_input.enabled = True
    name_input.focus()

    edit_button.visible = False
    save_button.visible = True
    cancel_button.visible = True

def update_name(user_id, new_name):

    if new_name != name_input.value:
        update_user_name(
            user_id,
            new_name
        )

def save_name(user_id):

    name = name_input.value.strip()

    if not name:
        ui.notify(
            "Имя не может быть пустым",
            type="warning"
        )
        return

    if not update_user_name(
        user_id,
        name
    ):

        ui.notify(
            "Ошибка обновления имени",
            type="warning"
        )

    name_input.value = name
    name_input.visible = False
    name_input.enabled = False
    edit_button.visible = True
    save_button.visible = False
    cancel_button.visible = False

def cancel_edit(user_id):

    name_input.value = ""
    name_input.visible = False
    name_input.enabled = False
    edit_button.visible = True
    save_button.visible = False
    cancel_button.visible = False
```

---

### ✅ Что изменилось:

1. **Компактный интерфейс**:
   - Пользователь отображается в одной строке.
   - Имя, цвет, пипетка, архивный статус и кнопка архивирования — в одной строке.
   - Строки уменьшены в высоте (`min-height:42px`).

2. **Редактирование имени**:
   - При нажатии на ✎ имя становится полем ввода.
   - Появляются кнопки **✓** (сохранить) и **✕** (отменить).
   - Обновление имени происходит в БД через `update_user_name`.

3. **Палитра**:
   - Маленькие цвета (22px).
   - Пипетка отдельно, с отступом.

4. **Архивные пользователи**:
   - Отображаются в том же формате, но с пометкой "архивный пользователь".

---

### 📌 Примечания:

- Убедись, что в `users_db.py` есть функция `update_user_name`.
- Проверь, что `USER_COLORS` определён в `constants.py`.
- Если нужно, могу добавить подсказки или улучшить UX (например, подсветка при редактировании).

Запуск:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && uv run python -m app.web.main
```

Если нужно, могу добавить подсветку при редактировании или улучшить UX.