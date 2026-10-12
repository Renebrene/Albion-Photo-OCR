### ✅ Решение

#### 1. **Исправляем `/technical` — вызываем `show_technical()`**
В `technical.py` нужно изменить маршрут `/technical`, чтобы он вызывал `show_technical()` и возвращался на `/v2` после закрытия.

**Изменения в `technical.py`:**

```python
# technical.py
from nicegui import ui

def show_technical():
    with ui.dialog() as dialog:
        with ui.card():
            ui.label("Технический раздел")
            # Добавь нужные элементы интерфейса
            ui.button("Закрыть", on_click=dialog.close)

    def open_technical():
        dialog.open()

    ui.button("Технический раздел", on_click=open_technical)

    # После закрытия возвращаемся на /v2
    @ui.page("/technical")
    def technical_page():
        show_technical()
        return ui.html("<script>window.location.href = '/v2';</script>")
```

**Объяснение:**
- `show_technical()` отображает модальное окно.
- `@ui.page("/technical")` — обрабатывает маршрут `/technical`.
- После закрытия окна `window.location.href = '/v2'` возвращает пользователя на V2.

---

#### 2. **Переход на `/technical` из V2**
В `app/web/frontend_v2/app.js` изменяем кнопку "Технический раздел" так, чтобы она вызывала `/technical`:

```javascript
// app/web/frontend_v2/app.js
document.getElementById("technical-button").addEventListener("click", () => {
    window.location.href = "/technical";
});
```

**Объяснение:**
- Теперь при клике на кнопку происходит переход на `/technical`, который откроет модальное окно NiceGUI и вернётся обратно на `/v2`.

---

#### 3. **Переход на `/users` (отдельный HTML/JS)**
Если ты хочешь, чтобы "Пользователи" отображался как отдельная страница без NiceGUI, сделай:

**В `main.py`:**
```python
# main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI()

# Монтируем /users как статическую страницу
app.mount("/users", StaticFiles(directory=Path("app/web/users").resolve(), html=True))
```

**В `app/web/users/index.html`:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Пользователи</title>
</head>
<body>
    <h1>Пользователи</h1>
    <!-- Добавь нужный интерфейс -->
</body>
</html>
```

**В `app/web/frontend_v2/app.js`:**
```javascript
document.getElementById("users-button").addEventListener("click", () => {
    window.location.href = "/users";
});
```

**Объяснение:**
- `/users` становится отдельной статической страницей.
- Кнопка "Пользователи" в V2 теперь перенаправляет на `/users`.

---

### ✅ Итог
- **Технический раздел** теперь открывается как модальное окно NiceGUI поверх V2.
- **Пользователи** — отдельная статическая страница без NiceGUI.
- Все изменения минимальны и не ломают текущую логику.

Если нужно, могу помочь с реализацией `build_users()` или `build_data()` в отдельном HTML.