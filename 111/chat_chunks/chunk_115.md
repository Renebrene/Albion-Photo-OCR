## СЕССИЯ: Продолжение разговора 1

**Создано:** 2026-08-18 12:11:53
**Обновлено:** 2026-08-19 17:07:58
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8421d7-3160-83ea-be54-4a2ad097babc](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8421d7-3160-83ea-be54-4a2ad097babc)

---

### 🤖 **Assistant** — 2026-08-18 13:01:40

Отлично. Теперь уже достаточно данных, чтобы сделать **реальную статистику обработчиков**.

Причём я бы сейчас **не трогал `last_run.py` и pipeline**. Добавим статистику прямо в `Данные`, используя существующие файлы и текущий `PHOTO_INDEX`.

### Что покажем

**Общая статистика**
- Фото в текущем `PHOTO_INDEX` — **526**
- Адресов — **18**
- Записей PostgreSQL — **100**

**DINO / Hybrid**
- последний daily-запуск — `20260818_115048`
- количество фото в результате
- количество адресных папок
- количество реально разложенных фотографий

**Qwen3-VL 4B**
- количество JSON-файлов
- количество обработанных фото
- количество адресов
- последний результат
- среднее время, если оно есть в `summary.json`

И всё это будет вычисляться автоматически при открытии вкладки.

---

### Сначала посмотрим `summary.json`

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat data/metadata/qwen4b/summary.json
```

И ещё:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find data/output/daily/20260818_115048 \
    -maxdepth 2 -type f \
    | head -20
```

После этого я дам тебе **готовый `data.py` целиком**, который просто заменит нынешний:

```python
Клиентов: 7
Адресов: 18
Правил исправления: 0
```

на нормальную живую статистику.

---

### 👤 **User** — 2026-08-18 13:02:13

},
    {
      "file": "Ашхабадский_09.JPG",
      "address": "85_v33",
      "status": "ok",
      "time_sec": 10.88,
      "client": "",
      "brand": "",
      "category": "выборы",
      "confidence": 95
    },
    {
      "file": "Ашхабадский_10.JPG",
      "address": "85_v33",
      "status": "ok",
      "time_sec": 8.63,
      "client": "",
      "brand": "",
      "category": "",
      "confidence": 30
    },
    {
      "file": "Ашхабадский_11.JPG",
      "address": "85_v33",
      "status": "ok",
      "time_sec": 8.54,
      "client": "",
      "brand": "",
      "category": "",
      "confidence": 0
    }
  ]
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v022

find data/output/daily/20260818_115048 \
    -maxdepth 2 -type f \
    | head -20
data/output/daily/20260818_115048/95_v33/Вавилова52_12.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_13.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_07.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_09.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_16.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_05.JPG
data/output/daily/20260818_115048/95_v33/Фурмановская ул. 106 - Плиева ул. 43 А (29).JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_11.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_10.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_06.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_14.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_15.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_04.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_01.JPG
data/output/daily/20260818_115048/95_v33/Зорге_17.jpg
data/output/daily/20260818_115048/95_v33/Вавилова52_02.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_03.JPG
data/output/daily/20260818_115048/95_v33/Вавилова52_08.JPG
data/output/daily/20260818_115048/87_v33/Шеболдаева8_05.JPG
data/output/daily/20260818_115048/87_v33/Шеболдаева8_13.JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:02:15

Да, этого уже достаточно. `summary.json` у нас содержит всё необходимое по Qwen: `file`, `address`, `status`, `time_sec`, `client`, `brand`, `category`, `confidence`.

Сделаем статистику **без изменения pipeline**.

Я предлагаю заменить `data.py` целиком. Сначала сделаем безопасную версию, которая:

- берёт текущие `526` из `PHOTO_INDEX`;
- находит последний daily-run;
- считает фотографии и адреса в нём;
- читает `summary.json`;
- считает Qwen `ok/error`;
- считает среднее время Qwen;
- считает среднюю confidence;
- показывает состояние **DINO v33 / Hybrid v12 / Qwen3-VL 4B**.

### 1. Замени `data.py`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/web/components/technical_modules/data.py <<'PY'
import json
from pathlib import Path

from nicegui import ui

from app.web.components.photos import PHOTO_INDEX
from app.web.photo_db import get_photo_records

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"

DAILY_ROOT = PROJECT / "data" / "output" / "daily"
QWEN_ROOT = PROJECT / "data" / "metadata" / "qwen4b"

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

def latest_daily_root():
    if not DAILY_ROOT.exists():
        return None

    dirs = [
        p for p in DAILY_ROOT.iterdir()
        if p.is_dir()
    ]

    if not dirs:
        return None

    return max(
        dirs,
        key=lambda p: p.name,
    )

def count_images(folder):
    if folder is None or not folder.exists():
        return 0

    return sum(
        1
        for p in folder.rglob("*")
        if (
            p.is_file()
            and p.suffix.lower() in IMAGE_EXTENSIONS
        )
    )

def daily_stats():
    root = latest_daily_root()

    if root is None:
        return {
            "run": "—",
            "addresses": 0,
            "photos": 0,
        }

    address_dirs = [
        p for p in root.iterdir()
        if p.is_dir()
    ]

    return {
        "run": root.name,
        "addresses": len(address_dirs),
        "photos": count_images(root),
    }

def qwen_stats():
    summary = QWEN_ROOT / "summary.json"

    if not summary.exists():
        return {
            "status": "Нет данных",
            "photos": 0,
            "ok": 0,
            "errors": 0,
            "avg_time": 0,
            "avg_confidence": 0,
            "addresses": 0,
        }

    try:
        data = json.loads(
            summary.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return {
            "status": "Ошибка чтения",
            "photos": 0,
            "ok": 0,
            "errors": 0,
            "avg_time": 0,
            "avg_confidence": 0,
            "addresses": 0,
        }

    if not isinstance(data, list):
        return {
            "status": "Неверный формат",
            "photos": 0,
            "ok": 0,
            "errors": 0,
            "avg_time": 0,
            "avg_confidence": 0,
            "addresses": 0,
        }

    total = len(data)

    ok = sum(
        1
        for row in data
        if row.get("status") == "ok"
    )

    errors = total - ok

    times = [
        float(row["time_sec"])
        for row in data
        if row.get("time_sec") is not None
    ]

    confidences = [
        float(row["confidence"])
        for row in data
        if row.get("confidence") is not None
    ]

    addresses = {
        row.get("address")
        for row in data
        if row.get("address")
    }

    return {
        "status": "ГОТОВ" if total else "Нет данных",
        "photos": total,
        "ok": ok,
        "errors": errors,
        "avg_time": (
            sum(times) / len(times)
            if times
            else 0
        ),
        "avg_confidence": (
            sum(confidences) / len(confidences)
            if confidences
            else 0
        ),
        "addresses": len(addresses),
    }

def build_stat(label, value):
    with ui.card().classes(
        "p-3 min-w-[150px]"
    ):
        ui.label(label).classes(
            "text-xs text-grey-6"
        )
        ui.label(value).classes(
            "text-xl font-bold"
        )

def build_data():

    daily = daily_stats()
    qwen = qwen_stats()

    try:
        db_records = get_photo_records()
        db_count = len(db_records)
    except Exception:
        db_count = 0

    photo_count = sum(
        len(files)
        for files in PHOTO_INDEX.values()
    )

    address_count = len(PHOTO_INDEX)

    with ui.card().classes("w-full"):

        ui.label(
            "СТАТИСТИКА"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        with ui.row().classes(
            "w-full gap-3 flex-wrap"
        ):

            build_stat(
                "Фото в текущем индексе",
                str(photo_count),
            )

            build_stat(
                "Адресов",
                str(address_count),
            )

            build_stat(
                "Записей PostgreSQL",
                str(db_count),
            )

    with ui.card().classes("w-full"):

        ui.label(
            "СТАТУС ОБРАБОТЧИКОВ"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        # ====================================================
        # DINO
        # ====================================================

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            with ui.column().classes("gap-0"):

                ui.label(
                    "DINO v33"
                ).classes(
                    "text-base font-bold"
                )

                ui.label(
                    "Распознавание сцен"
                ).classes(
                    "text-xs text-grey-6"
                )

            ui.badge(
                "ГОТОВ",
                color="positive",
            )

        ui.separator().classes("my-2")

        # ====================================================
        # HYBRID
        # ====================================================

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            with ui.column().classes("gap-0"):

                ui.label(
                    "Hybrid v12"
                ).classes(
                    "text-base font-bold"
                )

                ui.label(
                    f"Последний запуск: {daily['run']}"
                ).classes(
                    "text-xs text-grey-6"
                )

            ui.badge(
                "ГОТОВ" if daily["photos"] else "НЕТ ДАННЫХ",
                color="positive" if daily["photos"] else "warning",
            )

        with ui.row().classes(
            "gap-6 mt-1"
        ):

            ui.label(
                f"Фото: {daily['photos']}"
            )

            ui.label(
                f"Адресов: {daily['addresses']}"
            )

        ui.separator().classes("my-2")

        # ====================================================
        # QWEN
        # ====================================================

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            with ui.column().classes("gap-0"):

                ui.label(
                    "Qwen3-VL 4B"
                ).classes(
                    "text-base font-bold"
                )

                ui.label(
                    "Анализ содержимого фотографий"
                ).classes(
                    "text-xs text-grey-6"
                )

            qwen_color = (
                "positive"
                if qwen["status"] == "ГОТОВ"
                else "warning"
            )

            ui.badge(
                qwen["status"],
                color=qwen_color,
            )

        with ui.row().classes(
            "gap-6 mt-1 flex-wrap"
        ):

            ui.label(
                f"Обработано: {qwen['photos']}"
            )

            ui.label(
                f"OK: {qwen['ok']}"
            )

            ui.label(
                f"Ошибок: {qwen['errors']}"
            )

            ui.label(
                f"Адресов: {qwen['addresses']}"
            )

            ui.label(
                f"Среднее время: {qwen['avg_time']:.2f} сек"
            )

            ui.label(
                f"Средняя уверенность: {qwen['avg_confidence']:.1f}%"
            )

    with ui.card().classes("w-full"):

        ui.label(
            "ДАННЫЕ"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

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
```

### 2. Перезапуск

Поскольку UI у тебя работает через systemd, не запускай второй `uv`.

```bash
sudo systemctl restart lora.service
```

Потом:

```bash
sudo systemctl status lora.service --no-pager
```

И открой/обнови UI.

---

### Важный момент

Сейчас **Qwen `summary.json` — это общий накопленный summary**, а не обязательно только запуск `20260818_115048`. Поэтому показатель:

> `Qwen обработано`

может быть больше 526.

Это нормально на первом этапе. **Следующим шагом можем привязать Qwen статистику именно к текущему daily-run**, чтобы панель показывала строго:

```text
Текущий запуск
526 фото
DINO: 526
Hybrid: 526
Qwen: N / 526
```

Это будет гораздо полезнее для контроля ежедневной обработки.

---

### 👤 **User** — 2026-08-18 13:04:36

DINO v33

Распознавание сцен

ГОТОВ

---

Hybrid v12

Последний запуск: 20260818\_115048

ГОТОВ

Фото: 526

Адресов: 18

---

Qwen3-VL 4B

Анализ содержимого фотографий

Неверный формат

Обработано: 0

OK: 0

Ошибок: 0

Адресов: 0

Среднее время: 0.00 сек

Средняя уверенность: 0.0%

ДАННЫЕ
   Надо дино и гибрид поместить ан закладку обработка, а Квен - на закладку квен

---

### 🤖 **Assistant** — 2026-08-18 13:04:36

Да. Сейчас логика уже разделена на два процесса, но **статусы отображаются не в тех вкладках**.

Сделаем так:

### Вкладка «Обработка фото»

Оставляем только статус основной обработки:

**DINO v33**  
Распознавание сцен  
`ГОТОВ`

**Hybrid v12**  
Последний запуск: `20260818_115048`  
`ГОТОВ`  
Фото: `526`  
Адресов: `18`

То есть здесь будет отражаться именно состояние **DINO → Hybrid → сортировка**.

### Вкладка «Qwen»

Переносим туда:

**Qwen3-VL 4B**  
Анализ содержимого фотографий

и статистику:

- Обработано
- OK
- Ошибок
- Адресов
- Среднее время
- Средняя уверенность

При этом сейчас у тебя показывает:

> Неверный формат  
> Обработано: 0

хотя реальные JSON-файлы Qwen есть в `data/metadata/qwen4b`.

Значит, следующим шагом надо **не просто перенести блок**, а исправить источник статуса Qwen: он должен читать `summary.json` и/или реальные результаты текущего запуска.

И ещё важный момент: `last_run.py` сейчас вообще заглушка:

```text
Обработок ещё не запускалось
```

Её тоже логично заменить на реальные данные последнего Hybrid-запуска.

**Предлагаю сейчас сделать только UI-разделение и реальные статусы без изменения самого DINO/Hybrid/Qwen-пайплайна.**

---

### 👤 **User** — 2026-08-18 13:04:59

да

---

### 🤖 **Assistant** — 2026-08-18 13:04:59

Да. Делаем аккуратно: **алгоритмы DINO / Hybrid / Qwen не трогаем**, меняем только отображение статусов.

Сейчас сначала покажи текущий `technical_modules/system.py` — он, скорее всего, уже содержит часть блока DINO/Hybrid.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat app/web/components/technical_modules/system.py
```

И одновременно покажи начало `qwen4b_output_v01.py`, где формируется `summary.json`:

```bash
grep -n -E \
'summary|json.dump|results|processed|success|error|confidence|time_sec' \
scripts/qwen4b_output_v01.py
```

После этого я дам **готовые файлы целиком**, чтобы:

- **Обработка фото** → DINO v33 + Hybrid v12
- **Qwen** → Qwen3-VL 4B + реальные данные из `summary.json`
- текущий `20260818_115048` определялся автоматически
- `526 фото / 18 адресов` брались из фактического запуска
- `Qwen: 0` больше не показывался, если результаты реально существуют
- сам запуск `DINO → Hybrid → Qwen` останется без изменений.

---

### 👤 **User** — 2026-08-18 13:05:35

Hint: Some lines were ellipsized, use -l to show in full.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cat app/web/components/technical_modules/system.py
from nicegui import ui

from app.web.system.monitor import collect

def _format_gb(value):
    if value is None:
        return "—"

    return f"{value / (1024 ** 3):.1f} GB"

def _format_percent(value):
    if value is None:
        return "—"

    return f"{value:.1f}%"

def _format_temperature(value):
    if value is None:
        return "—"

    return f"{value:.0f} °C"

def build_system():
    with ui.card().classes("w-full"):
        ui.label("СИСТЕМА").classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        status_label = ui.label(
            "● Сервер работает"
        ).classes("text-sm")

        with ui.grid(columns=2).classes("w-full gap-2"):
            ui.label("CPU")
            cpu_label = ui.label("—")

            ui.label("Температура CPU")
            cpu_temp_label = ui.label("—")

            ui.label("GPU")
            gpu_label = ui.label("—")

            ui.label("Температура GPU")
            gpu_temp_label = ui.label("—")

            ui.label("RAM")
            ram_label = ui.label("—")

            ui.label("VRAM")
            vram_label = ui.label("—")

            ui.label("Сеть ↓ / ↑")
            network_label = ui.label("— / —")

            ui.label("Время работы")
            uptime_label = ui.label("—")

        ui.label(
            "Обновление каждые 2 секунды."
        ).classes("text-xs text-grey-6")

    def refresh():
        try:
            data = collect()

            cpu = data["cpu"]
            gpu = data["gpu"]
            ram = data["ram"]
            vram = data["vram"]
            network = data["network"]

            cpu_label.text = (
                f"{cpu['percent']:.1f}% "
                f"({cpu['cores']} потоков)"
            )

            cpu_temp_label.text = _format_temperature(
                data["cpu_temperature"]
            )

            gpu_label.text = gpu["name"]

            gpu_temp_label.text = _format_temperature(
                gpu["temperature"]
            )

            ram_label.text = (
                f"{_format_gb(ram['used'])} / "
                f"{_format_gb(ram['total'])} "
                f"({_format_percent(ram['percent'])})"
            )

            vram_label.text = (
                f"{_format_gb(vram['used'])} / "
                f"{_format_gb(vram['total'])} "
                f"({_format_percent(vram['percent'])})"
            )

            network_label.text = (
                f"{network['download_text']} ↓ / "
                f"{network['upload_text']} ↑"
            )

            uptime_label.text = data["uptime"]

            status_label.text = "● Сервер работает"

        except Exception as exc:
            status_label.text = (
                f"● Ошибка мониторинга: {exc}"
            )

    refresh()

    ui.timer(
        2.0,
        refresh,
    )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n -E \
'summary|json.dump|results|processed|success|error|confidence|time_sec' \
scripts/qwen4b_output_v01.py
71:  "confidence": 0
124:confidence — уверенность в анализе от 0 до 100.
218:    result["_time_sec"] = round(elapsed, 2)
260:    results = []
282:            results.append({
305:                json.dump(
313:                "_time_sec",
326:                "| confidence:",
327:                result.get("confidence", "")
358:            results.append({
362:                "time_sec": elapsed,
366:                "confidence": result.get("confidence", ""),
369:        except Exception as error:
373:                error
376:            results.append({
379:                "status": "error",
380:                "error": str(error),
388:    summary = {
394:        "results": results,
398:        OUTPUT_DIR / "summary.json",
403:        json.dump(
404:            summary,
418:            for x in results
426:            for x in results
434:            for x in results
435:            if x["status"] == "error"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:05:36

Отлично. `system.py` тут вообще не трогаем — это отдельная вкладка «Система».

Теперь нужно увидеть **точную структуру `summary.json` и участок Qwen**, чтобы не гадать с полями. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '240,450p' scripts/qwen4b_output_v01.py
```

И ещё:

```bash
cat data/metadata/qwen4b/summary.json | head -80
```

После этого я дам две готовые замены:

1. `app/web/components/technical_modules/photo_processing.py`
   - DINO v33
   - Hybrid v12
   - последний запуск
   - фото
   - адреса

2. `app/web/components/technical_modules/qwen.py`
   - Qwen3-VL 4B
   - обработано
   - OK
   - ошибок
   - адресов
   - среднее время
   - средняя уверенность

И **`technical.py` менять, скорее всего, вообще не понадобится** — вкладки `Обработка фото` и `Qwen` у тебя уже правильно существуют.

---

### 👤 **User** — 2026-08-18 13:05:49

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -n -E \
'summary|json.dump|results|processed|success|error|confidence|time_sec' \
scripts/qwen4b_output_v01.py
71:  "confidence": 0
124:confidence — уверенность в анализе от 0 до 100.
218:    result["_time_sec"] = round(elapsed, 2)
260:    results = []
282:            results.append({
305:                json.dump(
313:                "_time_sec",
326:                "| confidence:",
327:                result.get("confidence", "")
358:            results.append({
362:                "time_sec": elapsed,
366:                "confidence": result.get("confidence", ""),
369:        except Exception as error:
373:                error
376:            results.append({
379:                "status": "error",
380:                "error": str(error),
388:    summary = {
394:        "results": results,
398:        OUTPUT_DIR / "summary.json",
403:        json.dump(
404:            summary,
418:            for x in results
426:            for x in results
434:            for x in results
435:            if x["status"] == "error"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '240,450p' scripts/qwen4b_output_v01.py

---

### 🤖 **Assistant** — 2026-08-18 13:05:50

Да, вижу. Но сам вывод `sed` в сообщении не пришёл — только команда. Чтобы не гадать по структуре `summary.json`, давай сразу вытащим **готовую структуру файла**, который реально сейчас лежит на диске.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python - <<'PY'
import json
from pathlib import Path

p = Path("data/metadata/qwen4b/summary.json")

data = json.loads(p.read_text(encoding="utf-8"))

print("===== SUMMARY KEYS =====")
print(list(data.keys()))

print("\n===== SUMMARY =====")
for k, v in data.items():
    if k != "results":
        print(f"{k}: {v}")

print("\n===== RESULTS =====")
results = data.get("results", [])
print("count:", len(results))

for r in results[:3]:
    print(json.dumps(r, ensure_ascii=False, indent=2))
PY
```

И ещё один важный момент: у тебя Qwen уже запускается **после Hybrid автоматически** вот здесь:

```text
Hybrid v12 → result_dir
             ↓
qwen4b_output_v01.py
             ↓
data/metadata/qwen4b/<run_name>
```

Поэтому мы можем сделать правильно:

```text
┌───────────────────────┐
│ ОБРАБОТКА ФОТО        │
│                       │
│ DINO v33              │
│ ГОТОВ                 │
│                       │
│ Hybrid v12            │
│ 20260818_115048       │
│ ГОТОВ                 │
│ Фото: 526             │
│ Адресов: 18           │
└───────────────────────┘

┌───────────────────────┐
│ QWEN                  │
│                       │
│ Qwen3-VL 4B           │
│ ГОТОВ                  │
│                       │
│ Обработано: N         │
│ OK: N                 │
│ Ошибок: N             │
│ Адресов: N            │
│ Среднее время: X сек  │
│ Средняя уверенность: X%│
└───────────────────────┘
```

Причём **не будем хранить эти цифры вручную в UI**. Qwen-вкладка будет каждый раз читать актуальный `summary.json`, а вкладка обработки — определять последний каталог `data/output/daily/*`.

Пришли вывод команды выше — и я дам готовые `qwen.py` и `photo_processing.py` для замены.

---

### 👤 **User** — 2026-08-18 13:06:12

sed -n '240,450p' scripts/qwen4b_output_v01.pygrep -n -E \
'summary|json.dump|results|processed|success|error|confidence|time_sec' \
scripts/qwen4b_output_v01.py
sed: can't read scripts/qwen4b_output_v01.pygrep: No such file or directory
sed: can't read summary|json.dump|results|processed|success|error|confidence|time_sec: No such file or directory
    relative = source.relative_to(INPUT_DIR)

    address = relative.parts[0]

    return (
        OUTPUT_DIR
        / address
        / f"{source.stem}.json"
    )

def process(files):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    total_start = time.time()

    results = []

    for index, source in enumerate(files, 1):

        destination = output_path(source)

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        print()
        print("=" * 80)
        print(
            f"[{index}/{len(files)}] "
            f"{source.parent.name}/{source.name}"
        )

        if destination.exists():

            print("SKIP — metadata already exists")

            results.append({
                "file": source.name,
                "address": source.parent.name,
                "status": "skipped",
            })

            continue

        try:

            result = ask(source)

            result["address"] = source.parent.name
            result["source_file"] = str(
                source.relative_to(PROJECT)
            )

            with open(
                destination,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    result,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            elapsed = result.get(
                "_time_sec",
                0
            )

            print(
                "OK",
                "| time:",
                elapsed,
                "sec",
                "| client:",
                result.get("client", ""),
                "| brand:",
                result.get("brand", ""),
                "| confidence:",
                result.get("confidence", "")
            )

            quality = result.get(
                "image_quality",
                {}
            )

            print(
                "QUALITY:",
                quality.get("overall", ""),
                "| sharpness:",
                quality.get("sharpness", ""),
                "| banner:",
                quality.get("banner_visible", "")
            )

            environment = result.get(
                "environment",
                {}
            )

            print(
                "ENV:",
                environment.get("season", ""),
                "|",
                environment.get("weather", ""),
                "|",
                environment.get("precipitation", "")
            )

            results.append({
                "file": source.name,
                "address": source.parent.name,
                "status": "ok",
                "time_sec": elapsed,
                "client": result.get("client", ""),
                "brand": result.get("brand", ""),
                "category": result.get("category", ""),
                "confidence": result.get("confidence", ""),
            })

        except Exception as error:

            print(
                "ERROR:",
                error
            )

            results.append({
                "file": source.name,
                "address": source.parent.name,
                "status": "error",
                "error": str(error),
            })

    total_elapsed = round(
        time.time() - total_start,
        2
    )

    summary = {
        "model": MODEL,
        "input": str(INPUT_DIR),
        "output": str(OUTPUT_DIR),
        "files_in_run": len(files),
        "elapsed_sec": total_elapsed,
        "results": results,
    }

    with open(
        OUTPUT_DIR / "summary.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)
    print(
        "Processed:",
        sum(
            1
            for x in results
            if x["status"] == "ok"
        )
    )
    print(
        "Skipped:",
        sum(
            1
            for x in results
            if x["status"] == "skipped"
        )
    )
    print(
        "Errors:",
        sum(
            1
            for x in results
            if x["status"] == "error"
        )
    )
    print(
        "Total time:",
        total_elapsed,
        "sec"
    )

def main():

    global INPUT_DIR, OUTPUT_DIR

    parser = argparse.ArgumentParser()

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:06:13

Отлично, теперь структура понятна. И здесь есть важный момент: **Qwen `summary.json` не содержит готовых полей `processed`, `errors`, `avg_time` и т. п.** — их надо вычислять из `results`.

Также текущая проблема с «Неверный формат» почти наверняка из-за того, что UI ожидает другую структуру.

Делаем без изменения самого Qwen.

### 1. Заменяем `qwen.py`

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > app/web/components/technical_modules/qwen.py <<'PY'
import json
from pathlib import Path

from nicegui import ui

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"
QWEN_ROOT = PROJECT / "data" / "metadata" / "qwen4b"

def _find_latest_summary():
    """
    Ищет summary.json:
      data/metadata/qwen4b/summary.json
      data/metadata/qwen4b/<run>/summary.json

    Берёт самый свежий.
    """

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
            "state": "Нет данных",
            "processed": 0,
            "ok": 0,
            "errors": 0,
            "addresses": 0,
            "avg_time": 0.0,
            "avg_confidence": 0.0,
            "model": "Qwen3-VL 4B",
            "summary": None,
        }

    try:
        with open(
            summary_path,
            "r",
            encoding="utf-8",
        ) as f:
            summary = json.load(f)

        results = summary.get("results", [])

        ok_results = [
            x for x in results
            if x.get("status") == "ok"
        ]

        error_results = [
            x for x in results
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

        avg_time = (
            sum(times) / len(times)
            if times
            else 0.0
        )

        avg_confidence = (
            sum(confidences) / len(confidences)
            if confidences
            else 0.0
        )

        return {
            "state": "ГОТОВ",
            "processed": len(results),
            "ok": len(ok_results),
            "errors": len(error_results),
            "addresses": len(addresses),
            "avg_time": avg_time,
            "avg_confidence": avg_confidence,
            "model": summary.get(
                "model",
                "Qwen3-VL 4B",
            ),
            "summary": summary_path,
        }

    except Exception as exc:

        return {
            "state": "ОШИБКА ФОРМАТА",
            "processed": 0,
            "ok": 0,
            "errors": 0,
            "addresses": 0,
            "avg_time": 0.0,
            "avg_confidence": 0.0,
            "model": "Qwen3-VL 4B",
            "summary": summary_path,
            "error": str(exc),
        }

def build_qwen():

    with ui.card().classes("w-full"):

        ui.label(
            "РАСПОЗНАВАНИЕ"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            ui.label(
                "Qwen3-VL 4B"
            ).classes(
                "text-base font-medium"
            )

            status_label = ui.label(
                "● ГОТОВ"
            ).classes(
                "text-sm"
            )

        ui.label(
            "Анализ содержимого фотографий"
        ).classes(
            "text-sm text-grey-7"
        )

        ui.separator().classes("my-2")

        with ui.grid(columns=2).classes(
            "w-full gap-2"
        ):

            ui.label("Статус")
            state_label = ui.label("—")

            ui.label("Обработано")
            processed_label = ui.label("0")

            ui.label("OK")
            ok_label = ui.label("0")

            ui.label("Ошибок")
            errors_label = ui.label("0")

            ui.label("Адресов")
            addresses_label = ui.label("0")

            ui.label("Среднее время")
            avg_time_label = ui.label("0.00 сек")

            ui.label("Средняя уверенность")
            avg_confidence_label = ui.label("0.0%")

        ui.separator().classes("my-2")

        with ui.row().classes("gap-2"):

            ui.button(
                "⚙ Настройки распознавания",
                on_click=lambda: ui.notify(
                    "Настройки Qwen будут подключены следующим этапом"
                ),
            ).props("flat")

            ui.button(
                "↻ Обновить",
                on_click=lambda: refresh(),
            ).props("unelevated")

        source_label = ui.label(
            "Источник: —"
        ).classes(
            "text-xs text-grey-6"
        )

    def refresh():

        data = _load_qwen_status()

        state_label.text = data["state"]
        processed_label.text = str(
            data["processed"]
        )
        ok_label.text = str(
            data["ok"]
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
        elif data["state"] == "Нет данных":
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

    refresh()

    ui.timer(
        5.0,
        refresh,
    )
PY
```

### 2. Теперь `photo_processing.py`

Здесь **не меняем функцию запуска**. Просто добавим в верхнюю часть вкладки фактический статус последнего Hybrid.

Но сначала надо посмотреть, есть ли уже в этом файле какие-либо блоки статуса DINO/Hybrid, чтобы случайно не задублировать их.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -n -E \
'DINO|Hybrid|ГОТОВ|Последний запуск|Фото:|Адресов:' \
app/web/components/technical_modules/photo_processing.py
```

Если вывод пустой — я дам готовую вставку для блока статуса.

**Qwen при этом уже можно считать правильно подключённым к своей вкладке:** он будет брать фактические результаты из `summary.json`, а не из захардкоженных значений.

---

### 👤 **User** — 2026-08-18 13:06:49

PY  )   refresh,f'Ошибка: {data["error"]}'"]}'лючены следующим этапом"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -n -E \
'DINO|Hybrid|ГОТОВ|Последний запуск|Фото:|Адресов:' \
app/web/components/technical_modules/photo_processing.py
79:            f"Запуск Hybrid v12... "
134:                    f"✗ Hybrid v12: ошибка ({returncode})"
163:                    "⚠ Hybrid завершён, "
168:                    "Hybrid завершён, "
181:                "✓ Hybrid v12: сортировка завершена"
199:                    "✓ Hybrid завершён → Qwen script не найден"
210:            # Имя папки Hybrid запуска:
276:                        "✗ Hybrid v12: ✓  "
281:                        "Hybrid завершён успешно, "
290:                    "✓ Hybrid v12 + Qwen3-VL 4B: готово"
299:                    "Hybrid v12 + Qwen3-VL 4B.",
307:                    "✗ Hybrid: ✓  "
384:            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:06:50

Да. Значит сейчас `photo_processing.py` отвечает только за запуск и не имеет отдельного информационного блока. Добавим его **в начало вкладки «Обработка фото»**, не вмешиваясь в существующий запуск.

Но есть ещё один момент: у тебя Qwen уже запускается автоматически после Hybrid, поэтому в `photo_processing.py` оставляем только:

**DINO v33 → Hybrid v12**

А Qwen полностью показываем на своей вкладке.

### 1. Сначала сделаем резервную копию

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp app/web/components/technical_modules/photo_processing.py \
   app/web/components/technical_modules/photo_processing.py.bak
```

### 2. Добавим функцию поиска последнего Hybrid

В начало `photo_processing.py`, после:

```python
DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
```

добавь:

```python
DAILY_OUTPUT_ROOT = PROJECT / "data" / "output" / "daily"

def get_last_hybrid_run():
    """
    Возвращает информацию о последнем запуске Hybrid.
    """

    if not DAILY_OUTPUT_ROOT.exists():
        return None

    runs = [
        p for p in DAILY_OUTPUT_ROOT.iterdir()
        if p.is_dir()
    ]

    if not runs:
        return None

    result_dir = max(
        runs,
        key=lambda p: p.stat().st_mtime,
    )

    addresses = [
        p for p in result_dir.iterdir()
        if p.is_dir()
    ]

    photos = sum(
        1
        for address_dir in addresses
        for p in address_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in {
            ".jpg",
            ".jpeg",
            ".png",
        }
    )

    return {
        "name": result_dir.name,
        "path": result_dir,
        "photos": photos,
        "addresses": len(addresses),
    }
```

### 3. В `build_photo_processing()` добавим статус

Сейчас начало функции:

```python
def build_photo_processing():

    source_input = ui.input(
```

замени на:

```python
def build_photo_processing():

    # ============================================================
    # СТАТУС DINO / HYBRID
    # ============================================================

    with ui.card().classes("w-full"):

        ui.label(
            "РАСПОЗНАВАНИЕ СЦЕН"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            ui.label(
                "DINO v33"
            ).classes(
                "text-base font-medium"
            )

            dino_status = ui.label(
                "● ГОТОВ"
            ).classes(
                "text-sm"
            )

        ui.label(
            "Распознавание сцен"
        ).classes(
            "text-sm text-grey-7"
        )

        ui.separator().classes("my-2")

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            ui.label(
                "Hybrid v12"
            ).classes(
                "text-base font-medium"
            )

            hybrid_status = ui.label(
                "● ГОТОВ"
            ).classes(
                "text-sm"
            )

        hybrid_run_label = ui.label(
            "Последний запуск: —"
        ).classes(
            "text-sm"
        )

        hybrid_stats_label = ui.label(
            "Фото: 0    Адресов: 0"
        ).classes(
            "text-sm"
        )

    # ------------------------------------------------------------
    # Читаем последний результат
    # ------------------------------------------------------------

    last_run = get_last_hybrid_run()

    if last_run:

        hybrid_run_label.text = (
            f'Последний запуск: {last_run["name"]}'
        )

        hybrid_stats_label.text = (
            f'Фото: {last_run["photos"]}    '
            f'Адресов: {last_run["addresses"]}'
        )

    # ============================================================
    # ОСНОВНАЯ ОБРАБОТКА
    # ============================================================

    source_input = ui.input(
```

Всё остальное в `photo_processing.py` **оставляем как есть**.

---

### Что получим

На вкладке **«Обработка фото»**:

```text
РАСПОЗНАВАНИЕ СЦЕН

DINO v33                              ● ГОТОВ
Распознавание сцен

────────────────────────────────────────

Hybrid v12                            ● ГОТОВ

Последний запуск: 20260818_115048
Фото: 526    Адресов: 18
```

Ниже останется существующая форма:

```text
ФОТООТЧЁТ

Источник фотографий
[...]

Результат
[...]

DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B

[ ▶ ЗАПУСТИТЬ ОБРАБОТКУ ]
```

Но здесь я предлагаю **ещё одну маленькую правку**: строку

```text
DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B
```

лучше заменить на:

```text
DINO v33 → Hybrid v12 → сортировка
```

Потому что Qwen теперь относится к отдельной вкладке.

Командой:

```bash
sed -i \
's/DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B/DINO v33 → Hybrid v12 → сортировка/' \
app/web/components/technical_modules/photo_processing.py
```

После этого перезапусти **не вручную второй экземпляр**, а существующий systemd-сервис:

```bash
sudo systemctl restart lora
```

И проверить:

```bash
sudo systemctl status lora --no-pager
```

Затем открываем `:8081`.

**Важно:** Qwen уже не надо запускать отдельно — существующая цепочка `Hybrid → qwen4b_output_v01.py` остаётся нетронутой.

---

### 👤 **User** — 2026-08-18 13:07:20

давай исправления в файле командой

---

### 🤖 **Assistant** — 2026-08-18 13:07:20

Да. Давай одной командой полностью внесём изменения в `photo_processing.py`, без ручного редактирования.

Сначала резервная копия, затем Python-скрипт аккуратно вставит блоки:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/technical_modules/photo_processing.py \
   app/web/components/technical_modules/photo_processing.py.bak && \
python - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/photo_processing.py")
text = p.read_text(encoding="utf-8")

# ------------------------------------------------------------
# 1. Добавляем DAILY_OUTPUT_ROOT и функцию поиска последнего запуска
# ------------------------------------------------------------

old = '''DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
'''

new = '''DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
DAILY_OUTPUT_ROOT = PROJECT / "data" / "output" / "daily"

def get_last_hybrid_run():
    """
    Возвращает информацию о последнем запуске Hybrid.
    """

    if not DAILY_OUTPUT_ROOT.exists():
        return None

    runs = [
        p for p in DAILY_OUTPUT_ROOT.iterdir()
        if p.is_dir()
    ]

    if not runs:
        return None

    result_dir = max(
        runs,
        key=lambda p: p.stat().st_mtime,
    )

    addresses = [
        p for p in result_dir.iterdir()
        if p.is_dir()
    ]

    photos = sum(
        1
        for address_dir in addresses
        for photo in address_dir.iterdir()
        if photo.is_file()
        and photo.suffix.lower() in {
            ".jpg",
            ".jpeg",
            ".png",
        }
    )

    return {
        "name": result_dir.name,
        "path": result_dir,
        "photos": photos,
        "addresses": len(addresses),
    }
'''

if old not in text:
    raise SystemExit("ERROR: DAILY_SCRIPT block not found")

text = text.replace(old, new, 1)

# ------------------------------------------------------------
# 2. Добавляем статусный блок перед Source input
# ------------------------------------------------------------

old = '''def build_photo_processing():

    source_input = ui.input(
'''

new = '''def build_photo_processing():

    # ============================================================
    # DINO v33 / HYBRID v12 STATUS
    # ============================================================

    with ui.card().classes("w-full"):

        ui.label(
            "РАСПОЗНАВАНИЕ СЦЕН"
        ).classes(
            "text-lg font-bold"
        )

        ui.separator().classes("my-2")

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            ui.label(
                "DINO v33"
            ).classes(
                "text-base font-medium"
            )

            ui.label(
                "● ГОТОВ"
            ).classes(
                "text-sm"
            )

        ui.label(
            "Распознавание сцен"
        ).classes(
            "text-sm text-grey-7"
        )

        ui.separator().classes("my-2")

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            ui.label(
                "Hybrid v12"
            ).classes(
                "text-base font-medium"
            )

            hybrid_status = ui.label(
                "● ГОТОВ"
            ).classes(
                "text-sm"
            )

        hybrid_run_label = ui.label(
            "Последний запуск: —"
        ).classes(
            "text-sm"
        )

        hybrid_stats_label = ui.label(
            "Фото: 0    Адресов: 0"
        ).classes(
            "text-sm"
        )

    last_run = get_last_hybrid_run()

    if last_run:

        hybrid_run_label.text = (
            f'Последний запуск: {last_run["name"]}'
        )

        hybrid_stats_label.text = (
            f'Фото: {last_run["photos"]}    '
            f'Адресов: {last_run["addresses"]}'
        )

    source_input = ui.input(
'''

if old not in text:
    raise SystemExit("ERROR: build_photo_processing block not found")

text = text.replace(old, new, 1)

# ------------------------------------------------------------
# 3. Убираем Qwen из описания основной обработки
# ------------------------------------------------------------

old = "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
new = "DINO v33 → Hybrid v12 → сортировка"

if old in text:
    text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")

print("OK: photo_processing.py updated")
print("Backup: photo_processing.py.bak")
PY
```

После этого сразу проверим синтаксис:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/photo_processing.py \
app/web/components/technical_modules/qwen.py
```

Если получишь:

```text
OK
```

перезапускаем сервис:

```bash
sudo systemctl restart lora && \
sudo systemctl status lora --no-pager
```

После открытия UI на вкладке **«Обработка фото»** должны появиться **DINO v33 / Hybrid v12**, а на вкладке **«Qwen»** — статистика Qwen из `summary.json`.

---

### 👤 **User** — 2026-08-18 13:07:41

PYint("Backup: photo_processing.py.bak")а"→ Qwen3-VL 4B"------found")
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:07:42

Да, здесь просто ошибка: в команде был вызван `python`, а на сервере нужен `python3` либо `uv run python`.

Для нашего проекта лучше использовать **`uv run python`**, чтобы гарантированно работать в `.venv`.

Дай сейчас эту команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp app/web/components/technical_modules/photo_processing.py \
   app/web/components/technical_modules/photo_processing.py.bak

uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/photo_processing.py")
s = p.read_text(encoding="utf-8")

# Здесь пока только создаём резервную копию и проверяем файл.
print("Backup: photo_processing.py.bak")
print("File:", p)
print("Lines:", len(s.splitlines()))
PY
```

**Пока ничего в `photo_processing.py` не меняем.**

После этого пришли вывод. Затем дам **одну готовую команду**, которая разделит отображение на:

- **ОБРАБОТКА**
  - DINO v33
  - Hybrid v12
  - последний запуск
  - фото
  - адреса
  - статус

- **QWEN**
  - Qwen3-VL 4B
  - обработано
  - OK
  - ошибки
  - адреса
  - среднее время
  - средняя уверенность

То есть логику запуска не трогаем — меняем пока только UI-разделение.

---

### 👤 **User** — 2026-08-18 13:08:17

if not candidates:
PY  )   refresh,f'Ошибка: {data["error"]}'"]}'лючены следующим этапом"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -n -E \
'DINO|Hybrid|ГОТОВ|Последний запуск|Фото:|Адресов:' \
app/web/components/technical_modules/photo_processing.py
79:            f"Запуск Hybrid v12... "
134:                    f"✗ Hybrid v12: ошибка ({returncode})"
163:                    "⚠ Hybrid завершён, "
168:                    "Hybrid завершён, "
181:                "✓ Hybrid v12: сортировка завершена"
199:                    "✓ Hybrid завершён → Qwen script не найден"
210:            # Имя папки Hybrid запуска:
276:                        "✗ Hybrid v12: ✓  "
281:                        "Hybrid завершён успешно, "
290:                    "✓ Hybrid v12 + Qwen3-VL 4B: готово"
299:                    "Hybrid v12 + Qwen3-VL 4B.",
307:                    "✗ Hybrid: ✓  "
384:            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cp app/web/components/technical_modules/photo_processing.py \
   app/web/components/technical_modules/photo_processing.py.bak
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/technical_modules/photo_processing.py \
   app/web/components/technical_modules/photo_processing.py.bak && \
python - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/photo_processing.py")
text = p.read_text(encoding="utf-8")

# ------------------------------------------------------------
# 1. Добавляем DAILY_OUTPUT_ROOT и функцию поиска последнего запуска
# ------------------------------------------------------------

old = '''DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
'''

new = '''DAILY_SCRIPT = PROJECT / "scripts" / "run_daily_hybrid_v12.sh"
DAILY_OUTPUT_ROOT = PROJECT / "data" / "output" / "daily"

def get_last_hybrid_run():
    """
    Возвращает информацию о последнем запуске Hybrid.
    """

    if not DAILY_OUTPUT_ROOT.exists():
        return None

    runs = [
        p for p in DAILY_OUTPUT_ROOT.iterdir()
        if p.is_dir()
    ]

    if not runs:
        return None

    result_dir = max(
        runs,
PYint("Backup: photo_processing.py.bak")а"→ Qwen3-VL 4B"------found")
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cp app/web/components/technical_modules/photo_processing.py \
   app/web/components/technical_modules/photo_processing.py.bak

uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/photo_processing.py")
s = p.read_text(encoding="utf-8")

# Здесь пока только создаём резервную копию и проверяем файл.
print("Backup: photo_processing.py.bak")
print("File:", p)
print("Lines:", len(s.splitlines()))
PY
Backup: photo_processing.py.bak
File: app/web/components/technical_modules/photo_processing.py
Lines: 404
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cp app/web/components/technical_modules/photo_processing.py \
   app/web/components/technical_modules/photo_processing.py.bak

uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/photo_processing.py")
s = p.read_text(encoding="utf-8")

# Здесь пока только создаём резервную копию и проверяем файл.
print("Backup: photo_processing.py.bak")
print("File:", p)
print("Lines:", len(s.splitlines()))
PY
Backup: photo_processing.py.bak
File: app/web/components/technical_modules/photo_processing.py
Lines: 404
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:08:17

Отлично. Бэкап есть, исходный `photo_processing.py` пока не изменён.

Теперь давай сначала **точно посмотрим верхнюю часть файла**, чтобы не гадать по структуре и дать одну безопасную команду изменения.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,430p' app/web/components/technical_modules/photo_processing.py
```

Пришли вывод. После этого я дам готовую команду, которая разделит:

**ОБРАБОТКА**
- DINO v33
- Hybrid v12
- последний запуск
- 526 фото
- 18 адресов

и отдельно вкладку:

**QWEN**
- Qwen3-VL 4B
- обработано
- OK
- ошибки
- адреса
- среднее время
- средняя уверенность

При этом **сам запуск DINO/Hybrid/Qwen не трогаем**.

---

### 👤 **User** — 2026-08-18 13:08:43

# Здесь пока только создаём резервную копию и проверяем файл.
print("Backup: photo_processing.py.bak")
print("File:", p)
print("Lines:", len(s.splitlines()))
PY
Backup: photo_processing.py.bak
File: app/web/components/technical_modules/photo_processing.py
Lines: 404
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,430p' app/web/components/technical_modules/photo_processing.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:08:43

Да. Теперь структура понятна.

**Важный момент:** `photo_processing.py` сейчас отвечает именно за запуск всей цепочки. Поэтому его **не надо переписывать целиком**. Для нашей задачи правильнее вынести отображение статусов в отдельные технические модули:

- вкладка **«Обработка»** → DINO v33 + Hybrid v12;
- вкладка **«Qwen»** → Qwen3-VL 4B;
- текущий запуск при этом остаётся прежним.

Сначала сделаем безопасный шаг: **найдём, где создаются вкладки технических модулей**, чтобы вставить туда Qwen отдельно.

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -R -n -E \
'build_photo_processing|build_last_run|build_data|technical_modules|ui.tabs|ui.tab' \
app/web \
--include="*.py" \
--exclude-dir="__pycache__" \
| head -150
```

Пришли вывод.

После этого дам **одну команду**, которая создаст нужную структуру вкладок, не затрагивая рабочий DINO/Hybrid/Qwen pipeline.

---

### 👤 **User** — 2026-08-18 13:09:05

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -R -n -E \
'build_photo_processing|build_last_run|build_data|technical_modules|ui.tabs|ui.tab' \
app/web \
--include="*.py" \
--exclude-dir="__pycache__" \
| head -150
app/web/components/technical_modules/photo_processing.py:12:def build_photo_processing():
app/web/components/technical_modules/data.py:179:def build_data():
app/web/components/technical_modules/last_run.py:4:def build_last_run():
app/web/components/technical.py:3:from app.web.components.technical_modules.photo_processing import (
app/web/components/technical.py:4:    build_photo_processing,
app/web/components/technical.py:6:from app.web.components.technical_modules.last_run import (
app/web/components/technical.py:7:    build_last_run,
app/web/components/technical.py:9:from app.web.components.technical_modules.automation import (
app/web/components/technical.py:12:from app.web.components.technical_modules.qwen import (
app/web/components/technical.py:15:from app.web.components.technical_modules.data import (
app/web/components/technical.py:16:    build_data,
app/web/components/technical.py:18:from app.web.components.technical_modules.system import (
app/web/components/technical.py:21:from app.web.components.technical_modules.fingerprints import (
app/web/components/technical.py:24:from app.web.components.technical_modules.users import build_users
app/web/components/technical.py:152:            with ui.tabs().classes(
app/web/components/technical.py:156:                ui.tab(
app/web/components/technical.py:162:                ui.tab(
app/web/components/technical.py:168:                ui.tab(
app/web/components/technical.py:174:                ui.tab(
app/web/components/technical.py:180:                ui.tab(
app/web/components/technical.py:186:                ui.tab(
app/web/components/technical.py:192:                ui.tab(
app/web/components/technical.py:198:                ui.tab(
app/web/components/technical.py:214:                with ui.tab_panels(
app/web/components/technical.py:221:                    with ui.tab_panel("photo_processing"):
app/web/components/technical.py:222:                        build_photo_processing()
app/web/components/technical.py:224:                    with ui.tab_panel("last_run"):
app/web/components/technical.py:225:                        build_last_run()
app/web/components/technical.py:227:                    with ui.tab_panel("automation"):
app/web/components/technical.py:230:                    with ui.tab_panel("qwen"):
app/web/components/technical.py:233:                    with ui.tab_panel("data"):
app/web/components/technical.py:234:                        build_data()
app/web/components/technical.py:236:                    with ui.tab_panel("system"):
app/web/components/technical.py:239:                    with ui.tab_panel("fingerprints"):
app/web/components/technical.py:242:                    with ui.tab_panel("users"):
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:09:05

Отлично — **Qwen уже имеет отдельную вкладку** (`qwen`). Значит, структуру вкладок переделывать не нужно.

Проблема сейчас в другом: `photo_processing.py` показывает всю цепочку как одну операцию, а вкладка Qwen, судя по результату, не умеет читать `summary.json`.

Сначала посмотрим текущий `technical.py` и `qwen.py`. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== TECHNICAL ====="
sed -n '130,255p' app/web/components/technical.py

echo
echo "===== QWEN ====="
cat app/web/components/technical_modules/qwen.py
```

После этого сделаем именно то, что нужно:

### Вкладка «Обработка»
```text
DINO v33
Распознавание сцен
ГОТОВ

Hybrid v12
Последний запуск: 20260818_115048
ГОТОВ
Фото: 526
Адресов: 18
```

### Вкладка «Qwen»
```text
Qwen3-VL 4B
Анализ содержимого фотографий

Обработано: ...
OK: ...
Ошибок: ...
Адресов: ...
Среднее время: ... сек
Средняя уверенность: ...%
```

И главное — **Qwen будет брать реальные данные из `summary.json`**, а не показывать «Неверный формат / 0».

Пришли вывод этих двух файлов.

---

