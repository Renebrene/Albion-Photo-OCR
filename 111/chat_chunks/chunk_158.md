## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 🤖 **Assistant** — 2026-08-19 01:53:03

Отлично. Теперь цепочка **полностью подтверждена тестом**.

Что уже работает:

```text
Watcher mode
    ↓
отслеживание watcher_path
    ↓
появление нового JPG
    ↓
стабилизация файла
    ↓
start_watcher()
    ↓
running=True
    ↓
Supervisor
    ↓
run_pipeline()
    ↓
завершение
    ↓
mark_finished()
    ↓
mode=watcher
running=False
    ↓
Watcher снова ждёт следующую партию
```

И при остановке:

```text
STOP
 ↓
request_stop()
 ↓
DINO/Qwen terminate
 ↓
finish_stop()
 ↓
manual
running=False
stop_requested=False
```

То есть **сама логика режимов теперь замкнута**.

Следующий этап я бы не трогал код DINO/Qwen. Надо проверить **реальный запуск `supervisor.py` из веб-приложения** — сейчас именно это потенциально слабое место.

Для начала покажи, кто вообще запускает Supervisor:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SUPERVISOR REFERENCES ================" && \
grep -RniE \
'supervisor_loop|supervisor.py|asyncio.create_task|create_subprocess_exec' \
app \
--include="*.py" | grep -v '__pycache__'
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ MAIN ================" && \
sed -n '1,260p' app/main.py
```

По этим двум выводам уже решим, **куда правильно подключить постоянный Supervisor**, чтобы он жил вместе с NiceGUI и не создавал второй экземпляр при каждом открытии страницы.

---

### 👤 **User** — 2026-08-19 01:53:27

======================================================================
FULL WATCHER -> SUPERVISOR TEST: PASSED
======================================================================
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ SUPERVISOR REFERENCES ================" && \
grep -RniE \
'supervisor_loop|supervisor.py|asyncio.create_task|create_subprocess_exec' \
app \
--include="*.py" | grep -v '__pycache__'
================ SUPERVISOR REFERENCES ================
app/web/components/technical_modules/photo_processing.py:465:                await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:482:            asyncio.create_task(
app/web/components/technical_modules/photo_processing.py:607:                await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:624:            asyncio.create_task(
app/web/components/technical_modules/qwen.py:440:            process = await asyncio.create_subprocess_exec(
app/pipeline/supervisor.py:113:    process = await asyncio.create_subprocess_exec(
app/pipeline/supervisor.py:130:    output_task = asyncio.create_task(
app/pipeline/supervisor.py:729:async def supervisor_loop():
app/pipeline/supervisor.py:915:    await supervisor_loop()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ MAIN ================" && \
sed -n '1,260p' app/main.py
================ MAIN ================
from pathlib import Path
from nicegui import ui
from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer

embedder = SceneEmbedder(settings)
manager = FingerprintManager(settings, embedder)
recognizer = SceneRecognizer(settings, embedder, manager)

@ui.page("/")
def page():
    ui.label("Scene Fingerprint").classes("text-3xl font-bold")
    ui.label("Распознавание локации по визуальному окружению").classes("text-lg text-gray-600")

    with ui.tabs().classes("w-full") as tabs:
        create_tab = ui.tab("Создать слепок")
        recognize_tab = ui.tab("Распознавание")
        db_tab = ui.tab("База слепков")

    with ui.tab_panels(tabs, value=create_tab).classes("w-full"):
        with ui.tab_panel(create_tab):
            ui.label("Новый визуальный слепок").classes("text-2xl")
            fp_id = ui.input("ID локации / конструкции", placeholder="78").classes("w-96")
            folder = ui.input("Папка эталонных фотографий", value="data/input/78").classes("w-full")
            info = ui.label("")

            def create():
                try:
                    r = manager.create(fp_id.value.strip(), folder.value.strip())
                    info.text = f"Создан: {r['id']} | {r['images']} фото | {r['dimension']}D"
                except Exception as e:
                    info.text = f"Ошибка: {e}"

            ui.button("СОЗДАТЬ СЛЕПОК", on_click=create)

        with ui.tab_panel(recognize_tab):
            ui.label("Распознавание папки").classes("text-2xl")
            folder2 = ui.input("Папка", value="data/input/new").classes("w-full")
            topk = ui.number("Top-K", value=5, min=1, max=20).classes("w-32")
            threshold = ui.number("Порог", value=0.65, min=0, max=1, step=0.01).classes("w-32")
            results_box = ui.column().classes("w-full")

            def run_recognition():
                results_box.clear()
                try:
                    rows = recognizer.recognize_folder(
                        folder2.value, int(topk.value), float(threshold.value)
                    )
                    with results_box:
                        for row in rows:
                            ui.label(
                                f"{Path(row['file']).name} → "
                                f"{row['best_id'] or 'UNKNOWN'} "
                                f"{row['score']:.3f}"
                            )
                            for c in row["candidates"]:
                                ui.label(f"    {c['id']}: {c['score']:.3f}").classes("text-gray-500")
                except Exception as e:
                    with results_box:
                        ui.label(f"Ошибка: {e}")

            ui.button("РАСПОЗНАТЬ", on_click=run_recognition)

        with ui.tab_panel(db_tab):
            ui.label("База слепков").classes("text-2xl")
            rows = ui.column().classes("w-full")

            def refresh():
                rows.clear()
                with rows:
                    data = manager.list_fingerprints()
                    if not data:
                        ui.label("База пуста.")
                    for x in data:
                        ui.label(
                            f"№{x['id']} — {x['images']} фото — "
                            f"{x['dimension']}D — {x['model']}"
                        )

            ui.button("Обновить", on_click=refresh)
            refresh()

ui.run(host=settings.host, port=settings.port, title="Scene Fingerprint")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:53:31

Вот теперь картина ясна.

`app/pipeline/supervisor.py` **сам по себе готов**, но `app/main.py` его вообще не запускает. Более того, показанный `main.py` — старый минимальный интерфейс и не содержит нынешней архитектуры «Альбион: Фотобаза. Офис».

Поэтому **не будем сейчас патчить `app/main.py` вслепую**. Сначала найдём фактическую точку входа текущего веб-интерфейса и место, где создаётся `ui.run()`.

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ UI RUN ================" && \
grep -RniE \
'ui\.run\(|run_with|@ui\.page|technical_modules|photo_processing|automation' \
app \
--include="*.py" | grep -v '__pycache__' && \
echo "================ PROJECT ENTRYPOINTS ================" && \
grep -nE \
'^(main|web|server|start|dev)[[:space:]]*=|scene-fingerprint|app\.main|app\.web' \
pyproject.toml
```

Нам нужно найти **реальный `ui.run()` текущего приложения**.

После этого сделаем правильно:

```text
NiceGUI
   │
   ├── Web UI
   │
   └── один глобальный Supervisor
           │
           ├── manual
           ├── automatic
           └── watcher
                    │
                    └── DINO + Qwen
```

И принципиально важно: Supervisor должен запускаться **один раз на процесс приложения**, а не при открытии каждой страницы/вкладки.

Тесты у нас уже хорошие — **Watcher → Supervisor → finish полностью прошёл**. Сейчас осталось только правильно подключить его к живому веб-приложению.

---

### 👤 **User** — 2026-08-19 01:53:49

'^(main|web|server|start|dev)[[:space:]]*=|scene-fingerprint|app\.main|app\.web' \
pyproject.toml
================ UI RUN ================
app/web/components/technical_modules/photo_processing.py:39:def build_photo_processing():
app/web/components/technical_modules/automation.py:27:def build_automation():
app/web/components/technical_modules/automation.py:377:                    "[AUTOMATION] MODE ERROR:",
app/web/components/technical_modules/automation.py:454:                    "[AUTOMATION] WATCHER PATH ERROR:",
app/web/components/technical_modules/automation.py:497:                    "[AUTOMATION] TIME ERROR:",
app/web/components/technical.py:3:from app.web.components.technical_modules.photo_processing import (
app/web/components/technical.py:4:    build_photo_processing,
app/web/components/technical.py:6:from app.web.components.technical_modules.last_run import (
app/web/components/technical.py:9:from app.web.components.technical_modules.automation import (
app/web/components/technical.py:10:    build_automation,
app/web/components/technical.py:12:from app.web.components.technical_modules.data import (
app/web/components/technical.py:15:from app.web.components.technical_modules.system import (
app/web/components/technical.py:18:from app.web.components.technical_modules.fingerprints import (
app/web/components/technical.py:21:from app.web.components.technical_modules.users import build_users
app/web/components/technical.py:101:def show_technical(initial_tab="photo_processing"):
app/web/components/technical.py:154:                    "photo_processing",
app/web/components/technical.py:166:                    "automation",
app/web/components/technical.py:207:                    value="photo_processing",
app/web/components/technical.py:212:                    with ui.tab_panel("photo_processing"):
app/web/components/technical.py:213:                        build_photo_processing()
app/web/components/technical.py:218:                    with ui.tab_panel("automation"):
app/web/components/technical.py:219:                        build_automation()
app/web/frontend_v02.py:636:ui.run(
app/web/main.py:13:@ui.page("/")
app/web/main.py:70:ui.run(
app/web/frontend_v01_backup_before_modular.py:602:ui.run(
app/web/frontend_v01.py:602:ui.run(
app/main.py:12:@ui.page("/")
app/main.py:85:ui.run(host=settings.host, port=settings.port, title="Scene Fingerprint")
app/web_v01_backup_20260816_142053/frontend_v02.py:636:ui.run(
app/web_v01_backup_20260816_142053/main.py:11:@ui.page("/")
app/web_v01_backup_20260816_142053/main.py:67:ui.run(
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:602:ui.run(
app/web_v01_backup_20260816_142053/frontend_v01.py:602:ui.run(
================ PROJECT ENTRYPOINTS ================
2:name = "scene-fingerprint"
36:scene-fingerprint = "app.cli:main"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:53:50

Отлично. Теперь нашли **реальную точку входа**: судя по структуре, актуальный интерфейс — `app/web/main.py`, а не старый `app/main.py`.

Сначала покажи его целиком — особенно конец с `ui.run()`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ APP WEB MAIN ================" && \
cat app/web/main.py && \
echo "================ FRONTEND V02 END ================" && \
tail -80 app/web/frontend_v02.py && \
echo "================ CLI ================" && \
sed -n '1,220p' app/cli.py
```

После этого уже можно будет сделать **один правильный патч подключения Supervisor**, не затрагивая DINO/Qwen и не ломая текущий веб-интерфейс.

---

### 👤 **User** — 2026-08-19 01:54:09

================ CLI ================
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer
from app.core.scene_analyzer import SceneAnalyzer
from app.pipeline.queue import JobQueue

def build_parser():
    parser = argparse.ArgumentParser(
        prog="scene-fingerprint",
        description=(
            "Scene fingerprinting and "
            "recognition v3.3 compact"
        ),
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # --------------------------------------------------
    # CREATE
    # --------------------------------------------------

    create_parser = subparsers.add_parser(
        "create",
        help="Create v3.3 compact fingerprint",
    )

    create_parser.add_argument(
        "fingerprint",
        help="Fingerprint ID",
    )

    create_parser.add_argument(
        "folder",
        help="Folder with reference images",
    )

    # --------------------------------------------------
    # QUEUE ADD
    # --------------------------------------------------

    queue_add_parser = subparsers.add_parser(
        "queue-add",
        help="Add fingerprint creation job to queue",
    )

    queue_add_parser.add_argument(
        "fingerprint",
        help="Fingerprint ID",
    )

    queue_add_parser.add_argument(
        "folder",
        help="Folder with reference images",
    )

    queue_add_parser.add_argument(
        "--priority",
        type=int,
        default=0,
        help="Job priority",
    )

    # --------------------------------------------------
    # QUEUE BATCH ADD
    # --------------------------------------------------

    queue_batch_parser = subparsers.add_parser(
        "queue-batch-add",
        help="Add a range of folders to fingerprint queue",
    )

    queue_batch_parser.add_argument(
        "start",
        type=int,
        help="First address ID",
    )

    queue_batch_parser.add_argument(
        "end",
        type=int,
        help="Last address ID",
    )

    queue_batch_parser.add_argument(
        "--priority",
        type=int,
        default=0,
        help="Queue priority",
    )

    # --------------------------------------------------
    # ANALYZE
    # --------------------------------------------------

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze one fingerprint",
    )

    analyze_parser.add_argument(
        "folder",
        help="Folder with query images",
    )

    analyze_parser.add_argument(
        "--fingerprint",
        required=True,
        help="Fingerprint ID",
    )

    # --------------------------------------------------
    # RECOGNIZE
    # --------------------------------------------------

    recognize_parser = subparsers.add_parser(
        "recognize",
        help="Recognize images",
    )

    recognize_parser.add_argument(
        "folder",
        help="Folder with query images",
    )

    recognize_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of candidates",
    )

    recognize_parser.add_argument(
        "--threshold",
        type=float,
        default=0.65,
        help="Minimum absolute match score",
    )

    recognize_parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Number of CPU workers for descriptor calculation",
    )

    recognize_parser.add_argument(
        "--fingerprints",
        type=str,
        default=None,
        help="Comma-separated fingerprint IDs to use",
    )

    recognize_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON",
    )

    return parser

def print_analyze_result(
    path,
    result,
):
    print()
    print(
        f"## {Path(path).name}"
    )
    print()

    print(
        f"GLOBAL        "
        f"{result['global_score']:.4f}"
    )

    print(
        f"BEST IMAGE    "
        f"{result['best_image_score']:.4f}"
    )

    print(
        "PATCH         "
        "0.0000 (DISABLED)"
    )

    print(
        f"COLOR         "
        f"{result['color_score']:.4f}"
    )

    print(
        f"SPATIAL       "
        f"{result['spatial_score']:.4f}"
    )

    print(
        f"ENVIRONMENT   "
        f"{result['environment_score']:.4f}"
    )

    print(
        f"FINAL         "
        f"{result['final_score']:.4f}"
    )

    print(
        f"BEST MATCH    "
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:54:12

Вывод обрезался: пришёл только `CLI`. Нам сейчас важнее всего увидеть **актуальный `app/web/main.py` и конец `frontend_v02.py`**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ APP/WEB/MAIN.PY ================" && \
cat app/web/main.py && \
echo "================ FRONTEND V02 TAIL ================" && \
tail -100 app/web/frontend_v02.py
```

После этого уже дам **конкретную команду-патч** для подключения `supervisor_loop()` к текущему NiceGUI.

Важно: `app/main.py` пока **не трогаем**. Он явно старый и к нынешнему интерфейсу `app/web/components/technical_modules/...` отношения не имеет.

---

### 👤 **User** — 2026-08-19 01:54:32

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ APP/WEB/MAIN.PY ================" && \
cat app/web/main.py && \
echo "================ FRONTEND V02 TAIL ================" && \
tail -100 app/web/frontend_v02.py
================ APP/WEB/MAIN.PY ================
from nicegui import ui

from app.web.config import HOST, PORT
from app.web.components.header import build_header
from app.web.components.search import build_search
from app.web.filters import build_filters
from app.web.components.clients import build_clients_panel
from app.web.components.photos import build_photos
from app.web.components.addresses import build_addresses
from app.web.components.technical import show_technical

@ui.page("/")
def index():

    build_header()
    build_search()
    build_filters()

    with ui.row().classes(
        "w-full flex-nowrap items-start gap-3 px-3"
    ).style(
        "height: calc(100vh - 200px);"
        "overflow: hidden;"
    ):

        # ====================================================
        # CENTER — PHOTOS
        # Сначала создаём photo grid и получаем настоящий
        # callback refresh_photos.
        # ====================================================

        with ui.column().classes(
            "flex-1 min-w-0 h-full order-2"
        ).style(
            "overflow: hidden;"
        ):

            refresh_photos = build_photos()

        # ====================================================
        # LEFT — CLIENTS
        # ====================================================

        with ui.column().classes(
            "w-[280px] min-w-[280px] h-full order-1"
        ).style(
            "overflow-y: auto;"
        ):

            build_clients_panel(
                refresh_photos
            )

        # ====================================================
        # RIGHT — ADDRESSES
        # ====================================================

        with ui.column().classes(
            "w-[280px] min-w-[280px] h-full order-3"
        ).style(
            "overflow-y: auto;"
        ):

            build_addresses(
                refresh_photos
            )

ui.run(
    host=HOST,
    port=PORT,
    reload=False,
    title="АЛЬБИОН: Фотобаза. Офис",
)
================ FRONTEND V02 TAIL ================
            ).props(
                'flat title="Изменить подборку"'
            )

            ui.button(
                icon="delete"
            ).props(
                'flat title="Удалить подборку"'
            )

# ============================================================
# BOTTOM BAR
# ============================================================

with ui.footer().classes(
    "bottom-bar"
):

    with ui.row().classes(
        "w-full items-center gap-4"
    ):

        ui.label("Дата:")

ui.select(
            [
                "Все даты",
                "Сегодня",
                "Вчера",
                "Эта неделя",
                "Этот месяц",
                "Этот год",
            ],
            value="Все даты",
        ).props(
            "outlined dense"
        ).style(
            "width: 150px"
        )

ui.button(
            "Период",
            icon="date_range",
        ).props(
            "outline"
        )

ui.separator().props(
            "vertical"
        )

ui.label("Сортировка:")

ui.select(
            [
                "Новые сначала",
                "Старые сначала",
                "По адресу",
                "По клиенту",
                "По имени файла",
            ],
            value="Новые сначала",
        ).props(
            "outlined dense"
        ).style(
            "width: 170px"
        )

ui.space()

ui.label("Размер:")

ui.slider(
            min=1,
            max=5,
            value=3,
        ).style(
            "width: 120px"
        )

# ============================================================
# RUN
# ============================================================

ui.run(
    title="АЛЬБИОН: Фотобаза. Офис.",
    host="0.0.0.0",
    port=8081,
    reload=False,
)

---

### 🤖 **Assistant** — 2026-08-19 01:54:33

Да. Теперь видно точно: **реальный вход — `app/web/main.py`**, и именно туда надо подключить Supervisor.

Причём `frontend_v02.py` сейчас лучше вообще не трогать — это отдельный старый/резервный frontend с собственным `ui.run()`.

Я предлагаю подключить Supervisor **одним глобальным asyncio task при старте приложения**. Тогда:

- Supervisor существует один;
- открытие новых браузерных клиентов его не дублирует;
- Watcher/Automatic работают независимо от страницы;
- текущий `photo_processing.py` остаётся управлять процессами через Supervisor;
- при остановке приложения Supervisor корректно получает cancellation.

### Патч `app/web/main.py`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

path = Path("app/web/main.py")
text = path.read_text()

# ------------------------------------------------------------
# 1. Добавляем asyncio + supervisor
# ------------------------------------------------------------

old = """from nicegui import ui

from app.web.config import HOST, PORT
"""

new = """import asyncio

from nicegui import ui

from app.web.config import HOST, PORT
"""

if old not in text:
    raise RuntimeError(
        "Не найден блок импортов app/web/main.py"
    )

text = text.replace(old, new, 1)

# ------------------------------------------------------------
# 2. Добавляем supervisor import
# ------------------------------------------------------------

old = """from app.web.components.technical import show_technical
"""

new = """from app.web.components.technical import show_technical
from app.pipeline.supervisor import supervisor_loop
"""

if old not in text:
    raise RuntimeError(
        "Не найден импорт show_technical"
    )

text = text.replace(old, new, 1)

# ------------------------------------------------------------
# 3. Добавляем глобальный supervisor task
# ------------------------------------------------------------

marker = """@ui.page("/")
def index():
"""

insert = """# ============================================================
# PIPELINE SUPERVISOR
# ============================================================

_supervisor_task = None

@app.on_startup
async def start_pipeline_supervisor():
    global _supervisor_task

    if (
        _supervisor_task is not None
        and not _supervisor_task.done()
    ):
        print(
            "[WEB] Pipeline Supervisor already running",
            flush=True,
        )
        return

    print(
        "[WEB] Starting Pipeline Supervisor",
        flush=True,
    )

    _supervisor_task = asyncio.create_task(
        supervisor_loop()
    )

@app.on_shutdown
async def stop_pipeline_supervisor():
    global _supervisor_task

    if _supervisor_task is None:
        return

    print(
        "[WEB] Stopping Pipeline Supervisor",
        flush=True,
    )

    _supervisor_task.cancel()

    try:
        await _supervisor_task

    except asyncio.CancelledError:
        pass

    finally:
        _supervisor_task = None

"""

if marker not in text:
    raise RuntimeError(
        "Не найден @ui.page('/')"
    )

text = text.replace(
    marker,
    insert + marker,
    1,
)

path.write_text(text)

print("WEB SUPERVISOR PATCH APPLIED")
PY
```

Но здесь есть один важный момент: в NiceGUI `app` может отсутствовать в таком варианте. Поэтому **сразу не запускаем приложение**. Сначала проверяем синтаксис и импорты:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/main.py \
app/pipeline/controller.py \
app/pipeline/supervisor.py
```

И затем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -A55 \
'PIPELINE SUPERVISOR' \
app/web/main.py
```

**Если компиляция проходит**, следующим шагом я дам маленький тест запуска, потому что нам надо проверить именно lifecycle NiceGUI: `startup → supervisor task → shutdown`.

Не запускай пока `app/web/main.py` вручную.

---

### 👤 **User** — 2026-08-19 01:55:05

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -A55 \
'PIPELINE SUPERVISOR' \
app/web/main.py
17:# PIPELINE SUPERVISOR
18-# ============================================================
19-
20-_supervisor_task = None
21-
22-
23-@app.on_startup
24-async def start_pipeline_supervisor():
25-    global _supervisor_task
26-
27-    if (
28-        _supervisor_task is not None
29-        and not _supervisor_task.done()
30-    ):
31-        print(
32-            "[WEB] Pipeline Supervisor already running",
33-            flush=True,
34-        )
35-        return
36-
37-    print(
38-        "[WEB] Starting Pipeline Supervisor",
39-        flush=True,
40-    )
41-
42-    _supervisor_task = asyncio.create_task(
43-        supervisor_loop()
44-    )
45-
46-
47-@app.on_shutdown
48-async def stop_pipeline_supervisor():
49-    global _supervisor_task
50-
51-    if _supervisor_task is None:
52-        return
53-
54-    print(
55-        "[WEB] Stopping Pipeline Supervisor",
56-        flush=True,
57-    )
58-
59-    _supervisor_task.cancel()
60-
61-    try:
62-        await _supervisor_task
63-
64-    except asyncio.CancelledError:
65-        pass
66-
67-    finally:
68-        _supervisor_task = None
69-
70-
71-@ui.page("/")
72-def index():
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 01:55:07

Да, здесь сразу видна проблема: мы вставили `@app.on_startup`, но в `app/web/main.py` **нет объекта `app`**. Поэтому `py_compile` это не ловит, а при запуске будет `NameError`.

В NiceGUI нам проще не привязываться к неизвестному `app`, а использовать lifecycle через `ui.timer(..., once=True)` — Supervisor запустится после создания UI, один раз.

Сейчас исправим именно этот участок.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

path = Path("app/web/main.py")
text = path.read_text()

start = text.index(
    "# ============================================================\n"
    "# PIPELINE SUPERVISOR"
)

end = text.index(
    '@ui.page("/")',
    start,
)

replacement = """# ============================================================
# PIPELINE SUPERVISOR
# ============================================================

_supervisor_task = None

async def start_pipeline_supervisor():
    global _supervisor_task

    if (
        _supervisor_task is not None
        and not _supervisor_task.done()
    ):
        print(
            "[WEB] Pipeline Supervisor already running",
            flush=True,
        )
        return

    print(
        "[WEB] Starting Pipeline Supervisor",
        flush=True,
    )

    _supervisor_task = asyncio.create_task(
        supervisor_loop()
    )

# Запускаем Supervisor один раз после старта NiceGUI.
# Не привязан к конкретному браузерному клиенту.
ui.timer(
    0.1,
    start_pipeline_supervisor,
    once=True,
)

"""

text = text[:start] + replacement + text[end:]

path.write_text(text)

print("SUPERVISOR LIFECYCLE FIXED")
PY
```

Теперь проверяем **не только синтаксис**, но и импорт модуля:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import app.web.main

print("IMPORT: OK")
print("SUPERVISOR IMPORT: OK")
PY
```

Если получим:

```text
IMPORT: OK
SUPERVISOR IMPORT: OK
```

то следующим шагом проверим запуск самого веб-приложения и увидим в консоли:

```text
[WEB] Starting Pipeline Supervisor
======================================================================
ALBION PIPELINE SUPERVISOR
======================================================================
[SUPERVISOR] state: manual | running: False | stop: False
```

**Пока не запускай через `uv run ...` вручную**, сначала дай результат этой проверки импорта.

---

### 👤 **User** — 2026-08-19 01:55:44

SUPERVISOR LIFECYCLE FIXED
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
import app.web.main

print("IMPORT: OK")
print("SUPERVISOR IMPORT: OK")
PY
NiceGUI ready to go on http://localhost:8081, http://10.241.0.111:8081, http://172.17.0.1:8081, http://172.18.0.1:8081, http://172.19.0.1:8081, http://172.20.0.1:8081, and http://192.168.1.5:8081
ERROR:    [Errno 98] error while attempting to bind on address ('0.0.0.0', 8081): address already in use
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
  через систем lora

---

### 🤖 **Assistant** — 2026-08-19 01:55:45

Да, это нормально: **порт 8081 уже занят работающим экземпляром текущего приложения**. И как раз фраза «через system lora» важна — значит, приложение, скорее всего, запускается через системный сервис, а не вручную.

Сейчас **ничего не убиваем**. Сначала выясним, какой именно процесс держит `8081` и каким systemd-сервисом он запущен.

Выполни одну команду:

```bash
sudo ss -ltnp 'sport = :8081' && \
echo "================ SYSTEMD ================" && \
systemctl list-units --type=service --all | grep -Ei 'lora|albion|photo|scene|fingerprint'
```

По результату определим:

1. какой PID слушает `8081`;
2. имя systemd-сервиса;
3. как сейчас запускается `app/web/main.py`;
4. куда именно подключать Supervisor, чтобы он запускался **один раз вместе с системным сервисом**.

Пока **не перезапускай `lora` и не меняй systemd-файл**. Сначала посмотрим текущую схему запуска.

---

### 👤 **User** — 2026-08-19 01:56:02

это старый проесс

---

### 🤖 **Assistant** — 2026-08-19 01:56:03

Да, тогда всё сходится. Старый процесс держит `8081`, поэтому тестовый импорт пытается поднять второй NiceGUI и получает `address already in use`.

Нам сейчас нужно **остановить именно старый процесс**, затем проверить новый запуск с Supervisor.

Сначала найди PID:

```bash
sudo ss -ltnp 'sport = :8081'
```

Если увидишь PID, можно сразу проверить его команду:

```bash
ps -fp <PID>
```

Например, если PID `12345`:

```bash
ps -fp 12345
```

Если это действительно старый Albion/NiceGUI-процесс, останови его:

```bash
sudo kill 12345
```

Подожди пару секунд и проверь:

```bash
sudo ss -ltnp 'sport = :8081'
```

Если порт свободен — **не запускаем пока systemd**. Сначала сделаем чистый ручной тест нового `app/web/main.py`, чтобы увидеть:

```text
[WEB] Starting Pipeline Supervisor
ALBION PIPELINE SUPERVISOR
[SUPERVISOR] state: manual | running: False | stop: False
```

и убедиться, что Supervisor действительно стартует вместе с веб-приложением.

Если старый процесс управляется systemd и сам возвращается после `kill`, тогда его не убиваем повторно — покажи вывод `ps -fp PID`, и разберём сервис.

---

### 👤 **User** — 2026-08-19 01:57:44

перезапустим через систем

---

### 🤖 **Assistant** — 2026-08-19 01:57:44

> **Searching the web**
>
> [Running Weston — weston 16.0.90 documentation](https://wayland.pages.freedesktop.org/weston/toc/running-weston.html)
> [man: replace hard-coded /usr/lib - systemd/systemd - System and Session Manager](https://cgit.freedesktop.org/systemd/systemd/commit/src/udev/src/gudev/seed-example-enum.js?id=7d2e33a416388f9fed5f357e55dcd41394651edc)
> [SPLIT TYPE
AIR TO WATER HEAT PUMP
Heating & Hot Wa](https://bugs.freedesktop.org/attachment.cgi?id=108384)
> [Running the WirePlumber daemon — WirePlumber 0.5.15 documentation](https://pipewire.pages.freedesktop.org/wireplumber/daemon/running.html)
> [Xlib and X Protocol Test Suite](https://www.freedesktop.org/software/fontconfig/xtest/userguide.pdf)
> [PipeWire: pipewire-pulse](https://pipewire-jwrdegoede-052917a3d0c68700bedc17e351d5362286fc43f6aef.pages.freedesktop.org/page_man_pipewire-pulse_1.html)
>
> **Searched 6 websites**
>
> 
>
> Worked for a few seconds

Да. Если старый процесс запущен через **systemd**, лучше перезапустить именно сервис - тогда systemd сам корректно остановит старый экземпляр и поднимет новый.

Сначала найдём точное имя сервиса, чтобы не угадывать:

```bash
systemctl list-units --type=service --all | grep -iE 'albion|photo|photobase|nicegui|scene|lora'
```

Если в списке увидим, например:

```text
albion-photobase.service
```

тогда:

```bash
sudo systemctl restart albion-photobase.service
```

И сразу проверяем:

```bash
sudo systemctl status albion-photobase.service --no-pager
```

А затем журнал последних сообщений:

```bash
sudo journalctl -u albion-photobase.service -n 80 --no-pager
```

### Важно

После нашего изменения в `app/web/main.py` ожидаем в журнале примерно:

```text
[WEB] Starting Pipeline Supervisor
======================================================================
ALBION PIPELINE SUPERVISOR
======================================================================
[SUPERVISOR] state: manual | running: False | stop: False
```

и **не должно быть**:

```text
address already in use
```

Также проверим, что порт поднялся ровно одним процессом:

```bash
sudo ss -ltnp 'sport = :8081'
```

Поскольку мы уже получили:

```text
FULL WATCHER -> SUPERVISOR TEST: PASSED
```

сейчас задача именно **перезапустить production-процесс через systemd и убедиться, что новый Supervisor реально стартует внутри веб-приложения**.

---

### 👤 **User** — 2026-08-19 01:59:08

технический раздел не открывается

---

### 🤖 **Assistant** — 2026-08-19 01:59:14

Да. После последнего изменения это нужно проверить **в первую очередь**, потому что мы вмешивались в `app/web/main.py`, а технический раздел строится именно там через `show_technical()`.

Давай не будем пока ничего менять. Посмотрим ошибку именно при открытии технического раздела.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ WEB LOG ================" && \
sudo journalctl -u lora -n 150 --no-pager | \
grep -Ei \
'ERROR|Traceback|Exception|technical|automation|photo_processing|supervisor|NameError|ImportError'
```

Если сервис называется не `lora`, сначала:

```bash
systemctl list-units --type=service --all | grep -i lora
```

И ещё полезно проверить сам импорт технического раздела:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.components.technical import show_technical
print("TECHNICAL IMPORT: OK")
PY
```

### Почему это важно

В `app/web/main.py` у нас есть:

```python
from app.web.components.technical import show_technical
```

а внутри:

```python
build_photo_processing()
build_automation()
build_data()
build_system()
build_fingerprints()
build_users()
```

Поэтому если **весь технический раздел не открывается**, это скорее всего не проблема Supervisor, а исключение при построении одного из технических модулей.

**Пришли вывод этих двух команд.** По нему сразу определим, ломается ли `technical.py`, конкретный модуль или обработчик переключения вкладки.

---

### 👤 **User** — 2026-08-19 01:59:52

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sudo systemctl restart lora
[sudo] password for alexice: 
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ WEB LOG ================" && \
sudo journalctl -u lora -n 150 --no-pager | \
grep -Ei \
'ERROR|Traceback|Exception|technical|automation|photo_processing|supervisor|NameError|ImportError'
================ WEB LOG ================
Aug 19 01:57:29 NEURO uv[519510]:     build_automation()
Aug 19 01:57:29 NEURO uv[519510]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical_modules/automation.py", line 58, in build_automation
Aug 19 01:57:29 NEURO uv[519510]:     raise ValueError(f'Invalid value: {value}')
Aug 19 01:57:29 NEURO uv[519510]: ValueError: Invalid value: manual
Aug 19 01:57:30 NEURO uv[519510]: Traceback (most recent call last):
Aug 19 01:57:30 NEURO uv[519510]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical.py", line 219, in show_technical
Aug 19 01:57:30 NEURO uv[519510]:     build_automation()
Aug 19 01:57:30 NEURO uv[519510]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical_modules/automation.py", line 58, in build_automation
Aug 19 01:57:30 NEURO uv[519510]:     raise ValueError(f'Invalid value: {value}')
Aug 19 01:57:30 NEURO uv[519510]: ValueError: Invalid value: manual
Aug 19 01:57:32 NEURO uv[519510]: Traceback (most recent call last):
Aug 19 01:57:32 NEURO uv[519510]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical.py", line 219, in show_technical
Aug 19 01:57:32 NEURO uv[519510]:     build_automation()
Aug 19 01:57:32 NEURO uv[519510]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical_modules/automation.py", line 58, in build_automation
Aug 19 01:57:32 NEURO uv[519510]:     raise ValueError(f'Invalid value: {value}')
Aug 19 01:57:32 NEURO uv[519510]: ValueError: Invalid value: manual
Aug 19 01:58:31 NEURO uv[520526]: [WEB] Starting Pipeline Supervisor
Aug 19 01:58:31 NEURO uv[520526]: ALBION PIPELINE SUPERVISOR
Aug 19 01:58:31 NEURO uv[520526]: [SUPERVISOR] state: manual | running: False | stop: False
Aug 19 01:58:41 NEURO uv[520526]: Traceback (most recent call last):
Aug 19 01:58:41 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical.py", line 219, in show_technical
Aug 19 01:58:41 NEURO uv[520526]:     build_automation()
Aug 19 01:58:41 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical_modules/automation.py", line 58, in build_automation
Aug 19 01:58:41 NEURO uv[520526]:     raise ValueError(f'Invalid value: {value}')
Aug 19 01:58:41 NEURO uv[520526]: ValueError: Invalid value: manual
Aug 19 01:58:47 NEURO uv[520526]: Traceback (most recent call last):
Aug 19 01:58:47 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical.py", line 219, in show_technical
Aug 19 01:58:47 NEURO uv[520526]:     build_automation()
Aug 19 01:58:47 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical_modules/automation.py", line 58, in build_automation
Aug 19 01:58:47 NEURO uv[520526]:     raise ValueError(f'Invalid value: {value}')
Aug 19 01:58:47 NEURO uv[520526]: ValueError: Invalid value: manual
Aug 19 01:58:50 NEURO uv[520526]: Traceback (most recent call last):
Aug 19 01:58:50 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical.py", line 219, in show_technical
Aug 19 01:58:50 NEURO uv[520526]:     build_automation()
Aug 19 01:58:50 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical_modules/automation.py", line 58, in build_automation
Aug 19 01:58:50 NEURO uv[520526]:     raise ValueError(f'Invalid value: {value}')
Aug 19 01:58:50 NEURO uv[520526]: ValueError: Invalid value: manual
Aug 19 01:58:54 NEURO uv[520526]: Traceback (most recent call last):
Aug 19 01:58:54 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical.py", line 219, in show_technical
Aug 19 01:58:54 NEURO uv[520526]:     build_automation()
Aug 19 01:58:54 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical_modules/automation.py", line 58, in build_automation
Aug 19 01:58:54 NEURO uv[520526]:     raise ValueError(f'Invalid value: {value}')
Aug 19 01:58:54 NEURO uv[520526]: ValueError: Invalid value: manual
Aug 19 01:58:54 NEURO uv[520526]: Traceback (most recent call last):
Aug 19 01:58:54 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical.py", line 219, in show_technical
Aug 19 01:58:54 NEURO uv[520526]:     build_automation()
Aug 19 01:58:54 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical_modules/automation.py", line 58, in build_automation
Aug 19 01:58:54 NEURO uv[520526]:     raise ValueError(f'Invalid value: {value}')
Aug 19 01:58:54 NEURO uv[520526]: ValueError: Invalid value: manual
Aug 19 01:58:55 NEURO uv[520526]: Traceback (most recent call last):
Aug 19 01:58:55 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical.py", line 219, in show_technical
Aug 19 01:58:55 NEURO uv[520526]:     build_automation()
Aug 19 01:58:55 NEURO uv[520526]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical_modules/automation.py", line 58, in build_automation
Aug 19 01:58:55 NEURO uv[520526]:     raise ValueError(f'Invalid value: {value}')
Aug 19 01:58:55 NEURO uv[520526]: ValueError: Invalid value: manual
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$  service --all | grep -i lora
  lora.service                                          loaded    active     running      LORA Photo Database
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.components.technical import show_technical
print("TECHNICAL IMPORT: OK")
PY
TECHNICAL IMPORT: OK

---

### 🤖 **Assistant** — 2026-08-19 01:59:53

Да, причина теперь **точно найдена**. Supervisor работает нормально:

```text
[WEB] Starting Pipeline Supervisor
ALBION PIPELINE SUPERVISOR
[SUPERVISOR] state: manual | running: False | stop: False
```

Проблема только в `automation.py`:

```text
ValueError: Invalid value: manual
```

То есть `controller.get_state()` возвращает:

```text
mode = manual
```

а UI автоматизации в `build_automation()` ожидает другой набор значений и не умеет отображать `manual`.

Это не ошибка Supervisor. Нужно привести UI автоматизации к тем же значениям, которые теперь использует `pipeline.modes`:

```text
manual
automatic
watcher
```

### Давай сначала посмотрим точное место

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ AUTOMATION 1-100 ================" && \
sed -n '1,120p' app/web/components/technical_modules/automation.py && \
echo "================ MODES ================" && \
cat app/pipeline/modes.py
```

Особенно нас интересуют **строки 40–70 `automation.py`** и определения:

```python
MODE_MANUAL
MODE_AUTOMATIC
MODE_WATCHER
```

После этого я дам **одну команду-патч**, чтобы UI снова открылся и при этом не сломать уже протестированный Watcher/Supervisor.

---

### 👤 **User** — 2026-08-19 02:00:19

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ AUTOMATION 1-100 ================" && \
sed -n '1,120p' app/web/components/technical_modules/automation.py && \
echo "================ MODES ================" && \
cat app/pipeline/modes.py
================ AUTOMATION 1-100 ================
from __future__ import annotations

from datetime import datetime, time

from nicegui import ui

from app.pipeline.controller import (
    get_state,
    set_automatic,
    set_manual,
    set_watcher,
)
from app.pipeline.modes import (
    MODE_AUTOMATIC,
    MODE_MANUAL,
    MODE_WATCHER,
)

def _parse_time(value: str) -> time:
    return datetime.strptime(
        value,
        "%H:%M",
    ).time()

def build_automation():
    state = get_state()

    # ========================================================
    # CARD
    # ========================================================

    with ui.card().classes("w-full"):

        ui.label(
            "РЕЖИМ ЗАПУСКА"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        # ====================================================
        # MODE
        # ====================================================

        with ui.row().classes(
            "items-center gap-4"
        ):

            ui.label(
                "Режим:"
            ).classes(
                "font-medium"
            )

            manual_radio = ui.radio(
                [
                    (
                        MODE_MANUAL,
                        "Ручной",
                    ),
                ],
                value=(
                    MODE_MANUAL
                    if state.mode == MODE_MANUAL
                    else None
                ),
            ).props("inline dense")

            watcher_radio = ui.radio(
                [
                    (
                        MODE_WATCHER,
                        "Watcher",
                    ),
                ],
                value=(
                    MODE_WATCHER
                    if state.mode == MODE_WATCHER
                    else None
                ),
            ).props("inline dense")

            automatic_radio = ui.radio(
                [
                    (
                        MODE_AUTOMATIC,
                        "Автоматический",
                    ),
                ],
                value=(
                    MODE_AUTOMATIC
                    if state.mode == MODE_AUTOMATIC
                    else None
                ),
            ).props("inline dense")

        # ----------------------------------------------------
        # TOOLTIPS
        # ----------------------------------------------------

        manual_radio.tooltip(
            "Обработка запускается пользователем вручную. "
            "Кнопки запуска DINO и Qwen доступны. "
            "Процессы можно запускать независимо друг от друга."
        )

        watcher_radio.tooltip(
            "Система наблюдает за папкой источника. "
            "При появлении новых фотографий они автоматически "
            "добавляются в очередь. Ручной запуск недоступен. "
            "После остановки режим возвращается в «Ручной»."
        )

        automatic_radio.tooltip(
            "Обработка запускается автоматически в заданное время. "
            "Ручной запуск DINO и Qwen недоступен."
        )
================ MODES ================
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 02:00:22

Вот теперь видно точную проблему.

`modes.py` полностью корректен: `manual` — валидное значение.

А проблема в `automation.py`: мы создали **три отдельных `ui.radio`**, каждый с одним вариантом. Для NiceGUI это некорректная конструкция — состояние `manual` передаётся в конкретный radio, который в этот момент не содержит ожидаемого набора значений. Отсюда:

```text
ValueError: Invalid value: manual
```

Нужно сделать **один общий `ui.radio` с тремя режимами**. Это ещё и правильнее архитектурно: режим у нас один, а не три независимых переключателя.

Сделаем аккуратно, не трогая Controller/Supervisor.

Выполни эту команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

path = Path("app/web/components/technical_modules/automation.py")
text = path.read_text()

old = '''            manual_radio = ui.radio(
                [
                    (
                        MODE_MANUAL,
                        "Ручной",
                    ),
                ],
                value=(
                    MODE_MANUAL
                    if state.mode == MODE_MANUAL
                    else None
                ),
            ).props("inline dense")

            watcher_radio = ui.radio(
                [
                    (
                        MODE_WATCHER,
                        "Watcher",
                    ),
                ],
                value=(
                    MODE_WATCHER
                    if state.mode == MODE_WATCHER
                    else None
                ),
            ).props("inline dense")

            automatic_radio = ui.radio(
                [
                    (
                        MODE_AUTOMATIC,
                        "Автоматический",
                    ),
                ],
                value=(
                    MODE_AUTOMATIC
                    if state.mode == MODE_AUTOMATIC
                    else None
                ),
            ).props("inline dense")
'''

new = '''            mode_radio = ui.radio(
                [
                    (
                        MODE_MANUAL,
                        "Ручной",
                    ),
                    (
                        MODE_WATCHER,
                        "Watcher",
                    ),
                    (
                        MODE_AUTOMATIC,
                        "Автоматический",
                    ),
                ],
                value=state.mode,
            ).props("inline dense")
'''

if old not in text:
    raise SystemExit(
        "PATCH TARGET NOT FOUND — файл не изменён"
    )

text = text.replace(old, new)

text = text.replace(
    '''        manual_radio.tooltip(
''',
    '''        mode_radio.tooltip(
'''
)

# Удаляем старые три tooltip-блока и добавляем общий.
start = text.find('        mode_radio.tooltip(')
if start == -1:
    raise SystemExit(
        "TOOLTIP TARGET NOT FOUND — файл не изменён"
    )

end_marker = '''        automatic_radio.tooltip(
            "Обработка запускается автоматически в заданное время. "
            "Ручной запуск DINO и Qwen недоступен."
        )
'''

end = text.find(end_marker, start)

if end == -1:
    raise SystemExit(
        "TOOLTIP END NOT FOUND — файл не изменён"
    )

end += len(end_marker)

new_tooltips = '''        mode_radio.tooltip(
            "Выберите режим запуска: ручной, Watcher "
            "или автоматический по расписанию."
        )
'''

text = text[:start] + new_tooltips + text[end:]

path.write_text(text)

print("AUTOMATION RADIO PATCH APPLIED")
PY

echo "================ COMPILE ================" && \
uv run python -m py_compile \
app/web/components/technical_modules/automation.py \
app/pipeline/controller.py \
app/pipeline/modes.py \
app/pipeline/supervisor.py

echo "================ VERIFY ================" && \
sed -n '35,100p' app/web/components/technical_modules/automation.py
```

После этого **не надо вручную запускать второй NiceGUI**. Просто:

```bash
sudo systemctl restart lora
```

и проверь технический раздел.

Ожидаем:

```text
[WEB] Starting Pipeline Supervisor
[SUPERVISOR] state: manual | running: False | stop: False
```

и главное — **никакого**:

```text
ValueError: Invalid value: manual
```

При этом наша уже прошедшая цепочка

**Watcher → событие → `running=True` → Supervisor → pipeline**

не затрагивается. Мы меняем только отображение режима в UI.

---

### 👤 **User** — 2026-08-19 02:01:05

не работает кнопка технический раздел

---

### 🤖 **Assistant** — 2026-08-19 02:01:05

Да. Сейчас уже нужно не гадать, а посмотреть **почему именно кнопка не открывает раздел**. Предыдущая ошибка `Invalid value: manual` могла быть только одной из проблем.

Давай одной командой получим полный traceback именно при открытии технического раздела:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ TECHNICAL ERROR ================" && \
sudo journalctl -u lora -n 250 --no-pager | \
grep -A25 -B8 -Ei \
'technical|automation|photo_processing|Traceback|Exception|ERROR|ValueError|NameError|AttributeError'
```

**Ничего пока не меняем.** Пришли весь вывод этой команды. По нему найдем конкретное место, где падает открытие технического раздела.

---

### 👤 **User** — 2026-08-19 02:01:18

Aug 19 02:00:48 NEURO uv[522760]:              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Aug 19 02:00:48 NEURO uv[522760]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical.py", line 219, in show_technical
Aug 19 02:00:48 NEURO uv[522760]:     build_automation()
Aug 19 02:00:48 NEURO uv[522760]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical_modules/automation.py", line 58, in build_automation
Aug 19 02:00:48 NEURO uv[522760]:     mode_radio = ui.radio(
Aug 19 02:00:48 NEURO uv[522760]:                  ^^^^^^^^^
Aug 19 02:00:48 NEURO uv[522760]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/nicegui/elements/radio.py", line 26, in __init__
Aug 19 02:00:48 NEURO uv[522760]:     super().__init__(tag='q-option-group', options=options, value=value, on_change=on_change)
Aug 19 02:00:48 NEURO uv[522760]:   File "/home/alexice/projects/scene_fingerprint_mvp_v02/.venv/lib/python3.12/site-packages/nicegui/elements/choice_element.py", line 20, in __init__
Aug 19 02:00:48 NEURO uv[522760]:     raise ValueError(f'Invalid value: {value}')
Aug 19 02:00:48 NEURO uv[522760]: ValueError: Invalid value: manual
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 02:01:26

Отлично, теперь причина **100% конкретная**.

Падает именно создание `ui.radio()`:

```text
ValueError: Invalid value: manual
```

То есть проблема не в Controller, не в Supervisor и не в БД. В текущей версии NiceGUI передача списка кортежей:

```python
[
    ("manual", "Ручной"),
    ...
]
```

не даёт `ui.radio` набор допустимых значений так, как мы предположили.

Сделаем самый надёжный вариант для NiceGUI — **словарь `значение: подпись`**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

path = Path("app/web/components/technical_modules/automation.py")
text = path.read_text()

old = '''            mode_radio = ui.radio(
                [
                    (
                        MODE_MANUAL,
                        "Ручной",
                    ),
                    (
                        MODE_WATCHER,
                        "Watcher",
                    ),
                    (
                        MODE_AUTOMATIC,
                        "Автоматический",
                    ),
                ],
                value=state.mode,
            ).props("inline dense")
'''

new = '''            mode_radio = ui.radio(
                {
                    MODE_MANUAL: "Ручной",
                    MODE_WATCHER: "Watcher",
                    MODE_AUTOMATIC: "Автоматический",
                },
                value=state.mode,
            ).props("inline dense")
'''

if old not in text:
    raise SystemExit("PATCH TARGET NOT FOUND")

text = text.replace(old, new)

path.write_text(text)

print("RADIO DICT PATCH APPLIED")
PY

echo "================ COMPILE ================" && \
uv run python -m py_compile \
app/web/components/technical_modules/automation.py

echo "================ VERIFY ================" && \
sed -n '48,82p' app/web/components/technical_modules/automation.py
```

Потом:

```bash
sudo systemctl restart lora
```

И **сначала не трогая остальные кнопки** просто открой технический раздел.

После этого сразу дай:

```bash
sudo journalctl -u lora -n 80 --no-pager | \
grep -Ei 'Traceback|Exception|ERROR|technical|automation|ValueError'
```

Если ошибок нет — следующим шагом проверим уже **переключение Ручной / Watcher / Автоматический**, не затрагивая рабочий Supervisor.

---

### 👤 **User** — 2026-08-19 02:01:57

кнопка технический раздел на главной странице не открывает окно настреорк

---

### 🤖 **Assistant** — 2026-08-19 02:01:59

Понял. Тогда проблема **не в содержимом `automation.py`**, а в самой кнопке/механике открытия технического окна.

Сейчас нужно посмотреть, **как именно `show_technical()` вызывается с главной страницы**. Дай одной командой:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ TECHNICAL.PY ================" && \
sed -n '1,280p' app/web/components/technical.py && \
echo "================ BUTTON REFERENCES ================" && \
grep -RniE \
'show_technical|Технический|technical' \
app/web \
--include="*.py" | grep -v '__pycache__'
```

Особенно важны места, где создаётся кнопка **«Технический раздел»** и её `on_click`.

После этого исправим именно открытие окна, не трогая уже протестированные **Supervisor / Watcher / controller**.

---

### 👤 **User** — 2026-08-19 02:02:20

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ TECHNICAL.PY ================" && \
sed -n '1,280p' app/web/components/technical.py && \
echo "================ BUTTON REFERENCES ================" && \
grep -RniE \
'show_technical|Технический|technical' \
app/web \
--include="*.py" | grep -v '__pycache__'
================ TECHNICAL.PY ================
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
            lambda: tabs.set_value(initial_tab),
            once=True,
        )

    _restore_and_watch_size()
================ BUTTON REFERENCES ================
app/web/components/header.py:9:from app.web.components.technical import show_technical
app/web/components/header.py:223:        # TECHNICAL
app/web/components/header.py:227:            "Технический раздел",
app/web/components/header.py:229:            on_click=show_technical,
app/web/components/technical.py:3:from app.web.components.technical_modules.photo_processing import (
app/web/components/technical.py:6:from app.web.components.technical_modules.last_run import (
app/web/components/technical.py:9:from app.web.components.technical_modules.automation import (
app/web/components/technical.py:12:from app.web.components.technical_modules.data import (
app/web/components/technical.py:15:from app.web.components.technical_modules.system import (
app/web/components/technical.py:18:from app.web.components.technical_modules.fingerprints import (
app/web/components/technical.py:21:from app.web.components.technical_modules.users import build_users
app/web/components/technical.py:24:TECHNICAL_STORAGE_KEY = "albion_technical_window_size"
app/web/components/technical.py:36:            const card = document.getElementById('technical-dialog-card');
app/web/components/technical.py:42:            const storageKey = '{TECHNICAL_STORAGE_KEY}';
app/web/components/technical.py:101:def show_technical(initial_tab="photo_processing"):
app/web/components/technical.py:106:            "id=technical-dialog-card"
app/web/components/technical.py:108:            "technical-dialog-card"
app/web/components/technical.py:131:                    "⚙ Технический раздел"
app/web/main.py:12:from app.web.components.technical import show_technical
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 02:02:23

Вот причина стала понятнее: `show_technical()` сама по себе вызывается корректно, а кнопка в `header.py` передаёт `show_technical` напрямую.

Нужно посмотреть небольшой участок `header.py`, особенно окружающий код кнопки — там может быть контейнер/событие, которое перехватывает клик.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HEADER TECHNICAL ================" && \
sed -n '190,250p' app/web/components/header.py
```

И ещё сразу проверим, что кнопка вообще создаётся:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -A12 -B8 \
'Технический раздел' \
app/web/components/header.py
```

Пришли вывод. **Пока ничего не меняем.**

---

### 👤 **User** — 2026-08-19 02:02:38

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HEADER TECHNICAL ================" && \
sed -n '190,250p' app/web/components/header.py
================ HEADER TECHNICAL ================
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

        user_button.on(
            "click",
            open_user_switcher,
        )

        # ----------------------------------------------------
        # TECHNICAL
        # ----------------------------------------------------

        ui.button(
            "Технический раздел",
            icon="settings",
            on_click=show_technical,
        ).props(
            "unelevated dense"
        ).classes(
            "min-w-[190px] font-medium"
        ).style(
            """
            background: white !important;
            color: #333 !important;
            z-index: 100000 !important;
            """
        )

    # ========================================================
    # INITIAL COLOR
    # ========================================================

    try:

        users = get_users()

        for (
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 02:02:40

Кнопка в `header.py` **правильная**:

```python
on_click=show_technical
```

Значит клик доходит до `show_technical()`, а окно не появляется потому, что NiceGUI сначала строит содержимое `dialog`, и **во время построения падает `build_automation()`**. Поэтому `dialog.open()` до выполнения не доходит.

Причём в твоём предыдущем traceback была именно эта цепочка:

```text
show_technical()
  ↓
build_automation()
  ↓
ui.radio(...)
  ↓
ValueError: Invalid value: manual
```

Нужно сейчас увидеть **актуальные строки 35–90**, потому что ранее у тебя там были три отдельных `ui.radio`, а в предложенном патче мы ожидали один `mode_radio`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba app/web/components/technical_modules/automation.py | \
sed -n '35,95p'
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -nE \
'ui\.radio|mode_radio|manual_radio|watcher_radio|automatic_radio' \
app/web/components/technical_modules/automation.py
```

**Скорее всего, патч просто не попал в фактическую текущую конструкцию `automation.py`.** Тогда я дам одну команду, которая исправит именно её, без изменения Supervisor и Controller.

---

### 👤 **User** — 2026-08-19 02:03:07

exice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba app/web/components/technical_modules/automation.py | \
sed -n '35,95p'
    35	
    36	        ui.label(
    37	            "РЕЖИМ ЗАПУСКА"
    38	        ).classes(
    39	            "text-lg font-bold"
    40	        )
    41	
    42	        ui.separator().classes("my-2")
    43	
    44	        # ====================================================
    45	        # MODE
    46	        # ====================================================
    47	
    48	        with ui.row().classes(
    49	            "items-center gap-4"
    50	        ):
    51	
    52	            ui.label(
    53	                "Режим:"
    54	            ).classes(
    55	                "font-medium"
    56	            )
    57	
    58	            mode_radio = ui.radio(
    59	                [
    60	                    (
    61	                        MODE_MANUAL,
    62	                        "Ручной",
    63	                    ),
    64	                    (
    65	                        MODE_WATCHER,
    66	                        "Watcher",
    67	                    ),
    68	                    (
    69	                        MODE_AUTOMATIC,
    70	                        "Автоматический",
    71	                    ),
    72	                ],
    73	                value=state.mode,
    74	            ).props("inline dense")
    75	
    76	        # ----------------------------------------------------
    77	        # TOOLTIPS
    78	        # ----------------------------------------------------
    79	
    80	        mode_radio.tooltip(
    81	            "Выберите режим запуска: ручной, Watcher "
    82	            "или автоматический по расписанию."
    83	        )
    84	
    85	        # ====================================================
    86	        # WATCHER PATH
    87	        # ====================================================
    88	
    89	        with ui.row().classes(
    90	            "w-full items-center gap-2"
    91	        ):
    92	
    93	            watcher_path_input = ui.input(
    94	                "Папка для Watcher",
    95	                value=state.watcher_path or "",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -nE \
'ui\.radio|mode_radio|manual_radio|watcher_radio|automatic_radio' \
app/web/components/technical_modules/automation.py
58:            mode_radio = ui.radio(
80:        mode_radio.tooltip(
152:        processed_policy = ui.radio(
185:        missed_start = ui.radio(
277:            manual_radio.value = (
283:            watcher_radio.value = (
289:            automatic_radio.value = (
356:        manual_radio.on(
365:        watcher_radio.on(
374:        automatic_radio.on(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 02:03:09

Да, нашли точную ошибку. Сейчас у тебя **смешаны две версии `automation.py`**.

В начале уже стоит новый:

```python
mode_radio = ui.radio(...)
```

но ниже, на строках **277–374**, остался старый код, который обращается к:

```python
manual_radio
watcher_radio
automatic_radio
```

Это следующая ошибка, которая всплывёт после исправления текущей.

Но текущий `ValueError: Invalid value: manual` возникает потому, что `ui.radio()` получает список кортежей. Для NiceGUI здесь нужен словарь.

Сделаем сразу правильно и уберём остатки старой трёх-radio логики.

### 1. Исправляем `mode_radio`

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

path = Path("app/web/components/technical_modules/automation.py")
text = path.read_text()

old = '''            mode_radio = ui.radio(
                [
                    (
                        MODE_MANUAL,
                        "Ручной",
                    ),
                    (
                        MODE_WATCHER,
                        "Watcher",
                    ),
                    (
                        MODE_AUTOMATIC,
                        "Автоматический",
                    ),
                ],
                value=state.mode,
            ).props("inline dense")
'''

new = '''            mode_radio = ui.radio(
                {
                    MODE_MANUAL: "Ручной",
                    MODE_WATCHER: "Watcher",
                    MODE_AUTOMATIC: "Автоматический",
                },
                value=state.mode,
            ).props("inline dense")
'''

if old not in text:
    raise SystemExit("MODE RADIO BLOCK NOT FOUND")

text = text.replace(old, new)

path.write_text(text)

print("MODE RADIO FIXED")
PY
```

### 2. Теперь посмотрим старые обращения

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba app/web/components/technical_modules/automation.py | \
sed -n '250,390p'
```

**Пока не перезапускай `lora`.**

Нам нужно переделать эти строки:

```text
manual_radio.value
watcher_radio.value
automatic_radio.value

manual_radio.on(...)
watcher_radio.on(...)
automatic_radio.on(...)
```

на один:

```python
mode_radio
```

Причём это важно сделать аккуратно: логика переключения режима уже связана с нашим `controller`, и **Supervisor трогать вообще не будем**.

Пришли вывод `250–390`, и я дам одну финальную команду-патч для всего оставшегося блока.

---

