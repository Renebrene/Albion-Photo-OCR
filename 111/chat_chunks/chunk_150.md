## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 👤 **User** — 2026-08-19 00:55:20

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

for f in \
  app/web/components/technical.py \
  app/web/components/technical_modules/photo_processing.py \
  app/web/components/technical_modules/qwen.py \
  app/pipeline/controller.py \
  app/pipeline/modes.py \
  app/pipeline/queue.py \
  app/workers/dino_worker.py \
  app/workers/qwen_worker.py
do
    echo
    echo "============================================================"
    echo "FILE: $f"
    echo "============================================================"
    cat "$f"
done

============================================================
FILE: app/web/components/technical.py
============================================================
from nicegui import ui

from app.web.components.technical_modules.photo_processing import (
    build_photo_processing,
)
from app.web.components.technical_modules.last_run import (
    build_last_run,
)
from app.web.components.technical_modules.automation import (
    build_automation,
)
from app.web.components.technical_modules.qwen import (
    build_qwen,
)
from app.web.components.technical_modules.data import (
    build_data,
)
from app.web.components.technical_modules.system import (
    build_system,
)
from app.web.components.technical_modules.fingerprints import (
    build_fingerprints,
)
from app.web.components.technical_modules.users import build_users

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
                card.__albionResizeObserver.disconnect();
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

============================================================
FILE: app/web/components/technical_modules/photo_processing.py
============================================================
import asyncio
import re
from pathlib import Path

from nicegui import ui

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"
DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"

def build_photo_processing():

    source_input = ui.input(
        label="Источник фотографий",
        value=str(PROJECT / "data/input/daily"),
    ).props(
        "outlined dense"
    ).classes("flex-1")

    output_input = ui.input(
        label="Результат",
        value=str(PROJECT / "data/output/daily"),
    ).props(
        "outlined dense"
    ).classes("flex-1")

    status_label = ui.label(
        "Готов к запуску"
    ).classes(
        "text-sm text-grey-6"
    )

    run_button = None

    async def run_pipeline():

        input_dir = Path(
            source_input.value
        ).expanduser()

        if not input_dir.is_absolute():
            input_dir = PROJECT / input_dir

        if not input_dir.exists():
            ui.notify(
                f"Папка не найдена: {input_dir}",
                type="negative",
            )
            return

        images = [
            p for p in input_dir.iterdir()
            if p.is_file()
            and p.suffix.lower() in {
                ".jpg",
                ".jpeg",
                ".png",
            }
        ]

        if not images:
            ui.notify(
                "В папке нет фотографий",
                type="negative",
            )
            return

        if not DAILY_SCRIPT.exists():
            ui.notify(
                f"Не найден скрипт: {DAILY_SCRIPT}",
                type="negative",
            )
            return

        run_button.disable()

        status_label.text = (
            f"Запуск Hybrid v12... "
            f"Фотографий: {len(images)}"
        )

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

            process = await asyncio.create_subprocess_exec(
                "bash",
                str(DAILY_SCRIPT),
                cwd=str(PROJECT),
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            output_lines = []

            while True:

                line = await process.stdout.readline()

                if not line:
                    break

                text = line.decode(
                    "utf-8",
                    errors="replace",
                ).rstrip()

                output_lines.append(text)

                if text:
                    status_label.text = text[-180:]

            returncode = await process.wait()

            output = "\n".join(output_lines)

            if returncode != 0:

                status_label.text = (
                    f"✗ Hybrid v12: ошибка ({returncode})"
                )

                ui.notify(
                    "Распознавание завершилось ошибкой",
                    type="negative",
                    timeout=8000,
                )

                return

            match = re.search(
                r"Output\s*:\s*(.+)",
                output,
            )

            if match:

                result_dir = Path(
                    match.group(1).strip()
                )

            else:

                result_dir = None

            if not result_dir or not result_dir.exists():

                status_label.text = (
                    "⚠ Hybrid завершён, "
                    "папка результата не найдена"
                )

                ui.notify(
                    "Hybrid завершён, "
                    "но папка результата не определена.",
                    type="warning",
                    timeout=8000,
                )

                return

            output_input.value = str(
                result_dir
            )

            status_label.text = (
                "✓ Hybrid v12: сортировка завершена"
            )

            ui.notify(
                f"Сортировка завершена: {result_dir}",
                type="positive",
                timeout=5000,
            )

            # ====================================================
            # QWEN3-VL 4B
            # ====================================================

            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"

            if not qwen_script.exists():

                status_label.text = (
                    "✓ Hybrid завершён → Qwen script не найден"
                )

                ui.notify(
                    f"Не найден Qwen script: {qwen_script}",
                    type="warning",
                    timeout=8000,
                )

                return

            # Имя папки Hybrid запуска:
            # 20260816_230042
            run_name = result_dir.name

            qwen_output = (
                PROJECT
                / "data"
                / "metadata"
                / "qwen4b"
                / run_name
            )

            qwen_output.mkdir(
                parents=True,
                exist_ok=True,
            )

            status_label.text = (
                "▶ Qwen3-VL 4B: выполняется..."
            )

            ui.notify(
                "▶ Сортировка завершена. "
                "Запускается Qwen3-VL 4B.",
                type="info",
                timeout=5000,
            )

            try:

                qwen_process = await asyncio.create_subprocess_exec(
                    str(PROJECT / ".venv" / "bin" / "python"),
                    str(qwen_script),
                    "--input",
                    str(result_dir),
                    "--output",
                    str(qwen_output),
                    cwd=str(PROJECT),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )

                qwen_lines = []

                while True:

                    line = await qwen_process.stdout.readline()

                    if not line:
                        break

                    text = line.decode(
                        "utf-8",
                        errors="replace",
                    ).rstrip()

                    qwen_lines.append(text)

                    if status_label:
                        status_label.text = text[-160:]

                qwen_returncode = await qwen_process.wait()

                if qwen_returncode != 0:

                    status_label.text = (
                        "✗ Hybrid v12: ✓  "
                        "Qwen3-VL 4B: ошибка"
                    )

                    ui.notify(
                        "Hybrid завершён успешно, "
                        "но Qwen3-VL 4B завершился с ошибкой.",
                        type="negative",
                        timeout=10000,
                    )

                    return

                status_label.text = (
                    "✓ Hybrid v12 + Qwen3-VL 4B: готово"
                )

                output_input.value = str(
                    result_dir
                )

                ui.notify(
                    "✓ Полная обработка завершена: "
                    "Hybrid v12 + Qwen3-VL 4B.",
                    type="positive",
                    timeout=8000,
                )

            except Exception as qwen_error:

                status_label.text = (
                    "✗ Hybrid: ✓  "
                    "Qwen3-VL 4B: ошибка запуска"
                )

                ui.notify(
                    f"Ошибка запуска Qwen: {qwen_error}",
                    type="negative",
                    timeout=10000,
                )

        except Exception as e:

            status_label.text = (
                "✗ Ошибка запуска"
            )

            ui.notify(
                f"Ошибка запуска: {e}",
                type="negative",
                timeout=8000,
            )

        finally:

            run_button.enable()

    # ============================================================
    # UI
    # ============================================================

    with ui.card().classes("w-full"):

        ui.label(
            "ФОТООТЧЁТ"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        ui.label(
            "Источник фотографий"
        )

        with ui.row().classes(
            "w-full items-center gap-2"
        ):

            source_input

            ui.button(
                "Выбрать",
                icon="folder_open",
            ).props(
                "flat dense"
            )

        ui.label(
            "Результат"
        )

        with ui.row().classes(
            "w-full items-center gap-2"
        ):

            output_input

            ui.button(
                "Выбрать",
                icon="folder_open",
            ).props(
                "flat dense"
            )

        ui.separator().classes("my-2")

        ui.label(
            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
        ).classes(
            "text-sm"
        )

        run_button = ui.button(
            "▶  ЗАПУСТИТЬ ОБРАБОТКУ",
            on_click=run_pipeline,
        ).props(
            "unelevated"
        ).classes(
            "w-full text-lg font-bold"
        )

        status_label

        ui.label(
            "Главная рабочая операция"
        ).classes(
            "text-xs text-grey-6"
        )

============================================================
FILE: app/web/components/technical_modules/qwen.py
============================================================
import asyncio
import json
from pathlib import Path

from nicegui import ui

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"

QWEN_ROOT = (
    PROJECT
    / "data"
    / "metadata"
    / "qwen4b"
)

DAILY_ROOT = (
    PROJECT
    / "data"
    / "output"
    / "daily"
)

QWEN_SCRIPT = (
    PROJECT
    / "scripts"
    / "qwen4b_output_v01.py"
)

def _find_latest_summary():

    candidates = []

    root_summary = QWEN_ROOT / "summary.json"

    if root_summary.exists():
        candidates.append(root_summary)

    if QWEN_ROOT.exists():

        candidates.extend(
            p
            for p in QWEN_ROOT.glob("*/summary.json")
            if p.is_file()
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda p: p.stat().st_mtime,
    )

def _load_qwen_status():

    summary_path = _find_latest_summary()

    if summary_path is None:

        return {
            "state": "НЕТ ДАННЫХ",
            "processed": 0,
            "ok": 0,
            "skipped": 0,
            "errors": 0,
            "addresses": 0,
            "avg_time": 0.0,
            "avg_confidence": 0.0,
            "model": "Qwen3-VL 4B",
            "run": "—",
            "summary": None,
        }

    try:

        with open(
            summary_path,
            "r",
            encoding="utf-8",
        ) as f:

            summary = json.load(f)

        results = summary.get(
            "results",
            [],
        )

        if not isinstance(results, list):

            raise ValueError(
                "поле results отсутствует или имеет неверный формат"
            )

        ok_results = [
            x
            for x in results
            if x.get("status") == "ok"
        ]

        skipped_results = [
            x
            for x in results
            if x.get("status") == "skipped"
        ]

        error_results = [
            x
            for x in results
            if x.get("status") == "error"
        ]

        addresses = {
            x.get("address")
            for x in results
            if x.get("address")
        }

        times = [
            float(x["time_sec"])
            for x in ok_results
            if x.get("time_sec") is not None
        ]

        confidences = [
            float(x["confidence"])
            for x in ok_results
            if x.get("confidence") not in (
                None,
                "",
            )
        ]

        return {
            "state": "ГОТОВ",
            "processed": len(results),
            "ok": len(ok_results),
            "skipped": len(skipped_results),
            "errors": len(error_results),
            "addresses": len(addresses),
            "avg_time": (
                sum(times) / len(times)
                if times
                else 0.0
            ),
            "avg_confidence": (
                sum(confidences) / len(confidences)
                if confidences
                else 0.0
            ),
            "model": summary.get(
                "model",
                "Qwen3-VL 4B",
            ),
            "run": summary_path.parent.name,
            "summary": summary_path,
        }

    except Exception as exc:

        return {
            "state": "ОШИБКА ФОРМАТА",
            "processed": 0,
            "ok": 0,
            "skipped": 0,
            "errors": 0,
            "addresses": 0,
            "avg_time": 0.0,
            "avg_confidence": 0.0,
            "model": "Qwen3-VL 4B",
            "run": summary_path.parent.name,
            "summary": summary_path,
            "error": str(exc),
        }

def _find_latest_hybrid():

    if not DAILY_ROOT.exists():
        return None

    runs = [
        p
        for p in DAILY_ROOT.iterdir()
        if p.is_dir()
    ]

    if not runs:
        return None

    return max(
        runs,
        key=lambda p: p.name,
    )

def build_qwen():

    with ui.card().classes("w-full"):

        ui.label(
            "QWEN3-VL 4B"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            ui.label(
                "Анализ содержимого фотографий"
            ).classes(
                "text-base font-medium"
            )

            status_label = ui.label(
                "● НЕТ ДАННЫХ"
            ).classes(
                "text-sm"
            )

        with ui.grid(columns=2).classes(
            "w-full gap-2"
        ):

            ui.label("Статус")
            state_label = ui.label("—")

            ui.label("Последний запуск")
            run_label = ui.label("—")

            ui.label("Модель")
            model_label = ui.label("—")

            ui.label("Обработано")
            processed_label = ui.label("0")

            ui.label("OK")
            ok_label = ui.label("0")

            ui.label("Пропущено")
            skipped_label = ui.label("0")

            ui.label("Ошибок")
            errors_label = ui.label("0")

            ui.label("Адресов")
            addresses_label = ui.label("0")

            ui.label("Среднее время")
            avg_time_label = ui.label("0.00 сек")

            ui.label("Средняя уверенность")
            avg_confidence_label = ui.label("0.0%")

        ui.separator().classes("my-2")

        with ui.row().classes(
            "gap-2"
        ):

            run_button = ui.button(
                "▶ Запустить Qwen",
            ).props(
                "unelevated"
            )

            stop_button = ui.button(
                "■ Остановить Qwen",
            ).props(
                "unelevated color=negative"
            )

            stop_button.disable()

            refresh_button = ui.button(
                "↻ Обновить",
            ).props(
                "flat"
            )

        source_label = ui.label(
            "Источник: —"
        ).classes(
            "text-xs text-grey-6"
        )

    qwen_process = None
    qwen_stop_requested = False

    async def stop_qwen():
        nonlocal qwen_process
        nonlocal qwen_stop_requested

        if qwen_process is None:
            return

        qwen_stop_requested = True

        print(
            f"[QWEN MANUAL] STOP REQUESTED PID={qwen_process.pid}",
            flush=True,
        )

        try:
            qwen_process.terminate()
        except ProcessLookupError:
            pass
        except Exception as exc:
            print(
                f"[QWEN MANUAL] STOP FAILED: {exc!r}",
                flush=True,
            )

    async def run_qwen():

        nonlocal qwen_process
        nonlocal qwen_stop_requested

        print("[QWEN MANUAL] START", flush=True)

        qwen_stop_requested = False

        run_button.disable()
        stop_button.enable()

        try:

            if not QWEN_SCRIPT.exists():

                print(
                    f"[QWEN MANUAL] SCRIPT NOT FOUND: {QWEN_SCRIPT}",
                    flush=True,
                )

                ui.notify(
                    f"Не найден Qwen script: {QWEN_SCRIPT}",
                    type="negative",
                    timeout=8000,
                )

                return

            result_dir = _find_latest_hybrid()

            if result_dir is None:

                print(
                    "[QWEN MANUAL] HYBRID RUN NOT FOUND",
                    flush=True,
                )

                ui.notify(
                    "Не найден ни один запуск Hybrid.",
                    type="negative",
                    timeout=8000,
                )

                return

            images = [
                p
                for p in result_dir.rglob("*")
                if (
                    p.is_file()
                    and p.suffix.lower()
                    in {".jpg", ".jpeg", ".png", ".webp"}
                )
            ]

            total_images = len(images)

            if not images:

                print(
                    f"[QWEN MANUAL] NO IMAGES: {result_dir}",
                    flush=True,
                )

                ui.notify(
                    f"В последнем Hybrid нет фотографий: {result_dir}",
                    type="negative",
                    timeout=8000,
                )

                return

            run_name = result_dir.name

            qwen_output = QWEN_ROOT / run_name
            qwen_output.mkdir(
                parents=True,
                exist_ok=True,
            )

            print(
                f"[QWEN MANUAL] INPUT: {result_dir}",
                flush=True,
            )

            print(
                f"[QWEN MANUAL] OUTPUT: {qwen_output}",
                flush=True,
            )

            print(
                f"[QWEN MANUAL] IMAGES: {total_images}",
                flush=True,
            )

            state_label.text = "ВЫПОЛНЯЕТСЯ"
            status_label.text = "● ВЫПОЛНЯЕТСЯ"
            run_label.text = run_name
            model_label.text = "qwen3-vl:4b-instruct"
            processed_label.text = f"0 / {total_images}"
            ok_label.text = "0"
            skipped_label.text = "0"
            errors_label.text = "0"
            addresses_label.text = "0"
            avg_time_label.text = "0.00 сек"
            avg_confidence_label.text = "0.0%"

            source_label.text = (
                f"Источник: {result_dir} "
                f"({total_images} фото)"
            )

            ui.notify(
                f"Запуск Qwen3-VL 4B: {total_images} фото",
                type="info",
                timeout=5000,
            )

            process = await asyncio.create_subprocess_exec(
                str(
                    PROJECT
                    / ".venv"
                    / "bin"
                    / "python"
                ),
                str(QWEN_SCRIPT),
                "--input",
                str(result_dir),
                "--output",
                str(qwen_output),
                cwd=str(PROJECT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            qwen_process = process

            print(
                f"[QWEN MANUAL] PID: {process.pid}",
                flush=True,
            )

            current = 0
            ok_count = 0
            skipped_count = 0
            error_count = 0
            times = []
            confidences = []
            addresses = set()

            while True:

                line = await process.stdout.readline()

                if not line:
                    break

                text = line.decode(
                    "utf-8",
                    errors="replace",
                ).rstrip()

                if not text:
                    continue

                print(
                    f"[QWEN] {text}",
                    flush=True,
                )

                # -------------------------------------------------
                # PROGRESS: [346/526]
                # -------------------------------------------------

                import re

                progress = re.search(
                    r"$$(\d+)\s*/\s*(\d+)$$",
                    text,
                )

                if progress:

                    current = int(progress.group(1))

                    processed_label.text = (
                        f"{current} / {total_images}"
                    )

                    state_label.text = (
                        f"ВЫПОЛНЯЕТСЯ: "
                        f"{current}/{total_images}"
                    )

                # -------------------------------------------------
                # SKIP
                # -------------------------------------------------

                if "SKIP — metadata already exists" in text:
                    skipped_count += 1
                    skipped_label.text = str(
                        skipped_count
                    )

                # -------------------------------------------------
                # OK
                # -------------------------------------------------

                if "[QWEN] OK |" in text:

                    ok_count += 1
                    ok_label.text = str(
                        ok_count
                    )

                    time_match = re.search(
                        r"time:\s*([\d.]+)\s*sec",
                        text,
                    )

                    if time_match:

                        times.append(
                            float(
                                time_match.group(1)
                            )
                        )

                    conf_match = re.search(
                        r"confidence:\s*([\d.]+)",
                        text,
                    )

                    if conf_match:

                        confidences.append(
                            float(
                                conf_match.group(1)
                            )
                        )

                    if times:

                        avg_time_label.text = (
                            f"{sum(times) / len(times):.2f} сек"
                        )

                    if confidences:

                        avg_confidence_label.text = (
                            f"{sum(confidences) / len(confidences):.1f}%"
                        )

                # -------------------------------------------------
                # ERROR
                # -------------------------------------------------

                if (
                    "[QWEN] ERROR" in text
                    or "[QWEN] FAILED" in text
                ):

                    error_count += 1

                    errors_label.text = str(
                        error_count
                    )

                # -------------------------------------------------
                # ADDRESS
                # -------------------------------------------------

                address_match = re.search(
                    r"address:\s*([^|]+)",
                    text,
                    re.IGNORECASE,
                )

                if address_match:

                    address = (
                        address_match.group(1)
                        .strip()
                    )

                    if address:
                        addresses.add(address)
                        addresses_label.text = str(
                            len(addresses)
                        )

                # -------------------------------------------------
                # STOP REQUEST
                # -------------------------------------------------

                if qwen_stop_requested:

                    state_label.text = (
                        f"ОСТАНОВКА: "
                        f"{current}/{total_images}"
                    )

            returncode = await process.wait()

            print(
                f"[QWEN MANUAL] FINISHED "
                f"returncode={returncode}",
                flush=True,
            )

            if qwen_stop_requested:

                state_label.text = "ОСТАНОВЛЕН"
                status_label.text = "● ОСТАНОВЛЕН"

                ui.notify(
                    f"Qwen остановлен: "
                    f"{current}/{total_images}",
                    type="warning",
                    timeout=6000,
                )

            elif returncode == 0:

                state_label.text = "ГОТОВ"
                status_label.text = "● ГОТОВ"

                ui.notify(
                    "✓ Qwen3-VL 4B завершён",
                    type="positive",
                    timeout=6000,
                )

                refresh()

            else:

                state_label.text = "ОШИБКА"
                status_label.text = "● QWEN: ОШИБКА"

                ui.notify(
                    f"Qwen завершился с ошибкой: {returncode}",
                    type="negative",
                    timeout=10000,
                )

        except Exception as exc:

            print(
                f"[QWEN MANUAL] EXCEPTION: {exc!r}",
                flush=True,
            )

            state_label.text = "ОШИБКА"
            status_label.text = "● QWEN: ОШИБКА"

            try:
                ui.notify(
                    f"Ошибка запуска Qwen: {exc}",
                    type="negative",
                    timeout=10000,
                )
            except Exception:
                pass

        finally:

            qwen_process = None
            qwen_stop_requested = False

            try:
                run_button.enable()
            except Exception:
                pass

            try:
                stop_button.disable()
            except Exception:
                pass

            try:
                refresh()
            except Exception as exc:
                print(
                    f"[QWEN MANUAL] UI REFRESH FAILED: {exc!r}",
                    flush=True,
                )

    def refresh():

        data = _load_qwen_status()

        state_label.text = data["state"]

        run_label.text = (
            data["run"]
            if data.get("run")
            else "—"
        )

        model_label.text = data["model"]

        processed_label.text = str(
            data["processed"]
        )

        ok_label.text = str(
            data["ok"]
        )

        skipped_label.text = str(
            data["skipped"]
        )

        errors_label.text = str(
            data["errors"]
        )

        addresses_label.text = str(
            data["addresses"]
        )

        avg_time_label.text = (
            f'{data["avg_time"]:.2f} сек'
        )

        avg_confidence_label.text = (
            f'{data["avg_confidence"]:.1f}%'
        )

        if data["state"] == "ГОТОВ":
            status_label.text = "● ГОТОВ"

        elif data["state"] == "НЕТ ДАННЫХ":
            status_label.text = "● НЕТ ДАННЫХ"

        else:
            status_label.text = "● ОШИБКА"

        if data.get("summary"):

            source_label.text = (
                f'Источник: {data["summary"]}'
            )

        if data.get("error"):

            source_label.text = (
                f'Ошибка: {data["error"]}'
            )
    run_button.on_click(run_qwen)
    stop_button.on_click(stop_qwen)
    refresh_button.on_click(refresh)

    refresh()

    ui.timer(
        5.0,
        refresh,
    )

============================================================
FILE: app/pipeline/controller.py
============================================================
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

============================================================
FILE: app/pipeline/modes.py
============================================================
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Optional

MODE_MANUAL = "manual"
MODE_AUTOMATIC = "automatic"
MODE_WATCHER = "watcher"

VALID_MODES = {
    MODE_MANUAL,
    MODE_AUTOMATIC,
    MODE_WATCHER,
}

@dataclass
class PipelineMode:
    mode: str = MODE_MANUAL

    auto_enabled: bool = False
    auto_time: Optional[time] = None

    watcher_enabled: bool = False
    watcher_path: Optional[str] = None

    running: bool = False
    stop_requested: bool = False

def validate_mode(mode: str) -> str:
    if mode not in VALID_MODES:
        raise ValueError(
            f"Unknown pipeline mode: {mode}"
        )

    return mode

def build_manual_mode() -> PipelineMode:
    return PipelineMode(
        mode=MODE_MANUAL,
        auto_enabled=False,
        auto_time=None,
        watcher_enabled=False,
        watcher_path=None,
        running=False,
        stop_requested=False,
    )

def build_automatic_mode(
    auto_time: time,
) -> PipelineMode:

    return PipelineMode(
        mode=MODE_AUTOMATIC,
        auto_enabled=True,
        auto_time=auto_time,
        watcher_enabled=False,
        watcher_path=None,
        running=False,
        stop_requested=False,
    )

def build_watcher_mode(
    watcher_path: str,
) -> PipelineMode:

    if not watcher_path:
        raise ValueError(
            "Watcher path is required"
        )

    return PipelineMode(
        mode=MODE_WATCHER,
        auto_enabled=False,
        auto_time=None,
        watcher_enabled=True,
        watcher_path=watcher_path,
        running=False,
        stop_requested=False,
    )

def can_manual_start(state: PipelineMode) -> bool:
    """
    Кнопка «Запустить» доступна только
    в ручном режиме.
    """

    return (
        state.mode == MODE_MANUAL
        and not state.running
    )

def can_stop(state: PipelineMode) -> bool:
    return state.running

def reset_to_manual() -> PipelineMode:
    """
    Полный возврат в ручной режим.

    Используется после нажатия «Остановить».
    """

    return build_manual_mode()

============================================================
FILE: app/pipeline/queue.py
============================================================
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

class JobQueue:
    """
    Persistent SQLite job queue.

    States:
        PENDING
        PROCESSING
        DONE
        FAILED
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
        )

        connection.row_factory = sqlite3.Row

        return connection

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).isoformat()

    def _init_db(self):
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    source_folder TEXT NOT NULL,
                    fingerprint_id TEXT NOT NULL,

                    status TEXT NOT NULL
                        DEFAULT 'PENDING',

                    priority INTEGER NOT NULL
                        DEFAULT 0,

                    attempts INTEGER NOT NULL
                        DEFAULT 0,

                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,

                    error TEXT
                )
                """
            )

            db.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_jobs_status_priority
                ON jobs(status, priority DESC, id)
                """
            )

    def add(
        self,
        source_folder: str | Path,
        fingerprint_id: str,
        priority: int = 0,
    ):
        created_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO jobs (
                    source_folder,
                    fingerprint_id,
                    status,
                    priority,
                    attempts,
                    created_at
                )
                VALUES (?, ?, 'PENDING', ?, 0, ?)
                """,
                (
                    str(source_folder),
                    str(fingerprint_id),
                    int(priority),
                    created_at,
                ),
            )

            return int(cursor.lastrowid)

    def list(
        self,
        status: str | None = None,
    ):
        with self._connect() as db:

            if status is None:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    ORDER BY
                        priority DESC,
                        id ASC
                    """
                )
            else:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE status = ?
                    ORDER BY
                        priority DESC,
                        id ASC
                    """,
                    (status,),
                )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    def claim(self):
        """
        Atomically take the next PENDING job.

        Returns:
            dict with job data, or None if queue is empty.
        """

        with self._connect() as db:

            db.execute("BEGIN IMMEDIATE")

            cursor = db.execute(
                """
                SELECT *
                FROM jobs
                WHERE status = 'PENDING'
                ORDER BY
                    priority DESC,
                    id ASC
                LIMIT 1
                """
            )

            row = cursor.fetchone()

            if row is None:
                db.commit()
                return None

            job_id = row["id"]
            started_at = self._now()

            db.execute(
                """
                UPDATE jobs
                SET
                    status = 'PROCESSING',
                    attempts = attempts + 1,
                    started_at = ?,
                    error = NULL
                WHERE
                    id = ?
                    AND status = 'PENDING'
                """,
                (
                    started_at,
                    job_id,
                ),
            )

            db.commit()

            return dict(
                db.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE id = ?
                    """,
                    (job_id,),
                ).fetchone()
            )

    def complete(self, job_id):
        """
        Mark a processing job as DONE.
        """

        finished_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE jobs
                SET
                    status = 'DONE',
                    finished_at = ?,
                    error = NULL
                WHERE
                    id = ?
                    AND status = 'PROCESSING'
                """,
                (
                    finished_at,
                    int(job_id),
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Cannot complete job {job_id}"
                )

    def fail(self, job_id, error):
        """
        Mark a processing job as FAILED.
        """

        finished_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE jobs
                SET
                    status = 'FAILED',
                    finished_at = ?,
                    error = ?
                WHERE
                    id = ?
                    AND status = 'PROCESSING'
                """,
                (
                    finished_at,
                    str(error),
                    int(job_id),
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Cannot fail job {job_id}"
                )

    def counts(self):
        with self._connect() as db:
            cursor = db.execute(
                """
                SELECT
                    status,
                    COUNT(*) AS count
                FROM jobs
                GROUP BY status
                """
            )

            return {
                row["status"]: row["count"]
                for row in cursor.fetchall()
            }

if __name__ == "__main__":
    queue = JobQueue(
        "data/jobs.db"
    )

    print("Queue:", queue.db_path)
    print("Counts:", queue.counts())

============================================================
FILE: app/workers/dino_worker.py
============================================================
from __future__ import annotations

import os
import time
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import Settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer

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

def reset_processing(conn):
    """
    Возвращает зависшие DINO-задачи обратно в очередь.

    Это позволяет продолжить работу после:
        - остановки процесса
        - перезагрузки
        - падения Python
        - аварии машины
    """

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'pending',
                updated_at = CURRENT_TIMESTAMP
            WHERE dino_status = 'processing'
            """
        )

        count = cur.rowcount

    conn.commit()

    if count:
        print(
            f"[DINO] Reset stale processing jobs: {count}"
        )

def claim_photo(conn):
    """
    Забирает следующую фотографию из DINO-очереди.

    ВАЖНО:

    Qwen здесь вообще не учитывается.

    DINO получает фотографию только потому,
    что у неё уже существует photo_id и
    dino_status = pending.
    """

    with conn.cursor(
        cursor_factory=RealDictCursor
    ) as cur:

        cur.execute(
            """
            SELECT
                id,
                photo_id,
                initial_id,
                source_path,
                filename
            FROM photos
            WHERE
                dino_status = 'pending'
                AND source_path IS NOT NULL
                AND source_path <> ''
            ORDER BY id
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )

        row = cur.fetchone()

        if row is None:
            conn.commit()
            return None

        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE
                id = %s
                AND dino_status = 'pending'
            """,
            (row["id"],),
        )

        conn.commit()

        return row

# ============================================================
# RESULT
# ============================================================

def mark_done(
    conn,
    db_id,
    result,
    elapsed,
):
    """
    Сохраняет результат DINO.

    Главный результат нового слоя:

        address_id = адрес, определённый DINO.

    photo_id остаётся независимым идентификатором фотографии.
    """

    address_id = result.get("best_id")

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'done',

                address_id = %s,

                dino_fingerprint = %s,
                dino_score = %s,
                dino_second_score = %s,
                dino_margin = %s,
                dino_time_sec = %s,

                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = %s
            """,
            (
                address_id,

                # Старое поле оставляем для совместимости
                # со старым кодом и статистикой.
                address_id,

                result.get("score"),
                result.get("second_score"),
                result.get("margin"),

                elapsed,

                db_id,
            ),
        )

    conn.commit()

def mark_error(
    conn,
    db_id,
    error,
):
    """
    Фиксирует ошибку конкретной фотографии.

    Qwen-status при этом НЕ меняется.
    """

    message = str(error)

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                dino_status = 'error',
                error_message = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                message[:4000],
                db_id,
            ),
        )

    conn.commit()

# ============================================================
# WORKER
# ============================================================

def main():

    settings = Settings()

    print("=" * 70)
    print("DINO WORKER")
    print("=" * 70)
    print("device  :", settings.device)
    print("database:", DB_CONFIG["dbname"])
    print("=" * 70)

    # --------------------------------------------------------
    # MODEL
    # --------------------------------------------------------

    print("[DINO] Loading SceneEmbedder...")

    embedder = SceneEmbedder(settings)

    manager = FingerprintManager(
        settings,
        embedder,
    )

    recognizer = SceneRecognizer(
        settings,
        embedder,
        manager,
    )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    conn = get_connection()

    print("[DINO] Database connected.")

    # --------------------------------------------------------
    # RECOVERY
    # --------------------------------------------------------

    reset_processing(conn)

    print("[DINO] Worker ready.")

    max_items = int(
        os.getenv(
            "DINO_MAX_ITEMS",
            "0",
        )
    )

    processed = 0
    errors = 0

    try:

        while True:

            # ------------------------------------------------
            # LIMIT
            # ------------------------------------------------

            if (
                max_items > 0
                and processed >= max_items
            ):
                print(
                    f"[DINO] "
                    f"Reached max_items={max_items}."
                )
                break

            # ------------------------------------------------
            # CLAIM
            # ------------------------------------------------

            row = claim_photo(conn)

            if row is None:

                print(
                    "[DINO] Queue empty."
                )

                break

            db_id = row["id"]
            photo_id = row["photo_id"]
            initial_id = row["initial_id"]
            source_path = Path(
                row["source_path"]
            )

            print()
            print("-" * 70)

            print(
                "[DINO]",
                photo_id,
                "| initial_id:",
                initial_id,
                "| file:",
                source_path.name,
            )

            started = time.perf_counter()

            # ------------------------------------------------
            # PROCESS
            # ------------------------------------------------

            try:

                if not source_path.exists():
                    raise FileNotFoundError(
                        f"Photo not found: {source_path}"
                    )

                if not source_path.is_file():
                    raise FileNotFoundError(
                        f"Not a file: {source_path}"
                    )

                result = recognizer.recognize_one(
                    source_path,
                    top_k=5,
                    threshold=0.65,
                )

                elapsed = (
                    time.perf_counter()
                    - started
                )

                # ------------------------------------------------
                # SAVE
                # ------------------------------------------------

                mark_done(
                    conn,
                    db_id,
                    result,
                    elapsed,
                )

                address_id = result.get(
                    "best_id"
                )

                print(
                    f"[DINO] DONE "
                    f"{photo_id}"
                    f" -> address_id={address_id}"
                    f" score={result.get('score', 0):.6f}"
                    f" margin={result.get('margin', 0):.6f}"
                    f" time={elapsed:.2f}s"
                )

                processed += 1

            # ------------------------------------------------
            # ERROR
            # ------------------------------------------------

            except Exception as exc:

                errors += 1

                elapsed = (
                    time.perf_counter()
                    - started
                )

                print(
                    f"[DINO] ERROR "
                    f"{photo_id}: {exc}"
                    f" time={elapsed:.2f}s"
                )

                try:

                    mark_error(
                        conn,
                        db_id,
                        exc,
                    )

                except Exception as db_error:

                    print(
                        "[DINO] "
                        "DB ERROR while marking error:",
                        db_error,
                    )

    finally:

        conn.close()

        print()
        print("=" * 70)
        print("DINO WORKER STOPPED")
        print("=" * 70)

        print(
            "PROCESSED:",
            processed,
        )

        print(
            "ERRORS:",
            errors,
        )

if __name__ == "__main__":
    main()

============================================================
FILE: app/workers/qwen_worker.py
============================================================
from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

import psycopg2
import requests
from psycopg2.extras import RealDictCursor

# ============================================================
# DATABASE
# ============================================================

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
}

# ============================================================
# QWEN
# ============================================================

MODEL = "qwen3-vl:4b-instruct"
OLLAMA_URL = "http://localhost:11434/api/chat"

NUM_CTX = 16384
TEMPERATURE = 0

# ============================================================
# PROMPT
# ============================================================

PROMPT = r"""
Ты анализируешь фотографию с улицы для базы наружной рекламы.

Найди рекламный баннер и верни ТОЛЬКО JSON.
Не добавляй пояснений вне JSON.
Не повторяй информацию.
Не придумывай отсутствующую информацию.

Формат:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "banner_type": "видеоэкран",

  "environment": {
    "weather": "",
    "precipitation": "",
    "lighting": ""
  },

  "image_quality": {
    "overall": "",
    "sharpness": "",
    "exposure": "",
    "visibility": "",
    "banner_visible": true,
    "banner_readability": "",
    "motion_blur": false,
    "occlusion": false
  },

  "camera_view": {
    "distance": "",
    "angle": ""
  },

  "analysis_quality": {
    "banner_analysis": "",
    "text_analysis": ""
  },

  "confidence": 0
}

БАННЕР:
client — компания, организация или заказчик.
brand — торговая марка, имя кандидата или рекламируемый бренд.
category — категория рекламы.
text — читаемые надписи на баннере.
colors — основные цвета самого баннера.
objects — основные изображения и предметы НА БАННЕРЕ.
description — краткое описание композиции баннера, максимум 300 символов.
banner_type — на данном этапе "видеоэкран".

ОКРУЖЕНИЕ:
Определи ТОЛЬКО:
weather — солнечно / пасмурно / облачно / туман / неизвестно.
precipitation — нет / дождь / снег / мокрый снег / неизвестно.
lighting — яркий день / дневной свет / сумерки / ночь / искусственное освещение / неизвестно.

Не описывай окружающую сцену.
Не описывай здания, дороги, автомобили, автобусы, людей,
дорожные знаки, провода или растительность.

КАЧЕСТВО:
Оцени только качество фотографии и видимость баннера.

overall — хорошее / удовлетворительное / плохое.
sharpness — резкое / слегка размыто / сильно размыто / неизвестно.
exposure — нормальная / пересвечено / недоэкспонировано / очень тёмное / неизвестно.
visibility — хорошо виден / частично виден / плохо виден / не виден.
banner_visible — true или false.
banner_readability — высокая / средняя / низкая / невозможно определить.
motion_blur — true или false.
occlusion — true или false.

КАМЕРА:
distance — далеко / средняя дистанция / близко / неизвестно.
angle — прямо / слева / справа / сверху / снизу / косой ракурс / неизвестно.

Если баннер не виден:
client = ""
brand = ""
category = ""
text = []
colors = []
objects = []
description = ""
banner_visible = false

Массивы должны содержать только действительно важные элементы.
Не более 10 элементов в каждом массиве.
Не повторяй элементы.

confidence — уверенность в анализе от 0 до 100.
"""

# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def claim_photo(conn):
    """
    Берём следующую фотографию, которая ещё не обработана Qwen.

    ВАЖНО:
        Qwen работает независимо от DINO.

    Единственная связь:
        photo_id -> результат Qwen

    address_id здесь НЕ используется.
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:

        cur.execute(
            """
            SELECT
                id,
                photo_id,
                source_path,
                filename
            FROM photos
            WHERE qwen_status = 'pending'
              AND source_path IS NOT NULL
              AND source_path <> ''
            ORDER BY id
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )

        row = cur.fetchone()

        if row is None:
            conn.commit()
            return None

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND qwen_status = 'pending'
            """,
            (row["id"],),
        )

        conn.commit()

        return row

def mark_done(
    conn,
    db_id,
    result,
    elapsed,
):
    """
    Сохраняет результат Qwen.

    db_id — внутренний bigint photos.id.

    photo_id остаётся постоянным идентификатором
    фотографии и не зависит от адреса.
    """

    text_json = result.get("text", [])
    colors_json = result.get("colors", [])
    objects_json = result.get("objects", [])
    environment_json = result.get("environment", {})
    image_quality_json = result.get("image_quality", {})
    camera_view_json = result.get("camera_view", {})
    analysis_quality_json = result.get(
        "analysis_quality",
        {},
    )

    raw_json = dict(result)
    raw_json.pop("_time_sec", None)

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'done',

                client = %s,
                brand = %s,
                category = %s,
                description = %s,
                confidence = %s,

                qwen_time_sec = %s,

                text_json = %s::jsonb,
                colors_json = %s::jsonb,
                objects_json = %s::jsonb,
                environment_json = %s::jsonb,
                image_quality_json = %s::jsonb,
                camera_view_json = %s::jsonb,
                analysis_quality_json = %s::jsonb,
                raw_json = %s::jsonb,

                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = %s
            """,
            (
                result.get("client") or None,
                result.get("brand") or None,
                result.get("category") or None,
                result.get("description") or None,
                result.get("confidence"),

                elapsed,

                json.dumps(
                    text_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    colors_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    objects_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    environment_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    image_quality_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    camera_view_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    analysis_quality_json,
                    ensure_ascii=False,
                ),
                json.dumps(
                    raw_json,
                    ensure_ascii=False,
                ),

                db_id,
            ),
        )

    conn.commit()

def mark_error(
    conn,
    db_id,
    error,
):
    message = str(error)

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE photos
            SET
                qwen_status = 'error',
                error_message = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                message[:4000],
                db_id,
            ),
        )

    conn.commit()

# ============================================================
# IMAGE
# ============================================================

def image64(path: Path):
    with open(path, "rb") as f:
        return base64.b64encode(
            f.read()
        ).decode()

# ============================================================
# QWEN REQUEST
# ============================================================

def ask(path: Path):

    max_attempts = 2

    for attempt in range(
        1,
        max_attempts + 1,
    ):

        payload = {
            "model": MODEL,

            "messages": [
                {
                    "role": "user",
                    "content": PROMPT,
                    "images": [
                        image64(path)
                    ],
                }
            ],

            "stream": False,

            "options": {
                "num_ctx": NUM_CTX,
                "temperature": TEMPERATURE,
                "num_predict": 800,
            },
        }

        started = time.time()

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=1800,
        )

        elapsed = time.time() - started

        if response.status_code != 200:
            raise RuntimeError(
                response.text
            )

        data = response.json()

        print(
            "[OLLAMA]",
            {
                "total_duration_sec":
                    round(
                        data.get(
                            "total_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "load_duration_sec":
                    round(
                        data.get(
                            "load_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "prompt_eval_duration_sec":
                    round(
                        data.get(
                            "prompt_eval_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "eval_duration_sec":
                    round(
                        data.get(
                            "eval_duration",
                            0,
                        ) / 1e9,
                        2,
                    ),
                "prompt_eval_count":
                    data.get(
                        "prompt_eval_count"
                    ),
                "eval_count":
                    data.get(
                        "eval_count"
                    ),
            },
            flush=True,
        )

        answer = data[
            "message"
        ][
            "content"
        ]

        cleaned = answer.strip()

        if cleaned.startswith("```"):

            cleaned = cleaned.replace(
                "```json",
                "",
                1,
            )

            cleaned = cleaned.replace(
                "```",
                "",
            ).strip()

        try:

            result = json.loads(
                cleaned
            )

            description = str(
                result.get(
                    "description"
                ) or ""
            ).strip()

            if description:
                result["_time_sec"] = round(
                    elapsed,
                    2,
                )

                return result

            if attempt < max_attempts:

                print(
                    "[QWEN RETRY]",
                    "description empty",
                    "| attempt:",
                    attempt + 1,
                    flush=True,
                )

                continue

            result["_time_sec"] = round(
                elapsed,
                2,
            )

            return result

        except Exception as exc:

            print(
                "[QWEN JSON ERROR]",
                repr(exc),
                "| attempt:",
                attempt,
                flush=True,
            )

            if attempt < max_attempts:
                continue

            result = {
                "raw_answer": answer,
            }

            result["_time_sec"] = round(
                elapsed,
                2,
            )

            return result

# ============================================================
# WORKER
# ============================================================

def main():

    print("=" * 80)
    print("QWEN3-VL 4B — DATABASE WORKER")
    print("=" * 80)
    print("MODEL   :", MODEL)
    print("DATABASE:", DB_CONFIG["dbname"])
    print()
    print(
        "[QWEN] Works independently from DINO."
    )
    print(
        "[QWEN] Source: photos.source_path"
    )
    print(
        "[QWEN] Identity: photos.photo_id"
    )
    print()

    conn = get_connection()

    processed = 0
    errors = 0

    max_items = int(
        os.getenv(
            "QWEN_MAX_ITEMS",
            "0",
        )
    )

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT COUNT(*)
                FROM photos
                WHERE qwen_status = 'pending'
                """
            )

            pending = cur.fetchone()[0]

        print(
            "PENDING:",
            pending,
        )
        print()

        while True:

            if (
                max_items > 0
                and processed >= max_items
            ):

                print(
                    "[QWEN] Reached "
                    f"max_items={max_items}."
                )

                break

            row = claim_photo(
                conn
            )

            if row is None:

                print(
                    "[QWEN] Queue empty."
                )

                break

            db_id = row["id"]
            photo_id = row["photo_id"]
            source_path = Path(
                row["source_path"]
            )

            print("=" * 80)
            print(
                f"[QWEN] {photo_id}"
            )
            print(
                "SOURCE:",
                source_path,
            )

            started = time.time()

            try:

                if not source_path.exists():
                    raise FileNotFoundError(
                        f"Photo not found: "
                        f"{source_path}"
                    )

                if not source_path.is_file():
                    raise FileNotFoundError(
                        f"Not a file: "
                        f"{source_path}"
                    )

                result = ask(
                    source_path
                )

                elapsed = (
                    time.time()
                    - started
                )

                mark_done(
                    conn,
                    db_id,
                    result,
                    elapsed,
                )

                print(
                    "[QWEN] DONE",
                    photo_id,
                    "| time:",
                    round(
                        elapsed,
                        2,
                    ),
                    "sec",
                    "| client:",
                    result.get(
                        "client",
                        "",
                    ),
                    "| brand:",
                    result.get(
                        "brand",
                        "",
                    ),
                    "| confidence:",
                    result.get(
                        "confidence",
                        "",
                    ),
                )

                print(
                    "DESCRIPTION:",
                    result.get(
                        "description",
                        "",
                    ),
                )

                processed += 1

            except Exception as exc:

                errors += 1

                elapsed = (
                    time.time()
                    - started
                )

                print(
                    "[QWEN] ERROR",
                    photo_id,
                    ":",
                    exc,
                    "| time:",
                    round(
                        elapsed,
                        2,
                    ),
                )

                try:

                    mark_error(
                        conn,
                        db_id,
                        exc,
                    )

                except Exception as db_error:

                    print(
                        "[QWEN] DB ERROR:",
                        db_error,
                    )

    finally:

        conn.close()

        print()
        print("=" * 80)
        print("QWEN WORKER STOPPED")
        print("=" * 80)
        print(
            "PROCESSED:",
            processed,
        )
        print(
            "ERRORS:",
            errors,
        )

if __name__ == "__main__":
    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

