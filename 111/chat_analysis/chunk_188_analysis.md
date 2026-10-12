### 🧠 **Решение: Хранение настроек интерфейса и ид пользователя на сервере**

#### 📌 **Цель**
- Сохранять настройки интерфейса (выбранные клиенты, даты, сортировка и т.п.) на сервере, чтобы при входе с другого компьютера они были доступны.
- Хранить ид пользователя в куках для удобства, но не хранить пароль.
- Если ид отсутствует, автоматически устанавливать роль "Гость".

---

### 🧩 **Архитектура**

#### 1. **Хранение ид пользователя**
- Ид пользователя хранится в **куках** (`albion_user_id`).
- Если кука отсутствует → пользователь становится **Гостем**.
- Если кука есть → ид используется для поиска в БД.

#### 2. **Настройки интерфейса**
- Хранятся в **БД** (таблица `user_settings`) и связаны с `user_id`.
- Если `user_id` отсутствует (гость) → настройки хранятся в **куках** (`albion_settings`).

#### 3. **Пароль**
- Пароль **не хранится в куках**.
- Если `user_id` есть, но пароль не совпадает → пользователь удаляется из сессии.

---

### 📁 **Пример структуры БД**

```sql
CREATE TABLE user_settings (
    user_id INTEGER,
    selected_clients TEXT,
    selected_addresses TEXT,
    date_from TEXT,
    date_to TEXT,
    date_type TEXT,
    preview_size INTEGER,
    sort_column TEXT,
    sort_direction TEXT,
    view_mode TEXT,
    PRIMARY KEY (user_id)
);
```

---

### 🧾 **Логика работы**

#### 1. **При входе на сайт**
```python
def get_current_user():
    user_id = app.storage.user.get(SESSION_USER_ID)
    if user_id is None:
        return None

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    # Проверяем, есть ли пользователь в БД
    if not check_user_exists(user_id):
        clear_current_user()
        return None

    # Проверяем пароль
    if not is_password_valid(user_id):
        clear_current_user()
        return None

    return get_user_data(user_id)
```

#### 2. **Восстановление настроек**
```python
def restore_settings(user_id):
    if user_id is not None:
        # Пытаемся получить настройки из БД
        settings = get_user_settings(user_id)
        if settings:
            return settings
    else:
        # Если ид отсутствует → гость
        settings = get_guest_settings()

    return settings
```

#### 3. **Сохранение настроек**
```python
def save_settings(user_id, settings):
    if user_id is not None:
        save_to_db(user_id, settings)
    else:
        save_to_cookies(settings)
```

---

### 📦 **Куки для гостя**
- Если ид отсутствует, настройки сохраняются в куках:
  - `albion_settings` (JSON-строка)
  - `albion_user_id` (пустая строка или `None`)
- При следующем входе, если куки есть → восстанавливаем настройки.

---

### 🔐 **Безопасность**
- Ид пользователя хранится в куках, но **не используется для аутентификации**.
- Пароль **не хранится в куках**, а проверяется на сервере.
- Гость не имеет ид и настройки хранятся в куках, но **не сохраняются в БД**.

---

### 📌 **Итог**
- **Ид пользователя** хранится в куках для удобства.
- **Настройки интерфейса** сохраняются в БД (для зарегистрированных) или куках (для гостя).
- **Пароль** не хранится в куках, а проверяется на сервере.
- При входе с другого компьютера настройки восстанавливаются автоматически.

Если нужно, могу помочь с реализацией в коде.