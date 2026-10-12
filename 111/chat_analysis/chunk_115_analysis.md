### ✅ **Решение**

В `technical.py` вкладка "Qwen" вызывает `build_qwen()`, но в `qwen.py` отсутствует логика загрузки `summary.json`. Добавим её и убедимся, что данные отображаются корректно.

---

### 📁 **Файлы для проверки**

#### 1. `technical.py` (вкладка "Qwen")
```python
with ui.tab_panel("qwen"):
    build_qwen()
```

#### 2. `qwen.py` (логика отображения)
```python
def build_qwen():
    with ui.card().classes("w-full"):
        ui.label("Qwen3-VL 4B").classes("text-lg font-bold")
        ui.separator()
        ui.label("Анализ содержимого фотографий")
        ui.separator()
        ui.label("Обработано:").classes("text-sm")
        ui.label("OK:").classes("text-sm")
        ui.label("Ошибок:").classes("text-sm")
        ui.label("Адресов:").classes("text-sm")
        ui.label("Среднее время:").classes("text-sm")
        ui.label("Средняя уверенность:").classes("text-sm")
```

---

### 🔧 **Исправление**

Добавим в `qwen.py` загрузку `summary.json` и отображение данных:

```python
import json
from pathlib import Path

def build_qwen():
    summary_path = PROJECT / "data" / "metadata" / "qwen4b" / "summary.json"
    if summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
        except json.JSONDecodeError:
            ui.notify("Ошибка чтения summary.json", type="negative")
            return
    else:
        ui.notify("Файл summary.json не найден", type="warning")
        return

    with ui.card().classes("w-full"):
        ui.label("Qwen3-VL 4B").classes("text-lg font-bold")
        ui.separator()
        ui.label("Анализ содержимого фотографий")
        ui.separator()
        ui.label("Обработано:").classes("text-sm")
        ui.label(str(summary.get("processed", 0))).classes("text-sm")
        ui.label("OK:").classes("text-sm")
        ui.label(str(summary.get("ok", 0))).classes("text-sm")
        ui.label("Ошибок:").classes("text-sm")
        ui.label(str(summary.get("errors", 0))).classes("text-sm")
        ui.label("Адресов:").classes("text-sm")
        ui.label(str(summary.get("addresses", 0))).classes("text-sm")
        ui.label("Среднее время:").classes("text-sm")
        ui.label(f"{summary.get('avg_time', 0):.2f} сек").classes("text-sm")
        ui.label("Средняя уверенность:").classes("text-sm")
        ui.label(f"{summary.get('avg_confidence', 0):.1f}%").classes("text-sm")
```

---

### ✅ **Итог**

- Вкладка **«Обработка»** останется без изменений (DINO + Hybrid).
- Вкладка **«Qwen»** теперь:
  - Загружает `summary.json`.
  - Отображает статистику: `Обработано`, `OK`, `Ошибок`, `Адресов`, `Среднее время`, `Средняя уверенность`.
- Ошибки формата `summary.json` теперь обрабатываются и отображаются как уведомления.

Если нужно, могу добавить логирование или улучшить UI.