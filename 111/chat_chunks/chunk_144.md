## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 🤖 **Assistant** — 2026-08-19 00:01:37

Да. Тогда следующий шаг — **не трогать пока грид и автоматику**, а сначала сделать правильный слой **INGEST**.

### Шаг 1. Определяем постоянный каталог

Предлагаю:

```text
data/
└── catalog/
    ├── 2026-08/
    │   ├── 18/
    │   │   ├── photo_001.jpg
    │   │   ├── photo_002.jpg
    │   │   └── ...
    │   └── 19/
    └── 2026-09/
        └── 01/
```

Но **имя файла лучше пока не менять**, если исходное имя несёт полезную информацию. В БД всё равно будет храниться оригинальное имя.

---

## Шаг 2. Нужен уникальный идентификатор фотографии

Не стоит определять «новая/старая» только по имени.

Лучше:

```text
photo_id = SHA-256 содержимого файла
```

Тогда:

```text
один и тот же файл
→ один photo_id
→ повторно не импортируется
```

А если файл имеет другое имя, но содержимое полностью одинаковое:

```text
IMG001.jpg
IMG999.jpg
```

они тоже будут распознаны как один и тот же файл.

При этом в БД можно хранить:

```text
photo_id
filename
source_path
catalog_path
sha256
file_size
captured_at
catalog_date
```

---

# Шаг 3. INGEST должен делать именно это

```text
Входная папка
      │
      ▼
найти JPG/JPEG/PNG
      │
      ▼
SHA-256
      │
      ▼
есть такой hash в photos?
   ┌──┴───┐
  ДА      НЕТ
   │       │
 SKIP      ▼
       определить дату
           │
           ▼
       каталог
      YYYY-MM/DD
           │
           ▼
       скопировать
           │
           ▼
       INSERT photos
           │
           ▼
       dino=pending
       qwen=pending
```

---

## Шаг 4. Очень важный момент с датой

Здесь я бы **не привязывался к дате запуска программы**.

Нужно определить приоритет:

```text
1. EXIF DateTimeOriginal
2. дата файла
3. дата импорта — как fallback
```

То есть если фотография была сделана:

```text
18 августа
```

а мы загрузили её в базу:

```text
19 августа
```

она всё равно попадёт:

```text
2026-08/18/
```

Это как раз соответствует твоей модели:

> месяц → число → фотографии.

---

# Шаг 5. БД становится главным реестром

Условно запись:

```text
photos
────────────────────────────────────────────
id                  12345
photo_id            sha256:abcd...
filename            IMG_0042.JPG

catalog_path        /catalog/2026-08/18/IMG_0042.JPG

photo_date          2026-08-18
photo_month         2026-08
photo_day           18

dino_status         pending
qwen_status         pending

address_id          NULL
client              NULL
brand               NULL
...
```

После DINO:

```text
dino_status = done
address_id = 83
```

После Qwen:

```text
qwen_status = done
client = "..."
brand = "..."
...
```

**Запись не создаётся заново.**

---

# Шаг 6. Очередь

Тут у нас уже есть хорошая основа.

Сейчас `app/pipeline/queue.py` — очередь для создания fingerprint.

Её **не надо насильно превращать в очередь фотографий**.

Для фотографий у нас уже фактически есть очередь в PostgreSQL через:

```text
dino_status
qwen_status
```

и `FOR UPDATE SKIP LOCKED`.

То есть архитектура получается:

```text
                 photos
                   │
          ┌────────┴────────┐
          │                 │
    dino_status        qwen_status
          │                 │
          ▼                 ▼
     DINO worker       Qwen worker
```

Это даже лучше, чем отдельный SQLite queue.

---

# Что я предлагаю сделать прямо сейчас

**Не писать пока код вслепую.**

Следующее — посмотреть текущую структуру `photos`, потому что она у нас уже содержит довольно много нужных полей.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -h localhost -U lora -d photobase -c "\d photos"
```

И отдельно:

```bash
psql -h localhost -U lora -d photobase -c "
SELECT
    id,
    photo_id,
    source_path,
    filename,
    dino_status,
    qwen_status,
    address_id,
    client,
    brand,
    created_at,
    updated_at
FROM photos
ORDER BY id DESC
LIMIT 5;
"
```

**После этого уже точно спроектируем INGEST под твою существующую таблицу**, а не будем создавать параллельную структуру.

Следующим шагом сделаем маленький `photo_ingest.py`, который сначала будет работать в режиме **dry-run**: ничего не копирует и не меняет БД, а только показывает:

```text
NEW   IMG001.JPG → 2026-08/18/
SKIP  IMG002.JPG → уже существует
NEW   IMG003.JPG → 2026-08/18/
```

И только после проверки включим реальную запись.

---

### 👤 **User** — 2026-08-19 00:02:35

Column         |            Type             | Collation | Nullable |              Default               
-----------------------+-----------------------------+-----------+----------+------------------------------------
 id                    | bigint                      |           | not null | nextval('photos_id_seq'::regclass)
 photo_id              | text                        |           | not null | 
 source_path           | text                        |           | not null | 
 path                  | text                        |           | not null | 
 filename              | text                        |           | not null | 
 original_filename     | text                        |           |          | 
 address               | text                        |           |          | 
 client                | text                        |           |          | 
 brand                 | text                        |           |          | 
 category              | text                        |           |          | 
 description           | text                        |           |          | 
 status                | text                        |           | not null | 'pending'::text
 dino_status           | text                        |           | not null | 'pending'::text
 qwen_status           | text                        |           | not null | 'pending'::text
filename              | text                        |           | not null | 
 original_filename     | text                        |           |          | 
 address               | text                        |           |          | 
 client                | text                        |           |          | 
 brand                 | text                        |           |          | 
 category              | text                        |           |          | 
 description           | text                        |           |          | 
 status                | text                        |           | not null | 'pending'::text
 dino_status           | text                        |           | not null | 'pending'::text
 qwen_status           | text                        |           | not null | 'pending'::text
 sort_status           | text                        |           | not null | 'pending'::text
 preview_status        | text                        |           | not null | 'pending'::text
 error_message         | text                        |           |          | 
 dino_fingerprint      | text                        |           |          | 
 dino_score            | double precision            |           |          | 
 dino_second_score     | double precision            |           |          | 
 dino_margin           | double precision            |           |          | 
 dino_time_sec         | double precision            |            dino_score            | double precision            |           |          | 
 dino_second_score     | double precision            |           |          | 
 dino_margin           | double precision            |           |          | 
 dino_time_sec         | double precision            |           |          | 
 hybrid_original_id    | text                        |           |          | 
 hybrid_final_id       | text                        |           |          | 
 hybrid_changed        | boolean                     |           |          | false
 hybrid_old_score      | double precision            |           |          | 
 hybrid_score          | double precision            |           |          | 
 hybrid_margin         | double precision            |           |          | 
 hybrid_neighbors      | jsonb                       |           |          | 
 confidence            | integer                     |           |          | 
 qwen_time_sec         | double precision            |           |          | 
 text_json             | jsonb                       |           |          | 
 colors_json           | jsonb                       |           |          | 
 objects_json          | jsonb                       |           |          | 
 environment_json      | jsonb                       |           |          | 
 image_quality_json    | jsonb                       |           |          | 
 camera_view_json      | jsonb                       |           |          | 
 scene_objects_json    | jsonb                       |           |          | 
 analysis_quality_json | jsonb                       |           |          | 
 raw_json              | jsonb                       |           |          | 
:
 analysis_quality_json | jsonb                       |           |          | 
 raw_json              | jsonb                       |           |          | 
 preview_path          | text                        |           |          | 
 created_at            | timestamp without time zone |           | not null | CURRENT_TIMESTAMP
 updated_at            | timestamp without time zone |           | not null | CURRENT_TIMESTAMP
 source_id             | text                        |           |          | 
 address_id            | text                        |           |          | 
 initial_id            | text                        |           |          | 
 dino_started_at       | timestamp without time zone |           |          | 
 qwen_started_at       | timestamp without time zone |           |          | 
Indexes:
    "photos_pkey" PRIMARY KEY, btree (photo_id)
    "idx_photos_address" btree (address)
    "idx_photos_address_id" btree (address_id)
    "idx_photos_client" btree (client)
    "idx_photos_dino_fingerprint" btree (dino_fingerprint)
    "idx_photos_dino_processing" btree (dino_status, dino_started_at)
    "idx_photos_dino_queue" btree (dino_status, id)
    "idx_photos_hybrid_final" btree (hybrid_final_id)
    "idx_photos_initial_id" btree (initial_id)
    "idx_photos_preview_queue" btree (preview_status, id)
:    "idx_photos_dino_fingerprint" btree (dino_fingerprint)
    "idx_photos_dino_processing" btree (dino_status, dino_started_at)
    "idx_photos_dino_queue" btree (dino_status, id)
    "idx_photos_hybrid_final" btree (hybrid_final_id)
    "idx_photos_initial_id" btree (initial_id)
    "idx_photos_preview_queue" btree (preview_status, id)
    "idx_photos_qwen_processing" btree (qwen_status, qwen_started_at)
    "idx_photos_qwen_queue" btree (qwen_status, id)
    "idx_photos_sort_queue" btree (sort_status, id)
    "idx_photos_source_id" btree (source_id)
    "idx_photos_status" btree (status)
    "photos_id_key" UNIQUE CONSTRAINT, btree (id)
    "ux_photos_source_path" UNIQUE, btree (source_path)

---

### 🤖 **Assistant** — 2026-08-19 00:02:36

Отлично. Теперь видно, что **переделывать таблицу `photos` с нуля вообще не нужно**. Она уже практически готова под постоянный каталог.

И даже важнее: у нас уже есть правильные очереди для DINO, Qwen, сортировки и preview.

### Что уже есть

```text
photos
│
├── photo_id              ← PRIMARY KEY
├── source_path           ← UNIQUE
├── path
├── filename
├── original_filename
│
├── address
├── address_id
├── client
├── brand
├── category
├── description
│
├── dino_status
├── dino_fingerprint
├── dino_score
├── dino_second_score
├── dino_margin
│
├── hybrid_original_id
├── hybrid_final_id
├── hybrid_changed
├── hybrid_neighbors
│
├── qwen_status
├── text_json
├── colors_json
├── objects_json
├── environment_json
├── image_quality_json
├── camera_view_json
├── analysis_quality_json
├── raw_json
│
├── sort_status
├── preview_status
├── preview_path
│
└── created_at / updated_at
```

То есть **фактически у нас уже есть центральная фотобаза**.

---

# Единственное, чего сейчас явно не хватает

Для модели:

```text
2026-08/
   18/
      фото
   19/
      фото
```

нам желательно иметь **дату фотографии как отдельное нормальное поле**, а не пытаться каждый раз извлекать её из `source_path`.

Я бы добавил:

```sql
photo_date
```

тип:

```text
date
```

А при необходимости позже:

```text
capture_time
```

Но пока достаточно `photo_date`.

Тогда запрос грида становится элементарным:

```sql
WHERE photo_date >= '2026-08-01'
  AND photo_date <  '2026-09-01'
```

или:

```sql
WHERE photo_date = '2026-08-18'
```

И индекс:

```sql
CREATE INDEX idx_photos_photo_date
ON photos(photo_date);
```

---

# Но есть ещё более важный момент

Сейчас:

```text
PRIMARY KEY (photo_id)
UNIQUE (source_path)
```

Это хорошо, **но `source_path` не должен быть идентификатором фотографии**.

Например сегодня:

```text
/incoming/IMG001.JPG
```

завтра файл может оказаться:

```text
/incoming2/IMG001.JPG
```

Это должна быть **та же фотография**, если содержимое одинаковое.

Поэтому:

```text
photo_id = SHA-256 файла
```

оставляем главным постоянным ID.

А:

```text
source_path
```

означает только:

> откуда этот файл был импортирован.

---

# И я бы не менял `path`

Сейчас есть:

```text
source_path
path
```

Это удобно.

Предлагаю семантику:

```text
source_path
    ↓
исходное место поступления файла

path
    ↓
постоянное расположение файла в фотокаталоге
```

Например:

```text
source_path =
/mnt/incoming/IMG_0042.JPG

path =
/data/catalog/2026-08/18/IMG_0042.JPG
```

А:

```text
filename
```

— имя файла в каталоге.

```text
original_filename
```

— оригинальное имя при поступлении.

---

# Тогда INGEST становится очень чистым

При поступлении файла:

### 1. Считаем SHA-256

```text
photo_id = sha256(file)
```

### 2. Проверяем БД

```sql
SELECT photo_id
FROM photos
WHERE photo_id = %s;
```

Есть?

```text
ДА → ничего не делать
```

Нет?

```text
НЕТ → новая фотография
```

### 3. Определяем дату

```text
EXIF DateTimeOriginal
        ↓ если нет
mtime файла
        ↓ если проблема
текущая дата
```

### 4. Формируем каталог

Например:

```text
data/catalog/
└── 2026-08/
    └── 18/
        └── IMG_0042.JPG
```

### 5. INSERT

```text
photo_id
source_path
path
filename
original_filename
photo_date
status = pending
dino_status = pending
qwen_status = pending
sort_status = pending
preview_status = pending
```

---

# И вот здесь появляется очень хорошая вещь

**Не нужно отдельно создавать очередь новых фотографий.**

После INSERT:

```text
dino_status = pending
qwen_status = pending
sort_status = pending
preview_status = pending
```

И уже существующие workers смогут их подобрать.

Получается:

```text
             INGEST
                │
                ▼
             photos
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼
    DINO       QWEN     PREVIEW
      │         │         │
      └─────────┼─────────┘
                ▼
             photos
                │
                ▼
               GRID
```

---

# А `hybrid` я бы пока не выбрасывал

Потому что у нас есть:

```text
hybrid_original_id
hybrid_final_id
hybrid_neighbors
hybrid_score
hybrid_margin
```

и ты отдельно говорил, что **сортировка смотрит на соседние фотографии и результаты соседей**.

Это значит, что Hybrid/sequence sorting — это не просто «старый daily-скрипт».

Его надо встроить в новую систему как отдельный этап:

```text
DINO
 ↓
первичный результат
 ↓
SEQUENCE / HYBRID
 ↓
финальный address
```

То есть:

```text
dino_fingerprint
       ↓
initial_id
       ↓
hybrid_original_id
       ↓
neighbor analysis
       ↓
hybrid_final_id
       ↓
address_id
```

---

# Поэтому новая архитектура получается такой

```text
                    ПОСТУПИЛИ ФОТО
                          │
                          ▼
                    ┌───────────┐
                    │  INGEST   │
                    └─────┬─────┘
                          │
                 SHA-256 / EXIF
                          │
                          ▼
                    ┌───────────┐
                    │  PHOTOS   │
                    │ PostgreSQL│
                    └─────┬─────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
            DINO        QWEN       PREVIEW
              │
              ▼
        INITIAL RESULT
              │
              ▼
       HYBRID / NEIGHBORS
              │
              ▼
        FINAL ADDRESS
              │
              ▼
           PHOTOS
              │
              ▼
             GRID
```

### И главное:

**никакого `output/daily/20260819_...` для основной базы больше не требуется.**

Output конкретного запуска можно оставить только как **служебный отчёт/лог**, если он нужен для аудита.

А сами фотографии и результаты живут постоянно:

```text
catalog/2026-08/18/...
catalog/2026-08/19/...
catalog/2026-08/20/...
```

и:

```text
PostgreSQL
    ↓
все фотографии за всё время
```

---

## Следующий конкретный шаг

Я бы сейчас **не писал ещё INGEST**.

Сначала проверим существующие записи `photos`, чтобы понять, **что именно уже лежит в `source_path`, `path`, `filename`, `photo_id` и `created_at`**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -h localhost -U lora -d photobase -c "
SELECT
    id,
    photo_id,
    source_path,
    path,
    filename,
    original_filename,
    created_at,
    dino_status,
    qwen_status,
    sort_status,
    preview_status,
    address_id,
    hybrid_final_id
FROM photos
ORDER BY id DESC
LIMIT 10;
"
```

И ещё:

```bash
psql -h localhost -U lora -d photobase -c "
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE dino_status = 'done') AS dino_done,
    COUNT(*) FILTER (WHERE qwen_status = 'done') AS qwen_done,
    COUNT(*) FILTER (WHERE sort_status = 'done') AS sort_done,
    COUNT(*) FILTER (WHERE preview_status = 'done') AS preview_done
FROM photos;
"
```

По этим двум выводам уже можно будет **точно состыковать новый постоянный каталог с тем, что у нас реально накоплено сейчас**, не ломая существующую фотобазу.

---

### 👤 **User** — 2026-08-19 00:02:55

---+-------------+------------------------------------------------------------------------------------------+------------------------+-------------+-------------+------------+--------+-------+----------------------------+----------------------------
 526 | PH_00000526 | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (9).JPG | Шолохова 127 А (9).JPG | done        | pending     |            |        |       | 2026-08-18 21:22:57.684272 | 2026-08-18 22:54:48.253414
 525 | PH_00000525 | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (8).JPG | Шолохова 127 А (8).JPG | done        | pending     |            |        |       | 2026-08-18 21:22:57.684272 | 2026-08-18 22:54:48.253414
 524 | PH_00000524 | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (7).JPG | Шолохова 127 А (7).JPG | done        | pending     |            |        |       | 2026-08-18 21:22:57.684272 | 2026-08-18 22:54:48.253414
 523 | PH_00000523 | /home/alexice/projects/scene_fingerprint_mvp_v02/data/input/daily/Шолохова 127 А (6).JPG | Шолохова 127 А (6).JPG | done        | pending     |            |        |       | 2026-08-18 21:22:57.684272 | 2026-08-18 22:54:

---

### 🤖 **Assistant** — 2026-08-19 00:02:56

Вот теперь картина стала намного яснее.

Сейчас существующая база **уже содержит 526 фотографий**, но `photo_id` у неё не является SHA-256:

```text
PH_00000526
PH_00000525
PH_00000524
...
```

А `source_path` указывает прямо в старый:

```text
data/input/daily/
```

То есть текущая система фактически работает как **реестр последнего/текущего поступления**, а не как постоянный каталог.

### Я бы сейчас ничего не ломал

Нам нужно сделать переход:

```text
СТАРАЯ СХЕМА

data/input/daily/
        ↓
photos
        ↓
DINO / Hybrid / Qwen
```

в:

```text
НОВАЯ СХЕМА

data/catalog/
    2026-08/
        18/
        19/
        ...
        ↓
photos
        ↓
DINO / Hybrid / Qwen
        ↓
GRID
```

---

## И есть важный нюанс

Судя по записи:

```text
PH_00000526
/home/.../data/input/daily/Шолохова 127 А (9).JPG
Шолохова 127 А (9).JPG
```

**имя файла уже содержит потенциально полезную информацию**, например:

```text
Шолохова 127 А
```

и индекс:

```text
(9)
```

Но мы **не должны использовать имя как уникальный ID**.

Например завтра может снова прийти:

```text
Шолохова 127 А (9).JPG
```

и это совершенно не обязательно та же фотография.

---

# Поэтому предлагаю изменить только идентификацию

Не обязательно сразу переходить на SHA-256 как `photo_id`.

Можно сделать ещё лучше:

```text
photo_id = постоянный внутренний ID
```

например:

```text
PH_00000527
PH_00000528
PH_00000529
```

а дополнительно добавить:

```text
file_hash = SHA-256
```

Тогда:

```text
photo_id
    = идентификатор записи

file_hash
    = идентификатор содержимого файла
```

Это гораздо чище.

---

# Для существующих 526 фото

Мы их **не импортируем заново**.

Делаем миграцию:

```text
PH_00000526
        │
        ├── оставляем photo_id
        │
        ├── вычисляем file_hash
        │
        ├── определяем photo_date
        │
        └── переносим физический файл
             ↓
        data/catalog/2026-08/18/
```

Например:

```text
старое:

data/input/daily/Шолохова 127 А (9).JPG

новое:

data/catalog/2026-08/18/Шолохова 127 А (9).JPG
```

В БД:

```text
photo_id       PH_00000526

source_path    /home/.../data/input/daily/Шолохова 127 А (9).JPG

path           /home/.../data/catalog/2026-08/18/Шолохова 127 А (9).JPG

filename       Шолохова 127 А (9).JPG

original_filename
               Шолохова 127 А (9).JPG

file_hash      ...
photo_date     2026-08-18
```

---

# А дальше новые фото

Допустим, сегодня поступили:

```text
Шолохова 127 А (1).JPG
Шолохова 127 А (2).JPG
Шолохова 127 А (3).JPG
```

INGEST считает hash.

Если hash уже есть:

```text
SKIP
```

Если нет:

```text
PH_00000527
```

и:

```text
data/catalog/2026-08/19/Шолохова 127 А (1).JPG
```

После этого:

```text
dino_status = pending
qwen_status = pending
sort_status = pending
preview_status = pending
```

---

# И ещё одна важная вещь

Я вижу, что у нас уже есть:

```text
sort_status
preview_status
```

и соответствующие индексы:

```text
idx_photos_sort_queue
idx_photos_preview_queue
```

Это очень хорошо.

То есть мы можем сделать **единый постоянный конвейер**, не создавая новую архитектуру очередей.

```text
                 NEW PHOTO
                     │
                     ▼
                  INGEST
                     │
                     ▼
                  photos
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   dino=pending  qwen=pending  preview=pending
        │
        ▼
      DINO
        │
        ▼
     HYBRID
        │
        ▼
   sort_status
        │
        ▼
     address
```

Qwen при этом может работать независимо.

---

## Но прежде чем мигрировать 526 файлов

Нужно узнать **как сейчас физически расположены эти 526 файлов и какие даты у них есть**.

Потому что нам надо определить:

> откуда взять дату для старых фотографий.

Сейчас `created_at`:

```text
2026-08-18 21:22:57
```

— это явно **время внесения в БД**, а не обязательно время съёмки.

Поэтому следующим шагом я бы проверил EXIF и файловые даты **на нескольких существующих фотографиях**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

python - <<'PY'
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS

p = Path("data/input/daily")

files = sorted(
    x for x in p.iterdir()
    if x.is_file()
    and x.suffix.lower() in {".jpg", ".jpeg", ".png"}
)[:10]

for f in files:
    print()
    print("=" * 80)
    print("FILE:", f.name)
    print("MTIME:", f.stat().st_mtime)

    try:
        img = Image.open(f)
        exif = img.getexif()

        for key, value in exif.items():
            name = TAGS.get(key, key)

            if name in {
                "DateTime",
                "DateTimeOriginal",
                "DateTimeDigitized",
            }:
                print(name, "=", value)

    except Exception as e:
        print("EXIF ERROR:", e)
PY
```

**Пока ничего не переносим и ничего не меняем.**

После этого станет понятно, можно ли для старых 526 фотографий автоматически построить:

```text
месяц → день → фото
```

и тогда уже сделаем аккуратный `catalog_migration`, а не очередную временную `daily`-схему.

---

### 👤 **User** — 2026-08-19 00:03:17

базу можно пересчитать

---

### 🤖 **Assistant** — 2026-08-19 00:03:18

Да. И в нашем случае **лучше именно пересчитать/нормализовать базу**, а не пытаться подстраивать новую архитектуру под нынешний `daily`.

Я бы зафиксировал такую модель.

### 1. Файловая структура

Не:

```text
data/input/daily/
    фото...
```

а постоянный каталог:

```text
data/photos/
├── 2026-08/
│   ├── 01/
│   │   ├── фото1.JPG
│   │   ├── фото2.JPG
│   │   └── фото3.JPG
│   ├── 02/
│   │   ├── фото1.JPG
│   │   └── ...
│   ├── 18/
│   │   ├── фото1.JPG
│   │   └── ...
│   └── ...
├── 2026-09/
│   └── ...
└── ...
```

То есть **месяц → день → фотографии**.

При этом исходное имя файла сохраняется.

---

### 2. PostgreSQL становится главным реестром

`photos` — это не база конкретного запуска, а **постоянный каталог всех фотографий**.

Одна фотография = одна запись.

Например:

```text
photo_id       PH_00000526
source_path    /data/photos/2026-08/18/Шолохова 127 А (9).JPG
filename       Шолохова 127 А (9).JPG
created_at     2026-08-18 ...
```

А дальше уже постепенно заполняются:

```text
dino_status
dino_fingerprint
dino_score
hybrid_final_id
sort_status
preview_status
qwen_status
client
brand
...
```

То есть база хранит **историю обработки фотографии**, а не только результат последнего запуска.

---

### 3. При поступлении новых фотографий

Процесс должен быть таким:

```text
Новая папка/файлы
        ↓
INGEST
        ↓
проверка source_path / photo_id
        ↓
уже есть в БД?
    ↙           ↘
  ДА             НЕТ
  ↓               ↓
пропустить      добавить
                  ↓
             dino_status=pending
             qwen_status=pending
             sort_status=pending
             preview_status=pending
                  ↓
             обработка
```

Это очень важно:

**каждый следующий запуск не должен повторно прогонять всю фотобазу.**

Он сначала спрашивает:

> «Какие фотографии появились после последнего сканирования и отсутствуют в `photos`?»

И только их ставит в очередь.

---

### 4. DINO / сортировка тоже должны стать инкрементальными

Сейчас у нас логика фактически завязана на:

```text
daily → запуск → output/daily/TIMESTAMP
```

Это надо убрать из основной архитектуры.

Вместо этого:

```text
Новая фотография
       ↓
DINO
       ↓
первичный кандидат
       ↓
соседние фотографии / Hybrid
       ↓
финальный address / hybrid_final_id
       ↓
запись результата в photos
```

При этом **соседняя фотография может быть старой**.

Это как раз соответствует тому, что мы обсуждали раньше: сортировка смотрит не только на текущий снимок, но и на соседей/последовательность.

---

### 5. `output` тогда тоже меняем

Я бы не делал:

```text
output/daily/
    20260818_230042/
    20260819_...
```

как основное хранилище.

Лучше:

```text
data/
├── photos/
│   └── 2026-08/
│       └── 18/
│
├── output/
│   ├── previews/
│   ├── fingerprints/
│   ├── reports/
│   ├── qwen/
│   └── runs/
│
└── metadata/
```

`runs/` можно оставить для технических логов конкретного запуска, но **истиной является PostgreSQL + постоянный каталог фотографий**.

---

### 6. Грид

Здесь вообще становится гораздо проще.

Грид **не ищет фотографии в `output/daily`**.

Он делает запрос в PostgreSQL:

```text
photos
WHERE ...
ORDER BY ...
```

и получает:

```text
photo_id
path
preview_path
address
client
brand
...
```

То есть пользователь открывает фотобазу и видит **всю накопленную историю**:

```text
2026-08
  18 августа
    [фото] [фото] [фото] ...

  17 августа
    [фото] [фото] ...

  16 августа
    ...
```

Фильтры клиента, адреса, даты и т.д. работают уже по БД.

---

## И самое главное — существующую БД действительно можно пересчитать

Я бы **не удалял текущую `photos`**.

Сначала делаем миграцию:

```text
текущая photos
       ↓
нормализация
       ↓
постоянный каталог
       ↓
обновление source_path
       ↓
проверка уникальности
       ↓
сохранение всех результатов DINO / Hybrid / Qwen
```

Текущие 526 записей при этом не пропадут.

Например эта:

```text
PH_00000526
Шолохова 127 А (9).JPG
```

получит постоянный путь вроде:

```text
data/photos/2026-08/18/Шолохова 127 А (9).JPG
```

а все уже рассчитанные:

```text
dino_*
hybrid_*
qwen_*
sort_*
preview_*
```

останутся в записи.

---

### Но перед миграцией я бы сделал одну вещь

**Не писать код сразу.**

Сначала нужно посмотреть, как именно сейчас создаются записи в `photos`, потому что у нас уже есть:

```text
source_path
source_id
photo_id
filename
original_filename
created_at
updated_at
```

и есть `scripts/photo_ingest.py`.

Нам нужно определить **какое поле будет постоянным идентификатором фотографии** и откуда брать дату для каталога.

После этого можно сделать отдельный:

```text
scripts/migrate_photo_catalog.py
```

который в безопасном режиме сначала покажет:

```text
526 существующих фото
→ 526 новых постоянных путей
→ 0 дублей
→ 0 потерянных записей
```

и только потом физически перенесёт файлы.

**То есть да — базу можно и, на мой взгляд, сейчас как раз стоит пересчитать. Это хороший момент: пока UI и автоматика ещё перестраиваются, сразу отделить постоянную фотобазу от старого понятия `daily`.**

---

### 👤 **User** — 2026-08-19 00:03:31

да

---

### 🤖 **Assistant** — 2026-08-19 00:03:32

Да. Тогда идём **поэтапно и без риска сломать уже работающую распознавалку**.

### Шаг 1 — пока ничего не переносим

Сначала выясним, как именно сейчас `photo_ingest.py` создаёт записи в `photos`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,360p' scripts/photo_ingest.py
```

И ещё:

```bash
grep -RniE \
'INSERT INTO photos|ON CONFLICT|source_path|photo_id|original_filename|created_at' \
scripts/photo_ingest.py app \
--include="*.py" | head -200
```

### Что мы после этого зафиксируем

Будет новая схема:

```text
ВХОДЯЩИЕ ФОТО
      ↓
INGEST
      ↓
есть source_path / photo_id в БД?
      ├── да → пропустить
      └── нет
           ↓
      определить дату
           ↓
      2026-08/18/
           ↓
      добавить запись в photos
           ↓
      DINO pending
      SORT pending
      PREVIEW pending
      QWEN pending
```

А старые 526 фотографий **не будем повторно распознавать** — их существующие результаты останутся.

После того как посмотрим `photo_ingest.py`, я дам **точную миграцию текущих данных**, а не будем сейчас наугад менять `source_path` или структуру БД.

---

### 👤 **User** — 2026-08-19 00:03:54

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '1,360p' scripts/photo_ingest.py
#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg2

PROJECT = Path(__file__).resolve().parent.parent

DB_CONFIG = {
    "host": os.getenv("PHOTOBASE_HOST", "localhost"),
    "port": int(os.getenv("PHOTOBASE_PORT", "5432")),
    "dbname": os.getenv("PHOTOBASE_DB", "photobase"),
    "user": os.getenv("PHOTOBASE_USER", "lora"),
    "password": os.getenv("PHOTOBASE_PASSWORD", ""),
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

# ============================================================
# ID
# ============================================================

def get_next_photo_number(conn):
    """
    Следующий постоянный PHOTO_ID.

    PH_00000001
    PH_00000002
    ...
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT photo_id
            FROM photos
            WHERE photo_id LIKE 'PH_%'
            """
        )

        rows = cur.fetchall()

    max_number = 0

    for (photo_id,) in rows:

        if not photo_id:
            continue

        value = str(photo_id)

        if not value.startswith("PH_"):
            continue

        try:
            number = int(
                value[3:]
            )
        except ValueError:
            continue

        max_number = max(
            max_number,
            number,
        )

    return max_number + 1

def get_next_initial_number(conn):
    """
    Следующий внутренний INITIAL_ID.

    IN_00000001
    IN_00000002
    ...

    INITIAL_ID не зависит от адреса,
    DINO и Qwen.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT initial_id
            FROM photos
            WHERE initial_id LIKE 'IN_%'
            """
        )

        rows = cur.fetchall()

    max_number = 0

    for (initial_id,) in rows:

        if not initial_id:
            continue

        value = str(initial_id)

        if not value.startswith("IN_"):
            continue

        try:
            number = int(
                value[3:]
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

def make_initial_id(number):
    return f"IN_{number:08d}"

# ============================================================
# PATHS
# ============================================================

def normalize_path(path):
    return str(
        Path(path)
        .expanduser()
        .resolve()
    )

def get_existing_source_paths(conn):
    """
    Уже зарегистрированные source_path.

    Используется для безопасного продолжения
    после прерывания ingest.
    """

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT source_path
            FROM photos
            WHERE source_path IS NOT NULL
              AND source_path <> ''
            """
        )

        return {
            normalize_path(row[0])
            for row in cur.fetchall()
            if row[0]
        }

def find_images(input_dir):
    """
    Сканирует только файлы непосредственно
    во входной папке.

    Подкаталоги пока не трогаем.
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

# ============================================================
# REGISTER
# ============================================================

def register_photo(
    conn,
    photo_id,
    initial_id,
    source_path,
):
    """
    Создаёт единую первичную запись фотографии.

    На этом этапе НЕ происходит:

        - DINO
        - Qwen
        - сортировка
        - определение адреса
        - создание превью

    Здесь только создаётся объект PHOTО.
    """

    source = Path(source_path)

    filename = source.name

    with conn.cursor() as cur:

        cur.execute(
            """
            INSERT INTO photos (
                photo_id,
                initial_id,

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
                %s,

                'pending',

                'pending',
                'pending',
                'pending',
                'pending'
            )
            """,
            (
                photo_id,
                initial_id,

                source_path,
                source_path,

                filename,
                filename,
            ),
        )

# ============================================================
# INGEST
# ============================================================

def ingest(input_dir):

    input_dir = (
        input_dir
        .expanduser()
        .resolve()
    )

    if not input_dir.exists():

        raise RuntimeError(
            "Input directory does not exist:\n"
            f"{input_dir}"
        )

    if not input_dir.is_dir():

        raise RuntimeError(
            "Input path is not a directory:\n"
            f"{input_dir}"
        )

    images = find_images(
        input_dir
    )

    print("=" * 80)
    print("PHOTO INGEST")
    print("=" * 80)
    print()
    print("INPUT :", input_dir)
    print("FILES :", len(images))
    print()

    if not images:

        print(
            "No images found."
        )

        return

    with psycopg2.connect(
        **DB_CONFIG
    ) as conn:

        # ----------------------------------------------------
        # Existing
        # ----------------------------------------------------

        existing_paths = (
            get_existing_source_paths(
                conn
            )
        )

        # ----------------------------------------------------
        # Next IDs
        # ----------------------------------------------------

        next_photo_number = (
            get_next_photo_number(
                conn
            )
        )

        next_initial_number = (
            get_next_initial_number(
                conn
            )
        )

        registered = 0
        skipped = 0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ grep -RniE \
'INSERT INTO photos|ON CONFLICT|source_path|photo_id|original_filename|created_at' \
scripts/photo_ingest.py app \
--include="*.py" | head -200
scripts/photo_ingest.py:38:    Следующий постоянный PHOTO_ID.
scripts/photo_ingest.py:49:            SELECT photo_id
scripts/photo_ingest.py:51:            WHERE photo_id LIKE 'PH_%'
scripts/photo_ingest.py:59:    for (photo_id,) in rows:
scripts/photo_ingest.py:61:        if not photo_id:
scripts/photo_ingest.py:64:        value = str(photo_id)
scripts/photo_ingest.py:135:def make_photo_id(number):
scripts/photo_ingest.py:155:def get_existing_source_paths(conn):
scripts/photo_ingest.py:157:    Уже зарегистрированные source_path.
scripts/photo_ingest.py:167:            SELECT source_path
scripts/photo_ingest.py:169:            WHERE source_path IS NOT NULL
scripts/photo_ingest.py:170:              AND source_path <> ''
scripts/photo_ingest.py:209:    photo_id,
scripts/photo_ingest.py:211:    source_path,
scripts/photo_ingest.py:227:    source = Path(source_path)
scripts/photo_ingest.py:235:            INSERT INTO photos (
scripts/photo_ingest.py:236:                photo_id,
scripts/photo_ingest.py:239:                source_path,
scripts/photo_ingest.py:243:                original_filename,
scripts/photo_ingest.py:271:                photo_id,
scripts/photo_ingest.py:274:                source_path,
scripts/photo_ingest.py:275:                source_path,
scripts/photo_ingest.py:338:            get_existing_source_paths(
scripts/photo_ingest.py:368:            source_path = (
scripts/photo_ingest.py:378:            if source_path in existing_paths:
scripts/photo_ingest.py:393:            photo_id = make_photo_id(
scripts/photo_ingest.py:407:                photo_id,
scripts/photo_ingest.py:409:                source_path,
scripts/photo_ingest.py:413:                source_path
scripts/photo_ingest.py:418:                f"{photo_id}"
scripts/photo_ingest.py:485:            "assign photo_id and initial_id, "
app/web/photo_db.py:23:            source_path,
app/web/photo_db.py:24:            original_filename,
app/web/users_db.py:35:                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
app/pipeline/controller.py:40:            ON CONFLICT (id) DO NOTHING
app/pipeline/queue.py:64:                    created_at TEXT NOT NULL,
app/pipeline/queue.py:87:        created_at = self._now()
app/pipeline/queue.py:98:                    created_at
app/pipeline/queue.py:106:                    created_at,
app/workers/qwen_worker.py:162:        photo_id -> результат Qwen
app/workers/qwen_worker.py:173:                photo_id,
app/workers/qwen_worker.py:174:                source_path,
app/workers/qwen_worker.py:178:              AND source_path IS NOT NULL
app/workers/qwen_worker.py:179:              AND source_path <> ''
app/workers/qwen_worker.py:220:    photo_id остаётся постоянным идентификатором
app/workers/qwen_worker.py:555:        "[QWEN] Source: photos.source_path"
app/workers/qwen_worker.py:558:        "[QWEN] Identity: photos.photo_id"
app/workers/qwen_worker.py:621:            photo_id = row["photo_id"]
app/workers/qwen_worker.py:622:            source_path = Path(
app/workers/qwen_worker.py:623:                row["source_path"]
app/workers/qwen_worker.py:628:                f"[QWEN] {photo_id}"
app/workers/qwen_worker.py:632:                source_path,
app/workers/qwen_worker.py:639:                if not source_path.exists():
app/workers/qwen_worker.py:642:                        f"{source_path}"
app/workers/qwen_worker.py:645:                if not source_path.is_file():
app/workers/qwen_worker.py:648:                        f"{source_path}"
app/workers/qwen_worker.py:652:                    source_path
app/workers/qwen_worker.py:669:                    photo_id,
app/workers/qwen_worker.py:714:                    photo_id,
app/workers/dino_worker.py:74:    что у неё уже существует photo_id и
app/workers/dino_worker.py:86:                photo_id,
app/workers/dino_worker.py:88:                source_path,
app/workers/dino_worker.py:93:                AND source_path IS NOT NULL
app/workers/dino_worker.py:94:                AND source_path <> ''
app/workers/dino_worker.py:142:    photo_id остаётся независимым идентификатором фотографии.
app/workers/dino_worker.py:314:            photo_id = row["photo_id"]
app/workers/dino_worker.py:316:            source_path = Path(
app/workers/dino_worker.py:317:                row["source_path"]
app/workers/dino_worker.py:325:                photo_id,
app/workers/dino_worker.py:329:                source_path.name,
app/workers/dino_worker.py:340:                if not source_path.exists():
app/workers/dino_worker.py:342:                        f"Photo not found: {source_path}"
app/workers/dino_worker.py:345:                if not source_path.is_file():
app/workers/dino_worker.py:347:                        f"Not a file: {source_path}"
app/workers/dino_worker.py:351:                    source_path,
app/workers/dino_worker.py:378:                    f"{photo_id}"
app/workers/dino_worker.py:402:                    f"{photo_id}: {exc}"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 00:03:55

Да, теперь картина достаточно ясная. И есть важный момент: **текущий `photo_ingest.py` уже почти готов к нужной архитектуре**.

Сейчас он делает правильную вещь:

- `photo_id = PH_...` - постоянный ID;
- `initial_id = IN_...` - тоже независимый ID;
- проверяет уже зарегистрированный `source_path`;
- новые фото получают `pending`;
- DINO/Qwen/сортировка/preview запускаются отдельно;
- воркеры работают непосредственно с `photos`.

То есть **ядро БД менять радикально не нужно**.

### Что меняем

Сейчас:

```text
data/input/daily/
    Шолохова 127 А (9).JPG
```

и в БД:

```text
source_path =
/.../data/input/daily/Шолохова 127 А (9).JPG
```

Это и есть главная проблема.

Делаем постоянный каталог:

```text
data/photos/
└── 2026-08/
    ├── 18/
    │   ├── Шолохова 127 А (1).JPG
    │   ├── Шолохова 127 А (2).JPG
    │   └── ...
    └── 19/
        └── ...
```

А в БД:

```text
photo_id       PH_00000526
source_path    .../data/photos/2026-08/18/Шолохова 127 А (9).JPG
filename       Шолохова 127 А (9).JPG
original_filename
```

Все результаты:

```text
dino_*
hybrid_*
qwen_*
sort_*
preview_*
```

остаются на месте.

---

## И ещё важнее

**Не надо определять "новое фото" по имени файла.**

Уже есть:

```text
UNIQUE (source_path)
```

Но после переноса постоянный `source_path` изменится.

Поэтому я предлагаю добавить ещё один постоянный признак происхождения файла - например `source_hash` (SHA-256).

Тогда получится:

```text
photo_id       → кто это в нашей БД
source_hash    → какой это физический файл
source_path    → где он сейчас лежит
```

И если через месяц снова попадётся:

```text
Шолохова 127 А (9).JPG
```

с тем же содержимым, мы его узнаем **даже если он пришёл из другой входной папки или был переименован**.

Это гораздо надёжнее.

---

# Поэтому следующий шаг

Пока **ничего не переносим**.

Сначала посмотрим оставшуюся часть `photo_ingest.py`, потому что там как раз находится цикл регистрации и мы должны аккуратно переделать его под постоянный каталог.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

sed -n '330,520p' scripts/photo_ingest.py
```

После этого я предложу конкретно:

1. новую структуру `data/photos/YYYY-MM/DD`;
2. `source_hash`;
3. миграцию нынешних **526 фото**;
4. новый `photo_ingest`;
5. как изменить `photo_processing`, чтобы он больше не был `DAILY`;
6. как сделать автоматический поиск **только новых фото**;
7. как сохранить существующие результаты DINO/Hybrid/Qwen без повторного расчёта.

И уже после этого можно будет менять автоматику.

---

### 👤 **User** — 2026-08-19 00:04:42

app/workers/dino_worker.py:402:                    f"{photo_id}: {exc}"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

sed -n '330,520p' scripts/photo_ingest.py
        **DB_CONFIG
    ) as conn:

        # ----------------------------------------------------
        # Existing
        # ----------------------------------------------------

        existing_paths = (
            get_existing_source_paths(
                conn
            )
        )

        # ----------------------------------------------------
        # Next IDs
        # ----------------------------------------------------

        next_photo_number = (
            get_next_photo_number(
                conn
            )
        )

        next_initial_number = (
            get_next_initial_number(
                conn
            )
        )

        registered = 0
        skipped = 0

        # ----------------------------------------------------
        # REGISTER
        # ----------------------------------------------------

        for image in images:

            source_path = (
                normalize_path(
                    image
                )
            )

            # -----------------------------------------------
            # Already registered
            # -----------------------------------------------

            if source_path in existing_paths:

                print(
                    f"[SKIP]      {image.name}"
                    " — already registered"
                )

                skipped += 1

                continue

            # -----------------------------------------------
            # Create IDs
            # -----------------------------------------------

            photo_id = make_photo_id(
                next_photo_number
            )

            initial_id = make_initial_id(
                next_initial_number
            )

            # -----------------------------------------------
            # DB record
            # -----------------------------------------------

            register_photo(
                conn,
                photo_id,
                initial_id,
                source_path,
            )

            existing_paths.add(
                source_path
            )

            print(
                f"[REGISTER] "
                f"{photo_id}"
                f" | initial={initial_id}"
                f" | {image.name}"
            )

            registered += 1

            next_photo_number += 1
            next_initial_number += 1

        conn.commit()

    # ========================================================
    # REPORT
    # ========================================================

    print()
    print("=" * 80)
    print("INGEST FINISHED")
    print("=" * 80)
    print()

    print(
        "Found      :",
        len(images),
    )

    print(
        "Registered :",
        registered,
    )

    print(
        "Skipped    :",
        skipped,
    )

    print()

    print(
        "New photos are now available to:"
    )

    print(
        "  DINO : dino_status = pending"
    )

    print(
        "  QWEN : qwen_status = pending"
    )

    print()

    print(
        "No address has been assigned yet."
    )

# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Register new photos, "
            "assign photo_id and initial_id, "
            "and put them into independent "
            "DINO/Qwen queues."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help=(
            "Directory with incoming photos"
        ),
    )

    args = parser.parse_args()

    ingest(
        args.input
    )

if __name__ == "__main__":
    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 00:04:43

Отлично. Теперь уже видно всю цепочку. **Я бы сейчас не переписывал `photo_ingest.py` вслепую.** Сначала фиксируем архитектуру, а потом делаем одну миграцию.

### Что у нас уже хорошо

Текущий ingest:

```text
входная папка
    ↓
проверка source_path
    ↓
новая фотография?
    ↓
PH_xxxxxxxx
IN_xxxxxxxx
    ↓
photos
    ↓
DINO/Qwen pending
```

Это оставляем.

Меняем только понятие **входа и постоянного хранения**.

---

# Новая архитектура

Я предлагаю разделить три понятия.

### 1. Входящий буфер

Например:

```text
data/input/
```

Туда можно складывать новые фотографии.

Неважно, как они туда попали:

```text
data/input/
    batch_001/
    batch_002/
    camera/
    импорт/
```

или вообще одна папка.

---

### 2. Постоянный каталог

После ingest:

```text
data/photos/
    2026-08/
        18/
            PH_00000501.JPG
            PH_00000502.JPG
            ...
        19/
            ...
```

Но здесь я бы **не использовал оригинальное имя как единственный идентификатор файла**.

Лучше:

```text
PH_00000526.JPG
```

а в БД:

```text
photo_id       PH_00000526
original_filename  Шолохова 127 А (9).JPG
```

Почему это удобно:

- имя никогда не конфликтует;
- переименование оригинала не ломает систему;
- физический файл однозначно связан с `photo_id`;
- гриду вообще не нужно знать исходное имя для идентификации.

При этом **оригинальное имя сохраняется полностью**.

---

### 3. PostgreSQL

`photos` остаётся главным источником истины.

Например:

```text
PH_00000526
│
├── source_path
├── original_filename
├── created_at
│
├── dino_status
├── dino_fingerprint
├── dino_score
│
├── hybrid_original_id
├── hybrid_final_id
├── hybrid_neighbors
│
├── sort_status
│
├── preview_status
├── preview_path
│
├── qwen_status
├── client
├── brand
├── text_json
└── ...
```

---

# Дата

Здесь есть один важный вопрос архитектуры.

Для каталога:

```text
2026-08/18/
```

нам нужно определить **дату фотографии**, а не дату её загрузки в БД.

Я бы добавил:

```text
photo_taken_at
```

и:

```text
photo_date
```

или вообще достаточно `photo_taken_at`.

При ingest:

1. пытаемся взять EXIF DateTimeOriginal;
2. если EXIF отсутствует — берём дату файла;
3. если и она ненадёжна — дату ingest.

Тогда каталог строится именно по дате фотографии.

---

# Новое фото определяется не запуском

Вот это самое главное.

Допустим, сегодня в базе:

```text
PH_00000001 ... PH_00000526
```

Приходит ещё 100 фотографий.

Ingest:

```text
526 уже существуют
100 новых
```

Результат:

```text
526 → SKIP
100 → REGISTER
```

И только эти 100 получают:

```text
dino_status = pending
sort_status = pending
preview_status = pending
qwen_status = pending
```

Старые фотографии **вообще не трогаются**.

---

# А потом автоматическая обработка

Получится:

```text
                ФОТОБАЗА
                    │
                    ▼
               PostgreSQL
                    │
             новые pending
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
      DINO        Preview       Qwen
       │
       ▼
  первичный ID
       │
       ▼
 Hybrid / соседи
       │
       ▼
 final ID / address
       │
       ▼
 PostgreSQL
```

Причём Hybrid сможет смотреть **на уже существующие фотографии**.

Это особенно важно для нашей логики соседних кадров.

---

# Что делать с нынешними 526

И вот здесь я предлагаю **не запускать DINO заново**.

Берём существующие записи.

Например:

```text
PH_00000526
```

у неё уже есть:

```text
dino_status
dino_fingerprint
dino_score
hybrid_final_id
...
```

Мы просто физически перемещаем файл:

```text
data/input/daily/Шолохова 127 А (9).JPG
```

например в:

```text
data/photos/2026-08/18/PH_00000526.JPG
```

и обновляем:

```text
source_path
path
```

**Все остальные поля остаются нетронутыми.**

---

## Но есть ещё одна важная вещь

В текущей БД:

```text
photos_pkey PRIMARY KEY (photo_id)
photos_id_key UNIQUE (id)
ux_photos_source_path UNIQUE (source_path)
```

Это хорошо.

Но перед миграцией я хочу проверить **реальные значения `created_at`, `source_path`, `original_filename` и EXIF-даты**, потому что именно от этого зависит, как правильно разложить эти 526 файлов по:

```text
2026-08/18/
2026-08/17/
...
```

Поэтому следующий шаг — **только диагностика, ничего не меняет**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

psql -h localhost -U lora -d photobase -c "
SELECT
    COUNT(*) AS total,
    MIN(created_at) AS first_created,
    MAX(created_at) AS last_created,
    COUNT(*) FILTER (
        WHERE original_filename IS NULL
           OR original_filename = ''
    ) AS no_original_name,
    COUNT(*) FILTER (
        WHERE source_path LIKE '%/data/input/daily/%'
    ) AS from_daily
FROM photos;
"
```

И затем:

```bash
psql -h localhost -U lora -d photobase -c "
SELECT
    photo_id,
    original_filename,
    source_path,
    created_at,
    updated_at
FROM photos
ORDER BY id DESC
LIMIT 20;
"
```

**После этого уже можно безопасно написать мигратор именно под наши реальные 526 записей.**

---

### 👤 **User** — 2026-08-19 00:06:09

пока не трогаем инпут, просто имеем ввидку, что внутрие него могут быть вложенные папки, которые обновляются

---

### 🤖 **Assistant** — 2026-08-19 00:06:09

Да, именно так. **`data/input` пока вообще не трогаем и не переносим.** Фиксируем это как архитектурное требование.

### Что считаем входом

```text
data/input/
├── папка_1/
│   ├── фото...
│   └── ...
├── папка_2/
│   ├── фото...
│   └── ...
└── папка_3/
    └── ...
```

Папки внутри `input` могут:

- появляться;
- исчезать;
- обновляться;
- содержать новые фотографии;
- содержать уже обработанные фотографии.

Ingest должен **рекурсивно сканировать `data/input`**.

---

### Главное правило

`input` — это **источник**, а не фотобаза.

Мы не должны ориентироваться на:

```text
daily
batch_001
какая-то папка
```

как на сущность обработки.

Вместо этого:

```text
data/input/
       ↓
рекурсивный сканер
       ↓
найдены файлы
       ↓
сопоставление с PostgreSQL
       ↓
только новые
       ↓
регистрация в photos
       ↓
очередь обработки
```

---

### И при этом физически входные файлы пока остаются на месте

То есть:

```text
data/input/
    источник_А/
       IMG001.JPG
       IMG002.JPG

    источник_Б/
       IMG003.JPG
```

не переносим и не переименовываем.

Это особенно удобно сейчас: мы сначала отладим **учёт и инкрементальную обработку**, а вопрос постоянного каталога решим следующим этапом.

---

### Для базы

Будем считать:

```text
source_path
```

— **путём к исходному файлу**, который сейчас находится внутри `data/input`.

А постоянный каталог `data/photos/YYYY-MM/DD` пока проектируем отдельно.

То есть сейчас не ломаем существующую связку:

```text
photos.source_path
        ↓
dino_worker
        ↓
qwen_worker
        ↓
грид
```

---

И я бы сейчас сделал именно так:

**Этап A — безопасный:**

```text
input/
  └── любые вложенные папки
          ↓
       recursive ingest
          ↓
       PostgreSQL
          ↓
       только новые фото
```

**Этап B — потом:**

```text
новые записи
     ↓
дата
     ↓
data/photos/YYYY-MM/DD/
```

**Этап C — потом:**

грид работает исключительно через БД и постоянный каталог.

Это позволит нам сейчас не затронуть рабочую часть проекта и постепенно перейти от `daily` к настоящей накопительной фотобазе.

---

### 👤 **User** — 2026-08-19 00:06:35

ок

---

### 🤖 **Assistant** — 2026-08-19 00:06:36

Ок. **Инпут пока не меняем.** Но архитектурно фиксируем это как требование:

- `data/input/...` — входное хранилище фотографий.
- Внутри него в будущем могут быть **вложенные папки**.
- Структура может быть, например:
  ```text
  input/
    2026-08/
      01/
        фото1.jpg
        фото2.jpg
      02/
        фото1.jpg
    2026-09/
      01/
        ...
  ```
- Папки будут **постепенно обновляться**, поэтому система не должна считать, что папка обработана целиком.
- **База PostgreSQL — источник истины**: в ней находится запись о каждой поступившей фотографии и состояния её обработки.
- При следующем запуске нужно искать **только новые фотографии**, уже зарегистрированные `source_path` пропускать.
- Обработанные ранее DINO/Qwen повторно не запускаются, если их соответствующие статусы уже `done`.
- Грид получает фотографии **из БД**, а не сканирует input напрямую.
- `output/daily` как концепцию постепенно убираем: результат обработки должен быть частью общего каталога/метаданных, а не отдельного «дневного запуска».
- При этом **физическое расположение исходных фото в input сохраняется** — пока ничего не переносим.

И ещё важный момент из текущего `photo_ingest.py`: сейчас поиск идёт только через `input_dir.iterdir()`, то есть **только первый уровень**. Это пока оставляем как есть. Когда дойдём до изменения ingest, заменим на рекурсивный поиск, но сделаем это отдельно, чтобы сейчас не сломать работающий контур.

Следующий логичный шаг — **разобрать текущую связку `ingest → DINO worker → sort → preview → Qwen` и определить, что именно должно стать постоянным каталогом**, прежде чем что-либо переписывать.

---

### 👤 **User** — 2026-08-19 00:07:04

да

---

### 🤖 **Assistant** — 2026-08-19 00:07:06

Да. Тогда **сейчас ничего не переписываем**, а сначала фиксируем фактическую архитектуру текущего контура.

Наша целевая схема должна получиться примерно такой:

```text
                    INPUT
                      │
                      ▼
               ┌─────────────┐
               │    INGEST   │
               │ поиск новых │
               │   файлов    │
               └──────┬──────┘
                      │
                      ▼
                PostgreSQL
                ┌───────────┐
                │  photos   │
                │           │
                │ photo_id  │
                │ source    │
                │ statuses  │
                │ results   │
                └─────┬─────┘
                      │
          ┌───────────┼────────────┐
          ▼           ▼            ▼
        DINO         SORT         QWEN
          │           │            │
          └───────────┼────────────┘
                      ▼
                 PostgreSQL
                      │
                      ▼
                    GRID
```

Причём **DINO, сортировка, preview и Qwen должны работать не как "запуск дня", а как обработчики очереди фотографий**.

### Сейчас нужно посмотреть 4 вещи

Выполни одним блоком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "===== CONTROLLER ====="
cat app/pipeline/controller.py

echo
echo "===== DINO WORKER ====="
sed -n '1,460p' app/workers/dino_worker.py

echo
echo "===== PHOTO INGEST ====="
cat scripts/photo_ingest.py

echo
echo "===== SORT STATUS REFERENCES ====="
grep -RniE \
'sort_status|hybrid_final_id|hybrid_original_id|hybrid_score|hybrid_margin|hybrid_neighbors' \
app scripts \
--include="*.py" | head -250

echo
echo "===== PREVIEW REFERENCES ====="
grep -RniE \
'preview_status|preview_path|create_previews|preview' \
app scripts \
--include="*.py" | head -250
```

После этого мы сможем точно разделить:

### 1. Постоянный каталог

Это PostgreSQL:

```text
photos
 ├── photo_id
 ├── source_path
 ├── filename
 ├── created_at
 │
 ├── DINO
 ├── SORT/HYBRID
 ├── PREVIEW
 └── QWEN
```

### 2. Физический каталог

Он может жить годами:

```text
input/
├── 2026-08/
│   ├── 01/
│   │   ├── IMG001.JPG
│   │   ├── IMG002.JPG
│   │   └── ...
│   ├── 02/
│   └── ...
├── 2026-09/
│   ├── 01/
│   └── ...
└── ...
```

И **новый запуск не означает новый каталог обработки**.

Например, 19 августа добавили:

```text
input/2026-08/19/001.JPG
input/2026-08/19/002.JPG
```

система делает:

```text
INGEST
  ↓
нашёл 2 новых source_path
  ↓
добавил PH_00000527
добавил PH_00000528
  ↓
DINO → только эти 2
  ↓
SORT → только эти 2
  ↓
PREVIEW → только эти 2
  ↓
QWEN → только эти 2
```

А 526 старых фотографий **вообще не трогает**.

При этом если какой-то старый снимок был:

```text
dino_status = done
qwen_status = done
sort_status = done
preview_status = done
```

он просто остаётся в каталоге и доступен гриду.

Именно поэтому сейчас важно посмотреть **controller + workers + sort/preview**: скорее всего часть этой архитектуры у нас уже есть, и лучше её **собрать в единый постоянный pipeline**, а не переписывать заново.

---

