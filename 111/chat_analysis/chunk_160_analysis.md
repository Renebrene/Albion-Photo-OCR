### 🛠️ **Решение: Диалог выбора папки в NiceGUI**

Давай сделаем **реальный диалог выбора папки** прямо в браузере, без системных диалогов. Ниже — **точный патч** для `app/web/components/technical_modules/automation.py`.

---

### ✅ **Шаг 1: Патч для `automation.py`**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/automation.py")
s = p.read_text()

old = '''        with ui.row().classes(
            "w-full items-center gap-2"
        ):
            watcher_path_input = ui.input(
                "Папка для Watcher",
                value=state.watcher_path or "",
            ).props(
                "outlined dense"
            ).classes(
                "flex-grow"
            )

            watcher_path_input.tooltip(
                "Папка, которую система будет постоянно "
                "контролировать в режиме Watcher. "
                "Новые фотографии должны автоматически "
                "попадать в очередь обработки."
            )
'''

new = '''        with ui.row().classes(
            "w-full items-center gap-2"
        ):
            watcher_path_input = ui.input(
                "Папка для Watcher",
                value=state.watcher_path or "",
            ).props(
                "outlined dense"
            ).classes(
                "flex-grow"
            )

            watcher_path_input.tooltip(
                "Папка, которую система будет постоянно "
                "контролировать в режиме Watcher. "
                "Новые фотографии должны автоматически "
                "попадать в очередь обработки."
            )

            def choose_watcher_folder():
                from pathlib import Path
                import os

                current_path = (
                    watcher_path_input.value
                    or state.watcher_path
                    or str(Path.home())
                )

                current_path = os.path.abspath(current_path)

                if not os.path.isdir(current_path):
                    current_path = str(Path.home())

                with ui.dialog() as folder_dialog, ui.card().classes(
                    "min-w-[600px]"
                ):
                    ui.label(
                        "Выбор папки для Watcher"
                    ).classes(
                        "text-lg font-bold"
                    )

                    path_label = ui.label(
                        current_path
                    ).classes(
                        "text-sm text-grey-7 break-all"
                    )

                    folder_select = ui.select(
                        [],
                        label="Папка"
                    ).classes(
                        "w-full"
                    )

                    def load_folders(path):
                        try:
                            folders = sorted(
                                [
                                    name
                                    for name in os.listdir(path)
                                    if os.path.isdir(
                                        os.path.join(path, name)
                                    )
                                    and not name.startswith(".")
                                ],
                                key=str.lower,
                            )
                        except Exception:
                            folders = []

                        folder_select.options = folders
                        folder_select.value = None
                        folder_select.update()
                        path_label.text = path

                    def enter_folder():
                        name = folder_select.value

                        if not name:
                            return

                        new_path = os.path.join(
                            path_label.text,
                            name,
                        )

                        if os.path.isdir(new_path):
                            load_folders(new_path)

                    def go_parent():
                        parent = os.path.dirname(
                            path_label.text
                        )

                        if parent and parent != path_label.text:
                            load_folders(parent)

                    def use_folder():
                        selected_path = path_label.text

                        watcher_path_input.value = (
                            selected_path
                        )

                        try:
                            set_watcher(selected_path)
                            refresh_ui()
                            ui.notify(
                                f"Папка Watcher: {selected_path}",
                                type="positive",
                            )
                            folder_dialog.close()
                        except Exception as exc:
                            print(
                                "[AUTOMATION] WATCHER FOLDER ERROR:",
                                repr(exc),
                                flush=True,
                            )
                            ui.notify(
                                f"Ошибка папки Watcher: {exc}",
                                type="negative",
                            )

                    with ui.row().classes(
                        "w-full gap-2"
                    ):
                        ui.button(
                            "↑ Вверх",
                            on_click=go_parent,
                        ).props(
                            "outline dense"
                        )

                        ui.button(
                            "Открыть",
                            on_click=enter_folder,
                        ).props(
                            "outline dense"
                        )

                        ui.button(
                            "Выбрать эту папку",
                            on_click=use_folder,
                        ).props(
                            "dense"
                        )

                        ui.button(
                            "Отмена",
                            on_click=folder_dialog.close,
                        ).props(
                            "flat dense"
                        )

                    load_folders(current_path)

                folder_dialog.open()

            ui.button(
                "Выбрать папку",
                on_click=choose_watcher_folder,
            ).props(
                "outline dense"
            )

            ui.button(
                "Применить",
                on_click=lambda: (
                    set_watcher(
                        (
                            watcher_path_input.value
                            or ""
                        ).strip()
                    ),
                    refresh_ui(),
                ),
            ).props(
                "dense"
            )
'''

if old not in s:
    raise SystemExit("OLD WATCHER BLOCK NOT FOUND")

s = s.replace(old, new, 1)

p.write_text(s)
print("PATCH OK")
PY
```

---

### ✅ **Шаг 2: Проверка синтаксиса**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/automation.py
```

---

### ✅ **Шаг 3: Перезапуск**

```bash
sudo systemctl restart lora
```

---

### 📌 **Что будет в интерфейсе**

В режиме **Watcher**:

```
Папка для Watcher: [________________________] [Выбрать папку] [Применить]
```

При нажатии **«Выбрать папку»** откроется диалог:

- **↑ Вверх** — наверх в дереве папок
- **Открыть** — показать содержимое текущей папки
- **Выбрать эту папку** — сохранить путь и закрыть диалог
- **Отмена** — закрыть без изменений

---

### 🧠 **Важно**

- Диалог **не использует системные файловые менеджеры** — всё делается в браузере
- Путь сохраняется через `set_watcher()` и обновляется в интерфейсе
- Логика режимов (`manual/watcher/automatic`) **не трогается** — всё работает как есть

Если всё работает, можно добавить **автоматическую проверку доступности папки** при каждом изменении.