## СЕССИЯ: Продолжение разговора 1

**Создано:** 2026-08-18 12:11:53
**Обновлено:** 2026-08-19 17:07:58
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8421d7-3160-83ea-be54-4a2ad097babc](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8421d7-3160-83ea-be54-4a2ad097babc)

---

### 👤 **User** — 2026-08-18 12:54:40

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== QWEN MODULE ====="
sed -n '1,430p' app/web/components/technical_modules/qwen.py

echo
echo "===== PHOTO PROCESSING ====="
sed -n '1,430p' app/web/components/technical_modules/photo_processing.py

echo
echo "===== QWEN / PIPELINE REFERENCES ====="
grep -R -n -E \
'Qwen|qwen|run_pipeline|subprocess|Popen' \
app/web scripts \
--include='*.py' \
--exclude-dir='__pycache__' \
| head -250
===== QWEN MODULE =====
from nicegui import ui

def build_qwen():
    with ui.card().classes("w-full"):
        ui.label("РАСПОЗНАВАНИЕ").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        ui.label(
            "Qwen3-VL 4B"
        ).classes("text-base font-medium")

        ui.label(
            "● Рабочая модель"
        ).classes("text-sm")

        ui.checkbox(
            "Автоматически запускать после DINO",
            value=True,
        ).props("dense")

        with ui.row().classes("gap-2"):
            ui.button(
                "⚙  Настройки распознавания",
                on_click=lambda: ui.notify(
                    "Настройки Qwen будут подключены следующим этапом"
                ),
            ).props("flat")

            ui.button(
                "▶  Повторно запустить Qwen",
                on_click=lambda: ui.notify(
                    "Повторный запуск Qwen будет подключён следующим этапом"
                ),
            ).props("unelevated")

===== PHOTO PROCESSING =====
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

===== QWEN / PIPELINE REFERENCES =====
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:59:            qwen_status,
app/web/components/search.py:60:            qwen_time_sec,
app/web/components/technical_modules/photo_processing.py:36:    async def run_pipeline():
app/web/components/technical_modules/photo_processing.py:99:            process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:104:                stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/photo_processing.py:105:                stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/photo_processing.py:194:            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"
app/web/components/technical_modules/photo_processing.py:196:            if not qwen_script.exists():
app/web/components/technical_modules/photo_processing.py:199:                    "✓ Hybrid завершён → Qwen script не найден"
app/web/components/technical_modules/photo_processing.py:203:                    f"Не найден Qwen script: {qwen_script}",
app/web/components/technical_modules/photo_processing.py:214:            qwen_output = (
app/web/components/technical_modules/photo_processing.py:218:                / "qwen4b"
app/web/components/technical_modules/photo_processing.py:222:            qwen_output.mkdir(
app/web/components/technical_modules/photo_processing.py:228:                "▶ Qwen3-VL 4B: выполняется..."
app/web/components/technical_modules/photo_processing.py:233:                "Запускается Qwen3-VL 4B.",
app/web/components/technical_modules/photo_processing.py:240:                qwen_process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:242:                    str(qwen_script),
app/web/components/technical_modules/photo_processing.py:246:                    str(qwen_output),
app/web/components/technical_modules/photo_processing.py:248:                    stdout=asyncio.subprocess.PIPE,
app/web/components/technical_modules/photo_processing.py:249:                    stderr=asyncio.subprocess.STDOUT,
app/web/components/technical_modules/photo_processing.py:252:                qwen_lines = []
app/web/components/technical_modules/photo_processing.py:256:                    line = await qwen_process.stdout.readline()
app/web/components/technical_modules/photo_processing.py:266:                    qwen_lines.append(text)
app/web/components/technical_modules/photo_processing.py:271:                qwen_returncode = await qwen_process.wait()
app/web/components/technical_modules/photo_processing.py:273:                if qwen_returncode != 0:
app/web/components/technical_modules/photo_processing.py:277:                        "Qwen3-VL 4B: ошибка"
app/web/components/technical_modules/photo_processing.py:282:                        "но Qwen3-VL 4B завершился с ошибкой.",
app/web/components/technical_modules/photo_processing.py:290:                    "✓ Hybrid v12 + Qwen3-VL 4B: готово"
app/web/components/technical_modules/photo_processing.py:299:                    "Hybrid v12 + Qwen3-VL 4B.",
app/web/components/technical_modules/photo_processing.py:304:            except Exception as qwen_error:
app/web/components/technical_modules/photo_processing.py:308:                    "Qwen3-VL 4B: ошибка запуска"
app/web/components/technical_modules/photo_processing.py:312:                    f"Ошибка запуска Qwen: {qwen_error}",
app/web/components/technical_modules/photo_processing.py:384:            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
app/web/components/technical_modules/photo_processing.py:391:            on_click=run_pipeline,
app/web/components/technical_modules/qwen.py:4:def build_qwen():
app/web/components/technical_modules/qwen.py:13:            "Qwen3-VL 4B"
app/web/components/technical_modules/qwen.py:29:                    "Настройки Qwen будут подключены следующим этапом"
app/web/components/technical_modules/qwen.py:34:                "▶  Повторно запустить Qwen",
app/web/components/technical_modules/qwen.py:36:                    "Повторный запуск Qwen будет подключён следующим этапом"
app/web/components/photos.py:445:                        if value("qwen_status") != "—":
app/web/components/photos.py:448:                                f"Qwen: {value('qwen_status')}"
app/web/components/technical.py:12:from app.web.components.technical_modules.qwen import (
app/web/components/technical.py:13:    build_qwen,
app/web/components/technical.py:175:                    "qwen",
app/web/components/technical.py:176:                    label="Qwen",
app/web/components/technical.py:230:                    with ui.tab_panel("qwen"):
app/web/components/technical.py:231:                        build_qwen()
app/web/client_aliases.py:4:Qwen может распознавать одно и то же название с ошибками,
app/web/photo_db.py:28:            qwen_status,
app/web/photo_db.py:29:            qwen_time_sec,
app/web/system/monitor.py:3:import subprocess
app/web/system/monitor.py:27:        result = subprocess.run(
scripts/sort_test_and_report_v2.py:7:import subprocess
scripts/sort_test_and_report_v2.py:33:        result = subprocess.run(
scripts/sort_test_and_report_v2.py:120:    process = subprocess.run(
scripts/benchmark_test_v1.py:5:import subprocess
scripts/benchmark_test_v1.py:113:    proc = subprocess.run(
scripts/benchmark_test_sub_exp.py:5:import subprocess
scripts/benchmark_test_sub_exp.py:132:    proc = subprocess.run(
scripts/banner_model_compare_v04.py:19:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v04.py:20:    "qwen2.5vl:3b",
scripts/banner_qwen25vl_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen25vl_test_v01")
scripts/banner_qwen25vl_test_v01.py:14:MODEL = "qwen2.5vl:3b"
scripts/banner_model_compare_v05.py:16:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v05.py:17:    "qwen2.5vl:3b",
scripts/banner_llm_full_v02.py:11:MODEL = "qwen3-vl:4b-instruct"
scripts/import_qwen_to_db.py:10:QWEN_DIR = PROJECT / "data/metadata/qwen4b"
scripts/import_qwen_to_db.py:53:            qwen_status TEXT,
scripts/import_qwen_to_db.py:54:            qwen_time_sec REAL,
scripts/import_qwen_to_db.py:90:        ON photos(qwen_status)
scripts/import_qwen_to_db.py:178:            qwen_status,
scripts/import_qwen_to_db.py:179:            qwen_time_sec,
scripts/import_qwen_to_db.py:216:            qwen_status = excluded.qwen_status,
scripts/import_qwen_to_db.py:217:            qwen_time_sec = excluded.qwen_time_sec,
scripts/sort_test_and_report_hybrid_v12.py:7:import subprocess
scripts/sort_test_and_report_hybrid_v12.py:33:        result = subprocess.run(
scripts/sort_test_and_report_hybrid_v12.py:120:    process = subprocess.run(
scripts/banner_qwen4b_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen4b_test_v01")
scripts/banner_qwen4b_test_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/run_hybrid_v12.py:6:import subprocess
scripts/run_hybrid_v12.py:129:    process = subprocess.run(
scripts/banner_llm_folder_search_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01_before_compact_prompt.py:15:OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"
scripts/qwen4b_output_v01_before_compact_prompt.py:17:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01.py:15:OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"
scripts/qwen4b_output_v01.py:17:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01.py:469:        help="Output directory for Qwen metadata"
scripts/banner_llm_full_v01.py:9:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_model_compare_v02.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v02.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v01.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v01.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_database_v02.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/migrate_sqlite_to_postgres.py:75:                qwen_status,
scripts/migrate_sqlite_to_postgres.py:76:                qwen_time_sec,
scripts/migrate_sqlite_to_postgres.py:111:                row["qwen_status"],
scripts/migrate_sqlite_to_postgres.py:112:                row["qwen_time_sec"],
scripts/migrate_sqlite_to_postgres.py:165:                    qwen_status,
scripts/migrate_sqlite_to_postgres.py:166:                    qwen_time_sec,
scripts/banner_database_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/llm_resolver_v01.py:5:import subprocess
scripts/llm_resolver_v01.py:11:MODEL = "qwen3:4b"
scripts/llm_resolver_v01.py:166:    result = subprocess.run(
scripts/qwen_prompt_ablation.py:15:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_model_compare_v03.py:19:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v03.py:20:    "qwen3-vl:2b-instruct",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,280p' app/web/components/technical.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,280p' app/web/components/technical.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat app/web/components/technical_modules/data.py
from nicegui import ui

def build_data():
    with ui.card().classes("w-full"):
        ui.label("ДАННЫЕ").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        with ui.row().classes("gap-6"):
            ui.label("Клиентов: 7")
            ui.label("Адресов: 18")
            ui.label("Правил исправления: 0")

        with ui.row().classes("gap-2"):
            ui.button(
                "Клиенты",
                icon="business",
            ).props("flat")

            ui.button(
                "Адреса",
                icon="place",
            ).props("flat")

            ui.button(
                "Реестр исправлений",
                icon="edit_note",
            ).props("flat")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:54:42

Да. Сейчас у нас уже есть **фактический индекс 526 фото**, поэтому в `Данные` лучше убрать захардкоженные значения и сделать живую статистику.

Предлагаю первый вариант вкладки **«Данные»**:

- Клиентов: **7**
- Адресов: **18**
- Фотографий: **526**
- По адресам — количество фото
- Последний daily-run: `20260818_115048`
- Папка результата
- Qwen — пока отдельно, без выдумывания статистики

Причём статистика должна брать данные из тех же `STATE.addresses` и `PHOTO_INDEX`, которые уже используются UI.

### 1. Сначала покажи `state.py`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat app/web/state.py
```

И ещё:

```bash
grep -R -n \
"PHOTO_INDEX\|STATE.addresses\|clients" \
app/web \
--include="*.py" \
--exclude-dir="__pycache__" \
| head -100
```

**Пока ничего не меняем.**

Нам важно правильно подключить статистику к уже работающему индексу, чтобы не получить вторую независимую систему подсчёта.

После этого я дам готовую замену `data.py`, и в техническом разделе появится примерно:

```text
ДАННЫЕ

Клиентов       7
Адресов        18
Фотографий     526

Последний запуск
20260818_115048

ФОТО ПО АДРЕСАМ
78    89
79    33
...
94   120
95    18
```

И это будет **автоматически пересчитываться при открытии технического раздела**, а не вручную прописанные цифры.

---

### 👤 **User** — 2026-08-18 12:55:07

if initial_tab:
        ui.timer(
            0.05,
            lambda: tabs.set_value(initial_tab),
            once=True,
        )

    _restore_and_watch_size()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat app/web/components/technical_modules/data.py
from nicegui import ui

def build_data():
    with ui.card().classes("w-full"):
        ui.label("ДАННЫЕ").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        with ui.row().classes("gap-6"):
            ui.label("Клиентов: 7")
            ui.label("Адресов: 18")
            ui.label("Правил исправления: 0")

        with ui.row().classes("gap-2"):
            ui.button(
                "Клиенты",
                icon="business",
            ).props("flat")

            ui.button(
                "Адреса",
                icon="place",
            ).props("flat")

            ui.button(
                "Реестр исправлений",
                icon="edit_note",
            ).props("flat")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat app/web/state.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:55:09

Отлично. `STATE` у нас есть, но **PHOTO_INDEX находится не в `state.py`**. Чтобы не делать второй подсчёт и не сломать рабочий UI, сейчас найдём его точное место.

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -R -n \
"PHOTO_INDEX\s*=\|PHOTO_INDEX\[" \
app/web \
--include="*.py" \
--exclude-dir="__pycache__"
```

И отдельно найдём, откуда берутся **7 клиентов**:

```bash
grep -R -n \
"Все клиенты\|Единая Россия\|Яндекс\|Самокат\|Сбер\|Ozon" \
app/web \
--include="*.py" \
--exclude-dir="__pycache__"
```

После этого я дам **готовый `data.py`**, который будет показывать живую статистику:

```text
ДАННЫЕ

Клиентов       7
Адресов       18
Фотографий   526

ПО АДРЕСАМ
78             89
79             33
...
94            120
95             18
```

Причём количество фото будет брать именно из существующего `PHOTO_INDEX`, который мы уже проверили:

**526 фото / 18 адресов**, а не повторно сканировать папки.

---

### 👤 **User** — 2026-08-18 12:55:19

grep -R -n \
"PHOTO_INDEX\|STATE.addresses\|clients" \
app/web \
--include="*.py" \
--exclude-dir="__pycache__" \
| head -100

---

### 🤖 **Assistant** — 2026-08-18 12:55:19

Да, именно эту команду и запускаем. Она безопасная — ничего не меняет.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -R -n \
"PHOTO_INDEX\|STATE.addresses\|clients" \
app/web \
--include="*.py" \
--exclude-dir="__pycache__" \
| head -100
```

**Пришли весь вывод.** По нему сразу определим, где живёт `PHOTO_INDEX`, и следующим шагом сделаем статистику во вкладке **«Данные»** без дублирования логики.

---

### 👤 **User** — 2026-08-18 12:55:33

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat app/web/components/technical_modules/data.py
from nicegui import ui

def build_data():
    with ui.card().classes("w-full"):
        ui.label("ДАННЫЕ").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        with ui.row().classes("gap-6"):
            ui.label("Клиентов: 7")
            ui.label("Адресов: 18")
            ui.label("Правил исправления: 0")

        with ui.row().classes("gap-2"):
            ui.button(
                "Клиенты",
                icon="business",
            ).props("flat")

            ui.button(
                "Адреса",
                icon="place",
            ).props("flat")

            ui.button(
                "Реестр исправлений",
                icon="edit_note",
            ).props("flat")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat app/web/state.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:55:34

Да, теперь понятно. `state.py` содержит **18 адресов и 8 элементов списка клиентов, из которых один — «Все клиенты»**, то есть реальных клиентов сейчас 7.

А `PHOTO_INDEX` находится в другом модуле. Но мы уже знаем его структуру из рабочего запуска:

```text
PHOTO_INDEX = 526 фото
18 адресов
```

Сделаем пока статистику **без изменения существующей логики** и без повторного сканирования файлов.

### Шаг 1 — найди PHOTO_INDEX

Запусти именно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -R -n \
"PHOTO_INDEX" \
app/web \
--include="*.py" \
--exclude-dir="__pycache__" \
| head -100
```

Пришли вывод.

### Что потом сделаем

`data.py` превратим из текущего:

```text
Клиентов: 7
Адресов: 18
Правил исправления: 0
```

в нормальную статистическую панель:

```text
ДАННЫЕ

Клиенты        7
Адреса        18
Фотографии   526

────────────────────────

ФОТО ПО АДРЕСАМ

78       89
79       33
80        9
81       16
...
94      120
95       18

────────────────────────

Последний набор
20260818_115048
```

И важный момент: **526 не будем прописывать вручную**. Возьмём из уже существующего `PHOTO_INDEX`, чтобы после следующей загрузки фотографий цифра сама изменилась.

Сейчас только покажи результат `grep PHOTO_INDEX`.

---

### 👤 **User** — 2026-08-18 12:56:30

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -R -n \
"PHOTO_INDEX" \
app/web \
--include="*.py" \
--exclude-dir="__pycache__" \
| head -100
app/web/components/photos.py:106:PHOTO_INDEX: dict[str, list[Path]] = {}
app/web/components/photos.py:113:    PHOTO_INDEX.clear()
app/web/components/photos.py:186:            PHOTO_INDEX[address] = []
app/web/components/photos.py:203:        PHOTO_INDEX[address] = files
app/web/components/photos.py:212:            PHOTO_INDEX.get(
app/web/components/photos.py:284:                    PHOTO_INDEX.get(
app/web/components/photos.py:333:        PHOTO_INDEX.get(
app/web/components/photos.py:668:        f"addresses={len(PHOTO_INDEX)}",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:56:32

Отлично. Всё нашли. `PHOTO_INDEX` живёт в `app/web/components/photos.py` и имеет именно нужную структуру:

```python
PHOTO_INDEX: dict[str, list[Path]]
```

Значит, делаем статистику прямо из него.

### 1. Замени `data.py`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/web/components/technical_modules/data.py <<'PY'
from nicegui import ui

from app.web.state import STATE
from app.web.components.photos import (
    PHOTO_INDEX,
    get_latest_daily_root,
)

def build_data():

    # ============================================================
    # СТАТИСТИКА
    # ============================================================

    client_count = max(
        0,
        len(STATE.clients) - 1,
    )

    address_count = len(STATE.addresses)

    photo_count = sum(
        len(files)
        for files in PHOTO_INDEX.values()
    )

    daily_root = get_latest_daily_root()

    # ============================================================
    # UI
    # ============================================================

    with ui.card().classes("w-full"):

        ui.label(
            "ДАННЫЕ"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        # --------------------------------------------------------
        # ОСНОВНАЯ СТАТИСТИКА
        # --------------------------------------------------------

        with ui.row().classes(
            "w-full gap-3"
        ):

            with ui.card().classes(
                "flex-1"
            ):

                ui.label(
                    "Клиенты"
                ).classes(
                    "text-sm text-grey-6"
                )

                ui.label(
                    str(client_count)
                ).classes(
                    "text-2xl font-bold"
                )

            with ui.card().classes(
                "flex-1"
            ):

                ui.label(
                    "Адреса"
                ).classes(
                    "text-sm text-grey-6"
                )

                ui.label(
                    str(address_count)
                ).classes(
                    "text-2xl font-bold"
                )

            with ui.card().classes(
                "flex-1"
            ):

                ui.label(
                    "Фотографии"
                ).classes(
                    "text-sm text-grey-6"
                )

                ui.label(
                    str(photo_count)
                ).classes(
                    "text-2xl font-bold"
                )

        # --------------------------------------------------------
        # ПОСЛЕДНИЙ НАБОР
        # --------------------------------------------------------

        ui.separator().classes("my-3")

        ui.label(
            "ПОСЛЕДНИЙ НАБОР"
        ).classes(
            "text-sm font-bold"
        )

        if daily_root is not None:

            ui.label(
                daily_root.name
            ).classes(
                "text-base"
            )

            ui.label(
                str(daily_root)
            ).classes(
                "text-xs text-grey-6"
            )

        else:

            ui.label(
                "Набор не найден"
            ).classes(
                "text-sm text-grey-6"
            )

        # --------------------------------------------------------
        # ФОТО ПО АДРЕСАМ
        # --------------------------------------------------------

        ui.separator().classes("my-3")

        ui.label(
            "ФОТО ПО АДРЕСАМ"
        ).classes(
            "text-sm font-bold"
        )

        for address in STATE.addresses:

            count = len(
                PHOTO_INDEX.get(
                    address,
                    []
                )
            )

            with ui.row().classes(
                "w-full items-center"
            ):

                ui.label(
                    address
                ).classes(
                    "w-12 font-medium"
                )

                ui.label(
                    str(count)
                ).classes(
                    "w-16 text-right"
                )

                ui.linear_progress(
                    value=(
                        count / photo_count
                        if photo_count
                        else 0
                    )
                ).classes(
                    "flex-1"
                )

        # --------------------------------------------------------
        # СЛУЖЕБНАЯ ИНФОРМАЦИЯ
        # --------------------------------------------------------

        ui.separator().classes("my-3")

        with ui.row().classes("gap-2"):

            ui.button(
                "Клиенты",
                icon="business",
            ).props("flat")

            ui.button(
                "Адреса",
                icon="place",
            ).props("flat")

            ui.button(
                "Реестр исправлений",
                icon="edit_note",
            ).props("flat")

        ui.label(
            "Статистика формируется из текущего PHOTO_INDEX."
        ).classes(
            "text-xs text-grey-6"
        )
PY
```

### 2. Проверяем синтаксис

```bash
uv run python -m py_compile \
app/web/components/technical_modules/data.py
```

Если **ничего не вывело** — всё хорошо.

### 3. Перезапускаем UI

Сначала остановить текущий процесс:

```bash
kill 108732
```

Если PID уже другой:

```bash
sudo ss -ltnp 'sport = :8081'
```

и убить актуальный PID.

Затем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02
uv run python -m app.web.main
```

После открытия **⚙ Технический раздел → Данные** должны увидеть реальные:

```text
Клиенты       7
Адреса       18
Фотографии   526
```

и ниже распределение:

```text
78   89
79   33
80    9
...
94  120
95   18
```

Это уже будет **живая статистика из того же индекса, который формирует основной экран**, а не отдельный подсчёт.

---

### 👤 **User** — 2026-08-18 12:58:06

PY      )   "text-xs text-grey-6"ся из текущего PHOTO_INDEX."-----
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ kill 108732
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sudo ss -ltnp 'sport = :8081'
State        Recv-Q       Send-Q             Local Address:Port               Peer Address:Port       Process
LISTEN       0            2048                     0.0.0.0:8081                    0.0.0.0:*           users:(("python3",pid=116598,fd=19))
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ kill 2048
-bash: kill: (2048) - Operation not permitted
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ kill 116598
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02
uv run python -m app.web.main
NiceGUI ready to go on http://localhost:8081, http://10.241.0.111:8081, http://172.17.0.1:8081, http://172.18.0.1:8081, http://172.19.0.1:8081, http://172.20.0.1:8081, and http://192.168.1.5:8081
ERROR:    [Errno 98] error while attempting to bind on address ('0.0.0.0', 8081): address already in use
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:58:09

Да, здесь всё нормально с `kill 2048` — **2048 это Send-Q, не PID**. А новый PID `116598` сразу появился потому, что приложение, скорее всего, **запускается через systemd и автоматически перезапускается**.

Мы уже видели это раньше в `journalctl`: процесс `app.web.main` фактически является сервисом.

Сейчас **не запускай второй экземпляр**. Давай найдём, какой сервис держит 8081.

Выполни:

```bash
sudo systemctl status $(sudo lsof -t -i:8081 2>/dev/null) 2>/dev/null
```

Если команда ничего полезного не покажет, проще:

```bash
ps -fp 116598
```

и:

```bash
tr '\0' ' ' < /proc/116598/cmdline
echo
```

### Скорее всего увидим

что-то вроде:

```text
/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/python3 -m app.web.main --host 0.0.0.0 --port 8081
```

Тогда **не надо его убивать вручную**. Найдём unit:

```bash
sudo systemctl status 116598
```

Если опять не найдёт —:

```bash
systemctl list-units --type=service --all | grep -Ei 'albion|photo|scene|web'
```

Пришли вывод этих команд. **Сейчас наша задача только определить владельца 8081**, чтобы перезапускать UI правильно и не гоняться за автоматически возникающими PID.

---

### 👤 **User** — 2026-08-18 12:58:37

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ kill 116598
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02
uv run python -m app.web.main
NiceGUI ready to go on http://localhost:8081, http://10.241.0.111:8081, http://172.17.0.1:8081, http://172.18.0.1:8081, http://172.19.0.1:8081, http://172.20.0.1:8081, and http://192.168.1.5:8081
ERROR:    [Errno 98] error while attempting to bind on address ('0.0.0.0', 8081): address already in use
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sudo systemctl status $(sudo lsof -t -i:8081 2>/dev/null) 2>/dev/null
● lora.service - LORA Photo Database
     Loaded: loaded (/etc/systemd/system/lora.service; enabled; preset: enabled)
     Active: active (running) since Tue 2026-08-18 12:57:42 MSK; 38s ago
   Main PID: 117083 (uv)
      Tasks: 9 (limit: 34904)
     Memory: 70.5M (peak: 71.9M)
        CPU: 644ms
     CGroup: /system.slice/lora.service
             ├─117083 /home/alexice/.local/bin/uv run python -m app.web.main --host 0.0.0.0 --port 8081
             └─117086 /home/alexice/projects/scene_fingerprint_mvp_v02/.venv/bin/python3 -m app.web.main --host 0.0.0.0 --port 8081

Aug 18 12:57:42 NEURO systemd[1]: lora.service: Scheduled restart job, restart counter is at 3.
Aug 18 12:57:42 NEURO systemd[1]: Started lora.service - LORA Photo Database.
Aug 18 12:57:43 NEURO uv[117086]: NiceGUI ready to go on http://localhost:8081, http://10.241.0.111:8081, http://172.17.0.1:8081, http://172.18.0.1:8081, http://172.19.0.1:8081, http://172.20.0.1:8081, and http://192.168.1.5:8081
Aug 18 12:57:50 NEURO uv[117086]: [PHOTO RECORD INDEX] records= 100
Aug 18 12:57:50 NEURO uv[117086]: [DAILY PHOTO ROOT] /home/alexice/projects/scene_fingerprint_mvp_v02/data/output/daily/20260818_115048
Aug 18 12:57:50 NEURO uv[117086]: [DAILY ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 18 12:57:50 NEURO uv[117086]: [PHOTO INDEX] addresses=18 photos=526
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ ps -fp 116598
UID          PID    PPID  C STIME TTY          TIME CMD
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 12:58:38

Да, теперь причина ясна: **8081 уже занят вашим `lora.service`**, и это именно тот UI, который нам нужен.

Вручную `uv run python -m app.web.main` запускать **не надо** — systemd уже держит приложение запущенным.

Сейчас состояние хорошее:

- `lora.service` — **active (running)**
- PID приложения: `117086`
- порт `8081` занят корректно
- PostgreSQL/photo index: `100` записей
- текущий daily root: `20260818_115048`
- адресов: `18`
- фотографий: **526**
- UI уже работает.

### Что делаем дальше

Мы как раз хотели сделать **статистику во вкладке «Данные»** вместо захардкоженных:

```python
Клиентов: 7
Адресов: 18
Правил исправления: 0
```

И брать фактические значения из текущего состояния/индекса.

Сначала проверим, откуда сейчас реально берутся клиенты и адреса. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -R -n \
"PHOTO_INDEX\|STATE.clients\|STATE.addresses\|clients" \
app/web \
--include="*.py" \
--exclude-dir="__pycache__" \
| head -150
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '90,230p' app/web/components/photos.py
```

**После этого не будем менять рабочую логику фото.** Нам нужна только аккуратная статистическая панель в `Данные`, использующая уже существующие `PHOTO_INDEX` и данные БД.

---

### 👤 **User** — 2026-08-18 12:59:30

давай статус квен иобработчика дино

---

### 🤖 **Assistant** — 2026-08-18 12:59:30

Да. Сделаем во вкладке **«Данные»** отдельный блок **«Статус обработчиков»**:

- **DINO v33** — статус / последняя обработка / количество обработанных фото
- **Hybrid v12** — статус сортировки
- **Qwen3-VL 4B** — статус / количество обработанных фото / время
- текущий daily-запуск
- всего фото в текущем `PHOTO_INDEX`

Причём **не будем брать статус из захардкоженных значений** — лучше читать фактическое состояние последнего запуска и Qwen metadata.

Начнём с того, что посмотрим, какие данные уже есть для этого. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== LAST RUN ====="
cat app/web/components/technical_modules/last_run.py

echo
echo "===== PHOTO DB ====="
sed -n '1,260p' app/web/photo_db.py

echo
echo "===== HYBRID SCRIPT ====="
sed -n '1,180p' scripts/run_hybrid_v12.py

echo
echo "===== QWEN OUTPUT ====="
sed -n '1,120p' scripts/qwen4b_output_v01.py
```

После этого я дам **готовую замену `data.py`**, чтобы в UI появилась нормальная панель состояния обработчиков, не ломая текущие 526 фото и рабочий pipeline.

---

### 👤 **User** — 2026-08-18 13:00:21

echo "===== LAST RUN ====="
cat app/web/components/technical_modules/last_run.py

echo
echo "===== PHOTO DB ====="
sed -n '1,260p' app/web/photo_db.py

echo
echo "===== HYBRID SCRIPT ====="
sed -n '1,180p' scripts/run_hybrid_v12.py

echo
echo "===== QWEN OUTPUT ====="
sed -n '1,120p' scripts/qwen4b_output_v01.py
===== LAST RUN =====
from nicegui import ui

def build_last_run():
    with ui.card().classes("w-full"):
        ui.label("ПОСЛЕДНЯЯ ОБРАБОТКА").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        ui.label(
            "Обработок ещё не запускалось"
        ).classes("text-grey-7")

        with ui.row().classes("gap-2"):
            ui.button(
                "Подробнее",
                icon="info",
            ).props("flat dense")

            ui.button(
                "Журнал",
                icon="history",
            ).props("flat dense")

===== PHOTO DB =====
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

        index[str(db_path.resolve())] = record

    return index

===== HYBRID SCRIPT =====
#!/usr/bin/env python3

import argparse
import json
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from app.core.config import Settings
from app.core.embedder import SceneEmbedder

PROJECT = Path(__file__).resolve().parent.parent

SUB_DIR = PROJECT / "data/fingerprints_sub_exp"

# ============================================================
# HYBRID V12 — FROZEN CONTROL LOGIC
# ============================================================

MARGIN_LIMIT = 0.02

GLOBAL_WEIGHT = 10.0
SUB_WEIGHT = 2.5
NEIGHBOR_WEIGHT = 6.0

def normalize(x):
    x = np.asarray(x, dtype=np.float32)

    n = np.linalg.norm(x)

    if n > 0:
        x = x / n

    return x

def load_subs():
    result = {}

    if not SUB_DIR.exists():
        print(f"[Hybrid] WARNING: sub directory not found: {SUB_DIR}")
        return result

    for d in sorted(SUB_DIR.iterdir()):

        if not d.is_dir():
            continue

        f = d / "embeddings.npy"

        if not f.exists():
            continue

        emb = np.load(f)

        emb = np.array(
            [
                normalize(x)
                for x in emb
            ],
            dtype=np.float32,
        )

        result[d.name] = emb

    return result

def get_neighbor_votes(rows, index):
    votes = Counter()

    if index <= 0:
        return votes

    if index >= len(rows) - 1:
        return votes

    left = rows[index - 1]["top1"]
    right = rows[index + 1]["top1"]

    # FROZEN V12 RULE:
    # only complete agreement
    if left == right:
        votes[left] = 1

    return votes

def run_recognition(input_dir, fingerprints):
    """
    Run the existing DINO v33 recognizer.

    The recognizer itself is NOT modified.
    """

    fp_arg = ",".join(fingerprints)

    cmd = [
        "uv",
        "run",
        "scene-fingerprint",
        "recognize",
        str(input_dir),
        "--top-k",
        "5",
        "--threshold",
        "0.0",
        "--fingerprints",
        fp_arg,
        "--json",
    ]

    print("=" * 80)
    print("DINO v33 RECOGNITION")
    print("=" * 80)
    print("Input:", input_dir)
    print("Fingerprints:", ", ".join(fingerprints))
    print()

    start = time.perf_counter()

    process = subprocess.run(
        cmd,
        cwd=PROJECT,
        capture_output=True,
        text=True,
    )

    elapsed = time.perf_counter() - start

    if process.returncode != 0:
        print(process.stdout)
        print(process.stderr)

        raise RuntimeError(
            f"recognize завершился с кодом {process.returncode}"
        )

    combined = process.stdout + "\n" + process.stderr

    decoder = json.JSONDecoder()
    data = None

    for i, ch in enumerate(combined):

        if ch != "[":
            continue

        try:
            candidate, _ = decoder.raw_decode(
                combined[i:]
            )

            if isinstance(candidate, list):
                data = candidate
                break

        except json.JSONDecodeError:
            pass

    if data is None:
        raise RuntimeError(
            "Не удалось найти JSON-массив в выводе recognition"
        )

    print("Images:", len(data))
    print(f"Recognition time: {elapsed:.2f} sec")

    return data, elapsed

def adapt_recognizer_rows(rows):
    """

===== QWEN OUTPUT =====
#!/usr/bin/env python3

import argparse
import base64
import json
import time
from pathlib import Path

import requests

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data" / "output" / "test_sorted_v2"
OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"

MODEL = "qwen3-vl:4b-instruct"
OLLAMA_URL = "http://localhost:11434/api/chat"

NUM_CTX = 16384
TEMPERATURE = 0

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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:00:22

Отлично. Теперь видно, что для **статуса обработчиков** у нас уже есть реальные источники:

- PostgreSQL содержит `qwen_status`, `qwen_time_sec` и импортированные результаты Qwen.
- текущий `PHOTO_INDEX` даёт фактические `526` фото.
- `run_hybrid_v12.py` явно запускает DINO v33 и знает количество обработанных изображений и время.
- Qwen пишет результаты в `data/metadata/qwen4b/<run_name>`.

Но `last_run.py` пока полностью заглушка, поэтому **не будем пока пытаться восстанавливать историю из него**.

### Предлагаю сделать в «Данные» так

```text
СТАТИСТИКА

Фото в текущей базе       526
Адресов                   18
Записей PostgreSQL        100

ОБРАБОТЧИКИ

DINO v33                  ● ГОТОВ
Последний запуск          20260818_115048
Обработано                ...

Hybrid v12                ● ГОТОВ
Последний запуск          20260818_115048
Результат                 ...

Qwen3-VL 4B               ● ГОТОВ
Обработано                ...
Среднее время             ... сек
```

И главное — **DINO / Hybrid / Qwen будут показывать фактическое состояние**, а не просто зелёные надписи.

Сейчас нам нужно найти точный формат отчёта Hybrid, чтобы не гадать. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '180,380p' scripts/run_hybrid_v12.py

echo
echo "===== DAILY SCRIPT ====="
cat scripts/run_daily_hybrid_v12.sh

echo
echo "===== QWEN OUTPUT FILES ====="
find data/metadata/qwen4b -maxdepth 2 -type f \
    | sort \
    | tail -30
```

После этого сделаем `data.py` **одним изменением**, не трогая рабочие `photos.py`, `photo_db.py` и pipeline.

---

### 👤 **User** — 2026-08-18 13:01:39

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '180,380p' scripts/run_hybrid_v12.py

echo
echo "===== DAILY SCRIPT ====="
cat scripts/run_daily_hybrid_v12.sh

echo
echo "===== QWEN OUTPUT FILES ====="
find data/metadata/qwen4b -maxdepth 2 -type f \
    | sort \
    | tail -30
    """
    Convert current recognizer output into the legacy
    top1..top5 format required by frozen Hybrid v12.
    """

    adapted = []

    for row in rows:
        item = dict(row)

        candidates = row.get("candidates", [])

        for n in range(1, 6):
            item[f"top{n}"] = None
            item[f"top{n}_score"] = 0.0

        for n, candidate in enumerate(candidates[:5], start=1):
            item[f"top{n}"] = candidate.get("id")
            item[f"top{n}_score"] = float(
                candidate.get("score", 0.0)
            )

        adapted.append(item)

    return adapted

def hybrid_v12(rows, embedder, subs):
    """
    Exact production adaptation of the frozen Hybrid v12 logic.

    Input:
        recognizer rows containing top1..top5.

    Output:
        rows with final best_id.
    """

    changed = []
    results = []
    sub_count = 0

    for i, row in enumerate(rows):

        old = row.get("top1")

        scores = defaultdict(float)

        # ====================================================
        # GLOBAL TOP-5
        # ====================================================

        for k in range(1, 6):

            fp = row.get(f"top{k}")
            sc = row.get(f"top{k}_score")

            if fp:
                scores[fp] += (
                    float(sc)
                    * GLOBAL_WEIGHT
                )

        # ====================================================
        # SUB ONLY BORDER CASES
        # ====================================================

        margin = row.get(
            "margin",
            1,
        )

        if margin < MARGIN_LIMIT:

            sub_count += 1

            image = Path(
                row["file"]
            )

            query = embedder.embed_paths(
                [image]
            )[0]

            query = normalize(query)

            # FROZEN V12:
            # only TOP1 and TOP2
            candidates = [
                row.get("top1"),
                row.get("top2"),
            ]

            for parent in candidates:

                if not parent:
                    continue

                for sub_id, sub_emb in subs.items():

                    if not sub_id.startswith(parent):
                        continue

                    sim = max(
                        sub_emb @ query
                    )

                    if sim > 0.88:

                        if sim > 0.92:
                            bonus = 2.5
                        else:
                            bonus = 1.0

                        scores[parent] += (
                            float(sim)
                            * bonus
                        )

        # ====================================================
        # SEQUENCE CONSENSUS
        # ====================================================

        neighbors = get_neighbor_votes(
            rows,
            i,
        )

        left_fp = None
        right_fp = None

        if i > 0:
            left_fp = rows[i - 1].get("top1")

        if i < len(rows) - 1:
            right_fp = rows[i + 1].get("top1")

        if (
            left_fp
            and right_fp
            and left_fp == right_fp
        ):
            # FROZEN V12:
            # actual implementation uses +3.0
            scores[left_fp] += 3.0

        # ====================================================
        # FINAL DECISION V12
        # ====================================================

        best = old

        ranked = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        if ranked:

            candidate = ranked[0][0]

            gain = (
                scores[candidate]
                - scores.get(old, 0)
            )

            if (
                candidate != old
                and gain > 1.5
            ):
                best = candidate

        old_score = scores.get(
            old,
            0,
        )

        new_score = scores.get(
            best,
            0,
        )

        hybrid_changed = best != old

        result = dict(row)

        result["original_best_id"] = old
        result["best_id"] = best

        result["hybrid_changed"] = hybrid_changed

        result["hybrid_old_score"] = old_score
        result["hybrid_score"] = new_score

        result["hybrid_margin"] = margin
        result["hybrid_neighbors"] = dict(neighbors)

        results.append(result)

        if (

===== DAILY SCRIPT =====
#!/usr/bin/env bash

set -euo pipefail

PROJECT="$HOME/projects/scene_fingerprint_mvp_v02"

INPUT="$PROJECT/data/input/daily"

TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"

OUTPUT="$PROJECT/data/output/daily/$TIMESTAMP"

echo
echo "================================================================================"
echo "SCENE FINGERPRINT — DAILY HYBRID V12"
echo "================================================================================"
echo
echo "INPUT : $INPUT"
echo "OUTPUT: $OUTPUT"
echo

if [ ! -d "$INPUT" ]; then
    echo "ERROR: input directory does not exist:"
    echo "$INPUT"
    exit 1
fi

COUNT=$(find "$INPUT" -maxdepth 1 -type f \
    $ -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" $ \
    | wc -l)

echo "Images: $COUNT"
echo

if [ "$COUNT" -eq 0 ]; then
    echo "ERROR: no images found in $INPUT"
    exit 1
fi

mkdir -p "$OUTPUT"

/home/alexice/.local/bin/uv run python scripts/run_hybrid_v12.py \
    --input "$INPUT" \
    --output "$OUTPUT" \
    --first-address 78 \
    --last-address 95

echo
echo "================================================================================"
echo "DAILY PIPELINE FINISHED"
echo "================================================================================"
echo
echo "Images : $COUNT"
echo "Output : $OUTPUT"
echo

===== QWEN OUTPUT FILES =====
data/metadata/qwen4b/83_v33/Нагибина24_11.json
data/metadata/qwen4b/83_v33/Нагибина24_12.json
data/metadata/qwen4b/83_v33/Нагибина24_13.json
data/metadata/qwen4b/83_v33/Нагибина24_14.json
data/metadata/qwen4b/83_v33/Нагибина24_15.json
data/metadata/qwen4b/83_v33/Нагибина24_16.json
data/metadata/qwen4b/83_v33/Нагибина24_17.json
data/metadata/qwen4b/84_v33/Ленина125_01.json
data/metadata/qwen4b/84_v33/Ленина125_02.json
data/metadata/qwen4b/84_v33/Ленина125_03.json
data/metadata/qwen4b/84_v33/Ленина125_04.json
data/metadata/qwen4b/84_v33/Ленина125_05.json
data/metadata/qwen4b/84_v33/Ленина125_06.json
data/metadata/qwen4b/84_v33/Ленина125_07.json
data/metadata/qwen4b/84_v33/Ленина125_08.json
data/metadata/qwen4b/84_v33/Ленина125_09.json
data/metadata/qwen4b/84_v33/Ленина125_10.json
data/metadata/qwen4b/84_v33/Ленина125_11.json
data/metadata/qwen4b/85_v33/Ашхабадский_01.json
data/metadata/qwen4b/85_v33/Ашхабадский_02.json
data/metadata/qwen4b/85_v33/Ашхабадский_03.json
data/metadata/qwen4b/85_v33/Ашхабадский_04.json
data/metadata/qwen4b/85_v33/Ашхабадский_05.json
data/metadata/qwen4b/85_v33/Ашхабадский_06.json
data/metadata/qwen4b/85_v33/Ашхабадский_07.json
data/metadata/qwen4b/85_v33/Ашхабадский_08.json
data/metadata/qwen4b/85_v33/Ашхабадский_09.json
data/metadata/qwen4b/85_v33/Ашхабадский_10.json
data/metadata/qwen4b/85_v33/Ашхабадский_11.json
data/metadata/qwen4b/summary.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

