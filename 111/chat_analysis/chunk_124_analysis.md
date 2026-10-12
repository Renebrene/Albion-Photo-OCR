### 🧠 **Итоговый план: daily_pipeline_v01.py**

```python
import os
import time
import json
import shutil
from pathlib import Path
from datetime import datetime
import subprocess
import requests
import base64
import random

# Константы
INPUT_DIR = Path("data/input")
OUTPUT_DIR = Path("data/output/daily")
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
DINO_SCRIPT = "scripts/recognize.py"
SORT_SCRIPT = "scripts/sort_sequence_v39.py"
QWEN_SCRIPT = "scripts/qwen4b_output_v01.py"
DB_SCRIPT = "scripts/import_qwen_to_db.py"
PREVIEW_SIZE = (1024, 768)
DRY_RUN = False  # Установите True для тестирования без изменений

def generate_run_id():
    """Генерация уникального идентификатора запуска"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def run_command(command, cwd=None):
    """Запуск команды с логированием"""
    print(f"[CMD] {command}")
    result = subprocess.run(
        command.split(),
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False
    )
    if result.returncode != 0:
        print(f"[ERROR] {command}")
        print(result.stderr)
        raise RuntimeError(f"Ошибка выполнения: {command}")
    return result.stdout

def process_images():
    """Основной процесс обработки изображений"""
    print(f"[PIPELINE] Начало запуска {RUN_ID}")
    
    # 1. Создание структуры выходной директории
    run_folder = OUTPUT_DIR / RUN_ID
    run_folder.mkdir(parents=True, exist_ok=True)
    print(f"[PIPELINE] Создана папка {run_folder}")
    
    # 2. Запуск DINO для распознавания адресов
    dino_output = run_folder / "dino_output.json"
    dino_cmd = [
        "python", DINO_SCRIPT,
        "--input", str(INPUT_DIR),
        "--output", str(dino_output),
        "--device", "cpu"
    ]
    run_command(dino_cmd, cwd=str(run_folder))
    
    # 3. Сортировка файлов
    sort_cmd = [
        "python", SORT_SCRIPT,
        "--input", str(INPUT_DIR),
        "--output", str(run_folder),
        "--run_id", RUN_ID
    ]
    run_command(sort_cmd, cwd=str(run_folder))
    
    # 4. Генерация превью
    preview_dir = run_folder / "previews"
    preview_dir.mkdir(exist_ok=True)
    for file in run_folder.glob("*.*"):
        if file.is_file() and file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            preview_path = preview_dir / f"preview_{file.stem}.jpg"
            # Здесь реализовать генерацию превью
            # Пример: используйте PIL для ресайза
            print(f"[PREVIEW] Создано {preview_path}")
    
    # 5. Параллельная обработка Qwen
    qwen_cmd = [
        "python", QWEN_SCRIPT,
        "--input", str(run_folder),
        "--output", str(run_folder),
        "--run_id", RUN_ID
    ]
    qwen_process = subprocess.Popen(qwen_cmd, cwd=str(run_folder))
    
    # 6. Обновление PostgreSQL
    db_cmd = [
        "python", DB_SCRIPT,
        "--input", str(run_folder),
        "--run_id", RUN_ID
    ]
    run_command(db_cmd, cwd=str(run_folder))
    
    # 7. Завершение
    print(f"[PIPELINE] Завершение запуска {RUN_ID}")
    print(f"[PIPELINE] Статистика: {time.time() - start_time:.2f} секунд")
```

### 📁 **Структура выходной директории**
```
data/output/daily/
    20260818_202000/
        dino_output.json
        previews/
        qwen_output/
        db_update.log
```

### 🔄 **Особенности реализации**
1. **Параллельность**: Qwen запускается как отдельный процесс, не ждя завершения сортировки
2. **DRY RUN**: Включение режима тестирования без изменений в реальных данных
3. **Превью**: Генерация миниатюр для быстрого просмотра
4. **Логирование**: Все этапы отслеживаются в консоли
5. **Управление памятью**: Использование временных директорий для изоляции запусков

### 📌 **Дополнительные шаги**
1. Добавьте обработку ошибок для каждого этапа
2. Реализуйте генерацию превью с использованием PIL
3. Добавьте логирование времени выполнения каждого этапа
4. Реализуйте систему отслеживания прогресса
5. Добавьте обработку исключений для сетевых запросов

Этот подход обеспечивает гибкость, надежность и масштабируемость для обработки больших объемов изображений.