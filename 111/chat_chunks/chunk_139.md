## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 🤖 **Assistant** — 2026-08-18 23:32:33

Отлично. Уже видно важное: **`photos` у нас действительно подходит как центральная таблица**, и `photo_id` уже существует. Новую таблицу фотографий создавать не нужно.

Но вывод у тебя обрезался на `client`. Нужен остаток структуры, потому что там, скорее всего, уже есть часть полей Qwen и, возможно, статусы.

Выполни только:

```bash
psql -h localhost -U lora -d photobase -c '\d+ photos' | tail -n +1
```

или удобнее — получить только имена и типы всех полей:

```bash
psql -h localhost -U lora -d photobase -c "
SELECT
    ordinal_position,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'photos'
ORDER BY ordinal_position;
"
```

### Уже сейчас фиксируем

У нас есть:

```text
photos
├── id                 ← технический PK
├── photo_id           ← постоянный ID фотографии
├── source_path        ← исходный файл
├── path               ← текущий/рабочий путь
├── filename
├── original_filename
├── address            ← сейчас есть
└── client
```

Но я бы **не использовал существующее `address` как новый `address_id` автоматически**.

Новая логика должна быть:

```text
photo_id
   │
   ├── source_id
   │
   ├── source_path
   │
   ├── dino_status
   │
   └── address_id       ← результат DINO
```

А старое `address` пока оставляем как есть, чтобы ничего не сломать.

После полного вывода я определю:

1. какие поля уже есть и **не надо добавлять**;
2. какие поля Qwen уже использует;
3. какие поля добавляем для DINO;
4. какие добавляем для очередей;
5. какие индексы нужны;
6. что делать с существующими записями, чтобы **текущие фотографии не потерялись и повторно не обрабатывались без необходимости**.

Покажи этот второй вывод — дальше уже дам конкретный SQL миграции.

---

### 👤 **User** — 2026-08-18 23:32:56

alexice@NEURO:~/Desktop$ psql -h localhost -U lora -d photobase -c '\d+ photos' | tail -n +1
                                                                         Table "public.photos"
        Column         |            Type             | Collation | Nullable |              Default               | Storage  | Compression | Stats target | Description 
-----------------------+-----------------------------+-----------+----------+------------------------------------+----------+-------------+--------------+-------------
 id                    | bigint                      |           | not null | nextval('photos_id_seq'::regclass) | plain    |             |              | 
 photo_id              | text                        |           | not null |                                    | extended |             |              | 
 source_path           | text                        |           | not null |                                    | extended |             |              | 
 path                  | text                        |           | not null |                                    | extended |             |              | 
 filename              | text                        |           | not null |                                    | extended |             |              | 
 original_filename     | text                        |           |          |                                    | extended |             |              | 
 address               | text                        |           |          |                                    | extended |             |              | 
 client                | text                        |           |          |                                    | extended |             |              | 
 brand                 | text                        |           |          |                                    | extended |             |              | 
 category              | text                        |           |          |                                    | extended |             |              | 
 description           | text                        |           |          |                                    | extended |             |              | 
 status                | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 dino_status           | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 qwen_status           | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 sort_status           | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 preview_status        | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 error_message         | text                        |           |          |                                    | extended |             |              | 
 dino_fingerprint      | text                        |           |          |                                    | extended |             |              | 
 dino_score            | double precision            |           |          |                                    | plain    |             |              | 
 dino_second_score     | double precision            |           |          |                                    | plain    |             |              | 
 dino_margin           | double precision            |           |          |                                    | plain    |             |              | 
 dino_time_sec         | double precision            |           |          |                                    | plain    |             |              | 
 hybrid_original_id    | text                        |           |          |                                    | extended |             |              | 
 hybrid_final_id       | text                        |           |          |                                    | extended |             |              | 
 hybrid_changed        | boolean                     |           |          | false                              | plain    |             |              | 
 hybrid_old_score      | double precision            |           |          |                                    | plain    |             |              | 
 hybrid_score          | double precision            |           |          |                                    | plain    |             |              | 
 hybrid_margin         | double precision            |           |          |                                    | plain    |             |              | 
 hybrid_neighbors      | jsonb                       |           |          |                                    | extended |             |              | 
 confidence            | integer                     |           |          |                                    | plain    |             |              | 
 qwen_time_sec         | double precision            |           |          |                                    | plain    |             |              | 
 text_json             | jsonb                       |           |          |                                    | extended |             |              | 
 colors_json           | jsonb                       |           |          |                                    | extended |             |              | 
 objects_json          | jsonb                       |           |          |                                    | extended |             |              | 
 environment_json      | jsonb                       |           |          |                                    | extended |             |              | 
 image_quality_json    | jsonb                       |           |          |                                    | extended |             |              | 
 camera_view_json      | jsonb                       |           |          |                                    | extended |             |              | 
 scene_objects_json    | jsonb                       |           |          |                                    | extended |             |              | 
 analysis_quality_json | jsonb                       |           |          |                                    | extended |             |              | 
 raw_json              | jsonb                       |           |          |                                    | extended |             |              | 
 preview_path          | text                        |           |          |                                    | extended |             |              | 
 created_at            | timestamp without time zone |           | not null | CURRENT_TIMESTAMP                  | plain    |             |              | 
 updated_at            | timestamp without time zone |           | not null | CURRENT_TIMESTAMP                  | plain    |             |              | 
Indexes:
    "photos_pkey" PRIMARY KEY, btree (photo_id)
    "idx_photos_address" btree (address)
    "idx_photos_client" btree (client)
    "idx_photos_dino_fingerprint" btree (dino_fingerprint)
    "idx_photos_dino_queue" btree (dino_status, id)
    "idx_photos_hybrid_final" btree (hybrid_final_id)
    "idx_photos_preview_queue" btree (preview_status, id)
    "idx_photos_qwen_queue" btree (qwen_status, id)
    "idx_photos_sort_queue" btree (sort_status, id)
    "idx_photos_status" btree (status)
    "photos_id_key" UNIQUE CONSTRAINT, btree (id)
    "ux_photos_source_path" UNIQUE, btree (source_path)
Access method: heap

alexice@NEURO:~/Desktop$

---

### 🤖 **Assistant** — 2026-08-18 23:32:57

Отлично. Теперь картина полная. И здесь есть хорошая новость: **у нас уже примерно 70–80% нужной архитектуры есть в `photos`**. Не надо создавать новую таблицу фотографий и не надо ломать Qwen.

Более того, текущая схема уже содержит очереди:

```text
dino_status
qwen_status
sort_status
preview_status
```

и индексы под них.

### Но я бы сейчас внес одно принципиальное изменение

Не будем добавлять `address_id` как единственный новый результат DINO поверх старого `address`. У тебя уже есть:

```text
dino_fingerprint
hybrid_original_id
hybrid_final_id
address
```

И теперь надо чётко разделить их смысл.

## Финальная модель `photos`

```text
photo_id
│
├── source_id              ← новый: псевдоним источника/запуска
│
├── source_path            ← физический исходник
├── path                   ← текущий путь
│
├── DINO
│   ├── dino_status
│   ├── dino_fingerprint
│   ├── dino_score
│   ├── dino_second_score
│   ├── dino_margin
│   ├── dino_time_sec
│   ├── hybrid_original_id
│   ├── hybrid_final_id
│   └── address_id         ← НОВОЕ: окончательный ID адреса
│
└── QWEN
    ├── qwen_status
    ├── client
    ├── brand
    ├── category
    ├── description
    ├── confidence
    ├── *_json
    └── qwen_time_sec
```

### `address` пока не трогаем

Старое:

```text
address
```

оставляем для совместимости с нынешним гридом/кодом.

Но новая логика постепенно будет использовать:

```text
address_id
```

То есть:

```text
address_id = 78_v33
```

или соответствующее финальное значение Hybrid.

А уже UI может получить отображаемое название адреса отдельно.

---

# Что добавляем сейчас

Только `source_id` и `address_id`.

```bash
psql -h localhost -U lora -d photobase
```

Затем:

```sql
ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS source_id TEXT,
    ADD COLUMN IF NOT EXISTS address_id TEXT;
```

И индексы:

```sql
CREATE INDEX IF NOT EXISTS idx_photos_source_id
    ON photos(source_id);

CREATE INDEX IF NOT EXISTS idx_photos_address_id
    ON photos(address_id);
```

**Пока больше ничего не меняем.**

---

# Почему пока не добавляем `processing_jobs`

Потому что текущая `photos` уже является очередью.

Например:

```text
photo_id    dino_status    qwen_status
---------------------------------------
A001        pending        pending
A002        done           processing
A003        processing     done
A004        done           done
```

Для нашей задачи этого достаточно на первом этапе.

А `processing_jobs` понадобится, если нам действительно потребуется:

- несколько независимых экземпляров DINO;
- несколько Qwen workers;
- приоритеты;
- история нескольких повторных запусков одной фотографии.

Но это **второй слой**, и сейчас его преждевременно вводить.

---

# А вот `processing_runs` я бы добавил

Потому что это уже не состояние фотографии, а состояние **запуска системы**.

```sql
CREATE TABLE IF NOT EXISTS processing_runs (
    id BIGSERIAL PRIMARY KEY,

    run_id TEXT NOT NULL UNIQUE,

    mode TEXT NOT NULL DEFAULT 'manual',
    -- manual
    -- watcher
    -- automatic

    status TEXT NOT NULL DEFAULT 'idle',
    -- idle
    -- running
    -- stopping
    -- paused
    -- completed
    -- stopped
    -- error

    processing_policy TEXT NOT NULL DEFAULT 'skip',
    -- skip
    -- reprocess

    dino_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    qwen_enabled BOOLEAN NOT NULL DEFAULT TRUE,

    started_at TIMESTAMP,
    stopped_at TIMESTAMP,
    finished_at TIMESTAMP,

    error TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

И журнал:

```sql
CREATE TABLE IF NOT EXISTS processing_events (
    id BIGSERIAL PRIMARY KEY,

    run_id TEXT,

    photo_id TEXT,

    process TEXT,

    event TEXT NOT NULL,

    message TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

# Режимы запуска

В `processing_runs`:

```text
manual
watcher
automatic
```

А **текущий выбранный режим** я бы пока не хранил в отдельной таблице.

Сделаем маленький файл конфигурации приложения или отдельную таблицу настроек позже. Это UI-настройка, а не история обработки.

---

# Очень важное решение по `status`

У тебя сейчас есть:

```text
status
dino_status
qwen_status
sort_status
preview_status
```

Не надо превращать `status` в ещё один сложный процесс.

Предлагаю:

### `dino_status`

```text
pending
processing
done
error
paused
```

### `qwen_status`

```text
pending
processing
done
error
paused
```

### `sort_status`

Пока оставляем существующий.

Но в новой архитектуре физическая сортировка **не является обязательным этапом отображения**.

### `preview_status`

Тоже оставляем.

---

# Главный критерий грида

Теперь он должен быть:

```sql
WHERE address_id IS NOT NULL
```

а не:

```text
папка output/78_v33
```

И это очень важный переход.

Фото может физически находиться:

```text
data/input/daily/IMG_001.jpg
```

но после DINO:

```text
photo_id = P_20260818_000001
address_id = 78_v33
```

и оно уже отображается в гриде.

Qwen в этот момент может быть:

```text
qwen_status = processing
```

или уже:

```text
qwen_status = done
```

Грид подтянет описание по тому же `photo_id`.

---

# Итого

Текущая БД уже хорошо подготовлена:

```text
                    PHOTOS
                      │
             ┌────────┴────────┐
             │                 │
           DINO               QWEN
             │                 │
       address_id         description
             │                 │
             └────────┬────────┘
                      │
                   photo_id
                      │
                     GRID
```

И отдельно:

```text
processing_runs
        │
        ├── manual
        ├── watcher
        └── automatic
```

`processing_events` — история.

---

### Сейчас я бы сделал только миграцию

```sql
ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS source_id TEXT,
    ADD COLUMN IF NOT EXISTS address_id TEXT;

CREATE INDEX IF NOT EXISTS idx_photos_source_id
    ON photos(source_id);

CREATE INDEX IF NOT EXISTS idx_photos_address_id
    ON photos(address_id);
```

**Не запускаем пока никаких скриптов обработки.**

После этого следующим шагом посмотрим **как сейчас `photos` заполняется** — откуда создаётся `photo_id`, `source_path`, `path`, и где именно происходит запись в PostgreSQL. Это критично: именно там мы должны поставить точку, после которой фотография одновременно становится доступной DINO и Qwen.

---

### 👤 **User** — 2026-08-18 23:34:49

PHOTOS
                      │
             ┌────────┴────────┐
             │                 │
           DINO               QWEN
             │                 │
       address_id         description
             │                 │
             └────────┬────────┘
                      │
                   photo_id
                      │
                     GRID 

 photo_id присваивается еще ж до разделения на квен и дино

---

### 🤖 **Assistant** — 2026-08-18 23:34:50

Да. Именно так и фиксируем архитектуру. **`photo_id` создаётся один раз до запуска DINO и Qwen**, после чего оба процесса работают независимо, но записывают результат в одну запись фотографии.

### Финальная схема

```text
                         НОВЫЙ ФАЙЛ
                             │
                             ▼
                    ┌─────────────────┐
                    │   PHOTO INDEX   │
                    │                 │
                    │ photo_id        │ ← создаётся здесь
                    │ source_path     │
                    │ filename        │
                    │ initial_id      │ ← псевдоним / ID запуска
                    └────────┬────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
              DINO                     QWEN
                 │                       │
                 │                       │
                 ▼                       ▼
          address_id              description
          / address               brand
          hybrid...               client
                 │                category
                 │                quality...
                 │                       │
                 └───────────┬───────────┘
                             │
                             ▼
                         photo_id
                             │
                             ▼
                            GRID
```

### Ключевое правило

**`photo_id` — главный постоянный идентификатор фотографии.**

Он появляется **до DINO и Qwen**.

Например:

```text
photo_id = PH_20260818_000001
initial_id = RUN_20260818_190501_0001
source_path = /data/input/daily/Иванова_15.jpg
```

После этого:

**DINO:**

```text
photo_id
   ↓
dino...
   ↓
address_id = 83
```

**Qwen:**

```text
photo_id
   ↓
description
brand
client
text
colors
quality
...
```

Они **не должны зависеть друг от друга**.

---

### Поэтому я бы разделил идентификаторы так

| Поле | Назначение |
|---|---|
| `photo_id` | **Постоянный ID фотографии**, ключ связи всего пайплайна |
| `initial_id` | ID/псевдоним исходной фотографии для внутренних процессов и запуска |
| `address_id` | Результат DINO/Hybrid — определённый адрес |
| `dino_fingerprint` | Технический результат распознавания |
| `hybrid_final_id` | Финальный ID Hybrid, из которого получается адрес |

И главное:

```text
photo_id ≠ initial_id ≠ address_id
```

Они имеют разные задачи.

---

### GRID

Грид получает фотографии **только когда появился `address_id`**:

```sql
WHERE address_id IS NOT NULL
```

или эквивалентное состояние:

```text
DINO = DONE
address_id = 83
```

При этом Qwen может быть:

```text
QWEN = PENDING
```

и фотография **уже появляется в GRID**.

Потом Qwen заканчивает:

```text
photo_id = PH_20260818_000001

DINO:
address_id = 83

QWEN:
description = "..."
brand = "..."
client = "..."
```

Грид просто подтягивает Qwen-данные **по тому же `photo_id`**.

---

### Что это даёт

Например, DINO обработал 700 фотографий, а Qwen только 430:

```text
GRID
────────────────────────────
700 фотографий с адресами
────────────────────────────
430 — Qwen готов
270 — Qwen ещё выполняется
```

Никакой физической сортировки файлов для связи не требуется.

Именно поэтому предыдущую идею:

```text
DINO → физическая сортировка → Qwen
```

**отбрасываем.**

Будет:

```text
                  PHOTO INDEX
                       │
                создаём photo_id
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
            DINO                QWEN
             │                   │
        address_id          описание
             │                   │
             └─────────┬─────────┘
                       ▼
                    PHOTOS
                       │
                    photo_id
                       │
                       ▼
                      GRID
```

И это хорошо ложится на твою текущую PostgreSQL `photos`: **не нужно делать отдельную таблицу для связи DINO ↔ Qwen — связь уже естественно осуществляется через `photo_id`**, а вот `initial_id` я бы добавил как отдельное поле.

---

### 👤 **User** — 2026-08-18 23:35:13

далее

---

### 🤖 **Assistant** — 2026-08-18 23:35:14

Дальше логично зафиксировать **жизненный цикл одной фотографии** и уже от него строить очередь, кнопки и режимы запуска.

## 1. Жизненный цикл `photo_id`

```text
ФАЙЛ ОБНАРУЖЕН
      │
      ▼
┌──────────────────────┐
│ PHOTO INDEX          │
│                      │
│ photo_id             │ ← создаём
│ initial_id           │ ← создаём
│ source_path          │
│ filename             │
└──────────┬───────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
   DINO         QWEN
     │           │
     ▼           ▼
 address_id    описание
     │           │
     └─────┬─────┘
           ▼
          GRID
```

При этом **DINO и Qwen не блокируют друг друга**.

---

# 2. Состояния `photos`

Я бы теперь окончательно разделил состояния:

### Общий статус

```text
status
```

```text
pending
processing
ready
error
paused
```

Но он **не должен определять готовность GRID**. Это общий технический статус.

### DINO

```text
dino_status
```

```text
pending
processing
done
error
paused
```

### Qwen

```text
qwen_status
```

```text
pending
processing
done
error
paused
```

### Сортировка

С учётом новой архитектуры физическая сортировка больше не является обязательной частью основного процесса.

Поэтому:

```text
sort_status
```

может остаться отдельным техническим процессом, но **GRID от него не зависит**.

### Preview

```text
preview_status
```

также самостоятельный процесс.

---

# 3. Что является условием появления в GRID

Главное правило:

```text
DINO done
+
address_id существует
        ↓
     GRID = YES
```

Qwen вообще не участвует в этом условии.

Например:

```text
photo_id       PH_000123
dino_status    done
address        83
qwen_status    pending
```

→ **фотография уже в GRID.**

А справа/в карточке:

```text
Qwen: анализируется...
```

После завершения:

```text
qwen_status = done
```

GRID автоматически получает описание.

---

# 4. Что происходит при новом файле

Watcher обнаруживает:

```text
/data/input/daily/Петрова15_01.jpg
```

Создаётся запись:

```text
photo_id   = PH_20260818_000421
initial_id = RUN_20260818_190501_0421
```

И сразу:

```text
dino_status = pending
qwen_status = pending
```

То есть **Qwen уже видит эту фотографию как задачу**, но может начать только после того, как фотография зарегистрирована и получила `photo_id`.

---

# 5. DINO получает задачу

DINO берёт:

```text
photo_id = PH_20260818_000421
source_path = ...
```

Обрабатывает.

Получает:

```text
dino_fingerprint = 83_v33
dino_score = ...
dino_margin = ...
```

Hybrid принимает решение:

```text
hybrid_final_id = 83
```

И записывает:

```text
address = 83
dino_status = done
```

После этого **не надо копировать фотографию в папку `83` ради Qwen или GRID**.

---

# 6. Qwen работает параллельно

Qwen берёт ту же запись:

```text
photo_id = PH_20260818_000421
source_path = ...
```

Ему совершенно всё равно:

```text
address = 83
```

или:

```text
address = 91
```

или адрес ещё не определён.

Он делает только свою работу:

```text
client
brand
category
description
text_json
colors_json
objects_json
environment_json
image_quality_json
camera_view_json
analysis_quality_json
raw_json
```

И:

```text
qwen_status = done
```

---

# 7. Поэтому физическая папка больше не является базой данных

Это очень важный момент.

Старое:

```text
INPUT
  ↓
DINO
  ↓
OUTPUT/83/
OUTPUT/84/
OUTPUT/85/
  ↓
QWEN
```

убираем как архитектурную зависимость.

Новое:

```text
INPUT
  ↓
PHOTO INDEX
  ↓
PostgreSQL photos
  │
  ├── DINO
  │
  └── QWEN
```

А физическое:

```text
output/83/
output/84/
```

может создаваться **как производное представление**, если оно понадобится для экспорта/архива.

---

# 8. Главное изменение для текущего `qwen4b_output_v01.py`

Сейчас Qwen уже практически работает правильно:

```python
SELECT
    id,
    photo_id,
    source_path,
    filename
FROM photos
WHERE qwen_status = 'pending'
```

Это как раз нужная модель.

Единственное, что надо будет изменить — обеспечить, чтобы Qwen **не брал фотографию до её регистрации в PHOTO INDEX**, а дальше ему ничего знать про DINO не требуется.

---

# 9. А `run_hybrid_v12.py` надо перестроить

Сейчас он концептуально делает:

```text
input
 ↓
recognition
 ↓
hybrid
 ↓
sort_results()
 ↓
физические папки
```

Вот это:

```python
sort_results(rows, output_dir)
```

больше **не должно быть обязательной частью DINO-пайплайна**.

Вместо этого:

```text
DINO
 ↓
UPDATE photos
 SET
   dino_status = 'done',
   dino_fingerprint = ...,
   ...
   address = ...
```

И всё.

GRID сразу видит запись.

---

# 10. А теперь поверх этого строим управление

Получается три независимых управляющих уровня.

### Главная кнопка

```text
▶ ЗАПУСТИТЬ
■ ОСТАНОВИТЬ
```

управляет **всеми процессами**:

```text
DINO + QWEN
```

### DINO

```text
DINO
[▶ Запустить] [■ Остановить]

██████████░░░░░░  63%
63 / 100
```

### QWEN

```text
QWEN 3-VL 4B
[▶ Запустить] [■ Остановить]

██████░░░░░░░░░░  41%
41 / 100
```

---

# 11. Индикатор общего состояния

Предлагаю окончательно такие состояния:

🟢 **зелёный**

```text
ГОТОВ / ОЖИДАНИЕ
```

🟠 **оранжевый мигающий**

```text
РАБОТАЕТ
```

🟡 **жёлтый**

```text
ПАУЗА
```

🔴 **красный**

```text
ОШИБКА
```

Причём общий индикатор считается по состоянию DINO + Qwen.

Например:

```text
DINO  🟠 работает
QWEN  🟢 ждёт

ОБЩИЙ 🟠 работает
```

А:

```text
DINO  🟢 готов
QWEN  🟢 готов

ОБЩИЙ 🟢 готов
```

---

## 12. И самое важное — возобновление

Если компьютер выключился:

```text
1000 фотографий
```

было:

```text
DINO done = 643
DINO processing = 1
DINO pending = 356

QWEN done = 511
QWEN processing = 1
QWEN pending = 488
```

После запуска система **не начинает сначала**.

Она продолжает:

```text
DINO → pending
QWEN → pending
```

А `processing` старых задач при восстановлении переводятся обратно в:

```text
pending
```

если они были прерваны.

---

И тогда следующий шаг уже конкретный: **переделать `photos` под эту модель — добавить `initial_id`, определить точные состояния и написать SQL-правила для `PHOTO INDEX → DINO/QWEN → GRID`, не ломая существующие поля.**

---

### 👤 **User** — 2026-08-18 23:35:52

делаеми

---

### 🤖 **Assistant** — 2026-08-18 23:35:53

Да. Делаем **по этой архитектуре**, не трогая пока рабочую часть Qwen и сам алгоритм Hybrid v12.

Первый этап — привести БД к правильной модели: `photo_id` создаётся при индексации, `initial_id` хранит псевдоним запуска, DINO и Qwen независимы, а GRID зависит только от наличия адреса.

### 1. Добавляем `initial_id`

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -h localhost -U lora -d photobase <<'SQL'

ALTER TABLE photos
ADD COLUMN IF NOT EXISTS initial_id TEXT;

CREATE INDEX IF NOT EXISTS idx_photos_initial_id
ON photos(initial_id);

SQL
```

Проверяем:

```bash
psql -h localhost -U lora -d photobase -c '\d+ photos' | grep -E 'photo_id|initial_id|address|dino_status|qwen_status|sort_status|preview_status'
```

---

## 2. Фиксируем значения состояний

Не будем пока делать PostgreSQL `ENUM` — для разработки это будет только мешать миграциям.

Используем обычный `TEXT`.

### DINO

```text
pending
processing
done
error
paused
```

### Qwen

```text
pending
processing
done
error
paused
```

### Общий `status`

```text
pending
processing
ready
error
paused
```

### Sort

```text
pending
processing
done
error
paused
skipped
```

### Preview

```text
pending
processing
done
error
paused
skipped
```

---

# 3. Очень важное правило

`status` **не является источником истины для GRID**.

GRID определяет готовность так:

```text
dino_status = 'done'
AND
address IS NOT NULL
AND
address <> ''
```

То есть:

```text
DINO ──────► address ──────► GRID
                    ▲
                    │
                  photo_id
                    │
QWEN ──────► описание
```

Qwen вообще не должен влиять на появление фотографии в GRID.

---

# 4. Добавим явное `address_id`

Сейчас у тебя уже есть:

```text
address text
```

Но по нашей архитектуре лучше разделить:

```text
address_id
address
```

Потому что:

```text
address_id = "83"
address    = "какой-то реальный адрес"
```

При этом `hybrid_final_id` остаётся техническим результатом Hybrid.

Добавляем:

```bash
psql -h localhost -U lora -d photobase <<'SQL'

ALTER TABLE photos
ADD COLUMN IF NOT EXISTS address_id TEXT;

CREATE INDEX IF NOT EXISTS idx_photos_address_id
ON photos(address_id);

SQL
```

---

# 5. Как теперь выглядит одна запись

Например:

```text
photo_id:
PH_20260818_000421

initial_id:
RUN_20260818_190501_0421

source_path:
/data/input/daily/Петрова15_01.jpg

filename:
Петрова15_01.jpg

dino_status:
done

dino_fingerprint:
83_v33

dino_score:
0.91

hybrid_final_id:
83

address_id:
83

qwen_status:
processing
```

Это означает:

> фотография распознана как адрес 83, уже должна быть в GRID, а Qwen ещё работает.

---

# 6. Теперь `photo_id` создаётся на входе

Нам нужен отдельный индексатор.

Создадим:

```text
app/pipeline/photo_index.py
```

Он будет делать только это:

```text
файл
 ↓
проверка
 ↓
создание photo_id
 ↓
создание initial_id
 ↓
INSERT photos
 ↓
DINO pending
QWEN pending
```

**Никакого DINO внутри.**

**Никакого Qwen внутри.**

**Никакой сортировки.**

---

## 7. Сам принцип генерации ID

`photo_id` должен быть стабильным.

Например:

```text
PH_20260818_000001
PH_20260818_000002
PH_20260818_000003
```

А `initial_id` может отражать запуск:

```text
RUN_20260818_190501_000001
RUN_20260818_190501_000002
```

То есть:

```text
photo_id
```

— идентификатор **самой фотографии в базе**.

А:

```text
initial_id
```

— идентификатор её положения/поступления в конкретном запуске.

---

# 8. При повторном запуске

Вот здесь появляется нужная тебе логика:

```text
Обработать заново
Пропустить
Для всех
```

И она **не должна создавать новый `photo_id`**, если это та же самая фотография.

Например:

```text
source_path:
/data/input/daily/Petrova15_01.jpg
```

уже существует:

```text
photo_id = PH_20260818_000421
```

Повторный запуск:

```text
ПРОПУСТИТЬ
```

→ ничего не меняем.

```text
ОБРАБОТАТЬ ЗАНОВО
```

→ тот же:

```text
photo_id = PH_20260818_000421
```

но:

```text
dino_status = pending
qwen_status = pending
```

и старые результаты заменяются новыми.

Это очень важно для GRID: **карточка фотографии не меняет своего ID.**

---

# 9. Индексы для очередей

У тебя они уже практически правильные:

```text
idx_photos_dino_queue
idx_photos_qwen_queue
idx_photos_sort_queue
idx_photos_preview_queue
```

Оставляем.

Добавим индекс для GRID:

```bash
psql -h localhost -U lora -d photobase <<'SQL'

CREATE INDEX IF NOT EXISTS idx_photos_grid
ON photos(address_id, id);

SQL
```

---

# 10. Проверка структуры после миграции

Выполни:

```bash
psql -h localhost -U lora -d photobase -c '\d+ photos'
```

В результате среди основных полей должно быть:

```text
photo_id
initial_id

source_path
path
filename
original_filename

address_id
address

client
brand
category
description

status
dino_status
qwen_status
sort_status
preview_status

dino_fingerprint
dino_score
dino_second_score
dino_margin
dino_time_sec

hybrid_original_id
hybrid_final_id
hybrid_changed
hybrid_old_score
hybrid_score
hybrid_margin
hybrid_neighbors

...
```

---

# 11. Следующий шаг — DINO больше не сортирует

После этого мы меняем:

```text
run_hybrid_v12.py
```

Вот эту часть:

```python
sort_results(rows, output_dir)
```

из **обязательного DINO pipeline** убираем.

Вместо:

```text
DINO
 ↓
Hybrid
 ↓
copy2()
 ↓
папка адреса
```

будет:

```text
DINO
 ↓
Hybrid
 ↓
UPDATE photos
 ↓
address_id
 ↓
dino_status = done
```

И одновременно:

```text
Qwen
 ↓
UPDATE photos
 ↓
description / brand / ...
 ↓
qwen_status = done
```

---

# 12. И тогда наша окончательная архитектура

```text
                         WATCHER / MANUAL / AUTO
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   PHOTO INDEX   │
                         └────────┬────────┘
                                  │
                         photo_id создан
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
              ┌───────────┐               ┌───────────┐
              │   DINO    │               │   QWEN    │
              └─────┬─────┘               └─────┬─────┘
                    │                           │
                    ▼                           ▼
               address_id                 description
               dino_score                 brand
               hybrid...                  client
                    │                     quality
                    │                           │
                    └──────────┬────────────────┘
                               │
                         PostgreSQL
                            photos
                               │
                         ┌─────┴─────┐
                         │           │
                         ▼           ▼
                        GRID       EXPORT
```

И самое главное:

**физическая папка результата больше не является связующим звеном.**

Следующим шагом я бы уже сделал `photo_index.py` и функцию массовой регистрации файлов с режимами **«пропустить / обработать заново / для всех»**, а затем подключил к ней DINO и Qwen.

---

### 👤 **User** — 2026-08-18 23:36:31

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ psql -h localhost -U lora -d photobase -c '\d+ photos' | grep -E 'photo_id|initial_id|address|dino_status|qwen_status|sort_status|preview_status'
 photo_id              | text                        |           | not null |                                    | extended |             |              | 
 address               | text                        |           |          |                                    | extended |             |              | 
 dino_status           | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 qwen_status           | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 sort_status           | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 preview_status        | text                        |           | not null | 'pending'::text                    | extended |             |              | 
 address_id            | text                        |           |          |                                    | extended |             |              | 
 initial_id            | text                        |           |          |                                    | extended |             |              | 
    "photos_pkey" PRIMARY KEY, btree (photo_id)
    "idx_photos_address" btree (address)
    "idx_photos_address_id" btree (address_id)
    "idx_photos_dino_queue" btree (dino_status, id)
    "idx_photos_initial_id" btree (initial_id)
    "idx_photos_preview_queue" btree (preview_status, id)
    "idx_photos_qwen_queue" btree (qwen_status, id)
    "idx_photos_sort_queue" btree (sort_status, id)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ psql -h localhost -U lora -d photobase <<'SQL'

ALTER TABLE photos
ADD COLUMN IF NOT EXISTS address_id TEXT;

CREATE INDEX IF NOT EXISTS idx_photos_address_id
ON photos(address_id);

SQL
NOTICE:  column "address_id" of relation "photos" already exists, skipping
ALTER TABLE
NOTICE:  relation "idx_photos_address_id" already exists, skipping
CREATE INDEX
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:36:32

Да, всё правильно. **Миграция уже выполнена**: `initial_id` и `address_id` есть, индексы тоже есть. Повторный `ALTER` ничего не изменил — это нормально.

Теперь **БД пока не трогаем**. Переходим к следующему уровню: индексатор, который создаёт `photo_id` **до разделения на DINO/Qwen**.

### Следующий шаг

Сначала посмотрим, как сейчас создаются записи в `photos`, чтобы не написать второй параллельный механизм и не сломать существующий импорт.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "================ INSERT photos ================"
grep -RniE \
'INSERT INTO photos|insert into photos|photos\s*\(' \
app scripts \
--exclude-dir=.venv \
--exclude='*.pyc' \
| head -100

echo
echo "================ photo_id ================"
grep -RniE \
'photo_id|source_path|initial_id|address_id' \
app scripts \
--exclude-dir=.venv \
--exclude='*.pyc' \
| head -200
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find app scripts -type f \
  \( -name "*.py" -o -name "*.sh" \) \
  -not -path "*/.venv/*" \
  | sort
```

**Пока ничего не меняем.** По этому выводу найдём существующий импорт/индексатор и встроим новую логику именно туда. Это важно, потому что `photos` уже используется Qwen и GRID, и нам не нужен второй конкурирующий способ создавать записи.

---

### 👤 **User** — 2026-08-18 23:37:14

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "================ INSERT photos ================"
grep -RniE \
'INSERT INTO photos|insert into photos|photos\s*$' \
app scripts \
--exclude-dir=.venv \
--exclude='*.pyc' \
| head -100

echo
echo "================ photo_id ================"
grep -RniE \
'photo_id|source_path|initial_id|address_id' \
app scripts \
--exclude-dir=.venv \
--exclude='*.pyc' \
| head -200
================ INSERT photos ================
app/web/components/photos.py.bak_qwen_preview:206:def get_all_indexed_photos():
app/web/components/photos.py.bak_qwen_preview:221:def get_db_search_photos():
app/web/components/photos.py.bak_qwen_preview:260:def get_filtered_photos():
app/web/components/photos.py.bak_qwen_preview:267:        files = get_db_search_photos()
app/web/components/photos.py.bak_qwen_preview:273:            files = get_all_indexed_photos()
app/web/components/photos.py.bak_qwen_preview:647:def build_photos():
app/web/components/photos.py.bak_qwen_preview:663:        get_all_indexed_photos()
app/web/components/photos.py.bak_qwen_preview:745:        def select_all_photos():
app/web/components/photos.py.bak_qwen_preview:747:            files = get_filtered_photos()
app/web/components/photos.py.bak_qwen_preview:771:        def clear_selected_photos():
app/web/components/photos.py.bak_qwen_preview:1022:                all_files = get_filtered_photos()
app/web/components/photos.py.bak_qwen_preview:1255:            def load_more_photos():
app/web/components/photos.py.bak_qwen_preview:1262:                all_files = get_filtered_photos()
app/web/components/photos.py.bak_qwen_preview:1302:                    len(get_filtered_photos()),
app/web/components/photos.py.bak_qwen_preview:1333:                    load_more_photos()
app/web/components/photos.py.bak_qwen_preview:1344:    def refresh_photos():
app/web/components/photos.py.before_pg_link_20260816_183647:58:def get_all_indexed_photos():
app/web/components/photos.py.before_pg_link_20260816_183647:73:def get_db_search_photos():
app/web/components/photos.py.before_pg_link_20260816_183647:112:def get_filtered_photos():
app/web/components/photos.py.before_pg_link_20260816_183647:115:        return get_db_search_photos()
app/web/components/photos.py.before_pg_link_20260816_183647:120:        return get_all_indexed_photos()
app/web/components/photos.py.before_pg_link_20260816_183647:416:def build_photos():
app/web/components/photos.py.before_pg_link_20260816_183647:425:        get_all_indexed_photos()
app/web/components/photos.py.before_pg_link_20260816_183647:556:                files = get_filtered_photos()
app/web/components/photos.py.before_pg_link_20260816_183647:732:    def refresh_photos():
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:136:def get_all_indexed_photos():
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:151:def get_db_search_photos():
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:190:def get_filtered_photos():
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:197:        files = get_db_search_photos()
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:203:            files = get_all_indexed_photos()
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:577:def build_photos():
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:593:        get_all_indexed_photos()
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:675:        def select_all_photos():
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:677:            files = get_filtered_photos()
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:701:        def clear_selected_photos():
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:952:                all_files = get_filtered_photos()
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:1185:            def load_more_photos():
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:1192:                all_files = get_filtered_photos()
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:1232:                    len(get_filtered_photos()),
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:1263:                    load_more_photos()
app/web/components/photos.py.bak_before_daily_grid_fix_20260818_121648:1274:    def refresh_photos():
app/web/components/clients.py.bak:39:    refresh_photos()
app/web/components/clients.py.bak:50:    refresh_photos()
app/web/components/clients.py.bak:61:    refresh_photos()
app/web/components/photos.py.before_client_filter:59:def get_all_indexed_photos():
app/web/components/photos.py.before_client_filter:74:def get_db_search_photos():
app/web/components/photos.py.before_client_filter:113:def get_filtered_photos():
app/web/components/photos.py.before_client_filter:116:        return get_db_search_photos()
app/web/components/photos.py.before_client_filter:121:        return get_all_indexed_photos()
app/web/components/photos.py.before_client_filter:457:def build_photos():
app/web/components/photos.py.before_client_filter:466:        get_all_indexed_photos()
app/web/components/photos.py.before_client_filter:597:                files = get_filtered_photos()
app/web/components/photos.py.before_client_filter:773:    def refresh_photos():
app/web/components/photos_before_cache_20260816_145128.py:15:def all_photos():
app/web/components/photos_before_cache_20260816_145128.py:45:def get_filtered_photos():
app/web/components/photos_before_cache_20260816_145128.py:47:    files = all_photos()
app/web/components/photos_before_cache_20260816_145128.py:175:def build_photos():
app/web/components/photos_before_cache_20260816_145128.py:254:                files = get_filtered_photos()
app/web/components/photos_before_cache_20260816_145128.py:360:    def refresh_photos():
app/web/components/photos.py.bak_before_refresh_debug:58:def get_all_indexed_photos():
app/web/components/photos.py.bak_before_refresh_debug:73:def get_db_search_photos():
app/web/components/photos.py.bak_before_refresh_debug:112:def get_filtered_photos():
app/web/components/photos.py.bak_before_refresh_debug:115:        return get_db_search_photos()
app/web/components/photos.py.bak_before_refresh_debug:120:        return get_all_indexed_photos()
app/web/components/photos.py.bak_before_refresh_debug:276:def build_photos():
app/web/components/photos.py.bak_before_refresh_debug:285:        get_all_indexed_photos()
app/web/components/photos.py.bak_before_refresh_debug:416:                files = get_filtered_photos()
app/web/components/photos.py.bak_before_refresh_debug:539:    def refresh_photos():
app/web/components/photos.py.bak_before_db_search_fix:58:def get_all_indexed_photos():
app/web/components/photos.py.bak_before_db_search_fix:73:def get_db_search_photos():
app/web/components/photos.py.bak_before_db_search_fix:115:def get_filtered_photos():
app/web/components/photos.py.bak_before_db_search_fix:118:        return get_db_search_photos()
app/web/components/photos.py.bak_before_db_search_fix:123:        return get_all_indexed_photos()
app/web/components/photos.py.bak_before_db_search_fix:279:def build_photos():
app/web/components/photos.py.bak_before_db_search_fix:288:        get_all_indexed_photos()
app/web/components/photos.py.bak_before_db_search_fix:419:                files = get_filtered_photos()
app/web/components/photos.py.bak_before_db_search_fix:542:    def refresh_photos():
app/web/components/search.py:157:        STATE.refresh_photos()
app/web/components/photos.py.bak_before_db_search:56:def get_all_indexed_photos():
app/web/components/photos.py.bak_before_db_search:71:def get_filtered_photos():
app/web/components/photos.py.bak_before_db_search:77:        return get_all_indexed_photos()
app/web/components/photos.py.bak_before_db_search:233:def build_photos():
app/web/components/photos.py.bak_before_db_search:242:        get_all_indexed_photos()
app/web/components/photos.py.bak_before_db_search:373:                files = get_filtered_photos()
app/web/components/photos.py.bak_before_db_search:496:    def refresh_photos():
app/web/components/photos.py.before_info_panel_20260816_184210:59:def get_all_indexed_photos():
app/web/components/photos.py.before_info_panel_20260816_184210:74:def get_db_search_photos():
app/web/components/photos.py.before_info_panel_20260816_184210:113:def get_filtered_photos():
app/web/components/photos.py.before_info_panel_20260816_184210:116:        return get_db_search_photos()
app/web/components/photos.py.before_info_panel_20260816_184210:121:        return get_all_indexed_photos()
app/web/components/photos.py.before_info_panel_20260816_184210:417:def build_photos():
app/web/components/photos.py.before_info_panel_20260816_184210:426:        get_all_indexed_photos()
app/web/components/photos.py.before_info_panel_20260816_184210:557:                files = get_filtered_photos()
app/web/components/photos.py.before_info_panel_20260816_184210:733:    def refresh_photos():
app/web/components/photos.py.bak_viewer_empty:58:def get_all_indexed_photos():
app/web/components/photos.py.bak_viewer_empty:73:def get_db_search_photos():
app/web/components/photos.py.bak_viewer_empty:112:def get_filtered_photos():
app/web/components/photos.py.bak_viewer_empty:115:        return get_db_search_photos()
app/web/components/photos.py.bak_viewer_empty:120:        return get_all_indexed_photos()
app/web/components/photos.py.bak_viewer_empty:488:def build_photos():

================ photo_id ================
app/web/photo_db.py:23:            source_path,
app/workers/dino_worker.py:35:                photo_id,
app/workers/dino_worker.py:36:                source_path
app/workers/dino_worker.py:69:    photo_id,
app/workers/dino_worker.py:94:                photo_id,
app/workers/dino_worker.py:103:    photo_id,
app/workers/dino_worker.py:120:                photo_id,
app/workers/dino_worker.py:171:            photo_id = row["id"]
app/workers/dino_worker.py:172:            photo_key = row["photo_id"]
app/workers/dino_worker.py:173:            source_path = Path(row["source_path"])
app/workers/dino_worker.py:180:                f"{source_path.name}"
app/workers/dino_worker.py:186:                if not source_path.exists():
app/workers/dino_worker.py:188:                        f"Photo not found: {source_path}"
app/workers/dino_worker.py:192:                    source_path,
app/workers/dino_worker.py:201:                    photo_id,
app/workers/dino_worker.py:228:                        photo_id,
scripts/photo_ingest.py:28:    Возвращает следующий числовой номер PHOTO_ID.
scripts/photo_ingest.py:41:            SELECT photo_id
scripts/photo_ingest.py:43:            WHERE photo_id LIKE 'PH_%'
scripts/photo_ingest.py:50:    for (photo_id,) in rows:
scripts/photo_ingest.py:52:        if not photo_id:
scripts/photo_ingest.py:57:                str(photo_id)
scripts/photo_ingest.py:71:def make_photo_id(number):
scripts/photo_ingest.py:83:def get_existing_source_paths(conn):
scripts/photo_ingest.py:85:    Загружает уже зарегистрированные source_path.
scripts/photo_ingest.py:91:            SELECT source_path
scripts/photo_ingest.py:93:            WHERE source_path IS NOT NULL
scripts/photo_ingest.py:125:    photo_id,
scripts/photo_ingest.py:126:    source_path,
scripts/photo_ingest.py:134:    filename = Path(source_path).name
scripts/photo_ingest.py:140:                photo_id,
scripts/photo_ingest.py:142:                source_path,
scripts/photo_ingest.py:172:            photo_id,
scripts/photo_ingest.py:174:            source_path,
scripts/photo_ingest.py:175:            source_path,
scripts/photo_ingest.py:212:        existing_paths = get_existing_source_paths(conn)
scripts/photo_ingest.py:221:            source_path = normalize_path(image)
scripts/photo_ingest.py:227:            if source_path in existing_paths:
scripts/photo_ingest.py:239:            # Новый photo_id
scripts/photo_ingest.py:242:            photo_id = make_photo_id(
scripts/photo_ingest.py:248:                photo_id,
scripts/photo_ingest.py:249:                source_path,
scripts/photo_ingest.py:253:                source_path
scripts/photo_ingest.py:257:                f"[REGISTER] {photo_id}"
scripts/photo_ingest.py:281:            "Register new photos and assign permanent photo_id"
scripts/qwen4b_output_v01.py:154:    Для Qwen источником всегда является source_path.
scripts/qwen4b_output_v01.py:163:                photo_id,
scripts/qwen4b_output_v01.py:164:                source_path,
scripts/qwen4b_output_v01.py:168:              AND source_path IS NOT NULL
scripts/qwen4b_output_v01.py:169:              AND source_path <> ''
scripts/qwen4b_output_v01.py:198:def mark_done(conn, photo_id, result, elapsed):
scripts/qwen4b_output_v01.py:294:                photo_id,
scripts/qwen4b_output_v01.py:301:def mark_error(conn, photo_id, error):
scripts/qwen4b_output_v01.py:317:                photo_id,
scripts/qwen4b_output_v01.py:551:            photo_id = row["photo_id"]
scripts/qwen4b_output_v01.py:552:            source_path = row["source_path"]
scripts/qwen4b_output_v01.py:557:                photo_id,
scripts/qwen4b_output_v01.py:561:                source_path,
scripts/qwen4b_output_v01.py:568:                path = Path(source_path)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

find app scripts -type f \
  \( -name "*.py" -o -name "*.sh" $ \
  -not -path "*/.venv/*" \
  | sort
app/cli.py
app/core/config.py
app/core/embedder.py
app/core/fingerprint.py
app/core/image.py
app/core/__init__.py
app/core/recognizer.py
app/core/runtime.py
app/core/scene_analyzer.py
app/__init__.py
app/main.py
app/ocr/grid_ocr.py
app/ocr/__init__.py
app/ocr/ocr_pipeline.py
app/ocr/plate_detector.py
app/pipeline/__init__.py
app/pipeline/queue.py
app/pipeline/worker.py
app/web/client_aliases.py
app/web/client_db.py
app/web/components/addresses.py
app/web/components/clients.py
app/web/components/collections.py
app/web/components/filters.py
app/web/components/header.py
app/web/components/__init__.py
app/web/components/photos_before_cache_20260816_145128.py
app/web/components/photos.py
app/web/components/search.py
app/web/components/technical_modules/automation.py
app/web/components/technical_modules/data.py
app/web/components/technical_modules/fingerprints.py
app/web/components/technical_modules/__init__.py
app/web/components/technical_modules/last_run.py
app/web/components/technical_modules/photo_processing.py
app/web/components/technical_modules/qwen.py
app/web/components/technical_modules/system.py
app/web/components/technical_modules/users.py
app/web/components/technical.py
app/web/config.py
app/web/filters.py
app/web/frontend_v01_backup_before_modular.py
app/web/frontend_v01.py
app/web/frontend_v02.py
app/web/__init__.py
app/web/main.py
app/web/photo_db.py
app/web/state.py
app/web/system/__init__.py
app/web/system/monitor.py
app/web/users_db.py
app/web_v01_backup_20260816_142053/components/addresses.py
app/web_v01_backup_20260816_142053/components/clients.py
app/web_v01_backup_20260816_142053/components/collections.py
app/web_v01_backup_20260816_142053/components/filters.py
app/web_v01_backup_20260816_142053/components/header.py
app/web_v01_backup_20260816_142053/components/__init__.py
app/web_v01_backup_20260816_142053/components/photos.py
app/web_v01_backup_20260816_142053/components/search.py
app/web_v01_backup_20260816_142053/components/technical.py
app/web_v01_backup_20260816_142053/config.py
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py
app/web_v01_backup_20260816_142053/frontend_v01.py
app/web_v01_backup_20260816_142053/frontend_v02.py
app/web_v01_backup_20260816_142053/__init__.py
app/web_v01_backup_20260816_142053/main.py
app/web_v01_backup_20260816_142053/state.py
app/workers/dino_worker.py
scripts/analyze_sequence_v38.py
scripts/analyze_subfingerprints.py
scripts/banner_candidates_v01.py
scripts/banner_crop_search_v01.py
scripts/banner_crop_search_v02.py
scripts/banner_database_v01.py
scripts/banner_database_v02.py
scripts/banner_llm_folder_search_v01.py
scripts/banner_llm_full_v01.py
scripts/banner_llm_full_v02.py
scripts/banner_model_compare_v01.py
scripts/banner_model_compare_v02.py
scripts/banner_model_compare_v03.py
scripts/banner_model_compare_v04.py
scripts/banner_model_compare_v05.py
scripts/banner_qwen25vl_test_v01.py
scripts/banner_qwen4b_test_v01.py
scripts/banner_search_v01.py
scripts/banner_search_v02.py
scripts/banner_search_v03_2.py
scripts/banner_search_v03_3.py
scripts/banner_search_v03.py
scripts/benchmark_hybrid_v01.py
scripts/benchmark_hybrid_v02.py
scripts/benchmark_hybrid_v03.py
scripts/benchmark_hybrid_v04.py
scripts/benchmark_hybrid_v05.py
scripts/benchmark_hybrid_v06.py
scripts/benchmark_hybrid_v07.py
scripts/benchmark_hybrid_v08.py
scripts/benchmark_hybrid_v09.py
scripts/benchmark_hybrid_v10_debug.py
scripts/benchmark_hybrid_v11.py
scripts/benchmark_hybrid_v12_full.py
scripts/benchmark_sub_rerank_v01.py
scripts/benchmark_sub_rerank_v02.py
scripts/benchmark_sub_rerank_v03.py
scripts/benchmark_sub_rerank_v04.py
scripts/benchmark_test_sub_exp.py
scripts/benchmark_test_v1.py
scripts/build_margin_best_from_benchmark.py
scripts/build_subfingerprint_database.py
scripts/build_subfingerprints_exp.py
scripts/compare_benchmark_sub.py
scripts/create_previews_v01.py
scripts/crop_test_banner.py
scripts/dry_run_best_sequence.py
scripts/export_subclusters.py
scripts/export_visual_compare.py
scripts/import_qwen_to_db.py
scripts/llm_resolver_v01.py
scripts/make_subcluster_contact.py
scripts/make_subfingerprints.py
scripts/make_subfingerprints_v2.py
scripts/migrate_sqlite_to_postgres.py
scripts/photo_ingest.py
scripts/qwen4b_output_v01_before_compact_prompt.py
scripts/qwen4b_output_v01.py
scripts/qwen_prompt_ablation.py
scripts/run_daily_hybrid_v12.sh
scripts/run_hybrid_v12.py
scripts/search_banners_v01.py
scripts/sort_baseline.py
scripts/sort_margin005_best.py
scripts/sort_neighbor_v34.py
scripts/sort_neighbor_v35_benchmark.py
scripts/sort_neighbor_v35.py
scripts/sort_neighbor_v36_img.py
scripts/sort_neighbor_v36.py
scripts/sort_neighbor_v37.py
scripts/sort_sequence_sub_v01.py
scripts/sort_sequence_v38_1.py
scripts/sort_sequence_v38_1_subtest.py
scripts/sort_sequence_v38.py
scripts/sort_sequence_v39.py
scripts/sort_test_and_report_hybrid_v12.py
scripts/sort_test_and_report.py
scripts/sort_test_and_report_v2.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 23:37:16

> **Inspecting Ingest and Worker Files**
>
>
> **Inspecting Ingest and Worker Files**
>
> 
>
> Worked for a couple of seconds

Да. По выводу уже видно главное: **`photo_id` сейчас создаётся на этапе `photo_ingest.py`, то есть до разделения на DINO и Qwen — это именно то, что нам нужно.**

Но сейчас архитектуру надо немного довести до окончательной схемы.

### Фиксируем модель

```text
                    НОВЫЙ ФАЙЛ
                         │
                         ▼
                  PHOTO INGEST
                         │
             ┌───────────┴───────────┐
             │                       │
        initial_id               photo_id
        псевдоним                 постоянный
        запуска/пакета             ID фото
             │                       │
             └───────────┬───────────┘
                         │
                  ┌──────┴──────┐
                  │             │
                 DINO          QWEN
                  │             │
             address_id     описание/JSON
                  │             │
                  └──────┬──────┘
                         │
                      PHOTOS
                         │
                         ▼
                       GRID
```

При этом:

- `photo_id` **никогда не зависит от адреса**;
- `initial_id` — технический идентификатор исходного набора/псевдоним;
- `address_id` появляется **только после DINO**;
- Qwen вообще не интересуется `address_id`;
- Qwen работает по `photo_id`;
- Grid показывает фотографию **только если `address_id IS NOT NULL`**;
- описание Qwen подтягивается в Grid по тому же `photo_id`.

### И самое важное

DINO и Qwen больше **не должны быть одним последовательным pipeline**.

Будет:

```text
PHOTO INGEST
    │
    ├──────────────► DINO QUEUE
    │                    │
    │                    ▼
    │               address_id
    │                    │
    │                    ▼
    │                   GRID
    │
    └──────────────► QWEN QUEUE
                         │
                         ▼
                    Qwen JSON
                         │
                         ▼
                    photo_id
```

То есть Qwen может анализировать фотографию **сразу после получения `photo_id`**, не дожидаясь DINO.

А Grid начнёт её показывать только после:

```sql
address_id IS NOT NULL
```

Это также решает нашу предыдущую задачу: **Qwen не должен ждать физической сортировки файлов DINO**.

---

## По текущей БД

У тебя уже есть необходимые поля:

```text
photo_id
initial_id
address_id

dino_status
qwen_status
sort_status
preview_status
```

И индексы:

```text
idx_photos_initial_id
idx_photos_address_id
idx_photos_dino_queue
idx_photos_qwen_queue
```

То есть сейчас **не надо ломать таблицу `photos`**.

Следующий правильный шаг — не переписывать всё сразу, а сделать единый механизм состояния процесса.

### Я предлагаю следующие состояния

Для DINO:

```text
pending
processing
paused
done
error
```

Для Qwen:

```text
pending
processing
paused
done
error
```

Общее состояние фотографии:

```text
pending
processing
ready
error
```

Но `status` **не должен быть главным источником истины**. Главными остаются:

```text
dino_status
qwen_status
```

а `status` можно использовать как общее состояние.

---

## Режим запуска

И здесь уже фиксируем нашу договорённость:

```text
РЕЖИМ

○ Ручной
○ Watcher
○ Автоматический
```

### Ручной

UI:

```text
             [ ЗАПУСТИТЬ ]
             [ ОСТАНОВИТЬ ]

DINO        [ ЗАПУСТИТЬ ] [ОСТАНОВИТЬ]
            ███████░░░ 73%

QWEN        [ ЗАПУСТИТЬ ] [ОСТАНОВИТЬ]
            ████░░░░░░ 41%
```

Кнопки DINO/Qwen активны.

### Watcher

Watcher постоянно смотрит INPUT.

```text
WATCHER
   ↓
новый файл
   ↓
photo_id
   ↓
DINO + QWEN
```

При этом ручные кнопки запуска:

```text
[ ЗАПУСТИТЬ ]   ← неактивна
```

Работает только watcher.

### Автоматический

Например:

```text
Автоматический запуск
Время: [ 02:00 ]

                 [ ЗАПУСТИТЬ ]
```

Но запуск в назначенное время происходит автоматически.

При этом ручной запуск можно разрешить **дополнительно**, как мы договорились:

> автоматический режим не запрещает ручной запуск.

---

## Остановка

Очень важное правило:

Если нажали общий:

```text
[ ОСТАНОВИТЬ ]
```

то:

```text
DINO       → stop
QWEN       → stop
WATCHER    → stop
AUTOMATIC  → stop
```

и режим автоматически возвращается:

```text
РЕЖИМ: РУЧНОЙ
```

То есть после остановки UI возвращается в исходное состояние.

---

## Пауза

Как договорились:

```text
🟡 ЖЁЛТЫЙ = ПАУЗА
🟠 ОРАНЖЕВЫЙ = РАБОТАЕТ
🔴 КРАСНЫЙ = ОШИБКА
🟢 ЗЕЛЁНЫЙ = ГОТОВ / ОЖИДАНИЕ
```

Оранжевый индикатор мигает примерно раз в 1–2 секунды.

Например:

```text
PIPELINE     🟠 РАБОТАЕТ

DINO         🟠
████████░░░░  67 / 100

QWEN         🟠
█████░░░░░░░  43 / 100
```

Если DINO закончил:

```text
DINO         🟢 ГОТОВ
100 / 100
```

Qwen ещё работает:

```text
QWEN         🟠 РАБОТАЕТ
73 / 100
```

Общий:

```text
PIPELINE     🟠 РАБОТАЕТ
```

---

### И ещё один принцип, который сейчас особенно важен

**Не будем больше использовать наличие файла в OUTPUT как признак завершения обработки.**

Состояние определяется БД:

```text
photo_id
initial_id
dino_status
address_id
qwen_status
```

А физическое:

```text
OUTPUT/78/
OUTPUT/79/
...
```

становится вторичным результатом сортировки.

Это позволит нам нормально сделать:

- продолжение после остановки;
- пропуск уже обработанных;
- повторную обработку;
- параллельный DINO/Qwen;
- watcher;
- автоматический запуск;
- Grid в реальном времени.

Следующим шагом я бы **не трогал пока UI**. Сначала надо привести `photo_ingest → photos → dino_worker → qwen_worker` к этой схеме. После этого UI уже просто будет управлять этими состояниями.

---

### 👤 **User** — 2026-08-18 23:37:39

да

---

### 🤖 **Assistant** — 2026-08-18 23:37:40

Да. Тогда двигаемся **снизу вверх: сначала БД и workers, потом UI**.

Первый этап — сделать единый жизненный цикл фотографии:

```text
INPUT
  │
  ▼
photo_ingest
  │
  ├── photo_id       ← постоянный ID
  ├── initial_id     ← ID набора
  │
  ├──────────────► DINO
  │                  │
  │                  └── address_id
  │
  └──────────────► QWEN
                     │
                     └── JSON по photo_id
```

И только:

```sql
address_id IS NOT NULL
```

делает фотографию доступной Grid.

### Что делаем сейчас

1. **`photo_ingest.py`**
   - оставляем генерацию `photo_id`;
   - добавляем/сохраняем `initial_id`;
   - при регистрации новой фотографии выставляем:
     ```text
     dino_status = pending
     qwen_status = pending
     ```
   - повторно зарегистрированные `source_path` не создаём.

2. **DINO worker**
   - берёт `pending`;
   - ставит `processing`;
   - получает `address_id`;
   - записывает результат;
   - ставит `done`;
   - ошибка → `error`;
   - остановка → корректно оставляет необработанные записи `pending`.

3. **Qwen worker**
   - берёт ту же `photos`;
   - идентификация **только по `photo_id`**;
   - источник — `source_path`;
   - `address_id` ему не нужен;
   - результат сохраняет в ту же строку;
   - `qwen_status = done`.

4. **Физическая сортировка**
   - вообще убираем из критического пути DINO/Qwen;
   - она становится отдельным процессом;
   - Grid от неё не зависит.

5. **Grid**
   запрос примерно такого типа:
   ```sql
   SELECT ...
   FROM photos
   WHERE address_id IS NOT NULL
   ```
   и Qwen-поля подтягиваются из этой же строки.

6. После этого делаем **Process Controller**, который уже управляет:
   ```text
   Ручной / Watcher / Автоматический
   ```

---

### Главное изменение

Старый:

```text
DINO
 ↓
Hybrid
 ↓
SORT OUTPUT
 ↓
QWEN
 ↓
GRID
```

заменяем на:

```text
             ┌──► DINO ──► address_id ──┐
INPUT ─► ID ─┤                           ├──► GRID
             └──► QWEN ──► description ─┘
```

Причём обе ветки работают **параллельно и независимо**.

А `photo_id` является единственным ключом, связывающим их.

И это хорошо ложится на уже существующую структуру `photos`: у тебя для этого фактически всё необходимое уже есть.

---

### 👤 **User** — 2026-08-18 23:38:02

к

---

### 🤖 **Assistant** — 2026-08-18 23:38:03

Да, фиксируем. Следующий шаг - **реализуем этот слой в коде**, не меняя пока UI.

---

### 👤 **User** — 2026-08-18 23:38:06

Реализуй этот слой в коде

---

### 🤖 **Assistant** — 2026-08-18 23:38:07

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed photo ingest, connected DINO and Qwen workers, and checked photo identification**
>
> 
>
> Worked for 14s

Да. Реализуем **первый рабочий слой сейчас**, но не будем пока трогать UI и не будем переписывать сам алгоритм DINO v12.

Есть важный момент: у меня нет прямого доступа к твоему каталогу `~/projects/scene_fingerprint_mvp_v02` в твоей машине, поэтому я не могу физически изменить файлы там. Но я могу дать **точные команды, которые ты выполняешь в проекте**, и мы сразу проверяем результат.

Сделаем 4 изменения:

1. `photo_ingest.py` — регистрация `photo_id + initial_id`, постановка обеих веток в `pending`.
2. DINO worker — работает только со своей очередью и записывает `address_id`.
3. Qwen — работает только со своей очередью и записывает результат по `photo_id`.
4. Добавим общий DB-слой для атомарного claim/reset/retry, чтобы потом на него без переделки повесить Stop/Pause/Watcher.

### 1. Сначала сделаем резервные копии

```bash
cd ~/projects/scene_fingerprint_mvp_v02

cp scripts/photo_ingest.py \
   scripts/photo_ingest.py.bak_pipeline_v01

cp app/workers/dino_worker.py \
   app/workers/dino_worker.py.bak_pipeline_v01

cp scripts/qwen4b_output_v01.py \
   scripts/qwen4b_output_v01.py.bak_pipeline_v01
```

### 2. Проверяем текущую регистрацию

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,300p' scripts/photo_ingest.py
```

**Пришли вывод целиком.**

Я специально не предлагаю пока blindly заменять `photo_ingest.py`: там уже есть рабочая генерация постоянного `photo_id`, и нам надо сохранить её один-в-один, добавив только `initial_id` и начальные состояния.

После этого я дам готовую замену именно для этого файла, затем отдельно DINO и Qwen.

Целевая запись после ingest будет такой:

```text
photo_id       = PH_00000123
initial_id     = DAILY_20260818_001
source_path    = /.../INPUT/xxx.jpg

dino_status    = pending
qwen_status    = pending

address_id     = NULL
```

И **сразу после этой записи обе очереди видят фотографию независимо друг от друга**.

---

### 👤 **User** — 2026-08-18 23:39:01

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

cp scripts/photo_ingest.py \
   scripts/photo_ingest.py.bak_pipeline_v01

cp app/workers/dino_worker.py \
   app/workers/dino_worker.py.bak_pipeline_v01

cp scripts/qwen4b_output_v01.py \
   scripts/qwen4b_output_v01.py.bak_pipeline_v01
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,300p' scripts/photo_ingest.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

