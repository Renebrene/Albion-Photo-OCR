## СЕССИЯ: ФОТОБАЗА ОФИС

**Создано:** 2026-08-16 00:03:58
**Обновлено:** 2026-08-19 21:49:51
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a80d43d-8d70-83ea-8422-7ee2a65807df)

---

### 🤖 **Assistant** — 2026-08-16 14:51:09

Да. Делаем **только оптимизацию текущего UI**, без превью и без изменения backend.

Главное: сейчас при каждом выборе адреса заново создаётся 20–257 карточек и заново создаются `ui.image`. Это и тормозит.

Сделаем так:

- список файлов сканируется **один раз**;
- адрес → фотографии хранится в памяти;
- при фильтрации не сканируем диск;
- галерея всё равно обновляется, но только из уже готового индекса;
- `Все / Снять / чекбоксы` сохраняем как есть;
- оригинальные фотографии остаются оригинальными.

Сначала заменим только `photos.py`.

```bash id="6x0n7c"
cd ~/projects/scene_fingerprint_mvp_v02

cp app/web/components/photos.py \
   app/web/components/photos_before_cache_$(date +%Y%m%d_%H%M%S).py

cat > app/web/components/photos.py <<'PY'
from pathlib import Path

from nicegui import ui

from app.web.config import PHOTO_ROOT
from app.web.state import STATE, Photo

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

# ============================================================
# PHOTO INDEX
# ============================================================

PHOTO_INDEX: dict[str, list[Path]] = {}

def build_photo_index():

    PHOTO_INDEX.clear()

    if not PHOTO_ROOT.exists():
        return

    for address in STATE.addresses:

        folder = PHOTO_ROOT / f"{address}_v33"

        if not folder.exists():
            PHOTO_INDEX[address] = []
            continue

        files = [
            path
            for path in folder.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                in IMAGE_EXTENSIONS
            )
        ]

        files.sort(
            key=lambda p: p.name.lower()
        )

        PHOTO_INDEX[address] = files

def get_all_indexed_photos():

    result = []

    for address in STATE.addresses:
        result.extend(
            PHOTO_INDEX.get(
                address,
                [],
            )
        )

    return result

def get_filtered_photos():

    selected = STATE.selected_addresses

    # Ничего не выбрано = вся база
    if not selected:
        return get_all_indexed_photos()

    result = []

    for address in STATE.addresses:

        if address not in selected:
            continue

        result.extend(
            PHOTO_INDEX.get(
                address,
                [],
            )
        )

    return result

def get_address_count(address):

    return len(
        PHOTO_INDEX.get(
            address,
            [],
        )
    )

# ============================================================
# PHOTO VIEWER
# ============================================================

def open_photo(photo):

    with ui.dialog() as dialog:

        with ui.card().classes(
            "w-[95vw] h-[95vh] "
            "max-w-[1800px] "
            "bg-black p-2"
        ):

            with ui.row().classes(
                "w-full items-center "
                "justify-between"
            ):

                ui.label(
                    photo.path.name
                ).classes(
                    "text-white "
                    "text-sm truncate"
                )

                ui.button(
                    icon="close",
                    on_click=dialog.close,
                ).props(
                    "flat round"
                ).classes(
                    "text-white"
                )

            with ui.element(
                "div"
            ).classes(
                "flex-1 w-full "
                "flex items-center "
                "justify-center "
                "overflow-hidden"
            ):

                ui.image(
                    str(photo.path)
                ).classes(
                    "max-w-full "
                    "max-h-full "
                    "object-contain"
                )

    dialog.open()

def photo_menu(photo):

    with ui.dialog() as dialog:

        with ui.card().classes(
            "min-w-[260px]"
        ):

            with ui.row().classes(
                "w-full items-center "
                "justify-between"
            ):

                ui.label(
                    "Действия с фотографией"
                ).classes(
                    "font-bold"
                )

                ui.button(
                    icon="close",
                    on_click=dialog.close,
                ).props(
                    "flat round dense"
                )

            ui.separator()

            ui.button(
                "Открыть",
                icon="visibility",
                on_click=lambda: (
                    dialog.close(),
                    open_photo(photo),
                ),
            ).props(
                "flat align-left w-full"
            )

            ui.button(
                "Сохранить фото",
                icon="download",
                on_click=lambda: (
                    dialog.close(),
                    ui.notify(
                        "Экспорт будет подключён позже"
                    ),
                ),
            ).props(
                "flat align-left w-full"
            )

            ui.button(
                "Добавить в подборку",
                icon="folder",
                on_click=lambda: (
                    dialog.close(),
                    ui.notify(
                        "Подборки будут подключены позже"
                    ),
                ),
            ).props(
                "flat align-left w-full"
            )

    dialog.open()

# ============================================================
# BUILD PHOTOS
# ============================================================

def build_photos():

    # --------------------------------------------------------
    # Сканируем базу ОДИН РАЗ
    # --------------------------------------------------------

    build_photo_index()

    total_photos = len(
        get_all_indexed_photos()
    )

    print(
        "[PHOTO INDEX]",
        f"addresses={len(PHOTO_INDEX)}",
        f"photos={total_photos}",
        flush=True,
    )

    with ui.column().classes(
        "w-full h-full min-w-0"
    ):

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        with ui.row().classes(
            "w-full items-center "
            "justify-between px-3 py-2"
        ):

            with ui.column().classes(
                "gap-0"
            ):

                ui.label(
                    "Фотографии"
                ).classes(
                    "text-lg font-bold"
                )

                count_label = ui.label().classes(
                    "text-sm text-grey-6"
                )

            with ui.row().classes(
                "items-center gap-1"
            ):

                ui.button(
                    icon="view_module"
                ).props(
                    "flat round"
                )

                ui.button(
                    icon="view_list"
                ).props(
                    "flat round"
                )

                ui.separator().props(
                    "vertical"
                )

                ui.button(
                    icon="sort"
                ).props(
                    "flat round"
                )

                ui.button(
                    icon="filter_list"
                ).props(
                    "flat round"
                )

        ui.separator()

        # ----------------------------------------------------
        # TOOLBAR
        # ----------------------------------------------------

        with ui.row().classes(
            "w-full items-center "
            "px-3 py-2 gap-2"
        ):

            ui.label(
                "Фильтрация по адресам"
            ).classes(
                "text-sm text-grey-7"
            )

            ui.separator().props(
                "vertical"
            )

            ui.button(
                "Скачать выбранные",
                icon="download",
            ).props(
                "flat dense"
            )

            ui.button(
                "Скачать все",
                icon="archive",
            ).props(
                "flat dense"
            )

            ui.button(
                "В подборку",
                icon="folder",
            ).props(
                "flat dense"
            )

            ui.button(
                "Сохранить поиск",
                icon="bookmark",
            ).props(
                "flat dense"
            )

        ui.separator()

        # ----------------------------------------------------
        # SCROLL AREA
        # ----------------------------------------------------

        with ui.scroll_area().classes(
            "w-full flex-grow"
        ):

            @ui.refreshable
            def photo_grid():

                files = get_filtered_photos()

                STATE.photos = [
                    Photo(path)
                    for path in files
                ]

                count_label.text = (
                    f"{len(files)} "
                    f"фотографий в тестовой базе"
                )

                if not files:

                    with ui.column().classes(
                        "w-full "
                        "items-center "
                        "justify-center "
                        "p-12"
                    ):

                        ui.icon(
                            "photo_library",
                            size="64px",
                        ).classes(
                            "text-grey-5"
                        )

                        ui.label(
                            "Фотографий нет"
                        ).classes(
                            "text-grey-6"
                        )

                    return

                with ui.grid(
                    columns=4
                ).classes(
                    "w-full p-3 gap-3"
                ):

                    for photo in STATE.photos:

                        with ui.card().classes(
                            "overflow-hidden "
                            "cursor-pointer "
                            "hover:shadow-lg"
                        ):

                            # ----------------------------
                            # IMAGE
                            # ----------------------------

                            with ui.element(
                                "div"
                            ).classes(
                                "relative "
                                "w-full h-44 "
                                "bg-grey-2 "
                                "flex items-center "
                                "justify-center"
                            ).on(
                                "contextmenu.prevent",
                                lambda e, p=photo:
                                    photo_menu(p),
                            ):

                                ui.image(
                                    str(photo.path)
                                ).classes(
                                    "w-full h-full "
                                    "object-contain"
                                ).on(
                                    "click",
                                    lambda e, p=photo:
                                        open_photo(p),
                                )

                            # ----------------------------
                            # NAME
                            # ----------------------------

                            with ui.row().classes(
                                "w-full "
                                "items-center "
                                "px-2 pt-1"
                            ):

                                ui.checkbox(
                                    value=False
                                ).props(
                                    "dense"
                                )

                                ui.label(
                                    photo.path.name
                                ).classes(
                                    "font-medium "
                                    "text-sm truncate"
                                )

                            # ----------------------------
                            # ADDRESS
                            # ----------------------------

                            ui.label(
                                photo.path.parent.name.replace(
                                    "_v33",
                                    "",
                                )
                            ).classes(
                                "px-2 pb-2 "
                                "text-xs text-grey-6"
                            )

            # Первичная отрисовка
            photo_grid()

    # --------------------------------------------------------
    # CALLBACK FOR ADDRESS FILTER
    # --------------------------------------------------------

    def refresh_photos():

        photo_grid.refresh()

    return refresh_photos
PY
```

Теперь проверяем:

```bash id="d3q9rb"
uv run python -m py_compile \
    app/web/components/photos.py \
    app/web/components/addresses.py \
    app/web/main.py
```

И запускаем:

```bash id="j9g2pn"
uv run python app/web/main.py
```

В терминале при старте должно быть примерно:

```text
[PHOTO INDEX] addresses=18 photos=257
```

### Что должно измениться

При первом открытии UI один раз читаются:

```text
78_v33 ... 95_v33
```

После этого при клике:

```text
78
```

мы **не обращаемся к диску**, а берём уже готовый список:

```text
PHOTO_INDEX["78"]
```

Поэтому переключение адресов должно стать ощутимо быстрее.

И ещё важное: **оригиналы пока остаются как есть**. Никакого создания 257 дополнительных файлов мы сейчас не делаем.

Если после этого всё ещё будет заметная задержка, следующим шагом оптимизируем уже саму **отрисовку 257 карточек** — это отдельная проблема, и там есть несколько вариантов без введения превью.

---

### 👤 **User** — 2026-08-16 14:51:57

ок

---

### 🤖 **Assistant** — 2026-08-16 14:51:58

Отлично. Тогда **превью пока замораживаем**, а текущую архитектуру оставляем.

Следующий логичный этап — не трогая распознавание и backend, довести UI до рабочего состояния:

1. **Клиенты** — добавить / архивировать.
2. **Подборки** — создание и сохранение результатов поиска.
3. **Техническое окно** — адреса, переименование адресов, менеджеры.
4. **Фото** — ПКМ, открытие оригинала, выбор нескольких фото.
5. **Экспорт подборки** — в ZIP/папку.
6. После этого уже подключаем реальные результаты `output` вместо тестовой базы `input/test`.

И главное — **сейчас не меняем v33 и рабочий pipeline распознавания**.

---

### 👤 **User** — 2026-08-16 14:52:39

у нас уже есть описания фотографий от qwen 4B

---

### 🤖 **Assistant** — 2026-08-16 14:52:40

Да, это важно. **Не нужно заново получать описания — Qwen 4B уже сделал эту работу.**

Значит, в нашей архитектуре стоит использовать существующие описания как готовые метаданные фотографий.

Для каждой фотографии в итоге желательно иметь:

```text
фото
├── оригинал
├── адрес
├── дата/время
├── описание Qwen 4B
├── embedding / результаты v33
└── технические метаданные
```

И это особенно полезно для будущего UI:

- при открытии фотографии показывать **описание Qwen**;
- поиск можно будет делать не только по адресу/слепку, но и по описанию;
- можно будет искать что-то вроде **«красный баннер возле здания»**;
- результаты Qwen можно использовать при формировании подборок;
- при экспорте фотоотчёта описание можно сохранять в CSV/JSON.

**Сейчас я бы ничего нового не генерировал.** Надо сначала найти, **где именно у нас уже лежат результаты Qwen 4B и в каком формате**, чтобы подключить их к UI.

Давай следующим шагом найдём существующие файлы с описаниями Qwen 4B.

---

### 👤 **User** — 2026-08-16 14:52:51

lfdfq

---

### 🤖 **Assistant** — 2026-08-16 14:52:52

Давай. Найдём существующие результаты Qwen 4B, ничего не меняя.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== QWEN 4B FILES ==="
find . -type f \
  \( -iname "*qwen*" -o -iname "*caption*" -o -iname "*description*" \) \
  -not -path "./.venv/*" \
  -not -path "./.git/*" \
  -print | sort

echo
echo "=== QWEN REFERENCES IN CODE ==="
grep -RniE "qwen4b|qwen.*4b|caption|description" \
  scripts app data \
  --include="*.py" \
  --include="*.json" \
  --include="*.csv" \
  --include="*.jsonl" \
  2>/dev/null | head -200
```

И отдельно посмотрим, какие файлы вообще появились в `data/output`:

```bash
echo
echo "=== OUTPUT ==="
find data/output -maxdepth 3 -type f -printf "%p\n" \
  2>/dev/null | sort | head -200
```

Пришли вывод. По нему определим **точный источник описаний Qwen 4B** и подключим его к карточке фотографии, не затрагивая распознавание v33.

---

### 👤 **User** — 2026-08-16 14:54:11

nfv ,jkmijq dsdjl yflj cjhnbhjdfnm

---

### 🤖 **Assistant** — 2026-08-16 14:54:13

Понял 🙂 **там большой вывод, надо сортировать**, чтобы не тащить всё подряд.

Давай сразу ищем только то, что относится к **Qwen 4B и описаниям**, без огромного вывода:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== QWEN 4B ==="

find data scripts app -type f \
  \( -iname "*qwen*4b*" -o -iname "*qwen4b*" \) \
  -not -path "*/.venv/*" \
  -print | sort
```

Потом:

```bash
echo
echo "=== DESCRIPTION / CAPTION FILES ==="

find data -type f \
  \( -iname "*.json" -o -iname "*.jsonl" -o -iname "*.csv" -o -iname "*.txt" \) \
  -print \
  | grep -Ei 'qwen|caption|description|describe|annotation' \
  | sort
```

И самое полезное — **посмотреть только названия файлов и размеры**:

```bash
echo
echo "=== POSSIBLE QWEN DATA ==="

find data -type f \
  \( -iname "*qwen*" -o -iname "*caption*" -o -iname "*description*" \) \
  -printf "%s %p\n" \
  2>/dev/null \
  | sort -n \
  | tail -50
```

Этого достаточно. **Не будем пока grep-ать весь проект**.

---

### 👤 **User** — 2026-08-16 14:54:34

ice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "=== DESCRIPTION / CAPTION FILES ==="

find data -type f \
  $ -iname "*.json" -o -iname "*.jsonl" -o -iname "*.csv" -o -iname "*.txt" $ \
  -print \
  | grep -Ei 'qwen|caption|description|describe|annotation' \
  | sort

=== DESCRIPTION / CAPTION FILES ===
data/banner_database/model_compare_v02/Screenshot from 2026-08-16 00-38-11/qwen3-vl_2b-instruct.json
data/banner_database/model_compare_v02/Screenshot from 2026-08-16 00-38-11/qwen3-vl_4b-instruct.json
data/banner_database/model_compare_v04/Screenshot from 2026-08-16 00-38-11/qwen2.5vl_3b.json
data/banner_database/model_compare_v04/Screenshot from 2026-08-16 00-38-11/qwen3-vl_2b-instruct.json
data/banner_database/model_compare_v04/Ашхабадский_01/qwen2.5vl_3b.json
data/banner_database/model_compare_v04/Ашхабадский_01/qwen3-vl_2b-instruct.json
data/banner_database/model_compare_v05/Screenshot from 2026-08-16 00-38-11/qwen3-vl_2b-instruct.json
data/banner_database/model_compare_v05/Ашхабадский_01/qwen3-vl_2b-instruct.json
data/banner_database/model_compare_v05/Ашхабадский_02/qwen3-vl_2b-instruct.json
data/banner_database/model_compare_v05/Ашхабадский_03/qwen3-vl_2b-instruct.json
data/banner_database/model_compare_v05/Ашхабадский_04/qwen3-vl_2b-instruct.json
data/banner_database/model_compare_v05/Ашхабадский_05/qwen3-vl_2b-instruct.json
data/banner_database/model_compare_v05/Ашхабадский_06/qwen3-vl_2b-instruct.json
data/banner_database/qwen25vl_test_v01/Screenshot from 2026-08-16 00-38-11.json
data/banner_database/qwen25vl_test_v01/summary.json
data/banner_database/qwen25vl_test_v01/Ашхабадский_01.json
data/banner_database/qwen25vl_test_v01/Ашхабадский_02.json
data/banner_database/qwen25vl_test_v01/Ашхабадский_03.json
data/banner_database/qwen25vl_test_v01/Ашхабадский_04.json
data/banner_database/qwen25vl_test_v01/Ашхабадский_05.json
data/banner_database/qwen25vl_test_v01/Ашхабадский_06.json
data/banner_database/qwen25vl_test_v01/Ашхабадский_07.json
data/banner_database/qwen25vl_test_v01/Ашхабадский_08.json
data/banner_database/qwen25vl_test_v01/Ашхабадский_09.json
data/banner_database/qwen4b_test_v01/Screenshot from 2026-08-16 00-38-11.json
data/banner_database/qwen4b_test_v01/summary.json
data/banner_database/qwen4b_test_v01/Ашхабадский_01.json
data/banner_database/qwen4b_test_v01/Ашхабадский_02.json
data/banner_database/qwen4b_test_v01/Ашхабадский_03.json
data/banner_database/qwen4b_test_v01/Ашхабадский_04.json
data/banner_database/qwen4b_test_v01/Ашхабадский_05.json
data/banner_database/qwen4b_test_v01/Ашхабадский_06.json
data/banner_database/qwen4b_test_v01/Ашхабадский_07.json
data/banner_database/qwen4b_test_v01/Ашхабадский_08.json
data/banner_database/qwen4b_test_v01/Ашхабадский_09.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 14:54:36

Да, нашли. У нас уже есть **готовая база описаний Qwen 4B**:

```text
data/banner_database/qwen4b_test_v01/
```

В ней есть описания как минимум для:

```text
Ашхабадский_01
Ашхабадский_02
...
Ашхабадский_09
Screenshot from 2026-08-16 00-38-11
```

И `summary.json`.

При этом есть ещё более свежие результаты сравнений:

```text
data/banner_database/model_compare_v02/
data/banner_database/model_compare_v04/
data/banner_database/model_compare_v05/
```

Но **сейчас их смешивать не будем**. Для первого подключения UI логичнее использовать именно `qwen4b_test_v01`.

### Следующий шаг

Посмотрим структуру **одного JSON**, чтобы понять точное поле с описанием и как привязать его к имени фотографии:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== QWEN 4B SAMPLE ==="

uv run python - <<'PY'
import json
from pathlib import Path

root = Path("data/banner_database/qwen4b_test_v01")

files = sorted(
    p for p in root.glob("*.json")
    if p.name != "summary.json"
)

print("FILES:", len(files))
print()

if files:
    p = files[0]

    print("FILE:", p)
    print()

    data = json.loads(
        p.read_text(encoding="utf-8")
    )

    print(json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    ))
PY
```

**Ничего не меняем.** Просто посмотрим формат.

После этого сможем сделать так, чтобы при открытии фотографии UI показывал:

> **Описание сцены**  
> текст, полученный Qwen 4B

А позже это же описание станет частью поиска по базе.

---

### 👤 **User** — 2026-08-16 14:54:59

=== QWEN 4B SAMPLE ===
FILES: 10

FILE: data/banner_database/qwen4b_test_v01/Screenshot from 2026-08-16 00-38-11.json

{
  "client": "Единая Россия",
  "brand": "Дмитрий Сизякин",
  "category": "выборы",
  "text": [
    "ВЫБОРЫ В ГОСУДАРСТВЕННУЮ ДУМУ РОССИИ",
    "18 — 19 — 20 СЕНТЯБРЯ",
    "ДМИТРИЙ СИЗЯКИН",
    "ГЛАВНЫЙ ВРАЧ ЦГБ ИМ. СЕМАШКО",
    "ПОМОГАТЬ",
    "КАЖДОМУ!",
    "СИЗЯКИН РФ"
  ],
  "colors": [
    "синий",
    "белый",
    "красный"
  ],
  "objects": [
    "портрет мужчины в белом халате и галстуке",
    "логотип Единой России",
    "надпись «ПОМОГАТЬ КАЖДОМУ!»",
    "надпись «СИЗЯКИН РФ»"
  ],
  "description": "Баннер синего цвета с белым и красным текстом. На баннере изображен мужчина в белом халате и галстуке, предположительно врач. В левом верхнем углу — логотип партии «Единая Россия». Вверху — надпись «ВЫБОРЫ В ГОСУДАРСТВЕННУЮ ДУМУ РОССИИ» и даты «18 — 19 — 20 СЕНТЯБРЯ». Под названием кандидата — его должность. Центральная часть баннера содержит лозунг «ПОМОГАТЬ КАЖДОМУ!» в белом и красном цветах. Также присутствует надпись «СИЗЯКИН РФ». Внизу баннера — небольшой текст, который нечитаем. Баннер установлен на улице, видны провода и дорожный знак.",
  "confidence": 95,
  "_time_sec": 16.46
}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 14:55:03

Отлично. Формат очень удачный — **Qwen 4B уже даёт почти полноценную карточку фотографии**.

Получаем:

- `client` — клиент
- `brand` — бренд/кандидат
- `category` — категория
- `text[]` — распознанный текст
- `colors[]` — цвета
- `objects[]` — объекты
- `description` — человеческое описание сцены
- `confidence` — уверенность
- `_time_sec` — время обработки

### Я бы пока подключил это только к просмотру фотографии

То есть карточка в галерее остаётся лёгкой:

```text
┌──────────────────────┐
│                      │
│       ФОТО           │
│                      │
├──────────────────────┤
│ Ашххабадский_01.JPG  │
│ 78                   │
└──────────────────────┘
```

А при открытии фотографии:

```text
┌─────────────────────────────────────────────┐
│              ФОТОГРАФИЯ                     │
│                                             │
│                                             │
│                                             │
├─────────────────────────────────────────────┤
│ Клиент: Единая Россия                       │
│ Бренд: Дмитрий Сизякин                      │
│ Категория: выборы                            │
│                                             │
│ Описание                                    │
│ Баннер синего цвета с белым и красным...    │
│                                             │
│ Объекты                                     │
│ • портрет мужчины...                        │
│ • логотип Единой России                     │
│ • надпись «ПОМОГАТЬ КАЖДОМУ!»              │
│                                             │
│ Текст                                       │
│ ВЫБОРЫ В ГОСУДАРСТВЕННУЮ ДУМУ РОССИИ       │
│ ...                                         │
└─────────────────────────────────────────────┘
```

### Но есть один важный вопрос

Сейчас JSON называется:

```text
Ашххабадский_01.json
```

а фотография:

```text
Ашххабадский_01.JPG
```

То есть привязка по имени уже очевидна. **Это очень хорошо.**

Но у нас в `input/test` **257 фотографий**, а Qwen 4B сейчас описал только 10. Поэтому UI должен спокойно работать так:

```text
есть Qwen JSON → показать описание
нет Qwen JSON → просто не показывать блок описания
```

Никаких ошибок и повторного запуска Qwen.

### Предлагаю следующий шаг

Сделать отдельный маленький модуль:

```text
app/web/services/qwen_metadata.py
```

Он будет отвечать только за:

```text
фотография
    ↓
найти соответствующий JSON
    ↓
загрузить metadata
```

`photos.py` при этом не будет знать, **где и как хранятся Qwen-данные**.

Это как раз соответствует нашей идее модульного frontend/backend.

И потом этот же модуль можно будет использовать для поиска:

**текст → Qwen metadata → фотографии**

а также:

**«покажи фотографии с красным баннером» → objects/colors/description.**

Я бы сейчас именно так и сделал — **подключил Qwen 4B к окну просмотра, но пока не трогал поиск.**

---

### 👤 **User** — 2026-08-16 14:55:49

может быть прогнать qwen по всему outpet

---

### 🤖 **Assistant** — 2026-08-16 14:55:49

Да. Более того, **это сейчас имеет смысл**, но я бы не запускал Qwen 4B просто «по всем файлам output» без структуры.

У нас уже есть:

```text
input/test
   ↓
v33 распознавание
   ↓
78_v33 ... 95_v33
   ↓
output / отсортированные фотографии
```

И логично сделать второй слой:

```text
отсортированное фото
        ↓
     Qwen 4B
        ↓
  metadata JSON
```

### Что это нам даст

После полного прогона каждая фотография сможет иметь:

- клиент;
- бренд;
- категорию;
- весь текст с баннера;
- цвета;
- объекты;
- описание сцены;
- confidence;
- время обработки.

И тогда UI уже будет работать не просто как **фотогалерея**, а как база данных.

Например:

> «Покажи фотографии Самоката с красным баннером»

можно будет искать по:

```text
client
brand
category
colors
objects
text
description
```

А Qwen **не надо будет запускать при каждом поиске** — всё уже сохранено.

### Но есть важный момент

Я бы сначала проверил, **что именно сейчас лежит в output** и сколько там фотографий.

У нас предыдущий тест дал:

```text
257 фотографий
78_v33 ... 95_v33
```

Если это именно тот набор, который хотим использовать как первую рабочую базу, можно прогнать его полностью.

Сначала безопасная проверка:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== OUTPUT ==="

find data/output -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  | wc -l

echo
find data/output -maxdepth 2 -type d | sort
```

И отдельно:

```bash
echo
echo "=== QWEN SCRIPT ==="

sed -n '1,280p' scripts/banner_qwen4b_test_v01.py
```

**Пока ничего не запускаем.**

Посмотрим на текущий скрипт Qwen 4B — возможно, он уже умеет проходить папку, и тогда мы просто сделаем аккуратный вариант `qwen4b_output_v01`, который:

1. проходит весь `output`;
2. сохраняет JSON рядом в отдельную metadata-базу;
3. не перезаписывает уже обработанные фотографии;
4. умеет продолжить после остановки;
5. показывает прогресс;
6. не трогает сами фотографии.

Это будет намного правильнее, чем привязывать Qwen непосредственно к UI.

---

### 👤 **User** — 2026-08-16 14:56:17

=== OUTPUT ===
261

data/output
data/output/banner_candidates
data/output/banner_candidates/видео_сизякин
data/output/banner_debug
data/output/banner_debug/Ashhabadskiy_01
data/output/banner_search
data/output/banner_search_v03_2
data/output/banner_search_v03_3
data/output/banner_search_v03_3/Ашхабадский_17
data/output/banner_search_v03_3/Вавилова52_12
data/output/banner_search_v03_3/Добровольского17_07
data/output/banner_search_v03_3/Зорге_02
data/output/banner_search_v03_3/Зорге_14
data/output/banner_search_v03_3/КА_04
data/output/banner_search_v03_3/Комарова13_06
data/output/banner_search_v03_3/Комарова13_20
data/output/banner_search_v03_3/Ленина125_06
data/output/banner_search_v03_3/Малиновского(_05
data/output/banner_search_v03_3/Малиновского_к_Доватора_01
data/output/banner_search_v03_3/Малиновского_к_Доватора_04
data/output/banner_search_v03_3/Малиновского_к_Доватора_06
data/output/banner_search_v03_3/Малиновского_к_Доватора_15
data/output/banner_search_v03_3/Малиновского_к_Стачки_05
data/output/banner_search_v03_3/Нагибина24_01
data/output/banner_search_v03_3/Нагибина24_06
data/output/banner_search_v03_3/Нагибина24_11
data/output/banner_search_v03_3/Радиаторный_02
data/output/banner_search_v03_3/Радиаторный_05
data/output/banner_search_v03_3/Радиаторный_14
data/output/banner_search_v03_3/Радиаторный_22
data/output/banner_search_v03_3/Радиаторный_23
data/output/banner_search_v03_3/Стачки_41_01
data/output/banner_search_v03_3/Стачки_41_03
data/output/banner_search_v03_3/Стачки_41_07
data/output/banner_search_v03_3/Шеболдаева8_05
data/output/banner_search/Ашхабадский_01
data/output/banner_search/Ашхабадский_17
data/output/banner_search/Вавилова52_12
data/output/banner_search/Добровольского17_07
data/output/banner_search/Зорге_02
data/output/banner_search/Зорге_14
data/output/banner_search/КА_04
data/output/banner_search/Комарова13_06
data/output/banner_search/Малиновского(_05
data/output/banner_search/Малиновского_к_Доватора_04
data/output/banner_search/Малиновского_к_Доватора_06
data/output/banner_search/Малиновского_к_Доватора_15
data/output/banner_search/Малиновского_к_Стачки_05
data/output/banner_search/Радиаторный_02
data/output/banner_search/Радиаторный_05
data/output/banner_search/Радиаторный_14
data/output/banner_search/Радиаторный_22
data/output/banner_search/Радиаторный_23
data/output/banner_search/Стачки_41_01
data/output/banner_search/Стачки_41_03
data/output/banner_search/Стачки_41_07
data/output/banner_search/Шеболдаева8_05
data/output/benchmark_sub_exp
data/output/benchmark_v1
data/output/check_visual
data/output/check_visual/hybrid_v12
data/output/check_visual/v33
data/output/found_banners
data/output/found_banners/18_19_20
data/output/found_banners_debug
data/output/found_banners_debug/Screenshot from 2026-08-16 00-38-11
data/output/found_banners_debug/видео_сизякин
data/output/found_banners/Ozon
data/output/found_banners/Screenshot from 2026-08-16 00-13-31
data/output/found_banners/Screenshot from 2026-08-16 00-22-23
data/output/found_banners/Screenshot from 2026-08-16 00-22-42
data/output/found_banners/Screenshot from 2026-08-16 00-23-32
data/output/found_banners/бетсити
data/output/found_banners/Бетсити
data/output/found_banners/видео_сизякин
data/output/found_banners/выборы
data/output/found_banners/купер
data/output/found_banners/сизякин
data/output/found_banners/яндекс
data/output/test_sorted_v2
data/output/test_sorted_v2/78_v33
data/output/test_sorted_v2/79_v33
data/output/test_sorted_v2/80_v33
data/output/test_sorted_v2/81_v33
data/output/test_sorted_v2/82_v33
data/output/test_sorted_v2/83_v33
data/output/test_sorted_v2/84_v33
data/output/test_sorted_v2/85_v33
data/output/test_sorted_v2/86_v33
data/output/test_sorted_v2/87_v33
data/output/test_sorted_v2/88_v33
data/output/test_sorted_v2/89_v33
data/output/test_sorted_v2/90_v33
data/output/test_sorted_v2/91_v33
data/output/test_sorted_v2/92_v33
data/output/test_sorted_v2/93_v33
data/output/test_sorted_v2/94_v33
data/output/test_sorted_v2/95_v33

---

### 🤖 **Assistant** — 2026-08-16 14:56:18

Вот теперь картина ясная. **Не надо прогонять Qwen по всему `data/output` целиком.** Там лежат разные экспериментальные результаты и дубликаты.

Для нашей рабочей базы сейчас есть один правильный источник:

```text
data/output/test_sorted_v2/
├── 78_v33
├── 79_v33
├── ...
└── 95_v33
```

И именно его я бы взял для Qwen 4B.

У тебя там должно быть **257 фотографий**, которые мы только что рассортировали v33. Остальные 4 файла в `data/output` — это другие результаты/эксперименты.

### Предлагаю структуру

Не смешивать JSON с фотографиями:

```text
data/
├── output/
│   └── test_sorted_v2/
│       ├── 78_v33/
│       ├── 79_v33/
│       └── ...
│
└── metadata/
    └── qwen4b/
        ├── 78_v33/
        ├── 79_v33/
        └── ...
```

Например:

```text
78_v33/
    Ашхабадский_01.JPG
```

получает:

```text
metadata/qwen4b/78_v33/
    Ашхабадский_01.json
```

Так мы **не портим output**, а метаданные становятся самостоятельным слоем базы.

### И самое важное

Уже существующие 10 JSON из:

```text
data/banner_database/qwen4b_test_v01/
```

можно будет использовать как **готовые результаты**, чтобы не гонять эти 10 фотографий повторно.

То есть будущий скрипт должен работать по принципу:

```text
257 фото
   │
   ├── JSON уже существует → пропустить
   │
   └── JSON нет → Qwen 4B
```

И запуск можно будет прервать в любой момент и продолжить.

---

Но прежде чем писать новый скрипт, я хочу проверить **текущий `banner_qwen4b_test_v01.py`**. Возможно, там уже есть хороший код работы с Qwen, и мы просто адаптируем его под `test_sorted_v2`, вместо того чтобы писать второй независимый механизм.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,320p' scripts/banner_qwen4b_test_v01.py
```

Пришли вывод. После этого дам **готовую команду создания рабочего скрипта для полного прогона 78–95**.

---

### 👤 **User** — 2026-08-16 14:56:48

=== QWEN SCRIPT ===
#!/usr/bin/env python3

import base64
import json
import time
from pathlib import Path

import requests

INPUT_DIR = Path("data/input/test")
OUTPUT_DIR = Path("data/banner_database/qwen4b_test_v01")

MODEL = "qwen3-vl:4b-instruct"

OLLAMA_URL = "http://localhost:11434/api/chat"

LIMIT = 10
NUM_CTX = 16384
TEMPERATURE = 0

PROMPT = """
Ты анализируешь фотографию с улицы.

Найди рекламный баннер, если он присутствует.
Нужно максимально подробно описать именно баннер.

Верни строго JSON:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "confidence": 0
}

client:
Компания, организация, партия или заказчик рекламы.

brand:
Торговая марка, имя кандидата или бренд.

category:
Категория рекламы: продукты, банк, букмекер,
выборы, политика, строительство, магазин и т.д.

text:
ВСЕ читаемые надписи на баннере.
Особенно важны названия, имена, даты, телефоны,
цены, сайты и лозунги.

colors:
Основные цвета баннера.

objects:
Главные изображения и объекты.

description:
Подробно опиши внешний вид баннера,
изображения, логотипы, расположение текста
и цветовую схему.

confidence:
Уверенность от 0 до 100.

Если баннера нет или его невозможно разобрать,
верни пустые поля.

Не придумывай информацию.
"""

def image64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def ask(path):

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT,
                "images": [image64(path)],
            }
        ],
        "stream": False,
        "options": {
            "num_ctx": NUM_CTX,
            "temperature": TEMPERATURE,
        },
    }

    started = time.time()

    r = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=900,
    )

    elapsed = time.time() - started

    if r.status_code != 200:
        raise RuntimeError(r.text)

    data = r.json()

    answer = data["message"]["content"]

    try:
        result = json.loads(answer)
    except Exception:

        cleaned = answer.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace(
                "```json", "", 1
            )
            cleaned = cleaned.replace(
                "```", ""
            ).strip()

        try:
            result = json.loads(cleaned)
        except Exception:
            result = {
                "raw_answer": answer
            }

    result["_time_sec"] = round(elapsed, 2)

    return result

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    files = sorted(
        list(INPUT_DIR.glob("*.JPG"))
        + list(INPUT_DIR.glob("*.jpg"))
        + list(INPUT_DIR.glob("*.PNG"))
        + list(INPUT_DIR.glob("*.png"))
    )[:LIMIT]

    print("=" * 70)
    print("QWEN3-VL 4B TEST")
    print("=" * 70)
    print()
    print("MODEL:", MODEL)
    print("FILES:", len(files))
    print("IMAGE RESIZE: DISABLED")
    print("NUM_CTX:", NUM_CTX)
    print("TEMPERATURE:", TEMPERATURE)
    print()

    total_start = time.time()
    results = []

    for i, path in enumerate(files, 1):

        print()
        print(
            f"[{i}/{len(files)}]",
            path.name
        )

        try:

            result = ask(path)

            output = (
                OUTPUT_DIR /
                f"{path.stem}.json"
            )

            with open(
                output,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    result,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            t = result.get(
                "_time_sec",
                0
            )

            client = result.get(
                "client", ""
            )

            brand = result.get(
                "brand", ""
            )

            confidence = result.get(
                "confidence", ""
            )

            print(
                "OK |",
                "client=",
                client,
                "| brand=",
                brand,
                "| confidence=",
                confidence,
                "| time=",
                t,
                "sec"
            )

            results.append({
                "file": path.name,
                "time_sec": t,
                "client": client,
                "brand": brand,
                "confidence": confidence,
                "category": result.get(
                    "category", ""
                ),
                "text": result.get(
                    "text", []
                ),
            })

        except Exception as e:

            print(
                "ERROR:",
                e
            )

            results.append({
                "file": path.name,
                "error": str(e),
            })

    total = round(
        time.time() - total_start,
        2
    )

    with open(
        OUTPUT_DIR / "summary.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )

    successful = [
        x for x in results
        if "time_sec" in x
    ]

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 14:56:50

Да, этого достаточно. Скрипт хороший, и **Qwen 4B уже проверен на реальных фотографиях**. Я бы его не переписывал — сделаем рабочую версию на его основе.

Но есть одно существенное изменение: сейчас он ищет фотографии только непосредственно в `data/input/test`, а нам нужно рекурсивно пройти:

```text
data/output/test_sorted_v2/
    78_v33/
    79_v33/
    ...
    95_v33/
```

И сохранять метаданные с сохранением адреса.

### Предлагаю сделать `qwen4b_output_v01.py`

Структура:

```text
data/metadata/qwen4b/
├── 78_v33/
│   ├── Ашхабадский_01.json
│   └── ...
├── 79_v33/
│   └── ...
...
└── 95_v33/
```

При этом:

- **257 фотографий**
- уже существующие 10 JSON можно перенести/учесть;
- обработанные фотографии повторно не запускаются;
- ошибка одной фотографии не останавливает весь процесс;
- после Ctrl+C можно продолжить;
- в конце будет `summary.json`;
- оригинальные фотографии вообще не трогаются.

И я бы добавил **привязку `address` прямо в JSON**:

```json
{
  "address": "78",
  "source_file": "...",
  "client": "...",
  "brand": "...",
  ...
}
```

Тогда frontend потом сможет получить всю карточку фотографии практически одним чтением metadata.

### Перед запуском

Поскольку 257 фотографий × ~16 секунд — это ориентировочно **около 70 минут**, сначала сделаем рабочий скрипт с `--limit 5` и проверим на пяти фотографиях.

После успешной проверки запускаем:

```bash
uv run python scripts/qwen4b_output_v01.py
```

без ограничения.

Если хочешь, следующим сообщением дам **готовую команду `cat > scripts/qwen4b_output_v01.py <<'PY'` целиком**, чтобы ты просто вставил её в терминал.

---

### 👤 **User** — 2026-08-16 14:57:32

можно добавить к описанию - зимняя погода, пасмурно, дождь, солнечный день - относящиеся не к баннеру, а к окружению

---

### 🤖 **Assistant** — 2026-08-16 14:57:33

Да, и **это очень полезно** для нашей задачи. Я бы добавил это отдельным полем, чтобы не смешивать характеристики баннера с окружающей сценой.

Например:

```json
{
  "client": "Единая Россия",
  "brand": "Дмитрий Сизякин",
  "category": "выборы",

  "text": [],
  "colors": [],
  "objects": [],

  "description": "Описание именно баннера...",

  "environment": {
    "season": "зима",
    "weather": "пасмурно",
    "precipitation": "снег",
    "lighting": "дневной свет",
    "scene": "улица, видны провода и дорожный знак"
  },

  "confidence": 95
}
```

### Я бы сделал немного шире

Потому что для **поиска похожих фотографий** окружение нам может оказаться очень полезным:

- `season` — весна / лето / осень / зима / неизвестно
- `weather` — солнечно / пасмурно / облачно / туман / неизвестно
- `precipitation` — дождь / снег / нет / неизвестно
- `lighting` — солнечный день / дневной рассеянный / сумерки / ночь
- `road_condition` — сухо / мокро / снег / лёд / неизвестно
- `scene` — краткое описание окружения
- `vegetation` — зелёная / без листвы / снег / смешанная
- `urban_context` — дорога, перекрёсток, дома, остановка, парковка и т.п.

При этом **не заставляем Qwen придумывать**. Если по фотографии нельзя определить сезон или погоду:

```json
"season": "неизвестно"
```

### И это разделяем на два независимых слоя

**Баннер:**

```text
brand
category
text
colors
objects
description
```

**Окружение:**

```text
season
weather
precipitation
lighting
road_condition
scene
vegetation
urban_context
```

Это потом позволит делать очень интересные запросы:

> найти Самокат зимой

> найти похожие места в пасмурную погоду

> фотографии с мокрой дорогой

> баннеры на перекрёстках летом

> показать фотографии с таким же окружением

И главное — **DINOv2 и Qwen будут дополнять друг друга**: DINO отвечает за визуальное сходство сцены, а Qwen даёт структурированное семантическое описание.

Я бы **обязательно добавил `environment` уже сейчас, до полного прогона 257 фотографий**, чтобы потом не пришлось прогонять Qwen второй раз.

---

### 👤 **User** — 2026-08-16 14:58:21

еще описать качество изображения - размытое, пересвеченное, темное, баннер не виден. Пусть модель рабюотает дольше - это не важно

---

### 🤖 **Assistant** — 2026-08-16 14:58:21

Да. Это стоит добавить **отдельным блоком**, причём не смешивать ни с баннером, ни с окружением.

И я согласен: **скорость Qwen 4B здесь вторична**. Для 257 фотографий лучше получить качественную разметку один раз, чем потом повторно прогонять базу.

Я бы сделал итоговую структуру так:

```json
{
  "client": "",
  "brand": "",
  "category": "",

  "text": [],
  "colors": [],
  "objects": [],

  "description": "",

  "environment": {
    "season": "",
    "weather": "",
    "precipitation": "",
    "lighting": "",
    "road_condition": "",
    "vegetation": "",
    "urban_context": "",
    "scene": ""
  },

  "image_quality": {
    "overall": "",
    "sharpness": "",
    "exposure": "",
    "visibility": "",
    "motion_blur": false,
    "occlusion": false,
    "banner_visible": true,
    "banner_readability": "",
    "notes": ""
  },

  "confidence": 0
}
```

### Что именно просим Qwen определить

**Качество фотографии:**

- резкая / слегка размытая / сильно размытая;
- нормальная экспозиция / пересвет / недоэкспонирована / очень тёмная;
- есть ли смаз от движения;
- закрыт ли баннер объектами;
- полностью ли виден баннер;
- насколько хорошо читается баннер;
- есть ли проблемы с ракурсом;
- есть ли сильные блики;
- есть ли препятствия перед баннером;
- пригодна ли фотография для анализа;
- краткое объяснение проблем.

Например:

```json
"image_quality": {
  "overall": "удовлетворительное",
  "sharpness": "слегка размыто",
  "exposure": "нормальная",
  "visibility": "баннер частично закрыт ветками",
  "motion_blur": false,
  "occlusion": true,
  "banner_visible": true,
  "banner_readability": "средняя",
  "notes": "Мелкий текст на баннере плохо читается."
}
```

А если фотография совсем плохая:

```json
"image_quality": {
  "overall": "плохое",
  "sharpness": "сильное размытие",
  "exposure": "нормальная",
  "visibility": "баннер плохо различим",
  "motion_blur": true,
  "occlusion": false,
  "banner_visible": false,
  "banner_readability": "невозможно определить",
  "notes": "Сильный смаз изображения, детали баннера неразличимы."
}
```

### Важный момент

Я бы **не заставлял модель оценивать только баннер**. Пусть она сначала оценивает фотографию целиком, а затем отдельно:

1. **что на баннере;**
2. **что вокруг баннера;**
3. **качество самой фотографии.**

Так мы получим три независимых слоя:

**Содержание**

`client / brand / text / objects / ...`

**Окружение**

`season / weather / road / vegetation / urban_context / ...`

**Качество**

`sharpness / exposure / visibility / readability / ...`

Это потом очень хорошо ложится на нашу базу и поиск.

И ещё я бы добавил одно поле верхнего уровня:

```json
"analysis_status": "good"
```

с вариантами:

```text
good
partial
poor
banner_not_visible
```

Тогда UI сможет сразу показывать, например:

**⚠ Баннер плохо виден**

вместо того чтобы пользователю читать всё описание.

**Сейчас я бы уже зафиксировал этот формат и только после этого запускал полный Qwen 4B по 257 фотографиям.**

---

### 👤 **User** — 2026-08-16 14:58:47

давай

---

### 🤖 **Assistant** — 2026-08-16 14:58:48

Да. Фиксируем формат и делаем отдельный скрипт полного прогона. Он будет использовать текущий `qwen3-vl:4b-instruct`, но с расширенным промптом и отдельным `environment` + `image_quality`.

Сделаем сначала **тест на 5 фотографиях**, а затем уже полный прогон 257.

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cat > scripts/qwen4b_output_v01.py <<'PY'
#!/usr/bin/env python3

import argparse
import base64
import json
import time
from pathlib import Path

import requests

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data" / "output" / "test_sorted_v2"
OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"

MODEL = "qwen3-vl:4b-instruct"
OLLAMA_URL = "http://localhost:11434/api/chat"

NUM_CTX = 16384
TEMPERATURE = 0

PROMPT = r"""
Ты выполняешь подробный анализ фотографии с улицы.

Фотография является частью базы наружной рекламы.

Нужно анализировать ТРИ НЕЗАВИСИМЫХ СЛОЯ:

1. БАННЕР / РЕКЛАМА
2. ОКРУЖЕНИЕ
3. КАЧЕСТВО ФОТОГРАФИИ

Очень важно:
НЕ ПУТАЙ характеристики баннера с характеристиками окружающей сцены.

Верни СТРОГО JSON следующего формата:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",

  "environment": {
    "season": "",
    "weather": "",
    "precipitation": "",
    "lighting": "",
    "road_condition": "",
    "vegetation": "",
    "urban_context": "",
    "scene": ""
  },

  "image_quality": {
    "overall": "",
    "sharpness": "",
    "exposure": "",
    "visibility": "",
    "motion_blur": false,
    "occlusion": false,
    "banner_visible": true,
    "banner_readability": "",
    "notes": ""
  },

  "confidence": 0
}

========================
1. БАННЕР / РЕКЛАМА
========================

Найди рекламный баннер, если он присутствует.

Опиши именно содержание баннера.

client:
Компания, организация, партия или заказчик рекламы.

brand:
Торговая марка, имя кандидата, бренд или рекламируемый объект.

category:
Категория рекламы:
продукты, банк, букмекер, выборы, политика,
строительство, магазин, услуги, медицина,
туризм и т.д.

text:
ВСЕ читаемые надписи на баннере.

Особенно важны:
названия,
имена,
даты,
телефоны,
цены,
адреса,
сайты,
логотипы,
слоганы.

Не придумывай текст, которого невозможно прочитать.

colors:
Основные цвета самого баннера.

objects:
Главные изображения и объекты НА БАННЕРЕ.

description:
Подробно опиши внешний вид самого баннера:
композицию,
цветовую схему,
логотипы,
людей,
предметы,
расположение текста,
графические элементы.

========================
2. ОКРУЖЕНИЕ
========================

Описывай только то, что находится ВНЕ БАННЕРА.

season:
весна / лето / осень / зима / неизвестно

weather:
солнечно / пасмурно / облачно / туман / неизвестно

precipitation:
нет / дождь / снег / мокрый снег / неизвестно

lighting:
яркий солнечный день /
обычный дневной свет /
рассеянный дневной свет /
сумерки /
ночь /
искусственное освещение /
неизвестно

road_condition:
сухая / мокрая / снег / лёд / грязь / неизвестно

vegetation:
зелёная растительность /
деревья без листвы /
снег /
минимальная растительность /
неизвестно

urban_context:
Например:
перекрёсток,
дорога,
тротуар,
остановка,
жилые дома,
магазины,
парковка,
промышленная зона,
центр города и т.д.

scene:
Кратко опиши окружающую сцену:
дорогу, здания, провода, деревья,
дорожные знаки, автомобили и другие объекты.

НЕ включай сюда содержание баннера.

========================
3. КАЧЕСТВО ФОТОГРАФИИ
========================

Оцени качество исходной фотографии.

overall:
хорошее / удовлетворительное / плохое

sharpness:
резкое /
слегка размыто /
сильно размыто /
неизвестно

exposure:
нормальная /
пересвечено /
недоэкспонировано /
очень тёмное /
неизвестно

visibility:
Насколько хорошо виден баннер.

motion_blur:
true, если заметен смаз от движения.
false, если его нет.

occlusion:
true, если баннер частично закрыт деревьями,
машинами, объектами или другими препятствиями.
false, если препятствий нет.

banner_visible:
true, если баннер действительно виден.
false, если баннер отсутствует или практически неразличим.

banner_readability:
высокая /
средняя /
низкая /
невозможно определить

notes:
Другие проблемы качества:
сильные блики,
пересвет,
темнота,
размытие,
малый размер баннера,
неудачный ракурс,
закрытие объектами и т.д.

========================

Если баннера нет или он неразличим:

- client = ""
- brand = ""
- category = ""
- text = []
- colors = []
- objects = []
- description = ""
- banner_visible = false

Но ВСЕГДА продолжай анализировать environment и image_quality.

Не придумывай информацию.

Если параметр невозможно достоверно определить,
используй "неизвестно".

confidence:
Общая уверенность в анализе от 0 до 100.
"""

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

def image64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def ask(path: Path) -> dict:

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": PROMPT,
                "images": [image64(path)],
            }
        ],
        "stream": False,
        "options": {
            "num_ctx": NUM_CTX,
            "temperature": TEMPERATURE,
        },
    }

    started = time.time()

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=1800,
    )

    elapsed = time.time() - started

    if response.status_code != 200:
        raise RuntimeError(response.text)

    data = response.json()
    answer = data["message"]["content"]

    cleaned = answer.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1)
        cleaned = cleaned.replace("```", "").strip()

    try:
        result = json.loads(cleaned)
    except Exception:
        result = {
            "raw_answer": answer
        }

    result["_time_sec"] = round(elapsed, 2)

    return result

def find_images():

    files = []

    for path in INPUT_DIR.rglob("*"):

        if (
            path.is_file()
            and path.suffix.lower() in IMAGE_EXTENSIONS
        ):
            files.append(path)

    return sorted(files, key=lambda p: str(p).lower())

def output_path(source: Path) -> Path:

    relative = source.relative_to(INPUT_DIR)

    address = relative.parts[0]

    return (
        OUTPUT_DIR
        / address
        / f"{source.stem}.json"
    )

def process(files):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    total_start = time.time()

    results = []

    for index, source in enumerate(files, 1):

        destination = output_path(source)

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        print()
        print("=" * 80)
        print(
            f"[{index}/{len(files)}] "
            f"{source.parent.name}/{source.name}"
        )

        if destination.exists():

            print("SKIP — metadata already exists")

            results.append({
                "file": source.name,
                "address": source.parent.name,
                "status": "skipped",
            })

            continue

        try:

            result = ask(source)

            result["address"] = source.parent.name
            result["source_file"] = str(
                source.relative_to(PROJECT)
            )

            with open(
                destination,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    result,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

            elapsed = result.get(
                "_time_sec",
                0
            )

            print(
                "OK",
                "| time:",
                elapsed,
                "sec",
                "| client:",
                result.get("client", ""),
                "| brand:",
                result.get("brand", ""),
                "| confidence:",
                result.get("confidence", "")
            )

            quality = result.get(
                "image_quality",
                {}
            )

            print(
                "QUALITY:",
                quality.get("overall", ""),
                "| sharpness:",
                quality.get("sharpness", ""),
                "| banner:",
                quality.get("banner_visible", "")
            )

            environment = result.get(
                "environment",
                {}
            )

            print(
                "ENV:",
                environment.get("season", ""),
                "|",
                environment.get("weather", ""),
                "|",
                environment.get("precipitation", "")
            )

            results.append({
                "file": source.name,
                "address": source.parent.name,
                "status": "ok",
                "time_sec": elapsed,
                "client": result.get("client", ""),
                "brand": result.get("brand", ""),
                "category": result.get("category", ""),
                "confidence": result.get("confidence", ""),
            })

        except Exception as error:

            print(
                "ERROR:",
                error
            )

            results.append({
                "file": source.name,
                "address": source.parent.name,
                "status": "error",
                "error": str(error),
            })

    total_elapsed = round(
        time.time() - total_start,
        2
    )

    summary = {
        "model": MODEL,
        "input": str(INPUT_DIR),
        "output": str(OUTPUT_DIR),
        "files_in_run": len(files),
        "elapsed_sec": total_elapsed,
        "results": results,
    }

    with open(
        OUTPUT_DIR / "summary.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)
    print(
        "Processed:",
        sum(
            1
            for x in results
            if x["status"] == "ok"
        )
    )
    print(
        "Skipped:",
        sum(
            1
            for x in results
            if x["status"] == "skipped"
        )
    )
    print(
        "Errors:",
        sum(
            1
            for x in results
            if x["status"] == "error"
        )
    )
    print(
        "Total time:",
        total_elapsed,
        "sec"
    )

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only N images"
    )

    args = parser.parse_args()

    files = find_images()

    print("=" * 80)
    print("QWEN3-VL 4B — OUTPUT ANALYSIS")
    print("=" * 80)
    print()
    print("MODEL:", MODEL)
    print("INPUT:", INPUT_DIR)
    print("OUTPUT:", OUTPUT_DIR)
    print("FOUND:", len(files))
    print("NUM_CTX:", NUM_CTX)
    print("TEMPERATURE:", TEMPERATURE)
    print()

    if args.limit is not None:
        files = files[:args.limit]
        print("LIMIT:", args.limit)
        print()

    if not files:
        print("No images found.")
        return

    process(files)

if __name__ == "__main__":
    main()
PY

chmod +x scripts/qwen4b_output_v01.py
```

Теперь **пока не запускаем все 257**.

Сначала:

```bash
uv run python scripts/qwen4b_output_v01.py --limit 5
```

После него проверим один JSON:

```bash
find data/metadata/qwen4b -type f -name "*.json" | sort
```

и:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

files = sorted(
    Path("data/metadata/qwen4b").rglob("*.json")
)

for p in files:
    if p.name == "summary.json":
        continue

    print()
    print("===", p, "===")

    data = json.loads(
        p.read_text(encoding="utf-8")
    )

    print(json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    ))

    break
PY
```

**После этих 5 фотографий посмотрим качество именно `environment` и `image_quality`.** Если Qwen хорошо различает погоду, сезон, пересвет/темноту и видимость баннера — запускаем остальные 252.

---

### 👤 **User** — 2026-08-16 15:00:53

LIMIT: 5

================================================================================
[1/5] 78_v33/Комарова13_01.JPG
OK | time: 16.53 sec | client:  | brand: Ozon Fresh | confidence: 90
QUALITY: удовлетворительное | sharpness: слегка размыто | banner: True
ENV: зима | облачно | мокрый снег

================================================================================
[2/5] 78_v33/Комарова13_02.JPG
OK | time: 14.61 sec | client: Магнит | brand: Магнит | confidence: 95
QUALITY: удовлетворительное | sharpness: резкое | banner: True
ENV: зима | облачно | мокрый снег

================================================================================
[3/5] 78_v33/Комарова13_03.JPG
OK | time: 15.43 sec | client: Магнит | brand: Магнит | confidence: 95
QUALITY: удовлетворительное | sharpness: резкое | banner: True
ENV: зима | облачно | мокрый снег

================================================================================
[4/5] 78_v33/Комарова13_04.JPG
OK | time: 15.29 sec | client: Магнит | brand: Магнит | confidence: 95
QUALITY: удовлетворительное | sharpness: слегка размыто | banner: True
ENV: зима | облачно | мокрый снег

================================================================================
[5/5] 78_v33/Комарова13_05.JPG
OK | time: 13.07 sec | client: Самокат | brand: Самокат | confidence: 95
QUALITY: удовлетворительное | sharpness: резкое | banner: True
ENV: зима | пасмурно | снег

================================================================================
DONE
================================================================================
Processed: 5
Skipped: 0
Errors: 0
Total time: 74.98 sec
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 15:00:55

Отлично. **Результат именно такой, какой нам нужен.** Qwen уверенно выделяет три независимых слоя.

По первым пяти:

- все 5 баннеров обнаружены;
- `confidence` 90-95;
- различает резкость/размытие;
- определяет зиму;
- различает облачность/пасмурность;
- определяет мокрый снег/снег;
- распознаёт разных клиентов и бренды.

Среднее время получилось около **15 секунд/фото**, то есть полный прогон 257 фотографий займёт ориентировочно **65 минут**. Для нашей задачи это совершенно нормально.

### Я бы теперь запускал полный прогон

Причём наш скрипт умеет продолжать работу: эти 5 уже имеют JSON и будут показаны как `SKIP`.

Запускаем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run python scripts/qwen4b_output_v01.py
```

**Не закрывай терминал**, пока он работает.

После завершения получим:

```text
data/metadata/qwen4b/
├── 78_v33/
├── 79_v33/
├── ...
├── 95_v33/
└── summary.json
```

И это будет уже первая полноценная **семантическая база фотографий**, поверх которой потом можно строить поиск.

Особенно ценно, что мы теперь не ограничены только:

**«что изображено на баннере»**

а получаем ещё:

**«в каких условиях была сделана фотография» + «насколько сама фотография пригодна для анализа».**

Это хорошо сочетается с нашим DINOv2: **DINOv2 - визуальный отпечаток, Qwen - смысловой отпечаток.**

---

### 👤 **User** — 2026-08-16 15:01:28

чтобы ты посоветовал добавить или все нормально?

---

### 🤖 **Assistant** — 2026-08-16 15:01:29

Я бы **не расширял схему сильно** — текущая уже хорошая. Но перед полным прогоном я бы добавил **4 вещи**, которые потом будет дорого получать повторно.

### 1. `banner_type`

Чтобы различать физический тип конструкции:

```json
"banner_type": "билборд"
```

Варианты:

- билборд
- суперсайт
- ситиборд
- остановочный павильон
- фасадная реклама
- перетяжка
- вывеска
- экран
- плакат
- другое
- неизвестно

Это пригодится для поиска: **«покажи рекламу на остановках»**.

### 2. `camera_view`

Очень полезно именно для нашей задачи поиска похожих фотографий:

```json
"camera_view": {
    "distance": "средняя",
    "angle": "прямой",
    "perspective": "фронтальная",
    "banner_size_in_frame": "крупный"
}
```

Потому что две фотографии одного места могут иметь совершенно разный визуальный вид из-за расстояния и ракурса.

### 3. `people_and_vehicles`

Не обязательно подробно, но:

```json
"scene_objects": {
    "people": true,
    "cars": true,
    "buses": false,
    "trucks": false,
    "pedestrians": true
}
```

Это может помочь потом отличать сцену:

> «тот же адрес, но фотографии с автобусом»

### 4. `analysis_quality`

Я бы добавил **отдельно от качества фотографии**:

```json
"analysis_quality": {
    "banner_analysis": "high",
    "environment_analysis": "high",
    "text_ocr": "medium"
}
```

Потому что фотография может быть вполне хорошей, но **мелкий текст на баннере не читается**.

---

### А вот это я бы НЕ добавлял сейчас

Не стал бы заставлять Qwen определять:

- точное время суток;
- координаты;
- конкретную улицу;
- направление движения;
- архитектурный стиль;
- точный цвет в RGB;
- размеры баннера;
- точное количество этажей зданий.

Это либо ненадёжно, либо у нас уже есть/будет другой источник данных.

### Итого

Я бы остановился на такой архитектуре:

```text
DINOv2
│
└── визуальный отпечаток
    ├── похожесть сцены
    ├── похожесть окружения
    └── поиск похожих фотографий

Qwen 4B
│
├── banner
│   ├── client
│   ├── brand
│   ├── category
│   ├── text
│   ├── colors
│   ├── objects
│   └── description
│
├── environment
│   ├── season
│   ├── weather
│   ├── precipitation
│   ├── lighting
│   ├── road_condition
│   ├── vegetation
│   └── urban_context
│
├── image_quality
│   ├── sharpness
│   ├── exposure
│   ├── visibility
│   ├── occlusion
│   └── readability
│
├── banner_type
├── camera_view
└── analysis_quality
```

**После этого я бы заморозил формат и запускал все 257.**

Причём особенно важно: **не надо сейчас пытаться сделать Qwen универсальным аналитиком.** Наша цель — получить полезные структурированные данные для будущего поиска и карточки фотографии. Текущая схема уже практически оптимальна для MVP.

---

### 👤 **User** — 2026-08-16 15:03:09

ах - да. у нас есть не только щиты, но и малые форматы вроде ситиков - но там нужно отдельно дорабатывать . сейчас просто не могу подкинуть нужные фото для обработки. пока отработаем схему на видеоэкранах - то что у нас сейчас

---

### 🤖 **Assistant** — 2026-08-16 15:03:10

Да, тогда **сейчас вообще не усложняем**.

Для текущей базы фиксируем специализацию на том, что уже есть — **видеоэкраны/крупные рекламные конструкции**, а поддержку ситибордов и других малых форматов вынесем в отдельный этап.

Я бы только добавил одно поле:

```json id="w3h8e2"
"banner_type": "видеоэкран"
```

Пока допустимые значения можно сделать:

```text
видеоэкран
билборд
неизвестно
```

Но **не заставляем Qwen сейчас точно различать все типы наружной рекламы**. Когда появятся фотографии ситибордов, сделаем отдельный тестовый набор и отдельно настроим промпт под малые форматы — там действительно важны другие признаки: размер в кадре, читаемость мелкого текста, расстояние до объекта и т.д.

### Поэтому сейчас схема такая

**Фиксируем:**

- содержание баннера;
- окружение;
- качество фотографии;
- видимость и читаемость;
- тип конструкции в общих чертах;
- исходный адрес `78_v33 ... 95_v33`.

И **запускаем полный прогон 257 фотографий**.

Команда уже готова:

```bash
cd ~/projects/scene_fingerprint_mvp_v02
uv run python scripts/qwen4b_output_v01.py
```

Первые 5 он пропустит, потому что JSON уже существуют.

После полного прогона я бы следующим шагом **не трогал Qwen**, а подключил эти metadata к нашему фронтенду: карточка фотографии → клиент, бренд, описание, погода, качество, адрес. Это уже даст ощутимый эффект в UI.

---

### 👤 **User** — 2026-08-16 15:04:29

Чтобы различать физический тип конструкции: - на данном этапе видеоэкран, нужно добавить план далеко - близко и ракурс, автобусы, елси видны вкадре, analysis quality

---

### 🤖 **Assistant** — 2026-08-16 15:04:30

Да. Тогда **фиксируем именно эти поля**, без расширения схемы в сторону ситибордов и других форматов.

Я бы сделал так:

```json
{
  "banner_type": "видеоэкран",

  "camera_view": {
    "distance": "далеко",
    "angle": "прямой"
  },

  "scene_objects": {
    "buses": true,
    "cars": true,
    "people": false
  },

  "analysis_quality": {
    "banner_analysis": "high",
    "environment_analysis": "high",
    "text_analysis": "medium"
  }
}
```

### Что важно для этих полей

**`distance`**

Только:

- `далеко`
- `средне`
- `близко`
- `очень близко`
- `неизвестно`

Здесь оцениваем **положение камеры относительно видеоэкрана**, а не размер самого экрана.

**`angle`**

- `прямой`
- `слева`
- `справа`
- `сверху`
- `снизу`
- `сильный боковой`
- `неизвестно`

Можно дополнительно разрешить `слабый боковой`, но пока это не обязательно.

**`scene_objects`**

Автобусы я бы сделал обязательным отдельным признаком:

```json
"scene_objects": {
  "buses": true,
  "cars": true,
  "trucks": false,
  "people": true
}
```

Причём `true` означает **объект реально виден в кадре**, а не просто предполагается.

**`analysis_quality`**

Очень полезное поле:

```text
banner_analysis
environment_analysis
text_analysis
```

со значениями:

```text
high
medium
low
none
```

Например, фото может быть хорошим для определения окружения, но текст на видеоэкране совершенно не читается:

```json
"analysis_quality": {
  "banner_analysis": "high",
  "environment_analysis": "high",
  "text_analysis": "low"
}
```

Это гораздо информативнее одного общего `confidence`.

### Итого

Я бы сейчас **заморозил Qwen-схему именно на этом уровне**:

**Баннер**
→ кто / что / текст / цвета / объекты / описание / тип `видеоэкран`

**Окружение**
→ сезон / погода / осадки / освещение / дорога / растительность / городская сцена

**Положение камеры**
→ далеко / средне / близко + ракурс

**Объекты сцены**
→ автобусы / автомобили / люди / грузовики

**Качество**
→ резкость / экспозиция / видимость / перекрытие / читаемость

**Качество анализа**
→ banner / environment / text

Это уже очень хорошая база для последующего поиска. Я бы **после добавления этих полей больше ничего не добавлял перед прогоном 257 фотографий**.

---

### 👤 **User** — 2026-08-16 15:04:49

пойдет

---

### 🤖 **Assistant** — 2026-08-16 15:04:49

Да. Тогда **схему фиксируем** и не расширяем.

Следующий шаг — обновить `qwen4b_output_v01.py` этими полями и прогнать сначала 5 тестовых фотографий. Если результат нормальный — запускаем все 257.

---

### 👤 **User** — 2026-08-16 15:04:55

да

---

### 🤖 **Assistant** — 2026-08-16 15:04:56

Тогда делаем обновление. Старые 5 JSON лучше **перегенерировать**, потому что схема изменилась.

Выполни:

```bash id="qwen_update_01"
cd ~/projects/scene_fingerprint_mvp_v02

uv run python - <<'PY'
from pathlib import Path

p = Path("scripts/qwen4b_output_v01.py")
text = p.read_text(encoding="utf-8")

old = '''  "description": "",

  "environment": {
'''

new = '''  "description": "",
  "banner_type": "видеоэкран",

  "environment": {
'''

if old not in text:
    raise SystemExit("Не найден блок description/environment")

text = text.replace(old, new, 1)

old = '''  "image_quality": {
    "overall": "",
    "sharpness": "",
    "exposure": "",
    "visibility": "",
    "motion_blur": false,
    "occlusion": false,
    "banner_visible": true,
    "banner_readability": "",
    "notes": ""
  },

  "confidence": 0
'''

new = '''  "image_quality": {
    "overall": "",
    "sharpness": "",
    "exposure": "",
    "visibility": "",
    "motion_blur": false,
    "occlusion": false,
    "banner_visible": true,
    "banner_readability": "",
    "notes": ""
  },

  "camera_view": {
    "distance": "",
    "angle": ""
  },

  "scene_objects": {
    "buses": false,
    "cars": false,
    "trucks": false,
    "people": false
  },

  "analysis_quality": {
    "banner_analysis": "",
    "environment_analysis": "",
    "text_analysis": ""
  },

  "confidence": 0
'''

if old not in text:
    raise SystemExit("Не найден блок image_quality")

text = text.replace(old, new, 1)

# Добавляем инструкции перед разделом ОКРУЖЕНИЕ
marker = '''========================
2. ОКРУЖЕНИЕ
========================
'''

insert = '''========================
ДОПОЛНИТЕЛЬНО
========================

banner_type:
На данном этапе основной тип конструкции — "видеоэкран".
Если конструкцию невозможно определить, используй "неизвестно".
Не пытайся классифицировать малые рекламные форматы.

camera_view:
Оцени положение камеры относительно видеоэкрана.

distance:
далеко / средне / близко / очень близко / неизвестно

angle:
прямой / слева / справа / сверху / снизу /
сильный боковой / неизвестно

scene_objects:
Отметь только объекты, которые реально видны в кадре:
buses — автобусы
cars — автомобили
trucks — грузовики
people — люди

analysis_quality:
Оцени качество именно анализа:
banner_analysis — high / medium / low / none
environment_analysis — high / medium / low / none
text_analysis — high / medium / low / none

Не оценивай здесь качество самой фотографии.
Качество фотографии указывается отдельно в image_quality.

========================
2. ОКРУЖЕНИЕ
========================
'''

if marker not in text:
    raise SystemExit("Не найден раздел ОКРУЖЕНИЕ")

text = text.replace(marker, insert, 1)

p.write_text(text, encoding="utf-8")

print("Qwen schema updated OK")
PY
```

Теперь удаляем **только первые пять старых результатов**, чтобы они прошли заново:

```bash id="remove_test_metadata"
cd ~/projects/scene_fingerprint_mvp_v02

rm -f \
  data/metadata/qwen4b/78_v33/Комарова13_01.json \
  data/metadata/qwen4b/78_v33/Комарова13_02.json \
  data/metadata/qwen4b/78_v33/Комарова13_03.json \
  data/metadata/qwen4b/78_v33/Комарова13_04.json \
  data/metadata/qwen4b/78_v33/Комарова13_05.json
```

И запускаем тест:

```bash id="run_qwen_test"
uv run python scripts/qwen4b_output_v01.py --limit 5
```

После этого покажи вывод. Особенно посмотрим на:

```text
BANNER TYPE
DISTANCE
ANGLE
BUSES
ANALYSIS QUALITY
```

Если всё нормально — **только тогда запускаем остальные 252 фотографии**.

---

### 👤 **User** — 2026-08-16 15:14:22

================================================================================
QWEN3-VL 4B — OUTPUT ANALYSIS
================================================================================

MODEL: qwen3-vl:4b-instruct
INPUT: /home/alexice/projects/scene_fingerprint_mvp_v02/data/output/test_sorted_v2
OUTPUT: /home/alexice/projects/scene_fingerprint_mvp_v02/data/metadata/qwen4b
FOUND: 256
NUM_CTX: 16384
TEMPERATURE: 0

LIMIT: 5

================================================================================
[1/5] 78_v33/Комарова13_01.JPG
OK | time: 11.36 sec | client:  | brand: Ozon | confidence: 95
QUALITY: удовлетворительное | sharpness: слегка размыто | banner: True
ENV: зима | пасмурно | мокрый снег

================================================================================
[2/5] 78_v33/Комарова13_02.JPG
OK | time: 162.29 sec | client:  | brand:  | confidence: 
QUALITY:  | sharpness:  | banner: 
ENV:  |  | 

================================================================================
[3/5] 78_v33/Комарова13_03.JPG
OK | time: 12.13 sec | client:  | brand: Магнит | confidence: 95
QUALITY: хорошо | sharpness: резкое | banner: True
ENV: зима | пасмурно | мокрый снег

================================================================================
[4/5] 78_v33/Комарова13_04.JPG
OK | time: 162.1 sec | client:  | brand:  | confidence: 
QUALITY:  | sharpness:  | banner: 
ENV:  |  | 

================================================================================
[5/5] 78_v33/Комарова13_05.JPG
OK | time: 10.26 sec | client:  | brand: самокат | confidence: 95
QUALITY: удовлетворительное | sharpness: резкое | banner: True
ENV: зима | пасмурно | снег

================================================================================
DONE
================================================================================
Processed: 5
Skipped: 0
Errors: 0
Total time: 358.19 sec
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 15:14:25

Вот это уже важный результат. **Схема сама по себе нормальная, но два из пяти запроса ушли в ~162 секунды и вернули пустой результат.** На полном прогоне так делать не стоит.

Причина, скорее всего, не в новых полях, а в том, что расширенный промпт иногда заставляет Qwen «зависать» на сложном кадре/JSON-ответе.

Я бы **не запускал 256 фото сейчас**.

### Что делаем

1. **Сохраняем новую схему.**
2. Добавляем защиту от пустого ответа.
3. Уменьшаем вероятность длинного рассуждения.
4. При плохом ответе автоматически повторяем запрос один раз.
5. Если повтор снова плохой — записываем ошибку, а не фальшивый пустой JSON.
6. Потом прогоняем тест ещё на 5.

При этом `NUM_CTX=16384` оставляем — памяти у нас достаточно, а скорость нормальных кадров около **10–12 секунд**.

И ещё: `FOUND: 256`, хотя раньше было 257. Это надо проверить отдельно — **одна фотография исчезла из `test_sorted_v2`**. Это не связано с Qwen, но перед полным прогоном обязательно найдём её.

Сначала выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== INPUT TEST ==="
find data/input/test -maxdepth 1 -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  | wc -l

echo
echo "=== SORTED OUTPUT ==="
find data/output/test_sorted_v2 -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  | wc -l

echo
echo "=== EMPTY QWEN RESULTS ==="
uv run python - <<'PY'
import json
from pathlib import Path

root = Path("data/metadata/qwen4b")

for p in sorted(root.rglob("*.json")):
    if p.name == "summary.json":
        continue

    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print("BROKEN JSON:", p, e)
        continue

    if not d.get("client") and not d.get("brand") and not d.get("environment"):
        print("EMPTY:", p)
PY
```

**Пока больше ничего не запускаем.**

Особенно хочу увидеть, какая именно фотография дала 162 секунды. У нас уже есть хороший ориентир: нормальный кадр обрабатывается примерно за 10–16 секунд, значит эти два случая надо разобрать отдельно, прежде чем отдавать Qwen все 256.

---

### 👤 **User** — 2026-08-16 15:15:25

я убрал лишнее фото

---

### 🤖 **Assistant** — 2026-08-16 15:15:26

Отлично. Тогда `256` — это ожидаемо, если ты сознательно убрал одну фотографию.

Но **два зависания по ~162 секунды всё равно надо решить до полного прогона**. Я бы сейчас не менял саму схему — она нам подходит.

Следующий шаг: покажи, **что именно Qwen записал для `Комарова13_02` и `Комарова13_04`**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== 02 ==="
cat "data/metadata/qwen4b/78_v33/Комарова13_02.json"

echo
echo "=== 04 ==="
cat "data/metadata/qwen4b/78_v33/Комарова13_04.json"
```

По этим двум JSON будет понятно, это:

- модель реально не смогла разобрать кадр;
- ответ оборвался;
- не сработал JSON;
- или новые требования заставили её слишком долго формировать ответ.

**После этого уже поправим обработку и только потом запустим весь набор.**

---

### 👤 **User** — 2026-08-16 15:15:41

PY      print("EMPTY:", p) and not d.get("brand") and not d.get("environment"):
=== INPUT TEST ===
257

=== SORTED OUTPUT ===
256

=== EMPTY QWEN RESULTS ===
EMPTY: data/metadata/qwen4b/78_v33/Комарова13_02.json
EMPTY: data/metadata/qwen4b/78_v33/Комарова13_04.json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

