### 📌 **Добавляем статистику в "Данные"**

Вот как будет выглядеть обновлённый `data.py` с динамической статистикой:

```python
# app/web/components/technical_modules/data.py

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from ..utils import get_daily_root, get_photo_index, get_qwen_status, get_qwen_errors
from ..state import STATE

def build_data():
    """Статистика текущей базы данных"""
    daily_root = get_daily_root()
    photo_index = get_photo_index()
    qwen_status = get_qwen_status()
    qwen_errors = get_qwen_errors()

    with ui.column().classes("w-full gap-4"):
        # 🔍 СТАТИСТИКА ТЕКУЩЕЙ БАЗЫ
        with ui.card().classes("w-full"):
            ui.label("📊 Статистика текущей базы").classes("text-xl font-bold mb-3")

            with ui.row().classes("w-full gap-4"):
                ui.label("📦 Текущий запуск").classes("font-medium")
                ui.label(str(daily_root.name)).classes("text-blue-600")

            with ui.row().classes("w-full gap-4"):
                ui.label("📍 Адресов").classes("font-medium")
                ui.label(str(len(STATE.addresses))).classes("text-green-600")

            with ui.row().classes("w-full gap-4"):
                ui.label("📸 Фотографий").classes("font-medium")
                ui.label(str(len(photo_index))).classes("text-purple-600")

            with ui.row().classes("w-full gap-4"):
                ui.label("🖼️ Фотографий по адресам").classes("font-medium")
                ui.label(str(sum(len(v) for v in photo_index.values()))).classes("text-purple-600")

            with ui.row().classes("w-full gap-4"):
                ui.label("🔍 Индекс фото").classes("font-medium")
                ui.label("✅ Полностью проиндексировано" if all(v) for v in photo_index.values() else "⚠️ Неполный индекс").classes("text-yellow-600")

            with ui.row().classes("w-full gap-4"):
                ui.label("🤖 Qwen-обработано").classes("font-medium")
                ui.label(str(qwen_status.get("total", 0))).classes("text-green-600")

            with ui.row().classes("w-full gap-4"):
                ui.label("🤖 Qwen с ошибками").classes("font-medium")
                ui.label(str(qwen_status.get("errors", 0))).classes("text-red-600")

            with ui.row().classes("w-full gap-4"):
                ui.label("⏱ Последняя обработка").classes("font-medium")
                ui.label(str(datetime.fromtimestamp(qwen_status.get("last_processed", 0)))).classes("text-blue-600")

            with ui.row().classes("w-full gap-4"):
                ui.label("🔄 Обновление").classes("font-medium")
                ui.label("✅ Активно" if STATE.is_updating else "⚠️ Пауза").classes("text-yellow-600")

        # 📁 Дополнительные данные
        with ui.card().classes("w-full mt-4"):
            ui.label("📁 Дополнительные данные").classes("text-xl font-bold mb-3")
            ui.label(f"Папка: {daily_root}").classes("text-gray-600")
            ui.label(f"Файлов: {len(os.listdir(daily_root))}").classes("text-gray-600")
```

---

### ✅ **Что это даёт**

1. **Динамическая статистика** — данные берутся из:
   - `daily/...` (текущий запуск)
   - `photo_index` (индекс фото)
   - `qwen_status` (статус обработки)
   - `qwen_errors` (ошибки Qwen)

2. **Нет жёстких значений** — больше нет `946 фотографий` или `78–95 адресов`.

3. **Обновляется автоматически** — при изменении данных в `daily/...` или базе.

4. **Ошибки и статусы** — отображаются в реальном времени.

---

### 🚀 **Далее**

Теперь можно:
1. Добавить **график** или **таблицу** для `фотографий по адресам`
2. Реализовать **фильтрацию** по дате/адресу
3. Добавить **логи обработки** в раздел "Данные"

Хочешь, я сделаю один из этих шагов?