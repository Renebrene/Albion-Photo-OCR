### 🛠️ **Решение проблемы с пустыми ответами**

#### 1. **Проверяем содержимое пустых JSON-файлов**
Сначала посмотрим, что именно записал Qwen в `Комарова13_02.json` и `Комарова13_04.json`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== 02 ==="
cat "data/metadata/qwen4b/78_v33/Комарова13_02.json"

echo
echo "=== 04 ==="
cat "data/metadata/qwen4b/78_v33/Комарова13_04.json"
```

Если файлы пустые, это может означать:
- Модель не смогла сформировать ответ.
- Ответ был обрезан из-за ограничений на длину.
- Скрипт не обработал ошибку корректно.

---

#### 2. **Добавляем защиту от пустых ответов**
Обновим `qwen4b_output_v01.py`, чтобы:
- Повторять запрос при пустом ответе.
- Записывать ошибку, а не пустой JSON.
- Уменьшать вероятность долгих рассуждений.

```python
# Вставляем в qwen4b_output_v01.py
import json
from pathlib import Path
import time
import random

def safe_query(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = model(prompt)
            if response and isinstance(response, dict):
                return response
            else:
                print(f"⚠️ Пустой ответ на попытку {attempt + 1}")
                time.sleep(random.uniform(1, 3))
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(random.uniform(1, 3))
    return None
```

---

#### 3. **Упрощаем промпт для ускорения**
Уберите сложные разделы, которые могут вызывать задержки. Например, упростите инструкции к `camera_view` и `scene_objects`:

```python
# Вставляем в qwen4b_output_v01.py
prompt = """Определи тип конструкции, объекты, погоду и качество изображения.
Тип конструкции: видеоэкран (если неясно — "неизвестно").
Камера: расстояние (далеко/средне/близко/очень близко/неизвестно), ракурс (прямой/слева/справа/сверху/снизу/неизвестно).
Объекты: автобусы, автомобили, люди (если видны).
Качество анализа: banner_analysis, environment_analysis, text_analysis (high/medium/low/none).
"""
```

---

#### 4. **Проверяем корректность изображений**
Добавьте проверку на наличие и формат изображений перед обработкой:

```python
# Вставляем в qwen4b_output_v01.py
from PIL import Image
import os

def validate_image(path):
    if not os.path.exists(path):
        print(f"❌ Изображение не найдено: {path}")
        return False
    try:
        img = Image.open(path)
        img.verify()
        return True
    except Exception as e:
        print(f"❌ Ошибка открытия изображения: {path} — {e}")
        return False
```

---

#### 5. **Повторный тест на 5 изображений**
Запускаем тест с обновленным скриптом:

```bash
uv run python scripts/qwen4b_output_v01.py --limit 5
```

Если всё работает, запускаем полный прогон:

```bash
uv run python scripts/qwen4b_output_v01.py
```

---

### ✅ **Итог**
- **Пустые ответы** — это результат сложных промптов или проблем с моделью.
- **Обновленный скрипт** с защитой от ошибок и упрощенным промптом решит большинство проблем.
- **Проверка изображений** гарантирует корректность входных данных.
- **Повторный тест** поможет убедиться, что всё работает корректно перед полным прогоном.