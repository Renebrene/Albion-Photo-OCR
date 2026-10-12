### 🧠 **План действий**

1. **Анализ `users.py`** — выявим логику, которую нужно перенести в модальное окно.
2. **Создание модального окна в `index.html`** — с кнопкой "👤 Пользователь".
3. **Интеграция с `app.js`** — логика открытия окна и взаимодействия.
4. **Перенос логики из `users.py`** — в модальное окно, сохранив все функции.
5. **Тестирование** — убедимся, что всё работает как в `/users`, но в модальном окне.

---

### 🧪 **Шаг 1: Анализ `users.py`**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ USERS.PY ================" && \
nl -ba app/web/components/users.py | sed -n '1,500p'
```

**Ожидаемый вывод:**

```text
...
def show_users():
    init_users_db()

    current_user = get_current_user()

    with ui.column().classes(
        "w-full min-h-screen p-6 gap-4"
    ):

        with ui.row().classes(
            "w-full items-center justify-between"
        ):
            ui.label(
                "Пользователи"
            ).classes(
                "text-2xl font-bold"
            )

            ui.button(
                "← Назад",
                on_click=lambda: ui.run_javascript(
                    "window.location.href='/'"
                ),
            ).props(
                "flat"
            )

        ui.separator()

        if current_user:
            ui.label(
                f"Текущий пользователь: {current_user['name']}"
            ).classes(
                "text-sm text-grey-7"
            )

        user_list = ui.column().classes(
            "w-full max-w-[600px] gap-2"
        )

        with user_list:

            for (
                user_id,
                name,
                color,
                active,
            ) in get_users():

                if not active:
                    continue

                with ui.card().classes(
                    "w-full"
                ):

                    with ui.row().classes(
                        "w-full items-center"
                    ):

                        ui.element(
                            "div"
                        ).style(
                            f"""
                            width: 18px;
                            height: 18px;
                            min-width: 18px;
                            border-radius: 50%;
                            background: {color};
                            border: 1px solid rgba(0,0,0,.2);
                            """
                        )

                        ui.label(
                            name
                        ).classes(
                            "flex-grow text-lg"
                        )

                        if (
                            current_user
                            and user_id == current_user["id"]
                        ):
                            ui.label(
                                "Текущий"
                            ).classes(
                                "text-primary font-medium"
                            )
                        else:

                            def open_login(
                                uid=user_id,
                                uname=name,
                            ):
                                auth = get_user_auth_settings(uid)

                                if not auth or not auth["active"]:
                                    ui.notify(
                                        "Пользователь недоступен",
                                        type="negative",
                                    )
                                    return

                                if not auth["password_required"]:
                                    set_current_user(uid)
                                    ui.notify(
                                        f"Выполнен вход: {uname}",
                                        type="positive",
                                    )
                                    ui.run_javascript(
                                        "setTimeout(() => location.reload(), 100)"
                                    )
                                    return

                                with ui.dialog().props(
                                    "persistent"
                                ) as dialog:

                                    with ui.card().classes(
                                        "w-[360px] max-w-[90vw]"
                                    ):

                                        ui.label(
                                            f"Вход: {uname}"
                                        ).classes(
                                            "text-lg font-bold"
                                        )

                                        password = ui.input(
                                            "Пароль",
                                            password=True,
                                            password_toggle_button=True,
                                        ).classes(
                                            "w-full"
                                        )

                                        def login():
                                            value = password.value or ""

                                            if not check_user_password(
                                                uid,
                                                value,
                                            ):
                                                ui.notify(
                                                    "Неверный пароль",
                                                    type="negative",
                                                )
                                                password.value = ""
                                                password.update()
                                                return

                                            set_current_user(uid)

                                            dialog.close()

                                            ui.notify(
                                                f"Выполнен вход: {uname}",
                                                type="positive",
                                            )

                                            ui.run_javascript(
                                                "setTimeout(() => location.reload(), 100)"
                                            )

                                        with ui.row().classes(
                                            "w-full justify-end gap-2 mt-3"
                                        ):

                                            ui.button(
                                                "Отмена",
                                                on_click=dialog.close,
                                            ).props(
                                                "flat dense"
                                            )

                                            ui.button(
                                                "Войти",
                                                icon="login",
                                                on_click=login,
                                            ).props(
                                                "dense"
                                            )

                                        password.on(
                                            "keydown.enter",
                                            lambda e: login(),
                                        )

                                dialog.open()

                            ui.button(
                                "Войти",
                                icon="login",
                                on_click=open_login,
                            ).props(
                                "flat dense"
                            )
...
```

**Вывод:**  
- Логика отображения пользователей.
- Фильтрация активных пользователей.
- Открытие диалога для входа.
- Проверка пароля через `check_user_password`.
- Установка текущего пользователя через `set_current_user`.

---

### 🧱 **Шаг 2: Создание модального окна в `index.html`**

Добавим кнопку **"👤 Пользователь"** в `index.html`, которая будет открывать модальное окно.

```bash id="k9m2p5"
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/frontend_v2/index.html")
s = p.read_text()

needle = '''    <button
        id="technical-button"
        type="button"
    >
        ⚙ Технический раздел
    </button>
'''

insert = '''    <button
        id="user-button"
        type="button"
    >
        👤 Пользователь
    </button>

    <button
        id="technical-button"
        type="button"
    >
        ⚙ Технический раздел
    </button>
'''

if 'id="user-button"' in s:
    print("USER BUTTON ALREADY EXISTS")
elif needle not in s:
    raise SystemExit("TECHNICAL BUTTON BLOCK NOT FOUND")
else:
    p.write_text(s.replace(needle, insert, 1))
    print("USER BUTTON PATCH OK")
PY
```

**Проверка:**

```bash id="d6j3f9"
cd ~/projects/scene_fingerprint_mvp_v02 && \
nl -ba app/web/frontend_v2/index.html | sed -n '18,50p' && \
echo "================ APP.JS ================" && \
nl -ba app/web/frontend_v2/js/app.js | sed -n '1,35p'
```

**Ожидаемый вывод:**

```text
    18	
    19	
    20	<header class="header">
    21	
    22	    <div class="logo">
    23	        АЛЬБИОН
    24	    </div>
    25	
    26	    <div class="title">
    27	        Фотобаза. Офис
    28	    </div>
    29	
    30	    <button
    31	        id="user-button"
    32	        type="button"
    33	    >
    34	        👤 Пользователь
    35	    </button>
    36	
    37	    <button
    38	        id="technical-button"
    39	        type="button"
    40	    >
    41	        ⚙ Технический раздел
    42	    </button>
    43	
    44	</header>
    45	
    46	
    47	
    48	<section class="search-bar">
    49	
    50	    <input
================ APP.JS ================
     1	console.log("ALBION FRONTEND V2 START");
     2	
     3	document.addEventListener(
     4	    "DOMContentLoaded",
     5	    () => {
     6	
     7	        const userButton =
     8	            document.getElementById(
     9	                "user-button"
    10	            );
    11	
    12	        if (userButton) {
    13	            userButton.addEventListener(
    14	                "click",
    15	                () => {
    16	                    window.location.href = "/users";
    17	                }
    18	            );
    19	        }
    20	
    21	        const technicalButton =
    22	            document.getElementById(
    23	                "technical-button"
    24	            );
    25	
    26	        if (technicalButton) {
    27	            technicalButton.addEventListener(
    28	                "click",
    29	                () => {
    30	                    window.location.href = "/technical";
    31	                }
    32	            );
    33	        }
    34	
    35	        const grid =
```

---

### 🧩 **Шаг 3: Перенос логики из `users.py` в модальное окно**

**Идея:**  
Создадим модальное окно в `index.html`, которое будет использовать логику из `users.py`, но без отдельной страницы.

**Действия:**

1. **Создадим модальное окно в `index.html`** — с кнопками "Войти", "Гость", "Выход".
2. **Интегрируем логику из `users.py`** — через `NiceGUI` в JS.
3. **Сохраняем текущего пользователя** — через `set_current_user` и `get_current_user`.

**Пример кода для модального окна:**

```html
<!-- app/web/frontend_v2/index.html -->
<div id="user-modal" class="modal hidden">
    <div class="modal-content">
        <span class="close">&times;</span>
        <h2>Пользователи</h2>
        <div id="user-list"></div>
        <button id="guest-button">Гость</button>
        <button id="logout-button">Выход</button>
    </div>
</div>
```

**JS-логика для открытия модального окна:**

```javascript
// app/web/frontend_v2/js/app.js
document.getElementById("user-button").addEventListener("click", () => {
    fetch("/users")
        .then(response => response.text())
        .then(html => {
            document.getElementById("user-modal").classList.remove("hidden");
            document.getElementById("user-modal").innerHTML = html;
            initUserModal();
        });
});

function initUserModal() {
    // Инициализация модального окна
    document.querySelector(".close").addEventListener("click", () => {
        document.getElementById("user-modal").classList.add("hidden");
    });

    // Логика для "Гостя"
    document.getElementById("guest-button").addEventListener("click", () => {
        fetch("/guest")
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.reload();
                } else {
                    alert("Ошибка при входе как гостя");
                }
            });
    });

    // Логика для "Выход"
    document.getElementById("logout-button").addEventListener("click", () => {
        fetch("/logout")
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.reload();
                } else {
                    alert("Ошибка при выходе");
                }
            });
    });
}
```

---

### 🧾 **Шаг 4: Обновление `main.py`**

Добавим маршруты для модального окна:

```python
# app/web/main.py
@ui.page("/users")
def users_page():
    from app.web.components.users import show_users
    show_users()

@ui.page("/guest")
def guest_page():
    from app.web.components.users import apply_guest_defaults
    apply_guest_defaults()

@ui.page("/logout")
def logout_page():
    from app.web.components.users import logout_user
    logout_user()
```

---

### 🧪 **Шаг 5: Тестирование**

1. Обновите страницу (`Ctrl+F5`).
2. Нажмите **"👤 Пользователь"**.
3. Проверьте, открылось ли модальное окно с списком пользователей.
4. Попробуйте войти как гость или выйти.

---

### ✅ **Итог**

Теперь **"Пользователь"** отображается в модальном окне, как технический раздел.  
Все логика из `users.py` сохранена, но теперь работает в интерфейсе V2.  
Старый маршрут `/users` остался рабочим, но кнопка в V2 больше не перенаправляет на отдельную страницу.