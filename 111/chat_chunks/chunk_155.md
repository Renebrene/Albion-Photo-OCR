## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 👤 **User** — 2026-08-19 01:29:55

# ============================================================
    # INITIAL STATE
    # ============================================================

    stop_all_button.disable()
    dino_stop_button.disable()
    qwen_stop_button.disable()

    # ============================================================
    # PERIODIC REFRESH
    # ============================================================

    ui.timer(
        1.0,
        update_stats,
    )

    # Первое заполнение сразу
    update_stats()
================ TECHNICAL TABS ================
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:29:57

Да, вот теперь нашли: **отдельная вкладка Qwen всё ещё есть в `technical.py`**. Предыдущий `grep` показал `ui.tab`, но мы не видели строки содержимого.

Нужно удалить **только этот блок**:

```python
ui.tab(
    "qwen",
    label="Qwen",
    icon="smart_toy",
)
```

А `build_qwen()` панели уже нет — поэтому после удаления вкладки ничего дополнительного в `technical.py` не требуется.

Сделаем автоматически и сразу проверим:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical.py")
text = p.read_text()

old = '''                ui.tab(
                    "qwen",
                    label="Qwen",
                    icon="smart_toy",
                )

'''

if old not in text:
    print("QWEN TAB BLOCK NOT FOUND")
else:
    text = text.replace(old, "", 1)
    p.write_text(text)
    print("OK: Qwen tab removed")
PY

echo "================ CHECK ================"

grep -nE 'ui\.tab\(|ui\.tab_panel\(|"qwen"|label="Qwen"' \
app/web/components/technical.py || true

echo "================ SYNTAX ================"

uv run python -m py_compile \
app/web/components/technical.py \
app/web/components/technical_modules/automation.py
```

Ожидаем:

```text
OK: Qwen tab removed
```

и в `technical.py` **вообще не должно быть**:

```text
"qwen"
label="Qwen"
```

При этом Qwen в `photo_processing.py` **не удаляем** — там он должен остаться как отдельный процесс внутри общей вкладки **«Обработка фото»**.

После этого уже займёмся самой вкладкой **«Автоматизация»** и свяжем её с тремя режимами запуска.

---

### 👤 **User** — 2026-08-19 01:30:20

app/web/components/technical_modules/automation.pyQwen"' \
OK: Qwen tab removed
================ CHECK ================
153:                ui.tab(
159:                ui.tab(
165:                ui.tab(
171:                ui.tab(
177:                ui.tab(
183:                ui.tab(
189:                ui.tab(
212:                    with ui.tab_panel("photo_processing"):
215:                    with ui.tab_panel("last_run"):
218:                    with ui.tab_panel("automation"):
222:                    with ui.tab_panel("data"):
225:                    with ui.tab_panel("system"):
228:                    with ui.tab_panel("fingerprints"):
231:                    with ui.tab_panel("users"):
================ SYNTAX ================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:30:21

Отлично. Фиксируем этот этап:

- отдельной вкладки **Qwen** больше нет;
- `Qwen` остаётся внутри **«Обработка фото»**;
- `technical.py` синтаксически корректен;
- новый `automation.py` тоже синтаксически корректен;
- DINO/Qwen workers пока не трогали.

Теперь логичный следующий шаг — **привести саму «Обработку фото» к нашей общей схеме запуска**.

Сначала посмотрим текущий блок целиком, чтобы не ломать уже работающие кнопки и статистику:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,360p' app/web/components/technical_modules/photo_processing.py && \
echo "================ UI / BUTTONS ================" && \
sed -n '360,1040p' app/web/components/technical_modules/photo_processing.py
```

Особенно нас интересует, как сейчас устроены:

- `ЗАПУСТИТЬ`;
- `ОСТАНОВИТЬ`;
- DINO;
- Qwen;
- `running`;
- `stop_requested`;
- обновление прогресса.

**Пока ничего не меняем.** По этому выводу я соберу финальную схему, чтобы общий запуск действительно запускал оба независимых worker-а, а Watcher/Automatic управляли только способом запуска.

---

### 👤 **User** — 2026-08-19 01:30:58

from nicegui import ui

from app.web.photo_db import get_processing_stats

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"

UV = Path.home() / ".local" / "bin" / "uv"

DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
QWEN_WORKER = PROJECT / "app" / "workers" / "qwen_worker.py"

DEFAULT_SOURCE = (
    PROJECT
    / "data"
    / "input"
    / "daily"
)

DEFAULT_RESULT = (
    PROJECT
    / "data"
    / "output"
    / "daily"
)

def build_photo_processing():

    # ============================================================
    # PROCESS STATE
    # ============================================================

    dino_process = None
    qwen_process = None

    dino_stopping = False
    qwen_stopping = False

    # ============================================================
    # HELPERS
    # ============================================================

    def process_running(process):
        return (
            process is not None
            and process.returncode is None
        )

    def set_indicator(label, state):
        """
        state:
            ready
            working
            error
            stopped
        """

        label.classes(
            remove=(
                "text-positive "
                "text-warning "
                "text-negative "
                "text-grey-7"
            )
        )

        if state == "working":
            label.text = "● Идёт обработка"
            label.classes(add="text-warning")

        elif state == "error":
            label.text = "● Ошибка"
            label.classes(add="text-negative")

        elif state == "stopped":
            label.text = "● Остановлено"
            label.classes(add="text-grey-7")

        else:
            label.text = "● Готово"
            label.classes(add="text-positive")

    def set_branch_indicator(label, running, error=False):
        label.classes(
            remove=(
                "text-positive "
                "text-warning "
                "text-negative "
                "text-grey-7"
            )
        )

        if error:
            label.text = "● Ошибка"
            label.classes(add="text-negative")

        elif running:
            label.text = "● Работает"
            label.classes(add="text-warning")

        else:
            label.text = "● Готово"
            label.classes(add="text-positive")

    # ============================================================
    # STATISTICS
    # ============================================================

    def update_stats():

        try:
            data = get_processing_stats()

        except Exception as exc:

            overall_label.text = "● Ошибка БД"
            overall_label.classes(
                remove="text-positive text-warning text-negative"
            )
            overall_label.classes(
                add="text-negative"
            )

            db_error_label.text = str(exc)[:200]

            return

        db_error_label.text = ""

        total = int(data.get("total", 0))

        dino = data.get("dino", {})
        qwen = data.get("qwen", {})

        # --------------------------------------------------------
        # DINO
        # --------------------------------------------------------

        dino_done = int(dino.get("done", 0))
        dino_processing = int(
            dino.get("processing", 0)
        )
        dino_pending = int(
            dino.get("pending", 0)
        )
        dino_error = int(
            dino.get("error", 0)
        )

        dino_finished = (
            dino_done + dino_error
        )

        dino_progress = (
            min(
                100,
                int(
                    dino_finished
                    / total
                    * 100
                ),
            )
            if total
            else 0
        )

        dino_progress_bar.value = (
            dino_progress / 100
        )

        dino_progress_label.text = (
            f"{dino_finished} / {total}"
        )

        dino_done_label.text = str(
            dino_done
        )

        dino_processing_label.text = str(
            dino_processing
        )

        dino_pending_label.text = str(
            dino_pending
        )

        dino_error_label.text = str(
            dino_error
        )

        # --------------------------------------------------------
        # QWEN
        # --------------------------------------------------------

        qwen_done = int(qwen.get("done", 0))
        qwen_processing = int(
            qwen.get("processing", 0)
        )
        qwen_pending = int(
            qwen.get("pending", 0)
        )
        qwen_error = int(
            qwen.get("error", 0)
        )

        qwen_finished = (
            qwen_done + qwen_error
        )

        qwen_progress = (
            min(
                100,
                int(
                    qwen_finished
                    / total
                    * 100
                ),
            )
            if total
            else 0
        )

        qwen_progress_bar.value = (
            qwen_progress / 100
        )

        qwen_progress_label.text = (
            f"{qwen_finished} / {total}"
        )

        qwen_done_label.text = str(
            qwen_done
        )

        qwen_processing_label.text = str(
            qwen_processing
        )

        qwen_pending_label.text = str(
            qwen_pending
        )

        qwen_error_label.text = str(
            qwen_error
        )

        # --------------------------------------------------------
        # BRANCH STATES
        # --------------------------------------------------------

        dino_running = process_running(
            dino_process
        )

        qwen_running = process_running(
            qwen_process
        )

        set_branch_indicator(
            dino_status_label,
            dino_running,
            dino_error > 0,
        )

        set_branch_indicator(
            qwen_status_label,
            qwen_running,
            qwen_error > 0,
        )

        # --------------------------------------------------------
        # MAIN STATE
        # --------------------------------------------------------

        if dino_running or qwen_running:

            set_indicator(
                overall_label,
                "working",
            )

        elif dino_error or qwen_error:

            set_indicator(
                overall_label,
                "error",
            )

        else:

            set_indicator(
                overall_label,
                "ready",
            )

        # --------------------------------------------------------
        # BUTTONS
        # --------------------------------------------------------

        run_all_button.enabled = not (
            dino_running
            or qwen_running
        )

        stop_all_button.enabled = (
            dino_running
            or qwen_running
        )

        dino_run_button.enabled = not (
            dino_running
        )

        dino_stop_button.enabled = (
            dino_running
        )

        qwen_run_button.enabled = not (
            qwen_running
        )

        qwen_stop_button.enabled = (
            qwen_running
        )

    # ============================================================
    # PROCESS OUTPUT
    # ============================================================

    async def consume_output(process, prefix):

        if process is None:
            return

        if process.stdout is None:
            return

        try:

            while True:

                line = await process.stdout.readline()

                if not line:
                    break

                text = (
                    line
                    .decode(
                        "utf-8",
                        errors="replace",
                    )
                    .strip()
                )
================ UI / BUTTONS ================
                )

                if text:
                    print(
                        f"[{prefix}] {text}",
                        flush=True,
                    )

        except Exception as exc:

            print(
                f"[{prefix}] OUTPUT ERROR: {exc}",
                flush=True,
            )

    # ============================================================
    # START DINO
    # ============================================================

    async def start_dino():

        nonlocal dino_process
        nonlocal dino_stopping

        if process_running(dino_process):
            return

        if not UV.exists():

            ui.notify(
                f"Не найден uv: {UV}",
                type="negative",
                timeout=8000,
            )

            return

        if not DINO_WORKER.exists():

            ui.notify(
                f"Не найден DINO worker: {DINO_WORKER}",
                type="negative",
                timeout=8000,
            )

            return

        dino_stopping = False

        try:

            env = {
                "PATH": (
                    f"{Path.home() / '.local/bin'}:"
                    "/usr/local/sbin:"
                    "/usr/local/bin:"
                    "/usr/sbin:"
                    "/usr/bin:"
                    "/sbin:"
                    "/bin"
                ),
                "HOME": str(Path.home()),
                "PYTHONUNBUFFERED": "1",
            }

            dino_process = (
                await asyncio.create_subprocess_exec(
                    str(UV),
                    "run",
                    "python",
                    str(DINO_WORKER),
                    cwd=str(PROJECT),
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
            )

            print(
                f"[WEB] DINO START PID={dino_process.pid}",
                flush=True,
            )

            asyncio.create_task(
                consume_output(
                    dino_process,
                    "DINO",
                )
            )

            ui.notify(
                "DINO запущен",
                type="positive",
                timeout=3000,
            )

        except Exception as exc:

            dino_process = None

            print(
                "[WEB] DINO START ERROR:",
                repr(exc),
                flush=True,
            )

            ui.notify(
                f"Ошибка запуска DINO: {exc}",
                type="negative",
                timeout=8000,
            )

    # ============================================================
    # STOP DINO
    # ============================================================

    async def stop_dino():

        nonlocal dino_stopping

        if not process_running(dino_process):
            return

        dino_stopping = True

        try:

            dino_process.terminate()

            ui.notify(
                "DINO останавливается",
                type="warning",
                timeout=3000,
            )

        except ProcessLookupError:
            pass

        except Exception as exc:

            ui.notify(
                f"Ошибка остановки DINO: {exc}",
                type="negative",
                timeout=8000,
            )

    # ============================================================
    # START QWEN
    # ============================================================

    async def start_qwen():

        nonlocal qwen_process
        nonlocal qwen_stopping

        if process_running(qwen_process):
            return

        if not UV.exists():

            ui.notify(
                f"Не найден uv: {UV}",
                type="negative",
                timeout=8000,
            )

            return

        if not QWEN_WORKER.exists():

            ui.notify(
                f"Не найден Qwen worker: {QWEN_WORKER}",
                type="negative",
                timeout=8000,
            )

            return

        qwen_stopping = False

        try:

            env = {
                "PATH": (
                    f"{Path.home() / '.local/bin'}:"
                    "/usr/local/sbin:"
                    "/usr/local/bin:"
                    "/usr/sbin:"
                    "/usr/bin:"
                    "/sbin:"
                    "/bin"
                ),
                "HOME": str(Path.home()),
                "PYTHONUNBUFFERED": "1",
            }

            qwen_process = (
                await asyncio.create_subprocess_exec(
                    str(UV),
                    "run",
                    "python",
                    str(QWEN_WORKER),
                    cwd=str(PROJECT),
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
            )

            print(
                f"[WEB] QWEN START PID={qwen_process.pid}",
                flush=True,
            )

            asyncio.create_task(
                consume_output(
                    qwen_process,
                    "QWEN",
                )
            )

            ui.notify(
                "Qwen запущен",
                type="positive",
                timeout=3000,
            )

        except Exception as exc:

            qwen_process = None

            print(
                "[WEB] QWEN START ERROR:",
                repr(exc),
                flush=True,
            )

            ui.notify(
                f"Ошибка запуска Qwen: {exc}",
                type="negative",
                timeout=8000,
            )

    # ============================================================
    # STOP QWEN
    # ============================================================

    async def stop_qwen():

        nonlocal qwen_stopping

        if not process_running(qwen_process):
            return

        qwen_stopping = True

        try:

            qwen_process.terminate()

            ui.notify(
                "Qwen останавливается",
                type="warning",
                timeout=3000,
            )

        except ProcessLookupError:
            pass

        except Exception as exc:

            ui.notify(
                f"Ошибка остановки Qwen: {exc}",
                type="negative",
                timeout=8000,
            )

    # ============================================================
    # START ALL
    # ============================================================

    async def start_all():

        await start_dino()

        await asyncio.sleep(0.2)

        await start_qwen()

    # ============================================================
    # STOP ALL
    # ============================================================

    async def stop_all():

        await stop_dino()

        await stop_qwen()

    # ============================================================
    # SOURCE PICKER
    # ============================================================

    async def choose_source():

        ui.notify(
            "Укажите папку источника в поле выше.",
            type="info",
            timeout=3000,
        )

    # ============================================================
    # UI
    # ============================================================

    with ui.card().classes(
        "w-full"
    ):

        # --------------------------------------------------------
        # TITLE
        # --------------------------------------------------------

        ui.label(
            "ФОТООБРАБОТКА"
        ).classes(
            "text-lg font-bold"
        )

        ui.label(
            "Параллельная обработка фотографий"
        ).classes(
            "text-sm text-grey-6"
        )

        ui.separator().classes(
            "my-3"
        )

        # --------------------------------------------------------
        # SOURCE / RESULT
        # --------------------------------------------------------

        with ui.row().classes(
            "w-full items-center gap-3"
        ):

            ui.label(
                "Источник"
            ).classes(
                "text-sm font-medium whitespace-nowrap"
            )

            source_input = ui.input(
                value=str(DEFAULT_SOURCE)
            ).props(
                "outlined dense"
            ).classes(
                "flex-1"
            )

            source_button = ui.button(
                "Выбрать",
                icon="folder_open",
                on_click=choose_source,
            ).props(
                "outline dense"
            )

            ui.label(
                "Результат"
            ).classes(
                "text-sm font-medium whitespace-nowrap ml-3"
            )

            output_input = ui.input(
                value=str(DEFAULT_RESULT)
            ).props(
                "outlined dense readonly"
            ).classes(
                "flex-1"
            )

        # --------------------------------------------------------
        # MAIN CONTROLS
        # --------------------------------------------------------

        with ui.row().classes(
            "w-full items-center gap-3 mt-4"
        ):

            run_all_button = ui.button(
                "▶  ЗАПУСТИТЬ",
                on_click=start_all,
            ).props(
                "unelevated"
            ).classes(
                "flex-1"
            )

            stop_all_button = ui.button(
                "■  ОСТАНОВИТЬ",
                on_click=stop_all,
            ).props(
                "outline color=negative"
            ).classes(
                "flex-1"
            )

        # --------------------------------------------------------
        # MAIN STATUS
        # --------------------------------------------------------

        with ui.row().classes(
            "w-full justify-center items-center mt-3"
        ):

            overall_label = ui.label(
                "● Готово"
            ).classes(
                "text-sm text-positive font-medium"
            )

        db_error_label = ui.label().classes(
            "text-xs text-negative"
        )

        # ========================================================
        # DINO
        # ========================================================

        ui.separator().classes(
            "my-3"
        )

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            with ui.column().classes(
                "gap-0"
            ):

                ui.label(
                    "DINO v33 / Hybrid v12"
                ).classes(
                    "font-bold"
                )

                dino_status_label = ui.label(
                    "● Готово"
                ).classes(
                    "text-xs text-positive"
                )

            with ui.row().classes(
                "items-center gap-2"
            ):

                dino_run_button = ui.button(
                    "▶ Запустить",
                    on_click=start_dino,
                ).props(
                    "dense unelevated"
                )

                dino_stop_button = ui.button(
                    "■ Остановить",
                    on_click=stop_dino,
                ).props(
                    "dense outline color=negative"
                )

        with ui.row().classes(
            "w-full items-center gap-3 mt-2"
        ):

            dino_progress_bar = ui.linear_progress(
                value=0
            ).props(
                "instant-feedback"
            ).classes(
                "flex-1"
            )

            dino_progress_label = ui.label(
                "0 / 0"
            ).classes(
                "text-sm whitespace-nowrap"
            )

        with ui.row().classes(
            "w-full justify-between text-sm mt-2"
        ):

            with ui.row().classes("gap-1"):
                ui.label("Готово:")
                dino_done_label = ui.label("0").classes(
                    "font-medium"
                )

            with ui.row().classes("gap-1"):
                ui.label("В работе:")
                dino_processing_label = ui.label("0").classes(
                    "font-medium"
                )

            with ui.row().classes("gap-1"):
                ui.label("В очереди:")
                dino_pending_label = ui.label("0").classes(
                    "font-medium"
                )

            with ui.row().classes("gap-1"):
                ui.label("Ошибки:")
                dino_error_label = ui.label("0").classes(
                    "font-medium"
                )

        # ========================================================
        # QWEN
        # ========================================================

        ui.separator().classes(
            "my-3"
        )

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            with ui.column().classes(
                "gap-0"
            ):

                ui.label(
                    "Qwen3-VL 4B"
                ).classes(
                    "font-bold"
                )

                qwen_status_label = ui.label(
                    "● Готово"
                ).classes(
                    "text-xs text-positive"
                )

            with ui.row().classes(
                "items-center gap-2"
            ):

                qwen_run_button = ui.button(
                    "▶ Запустить",
                    on_click=start_qwen,
                ).props(
                    "dense unelevated"
                )

                qwen_stop_button = ui.button(
                    "■ Остановить",
                    on_click=stop_qwen,
                ).props(
                    "dense outline color=negative"
                )

        with ui.row().classes(
            "w-full items-center gap-3 mt-2"
        ):

            qwen_progress_bar = ui.linear_progress(
                value=0
            ).props(
                "instant-feedback"
            ).classes(
                "flex-1"
            )

            qwen_progress_label = ui.label(
                "0 / 0"
            ).classes(
                "text-sm whitespace-nowrap"
            )

        with ui.row().classes(
            "w-full justify-between text-sm mt-2"
        ):

            with ui.row().classes("gap-1"):
                ui.label("Готово:")
                qwen_done_label = ui.label("0").classes(
                    "font-medium"
                )

            with ui.row().classes("gap-1"):
                ui.label("В работе:")
                qwen_processing_label = ui.label("0").classes(
                    "font-medium"
                )

            with ui.row().classes("gap-1"):
                ui.label("В очереди:")
                qwen_pending_label = ui.label("0").classes(
                    "font-medium"
                )

            with ui.row().classes("gap-1"):
                ui.label("Ошибки:")
                qwen_error_label = ui.label("0").classes(
                    "font-medium"
                )

        # --------------------------------------------------------
        # FOOTER
        # --------------------------------------------------------

        ui.separator().classes(
            "my-3"
        )

        ui.label(
            "DINO и Qwen работают независимо. "
            "Состояние очередей определяется по PostgreSQL."
        ).classes(
            "text-xs text-grey-6"
        )

    # ============================================================
    # INITIAL STATE
    # ============================================================

    stop_all_button.disable()
    dino_stop_button.disable()
    qwen_stop_button.disable()

    # ============================================================
    # PERIODIC REFRESH
    # ============================================================

    ui.timer(
        1.0,
        update_stats,
    )

    # Первое заполнение сразу
    update_stats()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:31:00

Да. Теперь картина полная.

**Следующий шаг — не трогать DINO/Qwen workers и не переписывать весь `photo_processing.py`.** У нас уже есть хорошая основа: два независимых процесса, PostgreSQL-очереди и `controller.py` с тремя режимами.

Но сейчас есть 3 несоответствия нашей зафиксированной архитектуре:

1. `automation.py` пока показывает старую модель — один checkbox «Автоматическая обработка».
2. `controller.py` уже умеет `manual / automatic / watcher`, но UI Watcher фактически не подключён.
3. `photo_processing.py` запускает процессы напрямую и **не учитывает режим**. Поэтому сейчас DINO/Qwen кнопки будут доступны даже в `automatic/watcher`.

### Что предлагаю сделать сейчас

**Шаг 1 — привести `automation.py` к новой модели:**

```text
РЕЖИМ ЗАПУСКА

(●) Ручной
( ) Watcher
( ) Автоматический

Время запуска: [02:00]
```

с tooltip'ами, которые мы зафиксировали.

При выборе:

- Manual → `set_manual()`
- Watcher → `set_watcher(path)`
- Automatic → `set_automatic(time)`

И UI сразу обновляет состояние кнопок.

---

**Шаг 2 — связать `photo_processing.py` с `controller.py`.**

В начале:

```python
from app.pipeline.controller import (
    get_state,
    start_manual,
    request_stop,
    finish_stop,
)
```

И логика кнопок:

```text
manual
 ├── DINO Запустить       ENABLE
 ├── Qwen Запустить       ENABLE
 └── Общее Запустить      ENABLE

watcher
 ├── DINO Запустить       DISABLE
 ├── Qwen Запустить       DISABLE
 └── Общее Запустить      DISABLE

automatic
 ├── DINO Запустить       DISABLE
 ├── Qwen Запустить       DISABLE
 └── Общее Запустить      DISABLE
```

При ручном `ЗАПУСТИТЬ` сначала фиксируем запуск в `pipeline_control`, затем стартуем **оба независимых worker'а**.

---

### Шаг 3 — самое важное

Сейчас `stop_all()` делает:

```python
await stop_dino()
await stop_qwen()
```

Но это только убивает процессы.

Нужно сделать:

```text
ОСТАНОВИТЬ
       ↓
request_stop()
       ↓
DINO/Qwen корректно завершаются
       ↓
pending остаются pending
       ↓
finish_stop()
       ↓
mode = manual
```

То есть твой уже существующий:

```python
request_stop()
finish_stop()
```

как раз для этого и предназначен.

---

### И ещё один важный момент

`recovery.py` уже практически соответствует нашей архитектуре:

```text
DINO processing → pending
Qwen processing → pending
```

после зависания.

Это **оставляем**.

А `modes.py` тоже сейчас менять практически не надо. Он уже правильно описывает три режима.

---

### Сейчас я бы сделал именно так

Не трогаем:

- `modes.py`
- `recovery.py`
- DINO worker
- Qwen worker
- SQL очередей

Меняем только:

```text
app/web/components/technical_modules/automation.py
app/web/components/technical_modules/photo_processing.py
```

И после этого проверяем:

```text
Manual → кнопки активны
Watcher → кнопки заблокированы
Automatic → кнопки заблокированы

Manual → Запустить → DINO + Qwen
Manual → Остановить → оба останавливаются → Manual

Watcher → Остановить → Manual
Automatic → Остановить → Manual
```

**Это правильная следующая точка.** Сейчас у нас уже есть backend-состояние для этой схемы, поэтому не нужно заново проектировать архитектуру — нужно аккуратно состыковать существующий UI с уже созданным `controller.py`.

---

### 👤 **User** — 2026-08-19 01:32:10

далее

---

### 🤖 **Assistant** — 2026-08-19 01:32:14

Да. Идём дальше **поэтапно**, чтобы не сломать рабочий DINO v33 / Hybrid v12.

### Шаг 1. Сначала фиксируем backend

`modes.py`, `controller.py`, `recovery.py` пока **не меняем**.

Сейчас нужно проверить, кто ещё вызывает `start_manual()`, `request_stop()` и `finish_stop()`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ CONTROLLER CALLS ================" && \
grep -RniE \
'start_manual|start_automatic|start_watcher|request_stop|finish_stop|set_manual|set_automatic|set_watcher' \
app scripts \
--include="*.py" | grep -v '__pycache__'
```

И отдельно посмотрим, есть ли уже watcher/automatic worker:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PIPELINE FILES ================" && \
find app/pipeline app/workers -maxdepth 2 -type f -name "*.py" -print | sort
```

### Что мы хотим увидеть

Архитектура должна постепенно стать такой:

```text
                    pipeline_control
                          │
                ┌─────────┴─────────┐
                │                   │
             РЕЖИМ              СОСТОЯНИЕ
                │                   │
       manual / watcher /       running
       automatic                stop_requested
                │
                ▼
        ┌───────────────┐
        │   controller  │
        └───────┬───────┘
                │
        ┌───────┴────────┐
        ▼                ▼
     DINO worker      Qwen worker
        │                │
        └───────┬────────┘
                ▼
             PostgreSQL
```

А UI только показывает это состояние и отправляет команды.

### Шаг 2

После выполнения **первой команды** пришли вывод.

Особенно важно увидеть, нет ли уже какого-нибудь scheduler/watcher, чтобы мы **не создали второй механизм запуска поверх существующего**.

Затем первым делом переделаем `automation.py` на три радио-режима, а уже после этого подключим блокировки кнопок в `photo_processing.py`.

---

### 👤 **User** — 2026-08-19 01:32:31

int_mvp_v02 && \
echo "================ CONTROLLER CALLS ================" && \
grep -RniE \
'start_manual|start_automatic|start_watcher|request_stop|finish_stop|set_manual|set_automatic|set_watcher' \
app scripts \
--include="*.py" | grep -v '__pycache__'
================ CONTROLLER CALLS ================
app/web/components/technical_modules/automation.py:9:    set_automatic,
app/web/components/technical_modules/automation.py:10:    set_manual,
app/web/components/technical_modules/automation.py:11:    set_watcher,
app/web/components/technical_modules/automation.py:342:                    set_manual()
app/web/components/technical_modules/automation.py:358:                    set_watcher(
app/web/components/technical_modules/automation.py:368:                    set_automatic(
app/web/components/technical_modules/automation.py:447:                set_watcher(path)
app/web/components/technical_modules/automation.py:488:                set_automatic(
app/pipeline/controller.py:120:def set_manual():
app/pipeline/controller.py:126:def set_automatic(auto_time: time):
app/pipeline/controller.py:132:def set_watcher(watcher_path: str):
app/pipeline/controller.py:138:def start_manual():
app/pipeline/controller.py:174:def start_automatic():
app/pipeline/controller.py:208:def start_watcher():
app/pipeline/controller.py:242:def request_stop():
app/pipeline/controller.py:258:def finish_stop():
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PIPELINE FILES ================" && \
find app/pipeline app/workers -maxdepth 2 -type f -name "*.py" -print | sort
================ PIPELINE FILES ================
app/pipeline/controller.py
app/pipeline/__init__.py
app/pipeline/modes.py
app/pipeline/queue.py
app/pipeline/recovery.py
app/pipeline/worker.py
app/workers/dino_worker.py
app/workers/qwen_worker.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:32:32

Отлично. Тут есть важный момент: **`automation.py` уже существенно новее того фрагмента, который ты показывал раньше** — в нём уже есть `set_watcher()` и обработчики трёх режимов. Значит, его сейчас **не надо переписывать вслепую**.

Следующий шаг — посмотреть именно актуальный `automation.py` и механизм очереди/worker.

Дай эти три вывода:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ AUTOMATION CURRENT ================" && \
sed -n '1,560p' app/web/components/technical_modules/automation.py && \
echo "================ QUEUE ================" && \
cat app/pipeline/queue.py && \
echo "================ WORKER ================" && \
cat app/pipeline/worker.py
```

И отдельно очень важная проверка — **не запускаются ли DINO/Qwen сейчас где-то помимо UI**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ WORKER LAUNCHES ================" && \
grep -RniE \
'create_subprocess|dino_worker|qwen_worker|start_dino|start_qwen|asyncio\.create_task|subprocess' \
app \
--include="*.py" | grep -v '__pycache__'
```

### Почему именно это

У нас сейчас уже видно:

```text
controller.py
    ├── manual
    ├── automatic
    ├── watcher
    ├── start_manual()
    ├── start_automatic()
    ├── start_watcher()
    ├── request_stop()
    └── finish_stop()
```

и отдельно:

```text
queue.py
worker.py
    ├── DINO
    └── Qwen
```

Поэтому надо понять, **где находится настоящий диспетчер**.

Если `queue.py / worker.py` уже умеют работать через PostgreSQL-статусы, то мы просто подключим к ним `pipeline_control`.

Если же сейчас `photo_processing.py` является единственным диспетчером, тогда сделаем небольшой контролирующий слой, **не трогая саму обработку DINO/Qwen**.

И ещё: в выводе уже видно, что `automation.py` вызывает `set_watcher()` и `set_automatic()`. Значит, **не надо сейчас ничего удалять или заменять**. Сначала смотрим актуальное состояние.

---

### 👤 **User** — 2026-08-19 01:33:22

alexice@NEURO:~/Desktop$ 
    print("Queue:", queue.db_path)
    print("Counts:", queue.counts())
================ WORKER ================
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.pipeline.queue import JobQueue

class FingerprintWorker:

    def __init__(self):
        self.queue = JobQueue(
            settings.data_dir / "jobs.db"
        )

        print("[Worker] Loading SceneEmbedder...")

        self.embedder = SceneEmbedder(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ d}")
alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ WORKER LAUNCHES ================" && \
grep -RniE \
'create_subprocess|dino_worker|qwen_worker|start_dino|start_qwen|asyncio\.create_task|subprocess' \
app \
--include="*.py" | grep -v '__pycache__'
================ WORKER LAUNCHES ================
app/web/components/technical_modules/photo_processing.py:15:DINO_WORKER = PROJECT / "app" / "workers" / "dino_worker.py"
app/web/components/technical_modules/photo_processing.py:16:QWEN_WORKER = PROJECT / "app" / "workers" / "qwen_worker.py"
app/web/components/technical_modules/photo_processing.py:379:    async def start_dino():
app/web/components/technical_modules/photo_processing.py:397:        if not DINO_WORKER.exists():
app/web/components/technical_modules/photo_processing.py:400:                f"Не найден DINO worker: {DINO_WORKER}",
app/web/components/technical_modules/photo_processing.py:426:                await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:430:                    str(DINO_WORKER),
app/web/components/technical_modules/photo_processing.py:433:                    stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/photo_processing.py:434:                    stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/photo_processing.py:443:            asyncio.create_task(
app/web/components/technical_modules/photo_processing.py:510:    async def start_qwen():
app/web/components/technical_modules/photo_processing.py:528:        if not QWEN_WORKER.exists():
app/web/components/technical_modules/photo_processing.py:531:                f"Не найден Qwen worker: {QWEN_WORKER}",
app/web/components/technical_modules/photo_processing.py:557:                await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:561:                    str(QWEN_WORKER),
app/web/components/technical_modules/photo_processing.py:564:                    stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/photo_processing.py:565:                    stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/photo_processing.py:574:            asyncio.create_task(
app/web/components/technical_modules/photo_processing.py:643:        await start_dino()
app/web/components/technical_modules/photo_processing.py:647:        await start_qwen()
app/web/components/technical_modules/photo_processing.py:821:                    on_click=start_dino,
app/web/components/technical_modules/photo_processing.py:913:                    on_click=start_qwen,
app/web/components/technical_modules/qwen.py:440:            process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/qwen.py:453:                stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/qwen.py:454:                stderr=asyncio.subprocess.STDOUT,
app/web/system/monitor.py:3:import subprocess
app/web/system/monitor.py:27:        result = subprocess.run(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:33:24

Да, теперь всё ясно. И здесь обнаружился **важный архитектурный момент**.

Сейчас фактический запуск DINO/Qwen происходит **только из `photo_processing.py`**:

```text
photo_processing.py
    ├── start_dino()
    │      └── create_subprocess_exec(dino_worker.py)
    │
    ├── start_qwen()
    │      └── create_subprocess_exec(qwen_worker.py)
    │
    └── start_all()
           ├── start_dino()
           └── start_qwen()
```

А `controller.py` пока управляет только записью состояния в PostgreSQL.

То есть сейчас:

```text
UI → напрямую запускает процессы
```

а должно стать:

```text
UI
 │
 ▼
controller
 │
 ├── pipeline_control
 │
 └── разрешение запуска
       │
       ├── DINO worker
       └── Qwen worker
```

### Но `worker.py` пока не трогаем

То, что ты показал:

```python
class FingerprintWorker:
    ...
    self.queue = JobQueue(
        settings.data_dir / "jobs.db"
    )
```

— это **другая старая очередь SQLite**, судя по всему.

Наш текущий DINO/Qwen контур работает через PostgreSQL `photos.dino_status / qwen_status`, что подтверждается `get_processing_stats()` и `recovery.py`.

Поэтому сейчас **не надо пытаться объединять `JobQueue` с PostgreSQL**. Иначе мы можем случайно сломать уже работающий v33/Hybrid v12.

---

## Сейчас делаем первый реальный патч

Нужно подключить `photo_processing.py` к `controller.py`.

### 1. Добавляем импорт

В начало `photo_processing.py` рядом с импортами:

```python
from app.pipeline.controller import (
    get_state,
    start_manual,
    request_stop,
    finish_stop,
)
```

### 2. Ограничиваем ручной запуск

В `start_dino()` перед запуском процесса:

```python
state = get_state()

if state.mode != "manual":
    ui.notify(
        "Ручной запуск доступен только в режиме «Ручной».",
        type="warning",
        timeout=3000,
    )
    return

if not state.running:
    start_manual()
```

Но **здесь есть нюанс**: если пользователь нажмёт сначала DINO, мы запишем `pipeline_control.running=True`, а потом Qwen тоже должен иметь возможность запуститься независимо.

Поэтому лучше сделать иначе.

---

## Правильнее: общий запуск владеет `pipeline_control`

То есть:

### `ЗАПУСТИТЬ`

```text
start_all()
    │
    ├── проверить mode == manual
    │
    ├── start_manual()
    │
    ├── start_dino()
    │
    └── start_qwen()
```

А индивидуальные:

```text
DINO ЗАПУСТИТЬ
Qwen ЗАПУСТИТЬ
```

в ручном режиме должны запускать **свою ветку**, но не переводить всю систему в `running=False/True` отдельно.

Именно поэтому `pipeline_control.running` должен означать:

> работает хотя бы один из двух процессов.

Это соответствует нашему требованию.

---

# Поэтому предлагаю следующий маленький патч

Сначала **не меняем запуск**.

Добавим только функцию синхронизации общего состояния:

```python
def sync_pipeline_state():
    state = get_state()

    if state.mode != "manual":
        return state

    dino_running = process_running(dino_process)
    qwen_running = process_running(qwen_process)

    if dino_running or qwen_running:
        if not state.running:
            start_manual()
    else:
        if state.running:
            finish_stop()

    return get_state()
```

Но `finish_stop()` сейчас автоматически переводит режим в Manual — это нормально **только когда пользователь действительно остановил систему**.

Если DINO завершился сам, а Qwen продолжает работать — ничего делать нельзя.

Поэтому пока эту функцию тоже **не вставляем**.

---

## Сначала делаем самое безопасное

В `photo_processing.py` нужно добавить **только блокировку кнопок по режиму**.

В `update_stats()` после определения `dino_running/qwen_running`:

```python
state = get_state()

manual_mode = (
    state.mode == "manual"
    and not state.running
)
```

и заменить:

```python
run_all_button.enabled = not (
    dino_running
    or qwen_running
)
```

на:

```python
run_all_button.enabled = (
    manual_mode
    and not dino_running
    and not qwen_running
)
```

DINO:

```python
dino_run_button.enabled = (
    manual_mode
    and not dino_running
)
```

Qwen:

```python
qwen_run_button.enabled = (
    manual_mode
    and not qwen_running
)
```

А stop оставить:

```python
stop_all_button.enabled = (
    dino_running
    or qwen_running
)
```

```python
dino_stop_button.enabled = dino_running
qwen_stop_button.enabled = qwen_running
```

### Это даст уже правильное поведение UI

```text
             MANUAL
               │
       ┌───────┼───────┐
       ▼       ▼       ▼
     общий    DINO    Qwen
     ON       ON       ON

WATCHER
               │
       ┌───────┼───────┐
       ▼       ▼       ▼
     общий    DINO    Qwen
     OFF      OFF      OFF

AUTOMATIC
               │
       ┌───────┼───────┐
       ▼       ▼       ▼
     общий    DINO    Qwen
     OFF      OFF      OFF
```

И **мы пока вообще не вмешиваемся в работающий запуск workers**.

---

### Давай сначала внесём именно этот безопасный шаг

После изменения выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python -m py_compile \
app/web/components/technical_modules/photo_processing.py \
app/web/components/technical_modules/automation.py \
app/pipeline/controller.py \
app/pipeline/modes.py \
app/pipeline/recovery.py
```

Если `py_compile` проходит без вывода — следующий шаг будет **подключение `request_stop()` / `finish_stop()` к настоящей кнопке ОСТАНОВИТЬ**, а потом уже сделаем корректное восстановление `processing → pending`.

---

### 👤 **User** — 2026-08-19 01:34:12

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
python -m py_compile \
app/web/components/technical_modules/photo_processing.py \
app/web/components/technical_modules/automation.py \
app/pipeline/controller.py \
app/pipeline/modes.py \
app/pipeline/recovery.py
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:34:13

Да, это просто потому, что у проекта используется **`uv`**, а системной команды `python` нет.

Проверяем тем же окружением проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/photo_processing.py \
app/web/components/technical_modules/automation.py \
app/pipeline/controller.py \
app/pipeline/modes.py \
app/pipeline/recovery.py
```

Если команда завершится **без вывода**, синтаксис всех пяти файлов корректен.

Пока ничего больше не меняем. Пришли результат этой команды.

---

### 👤 **User** — 2026-08-19 01:34:29

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/photo_processing.py \
app/web/components/technical_modules/automation.py \
app/pipeline/controller.py \
app/pipeline/modes.py \
app/pipeline/recovery.py

---

### 🤖 **Assistant** — 2026-08-19 01:34:30

Отлично. **Команда прошла без ошибок** — синтаксис пяти файлов корректный.

Но важный момент: мы пока проверили только компиляцию. Теперь можно переходить к следующему безопасному шагу — **подключить реальную кнопку `ОСТАНОВИТЬ` к `pipeline_control`**, чтобы остановка соответствовала нашей схеме:

```text
ОСТАНОВИТЬ
    ↓
request_stop()
    ↓
DINO/Qwen завершаются
    ↓
незавершённые задания остаются pending
    ↓
finish_stop()
    ↓
mode = manual
```

Перед изменением я хочу увидеть **актуальные `stop_dino()`, `stop_qwen()` и `stop_all()`**, потому что именно там сейчас нужно сделать минимальный патч.

Выполни:

```bash id="j6x3nt"
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '455,675p' app/web/components/technical_modules/photo_processing.py
```

После этого дам точную замену только нужного участка, без переписывания всего файла.

---

### 👤 **User** — 2026-08-19 01:34:48

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '455,675p' app/web/components/technical_modules/photo_processing.py

        except Exception as exc:

            dino_process = None

            print(
                "[WEB] DINO START ERROR:",
                repr(exc),
                flush=True,
            )

            ui.notify(
                f"Ошибка запуска DINO: {exc}",
                type="negative",
                timeout=8000,
            )

    # ============================================================
    # STOP DINO
    # ============================================================

    async def stop_dino():

        nonlocal dino_stopping

        if not process_running(dino_process):
            return

        dino_stopping = True

        try:

            dino_process.terminate()

            ui.notify(
                "DINO останавливается",
                type="warning",
                timeout=3000,
            )

        except ProcessLookupError:
            pass

        except Exception as exc:

            ui.notify(
                f"Ошибка остановки DINO: {exc}",
                type="negative",
                timeout=8000,
            )

    # ============================================================
    # START QWEN
    # ============================================================

    async def start_qwen():

        nonlocal qwen_process
        nonlocal qwen_stopping

        if process_running(qwen_process):
            return

        if not UV.exists():

            ui.notify(
                f"Не найден uv: {UV}",
                type="negative",
                timeout=8000,
            )

            return

        if not QWEN_WORKER.exists():

            ui.notify(
                f"Не найден Qwen worker: {QWEN_WORKER}",
                type="negative",
                timeout=8000,
            )

            return

        qwen_stopping = False

        try:

            env = {
                "PATH": (
                    f"{Path.home() / '.local/bin'}:"
                    "/usr/local/sbin:"
                    "/usr/local/bin:"
                    "/usr/sbin:"
                    "/usr/bin:"
                    "/sbin:"
                    "/bin"
                ),
                "HOME": str(Path.home()),
                "PYTHONUNBUFFERED": "1",
            }

            qwen_process = (
                await asyncio.create_subprocess_exec(
                    str(UV),
                    "run",
                    "python",
                    str(QWEN_WORKER),
                    cwd=str(PROJECT),
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
            )

            print(
                f"[WEB] QWEN START PID={qwen_process.pid}",
                flush=True,
            )

            asyncio.create_task(
                consume_output(
                    qwen_process,
                    "QWEN",
                )
            )

            ui.notify(
                "Qwen запущен",
                type="positive",
                timeout=3000,
            )

        except Exception as exc:

            qwen_process = None

            print(
                "[WEB] QWEN START ERROR:",
                repr(exc),
                flush=True,
            )

            ui.notify(
                f"Ошибка запуска Qwen: {exc}",
                type="negative",
                timeout=8000,
            )

    # ============================================================
    # STOP QWEN
    # ============================================================

    async def stop_qwen():

        nonlocal qwen_stopping

        if not process_running(qwen_process):
            return

        qwen_stopping = True

        try:

            qwen_process.terminate()

            ui.notify(
                "Qwen останавливается",
                type="warning",
                timeout=3000,
            )

        except ProcessLookupError:
            pass

        except Exception as exc:

            ui.notify(
                f"Ошибка остановки Qwen: {exc}",
                type="negative",
                timeout=8000,
            )

    # ============================================================
    # START ALL
    # ============================================================

    async def start_all():

        await start_dino()

        await asyncio.sleep(0.2)

        await start_qwen()

    # ============================================================
    # STOP ALL
    # ============================================================

    async def stop_all():

        await stop_dino()

        await stop_qwen()

    # ============================================================
    # SOURCE PICKER
    # ============================================================

    async def choose_source():

        ui.notify(
            "Укажите папку источника в поле выше.",
            type="info",
            timeout=3000,
        )

    # ============================================================
    # UI
    # ============================================================

    with ui.card().classes(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:34:52

Отлично. Теперь видно точное место. Делаем **минимальный патч**, не трогая workers.

Главное: **`ОСТАНОВИТЬ` общий** будет выставлять `stop_requested`, затем корректно завершать оба процесса. После того как оба реально остановились, `finish_stop()` переведёт режим обратно в `manual`.

При этом **индивидуальная кнопка DINO/Qwen не должна останавливать второй процесс**.

### 1. Добавь импорт

В начало `photo_processing.py`, где импорты, добавь:

```python
from app.pipeline.controller import (
    get_state,
    request_stop,
    finish_stop,
)
```

### 2. Замени только `stop_all()`

Сейчас:

```python
async def stop_all():

    await stop_dino()

    await stop_qwen()
```

замени на:

```python
async def stop_all():

    if not (
        process_running(dino_process)
        or process_running(qwen_process)
    ):
        return

    try:
        # Фиксируем намерение остановки в PostgreSQL.
        # Очередь и результаты при этом не сбрасываются.
        request_stop()

        await stop_dino()
        await stop_qwen()

        ui.notify(
            "Остановка DINO и Qwen запрошена",
            type="warning",
            timeout=3000,
        )

    except Exception as exc:

        print(
            "[WEB] STOP ALL ERROR:",
            repr(exc),
            flush=True,
        )

        ui.notify(
            f"Ошибка остановки: {exc}",
            type="negative",
            timeout=8000,
        )
```

### 3. Теперь добавляем завершение остановки в `update_stats()`

Найди в `update_stats()` участок:

```python
dino_running = process_running(
    dino_process
)

qwen_running = process_running(
    qwen_process
)
```

и **сразу после него** добавь:

```python
state = get_state()

if (
    state.stop_requested
    and not dino_running
    and not qwen_running
):
    try:
        finish_stop()
        state = get_state()

    except Exception as exc:
        print(
            "[WEB] FINISH STOP ERROR:",
            repr(exc),
            flush=True,
        )
```

Таким образом получится:

```text
ОСТАНОВИТЬ
    │
    ▼
request_stop()
    │
    ├── DINO terminate()
    └── Qwen terminate()
             │
             ▼
      следующий update_stats()
             │
             ▼
       оба процесса мертвы?
             │
            ДА
             │
             ▼
        finish_stop()
             │
             ▼
        mode = manual
        running = false
        stop_requested = false
```

### 4. Почему пока не меняем `stop_dino()` и `stop_qwen()`

Это важно.

Если нажать:

**DINO → Остановить**

а Qwen продолжает работать, мы **не должны** делать:

```python
finish_stop()
```

потому что тогда PostgreSQL скажет:

```text
running = false
mode = manual
```

хотя Qwen ещё работает.

Поэтому пока только **общая кнопка** управляет `pipeline_control.stop_requested`.

---

### 5. После патча проверяем синтаксис

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/photo_processing.py \
app/web/components/technical_modules/automation.py \
app/pipeline/controller.py \
app/pipeline/modes.py \
app/pipeline/recovery.py
```

Если опять **без вывода**, запускаем UI и проверяем уже поведение.

Следующим шагом после этого будет самое важное: **не дать `start_dino()` и `start_qwen()` запускаться вручную при `watcher/automatic` даже в обход заблокированной кнопки**. То есть сделаем защиту не только на UI, но и внутри функций запуска.

---

### 👤 **User** — 2026-08-19 01:35:04

давай патч

---

### 🤖 **Assistant** — 2026-08-19 01:35:05

Да. Сделаем патч автоматически, без ручного редактирования.

Выполни **одну команду** из корня проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/photo_processing.py")
s = p.read_text()

# ------------------------------------------------------------
# 1. Добавляем controller imports
# ------------------------------------------------------------

old = """from app.web.photo_db import get_processing_stats
"""

new = """from app.web.photo_db import get_processing_stats

from app.pipeline.controller import (
    get_state,
    request_stop,
    finish_stop,
)
"""

if old not in s:
    raise SystemExit("ERROR: import anchor not found")

s = s.replace(old, new, 1)

# ------------------------------------------------------------
# 2. Заменяем stop_all()
# ------------------------------------------------------------

old = """    async def stop_all():

        await stop_dino()

        await stop_qwen()
"""

new = """    async def stop_all():

        if not (
            process_running(dino_process)
            or process_running(qwen_process)
        ):
            return

        try:
            # Фиксируем намерение остановки в PostgreSQL.
            # Результаты и очередь при этом не сбрасываются.
            request_stop()

            await stop_dino()
            await stop_qwen()

            ui.notify(
                "Остановка DINO и Qwen запрошена",
                type="warning",
                timeout=3000,
            )

        except Exception as exc:

            print(
                "[WEB] STOP ALL ERROR:",
                repr(exc),
                flush=True,
            )

            ui.notify(
                f"Ошибка остановки: {exc}",
                type="negative",
                timeout=8000,
            )
"""

if old not in s:
    raise SystemExit("ERROR: stop_all anchor not found")

s = s.replace(old, new, 1)

# ------------------------------------------------------------
# 3. После определения состояния процессов
#    завершаем pipeline stop
# ------------------------------------------------------------

old = """        dino_running = process_running(
            dino_process
        )

        qwen_running = process_running(
            qwen_process
        )

        set_branch_indicator(
"""

new = """        dino_running = process_running(
            dino_process
        )

        qwen_running = process_running(
            qwen_process
        )

        # ----------------------------------------------------
        # PIPELINE STOP FINALIZATION
        # ----------------------------------------------------

        state = get_state()

        if (
            state.stop_requested
            and not dino_running
            and not qwen_running
        ):
            try:
                finish_stop()
                state = get_state()

            except Exception as exc:
                print(
                    "[WEB] FINISH STOP ERROR:",
                    repr(exc),
                    flush=True,
                )

        set_branch_indicator(
"""

if old not in s:
    raise SystemExit("ERROR: process state anchor not found")

s = s.replace(old, new, 1)

p.write_text(s)

print("OK: photo_processing.py patched")
PY
```

После этого сразу проверяем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/photo_processing.py \
app/web/components/technical_modules/automation.py \
app/pipeline/controller.py \
app/pipeline/modes.py \
app/pipeline/recovery.py
```

И затем покажи:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -A35 -B5 'async def stop_all' \
app/web/components/technical_modules/photo_processing.py && \
echo "================ STOP FINALIZATION ================" && \
grep -n -A20 -B8 'PIPELINE STOP FINALIZATION' \
app/web/components/technical_modules/photo_processing.py
```

**Пока больше ничего не патчим.** Сначала убедимся, что этот слой корректно встал.

---

### 👤 **User** — 2026-08-19 01:35:32

echo "================ STOP FINALIZATION ================" && \
grep -n -A20 -B8 'PIPELINE STOP FINALIZATION' \
app/web/components/technical_modules/photo_processing.py
676-
677-    # ============================================================
678-    # STOP ALL
679-    # ============================================================
680-
681:    async def stop_all():
682-
683-        if not (
684-            process_running(dino_process)
685-            or process_running(qwen_process)
686-        ):
687-            return
688-
689-        try:
690-            # Фиксируем намерение остановки в PostgreSQL.
691-            # Результаты и очередь при этом не сбрасываются.
692-            request_stop()
693-
694-            await stop_dino()
695-            await stop_qwen()
696-
697-            ui.notify(
698-                "Остановка DINO и Qwen запрошена",
699-                type="warning",
700-                timeout=3000,
701-            )
702-
703-        except Exception as exc:
704-
705-            print(
706-                "[WEB] STOP ALL ERROR:",
707-                repr(exc),
708-                flush=True,
709-            )
710-
711-            ui.notify(
712-                f"Ошибка остановки: {exc}",
713-                type="negative",
714-                timeout=8000,
715-            )
716-
================ STOP FINALIZATION ================
264-            dino_process
265-        )
266-
267-        qwen_running = process_running(
268-            qwen_process
269-        )
270-
271-        # ----------------------------------------------------
272:        # PIPELINE STOP FINALIZATION
273-        # ----------------------------------------------------
274-
275-        state = get_state()
276-
277-        if (
278-            state.stop_requested
279-            and not dino_running
280-            and not qwen_running
281-        ):
282-            try:
283-                finish_stop()
284-                state = get_state()
285-
286-            except Exception as exc:
287-                print(
288-                    "[WEB] FINISH STOP ERROR:",
289-                    repr(exc),
290-                    flush=True,
291-                )
292-
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:35:33

Да, патч встал правильно.

Сейчас имеем:

- `request_stop()` вызывается общей кнопкой **ОСТАНОВИТЬ**.
- DINO и Qwen останавливаются независимо.
- `finish_stop()` вызывается только когда **оба процесса уже остановлены**.
- После этого `controller.py` переводит состояние в:
  - `mode = manual`
  - `running = false`
  - `stop_requested = false`
- Результаты и статусы фотографий при этом не сбрасываются.

Но есть один следующий важный момент: **сейчас `start_dino()` и `start_qwen()` сами ещё не проверяют режим**. Значит, защита пока только на уровне кнопок UI.

Следующим патчем я бы добавил защиту непосредственно в `start_dino()` и `start_qwen()`:

```text
manual → можно
watcher → нельзя
automatic → нельзя
```

И это нужно сделать **до запуска subprocess**, чтобы даже вызов функции напрямую не смог нарушить режим.

После этого уже займёмся самим `automation.py`, чтобы его три режима действительно управляли запуском, а не только записывали состояние в БД.

---

### 👤 **User** — 2026-08-19 01:35:42

да

---

### 🤖 **Assistant** — 2026-08-19 01:35:43

Да. Сейчас добавляем **защиту непосредственно в `start_dino()` и `start_qwen()`**. UI пока не трогаем.

Сделаем патч автоматически:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/photo_processing.py")
s = p.read_text()

# ============================================================
# DINO — защита режима
# ============================================================

old = """    async def start_dino():

        nonlocal dino_process
        nonlocal dino_stopping

        if process_running(dino_process):
            return
"""

new = """    async def start_dino():

        nonlocal dino_process
        nonlocal dino_stopping

        # Ручной запуск разрешён только в ручном режиме.
        state = get_state()

        if state.mode != "manual":
            ui.notify(
                "DINO нельзя запускать вручную в текущем режиме.",
                type="warning",
                timeout=3000,
            )
            return

        if process_running(dino_process):
            return
"""

if old not in s:
    raise SystemExit("ERROR: DINO start anchor not found")

s = s.replace(old, new, 1)

# ============================================================
# QWEN — защита режима
# ============================================================

old = """    async def start_qwen():

        nonlocal qwen_process
        nonlocal qwen_stopping

        if process_running(qwen_process):
            return
"""

new = """    async def start_qwen():

        nonlocal qwen_process
        nonlocal qwen_stopping

        # Ручной запуск разрешён только в ручном режиме.
        state = get_state()

        if state.mode != "manual":
            ui.notify(
                "Qwen нельзя запускать вручную в текущем режиме.",
                type="warning",
                timeout=3000,
            )
            return

        if process_running(qwen_process):
            return
"""

if old not in s:
    raise SystemExit("ERROR: Qwen start anchor not found")

s = s.replace(old, new, 1)

p.write_text(s)

print("OK: manual start protection added")
PY
```

Теперь проверяем синтаксис:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/photo_processing.py \
app/web/components/technical_modules/automation.py \
app/pipeline/controller.py \
app/pipeline/modes.py \
app/pipeline/recovery.py
```

И проверяем, что оба ограничения действительно появились:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -A22 'async def start_dino' \
app/web/components/technical_modules/photo_processing.py && \
echo "================ QWEN ================" && \
grep -n -A22 'async def start_qwen' \
app/web/components/technical_modules/photo_processing.py
```

После этого следующий шаг — **связать `Watcher` и `Automatic` с фактическим запуском workers**. Сейчас `automation.py` умеет записывать режим в PostgreSQL, но само по себе это ещё не запускает DINO/Qwen.

---

### 👤 **User** — 2026-08-19 01:36:08

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -A22 'async def start_dino' \
app/web/components/technical_modules/photo_processing.py && \
echo "================ QWEN ================" && \
grep -n -A22 'async def start_qwen' \
app/web/components/technical_modules/photo_processing.py
407:    async def start_dino():
408-
409-        nonlocal dino_process
410-        nonlocal dino_stopping
411-
412-        # Ручной запуск разрешён только в ручном режиме.
413-        state = get_state()
414-
415-        if state.mode != "manual":
416-            ui.notify(
417-                "DINO нельзя запускать вручную в текущем режиме.",
418-                type="warning",
419-                timeout=3000,
420-            )
421-            return
422-
423-        if process_running(dino_process):
424-            return
425-
426-        if not UV.exists():
427-
428-            ui.notify(
429-                f"Не найден uv: {UV}",
================ QWEN ================
549:    async def start_qwen():
550-
551-        nonlocal qwen_process
552-        nonlocal qwen_stopping
553-
554-        # Ручной запуск разрешён только в ручном режиме.
555-        state = get_state()
556-
557-        if state.mode != "manual":
558-            ui.notify(
559-                "Qwen нельзя запускать вручную в текущем режиме.",
560-                type="warning",
561-                timeout=3000,
562-            )
563-            return
564-
565-        if process_running(qwen_process):
566-            return
567-
568-        if not UV.exists():
569-
570-            ui.notify(
571-                f"Не найден uv: {UV}",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:36:10

Отлично. Защита действительно стоит **внутри обеих функций**, а не только на кнопках UI.

Теперь следующий этап — фактически подключить `Watcher` и `Automatic`. Но перед патчем нужно увидеть их текущую реализацию целиком, потому что у тебя `automation.py` уже содержит обработчики `set_watcher()` и `set_automatic()`, и мы не должны создавать второй механизм поверх существующего.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '280,530p' app/web/components/technical_modules/automation.py
```

И отдельно покажи, есть ли уже какой-либо фоновый scheduler/watcher:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'watchdog|Observer|FileSystemEvent|schedule|scheduler|auto_time|watcher_path|watcher_enabled|start_automatic|start_watcher' \
app \
--include="*.py" | grep -v '__pycache__'
```

После этого уже сделаем **один правильный слой управления**, а не будем плодить отдельные таймеры и процессы.

---

