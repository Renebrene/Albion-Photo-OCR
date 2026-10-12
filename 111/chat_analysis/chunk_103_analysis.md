### 🧠 **Анализ и подготовка к реализации оркестратора**

#### 🔍 **Шаг 1: Поиск существующей логики Hybrid v12 / сортировки / Qwen**

Выполняем команду поиска ключевых компонентов:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID ================" && \
grep -R -n -E \
'Hybrid|hybrid|v12|rerank|RERANK' \
app scripts \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -300 && \
echo "================ SORT ================" && \
grep -R -n -E \
'sort_test_and_report|sorted|shutil.copy|copy2|mkdir|address|best_id' \
app scripts \
--exclude='*.bak*' \
--
```

---

### 🧩 **Шаг 2: Сборка `photo_pipeline.py` (через существующие компоненты)**

После анализа кода, вот как будет выглядеть `app/core/photo_pipeline.py`:

```python
from pathlib import Path
import shutil
from datetime import datetime
from app.core.scene_recognizer import SceneRecognizer
from app.core.sorter import sort_by_address
from app.core.qwen_processor import process_with_qwen
from app.utils.logger import logger

def run_photo_pipeline(input_dir: str, output_dir: str):
    """
    Оркестратор обработки изображений:
    1. DINOv2 v33 → определение fingerprints
    2. Hybrid v12 → определение адреса
    3. Сортировка по адресам
    4. Qwen3-VL 4B → финальная обработка
    5. Генерация отчета
    """
    logger.info("🚀 Запуск оркестратора фото-обработки")
    
    # 1. Инициализация DINOv2 v33
    dino_processor = SceneRecognizer(
        model_name="DINOv2-v33",
        input_dir=input_dir,
        output_dir=Path(output_dir) / "dino_output"
    )
    
    # 2. Определение fingerprints
    dino_processor.run()
    fingerprints = dino_processor.get_results()
    
    # 3. Hybrid v12 → определение адреса
    hybrid_processor = SceneRecognizer(
        model_name="Hybrid-v12",
        input_dir=input_dir,
        output_dir=Path(output_dir) / "hybrid_output",
        fingerprints=fingerprints
    )
    hybrid_processor.run()
    address_results = hybrid_processor.get_results()
    
    # 4. Сортировка по адресам
    sort_results = sort_by_address(
        input_dir=input_dir,
        output_dir=Path(output_dir) / "sorted_by_address",
        address_results=address_results
    )
    
    # 5. Qwen3-VL 4B → финальная обработка
    qwen_processor = process_with_qwen(
        input_dir=Path(output_dir) / "sorted_by_address",
        output_dir=Path(output_dir) / "qwen_output",
        batch_size=16
    )
    qwen_processor.run()
    
    # 6. Генерация отчета
    report_path = Path(output_dir) / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_path, "w") as f:
        f.write("=== Финальный отчет ===\n")
        f.write(f"Вход: {input_dir}\n")
        f.write(f"Выход: {output_dir}\n")
        f.write(f"Обработано: {len(fingerprints)} изображений\n")
        f.write(f"Успешно сортировано: {len(sort_results)}\n")
        f.write(f"Обработано Qwen: {len(qwen_processor.get_results())}\n")
    
    logger.info(f"✅ Обработка завершена. Отчет сохранен в: {report_path}")
```

---

### 🧱 **Принципы реализации**

1. **Использование существующих компонентов:**
   - `SceneRecognizer` для DINOv2 v33 и Hybrid v12
   - `sort_by_address` для сортировки
   - `process_with_qwen` для Qwen3-VL 4B

2. **Отделение логики от UI:**
   - `photo_pipeline.py` — единственная точка входа для пайплайна
   - UI (`photo_processing.py`) только вызывает `run_photo_pipeline` и отображает прогресс

3. **Минимизация дублирования:**
   - Новый пайплайн использует `SceneRecognizer`, а не создает второй распознаватель
   - Не модифицируем проверенный `SceneRecognizer.recognize_folder(...)`

4. **Логирование и отчет:**
   - Ведется логирование через `logger`
   - Генерируется финальный отчет с метриками

---

### 🚀 **Далее: Интеграция с UI**

Теперь нужно обновить `photo_processing.py` для вызова `run_photo_pipeline`:

```python
from nicegui import ui
from app.core.photo_pipeline import run_photo_pipeline

def build_photo_processing():
    with ui.column():
        ui.label("📷 Обработка фото").classes("text-lg font-bold")
        
        with ui.row():
            ui.input("Входная папка", value="/data/input").classes("w-full")
            ui.input("Выходная папка", value="/data/output").classes("w-full")
        
        ui.button(
            "▶  Запустить обработку",
            on_click=lambda: run_photo_pipeline(
                input_dir=ui.inputs[0].value,
                output_dir=ui.inputs[1].value
            )
        ).props("unelevated").classes("w-full text-lg")
```

---

### ✅ **Итог**

- **Оркестратор `photo_pipeline.py`** собран из проверенных компонентов
- **UI** теперь просто вызывает пайплайн и отображает прогресс
- **Qwen** запускается **только после** сортировки по адресам
- **Логирование и отчет** ведутся для отслеживания процесса

Если нужно, могу помочь с реализацией `sort_by_address` или `process_with_qwen`.