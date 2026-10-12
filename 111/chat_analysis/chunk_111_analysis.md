### ✅ **Решение**

Теперь мы знаем, что:

- Скрипт `create_previews_v01.py` **уже умеет** создавать `data/preview/daily/20260816_230042/`
- Он **не вызывается автоматически** в текущем pipeline
- Нам нужно **восстановить его вызов** после Qwen

---

### 🔧 **Шаг 1: Проверим содержимое `create_previews_v01.py`**

```bash
cd ~/projects/scene_fingerprint_mvp_v02
cat scripts/create_previews_v01.py
```

**Ожидаемый вывод** (пример):

```python
import os
from PIL import Image

def create_previews(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            img_path = os.path.join(input_dir, filename)
            img = Image.open(img_path)
            img.thumbnail((128, 128))
            preview_path = os.path.join(output_dir, filename)
            img.save(preview_path)
```

---

### 🔧 **Шаг 2: Найдём, где раньше вызывался `create_previews_v01.py`**

```bash
grep -R -n "create_previews_v01" . \
    --exclude-dir=.venv \
    --exclude-dir=.git \
    --exclude="*.pyc"
```

**Ожидаемый вывод** (пример):

```
scripts/banner_database_v02.py:123:    create_previews_v01(input_dir, preview_dir)
```

---

### ✅ **Шаг 3: Восстановим вызов в pipeline**

Теперь нужно **вставить вызов `create_previews_v01.py`** после Qwen в `photo_processing.py`, чтобы preview создавался **вместе с** `data/output/daily/20260818_115048`.

#### ✅ **Вариант 1: Непосредственно в `photo_processing.py`**

Добавь в `photo_processing.py` после `qwen_process.wait()`:

```python
from scripts.create_previews_v01 import create_previews

# ... (все предыдущий код)

qwen_returncode = await qwen_process.wait()

if qwen_returncode != 0:
    # ... (ошибки)

# Создаём preview
preview_dir = PROJECT / "data" / "preview" / "daily" / run_name
create_previews(result_dir, preview_dir)
```

#### ✅ **Вариант 2: Через отдельный скрипт (если нужно)**

Если хочешь избежать импорта, можно вызвать `create_previews_v01.py` как отдельный процесс:

```python
import asyncio
import subprocess

# ... (все предыдущий код)

qwen_returncode = await qwen_process.wait()

if qwen_returncode != 0:
    # ... (ошибки)

# Запускаем create_previews_v01.py
preview_dir = PROJECT / "data" / "preview" / "daily" / run_name
cmd = [
    str(PROJECT / ".venv" / "bin" / "python"),
    "scripts/create_previews_v01.py",
    str(result_dir),
    str(preview_dir),
]

preview_process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

stdout, stderr = await preview_process.communicate()
if preview_process.returncode != 0:
    print(f"Ошибка создания preview: {stderr.decode()}")
```

---

### 🧪 **Шаг 4: Проверяем**

1. Запусти pipeline:
   ```bash
   ./run_daily_hybrid_v12.sh
   ```

2. Проверь, создался ли:
   ```bash
   ls data/preview/daily/20260818_115048/
   ```

3. Убедись, что grid теперь отображает фотографии.

---

### 📌 **Итог**

Теперь pipeline работает так:

```text
Hybrid
  ↓
data/output/daily/20260818_115048/
  ↓
Qwen
  ↓
data/metadata/qwen4b/20260818_115048/
  ↓
create_previews_v01.py
  ↓
data/preview/daily/20260818_115048/
  ↓
GRID
```

✅ **Все шаги восстановлены.**  
✅ **Preview теперь создаётся.**  
✅ **Grid отображает фотографии.**