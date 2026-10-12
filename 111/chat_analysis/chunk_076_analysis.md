### 🛠️ **Изменения для адресов + источника фотографий**

#### ✅ **1. Изменяем `config.py`**
Обновляем путь к фотографиям:

```python
# app/web/config.py
PHOTO_ROOT = PROJECT_ROOT / "data" / "output" / "test_sorted_v2"
```

---

#### ✅ **2. Обновляем `state.py`**
Изменяем список адресов и убираем суффикс `_v33`:

```python
# app/web/state.py
@dataclass
class AppState:
    ...

    addresses: list[str] = field(default_factory=lambda: [
        "78_v33",
        "79_v33",
        "80_v33",
        "81_v33",
        "82_v33",
        "83_v33",
        "84_v33",
        "85_v33",
        "86_v33",
        "87_v33",
        "88_v33",
        "89_v33",
        "90_v33",
        "91_v33",
        "92_v33",
        "93_v33",
        "94_v33",
        "95_v33",
    ])

    ...
```

---

#### ✅ **3. Обновляем `addresses.py`**
Изменяем отображение адресов, чтобы показывать только цифры:

```python
# app/web/components/addresses.py
def build_addresses():

    with ui.card().classes(
        "w-full"
    ):

        ui.label(
            "Адреса"
        ).classes(
            "text-lg font-bold"
        )

        ui.label(
            "Фильтр по адресам"
        ).classes(
            "text-sm text-grey-6"
        )

        ui.separator().classes("my-2")

        for address in STATE.addresses:

            # Убираем суффикс _v33
            display_name = address.replace("_v33", "")

            ui.checkbox(
                address,  # Идентификатор (полное имя папки)
                value=address in STATE.selected_addresses,
                on_change=lambda e, a=address:
                    toggle_address(a, e.value),
            ).props(
                "dense"
            ).classes(
                "w-full"
            ).classes(
                f"text-{display_name}"  # Дополнительный стиль (опционально)
            )
```

---

### 🧠 **Что изменилось**
- **Источник фотографий** теперь `data/output/test_sorted_v2` (в `config.py`)
- **Адреса** теперь `78_v33 ... 95_v33` (в `state.py`)
- **Отображение** адресов: пользователь видит `78 ... 95` (в `addresses.py`)
- **Фильтрация** работает через `STATE.selected_addresses`
- **Сохранение выбора** в `STATE` (в `state.py`)

---

### 🚀 **Проверяем**
Запуск:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python app/web/main.py
```

**Ожидаемое поведение:**
- Правая панель показывает `78 ... 95` (без `_v33`)
- Выбор адреса фильтрует центральную галерею
- Выбранные адреса сохраняются в `STATE`
- Фотографии копируются из `data/output/test_sorted_v2` (не перемещаются)

---

### 📌 **Дополнительные шаги**
1. **Дополнительные фильтры** (клиенты, коллекции) — можно добавить в `filters.py`
2. **Сохранение состояния** (localStorage) — можно реализовать в `state.py`
3. **Интеграция с фронтендом** (React/JS) — если планируется переход на JS

Если нужно, могу помочь с любым из этих шагов.