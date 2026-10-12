## СЕССИЯ: ФОТОБАЗА ОФИС

**Создано:** 2026-08-16 00:03:58
**Обновлено:** 2026-08-19 21:49:51
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df)

---

### 🤖 **Assistant** — 2026-08-16 19:13:49

Отлично. Тогда **архитектуру фиксируем**.

Следующий шаг — не писать сразу всё окно, а сделать **каркас модульной системы**, подключить его к существующему `main.py` и проверить, что текущая фотобаза продолжает работать.

Порядок такой:

1. Создать `app/web/components/technical/`.
2. Вынести туда отдельные UI-модули.
3. `technical.py` оставить сборщиком.
4. Пока внутри модулей сделать только согласованный интерфейс, без изменения существующего backend.
5. Проверить `py_compile`.
6. Запустить через:
   `uv run python -m app.web.main`
7. Убедиться, что:
   - фотогалерея работает;
   - PostgreSQL-привязка 100 тестовых фото не сломалась;
   - поиск работает;
   - техническое окно открывается;
   - каждый блок отображается отдельно.

**Тяжёлые операции DINO/Qwen пока не подключаем к новым кнопкам.** Сначала безопасно собираем UI-каркас.

После этого будем подключать функциональность **по одному модулю**, начиная с «Система» и «Фотообработка».

---

### 👤 **User** — 2026-08-16 19:14:00

давай

---

### 🤖 **Assistant** — 2026-08-16 19:14:05

Делаем. Первый проход — **только модульный каркас**, без подключения новых backend-операций.

В терминале проекта:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

# ------------------------------------------------------------
# 1. BACKUP
# ------------------------------------------------------------

cp app/web/components/technical.py \
   app/web/components/technical.py.before_modular_$(date +%Y%m%d_%H%M%S)

# ------------------------------------------------------------
# 2. MODULAR TECHNICAL DIRECTORY
# ------------------------------------------------------------

mkdir -p app/web/components/technical

touch app/web/components/technical/__init__.py

# ------------------------------------------------------------
# 3. PHOTO PROCESSING
# ------------------------------------------------------------

cat > app/web/components/technical/photo_processing.py <<'PY'
from nicegui import ui

def build_photo_processing():
    with ui.card().classes("w-full"):
        ui.label("ФОТООТЧЁТ").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        ui.label("Источник фотографий")

        with ui.row().classes("w-full items-center gap-2"):
            ui.input(
                value="/data/input/test"
            ).props(
                "outlined dense"
            ).classes("flex-1")

            ui.button(
                "Выбрать",
                icon="folder_open",
            ).props("flat dense")

        ui.label("Результат")

        with ui.row().classes("w-full items-center gap-2"):
            ui.input(
                value="/data/output/test_sorted_v2"
            ).props(
                "outlined dense"
            ).classes("flex-1")

            ui.button(
                "Выбрать",
                icon="folder_open",
            ).props("flat dense")

        ui.separator().classes("my-2")

        ui.label(
            "DINO / v33 → определение адреса → сортировка → Qwen3-VL 4B"
        ).classes("text-sm")

        ui.button(
            "▶  ЗАПУСТИТЬ ОБРАБОТКУ",
            on_click=lambda: ui.notify(
                "Запуск обработки будет подключён следующим этапом"
            ),
        ).props(
            "unelevated"
        ).classes(
            "w-full text-lg font-bold"
        )

        ui.label(
            "Главная рабочая операция"
        ).classes("text-xs text-grey-6")
PY

# ------------------------------------------------------------
# 4. LAST RUN
# ------------------------------------------------------------

cat > app/web/components/technical/last_run.py <<'PY'
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
PY

# ------------------------------------------------------------
# 5. AUTOMATION
# ------------------------------------------------------------

cat > app/web/components/technical/automation.py <<'PY'
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
PY

# ------------------------------------------------------------
# 6. QWEN
# ------------------------------------------------------------

cat > app/web/components/technical/qwen.py <<'PY'
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
PY

# ------------------------------------------------------------
# 7. DATA
# ------------------------------------------------------------

cat > app/web/components/technical/data.py <<'PY'
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
PY

# ------------------------------------------------------------
# 8. SYSTEM
# ------------------------------------------------------------

cat > app/web/components/technical/system.py <<'PY'
from nicegui import ui

def build_system():
    with ui.card().classes("w-full"):
        ui.label("СИСТЕМА").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        ui.label(
            "● Сервер работает"
        ).classes("text-sm")

        with ui.grid(columns=2).classes("w-full gap-2"):
            ui.label("CPU")
            ui.label("—")

            ui.label("Температура CPU")
            ui.label("—")

            ui.label("GPU")
            ui.label("—")

            ui.label("Температура GPU")
            ui.label("—")

            ui.label("RAM")
            ui.label("—")

            ui.label("VRAM")
            ui.label("—")

            ui.label("Сеть ↓ / ↑")
            ui.label("— / —")

            ui.label("Время работы")
            ui.label("—")

        ui.label(
            "Мониторинг будет подключён отдельным backend-модулем."
        ).classes("text-xs text-grey-6")
PY

# ------------------------------------------------------------
# 9. FINGERPRINTS
# ------------------------------------------------------------

cat > app/web/components/technical/fingerprints.py <<'PY'
from nicegui import ui

def build_fingerprints():
    with ui.card().classes("w-full"):
        ui.label("СЛЕПКИ").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        ui.label(
            "Используется для добавления новых адресов."
        ).classes("text-sm")

        ui.label(
            "Рабочая версия: DINO / v33"
        )

        ui.label(
            "Адресов со слепками: 18"
        )

        ui.button(
            "▶  СОЗДАТЬ / ОБНОВИТЬ СЛЕПКИ",
            on_click=lambda: ui.notify(
                "Создание слепков будет подключено следующим этапом"
            ),
        ).props("unelevated")
PY

# ------------------------------------------------------------
# 10. MAIN MODULAR TECHNICAL WINDOW
# ------------------------------------------------------------

cat > app/web/components/technical.py <<'PY'
from nicegui import ui

from app.web.components.technical.photo_processing import (
    build_photo_processing,
)
from app.web.components.technical.last_run import (
    build_last_run,
)
from app.web.components.technical.automation import (
    build_automation,
)
from app.web.components.technical.qwen import (
    build_qwen,
)
from app.web.components.technical.data import (
    build_data,
)
from app.web.components.technical.system import (
    build_system,
)
from app.web.components.technical.fingerprints import (
    build_fingerprints,
)

def show_technical():

    with ui.dialog() as dialog, ui.card().classes(
        "w-[1000px] max-w-[94vw] max-h-[94vh]"
    ):

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
            ).props("flat")

        ui.separator()

        with ui.scroll_area().classes(
            "w-full"
        ).style(
            "max-height: calc(94vh - 80px);"
        ):

            build_photo_processing()
            build_last_run()
            build_automation()
            build_qwen()
            build_data()
            build_system()
            build_fingerprints()

    dialog.open()
PY

# ------------------------------------------------------------
# 11. CHECK
# ------------------------------------------------------------

echo
echo "=== PYTHON COMPILE ==="

uv run python -m py_compile \
    app/web/components/technical.py \
    app/web/components/technical/*.py

echo
echo "=== TECHNICAL MODULES ==="

find app/web/components/technical \
    -maxdepth 1 \
    -type f \
    -printf '%f\n' \
    | sort

echo
echo "=== DONE ==="
```

После этого запускаем:

```bash
uv run python -m app.web.main
```

**Пока ничего из DINO/Qwen/backend не меняем.** На этом этапе проверяем именно каркас: открылось ли техническое окно и нормально ли отображаются все семь независимых модулей.

Особенно важно: если что-то не понравится в одном блоке, дальше будем менять **только соответствующий файл**, например `system.py` или `photo_processing.py`, а не весь `technical.py`.

---

### 👤 **User** — 2026-08-16 19:14:35

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ uv run python -m app.web.main
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/main.py", line 10, in <module>
    from app.web.components.technical import show_technical
ImportError: cannot import name 'show_technical' from 'app.web.components.technical' (/home/alexice/projects/scene_fingerprint_mvp_v02/app/web/components/technical/__init__.py)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 19:14:37

Да, причина понятна. Мы создали одновременно:

```text
app/web/components/technical.py
```

и

```text
app/web/components/technical/
```

Python теперь воспринимает `technical` как **пакет** и импортирует:

```text
app/web/components/technical/__init__.py
```

а не `technical.py`.

Лучше не ломать текущую архитектуру. Сделаем правильно: `technical.py` станет сборщиком, а папку переименуем в `technical_modules`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

mv app/web/components/technical \
   app/web/components/technical_modules

echo "=== CHECK ==="
ls -lah app/web/components/technical.py
ls -lah app/web/components/technical_modules/
```

Теперь исправим импорты в `technical.py`:

```bash
sed -i 's/app\.web\.components\.technical\./app.web.components.technical_modules./g' \
    app/web/components/technical.py
```

Проверим:

```bash
echo "=== TECHNICAL.PY IMPORTS ==="
head -n 40 app/web/components/technical.py

echo
echo "=== COMPILE ==="

uv run python -m py_compile \
    app/web/components/technical.py \
    app/web/components/technical_modules/*.py
```

Если получаем **без ошибок**, запускаем:

```bash
uv run python -m app.web.main
```

И архитектура будет такой:

```text
app/web/components/
│
├── technical.py                 ← сборщик окна
│
└── technical_modules/
    ├── __init__.py
    ├── photo_processing.py
    ├── last_run.py
    ├── automation.py
    ├── qwen.py
    ├── data.py
    ├── system.py
    └── fingerprints.py
```

Это даже лучше первоначального варианта: **`technical.py` сохраняет старый импорт**

```python
from app.web.components.technical import show_technical
```

и поэтому `main.py` вообще **не надо менять**.

После запуска посмотрим окно.

---

### 👤 **User** — 2026-08-16 19:15:05

dino, qwen другой backend не трогаем

---

### 🤖 **Assistant** — 2026-08-16 19:15:06

Да. **Абсолютно не трогаем.**

Фиксируем границу:

```text id="backend01"
СУЩЕСТВУЮЩИЙ BACKEND
────────────────────────────────

DINO / v33
Qwen3-VL 4B
Fingerprint
Recognizer
Сортировка
Существующие скрипты
PostgreSQL
```

**Никаких изменений** в них на этом этапе.

Мы сейчас работаем только с:

```text id="backend02"
app/web/
└── components/
    ├── technical.py
    └── technical_modules/
        ├── photo_processing.py
        ├── last_run.py
        ├── automation.py
        ├── qwen.py
        ├── data.py
        ├── system.py
        └── fingerprints.py
```

Причём кнопки пока **не запускают DINO/Qwen**, а только показывают:

> «Будет подключено следующим этапом».

Сначала доводим **предпроект и UI технического окна** до удобного состояния.

И исправление с `technical → technical_modules` — это исключительно устранение конфликта Python-модулей, **к backend распознавания оно отношения не имеет**.

---

### 👤 **User** — 2026-08-16 19:15:18

mv app/web/components/technical \
   app/web/components/technical_modules

echo "=== CHECK ==="
ls -lah app/web/components/technical.py
ls -lah app/web/components/technical_modules/
=== CHECK ===
-rw-rw-r-- 1 alexice alexice 1.4K Aug 16 19:14 app/web/components/technical.py
total 40K
drwxrwxr-x 3 alexice alexice 4.0K Aug 16 19:14 .
drwxrwxr-x 4 alexice alexice 4.0K Aug 16 19:15 ..
-rw-rw-r-- 1 alexice alexice 1.2K Aug 16 19:14 automation.py
-rw-rw-r-- 1 alexice alexice  810 Aug 16 19:14 data.py
-rw-rw-r-- 1 alexice alexice  808 Aug 16 19:14 fingerprints.py
-rw-rw-r-- 1 alexice alexice    0 Aug 16 19:14 __init__.py
-rw-rw-r-- 1 alexice alexice  641 Aug 16 19:14 last_run.py
-rw-rw-r-- 1 alexice alexice 1.7K Aug 16 19:14 photo_processing.py
drwxrwxr-x 2 alexice alexice 4.0K Aug 16 19:14 __pycache__
-rw-rw-r-- 1 alexice alexice 1.2K Aug 16 19:14 qwen.py
-rw-rw-r-- 1 alexice alexice 1.1K Aug 16 19:14 system.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 19:15:21

Отлично. Теперь структура правильная. **DINO/Qwen/backend не затронуты.**

Следующий шаг — только проверить импорты и запуск.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== FIX IMPORT PATHS ==="

sed -i \
's/app\.web\.components\.technical\./app.web.components.technical_modules./g' \
app/web/components/technical.py

echo
echo "=== TECHNICAL IMPORTS ==="
grep -n "^from app.web.components" \
app/web/components/technical.py

echo
echo "=== COMPILE TECHNICAL ==="

uv run python -m py_compile \
    app/web/components/technical.py \
    app/web/components/technical_modules/*.py

echo
echo "=== COMPILE MAIN ==="

uv run python -m py_compile \
    app/web/main.py

echo
echo "=== OK ==="
```

Если увидишь:

```text
=== OK ===
```

запускай:

```bash
uv run python -m app.web.main
```

### Что сейчас должно произойти

Существующая строка в `main.py`:

```python
from app.web.components.technical import show_technical
```

остаётся **без изменений**.

А внутри `technical.py` теперь:

```text
technical.py
     │
     ├── photo_processing.py
     ├── last_run.py
     ├── automation.py
     ├── qwen.py
     ├── data.py
     ├── system.py
     └── fingerprints.py
```

То есть мы получили модульное техническое окно, **не вмешиваясь в существующий DINO/Qwen pipeline**.

После запуска покажи вывод.

---

### 👤 **User** — 2026-08-16 19:16:02

nt[ybxtcrbq hfpltk ytgjlrk.xty

---

### 🤖 **Assistant** — 2026-08-16 19:16:03

> **Decoding Russian keyboard garble**
>
>
> **Decoded Russian keyboard garble**
>
> 
>
> Worked for 5s

Похоже, текст набран в неправильной раскладке. Переключи клавиатуру на русский и напиши ещё раз — я пойму.

---

### 👤 **User** — 2026-08-16 19:16:18

технический раздел не подключен

---

### 🤖 **Assistant** — 2026-08-16 19:16:19

Да. Значит, **не будем пока трогать остальную систему**. Нужно посмотреть, как сейчас открывается техническое окно из `header.py` — скорее всего, после перестройки `technical.py` связь с кнопкой открытия потерялась или вообще не была подключена в текущем `main.py`.

Сначала давай найдём точку вызова. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== TECHNICAL REFERENCES ==="

grep -RniE \
"show_technical|Технический|technical" \
app/web \
--include="*.py" \
--exclude-dir=__pycache__
```

И отдельно:

```bash
echo
echo "=== HEADER ==="

sed -n '1,280p' app/web/components/header.py
```

**DINO, Qwen и весь backend пока вообще не трогаем.**

После этого я дам точечное исправление именно подключения технического окна.

---

### 👤 **User** — 2026-08-19 21:37:48

дай скрипт проверки скорости работы qwen 2.5 vl instruct 7b qquf и qwen 3 4b vl

---

### 🤖 **Assistant** — 2026-08-19 21:37:51

Да. Для твоего проекта лучше сделать **одинаковый тест для обеих моделей через Ollama**, чтобы сравнение было честным:

- одна и та же фотография;
- один и тот же prompt;
- одинаковое количество повторов;
- первый запуск отдельно как **cold start**;
- затем несколько **warm runs**;
- измеряем:
  - общее время;
  - время загрузки/генерации, если Ollama его отдаёт;
  - tokens/sec;
  - prompt tokens;
  - generated tokens;
  - среднее и медиану.

Для твоих моделей можно сравнить, например:

```text
qwen2.5-vl:7b
qwen3-vl:4b
```

Если GGUF `Qwen2.5-VL 7B` у тебя зарегистрирован в Ollama под другим именем — скрипт позволит указать его аргументом.

### Скрипт

Создай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/benchmark_qwen_vl.py <<'PY'
#!/usr/bin/env python3

import argparse
import base64
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

PROMPT = """Проанализируй фотографию рекламной конструкции.

Определи:
1. клиента;
2. бренд;
3. категорию;
4. весь читаемый текст;
5. основные объекты непосредственно на рекламной конструкции;
6. основные цвета;
7. подробное описание рекламной конструкции.

Ответ дай кратко, структурированно и без лишних рассуждений."""

def check_ollama():
    try:
        with urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"[ERROR] Ollama недоступен: {e}")
        sys.exit(1)

def get_models():
    data = check_ollama()
    return [
        x.get("name")
        for x in data.get("models", [])
    ]

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def run_model(model, image_b64):
    payload = {
        "model": model,
        "prompt": PROMPT,
        "images": [image_b64],
        "stream": False,
        "options": {
            "temperature": 0,
        },
    }

    data = json.dumps(payload).encode("utf-8")

    req = Request(
        OLLAMA_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
        },
    )

    start = time.perf_counter()

    with urlopen(req, timeout=600) as response:
        result = json.loads(response.read())

    wall_time = time.perf_counter() - start

    return result, wall_time

def print_result(model, run_number, result, wall_time):
    eval_count = result.get("eval_count", 0)
    eval_duration = result.get("eval_duration", 0)

    prompt_count = result.get("prompt_eval_count", 0)
    prompt_duration = result.get("prompt_eval_duration", 0)

    if eval_duration:
        tok_sec = eval_count / (eval_duration / 1e9)
    else:
        tok_sec = 0

    print()
    print(
        f"RUN {run_number}: {model}"
    )
    print(
        f"  wall time:       {wall_time:.3f} sec"
    )
    print(
        f"  prompt tokens:   {prompt_count}"
    )
    print(
        f"  output tokens:   {eval_count}"
    )
    print(
        f"  generation:      {eval_duration / 1e9:.3f} sec"
    )
    print(
        f"  generation rate: {tok_sec:.2f} tok/s"
    )
    print(
        f"  prompt eval:     {prompt_duration / 1e9:.3f} sec"
    )

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Qwen-VL models through Ollama"
    )

    parser.add_argument(
        "image",
        help="Путь к JPG/PNG для теста",
    )

    parser.add_argument(
        "--models",
        nargs="+",
        default=[
            "qwen2.5-vl:7b",
            "qwen3-vl:4b",
        ],
        help="Модели Ollama",
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Количество warm запусков",
    )

    parser.add_argument(
        "--cold",
        action="store_true",
        help="Сделать отдельный cold-start запуск",
    )

    args = parser.parse_args()

    image = Path(args.image)

    if not image.exists():
        print(f"[ERROR] Файл не найден: {image}")
        sys.exit(1)

    if not image.is_file():
        print(f"[ERROR] Это не файл: {image}")
        sys.exit(1)

    print("=" * 70)
    print("QWEN VL BENCHMARK")
    print("=" * 70)

    print(f"IMAGE: {image}")
    print(f"SIZE:  {image.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"RUNS:  {args.runs}")

    available = get_models()

    print()
    print("OLLAMA MODELS:")
    for m in available:
        print(f"  {m}")

    image_b64 = encode_image(image)

    all_results = {}

    for model in args.models:

        print()
        print("=" * 70)
        print(f"MODEL: {model}")
        print("=" * 70)

        if model not in available:
            print(
                f"[WARNING] Модель '{model}' "
                f"не найдена в `ollama list`."
            )
            print("Пропускаю.")
            continue

        # ------------------------------------------------------
        # COLD START
        # ------------------------------------------------------

        if args.cold:
            print()
            print("COLD START")
            print("-" * 70)

            result, wall = run_model(
                model,
                image_b64,
            )

            print_result(
                model,
                "COLD",
                result,
                wall,
            )

        # ------------------------------------------------------
        # WARM RUNS
        # ------------------------------------------------------

        times = []
        tok_rates = []
        output_tokens = []

        for i in range(1, args.runs + 1):

            result, wall = run_model(
                model,
                image_b64,
            )

            eval_count = result.get(
                "eval_count",
                0,
            )

            eval_duration = result.get(
                "eval_duration",
                0,
            )

            if eval_duration:
                tok_sec = (
                    eval_count
                    / (eval_duration / 1e9)
                )
            else:
                tok_sec = 0

            times.append(wall)
            tok_rates.append(tok_sec)
            output_tokens.append(eval_count)

            print_result(
                model,
                i,
                result,
                wall,
            )

        # ------------------------------------------------------
        # SUMMARY
        # ------------------------------------------------------

        summary = {
            "model": model,
            "runs": len(times),
            "wall_avg": statistics.mean(times),
            "wall_median": statistics.median(times),
            "wall_min": min(times),
            "wall_max": max(times),
            "tok_sec_avg": statistics.mean(tok_rates),
            "tok_sec_median": statistics.median(tok_rates),
            "output_tokens_avg": statistics.mean(
                output_tokens
            ),
        }

        all_results[model] = summary

        print()
        print("SUMMARY")
        print("-" * 70)
        print(
            f"  average wall:   "
            f"{summary['wall_avg']:.3f} sec"
        )
        print(
            f"  median wall:    "
            f"{summary['wall_median']:.3f} sec"
        )
        print(
            f"  min wall:       "
            f"{summary['wall_min']:.3f} sec"
        )
        print(
            f"  max wall:       "
            f"{summary['wall_max']:.3f} sec"
        )
        print(
            f"  average tok/s:   "
            f"{summary['tok_sec_avg']:.2f}"
        )
        print(
            f"  median tok/s:    "
            f"{summary['tok_sec_median']:.2f}"
        )

    # ----------------------------------------------------------
    # FINAL COMPARISON
    # ----------------------------------------------------------

    print()
    print()
    print("=" * 70)
    print("FINAL COMPARISON")
    print("=" * 70)

    print(
        f"{'MODEL':28} "
        f"{'SEC':>10} "
        f"{'TOK/S':>10}"
    )

    print("-" * 70)

    for model, s in all_results.items():

        print(
            f"{model:28} "
            f"{s['wall_median']:10.3f} "
            f"{s['tok_sec_median']:10.2f}"
        )

    output = Path(
        "data"
        "/"
        "benchmark_qwen_vl.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            all_results,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"Результат сохранён: {output}"
    )

if __name__ == "__main__":
    main()
PY

chmod +x scripts/benchmark_qwen_vl.py
```

### Сначала посмотрим, как модели называются у тебя

```bash
ollama list
```

Если там есть:

```text
qwen2.5-vl:7b
qwen3-vl:4b
```

можно сразу:

```bash
uv run python scripts/benchmark_qwen_vl.py \
    "data/input/test/ИМЯ_ФОТО.JPG" \
    --runs 3 \
    --cold
```

Если имена другие:

```bash
uv run python scripts/benchmark_qwen_vl.py \
    "data/input/test/ИМЯ_ФОТО.JPG" \
    --models \
    "ИМЯ_QWEN25" \
    "ИМЯ_QWEN3" \
    --runs 3 \
    --cold
```

### Для более честного сравнения

Я бы потом сделал **10 warm-запусков**, но сначала достаточно 3:

```bash
uv run python scripts/benchmark_qwen_vl.py \
    "data/input/test/ИМЯ_ФОТО.JPG" \
    --runs 10 \
    --cold
```

Причём для нашего проекта наиболее интересна не только `tok/s`, а **полное время обработки одной фотографии**:

```text
Qwen2.5-VL 7B GGUF
    ↓
X.XX сек / фото

Qwen3-VL 4B
    ↓
X.XX сек / фото
```

Именно это потом можно экстраполировать на **100 / 1 000 / 10 000 фотографий** и понять, насколько Qwen3-VL 4B реально быстрее для нашего фотоотчёта.

---

### 👤 **User** — 2026-08-19 21:39:28

скачать qwen2.5-vl:7b

---

### 🤖 **Assistant** — 2026-08-19 21:39:29

Если речь именно про Ollama, команда простая:

```bash
ollama pull qwen2.5vl:7b
```

После скачивания проверь:

```bash
ollama list
```

И затем можно проверить, что модель запускается:

```bash
ollama run qwen2.5vl:7b
```

Но **не меняем текущую рабочую `qwen3-vl:4b`** — это будет отдельная модель только для сравнения производительности.

---

### 👤 **User** — 2026-08-19 21:40:46

/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily  input

---

### 🤖 **Assistant** — 2026-08-19 21:40:47

Да. Тогда для теста берём фотографии из:

```text id="0y1h6k"
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily
```

Сначала скачиваем модель:

```bash
ollama pull qwen2.5vl:7b
```

Проверяем:

```bash
ollama list
```

А затем запускаем наш benchmark на первой фотографии из `daily` автоматически, без необходимости вручную вводить имя файла:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

IMG=$(find /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily \
  -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) \
  | sort | head -n 1)

echo "TEST IMAGE:"
echo "$IMG"

uv run python scripts/benchmark_qwen_vl.py \
  "$IMG" \
  --models \
  "qwen2.5vl:7b" \
  "qwen3-vl:4b" \
  --runs 3 \
  --cold
```

Это сравнит **Qwen 2.5 VL 7B vs Qwen 3 VL 4B на одной и той же фотографии**.

Если `ollama list` покажет другое точное имя Qwen 2.5, пришли вывод — подставим его, не трогая рабочую Qwen 3.

---

### 👤 **User** — 2026-08-19 21:41:20

давай на 20 первых фото

---

### 🤖 **Assistant** — 2026-08-19 21:41:24

Да. Для 20 первых фото лучше сделать **один и тот же набор из `daily` для обеих моделей**, чтобы сравнение было честным.

Сначала проверь, что модель скачана:

```bash
ollama list
```

Затем запускай benchmark на **20 первых фотографиях**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > /tmp/run_qwen_20.sh <<'SH'
#!/bin/bash

set -u

INPUT="/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily"

MODELS=(
    "qwen2.5vl:7b"
    "qwen3-vl:4b"
)

mkdir -p data/benchmark_qwen_vl_20

mapfile -t IMAGES < <(
    find "$INPUT" -type f \
        \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) \
        | sort \
        | head -n 20
)

echo "============================================================"
echo "QWEN 20 PHOTO BENCHMARK"
echo "============================================================"
echo "INPUT: $INPUT"
echo "PHOTOS: ${#IMAGES[@]}"
echo

if [ "${#IMAGES[@]}" -lt 20 ]; then
    echo "WARNING: найдено меньше 20 фотографий"
fi

for MODEL in "${MODELS[@]}"; do

    SAFE_NAME="${MODEL//:/_}"
    RESULT="data/benchmark_qwen_vl_20/${SAFE_NAME}.csv"

    echo
    echo "============================================================"
    echo "MODEL: $MODEL"
    echo "============================================================"

    printf "photo\tseconds\toutput_tokens\ttokens_sec\n" > "$RESULT"

    TOTAL_TIME=0
    TOTAL_TOKENS=0

    N=0

    for IMAGE in "${IMAGES[@]}"; do

        N=$((N + 1))

        echo
        echo "[$N/${#IMAGES[@]}] $(basename "$IMAGE")"

        START=$(date +%s.%N)

        RESPONSE=$(curl -s http://127.0.0.1:11434/api/generate \
            -H "Content-Type: application/json" \
            -d "$(python3 - "$MODEL" "$IMAGE" <<'PY'
import base64
import json
import sys

model = sys.argv[1]
image = sys.argv[2]

with open(image, "rb") as f:
    encoded = base64.b64encode(f.read()).decode()

payload = {
    "model": model,
    "prompt": """Проанализируй рекламную конструкцию на фотографии.
Определи клиента, бренд, категорию, читаемый текст,
объекты на рекламной конструкции, основные цвета
и краткое описание.
Отвечай структурированно и без лишних рассуждений.""",
    "images": [encoded],
    "stream": False,
    "options": {
        "temperature": 0
    }
}

print(json.dumps(payload, ensure_ascii=False))
PY
)" 

        END=$(date +%s.%N)

        SECONDS=$(python3 - "$START" "$END" <<'PY'
import sys
print(float(sys.argv[2]) - float(sys.argv[1]))
PY
)

        TOKENS=$(python3 - "$RESPONSE" <<'PY'
import json
import sys

try:
    x = json.loads(sys.argv[1])
    print(int(x.get("eval_count", 0)))
except Exception:
    print(0)
PY
)

        EVAL_NS=$(python3 - "$RESPONSE" <<'PY'
import json
import sys

try:
    x = json.loads(sys.argv[1])
    print(int(x.get("eval_duration", 0)))
except Exception:
    print(0)
PY
)

        TOKENS_SEC=$(python3 - "$TOKENS" "$EVAL_NS" <<'PY'
import sys

tokens = int(sys.argv[1])
ns = int(sys.argv[2])

if ns:
    print(tokens / (ns / 1e9))
else:
    print(0)
PY
)

        printf "%s\t%.3f\t%d\t%.2f\n" \
            "$(basename "$IMAGE")" \
            "$SECONDS" \
            "$TOKENS" \
            "$TOKENS_SEC" >> "$RESULT"

        TOTAL_TIME=$(python3 - "$TOTAL_TIME" "$SECONDS" <<'PY'
import sys
print(float(sys.argv[1]) + float(sys.argv[2]))
PY
)

        TOTAL_TOKENS=$((TOTAL_TOKENS + TOKENS))

        echo "  time:    ${SECONDS}s"
        echo "  tokens:  $TOKENS"
        echo "  tok/s:   ${TOKENS_SEC}"

    done

    AVG_TIME=$(python3 - "$TOTAL_TIME" "${#IMAGES[@]}" <<'PY'
import sys
print(float(sys.argv[1]) / int(sys.argv[2]))
PY
)

    AVG_TOKENS=$(python3 - "$TOTAL_TOKENS" "${#IMAGES[@]}" <<'PY'
import sys
print(float(sys.argv[1]) / int(sys.argv[2]))
PY
)

    echo
    echo "------------------------------------------------------------"
    echo "SUMMARY: $MODEL"
    echo "------------------------------------------------------------"
    echo "Photos:              ${#IMAGES[@]}"
    echo "Total time:          ${TOTAL_TIME}s"
    echo "Average / photo:     ${AVG_TIME}s"
    echo "Average output:      ${AVG_TOKENS} tokens"
    echo "Results:             $RESULT"

done

echo
echo "============================================================"
echo "BENCHMARK FINISHED"
echo "============================================================"
SH

chmod +x /tmp/run_qwen_20.sh

/tmp/run_qwen_20.sh
```

В конце получим примерно:

```text
SUMMARY: qwen2.5vl:7b
Photos:              20
Total time:          XXXs
Average / photo:     XX.Xs
Average output:      XXX tokens

SUMMARY: qwen3-vl:4b
Photos:              20
Total time:          XXXs
Average / photo:     XX.Xs
Average output:      XXX tokens
```

Результаты сохранятся отдельно:

```text
data/benchmark_qwen_vl_20/qwen2.5vl_7b.csv
data/benchmark_qwen_vl_20/qwen3-vl_4b.csv
```

**Важно:** обе модели последовательно обработают **одни и те же 20 фотографий**, поэтому сравнение времени будет значительно показательнее, чем тест на одной фотографии.

---

### 👤 **User** — 2026-08-19 21:44:44

насколько сложно переключать модель для работы в интерфейсе?\

---

### 🤖 **Assistant** — 2026-08-19 21:44:45

Нет, **технически это несложно**. Если оставить архитектуру, которую мы сейчас выбрали, переключение модели можно сделать очень аккуратно и **не трогать сам DINO/backend**.

Для Qwen достаточно вынести имя модели в конфигурацию:

```text
Qwen3-VL 4B
        ↓
qwen3-vl:4b

Qwen2.5-VL 7B
        ↓
qwen2.5vl:7b
```

А интерфейс будет иметь, например:

```text
РАСПОЗНАВАНИЕ

Модель:
[ Qwen3-VL 4B ▼ ]

☑ Автоматически запускать после DINO

[ ▶ Повторно запустить Qwen ]
```

В списке:

```text
Qwen3-VL 4B
Qwen2.5-VL 7B
```

### Что реально нужно изменить

Примерно **3 уровня**:

1. **Настройка**
   ```python
   QWEN_MODEL = "qwen3-vl:4b"
   ```

2. **UI**
   ```text
   выбранная модель → STATE / config
   ```

3. **Qwen runner**
   Вместо жёстко заданного:

   ```python
   model = "qwen3-vl:4b"
   ```

   использовать:

   ```python
   model = выбранная_модель
   ```

И всё.

### Но я бы сделал ещё лучше

Не переключать модель прямо во время работающей обработки.

Например:

```text
Модель Qwen:
[ Qwen3-VL 4B ▼ ]

Текущая модель: Qwen3-VL 4B
Статус: готова

                    [Сохранить]
```

После выбора:

```text
Qwen2.5-VL 7B
```

следующий запуск Qwen уже использует её.

При этом:

**DINO → сортировка → Qwen**

останется абсолютно тем же pipeline.

---

### И важный момент для нашего проекта

Я бы **не делал две независимые версии Qwen-кода**.

То есть не:

```text
qwen3.py
qwen25.py
```

а один:

```text
qwen_service.py
```

который получает:

```text
model = "qwen3-vl:4b"
```

или

```text
model = "qwen2.5vl:7b"
```

Так мы сможем позже добавить хоть:

```text
Qwen3-VL 4B
Qwen2.5-VL 7B
Qwen3-VL 8B
```

без переписывания интерфейса.

**Поэтому переключение модели я бы заложил уже сейчас в архитектуру технического окна, но сам backend пока не трогал**, как мы договорились. Сначала закончим UI и сравним 20 фотографий — тогда будет понятно, какую модель поставить основной.

---

### 👤 **User** — 2026-08-19 21:47:28

какой размер выходных токенов сейчас?

---

### 🤖 **Assistant** — 2026-08-19 21:47:31

Если ты имеешь в виду **текущий Qwen3-VL 4B в нашем интерфейсе**, то сейчас у нас **нет жёстко заданного лимита выходных токенов**.

В нашем benchmark мы тоже пока не задавали `num_predict`, поэтому Ollama генерирует до естественного завершения ответа.

Для текущего промпта обычно это будет порядка **нескольких сотен токенов**, но точное значение нужно смотреть по `eval_count` для конкретных фотографий.

В тесте на 20 фото мы как раз сохраняем:

```text
output_tokens
tokens_sec
seconds
```

Так что после теста можно будет увидеть, например:

```text
Qwen3-VL 4B
среднее: 180 токенов/фото

Qwen2.5-VL 7B
среднее: 240 токенов/фото
```

Если цель — **ускорить обработку 1000+ фотографий**, я бы отдельно протестировал ограничение примерно **256–384 выходных токена**. Для нашей структуры метаданных этого, скорее всего, будет достаточно, но сначала лучше посмотреть реальные `eval_count` на твоих 20 фотографиях.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)

---
