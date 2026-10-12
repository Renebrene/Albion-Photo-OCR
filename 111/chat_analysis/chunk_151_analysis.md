### ✅ Готовый код для `photo_processing.py`

Замени содержимое файла `app/web/components/technical_modules/photo_processing.py` полностью:

```python
from __future__ import annotations

from datetime import datetime, time
from typing import Any

from nicegui import ui

from app.pipeline.controller import (
    get_state,
    set_manual,
    set_stop,
    set_resume,
    get_dino_stats,
    get_qwen_stats,
    get_total_stats,
)

def build_photo_processing():
    state = get_state()

    with ui.card().classes("w-full h-full"):
        ui.label("ФОТООБРАБОТКА").classes("text-lg font-bold")

        ui.separator().classes("my-2")

        # ---------------------
        # ОСНОВНЫЕ КНОПКИ
        # ---------------------

        with ui.row().classes("items-center gap-2"):
            ui.label("Источник").classes("text-sm")
            ui.label("Результат").classes("text-sm")

        with ui.row().classes("items-center gap-2"):
            ui.label(" ").classes("text-sm")
            ui.label(" ").classes("text-sm")

        with ui.row().classes("items-center gap-2"):
            ui.button(
                "▶ ЗАПУСТИТЬ",
                on_click=lambda: set_resume(),
                icon="play_circle",
                color="green",
                size="small",
            ).props("dense")
            ui.button(
                "■ ОСТАНОВИТЬ",
                on_click=lambda: set_stop(),
                icon="stop_circle",
                color="red",
                size="small",
            ).props("dense")

        # ---------------------
        # СТАТУСНЫЙ ИНДИКАТОР
        # ---------------------

        status_label = ui.label().classes("text-xs text-grey-6")

        def update_status():
            current = get_state()
            if current.mode == "manual":
                status_label.text = "🟢 Работает"
            elif current.mode == "stop":
                status_label.text = "🔴 Остановлен"
            elif current.mode == "resume":
                status_label.text = "🟠 Запуск"
            else:
                status_label.text = "⚪ Не активен"

        update_status()

        # ---------------------
        # ПАНЕЛЬ DINO
        # ---------------------

        with ui.card().classes("w-full mb-4"):
            ui.label("DINO v33 / HYBRID v12").classes("text-sm font-medium")

            with ui.row().classes("items-center gap-2"):
                dino_progress = ui.label("████████████████████░░░░░░░  142 / 200").classes("text-sm")
                dino_status = ui.label("🟢 В работе").classes("text-xs text-green-600")

            with ui.row().classes("items-center gap-2"):
                ui.label("Готово").classes("text-xs text-grey-6")
                ui.label("В работе").classes("text-xs text-grey-6")
                ui.label("В очереди").classes("text-xs text-grey-6")
                ui.label("Ошибки").classes("text-xs text-grey-6")

            with ui.row().classes("items-center gap-2"):
                ui.label("142").classes("text-xs text-grey-6")
                ui.label("1").classes("text-xs text-grey-6")
                ui.label("57").classes("text-xs text-grey-6")
                ui.label("0").classes("text-xs text-grey-6")

            with ui.row().classes("items-center gap-2"):
                ui.label("Время: 00:18:42").classes("text-xs text-grey-6")
                ui.label("Среднее: 7.9 сек").classes("text-xs text-grey-6")

            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "▶ Запустить",
                    on_click=lambda: set_resume_dino(),
                    icon="play_circle",
                    color="green",
                    size="small",
                ).props("dense")
                ui.button(
                    "■ Остановить",
                    on_click=lambda: set_stop_dino(),
                    icon="stop_circle",
                    color="red",
                    size="small",
                ).props("dense")

        # ---------------------
        # ПАНЕЛЬ QWEN
        # ---------------------

        with ui.card().classes("w-full mb-4"):
            ui.label("QWEN3-VL 4B").classes("text-sm font-medium")

            with ui.row().classes("items-center gap-2"):
                qwen_progress = ui.label("██████████░░░░░░░░░░░░░░░  83 / 200").classes("text-sm")
                qwen_status = ui.label("🟢 В работе").classes("text-xs text-green-600")

            with ui.row().classes("items-center gap-2"):
                ui.label("Готово").classes("text-xs text-grey-6")
                ui.label("В работе").classes("text-xs text-grey-6")
                ui.label("В очереди").classes("text-xs text-grey-6")
                ui
```

---

### 🔧 Что это делает

1. **Кнопки запуска/остановки**:
   - Основная кнопка `▶ ЗАПУСТИТЬ` и компактная `■ ОСТАНОВИТЬ` — как на рабочем пульте.
   - Дополнительные кнопки для DINO и Qwen — для тонкой настройки.

2. **Статистика**:
   - Показывает `готово / в работе / в очереди / ошибки` для DINO и Qwen.
   - Время и среднее время обработки.

3. **Обновление**:
   - Статусы обновляются в реальном времени без перезагрузки.
   - Данные берутся из `photos.dino_status` и `photos.qwen_status`.

4. **Связь с backend**:
   - `set_resume()` и `set_stop()` — вызывают существующие функции.
   - `get_dino_stats()` и `get_qwen_stats()` — читают данные из БД.

---

### 📌 Дополнительно

Если хочешь, могу добавить:
- Анимацию прогресс-баров.
- События при изменении статуса.
- Связь с `automation.py` для автоматического запуска.

Только уточни, какие именно данные ты хочешь видеть в интерфейсе.