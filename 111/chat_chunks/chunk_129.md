## СЕССИЯ: вторник

**Создано:** 2026-08-18 18:12:03
**Обновлено:** 2026-08-22 20:16:20
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1)

---

### 🤖 **Assistant** — 2026-08-18 21:14:51

Да. Тогда сейчас логично сделать **единый интегратор входящих фото**, а не привязывать процесс к `data/input/daily`.

### Целевая схема

```text
                 ┌──────────────────────┐
                 │   Папка / источник   │
                 │  новые фотографии    │
                 └──────────┬───────────┘
                            │
             ┌──────────────▼──────────────┐
             │       INTEGRATOR             │
             │                              │
             │  1. обнаружить новый файл   │
             │  2. создать photo_id        │
             │  3. записать в PostgreSQL    │
             │  4. передать дальше          │
             └──────────────┬──────────────┘
                            │
                 photo_id = PH_00000123
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
          DINO / сортировка             Qwen
              │                           │
              └─────────────┬─────────────┘
                            ▼
                    запись photos
                            │
                            ▼
                     сортировка
                            │
                            ▼
                    превью / thumbnails
                            │
                            ▼
                         ГРИД
```

И важный момент: **грид вообще не должен смотреть непосредственно во входную папку**.

Он показывает только то, что уже прошло регистрацию/сортировку и существует в БД.

---

## `photo_id`

Я бы оставил именно:

```text
PH_00000001
PH_00000002
PH_00000003
...
```

и в PostgreSQL:

```sql
photo_id TEXT PRIMARY KEY
```

При этом внутренний `id` можно вообще убрать из логики приложения. Если пока оставляем `id INTEGER`, это не мешает — но **идентификатором фотографии для DINO/Qwen/грида становится `photo_id`**.

---

# Как должен работать интегратор

У него будет три режима.

### 1. Ручной запуск

Кнопка:

```text
[ ПРОВЕРИТЬ НОВЫЕ ФОТО ]
```

Интегратор сканирует заданную папку.

Например:

```text
data/input/
```

или любую папку, которую укажем в настройках.

Находит новые изображения.

---

### 2. Периодический запуск

Например:

```text
каждые 30 секунд
```

или:

```text
каждые 5 минут
```

Интегратор:

```text
сканирует
   ↓
находит новые
   ↓
регистрирует
   ↓
запускает обработку
```

---

### 3. Расписание

Например:

```text
08:00
12:00
18:00
```

или один раз ночью.

Это уже можно сделать отдельной настройкой.

---

# Главное — файл регистрируется ДО DINO

Например появился:

```text
data/input/incoming/IMG_18372.JPG
```

Интегратор сразу делает:

```text
PH_00000101
```

и создаёт запись:

```text
photo_id      PH_00000101
filename      IMG_18372
path          ...
address       NULL
client        NULL
qwen_status   pending
dino_status   pending
sort_status   pending
```

То есть **фотография уже существует в системе**, хотя ещё неизвестно, к какому адресу она относится.

---

# Потом DINO

DINO получает:

```text
photo_id = PH_00000101
path = ...
```

и возвращает:

```text
PH_00000101
    ↓
85_v33
    ↓
confidence / score
```

После Hybrid:

```text
photo_id      PH_00000101
address       85_v33
dino_status   ok
```

---

# Потом Qwen

Qwen тоже работает не с именем файла как идентификатором, а с:

```text
PH_00000101
```

Например:

```text
photo_id       PH_00000101
qwen_status    ok
description    ...
objects_json   ...
colors_json    ...
```

Таким образом, если файл потом переименовали:

```text
IMG_18372.JPG
```

→

```text
Ашхабадский_11.JPG
```

**ничего не ломается.**

`photo_id` остаётся:

```text
PH_00000101
```

---

# И это особенно важно для ручного исправления

Ты правильно сказал:

> имя потом можно менять у файла, если он неправильно отсортирован — по похожести, надо иметь возможность изменить имя и адресную папку

Значит:

```text
photo_id
     │
     ├── filename
     ├── path
     ├── address
     ├── client
     ├── DINO
     ├── Qwen
     └── preview
```

`filename` и `path` — **изменяемые свойства**.

`photo_id` — **неизменяемый идентификатор объекта**.

---

# А грид

Тут я полностью согласен с твоей логикой.

Грид строится не так:

```text
найти все JPG → показать
```

а так:

```text
PostgreSQL
    ↓
выбрать зарегистрированные фотографии
    ↓
применить чекбоксы адресов
    ↓
применить чекбоксы клиентов
    ↓
поиск
    ↓
проверить существование файла
    ↓
показать preview
```

Поэтому чекбокс:

```text
☑ 78_v33
☐ 79_v33
☑ 85_v33
```

означает:

```sql
WHERE address IN ('78_v33', '85_v33')
```

И **фото без присвоенного адреса туда вообще не попадает**, если только специально не сделать фильтр:

```text
☐ Без адреса
```

Это будет очень удобно для контроля ошибок.

---

# Превью

Да — **создавать превью в конце сортировки** сейчас даже правильнее.

То есть:

```text
вход
 ↓
photo_id
 ↓
DINO
 ↓
Hybrid
 ↓
адрес
 ↓
копирование в конечную папку
 ↓
обновление path/address в БД
 ↓
создание preview
 ↓
готово
```

Грид получает только:

```text
photo_id
path
preview_path
address
client
...
```

И никаких временных фотографий из входной папки.

---

## Что предлагаю сделать сейчас

Не трогать пока сам алгоритм **Hybrid v12**.

Сделать новый слой:

```text
scripts/photo_integrator.py
```

который отвечает только за:

1. поиск новых изображений;
2. генерацию `photo_id`;
3. регистрацию в PostgreSQL;
4. защиту от повторной регистрации;
5. передачу зарегистрированных фото в существующий DINO/Hybrid;
6. получение результата сортировки;
7. обновление `address/path`;
8. запуск создания preview;
9. запись состояния обработки.

А запускать его можно будет тремя способами:

```text
WEB:
[ ПРОВЕРИТЬ НОВЫЕ ФОТО ]

AUTO:
каждые N секунд

SCHEDULE:
по расписанию
```

И самое важное — **`run_daily_hybrid_v12.sh` больше не будет центральной точкой системы**. Он останется старым тестовым/совместимым запуском, а новым входом станет интегратор.

Следующим шагом я бы сделал **схему PostgreSQL + `photo_integrator.py`**, причем сначала только регистрацию `photo_id` и состояния, **без изменения DINO и Qwen**. Это позволит проверить фундамент, не ломая уже работающий Hybrid v12.

---

### 👤 **User** — 2026-08-18 21:15:56

в принципе таким образом после поступления новго файла - он в фоне пойдет на сортировку дино и квен, потом новый. новые файлы будут становится в очередь, не надо запускать много процуеесов

---

### 🤖 **Assistant** — 2026-08-18 21:15:56

Да. Именно так я бы и построил финальную архитектуру.

Не запускать отдельный DINO/Qwen-процесс на каждый новый файл, а сделать **один постоянный фоновой обработчик с очередью**.

```text
                 ВХОДНАЯ ПАПКА
                       │
                обнаружен новый файл
                       │
                       ▼
              ┌─────────────────┐
              │   INTEGRATOR    │
              │ создаёт photo_id│
              └────────┬────────┘
                       │
                       ▼
                    ОЧЕРЕДЬ
              ┌─────────────────┐
              │ PH_00000101     │
              │ PH_00000102     │
              │ PH_00000103     │
              │ PH_00000104     │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ WORKER          │
              │ DINO → QWEN     │
              └────────┬────────┘
                       │
                       ▼
                  СОРТИРОВКА
                       │
                       ▼
                  PREVIEW
                       │
                       ▼
                     ГРИД
```

### Причём worker один

Например пришли одновременно 20 фотографий:

```text
PH_00000101
PH_00000102
...
PH_00000120
```

не будет:

```text
20 × DINO
20 × Qwen
```

Будет:

```text
QUEUE
  ↓
worker
  ├─ PH_00000101
  ├─ PH_00000102
  ├─ PH_00000103
  └─ ...
```

После завершения одной фотографии берётся следующая.

---

### И можно сделать конвейер

Я бы даже разделил очереди:

```text
NEW
 ↓
DINO_QUEUE
 ↓
QWEN_QUEUE
 ↓
SORT_QUEUE
 ↓
PREVIEW_QUEUE
 ↓
DONE
```

Но **процессов всё равно не плодить**.

Например:

```text
DINO worker  = 1
QWEN worker  = 1
SORT worker  = 1
PREVIEW      = лёгкий процесс
```

При этом DINO и Qwen могут работать последовательно над одной фотографией:

```text
PH_00000101
    ↓
DINO
    ↓
адрес определён
    ↓
Qwen
    ↓
сортировка
    ↓
preview
    ↓
DONE
```

А если одновременно поступило много фотографий — они просто ждут.

---

### Ещё важнее — состояние в БД

Для каждой фотографии можно иметь:

```text
photo_id        PH_00000101

status          processing

dino_status     done
qwen_status     processing
sort_status     pending
preview_status  pending
```

После завершения:

```text
status          done

dino_status     done
qwen_status     done
sort_status     done
preview_status  done
```

Если Qwen упал:

```text
dino_status     done
qwen_status     error
sort_status     pending
preview_status  pending
```

И worker потом может повторить **только Qwen**, а не гонять DINO заново.

---

### И это решает ещё одну проблему

Если сервер перезагрузился:

```text
PH_00000101  done
PH_00000102  qwen_processing
PH_00000103  dino_pending
PH_00000104  pending
```

после запуска интегратор смотрит БД и продолжает очередь.

То есть очередь фактически можно сделать **персистентной в PostgreSQL**, а не держать только в RAM.

---

### Для грида

Пока фотография:

```text
pending
processing
```

её в обычном гриде нет.

Когда:

```text
sort_status = done
```

и появился `address` + конечный `path` + preview — она автоматически становится видимой.

Поэтому твоя исходная логика с чекбоксами адресов сохраняется:

```text
☑ 78
☐ 79
☑ 85
```

Грид показывает только **готовые фотографии с соответствующими адресами**.

А отдельный счётчик можно показывать:

```text
Очередь: 17
Обрабатывается: 1
Готово: 1264
Ошибки: 2
```

Это уже получается не «скрипт ежедневной сортировки», а **постоянно работающая фотобаза**.

И `photo_id` выдаётся **самым первым действием**, ещё до DINO и Qwen. Это я бы теперь зафиксировал как архитектурное правило.

---

### 👤 **User** — 2026-08-18 21:16:42

давай

---

### 🤖 **Assistant** — 2026-08-18 21:16:43

Да. Тогда **фиксируем архитектуру и начинаем с фундамента**.

### 1. Что сейчас не трогаем

Оставляем без изменений:

- DINO v33;
- Hybrid v12;
- Qwen;
- текущую логику чекбоксов адресов;
- текущий грид;
- текущую PostgreSQL `photos`.

Меняем только механизм поступления фотографий и их жизненный цикл.

---

### 2. Новая жизненная схема фотографии

```text
НОВЫЙ ФАЙЛ
    │
    ▼
[ INTEGRATOR ]
    │
    ├── создаёт photo_id
    │       PH_00000101
    │
    └── создаёт запись в PostgreSQL
             status = pending
    │
    ▼
       DINO QUEUE
    │
    ▼
       DINO v33
    │
    ▼
    определён адрес
    │
    ▼
       QWEN QUEUE
    │
    ▼
       QWEN 4B
    │
    ▼
      SORTING
    │
    ▼
   PREVIEW
    │
    ▼
     DONE
    │
    ▼
     ГРИД
```

---

## 3. Поля, которые я бы добавил в `photos`

Сейчас у нас уже есть:

```text
id
photo_id
address
filename
path
client
...
qwen_status
...
```

Добавляем состояние процесса:

```sql
status
dino_status
dino_score
dino_fingerprint
sort_status
preview_status
```

И я бы добавил:

```sql
source_path
```

Потому что **исходный файл и конечный файл — это разные вещи**.

Например:

```text
source_path
data/input/incoming/IMG_18372.JPG

path
data/output/photos/85_v33/Ашхабадский_11.JPG
```

---

## 4. Статусы

### Общий

```text
pending
processing
done
error
```

### DINO

```text
pending
processing
done
error
```

### Qwen

```text
pending
processing
done
error
```

### Sorting

```text
pending
processing
done
error
```

### Preview

```text
pending
processing
done
error
```

---

## 5. Очередь

Отдельную таблицу очереди на первом этапе я бы **не делал**.

PostgreSQL `photos` сама является очередью.

Например:

```sql
SELECT *
FROM photos
WHERE dino_status = 'pending'
ORDER BY id
LIMIT 1;
```

Worker берёт первую фотографию.

После обработки:

```text
dino_status = done
```

и следующая автоматически становится первой.

Это очень просто и надёжно.

---

## 6. Защита от повторного добавления

Это обязательно.

Интегратор обнаруживает:

```text
IMG_18372.JPG
```

Но если он просканирует папку ещё через 30 секунд, вторую запись создавать нельзя.

Поэтому нужен уникальный ключ.

Я бы сделал:

```sql
UNIQUE(source_path)
```

А `photo_id`:

```text
PH_00000001
PH_00000002
...
```

— уникальный постоянный идентификатор объекта.

---

## 7. Что делать с переименованием

После сортировки:

```text
PH_00000101
```

может быть:

```text
85_v33/IMG_18372.JPG
```

а оператор потом исправил:

```text
85_v33/Ашхабадский_11.JPG
```

В БД:

```text
photo_id = PH_00000101   ← НЕ МЕНЯЕТСЯ
address   = 85_v33       ← можно изменить
filename  = Ашхабадский_11 ← можно изменить
path      = новый путь    ← можно изменить
```

DINO/Qwen привязаны к `photo_id`, а не к имени файла.

Это как раз решает твою задачу.

---

## 8. Следующий конкретный шаг

Я предлагаю сейчас **не писать ещё весь worker**.

Сначала сделать миграцию PostgreSQL:

```text
photos
 ├─ photo_id
 ├─ source_path
 ├─ status
 ├─ dino_status
 ├─ dino_score
 ├─ dino_fingerprint
 ├─ qwen_status
 ├─ sort_status
 └─ preview_status
```

Потом отдельный:

```text
scripts/photo_integrator.py
```

который пока умеет только:

```text
сканировать папку
      ↓
найти новые фото
      ↓
выдать PH_xxxxxxxx
      ↓
записать в PostgreSQL
      ↓
показать очередь
```

**DINO/Qwen на этом шаге вообще не запускаем.**

Проверяем, что 10–20 новых фотографий корректно получают ID и повторное сканирование их не дублирует.

После этого подключаем к этой очереди существующий `run_hybrid_v12.py`.

Это безопаснее: мы не ломаем уже рабочее распознавание, а постепенно ставим вокруг него новый постоянный конвейер.

---

### 👤 **User** — 2026-08-18 21:17:18

далее

---

### 🤖 **Assistant** — 2026-08-18 21:17:23

Да. Идём дальше — **сначала ставим фундамент очереди**, не вмешиваясь пока в DINO/Qwen.

Сейчас у нас уже 100 записей с корректными `photo_id`, поэтому миграцию делаем поверх существующей БД.

## Шаг 1. Добавляем поля процесса

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -h localhost -p 5432 -U lora -d photobase <<'SQL'

-- ------------------------------------------------------------
-- 1. Последовательность для постоянных photo_id
-- ------------------------------------------------------------

CREATE SEQUENCE IF NOT EXISTS photos_photo_id_seq;

SELECT setval(
    'photos_photo_id_seq',
    COALESCE(
        (
            SELECT MAX(
                CAST(
                    SUBSTRING(photo_id FROM '[0-9]+$')
                    AS BIGINT
                )
            )
            FROM photos
            WHERE photo_id IS NOT NULL
        ),
        0
    )
);

-- ------------------------------------------------------------
-- 2. Поля жизненного цикла
-- ------------------------------------------------------------

ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS source_path TEXT;

ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS status TEXT
        DEFAULT 'pending';

ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS dino_status TEXT
        DEFAULT 'pending';

ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS dino_score DOUBLE PRECISION;

ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS dino_fingerprint TEXT;

ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS sort_status TEXT
        DEFAULT 'pending';

ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS preview_status TEXT
        DEFAULT 'pending';

-- ------------------------------------------------------------
-- 3. Для старых фотографий source_path = текущий path
-- ------------------------------------------------------------

UPDATE photos
SET source_path = path
WHERE source_path IS NULL;

-- ------------------------------------------------------------
-- 4. Новые photo_id будут создаваться автоматически
-- ------------------------------------------------------------

ALTER TABLE photos
    ALTER COLUMN photo_id
    SET DEFAULT (
        'PH_' ||
        LPAD(
            nextval('photos_photo_id_seq')::TEXT,
            8,
            '0'
        )
    );

-- ------------------------------------------------------------
-- 5. Уникальность
-- ------------------------------------------------------------

CREATE UNIQUE INDEX IF NOT EXISTS
    ux_photos_photo_id
ON photos(photo_id);

CREATE UNIQUE INDEX IF NOT EXISTS
    ux_photos_source_path
ON photos(source_path);

-- ------------------------------------------------------------
-- 6. Индексы очередей
-- ------------------------------------------------------------

CREATE INDEX IF NOT EXISTS
    idx_photos_dino_queue
ON photos(dino_status, id);

CREATE INDEX IF NOT EXISTS
    idx_photos_qwen_queue
ON photos(qwen_status, id);

CREATE INDEX IF NOT EXISTS
    idx_photos_sort_queue
ON photos(sort_status, id);

CREATE INDEX IF NOT EXISTS
    idx_photos_preview_queue
ON photos(preview_status, id);

SQL
```

---

# Шаг 2. Проверяем

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT id, photo_id, status, dino_status, qwen_status, sort_status, preview_status, source_path FROM photos ORDER BY id LIMIT 5;"
```

Для существующих 100 фотографий ожидаем примерно:

```text
 id |  photo_id   | status  | dino_status | qwen_status | sort_status | preview_status
----+-------------+---------+-------------+-------------+-------------+---------------
  1 | PH_00000001 | pending | pending     | ok          | pending     | pending
  2 | PH_00000002 | pending | pending     | ok          | pending     | pending
 ...
```

Но тут есть один нюанс: **старые 100 фотографий уже прошли DINO/Qwen**, поэтому после проверки мы их потом приведём в соответствующие `done`, а не оставим как pending.

---

# Шаг 3. Самое важное — интегратор

Создадим:

```text
scripts/photo_integrator.py
```

Его первая версия будет делать только это:

```text
папка
 ↓
найти JPG/JPEG/PNG/WEBP
 ↓
проверить source_path
 ↓
новый?
 ├─ нет → пропустить
 └─ да
      ↓
   INSERT photos
      ↓
   PostgreSQL выдаёт
   PH_00000101
```

Причём **никакого DINO и Qwen внутри интегратора пока нет**.

Это принципиально: сначала проверяем механизм регистрации.

Создай файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat > scripts/photo_integrator.py <<'PY'
#!/usr/bin/env python3

import argparse
from pathlib import Path

import psycopg2

PROJECT = Path(__file__).resolve().parent.parent

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

def find_images(input_dir: Path):

    return sorted(
        p
        for p in input_dir.rglob("*")
        if (
            p.is_file()
            and p.suffix.lower() in IMAGE_EXTENSIONS
        )
    )

def register_new_photos(input_dir: Path):

    images = find_images(input_dir)

    print("=" * 80)
    print("PHOTO INTEGRATOR")
    print("=" * 80)
    print("INPUT :", input_dir)
    print("FILES :", len(images))
    print()

    if not images:
        print("Новых изображений не найдено.")
        return []

    registered = []

    with psycopg2.connect(**PG_CONFIG) as conn:

        with conn.cursor() as cur:

            for image in images:

                source_path = str(
                    image.resolve()
                )

                # ------------------------------------------------
                # Уже зарегистрирована?
                # ------------------------------------------------

                cur.execute(
                    """
                    SELECT
                        photo_id,
                        status
                    FROM photos
                    WHERE source_path = %s
                    """,
                    (source_path,),
                )

                existing = cur.fetchone()

                if existing:

                    print(
                        f"[EXISTS] {existing[0]:15s} "
                        f"{image.name}"
                    )

                    continue

                # ------------------------------------------------
                # Новая фотография
                # ------------------------------------------------

                cur.execute(
                    """
                    INSERT INTO photos (
                        filename,
                        path,
                        source_path,
                        status,
                        dino_status,
                        qwen_status,
                        sort_status,
                        preview_status
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        'pending',
                        'pending',
                        'pending',
                        'pending',
                        'pending'
                    )
                    RETURNING
                        id,
                        photo_id
                    """,
                    (
                        image.stem,
                        source_path,
                        source_path,
                    ),
                )

                row_id, photo_id = cur.fetchone()

                registered.append(
                    {
                        "id": row_id,
                        "photo_id": photo_id,
                        "path": source_path,
                        "filename": image.name,
                    }
                )

                print(
                    f"[NEW]    {photo_id:15s} "
                    f"{image.name}"
                )

    print()
    print("=" * 80)
    print(f"REGISTERED: {len(registered)}")
    print("=" * 80)

    return registered

def main():

    parser = argparse.ArgumentParser(
        description="Register new photos in PostgreSQL"
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    input_dir = args.input.expanduser().resolve()

    if not input_dir.exists():
        raise RuntimeError(
            f"Папка не существует: {input_dir}"
        )

    register_new_photos(input_dir)

if __name__ == "__main__":
    main()
PY

chmod +x scripts/photo_integrator.py
```

---

# Шаг 4. Тестируем на отдельной папке

Например:

```bash
mkdir -p data/input/incoming_test
```

Положим туда пару фотографий.

Потом:

```bash
uv run python scripts/photo_integrator.py \
    --input data/input/incoming_test
```

Должно получиться:

```text
================================================================================
PHOTO INTEGRATOR
================================================================================
INPUT : .../data/input/incoming_test
FILES : 2

[NEW]    PH_00000101    IMG_001.JPG
[NEW]    PH_00000102    IMG_002.JPG

================================================================================
REGISTERED: 2
================================================================================
```

И сразу проверяем:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT id, photo_id, filename, source_path, status, dino_status, qwen_status, sort_status, preview_status FROM photos ORDER BY id DESC LIMIT 5;"
```

---

## И здесь уже появляется правильная архитектура

Например:

```text
PH_00000101
```

создан **до DINO**.

Потом worker возьмёт:

```text
PH_00000101
status=pending
dino_status=pending
```

и передаст фотографию в существующий Hybrid v12.

После этого:

```text
dino_status=done
dino_fingerprint=85_v33
dino_score=...
```

Затем Qwen:

```text
qwen_status=processing
```

→

```text
qwen_status=done
```

Потом сортировка:

```text
sort_status=done
address=85_v33
path=data/output/...
```

И только после этого:

```text
preview_status=done
status=done
```

**Именно после `sort_status=done` фотография становится кандидатом для обычного грида.**

Следующим шагом после проверки этого теста сделаем **один постоянный worker очереди**, который будет брать `dino_status='pending'` по одному `photo_id` и запускать существующий DINO/Hybrid, не создавая десятки параллельных процессов.

---

### 👤 **User** — 2026-08-18 21:18:00

id |  photo_id   | status  | dino_status | qwen_status | sort_status | preview_status |                     source_path                     
----+-------------+---------+-------------+-------------+-------------+----------------+-----------------------------------------------------
  1 | PH_00000001 | pending | pending     | ok          | pending     | pending        | data/output/test_sorted_v2/78_v33/Комарова13_01.JPG
  2 | PH_00000002 | pending | pending     | ok          | pending     | pending        | data/output/test_sorted_v2/78_v33/Комарова13_02.JPG
  3 | PH_00000003 | pending | pending     | ok          | pending     | pending        | data/output/test_sorted_v2/78_v33/Комарова13_03.JPG
  4 | PH_00000004 | pending | pending     | ok          | pending     | pending        | data/output/test_sorted_v2/78_v33/Комарова13_04.JPG
  5 | PH_00000005 | pending | pending     | ok          | pending     | pending        | data/output/test_sorted_v2/78_v33/Комарова13_05.JPG
(5 rows)

(END)

---

### 🤖 **Assistant** — 2026-08-18 21:18:01

Да, вижу. **Это ожидаемый промежуточный результат, но старые 100 фото сейчас нельзя оставлять такими.** Мы случайно применили новые `pending`-статусы к уже обработанным фотографиям.

Сейчас:

```text
DINO      pending   ← неправильно для старых фото
QWEN      ok        ← уже обработан
SORT      pending   ← неправильно
PREVIEW   pending
STATUS    pending
```

Новые фотографии должны иметь такую схему:

```text
pending
pending
pending
pending
pending
```

А **старые 100**, которые уже находятся в `test_sorted_v2` и имеют Qwen `ok`, нужно обозначить как готовые.

### Сначала ничего не запускаем

Выполни:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c "
UPDATE photos
SET
    status = 'done',
    dino_status = 'done',
    sort_status = 'done',
    preview_status = 'pending'
WHERE
    qwen_status = 'ok'
    AND path LIKE 'data/output/test_sorted_v2/%';
"
```

Почему `preview_status = 'pending'`?

Потому что мы договорились, что **превью теперь создаём в конце сортировки**, а существующие 100 могли ещё не иметь нового preview-механизма. Не будем притворяться, что они готовы.

Проверим:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c "
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE status = 'done') AS done,
    COUNT(*) FILTER (WHERE dino_status = 'done') AS dino_done,
    COUNT(*) FILTER (WHERE qwen_status = 'ok') AS qwen_done,
    COUNT(*) FILTER (WHERE sort_status = 'done') AS sorted,
    COUNT(*) FILTER (WHERE preview_status = 'pending') AS preview_pending
FROM photos;
"
```

Ожидаем примерно:

```text
total | done | dino_done | qwen_done | sorted | preview_pending
------+-----+-----------+-----------+--------+----------------
100   | 100 | 100       | 100       | 100    | 100
```

### Но есть ещё один важный момент

Я бы **не запускал пока worker**.

Сначала надо привести `photo_integrator.py` к правильной логике:

```text
НОВЫЙ ФАЙЛ
   ↓
photo_id
   ↓
БД
   ↓
dino_status=pending
qwen_status=pending
sort_status=pending
preview_status=pending
   ↓
очередь
```

А для старого набора:

```text
старые 100
   ↓
уже обработаны
   ↓
done
```

После этого можно безопасно сделать следующий слой — **`photo_worker.py`**, который будет брать ровно **одну** фотографию за раз и двигать её по конвейеру.

И тогда уже можно будет включить постоянный режим:

```text
каждые 10–30 секунд
        ↓
нашёл новые → зарегистрировал
        ↓
worker свободен?
   ├─ да → берёт следующую
   └─ нет → новые просто ждут
```

То есть **никакого запуска множества DINO/Qwen процессов**.

---

### 👤 **User** — 2026-08-18 21:18:20

можно по новой переписать базу

---

### 🤖 **Assistant** — 2026-08-18 21:18:20

Да. И я бы **сейчас именно так и сделал**. Мы ещё на этапе перестройки архитектуры, поэтому лучше не тащить старую структуру и миграции.

Сделаем PostgreSQL `photobase` с нуля под новую модель.

### Новая логика

```text id="7qk2n3"
photo_id          постоянный ID фотографии
source_path       откуда пришла
path              где лежит сейчас
filename          текущее имя
address           текущий адрес
client            клиент

status            общий статус

dino_status
dino_fingerprint
dino_score

qwen_status
qwen_time_sec
...

sort_status
preview_status

created_at
updated_at
```

`photo_id`:

```text
PH_00000001
PH_00000002
...
```

**Никогда не меняется**, даже если:

- файл переименовали;
- поменяли адрес;
- фотографию пересортировали;
- поменялся `path`.

А `filename`, `address`, `path` — изменяемые.

### И очередь

Новые:

```text
status=queued
dino_status=pending
qwen_status=pending
sort_status=pending
preview_status=pending
```

После DINO:

```text
dino_status=done
dino_fingerprint=85_v33
```

После Qwen:

```text
qwen_status=done
```

После сортировки:

```text
address=85_v33
path=...
sort_status=done
```

После preview:

```text
preview_status=done
status=done
```

### Грид

Грид берёт **только записи из этой БД**, причём обычный режим:

```text
sort_status = 'done'
```

и дальше применяет твои чекбоксы:

```text
☑ 78
☐ 79
☑ 85
```

Фото, которое только что появилось во входной папке, но ещё находится в очереди, **в гриде не появляется**.

---

Я бы также сразу добавил отдельное поле:

```text
original_filename
```

чтобы после ручного переименования всегда знать, **как файл назывался изначально**.

И `source_path` тоже не меняем — это история происхождения.

**То есть база становится центром всей системы, а файловая система — хранилищем.**

Если согласен, следующим сообщением дам **одну команду, которая полностью пересоздаст `photos`**, и сразу после неё — новую версию `photo_db.py` и интегратора под эту чистую схему.

---

### 👤 **User** — 2026-08-18 21:18:32

далее

---

### 🤖 **Assistant** — 2026-08-18 21:18:33

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed Scene Fingerprint stage, photo IDs, queues, and grid visibility rules**
>
> 
>
> Worked for 8s

Да. **Я бы сейчас не латал старую базу, а пересобрал её под новую архитектуру целиком.** Это как раз подходящий момент: у нас уже определён жизненный цикл фотографии.

### Фиксируем новую модель

Одна фотография получает `photo_id` **сразу при попадании в систему**, ещё до DINO и Qwen:

```text
новый файл
   ↓
PHOTO_ID = PH_00000001
   ↓
запись в БД
   ↓
очередь
   ├── DINO
   ├── Qwen
   ├── сортировка
   └── preview
```

И дальше `photo_id` **никогда не меняется**, даже если:

- DINO ошибся с адресом;
- фотографию перенесли в другую адресную папку;
- изменили имя файла;
- вручную исправили адрес;
- пересортировали фотографию.

То есть:

```text
photo_id = личность фотографии
filename = текущее имя
address  = текущее назначение
path     = текущее расположение
```

### Предлагаю сделать таблицу примерно такой

```sql
photos
------------------------------------------------
photo_id TEXT PRIMARY KEY

filename TEXT NOT NULL
source_path TEXT NOT NULL

address TEXT
client TEXT
brand TEXT
category TEXT
description TEXT

status TEXT
dino_status TEXT
qwen_status TEXT
sort_status TEXT
preview_status TEXT

dino_address TEXT
dino_score REAL
dino_second_score REAL
dino_margin REAL

qwen_status TEXT
qwen_time_sec REAL

preview_path TEXT

text_json JSONB
colors_json JSONB
objects_json JSONB
environment_json JSONB
image_quality_json JSONB
camera_view_json JSONB
scene_objects_json JSONB
analysis_quality_json JSONB
raw_json JSONB

created_at TIMESTAMP
updated_at TIMESTAMP
```

Но я бы **не удалял отдельно `id`**, если PostgreSQL уже его использует внутри проекта. Можно оставить технический:

```sql
id BIGSERIAL UNIQUE
```

а главным идентификатором сделать:

```sql
photo_id TEXT PRIMARY KEY
```

Например:

```text
id       = 1
photo_id = PH_00000001
```

Для DINO/Qwen используем именно:

```text
PH_00000001
```

---

### Главное изменение

Сейчас у нас логика фактически такая:

```text
файл → DINO → сортировка → Qwen → БД
```

Делаем:

```text
файл
 ↓
регистрация + PHOTO_ID
 ↓
БД: pending
 ↓
очередь
 ↓
DINO
 ↓
Qwen
 ↓
сортировка
 ↓
preview
 ↓
ready
```

И **грид берёт только `ready`/зарегистрированные отсортированные записи**, а не просто сканирует входную папку.

Это решает как раз ту проблему, о которой ты говорил: никаких фотографий «из воздуха» в гриде.

---

### Очередь

И отдельно будет таблица состояния, фактически очередь можно держать прямо в `photos`:

```text
photo_id       status       dino       qwen       sort       preview
PH_00000001    ready        done       done       done       done
PH_00000002    processing   done       running    pending    pending
PH_00000003    pending      pending    pending    pending    pending
PH_00000004    pending      pending    pending    pending    pending
```

**Один worker.**

Он берёт:

```text
pending → processing
```

обрабатывает одну фотографию и переходит к следующей.

Если одновременно пришло 100 файлов:

```text
PH_101
PH_102
PH_103
...
PH_200
```

не запускаются 100 DINO/Qwen процессов.

Просто:

```text
[worker]
   ↓
101
   ↓
102
   ↓
103
   ↓
...
```

А новые файлы добавляются в хвост очереди.

---

### И ещё важный момент

`source_path` должен означать **исходный файл**, а не обязательно его будущую сортированную позицию.

А отдельно:

```text
current_path
```

или `path` — где файл находится сейчас.

Тогда ручное исправление:

```text
PH_00001234

было:
78_v33/Комарова13_07.JPG

стало:
83_v33/Комарова13_07.JPG
```

не создаёт новую фотографию.

Меняются только:

```text
address
filename
path
```

а:

```text
photo_id = PH_00001234
```

остаётся прежним.

**Это особенно важно для будущих DINO/Qwen результатов и истории изменений.**

---

Я бы сейчас сделал именно так: **сначала полностью пересоздаём PostgreSQL `photos`, затем переписываем `import_qwen_to_db.py` уже под новую схему, а после этого делаем `photo_integrator/worker`, который выдаёт `photo_id` до запуска DINO.** Старые 100 записей можно либо заново импортировать, либо аккуратно перенести с сохранением `PH_00000001...PH_00000100`.

---

### 👤 **User** — 2026-08-18 21:19:20

в этой же базе все данные от вино и квен

---

### 🤖 **Assistant** — 2026-08-18 21:19:21

Да. **Всё держим в одной PostgreSQL базе `photobase`**, и я бы не делал отдельные БД для DINO, Qwen, сортировки или грида.

Логически одна запись `photos` — это **одна фотография и вся её история обработки**.

```text id="c2v8k1"
PH_00000101
│
├── исходный файл
├── текущий файл
├── имя
├── адрес
├── клиент
│
├── DINO
│   ├── fingerprint
│   ├── score
│   ├── second_score
│   ├── margin
│   ├── status
│   └── время обработки
│
├── HYBRID
│   ├── original_best_id
│   ├── final_best_id
│   ├── changed
│   ├── score
│   └── ...
│
├── QWEN
│   ├── status
│   ├── confidence
│   ├── description
│   ├── text
│   ├── colors
│   ├── objects
│   ├── environment
│   ├── image_quality
│   ├── camera_view
│   ├── scene_objects
│   └── raw_json
│
├── SORT
│   ├── status
│   └── ...
│
└── PREVIEW
    ├── status
    └── preview_path
```

### То есть Qwen не отдельная база

Сейчас у нас Qwen уже хранит много полезной информации:

```text id="1t8q4n"
text_json
colors_json
objects_json
environment_json
image_quality_json
camera_view_json
scene_objects_json
analysis_quality_json
raw_json
```

**Всё это оставляем в `photos`.**

И DINO туда же.

---

### Я бы только разделил поля по назначению

Например:

```text id="j5m1xq"
Идентичность
────────────────────────
photo_id
source_path
filename
path

Классификация
────────────────────────
address
client
brand
category

DINO
────────────────────────
dino_status
dino_fingerprint
dino_score
dino_second_score
dino_margin
dino_time_sec

HYBRID
────────────────────────
hybrid_original_id
hybrid_final_id
hybrid_changed
hybrid_score

QWEN
────────────────────────
qwen_status
qwen_time_sec
confidence
description
...
JSONB поля

PIPELINE
────────────────────────
status
sort_status
preview_status
created_at
updated_at
```

И это будет очень удобно для UI.

Например, открываем фотографию `PH_00000101` — и UI может показать:

```text
PH_00000101

Адрес:       85_v33
Файл:        Ашхабадский_11.JPG
Клиент:      ...

DINO
Fingerprint: 85_v33
Score:       0.914
Margin:      0.083
Status:      DONE

QWEN
Status:      DONE
Confidence:  96
Описание:   ...

Обработка
DINO:        ✓
Qwen:        ✓
Сортировка:  ✓
Preview:     ✓
```

И самое главное — **один `photo_id` проходит через весь конвейер**.

---

### Ещё один принцип я предлагаю зафиксировать

**База — источник истины.**

Не:

```text папки → грид
```

а:

```text файлы
   ↓
интегратор
   ↓
PostgreSQL
   ↓
DINO/Qwen/Sort/Preview
   ↓
PostgreSQL
   ↓
грид
```

Файловая система хранит сами изображения.

PostgreSQL знает, **что это за изображение, откуда оно пришло, что с ним сделал DINO, что увидел Qwen, куда оно отсортировано и готово ли оно для отображения**.

Это даст нам очень чистую архитектуру.

---

### 👤 **User** — 2026-08-18 21:19:46

далее

---

### 🤖 **Assistant** — 2026-08-18 21:19:46

Да. Тогда следующий шаг — **пересоздать `photos` окончательно**, уже с полным набором данных DINO + Hybrid + Qwen + очередь + сортировка + preview.

Но перед удалением старой таблицы лучше сделать резервную копию. У нас всего 100 записей, это безопасно.

### 1. Сначала backup

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
pg_dump -h localhost -p 5432 -U lora -d photobase \
  -t photos \
  > data/metadata/photos_backup_before_rebuild.sql
```

Проверим:

```bash
ls -lh data/metadata/photos_backup_before_rebuild.sql
```

---

### 2. Пересоздаём таблицу

Я предлагаю **не удалять всю БД `photobase`**, а только таблицу `photos`.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
psql -h localhost -p 5432 -U lora -d photobase <<'SQL'

DROP TABLE IF EXISTS photos CASCADE;

CREATE TABLE photos (

    -- ========================================================
    -- IDENTITY
    -- ========================================================

    id BIGSERIAL UNIQUE,

    photo_id TEXT PRIMARY KEY,

    -- ========================================================
    -- FILE
    -- ========================================================

    source_path TEXT NOT NULL,

    path TEXT NOT NULL,

    filename TEXT NOT NULL,

    original_filename TEXT,

    -- ========================================================
    -- CURRENT CLASSIFICATION
    -- ========================================================

    address TEXT,

    client TEXT,

    brand TEXT,

    category TEXT,

    description TEXT,

    -- ========================================================
    -- PIPELINE
    -- ========================================================

    status TEXT NOT NULL DEFAULT 'pending',

    dino_status TEXT NOT NULL DEFAULT 'pending',

    qwen_status TEXT NOT NULL DEFAULT 'pending',

    sort_status TEXT NOT NULL DEFAULT 'pending',

    preview_status TEXT NOT NULL DEFAULT 'pending',

    error_message TEXT,

    -- ========================================================
    -- DINO
    -- ========================================================

    dino_fingerprint TEXT,

    dino_score DOUBLE PRECISION,

    dino_second_score DOUBLE PRECISION,

    dino_margin DOUBLE PRECISION,

    dino_time_sec DOUBLE PRECISION,

    -- ========================================================
    -- HYBRID V12
    -- ========================================================

    hybrid_original_id TEXT,

    hybrid_final_id TEXT,

    hybrid_changed BOOLEAN DEFAULT FALSE,

    hybrid_old_score DOUBLE PRECISION,

    hybrid_score DOUBLE PRECISION,

    hybrid_margin DOUBLE PRECISION,

    hybrid_neighbors JSONB,

    -- ========================================================
    -- QWEN
    -- ========================================================

    confidence INTEGER,

    qwen_time_sec DOUBLE PRECISION,

    -- ========================================================
    -- QWEN JSON
    -- ========================================================

    text_json JSONB,

    colors_json JSONB,

    objects_json JSONB,

    environment_json JSONB,

    image_quality_json JSONB,

    camera_view_json JSONB,

    scene_objects_json JSONB,

    analysis_quality_json JSONB,

    raw_json JSONB,

    -- ========================================================
    -- PREVIEW
    -- ========================================================

    preview_path TEXT,

    -- ========================================================
    -- TIMESTAMPS
    -- ========================================================

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP

);

-- ============================================================
-- UNIQUE / QUEUE INDEXES
-- ============================================================

CREATE UNIQUE INDEX ux_photos_source_path
    ON photos(source_path);

CREATE INDEX idx_photos_status
    ON photos(status);

CREATE INDEX idx_photos_dino_queue
    ON photos(dino_status, id);

CREATE INDEX idx_photos_qwen_queue
    ON photos(qwen_status, id);

CREATE INDEX idx_photos_sort_queue
    ON photos(sort_status, id);

CREATE INDEX idx_photos_preview_queue
    ON photos(preview_status, id);

CREATE INDEX idx_photos_address
    ON photos(address);

CREATE INDEX idx_photos_client
    ON photos(client);

CREATE INDEX idx_photos_dino_fingerprint
    ON photos(dino_fingerprint);

CREATE INDEX idx_photos_hybrid_final
    ON photos(hybrid_final_id);

SQL
```

---

## 3. Проверяем структуру

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"\d photos"
```

Должны увидеть примерно:

```text
photo_id
source_path
path
filename
original_filename

address
client
brand
category

status
dino_status
qwen_status
sort_status
preview_status

dino_fingerprint
dino_score
dino_second_score
dino_margin

hybrid_original_id
hybrid_final_id
hybrid_changed
...

confidence
qwen_time_sec
text_json
colors_json
objects_json
...
preview_path

created_at
updated_at
```

---

## 4. Важное решение по `id` и `photo_id`

Я бы оставил оба.

```text
id = 1
photo_id = PH_00000001
```

Но смысл разный.

**`id`** — технический PostgreSQL ID.

**`photo_id`** — наш постоянный ID фотографии.

Для DINO/Qwen/UI/API используем:

```text
PH_00000001
```

а не внутренний `id`.

---

## 5. Старые 100 пока НЕ возвращаем

Это специально.

Сначала проверяем новую чистую базу:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT COUNT(*) FROM photos;"
```

Должно быть:

```text
 count
-------
     0
```

После этого мы **не будем импортировать старые данные старым `import_qwen_to_db.py`**, потому что он написан под старую архитектуру.

Следующий шаг — переписать его:

```text
scripts/import_qwen_to_db.py
```

чтобы он **не создавал фотографии**, а только находил уже существующий:

```text
photo_id
```

и записывал результаты Qwen в соответствующую строку.

Это принципиально важно.

Теперь порядок будет:

```text
ИНТЕГРАТОР
   ↓
создал PH_00000101
   ↓
DINO
   ↓
записал результаты в PH_00000101
   ↓
QWEN
   ↓
записал результаты в PH_00000101
   ↓
SORT
   ↓
обновил path/address
   ↓
PREVIEW
   ↓
status = ready
```

**То есть ни один следующий модуль больше не создаёт новую запись о фотографии.** Он только обрабатывает уже существующий `photo_id`.

И это, на мой взгляд, ключевой момент всей новой архитектуры.

---

### 👤 **User** — 2026-08-18 21:21:49

у нас пока нет фотограйи с id надо написать обработчик . для проверки берем /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily

---

### 🤖 **Assistant** — 2026-08-18 21:21:50

> **Inspecting Photo Schema And Existing Scripts**
>
>
> **Inspected photo schema and existing scripts**
>
> 
>
> Worked for 4s

Да. Тогда сейчас **не трогаем DINO и Qwen**. Сначала делаем отдельный первый обработчик:

**`data/input/daily` → присвоить `photo_id` → зарегистрировать фото в PostgreSQL → оставить исходный файл на месте.**

То есть первый этап будет таким:

```text
data/input/daily
        │
        ▼
[PHOTO ID HANDLER]
        │
        ├── новый файл?
        │       │
        │       └── да → PH_00000101
        │
        ▼
PostgreSQL.photos
        │
        ├── source_path
        ├── photo_id
        ├── status = pending
        ├── dino_status = pending
        ├── qwen_status = pending
        ├── sort_status = pending
        └── preview_status = pending
```

И **никаких копирований/перемещений на этом этапе**.

Это важно: `photo_id` становится постоянным идентификатором фотографии, а `filename`, `address` и физический `path` потом можно менять.

Я бы сделал отдельный скрипт:

```text
scripts/photo_ingest.py
```

Он должен быть **идемпотентным**: если один и тот же файл уже зарегистрирован, второй раз `photo_id` ему не выдаётся.

И ещё важный момент: поскольку сейчас в базе уже есть:

```text
PH_00000001 ... PH_00000100
```

новая фотография должна получить:

```text
PH_00000101
```

а не начинать нумерацию заново.

После этого следующим этапом подключим очередь:

```text
ingest
  ↓
DINO
  ↓
Qwen
  ↓
sort
  ↓
preview
```

Причём **один worker**, а новые фотографии складываются в очередь — именно как ты предложил, без запуска десятка параллельных процессов.

Я бы сейчас написал именно **первый `photo_ingest.py` и проверил его на `/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily`**, не запуская пока DINO/Qwen.

---

### 👤 **User** — 2026-08-18 21:22:11

да

---

### 🤖 **Assistant** — 2026-08-18 21:22:12

> **Inspecting Schema And Worker Files**
>
>
> ****
>
> 
>
> **Inspected schema and worker files in the project directory**
>
> 
>
> Worked for 6s

Да. **Сейчас следующий шаг — не трогать DINO и Qwen**, а сделать первый отдельный обработчик входящих фотографий.

Логика должна быть такой:

```text
data/input/daily
        │
        ▼
[INGEST / WATCHER]
        │
        ├─ новый файл?
        │
        ├─ получить следующий photo_id
        │      PH_00000101
        │
        └─ записать в PostgreSQL
             source_path = исходный файл
             status      = pending
             dino_status = pending
             qwen_status = pending
             sort_status = pending
             preview_status = pending
                    │
                    ▼
              дальше очередь
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
        DINO                 QWEN
          │                   │
          └─────────┬─────────┘
                    ▼
                  SORT
                    ▼
                PREVIEW
```

И самое важное: **`photo_id` создаётся здесь, до запуска DINO/Qwen и больше не меняется.**

Например:

```text
PH_00000101
PH_00000102
PH_00000103
```

При этом имя файла и адрес потом могут измениться:

```text
photo_id = PH_00000101

сейчас:
source_path = data/input/daily/IMG123.JPG

после сортировки:
address = 85_v33
filename = Ашхабадский_12.JPG
path = data/output/.../85_v33/Ашхабадский_12.JPG
```

`photo_id` остаётся тем же.

### Для первой проверки

Берём только:

```text
/home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily
```

И делаем **одноразовый обработчик**, который:

1. находит все JPG/JPEG/PNG;
2. проверяет, есть ли уже такой `source_path` в БД;
3. новым файлам выдаёт `photo_id`;
4. записывает их в `photos`;
5. **ничего пока не сортирует и не запускает DINO/Qwen**.

Это позволит сначала проверить фундаментальную часть системы: **файл → постоянный ID → запись в общей БД**.

После этого уже подключим очередь и сделаем фоновой процесс, который будет последовательно брать:

```text
pending → DINO → Qwen → сортировка → preview → done
```

и при появлении 20 новых фотографий не будет запускать 20 параллельных DINO/Qwen — они будут вставать в **одну очередь**.

---

### 👤 **User** — 2026-08-18 21:22:24

ок

---

### 🤖 **Assistant** — 2026-08-18 21:22:25

Тогда фиксируем этот этап. Следующий шаг — написать `scripts/photo_ingest.py` и прогнать его **только на `data/input/daily`**, без DINO, Qwen и сортировки.

После запуска проверим в БД:

```text
photo_id | source_path | status  | dino_status | qwen_status | sort_status | preview_status
---------+-------------+---------+-------------+-------------+-------------+---------------
PH_...   | ...         | pending | pending     | pending     | pending     | pending
```

И только после этой проверки подключаем worker/очередь.

---

### 👤 **User** — 2026-08-18 21:22:34

пишем

---

### 🤖 **Assistant** — 2026-08-18 21:22:34

Да. Пишем первый рабочий обработчик. Он **ничего не перемещает**, только регистрирует новые фотографии в PostgreSQL и выдаёт им постоянный `photo_id`.

Создай файл:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && cat > scripts/photo_ingest.py <<'PY'
#!/usr/bin/env python3

import argparse
from pathlib import Path

import psycopg2

PROJECT = Path(__file__).resolve().parent.parent

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "photobase",
    "user": "lora",
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

def get_next_photo_number(conn):
    """
    Возвращает следующий числовой номер PHOTO_ID.

    Например:
        PH_00000100 -> 100
        следующий -> 101

    Если фотографий ещё нет:
        -> 1
    """

    with conn.cursor() as cur:

        cur.execute("""
            SELECT photo_id
            FROM photos
            WHERE photo_id LIKE 'PH_%'
        """)

        rows = cur.fetchall()

    max_number = 0

    for (photo_id,) in rows:

        if not photo_id:
            continue

        try:
            number = int(
                str(photo_id)
                .replace("PH_", "", 1)
            )
        except ValueError:
            continue

        max_number = max(
            max_number,
            number,
        )

    return max_number + 1

def make_photo_id(number):
    return f"PH_{number:08d}"

def normalize_path(path):
    return str(
        Path(path)
        .expanduser()
        .resolve()
    )

def get_existing_source_paths(conn):
    """
    Загружает уже зарегистрированные source_path.
    """

    with conn.cursor() as cur:

        cur.execute("""
            SELECT source_path
            FROM photos
            WHERE source_path IS NOT NULL
        """)

        return {
            normalize_path(row[0])
            for row in cur.fetchall()
            if row[0]
        }

def find_images(input_dir):
    """
    Берёт только файлы непосредственно из входной папки.
    Подкаталоги пока не сканируем.
    """

    return sorted(
        (
            p
            for p in input_dir.iterdir()
            if (
                p.is_file()
                and p.suffix.lower()
                in IMAGE_EXTENSIONS
            )
        ),
        key=lambda p: p.name.casefold(),
    )

def register_photo(
    conn,
    photo_id,
    source_path,
):
    """
    Создаёт первичную запись фотографии.

    Никаких DINO/Qwen/сортировок здесь нет.
    """

    filename = Path(source_path).name

    with conn.cursor() as cur:

        cur.execute("""
            INSERT INTO photos (
                photo_id,

                source_path,
                path,

                filename,
                original_filename,

                status,

                dino_status,
                qwen_status,
                sort_status,
                preview_status
            )
            VALUES (
                %s,

                %s,
                %s,

                %s,
                %s,

                'pending',

                'pending',
                'pending',
                'pending',
                'pending'
            )
        """, (
            photo_id,

            source_path,
            source_path,

            filename,
            filename,
        ))

def ingest(input_dir):

    input_dir = input_dir.expanduser().resolve()

    if not input_dir.exists():
        raise RuntimeError(
            f"Input directory does not exist:\n{input_dir}"
        )

    if not input_dir.is_dir():
        raise RuntimeError(
            f"Input path is not a directory:\n{input_dir}"
        )

    images = find_images(input_dir)

    print("=" * 80)
    print("PHOTO INGEST")
    print("=" * 80)
    print()
    print("INPUT :", input_dir)
    print("FILES :", len(images))
    print()

    if not images:
        print("No images found.")
        return

    with psycopg2.connect(**PG_CONFIG) as conn:

        existing_paths = get_existing_source_paths(conn)

        next_number = get_next_photo_number(conn)

        registered = 0
        skipped = 0

        for image in images:

            source_path = normalize_path(image)

            # ------------------------------------------------
            # Уже зарегистрировано
            # ------------------------------------------------

            if source_path in existing_paths:

                print(
                    f"[SKIP]     {image.name}"
                    f" — already registered"
                )

                skipped += 1

                continue

            # ------------------------------------------------
            # Новый photo_id
            # ------------------------------------------------

            photo_id = make_photo_id(
                next_number
            )

            register_photo(
                conn,
                photo_id,
                source_path,
            )

            existing_paths.add(
                source_path
            )

            print(
                f"[REGISTER] {photo_id}"
                f"  {image.name}"
            )

            registered += 1
            next_number += 1

        conn.commit()

    print()
    print("=" * 80)
    print("INGEST FINISHED")
    print("=" * 80)
    print()
    print("Found      :", len(images))
    print("Registered :", registered)
    print("Skipped    :", skipped)
    print()

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Register new photos and assign permanent photo_id"
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Directory with incoming photos",
    )

    args = parser.parse_args()

    ingest(
        args.input
    )

if __name__ == "__main__":
    main()
PY

chmod +x scripts/photo_ingest.py
```

### Запускаем на нашей тестовой папке

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python scripts/photo_ingest.py \
  --input /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily
```

После этого сразу проверяем:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT id, photo_id, status, dino_status, qwen_status, sort_status, preview_status, source_path FROM photos ORDER BY id DESC LIMIT 20;"
```

И отдельно:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT COUNT(*) AS total, COUNT(photo_id) AS with_photo_id, COUNT(DISTINCT photo_id) AS unique_photo_ids FROM photos;"
```

**Пока ничего больше не запускаем.** Пришли вывод `photo_ingest.py` и двух `SELECT` — проверим, что выдача ID работает правильно, после чего подключим следующий слой: **очередь одного worker-а**.

---

### 👤 **User** — 2026-08-18 21:24:05

e  ^E  j  ^N  CR  *  Forward  one line   (or N lines).
  y  ^Y  k  ^K  ^P  *  Backward one line   (or N lines).
  f  ^F  ^V  SPACE  *  Forward  one window (or N lines).
  b  ^B  ESC-v      *  Backward one window (or N lines).
  z                 *  Forward  one window (and set window to N).
  w                 *  Backward one window (and set window to N).
  ESC-SPACE         *  Forward  one window, but don't stop at end-of-file.
  d  ^D             *  Forward  one half-window (and set half-window to N).
  u  ^U             *  Backward one half-window (and set half-window to N).
  ESC-)  RightArrow *  Right one half screen width (or N positions).
  ESC-(  LeftArrow  *  Left  one half screen width (or N positions).
  ESC-}  ^RightArrow   Right to last column displayed.
  ESC-{  ^LeftArrow    Left  to first column.
  F                    Forward forever; like "tail -f".
  ESC-F                Like F but stop when search pattern is found.
  r  ^R  ^L            Repaint screen.
  R                    Repaint screen, discarding buffered input.
        ---------------------------------------------------
        Default "window" is the screen height.
        Default "half-window" is half of the screen height.
 ---------------------------------------------------------------------------

/bin/bash: -c: line 1: unexpected EOF while looking for matching `"'
HELP -- Press RETURN for more, or q when done

_status |                                        source_path                                        
-----+-------------+---------+-------------+-------------+-------------+----------------+-------------------------------------------------------------------------------------------
 526 | PH_00000526 | pending | pending     | pending     | pending     | pending        | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (9).JPG
 525 | PH_00000525 | pending | pending     | pending     | pending     | pending        | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (8).JPG
 524 | PH_00000524 | pending | pending     | pending     | pending     | pending        | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (7).JPG
 523 | PH_00000523 | pending | pending     | pending     | pending     | pending        | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (6).JPG
 522 | PH_00000522 | pending | pending     | pending     | pending     | pending        | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (5).JPG
 521 | PH_00000521 | pending | pending     | pending     | pending     | pending        | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (4).JPG

[REGISTER] PH_00000339  Малиновского_к_Доватора_03.JPG
[REGISTER] PH_00000340  Малиновского_к_Доватора_04.JPG
[REGISTER] PH_00000341  Малиновского_к_Доватора_05.JPG
[REGISTER] PH_00000342  Малиновского_к_Доватора_06.JPG
[REGISTER] PH_00000343  Малиновского_к_Доватора_07.JPG
[REGISTER] PH_00000344  Малиновского_к_Доватора_08.JPG
[REGISTER] PH_00000345  Малиновского_к_Доватора_09.JPG
[REGISTER] PH_00000346  Малиновского_к_Доватора_10.JPG
[REGISTER] PH_00000347  Малиновского_к_Доватора_11.JPG
[REGISTER] PH_00000348  Малиновского_к_Доватора_12.JPG
[REGISTER] PH_00000349  Малиновского_к_Доватора_13.JPG
[REGISTER] PH_00000350  Малиновского_к_Доватора_14.JPG
[REGISTER] PH_00000351  Малиновского_к_Доватора_15.JPG
[REGISTER] PH_00000352  Малиновского_к_Доватора_16.JPG
[REGISTER] PH_00000353  Малиновского_к_Стачки_01.JPG
[REGISTER] PH_00000354  Малиновского_к_Стачки_02.JPG
[REGISTER] PH_00000355  Малиновского_к_Стачки_03.JPG
[REGISTER] PH_00000356  Малиновского_к_Стачки_04.JPG
[REGISTER] PH_00000357  Малиновского_к_Стачки_05.JPG
[REGISTER] PH_00000358  Менжинского_01.JPG
[REGISTER] PH_00000359  Менжинского_02.JPG
[REGISTER] PH_00000360  Менжинского_03.JPG
[REGISTER] PH_00000361  Менжинского_04.JPG
[REGISTER] PH_00000362  Менжинского_05.JPG
[REGISTER] PH_00000363  Менжинского_06.JPG
[REGISTER] PH_00000364  Менжинского_07.JPG
[REGISTER] PH_00000365  Менжинского_08.JPG
[REGISTER] PH_00000366  Менжинского_09.JPG
[REGISTER] PH_00000367  Менжинского_10.JPG
[REGISTER] PH_00000368  Менжинского_11.JPG
[REGISTER] PH_00000369  Менжинского_12.JPG
[REGISTER] PH_00000370  Менжинского_13.JPG
[REGISTER] PH_00000371  Менжинского_14.JPG
[REGISTER] PH_00000372  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (1).JPG
[REGISTER] PH_00000373  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (10).JPG
[REGISTER] PH_00000374  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (11).JPG
[REGISTER] PH_00000375  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (12).JPG
[REGISTER] PH_00000376  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (13).JPG
[REGISTER] PH_00000377  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (14).JPG
[REGISTER] PH_00000378  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (15).JPG
[REGISTER] PH_00000379  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (2).JPG
[REGISTER] PH_00000380  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (3).JPG
[REGISTER] PH_00000381  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (4).JPG
[REGISTER] PH_00000382  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (5).JPG
[REGISTER] PH_00000383  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (6).JPG
[REGISTER] PH_00000384  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (7).JPG
[REGISTER] PH_00000385  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (8).JPG
[REGISTER] PH_00000386  Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (9).JPG
[REGISTER] PH_00000387  Нагибина24_01.JPG
[REGISTER] PH_00000388  Нагибина24_02.JPG
[REGISTER] PH_00000389  Нагибина24_03.JPG
[REGISTER] PH_00000390  Нагибина24_04.JPG
[REGISTER] PH_00000391  Нагибина24_05.JPG
[REGISTER] PH_00000392  Нагибина24_06.JPG
[REGISTER] PH_00000393  Нагибина24_07.JPG
[REGISTER] PH_00000394  Нагибина24_08.JPG
[REGISTER] PH_00000395  Нагибина24_09.JPG
[REGISTER] PH_00000396  Нагибина24_10.JPG
[REGISTER] PH_00000397  Нагибина24_11.JPG
[REGISTER] PH_00000398  Нагибина24_12.JPG
[REGISTER] PH_00000399  Нагибина24_13.JPG
[REGISTER] PH_00000400  Нагибина24_14.JPG
[REGISTER] PH_00000401  Нагибина24_15.JPG
[REGISTER] PH_00000402  Нагибина24_16.JPG
[REGISTER] PH_00000403  Нагибина24_17.JPG
[REGISTER] PH_00000404  Радиаторный_01.JPG
[REGISTER] PH_00000405  Радиаторный_02.JPG
[REGISTER] PH_00000406  Радиаторный_03.JPG
[REGISTER] PH_00000407  Радиаторный_04.JPG
[REGISTER] PH_00000408  Радиаторный_05.JPG
[REGISTER] PH_00000409  Радиаторный_06.JPG
[REGISTER] PH_00000410  Радиаторный_07.JPG
[REGISTER] PH_00000411  Радиаторный_08.JPG
[REGISTER] PH_00000412  Радиаторный_09.JPG
[REGISTER] PH_00000413  Радиаторный_10.JPG
[REGISTER] PH_00000414  Радиаторный_11.JPG
[REGISTER] PH_00000415  Радиаторный_12.JPG
[REGISTER] PH_00000416  Радиаторный_13.JPG
[REGISTER] PH_00000417  Радиаторный_14.JPG
[REGISTER] PH_00000418  Радиаторный_15.JPG
[REGISTER] PH_00000419  Радиаторный_16.JPG
[REGISTER] PH_00000420  Радиаторный_17.JPG
[REGISTER] PH_00000421  Радиаторный_18.JPG
[REGISTER] PH_00000422  Радиаторный_19.JPG
[REGISTER] PH_00000423  Радиаторный_20.JPG
[REGISTER] PH_00000424  Радиаторный_21.JPG
[REGISTER] PH_00000425  Радиаторный_22.JPG
[REGISTER] PH_00000426  Радиаторный_23.JPG
[REGISTER] PH_00000427  Радиаторный_24.JPG
[REGISTER] PH_00000428  Радиаторный_25.JPG
[REGISTER] PH_00000429  Рубиновый_01.JPG
[REGISTER] PH_00000430  Рубиновый_02.JPG
[REGISTER] PH_00000431  Рубиновый_03.JPG
[REGISTER] PH_00000432  Рубиновый_04.JPG
[REGISTER] PH_00000433  Рубиновый_05.JPG
[REGISTER] PH_00000434  Рубиновый_06.JPG
[REGISTER] PH_00000435  Рубиновый_07.JPG
[REGISTER] PH_00000436  Рубиновый_08.JPG
[REGISTER] PH_00000437  Рубиновый_09.JPG
[REGISTER] PH_00000438  Рубиновый_10.JPG
[REGISTER] PH_00000439  Рубиновый_11.JPG
[REGISTER] PH_00000440  Рубиновый_12.JPG
[REGISTER] PH_00000441  Стачки_41_01.JPG
[REGISTER] PH_00000442  Стачки_41_02.JPG
[REGISTER] PH_00000443  Стачки_41_03.JPG
[REGISTER] PH_00000444  Стачки_41_04.JPG
[REGISTER] PH_00000445  Стачки_41_05.JPG
[REGISTER] PH_00000446  Стачки_41_06.JPG
[REGISTER] PH_00000447  Стачки_41_07.JPG
[REGISTER] PH_00000448  Стачки_41_08.JPG
[REGISTER] PH_00000449  Стачки_41_09.JPG
[REGISTER] PH_00000450  Стачки_41_10.JPG
[REGISTER] PH_00000451  Стачки_41_11.JPG
[REGISTER] PH_00000452  Стачки_41_12.JPG
[REGISTER] PH_00000453  Фурмановская ул. 106 - Плиева ул. 43 А (1).JPG
[REGISTER] PH_00000454  Фурмановская ул. 106 - Плиева ул. 43 А (10).JPG
[REGISTER] PH_00000455  Фурмановская ул. 106 - Плиева ул. 43 А (11).JPG
[REGISTER] PH_00000456  Фурмановская ул. 106 - Плиева ул. 43 А (12).JPG
[REGISTER] PH_00000457  Фурмановская ул. 106 - Плиева ул. 43 А (13).JPG
[REGISTER] PH_00000458  Фурмановская ул. 106 - Плиева ул. 43 А (14).JPG
[REGISTER] PH_00000459  Фурмановская ул. 106 - Плиева ул. 43 А (15).JPG
[REGISTER] PH_00000460  Фурмановская ул. 106 - Плиева ул. 43 А (16).JPG
[REGISTER] PH_00000461  Фурмановская ул. 106 - Плиева ул. 43 А (17).JPG
[REGISTER] PH_00000462  Фурмановская ул. 106 - Плиева ул. 43 А (18).JPG
[REGISTER] PH_00000463  Фурмановская ул. 106 - Плиева ул. 43 А (19).JPG
[REGISTER] PH_00000464  Фурмановская ул. 106 - Плиева ул. 43 А (2).JPG
[REGISTER] PH_00000465  Фурмановская ул. 106 - Плиева ул. 43 А (20).JPG
[REGISTER] PH_00000466  Фурмановская ул. 106 - Плиева ул. 43 А (21).JPG
[REGISTER] PH_00000467  Фурмановская ул. 106 - Плиева ул. 43 А (22).JPG
[REGISTER] PH_00000468  Фурмановская ул. 106 - Плиева ул. 43 А (23).JPG
[REGISTER] PH_00000469  Фурмановская ул. 106 - Плиева ул. 43 А (24).JPG
[REGISTER] PH_00000470  Фурмановская ул. 106 - Плиева ул. 43 А (25).JPG
[REGISTER] PH_00000471  Фурмановская ул. 106 - Плиева ул. 43 А (26).JPG
[REGISTER] PH_00000472  Фурмановская ул. 106 - Плиева ул. 43 А (27).JPG
[REGISTER] PH_00000473  Фурмановская ул. 106 - Плиева ул. 43 А (28).JPG
[REGISTER] PH_00000474  Фурмановская ул. 106 - Плиева ул. 43 А (29).JPG
[REGISTER] PH_00000475  Фурмановская ул. 106 - Плиева ул. 43 А (3).JPG
[REGISTER] PH_00000476  Фурмановская ул. 106 - Плиева ул. 43 А (30).JPG
[REGISTER] PH_00000477  Фурмановская ул. 106 - Плиева ул. 43 А (31).JPG
[REGISTER] PH_00000478  Фурмановская ул. 106 - Плиева ул. 43 А (32).JPG
[REGISTER] PH_00000479  Фурмановская ул. 106 - Плиева ул. 43 А (33).JPG
[REGISTER] PH_00000480  Фурмановская ул. 106 - Плиева ул. 43 А (34).JPG
[REGISTER] PH_00000481  Фурмановская ул. 106 - Плиева ул. 43 А (35).JPG
[REGISTER] PH_00000482  Фурмановская ул. 106 - Плиева ул. 43 А (36).JPG
[REGISTER] PH_00000483  Фурмановская ул. 106 - Плиева ул. 43 А (37).JPG
[REGISTER] PH_00000484  Фурмановская ул. 106 - Плиева ул. 43 А (38).JPG
[REGISTER] PH_00000485  Фурмановская ул. 106 - Плиева ул. 43 А (4).JPG
[REGISTER] PH_00000486  Фурмановская ул. 106 - Плиева ул. 43 А (5).JPG
[REGISTER] PH_00000487  Фурмановская ул. 106 - Плиева ул. 43 А (6).JPG
[REGISTER] PH_00000488  Фурмановская ул. 106 - Плиева ул. 43 А (7).JPG
[REGISTER] PH_00000489  Фурмановская ул. 106 - Плиева ул. 43 А (8).JPG
[REGISTER] PH_00000490  Фурмановская ул. 106 - Плиева ул. 43 А (9).JPG
[REGISTER] PH_00000491  Шеболдаева8_01.JPG
[REGISTER] PH_00000492  Шеболдаева8_02.JPG
[REGISTER] PH_00000493  Шеболдаева8_03.JPG
[REGISTER] PH_00000494  Шеболдаева8_04.JPG
[REGISTER] PH_00000495  Шеболдаева8_05.JPG
[REGISTER] PH_00000496  Шеболдаева8_06.JPG
[REGISTER] PH_00000497  Шеболдаева8_07.JPG
[REGISTER] PH_00000498  Шеболдаева8_08.JPG
[REGISTER] PH_00000499  Шеболдаева8_10.JPG
[REGISTER] PH_00000500  Шеболдаева8_11.JPG
[REGISTER] PH_00000501  Шеболдаева8_12.JPG
[REGISTER] PH_00000502  Шеболдаева8_13.JPG
[REGISTER] PH_00000503  Шеболдаева8_14.JPG
[REGISTER] PH_00000504  Шеболдаева8_15.JPG
[REGISTER] PH_00000505  Шеболдаева8_16.JPG
[REGISTER] PH_00000506  Шеболдаева8_17.JPG
[REGISTER] PH_00000507  Шеболдаева8_18.JPG
[REGISTER] PH_00000508  Шолохова 127 А (1).JPG
[REGISTER] PH_00000509  Шолохова 127 А (10).JPG
[REGISTER] PH_00000510  Шолохова 127 А (11).JPG
[REGISTER] PH_00000511  Шолохова 127 А (12).JPG
[REGISTER] PH_00000512  Шолохова 127 А (13).JPG
[REGISTER] PH_00000513  Шолохова 127 А (14).JPG
[REGISTER] PH_00000514  Шолохова 127 А (15).JPG
[REGISTER] PH_00000515  Шолохова 127 А (16).JPG
[REGISTER] PH_00000516  Шолохова 127 А (17).JPG
[REGISTER] PH_00000517  Шолохова 127 А (18).JPG
[REGISTER] PH_00000518  Шолохова 127 А (19).JPG
[REGISTER] PH_00000519  Шолохова 127 А (2).JPG
[REGISTER] PH_00000520  Шолохова 127 А (3).JPG
[REGISTER] PH_00000521  Шолохова 127 А (4).JPG
[REGISTER] PH_00000522  Шолохова 127 А (5).JPG
[REGISTER] PH_00000523  Шолохова 127 А (6).JPG
[REGISTER] PH_00000524  Шолохова 127 А (7).JPG
[REGISTER] PH_00000525  Шолохова 127 А (8).JPG
[REGISTER] PH_00000526  Шолохова 127 А (9).JPG

================================================================================
INGEST FINISHED
================================================================================

Found      : 526
Registered : 526
Skipped    : 0

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT id, photo_id, status, dino_status, qwen_status, sort_status, preview_status, source_path FROM photos ORDER BY id DESC LIMIT 20;"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:24:06

Да. Сейчас **ингест уже работает правильно**: из `/data/input/daily` зарегистрировано 526 файлов, каждому выдан `photo_id`, и только после этого они должны идти дальше в DINO/Qwen.

Следующий шаг я бы делал именно так:

```text
data/input/daily
        │
        ▼
┌──────────────────┐
│      INGEST       │
│ новый файл        │
│ → PH_00000527     │
│ → запись в photos │
└────────┬─────────┘
         │
         ▼
       QUEUE
         │
         ├──────────────► DINO
         │                 │
         │                 ▼
         │             dino_status
         │             dino_result
         │
         └──────────────► QWEN
                           │
                           ▼
                       qwen_status
                       qwen_result
         │
         ▼
       SORTER
         │
         ▼
 address / filename
 source_path → final_path
 sort_status
         │
         ▼
      PREVIEW
```

И главное: **`photo_id` становится постоянным идентификатором фотографии**. Имя файла и адресная папка — это уже изменяемые свойства.

То есть если:

```text
PH_00000527
```

DINO определил как `78_v33`, а потом оператор решил, что это `83_v33`, мы **не создаём новую фотографию** и не меняем `photo_id`.

Меняем:

```text
address
filename
path / final_path
```

а история DINO/Qwen остаётся привязанной к:

```text
PH_00000527
```

### Сейчас надо проверить одну вещь

Ты показал:

```text
INGEST FINISHED

Found      : 526
Registered : 526
Skipped    : 0
```

Но следующий `SELECT` почему-то ничего не показал. Похоже, команда либо ещё не была выполнена, либо вывод потерялся.

Давай сейчас **не менять код**, а сначала посмотрим фактическое состояние базы.

Выполни:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c "
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE dino_status = 'pending') AS dino_pending,
    COUNT(*) FILTER (WHERE qwen_status = 'pending') AS qwen_pending,
    COUNT(*) FILTER (WHERE sort_status = 'pending') AS sort_pending,
    COUNT(*) FILTER (WHERE preview_status = 'pending') AS preview_pending
FROM photos;
"
```

И затем:

```bash
psql -h localhost -p 5432 -U lora -d photobase -c "
SELECT
    id,
    photo_id,
    status,
    dino_status,
    qwen_status,
    sort_status,
    preview_status,
    filename
FROM photos
ORDER BY id DESC
LIMIT 10;
"
```

**После этого уже пишем обработчик очереди.**

Причём я предлагаю сделать его не как очередной `run_daily_hybrid_v12.sh`, а как отдельный **интегратор/worker**, который постоянно работает в фоне:

```text
один worker
    │
    ├─ берёт pending DINO
    ├─ обрабатывает
    ├─ записывает результат
    ├─ берёт pending Qwen
    ├─ обрабатывает
    ├─ записывает результат
    └─ берёт следующую фотографию
```

Никаких 20 одновременно запущенных DINO/Qwen процессов.

А источник при этом может быть любой:

- кнопка **«Обработать сейчас»**
- cron/таймер
- постоянный watcher папки
- запуск вручную из консоли

Но **очередь одна и база одна**. Это как раз даст нам нормальную основу для дальнейшего UI.

---

### 👤 **User** — 2026-08-18 21:24:29

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ psql -h localhost -p 5432 -U lora -d photobase -c "
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE dino_status = 'pending') AS dino_pending,
    COUNT(*) FILTER (WHERE qwen_status = 'pending') AS qwen_pending,
    COUNT(*) FILTER (WHERE sort_status = 'pending') AS sort_pending,
    COUNT(*) FILTER (WHERE preview_status = 'pending') AS preview_pending
FROM photos;
"
 total | dino_pending | qwen_pending | sort_pending | preview_pending 
-------+--------------+--------------+--------------+-----------------
   526 |          526 |          526 |          526 |             526
(1 row)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 21:24:30

Отлично. **База сейчас в правильном исходном состоянии.**

526 фотографий зарегистрированы и стоят в очереди:

```text
526 total
526 DINO pending
526 QWEN pending
526 SORT pending
526 PREVIEW pending
```

Теперь важно не запускать старый `run_daily_hybrid_v12.sh` напрямую. Он работает по папке и сам копирует файлы, а нам теперь нужна **система обработки по `photo_id`**.

### Предлагаю следующую архитектуру

```text
                    data/input/daily
                           │
                           ▼
                    ┌─────────────┐
                    │   INGEST    │
                    │ выдаёт ID    │
                    └──────┬──────┘
                           │
                           ▼
                    PostgreSQL photos
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        dino_status=pending       qwen_status=pending
              │                         │
              ▼                         ▼
          DINO worker               QWEN worker
              │                         │
              └────────────┬────────────┘
                           ▼
                       SORT worker
                           │
                           ▼
                     PREVIEW worker
```

Но **DINO и Qwen я бы не запускал одновременно на одной RTX 3060**, если Qwen использует GPU. Очередь лучше сделать последовательной:

```text
PH_00000527
     ↓
   DINO
     ↓
   QWEN
     ↓
   SORT
     ↓
 PREVIEW
     ↓
PH_00000528
     ↓
   DINO
     ↓
   QWEN
     ↓
   ...
```

При этом новые файлы могут поступать постоянно:

```text
PH_00000527 ──► processing
PH_00000528 ──► pending
PH_00000529 ──► pending
PH_00000530 ──► pending
...
```

Никаких новых процессов на каждый файл.

### И ещё один важный момент

Я бы **не переносил и не переименовывал исходный файл во время DINO/Qwen**.

У записи есть:

```text
photo_id
source_path
filename
address
```

и отдельно должны появиться результаты:

```text
dino_result
dino_score
dino_status

qwen_result
qwen_confidence
qwen_status

sort_status
final_path

preview_status
preview_path
```

Тогда исправление оператором будет простым:

```text
PH_00000527
DINO → 78_v33
Qwen → ...
SORT → 78_v33
```

Оператор увидел ошибку:

```text
PH_00000527
→ адрес изменить на 83_v33
→ имя изменить
```

И мы просто выполняем корректировку записи и физического файла. **ID остаётся PH_00000527 навсегда.**

---

## Следующий шаг

Теперь предлагаю написать первый настоящий компонент:

**`scripts/photo_worker.py`**

Он пока должен делать только безопасную вещь:

1. найти в `photos` одну запись `dino_status='pending'`;
2. взять её `photo_id`;
3. взять `source_path`;
4. обработать **только эту фотографию** существующим DINO;
5. записать результат обратно в `photos`;
6. поставить `dino_status='ok'`;
7. перейти к следующей.

А затем мы подключим Qwen → сортировку → preview.

Так мы сначала проверим **очередь на всех 526 фотографиях**, не рискуя сразу переписать весь pipeline.

---

### 👤 **User** — 2026-08-18 21:25:19

проверить дино на цпу и квен гпу

---

### 🤖 **Assistant** — 2026-08-18 21:25:20

Да. И это как раз лучше проверить **до написания worker**.

Нам нужно проверить два независимых режима:

- **DINO → CPU**
- **Qwen3-VL-4B-Instruct → GPU**

Причём проверяем не весь поток из 526 фото, а **по одной фотографии**, чтобы убедиться, что оба движка действительно используют нужное железо и нормально работают.

### 1. Сначала проверим DINO на CPU

Нужно посмотреть, как сейчас `SceneEmbedder` выбирает device. Выполни:

```bash id="4z5m4s"
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE "device|cuda|cpu|torch.device" \
app/core app \
--include="*.py" 2>/dev/null | head -100
```

### 2. Qwen проверим отдельно

Если Qwen у нас через Ollama, проверим GPU:

```bash id="3z9k0x"
nvidia-smi
```

и:

```bash id="v7j4q1"
ollama ps
```

Нас интересует, чтобы Qwen был загружен примерно так:

```text
qwen3-vl:4b-instruct    ...    GPU
```

а не CPU.

### В итоге хотим получить такую конфигурацию

```text id="9s4y7k"
                    RTX 3060 12 GB
                         │
                         └──── Qwen3-VL-4B
                               GPU

CPU Ryzen 5 5600
       │
       └──── DINOv2
             CPU
```

Это разумное разделение: **DINO не будет отъедать VRAM у Qwen**, а Qwen получит всю видеокарту.

И после этого уже делаем worker с такой последовательностью:

```text id="5u1r8d"
photo_id
   │
   ├── DINO CPU
   │
   ├── Qwen GPU
   │
   ├── сортировка
   │
   └── preview
```

Причём **один worker**, одна очередь и один следующий `photo_id` после завершения предыдущего.

---

