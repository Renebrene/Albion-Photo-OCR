### 🔍 Анализ текущей реализации

#### 1. **Левый список клиентов**
```python
# app/web/components/clients.py
def load_clients():
    return [
        {"id": 1, "name": "Самокат", "simple_name": "Самокат"},
        {"id": 2, "name": "Яндекс", "simple_name": "Яндекс"},
        ...
    ]
```

**Вывод:**  
Список клиентов сейчас формируется **локально** из статического списка. Нужно заменить его на запрос к `client_directory`:

```python
def load_clients():
    cur.execute("SELECT id, name, simple_name FROM client_directory ORDER BY sort_order")
    return cur.fetchall()
```

---

#### 2. **Правый список адресов**
```python
# app/web/components/addresses.py
def load_addresses():
    return [
        {"id": 78, "simple": "Комарова, 13", "legal": "бул. Комарова, 13 В / пр. Космонавтов, сторона Б"},
        ...
    ]
```

**Вывод:**  
Адреса тоже загружаются **локально**. Заменить на запрос к `address_directory`:

```python
def load_addresses():
    cur.execute("SELECT id, simple_address, legal_address FROM address_directory ORDER BY id")
    return cur.fetchall()
```

---

#### 3. **Обновление грида после изменения чекбоксов**
```python
# app/web/components/photos.py
def refresh_photos(selected_clients, selected_addresses):
    # Логика фильтрации по выбранным клиентам и адресам
    ...
```

**Вывод:**  
Текущая логика использует **локальные переменные** `selected_clients` и `selected_addresses`. Нужно заменить их на данные из `manager_selections`:

```python
def refresh_photos():
    cur.execute("""
        SELECT p.*
        FROM photos p
        JOIN manager_selections ms ON p.client_normalized = ms.item_id
        WHERE ms.item_type = 'client'
        AND ms.user_id = :user_id
    """)
    return cur.fetchall()
```

---

### ✅ Действия для реализации

1. **Заменить загрузку клиентов и адресов на запросы к PostgreSQL**  
   - `client_directory` → левый список клиентов  
   - `address_directory` → правый список адресов  

2. **Синхронизировать чекбоксы с `manager_selections`**  
   - Использовать `manager_selections` для определения выбранных клиентов и адресов  
   - Обновлять грид при изменении состояния чекбоксов  

3. **Обновить логику фильтрации фотографий**  
   - Использовать `client_normalized` и `address_id` из `photos`  
   - Связать `manager_selections` с `photos` через `client_normalized`  

---

### 🧠 Пример обновленного кода

#### ✅ Загрузка клиентов
```python
def load_clients():
    cur.execute("SELECT id, name, simple_name FROM client_directory ORDER BY sort_order")
    return cur.fetchall()
```

#### ✅ Загрузка адресов
```python
def load_addresses():
    cur.execute("SELECT id, simple_address, legal_address FROM address_directory ORDER BY id")
    return cur.fetchall()
```

#### ✅ Обновление грида
```python
def refresh_photos(user_id):
    cur.execute("""
        SELECT p.*
        FROM photos p
        JOIN manager_selections ms ON p.client_normalized = ms.item_id
        WHERE ms.item_type = 'client'
        AND ms.user_id = :user_id
    """)
    return cur.fetchall()
```

---

### 🚀 Итог

- **Левый список клиентов** теперь берется из `client_directory`  
- **Правый список адресов** теперь берется из `address_directory`  
- **Грид фотографий** обновляется на основе `manager_selections`  
- **Чекбоксы** сохраняют состояние пользователя в `manager_selections`  

Это позволяет убрать жёстко зашитые адреса и клиенты из UI и сделать систему более гибкой и масштабируемой.