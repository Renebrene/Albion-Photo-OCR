### ✅ **Шаг 2 — `header.py`**

Теперь переделаем логику выбора пользователя. Нужно:

- **Гость** → сразу открывает интерфейс без пароля.
- **Менеджеры** → требуют пароль.
- **Состояние интерфейса** → сохраняется только для менеджеров.
- **При смене пользователя** → старое состояние не сохраняется.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/header.py")
s = p.read_text()

# Найдём блок выбора пользователя
needle = """        # ------------------------------\n        # SELECT USER\n        # ------------------------------"""

# Вставим проверку на Гостя
insert = """        # ------------------------------\n        # SELECT USER\n        # ------------------------------\n\n        # Проверяем, не Гость ли\n        user = self.users[self.current_user]\n        if user['name'] == 'Гость':\n            self.show_user_interface()\n            return\n\n        # Для менеджеров — проверяем пароль\n        user_settings = get_user_auth_settings(self.current_user)\n        if user_settings and user_settings['password_required']:\n            if not self.password_dialog():\n                return\n"""

# Заменяем блок
if needle not in s:
    raise SystemExit("ERROR: needle not found")
s = s.replace(needle, insert, 1)

p.write_text(s)
PY

uv run python -m py_compile app/web/header.py
```

После этого проверь, что `header.py` не сломался:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.header import Header

h = Header()
h.users = [  # Имитация пользователей
    {"id": 1, "name": "Вихляева Алена", "color": "#FFCDD2"},
    {"id": 2, "name": "Пятницына Диана", "color": "#FFEBEE"},
    {"id": 3, "name": "Аннин Илья", "color": "#F8BBD0"},
    {"id": 4, "name": "Иванова Елена", "color": "#F0B27A"},
    {"id": 5, "name": "Марышева Елена", "color": "#FFD580"},
    {"id": 6, "name": "Бутовченко Ольга", "color": "#FFD580"},
    {"id": 7, "name": "Кривошлыкова Ангелина", "color": "#FFD580"},
    {"id": 8, "name": "Теплинская Наталья", "color": "#FFD580"},
    {"id": 9, "name": "Папикян Эля", "color": "#FFD580"},
    {"id": 10, "name": "Путилина Татьяна", "color": "#FFD580"},
    {"id": 11, "name": "Администратор", "color": "#FFD580"},
    {"id": 12, "name": "Гость", "color": "#78909C"},
]

h.current_user = 12  # Проверим Гостя
h.show_user_interface()  # Должен открыться без пароля

h.current_user = 1  # Проверим менеджера
h.show_user_interface()  # Должен запросить пароль
PY
```

Если всё работает — идём к **сохранению состояния**.

---

### 🔐 **Шаг 3 — Сохранение состояния**

В `header.py` найди блок, где сохраняется состояние интерфейса. Обычно это что-то вроде:

```python
def save_state(self):
    ...
```

Изменяем его так:

```python
def save_state(self):
    user_settings = get_user_auth_settings(self.current_user)
    if user_settings and user_settings["persist_state"]:
        # Сохраняем состояние только для менеджеров
        ...
```

И убедись, что при смене пользователя состояние **не переносится**.

---

### 🧪 **Итоговая проверка**

1. **Гость** → входит без пароля, состояние не сохраняется.
2. **Менеджер** → входит с паролем, состояние сохраняется.
3. **Смена пользователя** → старое состояние удаляется.
4. **Повторный вход** → состояние загружается только для текущего пользователя.

Если всё работает — можно запускать приложение. Если возникнут ошибки — пришли вывод.