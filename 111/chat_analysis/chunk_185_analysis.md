### ✅ **Решение: Интеграция настроек отображения пользователя в грид фотографий**

---

## 🧠 **Общая логика**

1. **Хранение настроек**:
   - Используем `app.storage.user` для хранения настроек отображения (режим, размер, сортировка).
   - По умолчанию: `mode='grid'`, `size=40`, `sort='date'`.

2. **Интеграция в `photos.py`**:
   - Загружаем настройки при инициализации.
   - Применяем их при отрисовке грида.
   - Обновляем грид при изменении настроек.

3. **Обновление грида**:
   - При изменении настроек (например, через UI) вызываем `render_photo_grid()`.

---

## 📁 **Файлы, которые нужно изменить**

1. **`photos.py`** (основной модуль грида)
2. **`main.py`** (авторизация, `app.storage.user`)
3. **`users_db.py`** (дополнительные настройки, если нужно)
4. **`technical_modules/users.py`** (если требуется интеграция с пользовательским интерфейсом)

---

## 🧩 **Изменения в `photos.py`**

### 1. **Загрузка настроек пользователя**

```python
# В начале файла
user_settings = app.storage.user.get('photo_grid_settings', {
    'mode': 'grid',       # 'grid' или 'list'
    'size': 40,           # размер страницы
    'sort': 'date'        # 'date', 'name', 'size'
})
```

### 2. **Интеграция настроек в `render_photo_grid()`**

```python
def render_photo_grid():
    global grid_loaded, grid_requested, grid_status_label

    if not grid_requested:
        return

    all_files = get_filtered_photos()

    if user_settings['mode'] == 'grid':
        # Отображать в режиме сетки
        pass
    elif user_settings['mode'] == 'list':
        # Отображать в режиме списка
        pass

    if user_settings['sort'] == 'date':
        all_files.sort(key=lambda x: x.date)
    elif user_settings['sort'] == 'name':
        all_files.sort(key=lambda x: x.name)
    elif user_settings['sort'] == 'size':
        all_files.sort(key=lambda x: x.size)

    # Остальной код отрисовки грида
    ...
```

### 3. **Обновление грида при изменении настроек**

```python
def update_photo_grid_settings(new_settings):
    app.storage.user['photo_grid_settings'] = new_settings
    render_photo_grid()
```

---

## 🧾 **Интеграция в `main.py` (авторизация)**

```python
# В `main.py`, после авторизации
app.storage.user['photo_grid_settings'] = {
    'mode': 'grid',
    'size': 40,
    'sort': 'date'
}
```

---

## 🔄 **Обновление грида при изменении настроек (через UI)**

Если есть интерфейс для изменения настроек (например, в `technical_modules/users.py`), добавьте обработчик:

```python
def on_settings_change(new_settings):
    update_photo_grid_settings(new_settings)
```

---

## 🧪 **Тестирование**

1. **Проверьте, что грид отображается с учетом настроек**:
   - Откройте интерфейс и измените настройки (режим, размер, сортировка).
   - Убедитесь, что грид обновляется автоматически.

2. **Проверьте сохранение настроек**:
   - Завершите сессию и вернитесь — настройки должны сохраняться в `app.storage.user`.

---

## 📌 **Дополнительные рекомендации**

- Если нужно, добавьте интерфейс для редактирования настроек (например, в `technical_modules/users.py`).
- Убедитесь, что `app.storage.user` корректно работает в вашей среде (например, в FastAPI с `fastapi-users` или `authlib`).
- Если настройки хранятся на сервере, используйте `app.storage.user` для их хранения.

---

## ✅ **Итог**

Теперь грид фотографий будет автоматически отображаться с учетом настроек пользователя, сохраненных в `app.storage.user`. Это обеспечит персонализированный опыт для каждого пользователя, и грид будет корректно отображать фотографии в соответствии с их предпочтениями.