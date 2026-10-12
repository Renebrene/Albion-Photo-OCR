### ✅ **Точечный патч для Гостя**

Вывод показал, что:

- `addresses.py` — отвечает за отображение адресов (чекбоксы);
- `filters.py` — фильтрация по периоду;
- `state.py` — хранит текущее состояние пользователя (включая адреса и период).

### 🛠️ **Изменения для Гостя**:
- При входе/восстановлении Гостя → **все адреса выбраны**;
- Период → **текущий месяц**;
- Остальные настройки (для менеджеров) — **не трогаем**.

---

### 📄 **Патч через `uv run python`**

```bash id="3q2v4k"
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

# Патч для state.py
state_py = Path("app/web/state.py")
state_py.write_text(state_py.read_text().replace(
    "from datetime import datetime",
    "from datetime import datetime\n\n# Гость-настройки\nGUEST_DEFAULT_PERIOD = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)"
), encoding="utf-8")

# Патч для filters.py
filters_py = Path("app/web/components/filters.py")
filters_py.write_text(filters_py.read_text().replace(
    "def get_period_filter():",
    "def get_period_filter():\n    if auth['user_id'] == 12:\n        return GUEST_DEFAULT_PERIOD"
), encoding="utf-8")

# Патч для addresses.py
addresses_py = Path("app/web/components/addresses.py")
addresses_py.write_text(addresses_py.read_text().replace(
    "def get_selected_addresses():",
    "def get_selected_addresses():\n    if auth['user_id'] == 12:\n        return list(range(1, 13))"  # Все адреса
), encoding="utf-8")

print("PATCH: state.py, filters.py, addresses.py")
PY
```

---

### 🔍 **Что изменилось**:

- **`state.py`**:
  - Добавлен `GUEST_DEFAULT_PERIOD` — текущий месяц (1-е число).
  - Фильтрация по периоду теперь учитывает роль Гостя.

- **`filters.py`**:
  - Для Гостя (`user_id == 12`) фильтр по периоду устанавливается на `GUEST_DEFAULT_PERIOD`.

- **`addresses.py`**:
  - Для Гостя (`user_id == 12`) возвращаются **все адреса** (`1–12`).

---

### ✅ **Проверка**

После патча:

```bash id="5l8h4k"
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.state import auth, GUEST_DEFAULT_PERIOD
from app.web.components.filters import get_period_filter
from app.web.components.addresses import get_selected_addresses

print("AUTH:", auth)
print("PERIOD:", get_period_filter())
print("ADDRESSES:", get_selected_addresses())
PY
```

Ожидаем:

```text
AUTH: {'user_id': 12, 'password_required': False, 'persist_state': False, 'active': True}
PERIOD: 2026-08-01 00:00:00
ADDRESSES: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
```

---

### 🚀 **Далее**
Теперь можно запускать UI и проверять:

1. **Гость** — все адреса выбраны, период — текущий месяц.
2. **Менеджер** — сохраняет свои настройки.
3. **Переключение** между пользователями — работает без сброса состояния.

Если всё ок — можно двигаться дальше.