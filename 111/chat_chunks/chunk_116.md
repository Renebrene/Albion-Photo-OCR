## СЕССИЯ: Продолжение разговора 1

**Создано:** 2026-08-18 12:11:53
**Обновлено:** 2026-08-19 17:07:58
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8421d7-3160-83ea-be54-4a2ad097babc](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8421d7-3160-83ea-be54-4a2ad097babc)

---

### 👤 **User** — 2026-08-18 13:11:20

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "===== TECHNICAL ====="
sed -n '130,255p' app/web/components/technical.py

echo
echo "===== QWEN ====="
cat app/web/components/technical_modules/qwen.py
===== TECHNICAL =====
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

===== QWEN =====
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:11:22

Да, теперь видно, в чём дело.

**Сами вкладки уже правильные.** Переделывать `technical.py` не нужно.

Нужно изменить только содержимое:

- `photo_processing.py` → показывает **DINO v33 + Hybrid v12**
- `qwen.py` → показывает **Qwen3-VL 4B**
- запуск Qwen из `photo_processing.py` пока оставляем, чтобы ничего не сломать.

Но у Qwen сейчас есть отдельная проблема: он получает `ОШИБКА ФОРМАТА`, хотя `summary.json` существует. Сначала проверим фактический JSON и сразу увидим причину.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== QWEN SUMMARY ====="
uv run python - <<'PY'
import json
from pathlib import Path

root = Path("data/metadata/qwen4b")

files = list(root.glob("*/summary.json")) + [root / "summary.json"]
files = [p for p in files if p.exists()]

print("Found:", len(files))

for p in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
    print()
    print("FILE:", p)

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        print("JSON: OK")
        print("model:", data.get("model"))
        print("files_in_run:", data.get("files_in_run"))
        print("results:", len(data.get("results", [])))
        print("first:", data.get("results", [])[:1])
    except Exception as e:
        print("JSON ERROR:", repr(e))
PY
```

### И ещё сразу проверим последний Hybrid

```bash
echo
echo "===== LAST HYBRID ====="

uv run python - <<'PY'
from pathlib import Path

root = Path("data/output/daily")

runs = sorted(
    [p for p in root.iterdir() if p.is_dir()],
    key=lambda p: p.name,
    reverse=True,
)

if not runs:
    print("Нет запусков")
else:
    p = runs[0]

    photos = [
        x for x in p.rglob("*")
        if x.is_file()
        and x.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]

    addresses = {
        x.parent.name
        for x in photos
    }

    print("Последний запуск:", p.name)
    print("Фото:", len(photos))
    print("Адресов:", len(addresses))
    print("Адреса:", ", ".join(sorted(addresses)))
PY
```

После этого уже дам **одну финальную команду изменения**, чтобы на вкладке **«Обработка фото»** было визуально:

```text
ОБРАБОТКА

DINO v33
Распознавание сцен
● ГОТОВ

Hybrid v12
Последний запуск: 20260818_115048
● ГОТОВ
Фото: 526
Адресов: 18
```

а на **«Qwen»**:

```text
Qwen3-VL 4B
Анализ содержимого фотографий

● ГОТОВ
Обработано: ...
OK: ...
Ошибок: ...
Адресов: ...
Среднее время: ... сек
Средняя уверенность: ... %
```

И **никакой логики распознавания DINO v33 / Hybrid v12 менять не будем**.

---

### 👤 **User** — 2026-08-18 13:11:39

echo "===== QWEN SUMMARY ====="
uv run python - <<'PY'
import json
from pathlib import Path

root = Path("data/metadata/qwen4b")

files = list(root.glob("*/summary.json")) + [root / "summary.json"]
files = [p for p in files if p.exists()]

print("Found:", len(files))

for p in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
    print()
    print("FILE:", p)

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        print("JSON: OK")
        print("model:", data.get("model"))
        print("files_in_run:", data.get("files_in_run"))
        print("results:", len(data.get("results", [])))
        print("first:", data.get("results", [])[:1])
    except Exception as e:
        print("JSON ERROR:", repr(e))
PY
===== QWEN SUMMARY =====
Found: 2

FILE: data/metadata/qwen4b/20260816_230042/summary.json
JSON: OK
model: qwen3-vl:4b-instruct
files_in_run: 1
results: 1
first: [{'file': 'Комарова13_01.JPG', 'address': '78_v33', 'status': 'ok', 'time_sec': 21.0, 'client': 'ОЗОН', 'brand': 'Ozon fresh', 'category': 'онлайн-магазин', 'confidence': 95}]

FILE: data/metadata/qwen4b/summary.json
JSON: OK
model: qwen3-vl:4b-instruct
files_in_run: 100
results: 100
first: [{'file': 'Комарова13_01.JPG', 'address': '78_v33', 'status': 'ok', 'time_sec': 6.8, 'client': 'ОЗОН', 'brand': 'Ozon fresh', 'category': 'онлайн-магазин', 'confidence': 95}]
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:11:42

Да. Сейчас у нас причина ясна:

- **DINO v33 + Hybrid v12** должны жить только во вкладке **«Обработка фото»**.
- **Qwen3-VL 4B** — отдельно во вкладке **«Qwen»**.
- Сейчас `photo_processing.py` после Hybrid **автоматически запускает Qwen** — этот блок нужно убрать.
- `qwen.py` уже умеет читать `data/metadata/qwen4b/summary.json`, и файл сейчас корректный: **100 записей, JSON OK**.
- Поэтому Qwen больше не должен запускаться как часть Hybrid.

Сделаем аккуратно, с backup. Выполни **одну команду**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/technical_modules/photo_processing.py \
   app/web/components/technical_modules/photo_processing.py.bak2 && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/photo_processing.py")
s = p.read_text(encoding="utf-8")

start_marker = '''            # ====================================================
            # QWEN3-VL 4B
            # ====================================================
'''

end_marker = '''        except Exception as e:

            status_label.text = (
                "✗ Ошибка запуска"
            )
'''

start = s.find(start_marker)
end = s.find(end_marker)

if start == -1:
    raise SystemExit("ОШИБКА: блок QWEN3-VL 4B не найден")

if end == -1:
    raise SystemExit("ОШИБКА: конец блока run_pipeline не найден")

# Удаляем весь автоматический запуск Qwen.
s = s[:start] + end_marker + s[end + len(end_marker):]

# Меняем финальную подпись процесса.
s = s.replace(
    '"DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"',
    '"DINO v33 → Hybrid v12 → сортировка"'
)

# Финальное сообщение после Hybrid.
s = s.replace(
    '"✓ Hybrid v12: сортировка завершена"',
    '"✓ DINO v33 + Hybrid v12: готово"'
)

s = s.replace(
    'f"Сортировка завершена: {result_dir}"',
    'f"DINO + Hybrid завершены: {result_dir}"'
)

p.write_text(s, encoding="utf-8")

print("OK: photo_processing.py исправлен")
print("Backup: photo_processing.py.bak2")
PY
```

Потом сразу проверяем, что **Qwen-блока больше нет**, а Hybrid остался:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -E \
'QWEN3|Qwen3|qwen_script|qwen_process|DINO|Hybrid|сортировка' \
app/web/components/technical_modules/photo_processing.py
```

Ожидаем примерно:

```text
79: Запуск Hybrid v12...
...
✓ DINO v33 + Hybrid v12: готово
...
DINO v33 → Hybrid v12 → сортировка
```

И **не должно быть**:

```text
qwen_script
qwen_process
QWEN3-VL 4B
```

После этого перезапустим `lora.service`, а затем отдельно приведём вкладку **Qwen** к нормальному отображению последнего `summary.json` и добавим туда кнопку запуска Qwen.

---

### 👤 **User** — 2026-08-18 13:11:59

d': 'Ozon fresh', 'category': 'онлайн-магазин', 'confidence': 95}]
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "===== LAST HYBRID ====="

uv run python - <<'PY'
from pathlib import Path

root = Path("data/output/daily")

runs = sorted(
    [p for p in root.iterdir() if p.is_dir()],
    key=lambda p: p.name,
    reverse=True,
)

if not runs:
    print("Нет запусков")
else:
    p = runs[0]

    photos = [
        x for x in p.rglob("*")
        if x.is_file()
        and x.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]

    addresses = {
        x.parent.name
        for x in photos
    }

    print("Последний запуск:", p.name)
    print("Фото:", len(photos))
    print("Адресов:", len(addresses))
    print("Адреса:", ", ".join(sorted(addresses)))
PY

===== LAST HYBRID =====
Последний запуск: 20260818_115048
Фото: 526
Адресов: 18
Адреса: 78_v33, 79_v33, 80_v33, 81_v33, 82_v33, 83_v33, 84_v33, 85_v33, 86_v33, 87_v33, 88_v33, 89_v33, 90_v33, 91_v33, 92_v33, 93_v33, 94_v33, 95_v33
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:11:59

Отлично. **Hybrid фактически отработал корректно**:

- Последний запуск: `20260818_115048`
- Фото: **526**
- Адресов: **18**
- Диапазон: **78_v33 → 95_v33**
- Qwen отдельно имеет корректный `summary.json` на **100 фото**.

Теперь логично проверить, что наше изменение `photo_processing.py` действительно отделило Qwen от обработки.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -E \
'QWEN3|Qwen3|qwen_script|qwen_process|DINO|Hybrid|сортировка' \
app/web/components/technical_modules/photo_processing.py
```

Пришли вывод. Затем сделаем **ровно две вкладки по назначению**:

**Обработка фото**
> DINO v33 → Hybrid v12 → сортировка  
> Последний запуск / 526 фото / 18 адресов

**Qwen**
> Qwen3-VL 4B → отдельная статистика → запуск/обработка Qwen

При этом существующий `summary.json` Qwen уже можно использовать как источник реального статуса.

---

### 👤 **User** — 2026-08-18 13:12:32

квен должен запускать автоматически после гибрид

---

### 🤖 **Assistant** — 2026-08-18 13:12:33

Да, тогда **автоматический запуск Qwen после Hybrid оставляем**. Я выше неверно понял задачу.

Правильная архитектура:

### Вкладка «Обработка фото»
Показывает общий процесс:

**DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B**

И кнопка **«ЗАПУСТИТЬ ОБРАБОТКУ»** запускает всё последовательно:

1. DINO v33
2. Hybrid v12
3. сортировка по адресам
4. автоматически запускается Qwen3-VL 4B
5. после завершения оба этапа имеют статус **ГОТОВ**

### Вкладка «Qwen»
Отдельно показывает именно состояние Qwen:

- модель `qwen3-vl:4b-instruct`
- обработано
- OK
- ошибок
- адресов
- среднее время
- средняя уверенность
- источник `summary.json`

То есть **разделяем отображение, но не разрываем pipeline**.

И текущий `photo_processing.py` **не надо откатывать** — в нём автоматический Qwen как раз уже реализован.

Сейчас нам нужно исправить только **статусы/отображение**, чтобы после запуска Hybrid/Qwen данные правильно попадали в соответствующие вкладки.

Сначала вернёмся к исходному файлу из backup, если предыдущая команда уже успела удалить Qwen-блок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/technical_modules/photo_processing.py.bak2 \
   app/web/components/technical_modules/photo_processing.py
```

После этого проверим:

```bash
grep -n -E \
'QWEN3|Qwen3|qwen_script|qwen_process|DINO|Hybrid|сортировка' \
app/web/components/technical_modules/photo_processing.py
```

**Qwen должен присутствовать.**

---

### 👤 **User** — 2026-08-18 13:13:06

Адреса: 78_v33, 79_v33, 80_v33, 81_v33, 82_v33, 83_v33, 84_v33, 85_v33, 86_v33, 87_v33, 88_v33, 89_v33, 90_v33, 91_v33, 92_v33, 93_v33, 94_v33, 95_v33
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/technical_modules/photo_processing.py.bak2 \
   app/web/components/technical_modules/photo_processing.py
cp: cannot stat 'app/web/components/technical_modules/photo_processing.py.bak2': No such file or directory
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:13:06

Да, `bak2` не создался — предыдущая команда с `python` не выполнилась, поэтому откатывать нечего.

И главное: **текущий `photo_processing.py` из твоего последнего вывода уже содержит правильный автоматический запуск Qwen**. Его не трогаем.

Проверим только наличие backup и текущего Qwen-блока:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "===== BACKUPS =====" && \
ls -lh app/web/components/technical_modules/photo_processing.py* && \
echo && \
echo "===== QWEN IN PIPELINE =====" && \
grep -n -E \
'QWEN3|Qwen3|qwen_script|qwen_process|Qwen3-VL 4B' \
app/web/components/technical_modules/photo_processing.py
```

**Ничего пока не меняй.** Пришли вывод этой команды — по нему точно определим, какая версия `photo_processing.py` сейчас стоит.

---

### 👤 **User** — 2026-08-18 13:13:21

-rw-rw-r-- 1 alexice alexice  11K Aug 16 23:11 app/web/components/technical_modules/photo_processing.py
-rw-rw-r-- 1 alexice alexice  11K Aug 18 13:08 app/web/components/technical_modules/photo_processing.py.bak
-rw-rw-r-- 1 alexice alexice 1.7K Aug 16 22:48 app/web/components/technical_modules/photo_processing.py.bak_before_hybrid_button
-rw-rw-r-- 1 alexice alexice 7.1K Aug 16 23:02 app/web/components/technical_modules/photo_processing.py.bak_before_path_fix
-rw-rw-r-- 1 alexice alexice 7.5K Aug 16 23:11 app/web/components/technical_modules/photo_processing.py.bak_before_qwen_integration
-rw-rw-r-- 1 alexice alexice 7.2K Aug 16 22:54 app/web/components/technical_modules/photo_processing.py.bak_button_error_debug
-rw-rw-r-- 1 alexice alexice 7.2K Aug 16 22:58 app/web/components/technical_modules/photo_processing.py.broken_backup

===== QWEN IN PIPELINE =====
191:            # QWEN3-VL 4B
194:            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"
196:            if not qwen_script.exists():
203:                    f"Не найден Qwen script: {qwen_script}",
228:                "▶ Qwen3-VL 4B: выполняется..."
233:                "Запускается Qwen3-VL 4B.",
240:                qwen_process = await asyncio.create_subprocess_exec(
242:                    str(qwen_script),
256:                    line = await qwen_process.stdout.readline()
271:                qwen_returncode = await qwen_process.wait()
277:                        "Qwen3-VL 4B: ошибка"
282:                        "но Qwen3-VL 4B завершился с ошибкой.",
290:                    "✓ Hybrid v12 + Qwen3-VL 4B: готово"
299:                    "Hybrid v12 + Qwen3-VL 4B.",
308:                    "Qwen3-VL 4B: ошибка запуска"
384:            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:13:22

Отлично. Теперь всё однозначно.

**Текущий `photo_processing.py` правильный:** Qwen автоматически запускается после Hybrid. Ничего откатывать не нужно.

Причём у нас есть хороший backup:

```text
photo_processing.py.bak
```

от `13:08`, а также старые версии.

Теперь задача именно такая:

### 1. Обработка фото

Оставляем pipeline:

```text
DINO v33
    ↓
Hybrid v12
    ↓
сортировка
    ↓
Qwen3-VL 4B
```

То есть кнопка **«ЗАПУСТИТЬ ОБРАБОТКУ»** запускает всё автоматически.

### 2. Вкладка Qwen

Qwen не запускаем повторно из вкладки. Она является **монитором Qwen**, который автоматически запускается из обработки.

И здесь сейчас есть проблема: `qwen.py` ищет:

```text
data/metadata/qwen4b/summary.json
```

или:

```text
data/metadata/qwen4b/<run>/summary.json
```

А текущий запуск из `photo_processing.py` создаёт:

```text
data/metadata/qwen4b/<run_name>/summary.json
```

Это хорошо.

Но твой `summary.json` в корне:

```text
data/metadata/qwen4b/summary.json
```

содержит старые **100 фото**, поэтому вкладка Qwen может показывать не тот запуск, который только что прошёл.

### Что предлагаю сделать сейчас

**Не трогать pipeline.** Исправить только `qwen.py`, чтобы вкладка Qwen:

- брала **последний запуск Qwen**;
- показывала реальные `processed / OK / errors`;
- показывала количество адресов;
- показывала среднее время;
- показывала среднюю уверенность;
- показывала имя запуска;
- автоматически обновлялась;
- не путалась со старым `data/metadata/qwen4b/summary.json`.

Для начала покажи текущие даты и содержимое обоих summary:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "===== SUMMARY FILES =====" && \
ls -lh --full-time \
data/metadata/qwen4b/summary.json \
data/metadata/qwen4b/*/summary.json 2>/dev/null | tail -20
```

После этого дам **одну безопасную команду для исправления `qwen.py`**, без изменения самого DINO → Hybrid → Qwen pipeline.

---

### 👤 **User** — 2026-08-18 13:14:06

data/metadata/qwen4b/summary.json \
data/metadata/qwen4b/*/summary.json 2>/dev/null | tail -20
===== SUMMARY FILES =====
-rw-rw-r-- 1 alexice alexice 557 2026-08-16 23:09:57.129531629 +0300 data/metadata/qwen4b/20260816_230042/summary.json
-rw-rw-r-- 1 alexice alexice 26K 2026-08-16 17:28:35.912538291 +0300 data/metadata/qwen4b/summary.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:14:07

Вот теперь видно главное: **последний Qwen реально запускался 16 августа**, а сегодняшний Hybrid `20260818_115048` ещё не имеет отдельного Qwen `summary.json`.

То есть:

- Hybrid: **18.08.2026 11:50:48**, 526 фото, 18 адресов — готов.
- Qwen: последний сохранённый запуск **16.08.2026 23:09:57**, 1 фото.
- Корневой `summary.json` от **16.08 17:28**, 100 фото — ещё более старый.

Поэтому вкладка Qwen сейчас совершенно закономерно может показывать старые данные.

### Но есть важный момент

Сам pipeline сейчас **не запущен после сегодняшнего Hybrid**. То есть мы пока не должны менять `qwen.py` так, чтобы он показывал сегодняшние 526 — их Qwen ещё не обработал.

Правильный следующий шаг — **сначала проверить, что Qwen действительно запускается автоматически из текущего `photo_processing.py`**, и только потом заниматься красивым статусом вкладки.

Сделаем проверку без запуска 526 фото:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '185,315p' app/web/components/technical_modules/photo_processing.py
```

Это покажет именно участок:

```text
Hybrid завершён
        ↓
определение result_dir
        ↓
qwen4b_output_v01.py
        ↓
summary.json
```

Пришли этот вывод. **Сам pipeline пока не меняем.**

---

### 👤 **User** — 2026-08-18 13:14:38

-rw-rw-r-- 1 alexice alexice 26K 2026-08-16 17:28:35.912538291 +0300 data/metadata/qwen4b/summary.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '185,315p' app/web/components/technical_modules/photo_processing.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:14:38

Да. **Цепочка сейчас правильная и её не меняем.**

Текущая логика:

```text
Кнопка обработки
      ↓
DINO v33
      ↓
Hybrid v12
      ↓
data/output/daily/20260818_115048
      ↓
Qwen3-VL 4B
      ↓
data/metadata/qwen4b/20260818_115048/
      ↓
summary.json
```

Причём Qwen запускается именно из:

```text
.venv/bin/python
```

и получает правильные параметры:

```text
--input  <результат Hybrid>
--output data/metadata/qwen4b/<имя запуска>
```

### Что сейчас надо исправить

Только интерфейс.

**Обработка фото** должна показывать состояние всей цепочки:

> DINO v33 → Hybrid v12 → Qwen3-VL 4B

А вкладка **Qwen** должна показывать состояние последнего Qwen-запуска.

И здесь есть небольшая проблема: `qwen.py` сейчас считает **`skipped` как `processed`**, потому что делает:

```python
"processed": len(results)
```

Кроме того, если Qwen ещё не запускался после последнего Hybrid, нельзя показывать старые данные как будто они относятся к сегодняшней обработке.

### Предлагаю следующий шаг

Сделаем `qwen.py` таким образом, чтобы он находил **последний Qwen-run по имени папки**, например:

```text
20260818_115048
```

и показывал:

```text
Qwen3-VL 4B

Последний запуск: 20260818_115048

Статус: ГОТОВ
Обработано: 526
OK: ...
Ошибок: ...
Адресов: 18
Среднее время: ... сек
Средняя уверенность: ...%
```

А если Qwen ещё не запускался после Hybrid — будет честно:

```text
НЕТ ДАННЫХ
Последний запуск Qwen: 20260816_230042
```

**Сам автоматический запуск Qwen не трогаем.**

Если готов — следующим сообщением дам одну команду `uv run python <<'PY'`, которая аккуратно заменит только `qwen.py`, с backup перед изменением.

---

### 👤 **User** — 2026-08-18 13:14:48

давай

---

### 🤖 **Assistant** — 2026-08-18 13:14:53

Да. Сделаем аккуратно: сначала backup, затем полностью заменим только `qwen.py`. Автоматический запуск Qwen в `photo_processing.py` **не трогаем**.

Команда:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/technical_modules/qwen.py \
   app/web/components/technical_modules/qwen.py.bak && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/qwen.py")

text = r'''import json
from pathlib import Path

from nicegui import ui

PROJECT = Path.home() / "projects" / "scene_fingerprint_mvp_v02"
QWEN_ROOT = PROJECT / "data" / "metadata" / "qwen4b"

def _find_latest_run():
    """
    Ищет последний отдельный запуск Qwen.

    Используется только:
        data/metadata/qwen4b/<YYYYMMDD_HHMMSS>/summary.json

    Старый корневой summary.json намеренно не используется,
    чтобы он не маскировал более свежий запуск.
    """

    if not QWEN_ROOT.exists():
        return None

    candidates = []

    for p in QWEN_ROOT.iterdir():

        if not p.is_dir():
            continue

        summary = p / "summary.json"

        if summary.is_file():
            candidates.append(summary)

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda p: p.parent.name,
    )

def _load_qwen_status():

    summary_path = _find_latest_run()

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
            "run": None,
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

        skipped_results = [
            x for x in results
            if x.get("status") == "skipped"
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

        times = []

        for x in ok_results:
            value = x.get("time_sec")

            if value is not None:
                try:
                    times.append(float(value))
                except (TypeError, ValueError):
                    pass

        confidences = []

        for x in ok_results:
            value = x.get("confidence")

            if value not in (None, ""):
                try:
                    confidences.append(float(value))
                except (TypeError, ValueError):
                    pass

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
            "processed": len(ok_results),
            "ok": len(ok_results),
            "skipped": len(skipped_results),
            "errors": len(error_results),
            "addresses": len(addresses),
            "avg_time": avg_time,
            "avg_confidence": avg_confidence,
            "model": summary.get(
                "model",
                "qwen3-vl:4b-instruct",
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

        with ui.row().classes("gap-2"):

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

    refresh()

    ui.timer(
        5.0,
        refresh,
    )
'''

p.write_text(text, encoding="utf-8")

print("OK: qwen.py обновлён")
print("Backup: qwen.py.bak")
print("Lines:", len(text.splitlines()))
PY
```

После этого **ничего не запускаем на 526 фото**. Сначала проверяем сам файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/qwen.py && \
echo "PYTHON SYNTAX: OK"
```

И затем проверяем, что новый статус действительно видит последний отдельный Qwen-запуск:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.components.technical_modules.qwen import _load_qwen_status

print(_load_qwen_status())
PY
```

Сейчас ожидаемо должен обнаружиться старый:

```text
20260816_230042
```

с **1 OK**, потому что сегодняшний Qwen ещё не запускался. После следующего запуска полного pipeline вкладка автоматически начнёт видеть:

```text
20260818_115048
```

и уже его статистику.

---

### 👤 **User** — 2026-08-18 13:15:34

Backup: qwen.py.bak
Lines: 307
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/qwen.py && \
echo "PYTHON SYNTAX: OK"
PYTHON SYNTAX: OK
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.components.technical_modules.qwen import _load_qwen_status

print(_load_qwen_status())
PY
{'state': 'ГОТОВ', 'processed': 1, 'ok': 1, 'skipped': 0, 'errors': 0, 'addresses': 1, 'avg_time': 21.0, 'avg_confidence': 95.0, 'model': 'qwen3-vl:4b-instruct', 'run': '20260816_230042', 'summary': PosixPath('/home/alexice/projects/scene_fingerprint_mvp_v02/data/metadata/qwen4b/20260816_230042/summary.json')}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:15:35

Отлично. **`qwen.py` работает правильно.**

Сейчас он честно показывает последний отдельный запуск Qwen:

- **Статус:** ГОТОВ
- **Запуск:** `20260816_230042`
- **Обработано:** 1
- **OK:** 1
- **Ошибок:** 0
- **Адресов:** 1
- **Среднее время:** 21.0 сек
- **Средняя уверенность:** 95%
- **Модель:** `qwen3-vl:4b-instruct`

И главное — **старый корневой `data/metadata/qwen4b/summary.json` больше не мешает**, потому что новый код его намеренно игнорирует.

### Теперь структура правильная

**Обработка фото**

```text
DINO v33
   ↓
Hybrid v12
   ↓
сортировка
   ↓
Qwen3-VL 4B
```

**Qwen**

```text
последний Qwen-run
        ↓
summary.json
        ↓
статистика Qwen
```

Осталось перезапустить сервис, чтобы NiceGUI подхватил новый `qwen.py`:

```bash
sudo systemctl restart lora.service
```

Потом:

```bash
sudo systemctl status lora.service --no-pager
```

И открыть:

```text
http://192.168.1.5:8081
```

Пока **не запускай обработку 526 фотографий**. Сначала посмотрим UI и убедимся, что вкладки выглядят правильно.

---

### 👤 **User** — 2026-08-18 13:17:52

СТАТУС ОБРАБОТЧИКОВ

---

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

статус обработчиков не разнесен

---

### 🤖 **Assistant** — 2026-08-18 13:17:52

> **Поиск компонентов статусного интерфейса**
>
>
> **Найдены компоненты статусного интерфейса**
>
> 
>
> Обработка заняла несколько секунд

Да. Сейчас проблема именно в **блоке «СТАТУС ОБРАБОТЧИКОВ»**, а не в `qwen.py`: Qwen уже отдельно отображается во вкладке, но верхний статусный блок, судя по всему, ещё собирает DINO + Hybrid + Qwen в одну логику.

Сначала найдём файл этого блока. Выполни **одну команду**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -R -n -E \
'СТАТУС ОБРАБОТЧИКОВ|Распознавание сцен|Анализ содержимого фотографий|Последний запуск:' \
app/web \
--include="*.py" \
--exclude-dir="__pycache__"
```

Пришли вывод. По нему дам **точную команду замены**, чтобы получить:

```text
СТАТУС ОБРАБОТЧИКОВ

DINO v33
Распознавание сцен
ГОТОВ

Hybrid v12
Последний запуск: 20260818_115048
ГОТОВ
Фото: 526
Адресов: 18

Qwen3-VL 4B
Анализ содержимого фотографий
ГОТОВ
Обработано: ...
OK: ...
Ошибок: ...
Адресов: ...
Среднее время: ...
Средняя уверенность: ...
```

И главное — **Qwen будет определяться по реальному `summary.json`, а не получать «Неверный формат» из-за старого root `summary.json`.**

---

### 👤 **User** — 2026-08-18 13:18:12

Aug 18 13:15:49 NEURO uv[129510]: [DAILY PHOTO ROOT] /home/alexice/projects/scene_fingerprint_mvp_v02/data/…8_115048
Aug 18 13:15:49 NEURO uv[129510]: [DAILY ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', …', '95']
Aug 18 13:15:49 NEURO uv[129510]: [PHOTO INDEX] addresses=18 photos=526
Hint: Some lines were ellipsized, use -l to show in full.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -R -n -E \
'СТАТУС ОБРАБОТЧИКОВ|Распознавание сцен|Анализ содержимого фотографий|Последний запуск:' \
app/web \
--include="*.py" \
--exclude-dir="__pycache__"
app/web/components/technical_modules/data.py:229:            "СТАТУС ОБРАБОТЧИКОВ"
app/web/components/technical_modules/data.py:253:                    "Распознавание сцен"
app/web/components/technical_modules/data.py:282:                    f"Последний запуск: {daily['run']}"
app/web/components/technical_modules/data.py:323:                    "Анализ содержимого фотографий"
app/web/components/technical_modules/qwen.py:183:                "Анализ содержимого фотографий"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:18:12

> **Вспоминаем**
>
>
> **Проверили статусы обработчиков и разделили модели Hybrid v12 и Qwen3-VL 4B**
>
> 
>
> Обработка заняла 5s

Отлично, нашли нужное место: **`data.py`**. Именно там сейчас формируется общий блок статусов, поэтому Qwen там ещё отображается как часть старой логики.

Давай сначала посмотрим точный код блока, а затем я дам одну команду замены без ручного редактирования.

На сервере выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '215,345p' app/web/components/technical_modules/data.py
```

Пришли вывод. После этого заменим **только блок «СТАТУС ОБРАБОТЧИКОВ»**, не трогая рабочую обработку DINO/Hybrid и отдельную вкладку Qwen.

---

### 👤 **User** — 2026-08-18 13:18:33

app/web/components/technical_modules/qwen.py:183:                "Анализ содержимого фотографий"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '215,345p' app/web/components/technical_modules/data.py

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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:18:35

Да, теперь всё ясно. В `data.py` Qwen уже вынесен отдельным блоком, но нам нужно проверить **как формируется переменная `qwen`** — именно там, скорее всего, возникает `Неверный формат`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,230p' app/web/components/technical_modules/data.py
```

И сразу после этого:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '345,390p' app/web/components/technical_modules/data.py
```

После этого я дам **одну готовую команду `uv run python - <<'PY'`**, которая:

- сохранит `.bak`;
- исправит только получение статуса Qwen;
- оставит DINO как есть;
- оставит Hybrid как есть;
- не затронет автоматический запуск Qwen после Hybrid;
- не затронет отдельную вкладку Qwen.

---

### 👤 **User** — 2026-08-18 13:18:53

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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,230p' app/web/components/technical_modules/data.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:18:54

Да, нашли причину.

`data.py` ожидает, что `summary.json` будет **списком**, а реальный Qwen `summary.json` имеет структуру:

```text
{
    "model": ...,
    "files_in_run": 100,
    "results": [...]
}
```

Поэтому и получается **«Неверный формат»**.

Причём у нас уже есть правильная логика в `qwen.py`. Лучше не дублировать её, а сделать `data.py` совместимым с фактическим форматом.

### 1. Исправляем `data.py`

Выполни целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/technical_modules/data.py \
   app/web/components/technical_modules/data.py.bak && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/data.py")
s = p.read_text(encoding="utf-8")

old = '''def qwen_stats():
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
'''

new = '''def qwen_stats():
    """
    Читает фактический формат Qwen summary.json.

    Формат:
    {
        "model": "...",
        "files_in_run": N,
        "elapsed_sec": ...,
        "results": [...]
    }

    Приоритет:
    1. summary.json в корне QWEN_ROOT
    2. самый свежий summary.json в подпапках запусков
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
        return {
            "status": "Нет данных",
            "photos": 0,
            "ok": 0,
            "errors": 0,
            "avg_time": 0,
            "avg_confidence": 0,
            "addresses": 0,
        }

    summary = max(
        candidates,
        key=lambda p: p.stat().st_mtime,
    )

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

    if not isinstance(data, dict):
        return {
            "status": "Неверный формат",
            "photos": 0,
            "ok": 0,
            "errors": 0,
            "avg_time": 0,
            "avg_confidence": 0,
            "addresses": 0,
        }

    results = data.get("results", [])

    if not isinstance(results, list):
        return {
            "status": "Неверный формат",
            "photos": 0,
            "ok": 0,
            "errors": 0,
            "avg_time": 0,
            "avg_confidence": 0,
            "addresses": 0,
        }

    total = len(results)

    ok = sum(
        1
        for row in results
        if isinstance(row, dict)
        and row.get("status") == "ok"
    )

    errors = sum(
        1
        for row in results
        if isinstance(row, dict)
        and row.get("status") == "error"
    )

    times = []

    for row in results:
        if not isinstance(row, dict):
            continue

        value = row.get("time_sec")

        if value is not None:
            try:
                times.append(float(value))
            except (TypeError, ValueError):
                pass

    confidences = []

    for row in results:
        if not isinstance(row, dict):
            continue

        value = row.get("confidence")

        if value not in (None, ""):
            try:
                confidences.append(float(value))
            except (TypeError, ValueError):
                pass

    addresses = {
        row.get("address")
        for row in results
        if isinstance(row, dict)
        and row.get("address")
    }

    return {
        "status": "ГОТОВ" if ok else "Нет данных",
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
'''

if old not in s:
    raise SystemExit("ERROR: старый блок qwen_stats() не найден")

p.write_text(
    s.replace(old, new),
    encoding="utf-8",
)

print("OK: qwen_stats() исправлен")
print("Backup: data.py.bak")
PY
```

### 2. Проверяем

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/data.py && \
echo "PYTHON SYNTAX: OK"
```

И затем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.components.technical_modules.data import qwen_stats
import pprint

pprint.pp(qwen_stats())
PY
```

Ожидаем примерно:

```text
{
    'status': 'ГОТОВ',
    'photos': 100,
    'ok': 100,
    'errors': 0,
    'avg_time': ...,
    'avg_confidence': ...,
    'addresses': ...
}
```

**Автоматический запуск Qwen после Hybrid мы не трогаем** — он у тебя уже реализован в `photo_processing.py`. Сейчас исправляем только отображение статуса в разделе «Данные».

---

### 👤 **User** — 2026-08-18 13:19:09

"СТАТУС ОБРАБОТЧИКОВ"
        ).classes(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '345,390p' app/web/components/technical_modules/data.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:19:09

Да, это конец блока Qwen. Теперь проверим, что исправление реально встало и что `qwen_stats()` отдаёт правильные данные.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/data.py && \
echo "PYTHON SYNTAX: OK"
```

Затем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.components.technical_modules.data import qwen_stats
import pprint

print("===== QWEN STATS =====")
pprint.pp(qwen_stats())
PY
```

Если получим `status: 'ГОТОВ'`, то **код исправлен**.

После этого перезапустим веб-приложение и проверим визуально блок:

```text
СТАТУС ОБРАБОТЧИКОВ

DINO v33
Распознавание сцен
ГОТОВ

Hybrid v12
Последний запуск: 20260818_115048
ГОТОВ
Фото: 526
Адресов: 18

Qwen3-VL 4B
Анализ содержимого фотографий
ГОТОВ
Обработано: 100
OK: 100
Ошибок: 0
Адресов: ...
Среднее время: ...
Средняя уверенность: ...
```

При этом **Qwen по-прежнему запускается автоматически после Hybrid** — мы эту часть не меняли.

---

### 👤 **User** — 2026-08-18 13:20:02

перезапускаем

---

### 🤖 **Assistant** — 2026-08-18 13:20:03

Да. Сначала останови текущий веб-процесс, затем запусти заново.

Если он запущен в текущем терминале — **Ctrl+C**, затем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python app/main.py
```

Если приложение у тебя запускается через systemd и работает в фоне, скажи — дам команду именно для перезапуска сервиса.

---

### 👤 **User** — 2026-08-18 13:20:15

у меня именно так

---

### 🤖 **Assistant** — 2026-08-18 13:20:15

Да, тогда просто:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python app/main.py
```

После запуска открой веб-интерфейс и зайди:

**Технический раздел → Данные**

Проверяем, что теперь Qwen показывает **ГОТОВ**, а не **Неверный формат**.

---

### 👤 **User** — 2026-08-18 13:20:27

запускается через systemd и работает в фоне,

---

### 🤖 **Assistant** — 2026-08-18 13:20:27

Тогда перезапускаем systemd-сервис.

Сначала найдём точное имя сервиса:

```bash
systemctl list-units --type=service --all | grep -Ei 'scene|fingerprint|nicegui|albion|photo'
```

Пришли вывод — дам точную команду `systemctl restart ...`, чтобы не угадать имя сервиса.

---

### 👤 **User** — 2026-08-18 13:20:42

print("===== QWEN STATS =====")
pprint.pp(qwen_stats())
PY
===== QWEN STATS =====
{'status': 'Неверный формат',
 'photos': 0,
 'ok': 0,
 'errors': 0,
 'avg_time': 0,
 'avg_confidence': 0,
 'addresses': 0}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ systemctl list-units --type=service --all | grep -Ei 'scene|fingerprint|nicegui|albion|photo'
  albion-autonom.service                                loaded    active     running      АЛЬБИОН: Локатор-Навигатор (Autonom Experimental)
  albion-loc-exp.service                                loaded    activating auto-restart Albion Locator Experimental Service
  albion-locator.service                                loaded    activating auto-restart АЛЬБИОН: Локатор-Навигатор (Stable)
  albion.service                                        loaded    active     running      Albion Renamer Service
  lora.service                                          loaded    active     running      LORA Photo Database
  skdf-photo.service                                    loaded    activating auto-restart АЛЬБИОН: Локатор-Навигатор
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:20:47

У нас веб-приложение, судя по списку, запущено сервисом **`lora.service`**.

Но сначала важный момент: `qwen_stats()` сейчас всё ещё возвращает `Неверный формат`, значит **до перезапуска нужно проверить, что исправленный код действительно записан**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -A15 'def qwen_stats' app/web/components/technical_modules/data.py
```

Если там уже есть:

```python
candidates = []
root_summary = QWEN_ROOT / "summary.json"
```

и далее:

```python
results = data.get("results", [])
```

тогда перезапускаем:

```bash
sudo systemctl restart lora.service && \
systemctl status lora.service --no-pager
```

После этого проверим:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.components.technical_modules.data import qwen_stats
import pprint
pprint.pp(qwen_stats())
PY
```

**Если снова будет `Неверный формат` — не будем дальше перезапускать.** Тогда сразу посмотрим конкретный `summary.json`, который выбирает `data.py`, и исправим причину.

---

### 👤 **User** — 2026-08-18 13:21:06

grep -n -A15 'def qwen_stats' app/web/components/technical_modules/data.py
78:def qwen_stats():
79-    summary = QWEN_ROOT / "summary.json"
80-
81-    if not summary.exists():
82-        return {
83-            "status": "Нет данных",
84-            "photos": 0,
85-            "ok": 0,
86-            "errors": 0,
87-            "avg_time": 0,
88-            "avg_confidence": 0,
89-            "addresses": 0,
90-        }
91-
92-    try:
93-        data = json.loads(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 13:21:07

Вот причина: **исправление `data.py` не применилось**. Файл всё ещё старый:

```python
summary = QWEN_ROOT / "summary.json"
```

Давай сейчас заменим `qwen_stats()` гарантированно. Сделаем через `uv run python`, чтобы не зависеть от отсутствующего `python`.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/technical_modules/data.py \
   app/web/components/technical_modules/data.py.bak_qwen_fix && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/data.py")
s = p.read_text(encoding="utf-8")

start = s.index("def qwen_stats():")
end = s.index("\ndef build_stat(", start)

new_func = '''def qwen_stats():
    """
    Статистика Qwen3-VL 4B.

    Читает фактический формат:
    summary.json -> {"model": ..., "results": [...]}

    Используется самый свежий summary.json.
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
        return {
            "status": "Нет данных",
            "photos": 0,
            "ok": 0,
            "errors": 0,
            "avg_time": 0,
            "avg_confidence": 0,
            "addresses": 0,
        }

    summary = max(
        candidates,
        key=lambda p: p.stat().st_mtime,
    )

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

    if not isinstance(data, dict):
        return {
            "status": "Неверный формат",
            "photos": 0,
            "ok": 0,
            "errors": 0,
            "avg_time": 0,
            "avg_confidence": 0,
            "addresses": 0,
        }

    results = data.get("results", [])

    if not isinstance(results, list):
        return {
            "status": "Неверный формат",
            "photos": 0,
            "ok": 0,
            "errors": 0,
            "avg_time": 0,
            "avg_confidence": 0,
            "addresses": 0,
        }

    total = len(results)

    ok = sum(
        1
        for row in results
        if isinstance(row, dict)
        and row.get("status") == "ok"
    )

    errors = sum(
        1
        for row in results
        if isinstance(row, dict)
        and row.get("status") == "error"
    )

    times = []

    for row in results:
        if not isinstance(row, dict):
            continue

        value = row.get("time_sec")

        if value is not None:
            try:
                times.append(float(value))
            except (TypeError, ValueError):
                pass

    confidences = []

    for row in results:
        if not isinstance(row, dict):
            continue

        value = row.get("confidence")

        if value not in (None, ""):
            try:
                confidences.append(float(value))
            except (TypeError, ValueError):
                pass

    addresses = {
        row.get("address")
        for row in results
        if isinstance(row, dict)
        and row.get("address")
    }

    return {
        "status": "ГОТОВ" if ok else "Нет данных",
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

'''

s = s[:start] + new_func + s[end + 1:]

p.write_text(s, encoding="utf-8")

print("QWEN STATS: FIXED")
print("Backup: data.py.bak_qwen_fix")
PY
```

Теперь **не перезапускаем systemd**, сначала проверяем непосредственно функцию:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/components/technical_modules/data.py && \
uv run python - <<'PY'
from app.web.components.technical_modules.data import qwen_stats
import pprint

pprint.pp(qwen_stats())
PY
```

Здесь уже должен появиться примерно такой результат:

```text
{
    'status': 'ГОТОВ',
    'photos': 100,
    'ok': 100,
    'errors': 0,
    'avg_time': ...,
    'avg_confidence': ...,
    'addresses': ...
}
```

**Если это получилось — только тогда:**

```bash
sudo systemctl restart lora.service
```

После перезапуска верхний блок «СТАТУС ОБРАБОТЧИКОВ» должен брать правильный статус Qwen.

---

### 👤 **User** — 2026-08-18 13:22:51

ок. надо настроить русной еще запуск квен

---

### 🤖 **Assistant** — 2026-08-18 13:22:52

Да. Сейчас у нас уже есть **автоматический запуск Qwen после Hybrid**, нужно добавить **ручной запуск Qwen** отдельно — без повторного запуска DINO/Hybrid.

Логика будет такая:

```text
ОБРАБОТКА ФОТО
    ↓
DINO v33
    ↓
Hybrid v12
    ↓
результат /data/output/daily/20260818_115048/
    ↓
Qwen автоматически

И отдельно:

QWEN
    ↓
[▶ ЗАПУСТИТЬ QWEN]
    ↓
выбирается последний Hybrid
    ↓
Qwen обрабатывает его
```

Причём ручной запуск должен использовать **последний Hybrid**, например:

```text
data/output/daily/20260818_115048
```

и складывать результат в:

```text
data/metadata/qwen4b/20260818_115048/
```

### Сначала покажи текущий `qwen.py`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,330p' app/web/components/technical_modules/qwen.py
```

По нему я дам точную команду, которая добавит кнопку:

**▶ ЗАПУСТИТЬ QWEN**

в отдельную вкладку Qwen, не ломая уже работающий автоматический запуск после Hybrid.

---

### 👤 **User** — 2026-08-18 13:23:10

"errors": len(error_results),
            "addresses": len(addresses),
            "avg_time": avg_time,
            "avg_confidence": avg_confidence,
            "model": summary.get(
                "model",
                "qwen3-vl:4b-instruct",
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

        with ui.row().classes("gap-2"):

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

    refresh()

    ui.timer(
        5.0,
        refresh,
    )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

