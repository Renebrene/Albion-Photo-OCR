### ✅ **Решение проблемы**

#### 1. **Убираем зависимость от `test_sorted_v2`**
В `config.py` изменяем `PHOTO_ROOT` на путь к `daily`:

```python
# app/web/config.py
PHOTO_ROOT = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "daily"
)
```

Это укажет приложению использовать только `daily/20260818_115048` как источник.

---

#### 2. **Обновляем `addresses.py`**
В `addresses.py` убираем статические адреса и используем динамический поиск по `daily`:

```python
# app/web/components/addresses.py
import os
from pathlib import Path

def get_addresses():
    daily_dir = Path("data/output/daily")
    if not daily_dir.exists():
        return []
    # Получаем список подкаталогов (адресов)
    return [d.name for d in daily_dir.iterdir() if d.is_dir()]
```

Теперь список адресов будет автоматически определяться из `daily/`.

---

#### 3. **Обновляем `state.py`**
Убираем статические адреса и используем динамический поиск:

```python
# app/web/state.py
from pathlib import Path

@dataclass
class AppState:
    ...
    addresses: list[str] = field(default_factory=lambda: get_addresses())
```

---

### 🔄 **Проверка**
После этих изменений:

1. **`PHOTO_ROOT`** теперь указывает на `daily/`.
2. **`addresses.py`** и **`state.py`** динамически определяют адреса из `daily/`.
3. **UI** будет отображать правильные адреса и количество фотографий (526).

---

### 🚀 **Далее: Persistent Job Manager для Hybrid + Qwen**
Теперь можно добавить:

- **Persistent progress** (сохранение прогресса после перезапуска).
- **STOP** (возможность остановить обработку).
- **Единый интерфейс** для Hybrid и Qwen.

Сделаем это в следующем шаге.