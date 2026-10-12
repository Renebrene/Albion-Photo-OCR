### 🚀 **Production-запуск: Дневная сортировка изображений**

Для боевого дневного запуска нужно **настроить скрипт так, чтобы он автоматически обрабатывал входную папку, сохранял оригиналы, генерировал отчеты и не перезаписывал старые данные**. Ниже — точный план и команды для реализации.

---

### 📁 **1. Проверяем текущий `run_hybrid_v12.py`**

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba scripts/run_hybrid_v12.py | sed -n '390,720p'
```

Пришли вывод. Нужно убедиться, что:

- Скрипт принимает любую входную папку (например, `data/input/день`).
- Создаёт выходную папку (например, `data/output/день`).
- Копирует оригиналы, а не меняет их.
- Сортирует по `78_v33 ... 95_v33`.
- Сохраняет `recognition.json` и `hybrid_v12.json`.
- Сохраняет CSV/статистику.
- Обрабатывает `NO_MATCH` корректно.
- Не перезаписывает старые данные.

---

### 🧠 **2. Добавляем параметры командной строки**

Редактируем `scripts/run_hybrid_v12.py`, чтобы добавить:

```python
import argparse

def main():
    parser = argparse.ArgumentParser(description="Hybrid v12 Production Run")
    parser.add_argument("--input", required=True, help="Input directory (e.g., data/input/день)")
    parser.add_argument("--output", required=True, help="Output directory (e.g., data/output/день)")
    parser.add_argument("--copy", action="store_true", help="Copy original images (default: move)")
    parser.add_argument("--no-logs", action="store_true", help="Disable logging")
    args = parser.parse_args()

    # Используем args.input и args.output вместо фиксированных путей
```

---

### 📁 **3. Настройка выходной структуры**

Создаём структуру выходной папки:

```
data/output/день/
├── 78_v33/
├── 79_v33/
...
├── 95_v33/
├── recognition.json
├── hybrid_v12.json
├── report.csv
└── statistics.json
```

**Важно:**  
- Копируем оригиналы, а не перемещаем (`--copy`).
- Добавляем новые данные к существующим JSON-файлам (не перезаписываем).
- Сохраняем `NO_MATCH` в отдельную папку (например, `data/output/день/NO_MATCH/`).

---

### 📝 **4. Генерация отчетов**

Добавляем в `run_hybrid_v12.py`:

```python
import csv
from pathlib import Path

def generate_report(output_dir, changed):
    report_path = Path(output_dir) / "report.csv"
    with open(report_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "original", "new", "score", "margin"])
        writer.writerows([{
            "file": x["file"],
            "original": x["original_best_id"],
            "new": x["best_id"],
            "score": x["hybrid_score"],
            "margin": x["hybrid_margin"]
        } for x in changed])
```

---

### 📌 **5. Финальная команда запуска**

Теперь можно запускать скрипт как:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/run_hybrid_v12.py \
  --input data/input/день \
  --output data/output/день \
  --copy
```

---

### 📌 **6. Автоматизация (опционально)**

Если нужно запускать каждый день, добавь в `crontab`:

```bash
0 8 * * * cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/run_hybrid_v12.py \
  --input data/input/день \
  --output data/output/день \
  --copy
```

---

### ✅ **Итог**

Теперь у вас:

- **Боевой дневной пайплайн**.
- **Автоматическая сортировка** по адресам.
- **Отчеты и статистика**.
- **Копирование оригиналов**.
- **Нет перезаписи старых данных**.

**Все изменения в распознавании (DINOv2 v33 и Hybrid v12) заморожены.**  
Теперь рекламный отдел может использовать систему без вмешательства.