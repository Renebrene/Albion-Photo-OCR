### 🚀 **Первый патч: фильтр периода + единая логика фильтрации**

---

## 🔧 **Изменения в коде**

### 1. **Добавим `period` в `STATE`**

```python
# app/web/state.py
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any

class Period(Enum):
    MONTH = "month"
    YEAR = "year"
    CUSTOM = "custom"

class STATE:
    period: Period = Period.MONTH
    selected_period: Optional[str] = None  # Формат: "YYYY-MM" (месяц) или "YYYY" (год)
    selected_addresses: List[str] = []  # ["78", "82", ...]
    selected_clients: List[str] = []  # ["Яндекс", "Сбер", ...]
    search_query: str = ""
    photo_grid: List[Dict] = []  # Lazy-loaded
    ...
```

---

### 2. **Фильтрация по периоду**

#### ✅ **Источник даты: `imported_at` (дата загрузки)**
Пока не найдено поле с датой фотографии, будем использовать `imported_at` как источник. Это не идеально, но позволяет начать.

#### 📌 **Функция `get_filtered_photos()`**

```python
# app/web/utils.py
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.web.state import STATE
from app.web.db import get_photos  # Предполагаем, что есть функция для запроса к БД

def get_filtered_photos() -> List[Dict]:
    # 1. Получаем все фото
    all_photos = get_photos()

    # 2. Фильтрация по периоду
    if STATE.period == Period.MONTH:
        if not STATE.selected_period:
            # По умолчанию — текущий месяц
            now = datetime.now()
            selected_period = now.strftime("%Y-%m")
        else:
            selected_period = STATE.selected_period
        # Фильтруем по месяцу
        all_photos = [
            photo for photo in all_photos
            if photo["imported_at"].startswith(selected_period)
        ]
    elif STATE.period == Period.YEAR:
        if not STATE.selected_period:
            # По умолчанию — текущий год
            now = datetime.now()
            selected_period = now.strftime("%Y")
        else:
            selected_period = STATE.selected
        # Фильтруем по году
        all_photos = [
            photo for photo in all_photos
            if photo["imported_at"].startswith(selected_period)
        ]

    # 3. Фильтрация по адресам
    if STATE.selected_addresses:
        all_photos = [
            photo for photo in all_photos
            if photo["address"] in STATE.selected_addresses
        ]

    # 4. Фильтрация по клиентам
    if STATE.selected_clients:
        all_photos = [
            photo for photo in all_photos
            if photo["client"] in STATE.selected_clients
        ]

    # 5. Lazy-load: показываем первые 40
    return all_photos[:40]
```

---

### 3. **Интеграция с UI**

#### ✅ **Сохранение выбранного периода**
В `main.py` добавим логику сохранения периода:

```python
# app/web/main.py
from datetime import datetime
from app.web.state import STATE
from app.web.utils import get_filtered_photos

# Пример: обновление периода
def update_period(period: Period, selected_period: str):
    STATE.period = period
    STATE.selected_period = selected_period
    # Обновляем грид
    STATE.photo_grid = get_filtered_photos()
```

#### ✅ **Инициализация периода**
При запуске приложения:

```python
# app/web/main.py
from datetime import datetime
from app.web.state import STATE

# Инициализация периода: по умолчанию — текущий месяц
now = datetime.now()
STATE.selected_period = now.strftime("%Y-%m")
STATE.period = Period.MONTH
```

---

### 4. **Обновление грида при изменении фильтров**

```python
# app/web/main.py
def update_photo_grid():
    STATE.photo_grid = get_filtered_photos()
```

Вызывайте `update_photo_grid()` при изменении любого фильтра (адреса, клиенты, период).

---

## 📌 **Важно**
- Пока используем `imported_at` как дату, но это не идеально. Нужно уточнить, есть ли в БД поле с датой фотографии (например, `taken_at`).
- Подборки и UI будут следующим шагом.
- Lazy-load на 40 фото сохраняется.

---

## 🚀 **Далее**
1. Перестраиваем `main.py` под новый порядок панелей.
2. Добавляем прокрутку списков.
3. Реализуем подборки.
4. Добавляем текстовый поиск и поиск по изображению.

Готов к следующему шагу?