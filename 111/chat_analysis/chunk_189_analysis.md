### 🚀 **Итог: Использование PostgreSQL для хранения настроек интерфейса**

#### ✅ **1. Подключение к PostgreSQL**
В `config.py` уже есть подключение к PostgreSQL через `DATABASE_URL` или отдельные параметры. Используем существующий пул соединений.

#### ✅ **2. Создание таблицы `user_interface_settings`**
Создадим таблицу в PostgreSQL:

```sql
CREATE TABLE user_interface_settings (
    user_id INTEGER PRIMARY KEY,
    settings_json JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

#### ✅ **3. Загрузка настроек при авторизации**
Изменим `set_current_user(user_id)` в `session.py`, чтобы загружать настройки из PostgreSQL:

```python
from app.web.config import db_pool
from asyncpg import pool

async def set_current_user(user_id):
    # Загрузка настроек из PostgreSQL
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT settings_json FROM user_interface_settings
            WHERE user_id = $1
        """, user_id)
    
    if result:
        app.storage.user_settings = result['settings_json']
    else:
        app.storage.user_settings = {}

    # Остальной код авторизации
    app.storage.user[SESSION_USER_ID] = user_id
```

#### ✅ **4. Сохранение изменений настроек**
Добавим обработку сохранения изменений в `user_interface_settings` при изменении полей в `STATE`:

```python
from app.web.config import db_pool
from asyncpg import pool

async def save_user_settings(user_id, settings):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_interface_settings (user_id, settings_json, updated_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE
            SET settings_json = $2, updated_at = CURRENT_TIMESTAMP
        """, user_id, settings)
```

#### ✅ **5. Интеграция с `STATE`**
Убедимся, что при изменении полей в `STATE` вызывается `save_user_settings`:

```python
# Пример: при изменении selected_clients
app.storage.selected_clients = new_value
await save_user_settings(app.storage.user[SESSION_USER_ID], {
    "selected_clients": new_value,
    # ... другие поля
})
```

#### ✅ **6. Разделение данных**
- **Постоянные настройки** (dark_mode, selected_clients и т.д.) хранятся в PostgreSQL.
- **Временные данные** (photos, search_results) остаются в `STATE`.

---

### 📌 **Итоговая архитектура**
```text
Браузер
   │
   └── cookie → user_id
                    │
                    ▼
              PostgreSQL
          ┌─────────────────┐
          │ users            │
          │ user_settings    │
          └─────────────────┘
                    │
                    ▼
                 STATE
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
       компьютер 1        компьютер 2
       свои настройки      свои настройки
```

---

### 🧪 **Проверка**
1. Убедитесь, что `set_current_user` теперь загружает настройки из PostgreSQL.
2. Проверьте, что изменения в `STATE` сохраняются в `user_interface_settings`.
3. Убедитесь, что при отсутствии `user_id` создаётся Гость с пустыми настройками.

Если всё работает — можно перейти к следующему этапу: **автоматическое сохранение настроек при выходе** или **интеграция с фильтрами**.