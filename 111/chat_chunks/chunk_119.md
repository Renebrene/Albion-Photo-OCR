## СЕССИЯ: Продолжение разговора 1

**Создано:** 2026-08-18 12:11:53
**Обновлено:** 2026-08-19 17:07:58
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8421d7-3160-83ea-be54-4a2ad097babc](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8421d7-3160-83ea-be54-4a2ad097babc)

---

### 👤 **User** — 2026-08-18 14:27:13

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1190,1275p' app/web/components/photos.py
                                                    "text",
                                                    f"Выбрано: {len(STATE.selected_photos)}",
                                                ),
                                            ),
                                    ).props(
                                        "dense"
                                    )

                                    photo_checkboxes[
                                        photo_key(photo)
                                    ] = checkbox

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

                    # ----------------------------
                    # LOADING STATUS
                    # ----------------------------

                    if len(files) < len(all_files):

                        ui.label(
                            f"Показано {len(files)} из "
                            f"{len(all_files)}"
                        ).classes(
                            "w-full text-center "
                            "text-sm text-grey-6 p-4"
                        )

                    else:

                        ui.label(
                            f"Показаны все {len(files)} фотографий"
                        ).classes(
                            "w-full text-center "
                            "text-sm text-grey-6 p-4"
                        )

                grid_status_label.text = (
                    f"Показано {len(files)} из "
                    f"{len(all_files)}"
                )

            # ------------------------------------------------
            # LOAD MORE
            # ------------------------------------------------

            def load_more_photos():

                nonlocal grid_loaded

                if not grid_requested:
                    return

                all_files = get_filtered_photos()

                if grid_loaded >= len(all_files):
                    return

                old_loaded = grid_loaded

                grid_loaded = min(
                    grid_loaded + GRID_PAGE_SIZE,
                    len(all_files),
                )

                print(
                    "[PHOTO GRID LOAD MORE]",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 14:27:16

Да. Теперь причина понятна.

**Qwen-описания уже есть в PostgreSQL** — `photo_db.py` их получает:

```python
description,
confidence,
qwen_status,
...
```

и `photo.db_record` уже содержит эти данные. В `open_photo()` описание выводится, но **в самом превью GRID оно вообще не рисуется**. Поэтому под миниатюрой сейчас только имя и адрес.

Сделаем так:

```text
[ ФОТО ]
☑ Комарова13_15.JPG
  78
  самокат · Миля
  Рекламный баннер с изображением банки с пастой Миля...
```

И лучше сразу добавить **короткое описание Qwen под каждой фотографией**, обрезая его до 2 строк, чтобы сетка не стала огромной.

### 1. Вставляем блок после ADDRESS

Сейчас у тебя заканчивается блок:

```python
ui.label(
    photo.path.parent.name.replace(
        "_v33",
        "",
    )
).classes(
    "px-2 pb-2 "
    "text-xs text-grey-6"
)
```

Сразу **после него**, до `# LOADING STATUS`, вставляем:

```python
# ----------------------------
# QWEN DESCRIPTION
# ----------------------------

record = photo.db_record or {}

description = record.get("description")

if description:
    description = str(description).strip()

    if description:
        ui.label(
            description
        ).classes(
            "px-2 pb-2 "
            "text-xs text-grey-7 "
            "leading-tight "
            "line-clamp-2"
        )
```

### 2. Но есть ещё один важный момент

У тебя `PHOTO_RECORD_INDEX` создаётся **один раз при `build_photo_index()`**:

```python
PHOTO_RECORD_INDEX.update(
    build_photo_record_index(PROJECT_ROOT)
)
```

То есть если Qwen сейчас обрабатывает 526 фотографий и PostgreSQL получает новые записи, **уже запущенная страница может не увидеть их автоматически**, пока индекс не обновится.

Это как раз объясняет предыдущую ситуацию:

> `416 / 526`

но данные в карточках остаются старыми.

Поэтому я предлагаю сделать следующий шаг правильно:

**Qwen → PostgreSQL → `PHOTO_RECORD_INDEX` → GRID**

и при каждом `refresh()` технического модуля не просто обновлять цифры Qwen, а после появления новых записей обновлять связи `photo.db_record`.

Тогда будет:

- Qwen обработал фото №417;
- запись появилась в PostgreSQL;
- GRID получает описание;
- под 417-й фотографией появляется текст;
- остановка Qwen не ломает уже обработанные результаты;
- при продолжении уже существующие metadata остаются `SKIP`.

То есть **не надо переделывать сам Qwen** — база и структура у нас уже правильные. Нужно довести связку **PostgreSQL → превью**.

---

### 👤 **User** — 2026-08-18 14:27:28

давай одной командой

---

### 🤖 **Assistant** — 2026-08-18 14:27:28

Да. Сделаем **одной командой**: в карточке превью добавим под именем короткое описание Qwen из `db_record["description"]`, а если его нет — ничего не показываем.

Сначала backup уже есть, поэтому можно сразу выполнить:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && python - <<'PY'
from pathlib import Path

p = Path("app/web/components/photos.py")
s = p.read_text(encoding="utf-8")

old = '''                                    ui.label(
                                        photo.path.name
                                    ).classes(
                                        "font-medium "
                                        "text-sm truncate"
                                    )

                                # ----------------------------
                                # ADDRESS
                                # ----------------------------
'''

new = '''                                    with ui.column().classes(
                                        "min-w-0 flex-1 gap-0"
                                    ):
                                        ui.label(
                                            photo.path.name
                                        ).classes(
                                            "font-medium "
                                            "text-sm truncate"
                                        )

                                        description = (
                                            photo.db_record.get("description")
                                            if photo.db_record
                                            else None
                                        )

                                        if description:
                                            ui.label(
                                                str(description)
                                            ).classes(
                                                "text-xs "
                                                "text-grey-7 "
                                                "leading-tight "
                                                "line-clamp-2"
                                            )

                                # ----------------------------
                                # ADDRESS
                                # ----------------------------
'''

if old not in s:
    raise SystemExit("ERROR: target block not found")

s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")

print("QWEN DESCRIPTION IN PREVIEW: ADDED")
PY

python -m py_compile app/web/components/photos.py && \
echo "PYTHON SYNTAX: OK"
```

После перезапуска `lora.service` в карточке будет примерно:

**Комарова13_15.JPG**  
*Рекламный баннер с изображением банки с пастой Миля, цена 399 рублей...*  
`78`

То есть описание берётся **не из JSON напрямую**, а уже из PostgreSQL `db_record`, который у тебя сейчас корректно привязывается к фотографии через `build_photo_record_index()`.

Если после этого описание не появится — следующим шагом проверим **одной командой**, что именно эта фотография действительно имеет `description` в PostgreSQL.

---

### 👤 **User** — 2026-08-18 14:28:23

uv

---

### 🤖 **Assistant** — 2026-08-18 14:28:23

Да. Делаем одной командой через `uv`, без ручного редактирования.

Нам нужно добавить в карточку превью **описание Qwen из `photo.db_record["description"]`**, а если его нет — ничего не показывать. Заодно не трогаем уже работающий viewer.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/photos.py app/web/components/photos.py.bak_qwen_preview && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/photos.py")
s = p.read_text(encoding="utf-8")

old = '''                                ui.label(
                                    photo.path.parent.name.replace(
                                        "_v33",
                                        "",
                                    )
                                ).classes(
                                    "px-2 pb-2 "
                                    "text-xs text-grey-6"
                                )
'''

new = '''                                ui.label(
                                    photo.path.parent.name.replace(
                                        "_v33",
                                        "",
                                    )
                                ).classes(
                                    "px-2 pb-1 "
                                    "text-xs text-grey-6"
                                )

                                # ----------------------------
                                # QWEN DESCRIPTION
                                # ----------------------------

                                description = (
                                    photo.db_record.get("description")
                                    if photo.db_record
                                    else None
                                )

                                if description:
                                    ui.label(
                                        str(description)
                                    ).classes(
                                        "px-2 pb-2 "
                                        "text-xs text-grey-8 "
                                        "leading-tight "
                                        "line-clamp-2"
                                    )
'''

if old not in s:
    raise SystemExit("ОШИБКА: блок ADDRESS не найден — файл не изменён")

p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("QWEN DESCRIPTION IN PREVIEW: ADDED")
PY
uv run python -m py_compile app/web/components/photos.py && \
echo "PYTHON SYNTAX: OK"
```

После этого перезапускаем:

```bash
sudo systemctl restart lora.service && \
sleep 2 && \
systemctl is-active lora.service
```

В карточках получится примерно:

**Комарова13_15.JPG**  
`78`  
*Рекламный баннер с изображением банки с пастой Миля, цена 399 рублей...*

То есть описание берётся **не из имени файла и не повторно из Qwen**, а непосредственно из уже записанной PostgreSQL-записи `photo.db_record`. У нас для этого поле `description` уже загружается в `photo_db.py`.

---

### 👤 **User** — 2026-08-18 14:29:16

ytne

---

### 🤖 **Assistant** — 2026-08-18 14:29:18

Да. Делаем **одной командой через `uv`**, без ручного редактирования. Добавим описание Qwen прямо под адресом в карточке превью.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/photos.py")
s = p.read_text()

old = '''                                ui.label(
                                    photo.path.parent.name.replace(
                                        "_v33",
                                        "",
                                    )
                                ).classes(
                                    "px-2 pb-2 "
                                    "text-xs text-grey-6"
                                )
'''

new = '''                                ui.label(
                                    photo.path.parent.name.replace(
                                        "_v33",
                                        "",
                                    )
                                ).classes(
                                    "px-2 pb-0 "
                                    "text-xs text-grey-6"
                                )

                                # ----------------------------
                                # QWEN DESCRIPTION
                                # ----------------------------

                                description = (
                                    photo.db_record.get("description")
                                    if photo.db_record
                                    else None
                                )

                                if description:
                                    ui.label(
                                        str(description)
                                    ).classes(
                                        "px-2 pb-2 "
                                        "text-xs text-grey-8 "
                                        "leading-tight "
                                        "line-clamp-2"
                                    )
'''

if old not in s:
    raise SystemExit("BLOCK NOT FOUND — файл не изменён")

backup = p.with_suffix(".py.bak_preview_description")
backup.write_text(s)

p.write_text(s.replace(old, new))

print("PATCH: QWEN DESCRIPTION IN PREVIEW ADDED")
print("BACKUP:", backup)
PY
```

После этого:

```bash
sudo systemctl restart lora.service
```

В карточке будет:

**[фото]**  
`Комарова13_15.JPG`  
`78`  
`Рекламный баннер с изображением банки с пастой Миля...`

При этом **полное описание уже остаётся в окне фотографии**, как у нас сейчас.

---

### 👤 **User** — 2026-08-18 14:29:24

нет описания

---

### 🤖 **Assistant** — 2026-08-18 14:29:26

Тогда проблема не в отображении. **`photo.db_record["description"]` у карточки пустой.**

Qwen JSON есть, но нужно проверить, что PostgreSQL действительно содержит это поле для конкретного фото.

Давай одной командой проверим одновременно **PostgreSQL + Qwen JSON** для `Комарова13_15.JPG`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.photo_db import get_photo_records

name = "Комарова13_15.JPG"

for r in get_photo_records():
    if str(r.get("path", "")).endswith(name):
        print("\nPOSTGRES RECORD:")
        print("path       =", r.get("path"))
        print("client     =", r.get("client"))
        print("brand      =", r.get("brand"))
        print("description=", repr(r.get("description")))
        print("qwen_status=", r.get("qwen_status"))
        print("qwen_time  =", r.get("qwen_time_sec"))
        break
else:
    print("POSTGRES: RECORD NOT FOUND")
PY
```

**Если `description=None`**, значит Qwen JSON пока не импортируется в PostgreSQL — тогда исправлять нужно импорт/запись Qwen, а не `photos.py`.

**Если описание там есть**, тогда проблема именно в формировании `Photo.db_record`, и следующим шагом поправим это.

---

### 👤 **User** — 2026-08-18 14:29:41

active
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.photo_db import get_photo_records

name = "Комарова13_15.JPG"

for r in get_photo_records():
    if str(r.get("path", "")).endswith(name):
        print("\nPOSTGRES RECORD:")
        print("path       =", r.get("path"))
        print("client     =", r.get("client"))
        print("brand      =", r.get("brand"))
        print("description=", repr(r.get("description")))
        print("qwen_status=", r.get("qwen_status"))
        print("qwen_time  =", r.get("qwen_time_sec"))
        break
else:
    print("POSTGRES: RECORD NOT FOUND")
PY

POSTGRES RECORD:
path       = data/output/test_sorted_v2/78_v33/Комарова13_15.JPG
client     = самокат
brand      = Миля
description= 'Рекламный баннер с изображением банки с пастой Миля, цена 399 рублей с скидкой 39% от 659 рублей. Баннер красный с белым и синим текстом, изображение продукта в центре.'
qwen_status= ok
qwen_time  = 10.94

---

### 🤖 **Assistant** — 2026-08-18 14:29:42

Отлично — значит **PostgreSQL исправен** и описание Qwen там есть.

Проблема в другом: текущая фотография в `data/output/daily/...` имеет путь, например:

```text
data/output/daily/20260818_115048/78_v33/Комарова13_15.JPG
```

а PostgreSQL запись для неё указывает:

```text
data/output/test_sorted_v2/78_v33/Комарова13_15.JPG
```

Поэтому `PHOTO_RECORD_INDEX` ищет **полный путь** и не находит запись для daily-фото. Отсюда `photo.db_record` пустой, и описание не показывается.

Нам нужно сделать привязку не только по полному пути, а с fallback по:

```text
адрес + имя файла
```

Это как раз правильнее для твоей структуры.

Сделаем **одной командой через `uv`**, с backup:

```bash id="m8d0kq"
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/photo_db.py app/web/photo_db.py.bak_path_fallback && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/photo_db.py")
s = p.read_text(encoding="utf-8")

old = '''        index[str(db_path.resolve())] = record

    return index
'''

new = '''        # Основной индекс: полный абсолютный путь
        index[str(db_path.resolve())] = record

        # Fallback для daily/test_sorted_v2 и других
        # запусков, где один и тот же файл имеет разные
        # корневые каталоги.
        #
        # Ключ: адрес + имя файла
        address = str(record.get("address") or "").strip()
        filename = db_path.name

        if address and filename:
            index[f"__ADDR_FILE__:{address}:{filename}"] = record

    return index
'''

if old not in s:
    raise SystemExit("ERROR: target block not found")

p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("PHOTO DB: FALLBACK INDEX ADDED")
PY

uv run python -m py_compile app/web/photo_db.py && \
echo "PYTHON SYNTAX: OK"
```

Но **этого недостаточно** — `photos.py` пока ищет только полный путь.

Поэтому следующим шагом нужно изменить место, где создаётся `record` перед:

```python
Photo(
    path=path,
    db_record=record,
)
```

чтобы при отсутствии полного пути он искал:

```text
адрес + имя файла
```

Давай сначала сделаем **первую команду выше**, а потом я дам вторую короткую команду для `photos.py`. Не будем менять всё сразу.

---

### 👤 **User** — 2026-08-18 14:38:52

ищем

---

### 🤖 **Assistant** — 2026-08-18 14:38:53

Да, ищем место, где именно `photos.py` получает `record` перед созданием `Photo`.

Одной командой:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -B12 -A18 \
-E 'record\s*=|PHOTO_RECORD_INDEX|get\(.*PHOTO_RECORD_INDEX|Photo\(' \
app/web/components/photos.py | sed -n '1,220p'
```

Пришли вывод — по нему точно поправим привязку `daily → PostgreSQL` без лишних изменений.

---

### 👤 **User** — 2026-08-18 14:39:08

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ Photo(
    path=path,
    db_record=record,
)
-bash: syntax error near unexpected token `newline'
-bash: syntax error near unexpected token `)'
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -B12 -A18 \
-E 'record\s*=|PHOTO_RECORD_INDEX|get\(.*PHOTO_RECORD_INDEX|Photo\(' \
app/web/components/photos.py | sed -n '1,220p'
96-    ".jpeg",
97-    ".png",
98-    ".webp",
99-}
100-
101-
102-# ============================================================
103-# PHOTO INDEX
104-# ============================================================
105-
106-PHOTO_INDEX: dict[str, list[Path]] = {}
107-
108:PHOTO_RECORD_INDEX: dict[str, dict] = {}
109-
110-
111-def build_photo_index():
112-
113-    PHOTO_INDEX.clear()
114:    PHOTO_RECORD_INDEX.clear()
115-
116-    try:
117:        PHOTO_RECORD_INDEX.update(
118-            build_photo_record_index(PROJECT_ROOT)
119-        )
120-
121-        print(
122-            "[PHOTO RECORD INDEX]",
123-            "records=",
124:            len(PHOTO_RECORD_INDEX),
125-            flush=True,
126-        )
127-
128-    except Exception as exc:
129-
130-        print(
131-            "[PHOTO RECORD INDEX ERROR]",
132-            repr(exc),
133-            flush=True,
134-        )
135-
136-    daily_root = get_latest_daily_root()
137-
138-    if daily_root is None:
139-        print(
140-            "[DAILY PHOTO ROOT] not found",
141-            flush=True,
142-        )
--
301-    if not selected_clients:
302-        return []
303-
304-    selected_normalized = {
305-        str(client).strip().casefold()
306-        for client in selected_clients
307-    }
308-
309-    result = []
310-
311-    for path in files:
312-
313:        record = PHOTO_RECORD_INDEX.get(
314-            str(path.resolve())
315-        )
316-
317-        if not record:
318-            continue
319-
320-        client = str(
321-            record.get("client") or ""
322-        ).strip().casefold()
323-
324-        if client in selected_normalized:
325-            result.append(path)
326-
327-    return result
328-
329-
330-def get_address_count(address):
331-
--
334-            address,
335-            [],
336-        )
337-    )
338-
339-
340-# ============================================================
341-# PHOTO VIEWER
342-# ============================================================
343-
344-def open_photo(photo):
345-
346:    record = photo.db_record or {}
347-
348-    print(
349-        "[PHOTO OPEN]",
350-        "file=", photo.path.name,
351:        "has_db_record=", bool(photo.db_record),
352-        "db_id=", record.get("id"),
353-        "brand=", record.get("brand"),
354-        "client=", record.get("client"),
355-        flush=True,
356-    )
357-
358-    def value(name, default="—"):
359-        value = record.get(name)
360-
361-        if value is None or value == "":
362-            return default
363-
364-        return str(value)
365-
366-    def json_text(name, default="—"):
367-        value = record.get(name)
368-
369-        if value is None:
--
1027-                    "[PHOTO GRID EXECUTED]",
1028-                    "loaded=", len(files),
1029-                    "total=", len(all_files),
1030-                    flush=True,
1031-                )
1032-
1033-                # ------------------------------------------------
1034-                # CLEAR PREVIOUS GRID
1035-                # ------------------------------------------------
1036-
1037-                photo_grid_container.clear()
1038-
1039:                record_by_path = PHOTO_RECORD_INDEX
1040-
1041-                STATE.photos = []
1042-
1043-                for path in files:
1044-
1045:                    record = record_by_path.get(
1046-                        str(path.resolve())
1047-                    )
1048-
1049-                    STATE.photos.append(
1050:                        Photo(
1051-                            path=path,
1052:                            db_record=record,
1053-                        )
1054-                    )
1055-
1056-                print(
1057-                    "[PHOTO RECORD LINK]",
1058-                    "linked=",
1059-                    sum(
1060-                        1
1061-                        for photo in STATE.photos
1062-                        if photo.db_record is not None
1063-                    ),
1064-                    "total=",
1065-                    len(STATE.photos),
1066-                    flush=True,
1067-                )
1068-
1069-                count_label.text = (
1070-                    f"{len(files)} "
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 14:39:09

Да, нашли. Причина подтверждена: в двух местах используется **только полный путь**:

- `313–315`
- `1045–1047`

Но для GRID нам особенно важен второй блок — там создаётся `Photo(... db_record=record)`.

Сейчас лучше сделать аккуратно: **не менять поиск клиентов**, а исправить именно привязку карточки к PostgreSQL по `address + filename`, если полный путь не найден.

Одной командой через `uv`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cp app/web/components/photos.py app/web/components/photos.py.bak_record_fallback && \
uv run python - <<'PY'
from pathlib import Path

p = Path("app/web/components/photos.py")
s = p.read_text(encoding="utf-8")

old = '''                    record = record_by_path.get(
                        str(path.resolve())
                    )

                    STATE.photos.append(
'''

new = '''                    record = record_by_path.get(
                        str(path.resolve())
                    )

                    # Fallback: daily-фото может иметь другой
                    # корневой путь, чем запись PostgreSQL.
                    if not record:
                        address = path.parent.name
                        filename = path.name

                        record = record_by_path.get(
                            f"__ADDR_FILE__:{address}:{filename}"
                        )

                    STATE.photos.append(
'''

if old not in s:
    raise SystemExit("ERROR: target block not found")

p.write_text(s.replace(old, new, 1), encoding="utf-8")

print("PHOTO RECORD FALLBACK: ADDED")
PY

uv run python -m py_compile app/web/components/photos.py && \
echo "PYTHON SYNTAX: OK"
```

Потом:

```bash
sudo systemctl restart lora.service && \
sleep 2 && \
journalctl -u lora.service -n 40 --no-pager -l | \
grep -E 'PHOTO RECORD INDEX|PHOTO RECORD LINK|DAILY PHOTO ROOT'
```

**Ожидаем главное:** `PHOTO RECORD LINKED` должен стать близким к количеству фотографий, а не `0`/частичному числу.

После этого обнови страницу браузера — описания Qwen должны появиться в превью.

---

### 👤 **User** — 2026-08-18 14:40:39

есть но не везде

---

### 🤖 **Assistant** — 2026-08-18 14:40:39

Да, это уже хороший знак: **механизм работает**, но часть фотографий не совпадает по ключу `address + filename`.

Скорее всего, для части записей PostgreSQL `address` отличается от имени папки (`92_v33` vs `92`, либо другой путь/вариант имени).

Давай не гадать. Одной командой найдём **все фотографии, у которых нет DB-записи**, и покажем первые 30 с тем, какой ключ ищется:

```bash id="7d2s9k"
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.components.photos import (
    get_latest_daily_root,
    PHOTO_RECORD_INDEX,
)

root = get_latest_daily_root()
missing = []

for path in root.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in {".jpg",".jpeg",".png",".webp"}:
        continue

    if PHOTO_RECORD_INDEX.get(str(path.resolve())):
        continue

    key = f"__ADDR_FILE__:{path.parent.name}:{path.name}"

    if not PHOTO_RECORD_INDEX.get(key):
        missing.append(
            (
                path.parent.name,
                path.name,
            )
        )

print("DAILY PHOTOS WITHOUT DB RECORD:", len(missing))
print("=" * 80)

for address, filename in missing[:30]:
    print(f"{address} | {filename}")
PY
```

Пришли вывод.

По нему станет видно, что именно отличается: **адрес, имя файла или структура пути**. Тогда сделаем один нормальный fallback, который закроет практически все оставшиеся случаи, не ломая уже работающие.

---

### 👤 **User** — 2026-08-18 14:40:58

if PHOTO_RECORD_INDEX.get(str(path.resolve())):
        continue

    key = f"__ADDR_FILE__:{path.parent.name}:{path.name}"

    if not PHOTO_RECORD_INDEX.get(key):
        missing.append(
            (
                path.parent.name,
                path.name,
            )
        )

print("DAILY PHOTOS WITHOUT DB RECORD:", len(missing))
print("=" * 80)

for address, filename in missing[:30]:
    print(f"{address} | {filename}")
PY
DAILY PHOTOS WITHOUT DB RECORD: 526
================================================================================
95_v33 | Вавилова52_12.JPG
95_v33 | Вавилова52_13.JPG
95_v33 | Вавилова52_07.JPG
95_v33 | Вавилова52_09.JPG
95_v33 | Вавилова52_16.JPG
95_v33 | Вавилова52_05.JPG
95_v33 | Фурмановская ул. 106 - Плиева ул. 43 А (29).JPG
95_v33 | Вавилова52_11.JPG
95_v33 | Вавилова52_10.JPG
95_v33 | Вавилова52_06.JPG
95_v33 | Вавилова52_14.JPG
95_v33 | Вавилова52_15.JPG
95_v33 | Вавилова52_04.JPG
95_v33 | Вавилова52_01.JPG
95_v33 | Зорге_17.jpg
95_v33 | Вавилова52_02.JPG
95_v33 | Вавилова52_03.JPG
95_v33 | Вавилова52_08.JPG
87_v33 | Шеболдаева8_05.JPG
87_v33 | Шеболдаева8_13.JPG
87_v33 | Шеболдаева8_02.JPG
87_v33 | Шеболдаева8_03.JPG
87_v33 | Шеболдаева8_08.JPG
87_v33 | Шеболдаева8_18.JPG
87_v33 | Шеболдаева8_10.JPG
87_v33 | Шеболдаева8_07.JPG
87_v33 | Шеболдаева8_16.JPG
87_v33 | Шеболдаева8_04.JPG
87_v33 | Шеболдаева8_14.JPG
87_v33 | Шеболдаева8_01.JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 14:41:00

Вот теперь понятно: **fallback сейчас вообще не срабатывает**, поэтому тест показывает все 526.

Причина, скорее всего, в том, что мы добавили fallback-ключ в `photo_db.py`, но `PHOTO_RECORD_INDEX` в уже работающем процессе был построен старой версией. Однако команда `uv run python` импортирует новый модуль, так что надо проверить сам ключ.

Давай одной командой проверим **конкретно `95_v33 / Вавилова52_12.JPG`**: какой `address` и `filename` реально лежат в PostgreSQL и существует ли соответствующий ключ.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from app.web.components.photos import PHOTO_RECORD_INDEX
from app.web.photo_db import get_photo_records

filename = "Вавилова52_12.JPG"

print("INDEX SIZE:", len(PHOTO_RECORD_INDEX))

print("\nPOSTGRES:")
for r in get_photo_records():
    if str(r.get("filename", "")) == filename:
        print("address =", repr(r.get("address")))
        print("filename=", repr(r.get("filename")))
        print("path    =", repr(r.get("path")))
        print("description=", repr(r.get("description"))[:200])
        break
else:
    print("RECORD NOT FOUND")

print("\nTEST KEYS:")
for address in ("95", "95_v33"):
    key = f"__ADDR_FILE__:{address}:{filename}"
    print(address, "=>", key in PHOTO_RECORD_INDEX)
PY
```

Пришли вывод.

После этого мы точно увидим, почему `95_v33 + Вавилова52_12.JPG` не совпадает.

---

### 👤 **User** — 2026-08-18 14:41:16

from app.web.components.photos import PHOTO_RECORD_INDEX
from app.web.photo_db import get_photo_records

filename = "Вавилова52_12.JPG"

print("INDEX SIZE:", len(PHOTO_RECORD_INDEX))

print("\nPOSTGRES:")
for r in get_photo_records():
    if str(r.get("filename", "")) == filename:
        print("address =", repr(r.get("address")))
        print("filename=", repr(r.get("filename")))
        print("path    =", repr(r.get("path")))
        print("description=", repr(r.get("description"))[:200])
        break
else:
    print("RECORD NOT FOUND")

print("\nTEST KEYS:")
for address in ("95", "95_v33"):
    key = f"__ADDR_FILE__:{address}:{filename}"
    print(address, "=>", key in PHOTO_RECORD_INDEX)
PY
INDEX SIZE: 0

POSTGRES:
RECORD NOT FOUND

TEST KEYS:
95 => False
95_v33 => False
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 14:41:16

Да, теперь причина ясна.

`INDEX SIZE: 0` — это потому, что `PHOTO_RECORD_INDEX` **не строится автоматически при импорте `photos.py`**. Поэтому этот тест был некорректным.

А важнее другое:

```text
RECORD NOT FOUND
```

для `Вавилова52_12.JPG`.

То есть **в PostgreSQL действительно нет записи именно с таким `filename`**. Но это ещё не означает, что для фотографии нет Qwen-метаданных — нужно искать по пути/частичному имени.

Давай сейчас одной командой найдём эту фотографию **в PostgreSQL по `Вавилова52_12`**, а также в Qwen JSON:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path
from app.web.photo_db import get_photo_records
import json

needle = "Вавилова52_12"

print("=" * 80)
print("POSTGRES")
print("=" * 80)

found = False

for r in get_photo_records():
    text = " ".join(
        str(r.get(k) or "")
        for k in ("filename", "path", "address")
    )

    if needle in text:
        found = True
        print("id         =", r.get("id"))
        print("address    =", repr(r.get("address")))
        print("filename   =", repr(r.get("filename")))
        print("path       =", repr(r.get("path")))
        print("client     =", repr(r.get("client")))
        print("brand      =", repr(r.get("brand")))
        print("description=", repr(r.get("description")))
        print()

if not found:
    print("POSTGRES: НЕ НАЙДЕНО")

print("=" * 80)
print("QWEN JSON")
print("=" * 80)

root = Path("data/metadata/qwen4b")

json_found = False

for f in root.rglob("*.json"):
    if needle not in f.stem:
        continue

    json_found = True

    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        print("JSON ERROR:", f, e)
        continue

    print("FILE:", f)
    print("address    =", repr(data.get("address")))
    print("source_file=", repr(data.get("source_file")))
    print("client     =", repr(data.get("client")))
    print("brand      =", repr(data.get("brand")))
    print("description=", repr(data.get("description")))
    print()

if not json_found:
    print("QWEN: НЕ НАЙДЕНО")
PY
```

Это даст нам ответ сразу на два вопроса:

1. **Есть ли описание Qwen для `Вавилова52_12.JPG` вообще.**
2. Если есть — **почему оно не попало в PostgreSQL**.

И дальше уже не будем ковырять `photos.py` вслепую. Нам нужно сначала понять, **какие именно 526 фотографий не имеют DB-записей, а какие имеют Qwen JSON, но не импортированы**.

---

### 👤 **User** — 2026-08-18 14:41:34

print("=" * 80)
print("QWEN JSON")
print("=" * 80)

PY  print("QWEN: НЕ НАЙДЕНО")r(data.get("description")))
================================================================================
POSTGRES
================================================================================
POSTGRES: НЕ НАЙДЕНО
================================================================================
QWEN JSON
================================================================================
FILE: data/metadata/qwen4b/20260818_115048/95_v33/Вавилова52_12.json
address    = '95_v33'
source_file= 'data/output/daily/20260818_115048/95_v33/Вавилова52_12.JPG'
client     = None
brand      = None
description= None

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 14:41:35

Вот теперь картина полностью ясна.

Для `95_v33/Вавилова52_12.JPG`:

- **PostgreSQL:** записи нет.
- **Qwen JSON:** есть.
- Но JSON содержит:
  - `client = None`
  - `brand = None`
  - `description = None`

То есть это **не проблема отображения превью**. Для этой фотографии Qwen действительно не записал описание.

При этом ранее `Комарова13_15.JPG` мы проверили — там Qwen JSON полноценный и PostgreSQL тоже содержит описание.

### Значит сейчас есть два разных случая

**1. Старые/успешные данные**

```text
Qwen JSON
   ↓
PostgreSQL
   ↓
PHOTO_RECORD_INDEX
   ↓
превью показывает описание
```

**2. Новый запуск 20260818**

```text
Qwen JSON
   ↓
PostgreSQL — записи нет
   ↓
PHOTO_RECORD_INDEX — записи нет
   ↓
превью — описания нет
```

Причём для `Вавилова52_12` сам Qwen JSON уже говорит, что анализа нет:

```json
"client": null,
"brand": null,
"description": null
```

Поэтому сейчас **не надо менять `photos.py`**.

Нужно проверить, почему Qwen на запуске `20260818_115048` создаёт JSON без анализа для части фотографий. Особенно интересно сравнить его с полноценным JSON из `20260816_231222`.

Давай найдём **сколько таких пустых JSON в текущем запуске**:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path
import json

root = Path("data/metadata/qwen4b/20260818_115048")

total = 0
empty = 0
ok = 0

for f in root.rglob("*.json"):
    if f.name == "summary.json":
        continue

    total += 1

    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        continue

    if d.get("description"):
        ok += 1
    else:
        empty += 1

print("TOTAL JSON :", total)
print("WITH DESCRIPTION:", ok)
print("EMPTY DESCRIPTION:", empty)
print("PERCENT OK:", f"{ok / total * 100:.1f}%" if total else "0%")

print("\nПРИМЕРЫ ПУСТЫХ:")
n = 0
for f in root.rglob("*.json"):
    if f.name == "summary.json":
        continue

    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        continue

    if not d.get("description"):
        print(f)
        n += 1
        if n >= 20:
            break
PY
```

Это сейчас самый важный тест. Он покажет, **почему в интерфейсе часть фотографий без описаний**: если пустых JSON много, исправлять надо Qwen pipeline/импорт, а не интерфейс.

---

### 👤 **User** — 2026-08-18 14:42:05

PY          break0:escription"):xt(encoding="utf-8"))
TOTAL JSON : 526
WITH DESCRIPTION: 375
EMPTY DESCRIPTION: 151
PERCENT OK: 71.3%

ПРИМЕРЫ ПУСТЫХ:
data/metadata/qwen4b/20260818_115048/95_v33/Фурмановская ул. 106 - Плиева ул. 43 А (29).json
data/metadata/qwen4b/20260818_115048/95_v33/Вавилова52_12.json
data/metadata/qwen4b/20260818_115048/95_v33/Вавилова52_11.json
data/metadata/qwen4b/20260818_115048/87_v33/Шеболдаева8_13.json
data/metadata/qwen4b/20260818_115048/87_v33/Шеболдаева8_18.json
data/metadata/qwen4b/20260818_115048/86_v33/Радиаторный_24.json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (33).json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (15).json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (14).json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (16).json
data/metadata/qwen4b/20260818_115048/83_v33/Нагибина24_08.json
data/metadata/qwen4b/20260818_115048/83_v33/Нагибина24_07.json
data/metadata/qwen4b/20260818_115048/83_v33/Нагибина24_06.json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (55).json
data/metadata/qwen4b/20260818_115048/78_v33/Комарова13_13.json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (9).json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (56).json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (47).json
data/metadata/qwen4b/20260818_115048/78_v33/Королева пр-кт (рядом с мостом), A (6).json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (27).json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 14:42:05

Да. Теперь причина подтверждена: **не интерфейс**.

В текущем запуске `20260818_115048`:

- 526 фотографий
- **375** имеют описание → 71,3%
- **151** имеют пустое описание → 28,7%

Причём пустые JSON уже создаются самим Qwen-процессом. Поэтому `photos.py` тут ничего не сможет показать.

Но есть важный момент: у нас раньше в логах встречалось:

```text
[QWEN] OK
client:
brand:
confidence: 0
```

То есть Qwen иногда отвечает, но результат получается пустым. Нужно посмотреть **реальный JSON одного успешного и одного пустого файла + код, который разбирает ответ Ollama**.

Давай сейчас одной командой найдём логику записи JSON в `qwen4b_output_v01.py`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -B15 -A35 -E \
'json.dump|description|client|brand|response|ollama|model|raw_json' \
scripts/qwen4b_output_v01.py | head -350
```

Пришли вывод.

**Пока ничего в коде не меняем.** Сначала найдём место, где из ответа Qwen формируется этот JSON. Тогда можно будет исправить именно причину 151 пустого результата, а не маскировать её в интерфейсе.

---

### 👤 **User** — 2026-08-18 14:42:46

data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (47).json
data/metadata/qwen4b/20260818_115048/78_v33/Королева пр-кт (рядом с мостом), A (6).json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (27).json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -B15 -A35 -E \
'json.dump|description|client|brand|response|ollama|model|raw_json' \
scripts/qwen4b_output_v01.py | head -350
20-NUM_CTX = 16384
21-TEMPERATURE = 0
22-
23-
24-PROMPT = r"""
25-Ты анализируешь фотографию с улицы для базы наружной рекламы.
26-
27-Найди рекламный баннер и верни ТОЛЬКО JSON.
28-Не добавляй пояснений вне JSON.
29-Не повторяй информацию.
30-Не придумывай отсутствующую информацию.
31-
32-Формат:
33-
34-{
35:  "client": "",
36:  "brand": "",
37-  "category": "",
38-  "text": [],
39-  "colors": [],
40-  "objects": [],
41:  "description": "",
42-  "banner_type": "видеоэкран",
43-
44-  "environment": {
45-    "weather": "",
46-    "precipitation": "",
47-    "lighting": ""
48-  },
49-
50-  "image_quality": {
51-    "overall": "",
52-    "sharpness": "",
53-    "exposure": "",
54-    "visibility": "",
55-    "banner_visible": true,
56-    "banner_readability": "",
57-    "motion_blur": false,
58-    "occlusion": false
59-  },
60-
61-  "camera_view": {
62-    "distance": "",
63-    "angle": ""
64-  },
65-
66-  "analysis_quality": {
67-    "banner_analysis": "",
68-    "text_analysis": ""
69-  },
70-
71-  "confidence": 0
72-}
73-
74-БАННЕР:
75:client — компания, организация или заказчик.
76:brand — торговая марка, имя кандидата или рекламируемый бренд.
77-category — категория рекламы.
78-text — читаемые надписи на баннере.
79-colors — основные цвета самого баннера.
80-objects — основные изображения и предметы НА БАННЕРЕ.
81:description — краткое описание композиции баннера, максимум 300 символов.
82-banner_type — на данном этапе "видеоэкран".
83-
84-ОКРУЖЕНИЕ:
85-Определи ТОЛЬКО:
86-weather — солнечно / пасмурно / облачно / туман / неизвестно.
87-precipitation — нет / дождь / снег / мокрый снег / неизвестно.
88-lighting — яркий день / дневной свет / сумерки / ночь / искусственное освещение / неизвестно.
89-
90-Не описывай окружающую сцену.
91-Не описывай здания, дороги, автомобили, автобусы, людей,
92-дорожные знаки, провода или растительность.
93-
94-КАЧЕСТВО:
95-Оцени только качество фотографии и видимость баннера.
96-
97-overall — хорошее / удовлетворительное / плохое.
98-sharpness — резкое / слегка размыто / сильно размыто / неизвестно.
99-exposure — нормальная / пересвечено / недоэкспонировано / очень тёмное / неизвестно.
100-visibility — хорошо виден / частично виден / плохо виден / не виден.
101-banner_visible — true или false.
102-banner_readability — высокая / средняя / низкая / невозможно определить.
103-motion_blur — true или false.
104-occlusion — true или false.
105-
106-КАМЕРА:
107-distance — далеко / средняя дистанция / близко / неизвестно.
108-angle — прямо / слева / справа / сверху / снизу / косой ракурс / неизвестно.
109-
110-Если баннер не виден:
111:client = ""
112:brand = ""
113-category = ""
114-text = []
115-colors = []
116-objects = []
117:description = ""
118-banner_visible = false
119-
120-Массивы должны содержать только действительно важные элементы.
121-Не более 10 элементов в каждом массиве.
122-Не повторяй элементы.
123-
124-confidence — уверенность в анализе от 0 до 100.
125-"""
126-
127-
128-IMAGE_EXTENSIONS = {
129-    ".jpg",
130-    ".jpeg",
131-    ".png",
132-    ".webp",
133-}
134-
135-
136-def image64(path: Path) -> str:
137-    with open(path, "rb") as f:
138-        return base64.b64encode(f.read()).decode()
139-
140-
141-def ask(path: Path) -> dict:
142-
143-    payload = {
144:        "model": MODEL,
145-        "messages": [
146-            {
147-                "role": "user",
148-                "content": PROMPT,
149-                "images": [image64(path)],
150-            }
151-        ],
152-        "stream": False,
153-        "options": {
154-            "num_ctx": NUM_CTX,
155-            "temperature": TEMPERATURE,
156-            "num_predict": 500,
157-        },
158-    }
159-
160-    started = time.time()
161-
162:    response = requests.post(
163-        OLLAMA_URL,
164-        json=payload,
165-        timeout=1800,
166-    )
167-
168-    elapsed = time.time() - started
169-
170:    if response.status_code != 200:
171:        raise RuntimeError(response.text)
172-
173:    data = response.json()
174-
175-    # Ollama performance diagnostics
176-    stats = {
177-        "total_duration_sec": round(
178-            data.get("total_duration", 0) / 1e9, 2
179-        ),
180-        "load_duration_sec": round(
181-            data.get("load_duration", 0) / 1e9, 2
182-        ),
183-        "prompt_eval_duration_sec": round(
184-            data.get("prompt_eval_duration", 0) / 1e9, 2
185-        ),
186-        "eval_duration_sec": round(
187-            data.get("eval_duration", 0) / 1e9, 2
188-        ),
189-        "prompt_eval_count": data.get(
190-            "prompt_eval_count"
191-        ),
192-        "eval_count": data.get(
193-            "eval_count"
194-        ),
195-    }
196-
197-    print(
198-        "[OLLAMA]",
199-        stats,
200-        flush=True,
201-    )
202-
203-    answer = data["message"]["content"]
204-
205-    cleaned = answer.strip()
206-
207-    if cleaned.startswith("```"):
208-        cleaned = cleaned.replace("```json", "", 1)
--
290-        try:
291-
292-            result = ask(source)
293-
294-            result["address"] = source.parent.name
295-            result["source_file"] = str(
296-                source.relative_to(PROJECT)
297-            )
298-
299-            with open(
300-                destination,
301-                "w",
302-                encoding="utf-8"
303-            ) as f:
304-
305:                json.dump(
306-                    result,
307-                    f,
308-                    ensure_ascii=False,
309-                    indent=2
310-                )
311-
312-            elapsed = result.get(
313-                "_time_sec",
314-                0
315-            )
316-
317-            print(
318-                "OK",
319-                "| time:",
320-                elapsed,
321-                "sec",
322:                "| client:",
323:                result.get("client", ""),
324:                "| brand:",
325:                result.get("brand", ""),
326-                "| confidence:",
327-                result.get("confidence", "")
328-            )
329-
330-            quality = result.get(
331-                "image_quality",
332-                {}
333-            )
334-
335-            print(
336-                "QUALITY:",
337-                quality.get("overall", ""),
338-                "| sharpness:",
339-                quality.get("sharpness", ""),
340-                "| banner:",
341-                quality.get("banner_visible", "")
342-            )
343-
344-            environment = result.get(
345-                "environment",
346-                {}
347-            )
348-
349-            print(
350-                "ENV:",
351-                environment.get("season", ""),
352-                "|",
353-                environment.get("weather", ""),
354-                "|",
355-                environment.get("precipitation", "")
356-            )
357-
358-            results.append({
359-                "file": source.name,
360-                "address": source.parent.name,
361-                "status": "ok",
362-                "time_sec": elapsed,
363:                "client": result.get("client", ""),
364:                "brand": result.get("brand", ""),
365-                "category": result.get("category", ""),
366-                "confidence": result.get("confidence", ""),
367-            })
368-
369-        except Exception as error:
370-
371-            print(
372-                "ERROR:",
373-                error
374-            )
375-
376-            results.append({
377-                "file": source.name,
378-                "address": source.parent.name,
379-                "status": "error",
380-                "error": str(error),
381-            })
382-
383-    total_elapsed = round(
384-        time.time() - total_start,
385-        2
386-    )
387-
388-    summary = {
389:        "model": MODEL,
390-        "input": str(INPUT_DIR),
391-        "output": str(OUTPUT_DIR),
392-        "files_in_run": len(files),
393-        "elapsed_sec": total_elapsed,
394-        "results": results,
395-    }
396-
397-    with open(
398-        OUTPUT_DIR / "summary.json",
399-        "w",
400-        encoding="utf-8"
401-    ) as f:
402-
403:        json.dump(
404-            summary,
405-            f,
406-            ensure_ascii=False,
407-            indent=2
408-        )
409-
410-    print()
411-    print("=" * 80)
412-    print("DONE")
413-    print("=" * 80)
414-    print(
415-        "Processed:",
416-        sum(
417-            1
418-            for x in results
419-            if x["status"] == "ok"
420-        )
421-    )
422-    print(
423-        "Skipped:",
424-        sum(
425-            1
426-            for x in results
427-            if x["status"] == "skipped"
428-        )
429-    )
430-    print(
431-        "Errors:",
432-        sum(
433-            1
434-            for x in results
435-            if x["status"] == "error"
436-        )
437-    )
438-    print(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 14:42:47

Да, нашли место. Но в выводе как раз **не хватает ключевого участка** — строки примерно `203–289`, где ответ Ollama превращается в `result`.

Именно там, скорее всего, причина 151 пустого JSON: либо Qwen возвращает JSON с пустыми полями, либо наш парсер/нормализация их обнуляет.

Давай одной командой покажем этот участок целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '195,290p' scripts/qwen4b_output_v01.py
```

После этого уже можно будет точно исправить причину, **не трогая `photos.py` и PostgreSQL**.

---

### 👤 **User** — 2026-08-18 14:44:53

n = 0
for f in root.rglob("*.json"):
    if f.name == "summary.json":
        continue

PY          break0:escription"):xt(encoding="utf-8"))
TOTAL JSON : 526
WITH DESCRIPTION: 375
EMPTY DESCRIPTION: 151
PERCENT OK: 71.3%

ПРИМЕРЫ ПУСТЫХ:
data/metadata/qwen4b/20260818_115048/95_v33/Фурмановская ул. 106 - Плиева ул. 43 А (29).json
data/metadata/qwen4b/20260818_115048/95_v33/Вавилова52_12.json
data/metadata/qwen4b/20260818_115048/95_v33/Вавилова52_11.json
data/metadata/qwen4b/20260818_115048/87_v33/Шеболдаева8_13.json
data/metadata/qwen4b/20260818_115048/87_v33/Шеболдаева8_18.json
data/metadata/qwen4b/20260818_115048/86_v33/Радиаторный_24.json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (33).json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (15).json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (14).json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (16).json
data/metadata/qwen4b/20260818_115048/83_v33/Нагибина24_08.json
data/metadata/qwen4b/20260818_115048/83_v33/Нагибина24_07.json
data/metadata/qwen4b/20260818_115048/83_v33/Нагибина24_06.json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (55).json
data/metadata/qwen4b/20260818_115048/78_v33/Комарова13_13.json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (9).json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (56).json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (47).json
data/metadata/qwen4b/20260818_115048/78_v33/Королева пр-кт (рядом с мостом), A (6).json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (27).json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -B15 -A35 -E \
'json.dump|description|client|brand|response|ollama|model|raw_json' \
scripts/qwen4b_output_v01.py | head -350
20-NUM_CTX = 16384
21-TEMPERATURE = 0
22-
23-
24-PROMPT = r"""
25-Ты анализируешь фотографию с улицы для базы наружной рекламы.
26-
27-Найди рекламный баннер и верни ТОЛЬКО JSON.
28-Не добавляй пояснений вне JSON.
29-Не повторяй информацию.
30-Не придумывай отсутствующую информацию.
31-
32-Формат:
33-
34-{
35:  "client": "",
36:  "brand": "",
37-  "category": "",
38-  "text": [],
39-  "colors": [],
40-  "objects": [],
41:  "description": "",
42-  "banner_type": "видеоэкран",
43-
44-  "environment": {
45-    "weather": "",
46-    "precipitation": "",
47-    "lighting": ""
48-  },
49-
50-  "image_quality": {
51-    "overall": "",
52-    "sharpness": "",
53-    "exposure": "",
54-    "visibility": "",
55-    "banner_visible": true,
56-    "banner_readability": "",
57-    "motion_blur": false,
58-    "occlusion": false
59-  },
60-
61-  "camera_view": {
62-    "distance": "",
63-    "angle": ""
64-  },
65-
66-  "analysis_quality": {
67-    "banner_analysis": "",
68-    "text_analysis": ""
69-  },
70-
71-  "confidence": 0
72-}
73-
74-БАННЕР:
75:client — компания, организация или заказчик.
76:brand — торговая марка, имя кандидата или рекламируемый бренд.
77-category — категория рекламы.
78-text — читаемые надписи на баннере.
79-colors — основные цвета самого баннера.
80-objects — основные изображения и предметы НА БАННЕРЕ.
81:description — краткое описание композиции баннера, максимум 300 символов.
82-banner_type — на данном этапе "видеоэкран".
83-
84-ОКРУЖЕНИЕ:
85-Определи ТОЛЬКО:
86-weather — солнечно / пасмурно / облачно / туман / неизвестно.
87-precipitation — нет / дождь / снег / мокрый снег / неизвестно.
88-lighting — яркий день / дневной свет / сумерки / ночь / искусственное освещение / неизвестно.
89-
90-Не описывай окружающую сцену.
91-Не описывай здания, дороги, автомобили, автобусы, людей,
92-дорожные знаки, провода или растительность.
93-
94-КАЧЕСТВО:
95-Оцени только качество фотографии и видимость баннера.
96-
97-overall — хорошее / удовлетворительное / плохое.
98-sharpness — резкое / слегка размыто / сильно размыто / неизвестно.
99-exposure — нормальная / пересвечено / недоэкспонировано / очень тёмное / неизвестно.
100-visibility — хорошо виден / частично виден / плохо виден / не виден.
101-banner_visible — true или false.
102-banner_readability — высокая / средняя / низкая / невозможно определить.
103-motion_blur — true или false.
104-occlusion — true или false.
105-
106-КАМЕРА:
107-distance — далеко / средняя дистанция / близко / неизвестно.
108-angle — прямо / слева / справа / сверху / снизу / косой ракурс / неизвестно.
109-
110-Если баннер не виден:
111:client = ""
112:brand = ""
113-category = ""
114-text = []
115-colors = []
116-objects = []
117:description = ""
118-banner_visible = false
119-
120-Массивы должны содержать только действительно важные элементы.
121-Не более 10 элементов в каждом массиве.
122-Не повторяй элементы.
123-
124-confidence — уверенность в анализе от 0 до 100.
125-"""
126-
127-
128-IMAGE_EXTENSIONS = {
129-    ".jpg",
130-    ".jpeg",
131-    ".png",
132-    ".webp",
133-}
134-
135-
136-def image64(path: Path) -> str:
137-    with open(path, "rb") as f:
138-        return base64.b64encode(f.read()).decode()
139-
140-
141-def ask(path: Path) -> dict:
142-
143-    payload = {
144:        "model": MODEL,
145-        "messages": [
146-            {
147-                "role": "user",
148-                "content": PROMPT,
149-                "images": [image64(path)],
150-            }
151-        ],
152-        "stream": False,
153-        "options": {
154-            "num_ctx": NUM_CTX,
155-            "temperature": TEMPERATURE,
156-            "num_predict": 500,
157-        },
158-    }
159-
160-    started = time.time()
161-
162:    response = requests.post(
163-        OLLAMA_URL,
164-        json=payload,
165-        timeout=1800,
166-    )
167-
168-    elapsed = time.time() - started
169-
170:    if response.status_code != 200:
171:        raise RuntimeError(response.text)
172-
173:    data = response.json()
174-
175-    # Ollama performance diagnostics
176-    stats = {
177-        "total_duration_sec": round(
178-            data.get("total_duration", 0) / 1e9, 2
179-        ),
180-        "load_duration_sec": round(
181-            data.get("load_duration", 0) / 1e9, 2
182-        ),
183-        "prompt_eval_duration_sec": round(
184-            data.get("prompt_eval_duration", 0) / 1e9, 2
185-        ),
186-        "eval_duration_sec": round(
187-            data.get("eval_duration", 0) / 1e9, 2
188-        ),
189-        "prompt_eval_count": data.get(
190-            "prompt_eval_count"
191-        ),
192-        "eval_count": data.get(
193-            "eval_count"
194-        ),
195-    }
196-
197-    print(
198-        "[OLLAMA]",
199-        stats,
200-        flush=True,
201-    )
202-
203-    answer = data["message"]["content"]
204-
205-    cleaned = answer.strip()
206-
207-    if cleaned.startswith("```"):
208-        cleaned = cleaned.replace("```json", "", 1)
--
290-        try:
291-
292-            result = ask(source)
293-
294-            result["address"] = source.parent.name
295-            result["source_file"] = str(
296-                source.relative_to(PROJECT)
297-            )
298-
299-            with open(
300-                destination,
301-                "w",
302-                encoding="utf-8"
303-            ) as f:
304-
305:                json.dump(
306-                    result,
307-                    f,
308-                    ensure_ascii=False,
309-                    indent=2
310-                )
311-
312-            elapsed = result.get(
313-                "_time_sec",
314-                0
315-            )
316-
317-            print(
318-                "OK",
319-                "| time:",
320-                elapsed,
321-                "sec",
322:                "| client:",
323:                result.get("client", ""),
324:                "| brand:",
325:                result.get("brand", ""),
326-                "| confidence:",
327-                result.get("confidence", "")
328-            )
329-
330-            quality = result.get(
331-                "image_quality",
332-                {}
333-            )
334-
335-            print(
336-                "QUALITY:",
337-                quality.get("overall", ""),
338-                "| sharpness:",
339-                quality.get("sharpness", ""),
340-                "| banner:",
341-                quality.get("banner_visible", "")
342-            )
343-
344-            environment = result.get(
345-                "environment",
346-                {}
347-            )
348-
349-            print(
350-                "ENV:",
351-                environment.get("season", ""),
352-                "|",
353-                environment.get("weather", ""),
354-                "|",
355-                environment.get("precipitation", "")
356-            )
357-
358-            results.append({
359-                "file": source.name,
360-                "address": source.parent.name,
361-                "status": "ok",
362-                "time_sec": elapsed,
363:                "client": result.get("client", ""),
364:                "brand": result.get("brand", ""),
365-                "category": result.get("category", ""),
366-                "confidence": result.get("confidence", ""),
367-            })
368-
369-        except Exception as error:
370-
371-            print(
372-                "ERROR:",
373-                error
374-            )
375-
376-            results.append({
377-                "file": source.name,
378-                "address": source.parent.name,
379-                "status": "error",
380-                "error": str(error),
381-            })
382-
383-    total_elapsed = round(
384-        time.time() - total_start,
385-        2
386-    )
387-
388-    summary = {
389:        "model": MODEL,
390-        "input": str(INPUT_DIR),
391-        "output": str(OUTPUT_DIR),
392-        "files_in_run": len(files),
393-        "elapsed_sec": total_elapsed,
394-        "results": results,
395-    }
396-
397-    with open(
398-        OUTPUT_DIR / "summary.json",
399-        "w",
400-        encoding="utf-8"
401-    ) as f:
402-
403:        json.dump(
404-            summary,
405-            f,
406-            ensure_ascii=False,
407-            indent=2
408-        )
409-
410-    print()
411-    print("=" * 80)
412-    print("DONE")
413-    print("=" * 80)
414-    print(
415-        "Processed:",
416-        sum(
417-            1
418-            for x in results
419-            if x["status"] == "ok"
420-        )
421-    )
422-    print(
423-        "Skipped:",
424-        sum(
425-            1
426-            for x in results
427-            if x["status"] == "skipped"
428-        )
429-    )
430-    print(
431-        "Errors:",
432-        sum(
433-            1
434-            for x in results
435-            if x["status"] == "error"
436-        )
437-    )
438-    print(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 14:44:53

> **Просмотр парсера и модели**
>
>
> **Просмотр парсера и модели**
>
> 
>
> Обработка заняла несколько секунд

Да. По тому, что мы уже нашли, **проблема не в `photos.py` и не в PostgreSQL как первопричине**.

Сейчас картина такая:

- 526 JSON-файлов Qwen созданы.
- 375 имеют `description`.
- 151 имеют `description: null`/пустое значение.
- Для `Вавилова52_12.JPG` записи в PostgreSQL нет вообще.
- В JSON Qwen для неё тоже:
  - `client = null`
  - `brand = null`
  - `description = null`
- При этом файл JSON существует.

То есть Qwen-скрипт **сохраняет результат, который пришёл от модели**, даже если поля оказались `null`. Надо посмотреть именно участок `ask()` после `answer = data["message"]["content"]`: там, скорее всего, есть логика очистки/парсинга JSON, и именно её нужно проверить.

У тебя сейчас команда была обрезана на `203–...`. Давай одной командой выведем **весь критический участок 203–290**, без лишнего:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '203,290p' scripts/qwen4b_output_v01.py
```

После этого уже точно скажу, **почему 151 результата стали пустыми и как исправить так, чтобы новые Qwen JSON нормально попадали в PostgreSQL и затем в карточку фото**.

---

### 👤 **User** — 2026-08-18 14:45:22

data/metadata/qwen4b/20260818_115048/87_v33/Шеболдаева8_13.json
data/metadata/qwen4b/20260818_115048/87_v33/Шеболдаева8_18.json
data/metadata/qwen4b/20260818_115048/86_v33/Радиаторный_24.json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (33).json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (15).json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (14).json
data/metadata/qwen4b/20260818_115048/86_v33/Фурмановская ул. 106 - Плиева ул. 43 А (16).json
data/metadata/qwen4b/20260818_115048/83_v33/Нагибина24_08.json
data/metadata/qwen4b/20260818_115048/83_v33/Нагибина24_07.json
data/metadata/qwen4b/20260818_115048/83_v33/Нагибина24_06.json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (55).json
data/metadata/qwen4b/20260818_115048/78_v33/Комарова13_13.json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (9).json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (56).json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (47).json
data/metadata/qwen4b/20260818_115048/78_v33/Королева пр-кт (рядом с мостом), A (6).json
data/metadata/qwen4b/20260818_115048/78_v33/Космонавтов Капустина (27).json
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -B15 -A35 -E \
'json.dump|description|client|brand|response|ollama|model|raw_json' \
scripts/qwen4b_output_v01.py | head -350
20-NUM_CTX = 16384
21-TEMPERATURE = 0
22-
23-
24-PROMPT = r"""
25-Ты анализируешь фотографию с улицы для базы наружной рекламы.
26-
27-Найди рекламный баннер и верни ТОЛЬКО JSON.
28-Не добавляй пояснений вне JSON.
29-Не повторяй информацию.
30-Не придумывай отсутствующую информацию.
31-
32-Формат:
33-
34-{
35:  "client": "",
36:  "brand": "",
37-  "category": "",
38-  "text": [],
39-  "colors": [],
40-  "objects": [],
41:  "description": "",
42-  "banner_type": "видеоэкран",
43-
44-  "environment": {
45-    "weather": "",
46-    "precipitation": "",
47-    "lighting": ""
48-  },
49-
50-  "image_quality": {
51-    "overall": "",
52-    "sharpness": "",
53-    "exposure": "",
54-    "visibility": "",
55-    "banner_visible": true,
56-    "banner_readability": "",
57-    "motion_blur": false,
58-    "occlusion": false
59-  },
60-
61-  "camera_view": {
62-    "distance": "",
63-    "angle": ""
64-  },
65-
66-  "analysis_quality": {
67-    "banner_analysis": "",
68-    "text_analysis": ""
69-  },
70-
71-  "confidence": 0
72-}
73-
74-БАННЕР:
75:client — компания, организация или заказчик.
76:brand — торговая марка, имя кандидата или рекламируемый бренд.
77-category — категория рекламы.
78-text — читаемые надписи на баннере.
79-colors — основные цвета самого баннера.
80-objects — основные изображения и предметы НА БАННЕРЕ.
81:description — краткое описание композиции баннера, максимум 300 символов.
82-banner_type — на данном этапе "видеоэкран".
83-
84-ОКРУЖЕНИЕ:
85-Определи ТОЛЬКО:
86-weather — солнечно / пасмурно / облачно / туман / неизвестно.
87-precipitation — нет / дождь / снег / мокрый снег / неизвестно.
88-lighting — яркий день / дневной свет / сумерки / ночь / искусственное освещение / неизвестно.
89-
90-Не описывай окружающую сцену.
91-Не описывай здания, дороги, автомобили, автобусы, людей,
92-дорожные знаки, провода или растительность.
93-
94-КАЧЕСТВО:
95-Оцени только качество фотографии и видимость баннера.
96-
97-overall — хорошее / удовлетворительное / плохое.
98-sharpness — резкое / слегка размыто / сильно размыто / неизвестно.
99-exposure — нормальная / пересвечено / недоэкспонировано / очень тёмное / неизвестно.
100-visibility — хорошо виден / частично виден / плохо виден / не виден.
101-banner_visible — true или false.
102-banner_readability — высокая / средняя / низкая / невозможно определить.
103-motion_blur — true или false.
104-occlusion — true или false.
105-
106-КАМЕРА:
107-distance — далеко / средняя дистанция / близко / неизвестно.
108-angle — прямо / слева / справа / сверху / снизу / косой ракурс / неизвестно.
109-
110-Если баннер не виден:
111:client = ""
112:brand = ""
113-category = ""
114-text = []
115-colors = []
116-objects = []
117:description = ""
118-banner_visible = false
119-
120-Массивы должны содержать только действительно важные элементы.
121-Не более 10 элементов в каждом массиве.
122-Не повторяй элементы.
123-
124-confidence — уверенность в анализе от 0 до 100.
125-"""
126-
127-
128-IMAGE_EXTENSIONS = {
129-    ".jpg",
130-    ".jpeg",
131-    ".png",
132-    ".webp",
133-}
134-
135-
136-def image64(path: Path) -> str:
137-    with open(path, "rb") as f:
138-        return base64.b64encode(f.read()).decode()
139-
140-
141-def ask(path: Path) -> dict:
142-
143-    payload = {
144:        "model": MODEL,
145-        "messages": [
146-            {
147-                "role": "user",
148-                "content": PROMPT,
149-                "images": [image64(path)],
150-            }
151-        ],
152-        "stream": False,
153-        "options": {
154-            "num_ctx": NUM_CTX,
155-            "temperature": TEMPERATURE,
156-            "num_predict": 500,
157-        },
158-    }
159-
160-    started = time.time()
161-
162:    response = requests.post(
163-        OLLAMA_URL,
164-        json=payload,
165-        timeout=1800,
166-    )
167-
168-    elapsed = time.time() - started
169-
170:    if response.status_code != 200:
171:        raise RuntimeError(response.text)
172-
173:    data = response.json()
174-
175-    # Ollama performance diagnostics
176-    stats = {
177-        "total_duration_sec": round(
178-            data.get("total_duration", 0) / 1e9, 2
179-        ),
180-        "load_duration_sec": round(
181-            data.get("load_duration", 0) / 1e9, 2
182-        ),
183-        "prompt_eval_duration_sec": round(
184-            data.get("prompt_eval_duration", 0) / 1e9, 2
185-        ),
186-        "eval_duration_sec": round(
187-            data.get("eval_duration", 0) / 1e9, 2
188-        ),
189-        "prompt_eval_count": data.get(
190-            "prompt_eval_count"
191-        ),
192-        "eval_count": data.get(
193-            "eval_count"
194-        ),
195-    }
196-
197-    print(
198-        "[OLLAMA]",
199-        stats,
200-        flush=True,
201-    )
202-
203-    answer = data["message"]["content"]
204-
205-    cleaned = answer.strip()
206-
207-    if cleaned.startswith("```"):
208-        cleaned = cleaned.replace("```json", "", 1)
--
290-        try:
291-
292-            result = ask(source)
293-
294-            result["address"] = source.parent.name
295-            result["source_file"] = str(
296-                source.relative_to(PROJECT)
297-            )
298-
299-            with open(
300-                destination,
301-                "w",
302-                encoding="utf-8"
303-            ) as f:
304-
305:                json.dump(
306-                    result,
307-                    f,
308-                    ensure_ascii=False,
309-                    indent=2
310-                )
311-
312-            elapsed = result.get(
313-                "_time_sec",
314-                0
315-            )
316-
317-            print(
318-                "OK",
319-                "| time:",
320-                elapsed,
321-                "sec",
322:                "| client:",
323:                result.get("client", ""),
324:                "| brand:",
325:                result.get("brand", ""),
326-                "| confidence:",
327-                result.get("confidence", "")
328-            )
329-
330-            quality = result.get(
331-                "image_quality",
332-                {}
333-            )
334-
335-            print(
336-                "QUALITY:",
337-                quality.get("overall", ""),
338-                "| sharpness:",
339-                quality.get("sharpness", ""),
340-                "| banner:",
341-                quality.get("banner_visible", "")
342-            )
343-
344-            environment = result.get(
345-                "environment",
346-                {}
347-            )
348-
349-            print(
350-                "ENV:",
351-                environment.get("season", ""),
352-                "|",
353-                environment.get("weather", ""),
354-                "|",
355-                environment.get("precipitation", "")
356-            )
357-
358-            results.append({
359-                "file": source.name,
360-                "address": source.parent.name,
361-                "status": "ok",
362-                "time_sec": elapsed,
363:                "client": result.get("client", ""),
364:                "brand": result.get("brand", ""),
365-                "category": result.get("category", ""),
366-                "confidence": result.get("confidence", ""),
367-            })
368-
369-        except Exception as error:
370-
371-            print(
372-                "ERROR:",
373-                error
374-            )
375-
376-            results.append({
377-                "file": source.name,
378-                "address": source.parent.name,
379-                "status": "error",
380-                "error": str(error),
381-            })
382-
383-    total_elapsed = round(
384-        time.time() - total_start,
385-        2
386-    )
387-
388-    summary = {
389:        "model": MODEL,
390-        "input": str(INPUT_DIR),
391-        "output": str(OUTPUT_DIR),
392-        "files_in_run": len(files),
393-        "elapsed_sec": total_elapsed,
394-        "results": results,
395-    }
396-
397-    with open(
398-        OUTPUT_DIR / "summary.json",
399-        "w",
400-        encoding="utf-8"
401-    ) as f:
402-
403:        json.dump(
404-            summary,
405-            f,
406-            ensure_ascii=False,
407-            indent=2
408-        )
409-
410-    print()
411-    print("=" * 80)
412-    print("DONE")
413-    print("=" * 80)
414-    print(
415-        "Processed:",
416-        sum(
417-            1
418-            for x in results
419-            if x["status"] == "ok"
420-        )
421-    )
422-    print(
423-        "Skipped:",
424-        sum(
425-            1
426-            for x in results
427-            if x["status"] == "skipped"
428-        )
429-    )
430-    print(
431-        "Errors:",
432-        sum(
433-            1
434-            for x in results
435-            if x["status"] == "error"
436-        )
437-    )
438-    print(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '203,290p' scripts/qwen4b_output_v01.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 14:45:22

Вот теперь причина практически очевидна.

`qwen4b_output_v01.py` **сам не превращает поля в `null`**. Он делает:

```python
result = json.loads(cleaned)
```

и затем без изменений пишет результат через `json.dump()`.

Значит, для этих 151 фотографий **сам Qwen вернул JSON с `null`**, либо вернул JSON с такими значениями после анализа изображения.

Но есть ещё более важный момент: сейчас скрипт считает такой результат успешным:

```text
OK
```

даже если:

```json
"client": null,
"brand": null,
"description": null
```

То есть проблема скрывается.

### Я бы сейчас не трогал PostgreSQL и `photos.py`

Сначала надо проверить **один конкретный плохой файл непосредственно через Qwen**, например `Вавилова52_12.JPG`, и увидеть настоящий ответ модели.

Давай одной командой:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python - <<'PY'
from pathlib import Path
from scripts.qwen4b_output_v01 import ask

p = Path("data/output/daily/20260818_115048/95_v33/Вавилова52_12.JPG")

print("=" * 80)
print("QWEN DIRECT TEST")
print("=" * 80)
print("FILE:", p)
print()

result = ask(p)

import json
print(json.dumps(result, ensure_ascii=False, indent=2))
PY
```

**Это ключевой тест.**

Если здесь Qwen вернёт нормальный `description`, значит проблема была в конкретном запуске/файле JSON.

Если прямо здесь получим:

```json
"description": null
```

или пустой `description`, тогда уже будем исправлять `ask()`/промпт.

И после этого я предлагаю сделать нормальную защиту:

**валидный JSON + обязательные ключевые поля → OK**

**JSON есть, но `description/client/brand` пустые → RETRY**

**после повторной попытки всё ещё пусто → записываем `status: incomplete`**

Тогда такие 151 фотографии больше не будут незаметно проходить как успешно обработанные.

---

### 👤 **User** — 2026-08-18 14:46:01

QWEN DIRECT TEST
================================================================================
FILE: data/output/daily/20260818_115048/95_v33/Вавилова52_12.JPG

[OLLAMA] {'total_duration_sec': 13.51, 'load_duration_sec': 2.71, 'prompt_eval_duration_sec': 4.43, 'eval_duration_sec': 6.03, 'prompt_eval_count': 4834, 'eval_count': 500}
{
  "raw_answer": "{\n  \"client\": \"ООО «Интернет Решений»\",\n  \"brand\": \"Ozon fresh\",\n  \"category\": \"продукты\",\n  \"text\": [\n    \"189₽\",\n    \"БЕДРО ПО-КАВКАЗСКИ\",\n    \"Благохр\",\n    \"OZON fresh\",\n    \"ООО «Интернет Решений»\",\n    \"12312, г. Москва, Пресненская наб., д. 10, эт. 41, пом. 1, комн. 6; ОТР 1027739244741\",\n    \"ПЕРИОД ПРОВЕДЕНИЯ АКЦИИ 08.07-21.07.26. ПОДРОБНЕЕ\",\n    \"НА OZON.RU КОЛИЧЕСТВО ТОВАРА ОГРАНИЧЕНО\"\n  ],\n  \"colors\": [\n    \"розовый\",\n    \"голубой\",\n    \"зеленый\"\n  ],\n  \"objects\": [\n    \"упаковка мяса\",\n    \"яблоко\"\n  ],\n  \"description\": \"Рекламный баннер с ценой 189₽ на продукт «Благохр» и логотипом Ozon fresh. Визуально разделен на три цвета: розовый, голубой и зеленый. На баннере также указаны адрес и сроки акции.\",\n  \"banner_type\": \"видеоэкран\",\n  \"environment\": {\n    \"weather\": \"облачно\",\n    \"precipitation\": \"нет\",\n    \"lighting\": \"дневной свет\"\n  },\n  \"image_quality\": {\n    \"overall\": \"хорошее\",\n    \"sharpness\": \"резкое\",\n    \"exposure\": \"нормальная\",\n    \"visibility\": \"хорошо виден\",\n    \"banner_visible\": true,\n    \"banner_readability\": \"высокая\",\n    \"motion_blur\": false,\n    \"occlusion\": false\n  },\n  \"camera_view\": {\n    \"distance\": \"с",
  "_time_sec": 13.53
}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

