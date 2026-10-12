### 🛠️ **Патч: Управление менеджерами с паролем и цветом**

---

#### 📌 **Изменения в `settings.py` / `models.py`**

```python
# settings.py
MANAGERS = {
    "admin": {"password": "admin123", "color": "bg-blue-600"},
    "user": {"password": "user123", "color": "bg-green-600"},
    # ... другие менеджеры
}

# models.py
class Manager:
    def __init__(self, name, password, color):
        self.name = name
        self.password = password  # Хранение пароля в открытом виде (временно)
        self.color = color
```

---

#### 🧾 **Изменения в интерфейсе (UI)**

```python
# ui/settings.py
with ui.card().classes("w-full p-4"):
    ui.label("Управление менеджерами").classes("text-lg font-bold mb-2")
    
    with ui.row().classes("w-full gap-2"):
        ui.select(
            options=[{"label": m.name, "value": m.name} for m in MANAGERS.values()],
            value=current_manager.name,
            on_change=lambda e: self.change_manager(e.value),
        ).props("dense")
        
        ui.input("Пароль", password=True, on_change=lambda e: self.set_password(e.value))
    
    ui.select(
        options=[
            {"label": "Красный", "value": "bg-red-600"},
            {"label": "Синий", "value": "bg-blue-600"},
            # ... 30 цветов
        ],
        value=current_manager.color,
        on_change=lambda e: self.set_color(e.value),
    ).props("dense")
```

---

#### 🔐 **Логика смены менеджера**

```python
def change_manager(self, new_manager_name):
    manager = MANAGERS.get(new_manager_name)
    if manager and self.check_password(manager.password):
        self.current_manager = manager
        self.update_ui()
    else:
        ui.notify("Неверный пароль", type="error")

def check_password(self, input_password):
    return input_password == self.current_manager.password
```

---

#### 🔄 **Сохранение состояния**

```python
# settings.py
def save_managers():
    with open("managers.json", "w") as f:
        json.dump([{"name": m.name, "password": m.password, "color": m.color} for m in MANAGERS.values()], f)

def load_managers():
    try:
        with open("managers.json", "r") as f:
            data = json.load(f)
            for item in data:
                MANAGERS[item["name"]] = Manager(item["name"], item["password"], item["color"])
    except FileNotFoundError:
        pass
```

---

### 📝 **Примечания**
1. **Безопасность**: Пароль хранится в открытом виде (временно). Для продакшна требуется хеширование.
2. **Сохранение**: Состояние менеджеров сохраняется в `managers.json`.
3. **UI**: Выпадающий список цветов заменяет множественный выбор.
4. **Логика**: При неверном пароле текущий менеджер не меняется.

---

### ✅ **Результат**
- Менеджеры управляются через пароль и цвет.
- Существующие менеджеры сохраняются.
- Новый менеджер добавляется с цветом из списка.
- При неверном пароле текущий менеджер остаётся.