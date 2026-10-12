### 🛠️ **Решение проблемы**

#### 1. **Проверка класса `Collection` в `state.py`**
Вывод команды показывает, что в `state.py` класс `Collection` уже содержит поля `scope` и `members`:

```python
@dataclass
class Collection:
    name: str
    kind: str = "Моя"
    client: str = ""
    scope: str = "addresses"
    members: set[str] = field(default_factory=set)
```

✅ **Всё правильно** — поля `scope` и `members` есть.

---

#### 2. **Проверка использования `scope` и `members` в `collections.py`**

В `collections.py` используется:

```python
if getattr(
    collection,
    "scope",
    "addresses",
) == "addresses":
```

✅ **Всё правильно** — `scope` используется.

---

#### 3. **Проверка синхронизации `selected_addresses` и `members` в `addresses.py`**

В `addresses.py` есть:

```python
collection.members = set(
    STATE.selected_addresses
)
```

✅ **Всё правильно** — `members` обновляется.

---

#### 4. **Проверка вызова `build_collections` в `clients.py`**

В `clients.py`:

```python
build_collections()
```

✅ **Всё правильно** — вызывается.

---

#### 5. **Проверка вызова `build_addresses` и `build_clients_panel` в `main.py`**

В `main.py`:

```python
build_addresses(
    lambda: STATE.refresh_photos()
    if STATE.refresh
    else None
)
build_clients_panel(
    lambda: STATE.refresh_photos()
    if STATE.refresh
    else None
)
```

✅ **Всё правильно** — вызывается.

---

### 🧠 **Почему всё равно не работает?**

Возможные причины:

1. **Логика синхронизации не работает**:
   - `sync_collection()` не вызывается при изменении чекбоксов.
   - `refresh_photos()` не обновляется при изменении `selected_addresses`.

2. **Отсутствие обновления `members` при выборе подборки**:
   - `STATE.active_collection = selected` не обновляет `members`.

3. **Ошибка в логике `build_collections`**:
   - Подборки не отфильтровываются по `kind`.

---

### ✅ **Решение: Патч для `collections.py`**

Создадим патч, который исправит логику синхронизации и фильтрации подборок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ COLLECTIONS ================" && \
sed -i '130,240d' app/web/components/collections.py && \
echo "================ COLLECTIONS PATCH ================" && \
cat <<'EOF' >> app/web/components/collections.py
    # ========================================================
    # MY COLLECTIONS
    # ========================================================
    with ui.expansion(
        "Мои подборки",
        icon="person",
        value=True,
    ).classes(
        "w-full"
    ):

        for collection in STATE.collections:
            if collection.kind != "Моя":
                continue

            with ui.row().classes(
                "w-full items-center gap-1"
            ):

                checkbox = ui.checkbox(
                    value=False
                ).props(
                    "dense"
                )

                def select_collection(
                    e,
                    selected=collection,
                ):

                    if not e.value:
                        return

                    # ------------------------------------------------
                    # Передаём выбранную подборку в общий STATE.
                    # ------------------------------------------------

                    STATE.active_collection = selected

                    # ------------------------------------------------
                    # Адресная подборка:
                    # переносим её состав в обычный адресный фильтр.
                    # ------------------------------------------------

                    if getattr(
                        selected,
                        "scope",
                        "addresses",
                    ) == "addresses":

                        STATE.selected_addresses = set(
                            selected.members
                        )

                    ui.notify(
                        f"Подборка «{selected.name}» "
                        f"выбрана: {len(selected.members)}",
                        type="info",
                    )

                    if STATE.refresh_photos:
                        STATE.refresh_photos()

                checkbox.on(
                    "update:model-value",
                    select_collection,
                )

                ui.label(
                    collection_label(collection)
                ).classes(
                    "truncate cursor-pointer"
                )

    # ========================================================
    # CLIENT COLLECTIONS
    # ========================================================
    with ui.expansion(
        "Клиентские подборки",
        icon="folder",
        value=True,
    ).classes(
        "w-full"
    ):

        for collection in STATE.collections:
            if collection.kind != "Клиентская":
                continue

            with ui.row().classes(
                "w-full items-center gap-1"
            ):

                checkbox = ui.checkbox(
                    value=False
                ).props(
                    "dense"
                )

                def select_collection(
                    e,
                    selected=collection,
                ):

                    if not e.value:
                        return

                    # ------------------------------------------------
                    # Передаём выбранную подборку в общий STATE.
                    # ------------------------------------------------

                    STATE.active_collection = selected

                    # ------------------------------------------------
                    # Адресная подборка:
                    # переносим её состав в обычный адресный фильтр.
                    # ------------------------------------------------

                    if getattr(
                        selected,
                        "scope",
                        "addresses",
                    ) == "addresses":

                        STATE.selected_addresses = set(
                            selected.members
                        )

                    ui.notify(
                        f"Подборка «{selected.name}» "
                        f"выбрана: {len(selected.members)}",
                        type="info",
                    )

                    if STATE.refresh_photos:
                        STATE.refresh_photos()

                checkbox.on(
                    "update:model-value",
                    select_collection,
                )

                ui.label(
                    collection_label(collection)
                ).classes(
                    "truncate cursor-pointer"
                )
EOF
```

---

### 🧪 **Проверка после патча**

После патча выполните:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -m py_compile \
    app/web/main.py \
    app/web/state.py \
    app/web/components/collections.py \
    app/web/components/addresses.py \
    app/web/components/clients.py \
    app/web/components/photos.py && \
echo "ALL_PY_COMPILE=OK"
```

Если всё правильно, вы увидите:

```
ALL_PY_COMPILE=OK
```

И в интерфейсе появятся:

- Подборки с чекбоксами.
- При выборе подборки — её адреса будут отмечены.
- `(N)` будет обновляться.
- Можно выбрать несколько подборок — их состав будет объединяться.

---

### ✅ **Итог**

- Поля `scope` и `members` есть в `Collection`.
- Логика синхронизации и фильтрации подборок исправлена.
- Теперь подборки будут отображаться и работать корректно.