### ✅ **Решение: Гость с фильтрами по умолчанию**

#### 🔍 **Шаг 1: Найдём логику инициализации сессии**
Проверим, где определяется "Гость" и как обрабатываются фильтры:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'Гость|guest|password_required|STATE\.manager|set_current_user|get_current_user' \
app/web \
--include="*.py" | head -200
```

#### 🔍 **Шаг 2: Найдём логику фильтров**
Проверим, где создаются чекбоксы и устанавливаются фильтры:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE \
'selected_clients|selected_addresses|selected_period|date_from|date_to|ui\.checkbox|checkbox' \
app/web \
--include="*.py" | head -250
```

#### ✅ **Шаг 3: Добавим логику для гостя**
Если в коде есть `app.storage.user`, то:

```python
if not app.storage.user.get("user_id"):
    # Гость
    app.storage.user["user_id"] = "guest"
    app.storage.user["selected_clients"] = list_of_all_clients
    app.storage.user["selected_addresses"] = list_of_all_addresses
    app.storage.user["selected_period"] = "previous_month"
    app.storage.user["date_from"], app.storage.user["date_to"] = calculate_previous_month()
```

#### 📌 **Пример патча**
Если в `app/web/main.py` есть `ui.run(...)`, то:

```python
from datetime import datetime, timedelta

def calculate_previous_month():
    today = datetime.today()
    first_day_of_month = today.replace(day=1)
    last_day_of_previous_month = first_day_of_month - timedelta(days=1)
    return (
        last_day_of_previous_month.replace(day=1).strftime("%Y-%m-%d"),
        last_day_of_previous_month.strftime("%Y-%m-%d"),
    )

# В `app/web/main.py` после `ui.run(...)`

if not app.storage.user.get("user_id"):
    app.storage.user["user_id"] = "guest"
    app.storage.user["selected_clients"] = list_of_all_clients
    app.storage.user["selected_addresses"] = list_of_all_addresses
    app.storage.user["selected_period"] = "previous_month"
    app.storage.user["date_from"], app.storage.user["date_to"] = calculate_previous_month()
```

#### 🧠 **Важно**
- Убедись, что `list_of_all_clients` и `list_of_all_addresses` определены в твоём коде.
- Если `list_of_all_clients` не существует, замени на `[]` или используй запрос к базе данных.

---

### 📌 **Проверка**
После патча:
1. Открой браузер и проверь, что:
   - Нет сохранённого `user_id` → появляется "Гость".
   - Все чекбоксы отмечены.
   - Период — предыдущий месяц.
2. Проверь логи:
   ```bash
   sudo journalctl -u lora -n 40 --no-pager
   ```

---

### 📌 **Дополнительно**
Если хочешь, чтобы гость не сохранял данные между сессиями, добавь:
```python
app.storage.user.clear()
```
в конец `ui.run(...)`, чтобы стирать сессию при выходе.