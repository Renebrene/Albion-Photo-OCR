### 🧠 **Анализ и поиск фильтров (UI + STATE)**

Выполняю запрошенные команды, чтобы найти **UI-компоненты** и **состояния** для фильтрации по адресам/клиентам. Это ключ к пониманию, как сейчас работает фильтрация в `scene_fingerprint_mvp_v02`.

---

### 🔍 **1. Поиск UI-компонентов (фильтры, чекбоксы, селекты)**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ FILTER UI LOCATIONS ================" && \
grep -RniE \
'selected_addresses|selected_clients|STATE\.addresses|STATE\.clients|ui\.checkbox|ui\.select|Адрес|Клиент' \
app/web \
--include="*.py" \
| head -400
```

**Ожидаемые результаты:**
- Файлы с `ui.checkbox` или `ui.select` для выбора адресов/клиентов.
- Упоминания `selected_addresses` или `STATE.addresses` в коде.
- Фрагменты, где обновляется список фотографий в зависимости от выбранных фильтров.

---

### 🔍 **2. Поиск состояний (STATE) и переменных**

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ STATE ================" && \
grep -RniE \
'class .*State|selected_addresses|selected_clients|addresses *=|clients *=' \
app/web \
--include="*.py" \
| head -250
```

**Ожидаемые результаты:**
- Класс `State` с полями `selected_addresses`, `selected_clients`.
- Переменные `addresses` и `clients` в коде, возможно, связанные с фильтрацией.
- Логика, которая обновляет `STATE.selected_photos` в зависимости от выбранных адресов/клиентов.

---

### 🧩 **Как это связано с `dino_fingerprint` и `hybrid_final_id`?**

1. **`dino_fingerprint`** — это, вероятно, архивный/диагностический идентификатор, который сейчас используется для отслеживания расхождений между DINO и Hybrid. Он может храниться в `STATE` или в `PHOTO_RECORD_INDEX`.

2. **`hybrid_final_id`** — это, скорее всего, идентификатор, который используется для сопоставления фотографий с адресами/клиентами. Он должен быть связан с `PHOTO_RECORD_INDEX` и `PHOTO_INDEX`.

3. **Фильтрация по адресам/клиентам**:
   - Адреса (`1–99`) из `address_directory` с количеством фото `(0)`, `(5)`, `(127)` и т.д. — это, вероятно, `PHOTO_INDEX` или `PHOTO_RECORD_INDEX`.
   - Клиенты — это те, кто реально присутствует в отобранных фотографиях после фильтрации. Это может быть `STATE.clients` или отдельный индекс.

---

### 🧾 **Что делать дальше?**

1. **Найдите `STATE.addresses` и `STATE.clients`** — это ключ к пониманию, как фильтры работают.
2. **Найдите UI-компоненты** (чекбоксы/селекты) для выбора адресов/клиентов.
3. **Проверьте логику фильтрации** — как `STATE.selected_photos` обновляется на основе выбранных адресов/клиентов.
4. **Убедитесь, что `dino_fingerprint` и `hybrid_final_id` используются корректно** — например, в `PHOTO_RECORD_INDEX` или `PHOTO_INDEX`.

---

### 📌 **Пример возможного кода (предположительно)**

Если найдены следующие фрагменты:

```python
# В STATE
class State:
    selected_addresses = set()
    selected_clients = set()

# В UI
ui.select(label="Адреса", options=addresses, value=STATE.selected_addresses)
ui.select(label="Клиенты", options=clients, value=STATE.selected_clients)

# В логике фильтрации
def update_photos():
    filtered_photos = [
        photo for photo in PHOTO_INDEX
        if photo.address in STATE.selected_addresses and photo.client in STATE.selected_clients
    ]
    STATE.photos = filtered_photos
```

Это будет означать, что фильтрация работает через `STATE.selected_addresses` и `STATE.selected_clients`.

---

### ✅ **Итог**

После выполнения команд и анализа результатов вы получите точное место, где реализованы фильтры по адресам/клиентам. Это позволит:
- Понять, как сейчас работает фильтрация.
- Убедиться, что `dino_fingerprint` и `hybrid_final_id` используются корректно.
- Избежать ненужных изменений в других частях кода.

Если нужно, могу помочь с анализом результатов grep-запросов.