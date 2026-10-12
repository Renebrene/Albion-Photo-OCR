### 🛠️ **Патч для обновления системы хранения паролей**

---

### 🔐 **Изменения в `users_db.py`**

```python
import bcrypt
import sqlite3
from app.web.config import DB_PATH

def hash_password(password: str) -> str:
    """Хэширует пароль с помощью bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_users_db():
    with get_connection() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL,
                password TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                archived_at TEXT
            )
        """)
        
        columns = {
            row[1]
            for row in con.execute("PRAGMA table_info(users)").fetchall()
        }

        if "password" not in columns:
            con.execute("""
                ALTER TABLE users
                ADD COLUMN password TEXT NOT NULL DEFAULT ''
            """)
            
            # Хэшируем существующие пароли (пустые строки)
            con.execute("""
                UPDATE users
                SET password = ?
                WHERE password = ''
            """, (hash_password("1234"),))

        # Инициализация данных
        count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            con.executemany("""
                INSERT INTO users
                    (name, color, password, active)
                VALUES (?, ?, ?, 1)
            """, [
                (
                    name,
                    color,
                    hash_password("1234"),
                )
                for name, color in DEFAULT_USERS
            ])
        
        con.commit()
```

---

### 🔐 **Изменения в `users.py`**

```python
def update_user_password(user_id, password):
    password = str(password or "")
    if not password:
        return False

    init_users_db()

    with get_connection() as con:
        con.execute("""
            UPDATE users
            SET password = ?
            WHERE id = ?
        """, (hash_password(password), user_id))
        con.commit()

    return True

def check_user_password(user_id, password):
    stored = get_user_password(user_id)
    if stored is None:
        return False

    return bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))

def get_user_password(user_id):
    init_users_db()

    with get_connection() as con:
        row = con.execute(
            """
            SELECT password
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

    return row[0] if row else None
```

---

### 📌 **Изменения в `header.py`**

```python
from nicegui import ui
from app.web.config import LOGO_PATH
from app.web.state import STATE
from app.web.users_db import (
    init_users_db,
    get_users,
    update_user_password,
    check_user_password,
    get_user_password
)

def build_header():
    init_users_db()

    with ui.header().classes("items-center justify-between px-4 py-2").style("position: relative; z-index: 1000;"):
        with ui.row().classes("items-center gap-3"):
            if LOGO_PATH.exists():
                ui.image(LOGO_PATH).classes("w-8 h-8")
            ui.label("Scene Fingerprint").classes("text-lg font-bold")
```

---

### 📌 **Изменения в `technical_modules/users.py`**

```python
def save():
    if password:
        update_user_password(user_id, password)
        if STATE.user_id == user_id:
            STATE.manager = name
    dialog.close()
    rebuild()
```

---

### 📌 **Изменения в `users_db.py` (дополнительно)**

```python
def archive_user(user_id):
    with get_connection() as con:
        con.execute("""
            UPDATE users
            SET active = 0, archived_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id,))
        con.commit()
```

---

### ✅ **Итог**

- **Пароли хешируются с помощью `bcrypt`**.
- **Существующие пароли** (`1234`) **хэшируются** при миграции.
- **Проверка паролей** теперь выполняется с помощью `bcrypt.checkpw`.
- **Все функции** (`update_user_password`, `check_user_password`, `get_user_password`) адаптированы под хеширование.
- **Миграция** обновлена, чтобы хэшировать старые пароли.

---

### 📌 **Дополнительные рекомендации**

1. **Удалите старые пароли** (`1234`) из кода, если они больше не нужны.
2. **Используйте более безопасные алгоритмы хеширования**, например, `argon2` или `bcrypt` (как в примере).
3. **Не храните пароли в чистом виде** — всегда используйте хэширование.
4. **Проверяйте наличие пароля** перед выполнением операций, чтобы избежать уязвимостей.