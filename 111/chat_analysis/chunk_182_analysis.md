### ✅ **Шаг 1: Проверка текущей реализации**

Запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ STATE ================" && \
nl -ba app/web/state.py | sed -n '1,360p' && \
echo "================ HEADER AUTH ================" && \
nl -ba app/web/components/header.py | sed -n '1,260p' && \
echo "================ SEARCH ================" && \
nl -ba app/web/components/search.py | sed -n '1,360p' && \
echo "================ USERS DB ================" && \
nl -ba app/web/users_db.py | sed -n '1,360p'
```

Из этого вывода мы увидим:
- Как `STATE.user` устанавливается;
- Как происходит авторизация;
- Как работает поиск и фильтрация;
- Как хранится и загружается пользователь.

---

### ✅ **Шаг 2: Настройка начального состояния**

В `app/web/state.py` найдите часть, где устанавливается `STATE.user`. Добавьте логику:

```python
# app/web/state.py
from pathlib import Path
import json

# Загрузка пользователя из cookie
def load_user_from_cookie():
    cookie_path = Path.home() / ".scene_fingerprint" / "user_cookie.json"
    if cookie_path.exists():
        try:
            with open(cookie_path, "r") as f:
                data = json.load(f)
                user_id = data.get("user_id")
                if user_id and users_db.get(user_id):
                    return users_db[user_id]
        except:
            pass
    return "ГОСТЬ"

# Инициализация состояния
STATE.user = load_user_from_cookie()

# Установка начальных фильтров
if STATE.user == "ГОСТЬ":
    STATE.selected_clients = None
    STATE.selected_addresses = None
    STATE.sort_period = "последний месяц"
else:
    # Если пользователь существует, применяем его настройки
    # (например, STATE.selected_clients = user.default_clients)
    pass
```

---

### ✅ **Шаг 3: Обновление авторизации**

В `app/web/components/header.py` убедитесь, что `STATE.user` корректно отображается. Если нужно, добавьте:

```python
# app/web/components/header.py
def render_user():
    if STATE.user == "ГОСТЬ":
        return "ГОСТЬ"
    else:
        return f"{STATE.user['name']} ({STATE.user['id']})"
```

---

### ✅ **Шаг 4: Проверка и запуск**

После изменений:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
app/web/main.py \
app/web/components/header.py \
app/web/components/search.py \
app/web/state.py \
app/web/users_db.py && \
echo "ALL PYTHON OK"
```

И проверьте в браузере:
- При открытии — `ГОСТЬ`;
- При наличии cookie — загрузка пользователя;
- Все клиенты и адреса выбраны;
- Сортировка — `последний месяц`.

---

### ✅ **Шаг 5: Дополнительные настройки (если нужно)**

Если нужно, добавьте в `app/web/state.py`:

```python
# Установка начальных фильтров
if STATE.user == "ГОСТЬ":
    STATE.selected_clients = None
    STATE.selected_addresses = None
    STATE.sort_period = "последний месяц"
else:
    # Применение настроек пользователя
    STATE.selected_clients = user.default_clients
    STATE.selected_addresses = user.default_addresses
    STATE.sort_period = user.default_period
```

---

### ✅ **Итог**

Теперь:
- При открытии приложения — `ГОСТЬ`;
- Если есть cookie — загрузка пользователя;
- Все клиенты и адреса выбраны;
- Сортировка — `последний месяц`;
- Начальное состояние не перезаписывается.

Если нужно, продолжим с подборок и архивов.