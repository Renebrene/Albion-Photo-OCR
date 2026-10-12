## СЕССИЯ: вторник

**Создано:** 2026-08-18 18:12:03
**Обновлено:** 2026-08-22 20:16:20
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a8475d2-5b18-83ea-868a-8e504f83aec1)

---

### 👤 **User** — 2026-08-18 20:11:35

SUMMARY OF LESS COMMANDS

      Commands marked with * may be preceded by a number, N.
      Notes in parentheses indicate the behavior if N is given.
      A key preceded by a caret indicates the Ctrl key; thus ^K is ctrl-K.

  h  H                 Display this help.
  q  :q  Q  :Q  ZZ     Exit.
 ---------------------------------------------------------------------------

                           MOVING

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
R: No such file or directory  (press RETURN)

---

### 🤖 **Assistant** — 2026-08-18 20:11:35

Да, это просто `less` открыл длинный вывод, а ты попал в его справку. Ничего не сломалось.

Сейчас нажми:

```text
q
```

Если после этого вернёшься в терминал, выполни **эту более удобную команду**, она не открывает `less`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT column_name, data_type
 FROM information_schema.columns
 WHERE table_name = 'photos'
 ORDER BY ordinal_position;" \
| cat
```

`| cat` здесь нужен именно для того, чтобы `psql` не передавал длинный вывод в `less`.

Пришли весь вывод.

---

### 👤 **User** — 2026-08-18 20:11:57

alexice@NEURO:~$ cd ~/projects/scene_fingerprint_mvp_v02 && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT column_name, data_type
 FROM information_schema.columns
 WHERE table_name = 'photos'
 ORDER BY ordinal_position;" \
| cat
      column_name      |          data_type          
-----------------------+-----------------------------
 id                    | integer
 address               | text
 filename              | text
 path                  | text
 client                | text
 brand                 | text
 category              | text
 description           | text
 confidence            | integer
 qwen_status           | text
 qwen_time_sec         | double precision
 text_json             | jsonb
 colors_json           | jsonb
 objects_json          | jsonb
 environment_json      | jsonb
 image_quality_json    | jsonb
 camera_view_json      | jsonb
 scene_objects_json    | jsonb
 analysis_quality_json | jsonb
 raw_json              | jsonb
 imported_at           | timestamp without time zone
(21 rows)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:11:59

Отлично. Теперь структура ясна.

В `photos` есть только одна обычная дата:

```text
imported_at | timestamp
```

То есть **реальной даты съёмки отдельным полем нет**. Для первого этапа предлагаю использовать `imported_at` как дату фотографии в интерфейсе — но перед этим быстро проверим, насколько она соответствует нашим месяцам.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT
    MIN(imported_at) AS first_date,
    MAX(imported_at) AS last_date,
    COUNT(*) AS total,
    COUNT(DISTINCT DATE_TRUNC('month', imported_at)) AS months
 FROM photos;" \
| cat
```

И затем:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT
    DATE_TRUNC('month', imported_at) AS month,
    COUNT(*) AS photos
 FROM photos
 GROUP BY 1
 ORDER BY 1 DESC;" \
| cat
```

Это даст нам картину:

```text
2026-08 | ...
2026-07 | ...
2026-06 | ...
```

После этого уже можно делать **первый рабочий патч**.

### Что зафиксируем в коде

Сделаем период не просто косметическим селектом, а настоящим фильтром:

```text
Период: Август 2026
        ↓
фото за август
        ↓
AND выбранные адреса
        ↓
AND выбранные клиенты
        ↓
GRID
```

И первый запуск будет:

```text
Период = текущий месяц
Адреса = все ☑
Клиенты = все
```

Причём выбранный период будем сохранять для следующего запуска.

**Важно:** сейчас не будем менять `PHOTO_INDEX` и физическую структуру файлов. Фильтрация должна происходить по уже существующему `PHOTO_RECORD_INDEX`, чтобы не создавать второй каталог фотографий и не ломать текущий грид.

---

### 👤 **User** — 2026-08-18 20:12:42

(21 rows)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT
    MIN(imported_at) AS first_date,
    MAX(imported_at) AS last_date,
    COUNT(*) AS total,
    COUNT(DISTINCT DATE_TRUNC('month', imported_at)) AS months
 FROM photos;" \
| cat
     first_date      |      last_date      | total | months 
---------------------+---------------------+-------+--------
 2026-08-16 14:29:56 | 2026-08-16 14:29:56 |   100 |      1
(1 row)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:12:45

Вот это важный результат. **`imported_at` нам для периода не подходит.**

Сейчас вся БД выглядит так:

```text
100 фотографий
MIN(imported_at) = 2026-08-16 14:29:56
MAX(imported_at) = 2026-08-16 14:29:56
```

То есть `imported_at` — это фактически **дата импорта в БД**, а не дата фотографии.

Поэтому использовать его для «за месяц» сейчас неправильно.

### Что делаем вместо этого

У нас уже есть файловая структура:

```text
data/output/daily/
    <дата или запуск>/
        78_v33/
        79_v33/
        ...
```

и именно там, судя по текущему коду, находятся фотографии разных запусков/периодов.

Нужно сначала посмотреть, **как реально называются каталоги `daily`**.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "=== DAILY RUNS ===" && \
find data/output/daily -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort && \
echo && \
echo "=== PREVIEW RUNS ===" && \
find data/preview/daily -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort
```

И ещё:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "=== EXAMPLE PHOTOS ===" && \
find data/output/daily -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) \
-printf '%TY-%Tm-%Td %TH:%TM:%TS | %p\n' | sort | head -30
```

### Почему это сейчас правильнее

Нам нужен такой механизм:

```text
                    ┌── период
                    │
                    ▼
ФОТО → дата/запуск → адрес → клиент → GRID
                    ▲
                    │
             единый фильтр
```

А не:

```text
БД imported_at
       ↓
все 100 фотографий
       ↓
один и тот же месяц
```

И ещё один момент: **не будем пока менять БД**, пока не увидим структуру `daily`. Возможно, нужная дата уже есть в имени каталога или в имени файла, и тогда мы вообще сможем сделать период без миграции PostgreSQL.

После этих двух команд уже можно будет точно определить источник периода и писать код.

---

### 👤 **User** — 2026-08-18 20:12:57

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT
    DATE_TRUNC('month', imported_at) AS month,
    COUNT(*) AS photos
 FROM photos
 GROUP BY 1
 ORDER BY 1 DESC;" \
| cat
        month        | photos 
---------------------+--------
 2026-08-01 00:00:00 |    100
(1 row)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:12:58

Да, это подтверждает: **`imported_at` пока вообще нельзя использовать для периода** — все 100 записей импортированы одним моментом.

И это даже хорошо: сейчас не будем привязывать новую архитектуру фильтров к неправильному полю.

Следующий шаг — посмотреть реальные папки `daily`, потому что именно там у нас уже организованы фото по запускам.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "=== DAILY RUNS ===" && \
find data/output/daily -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort && \
echo && \
echo "=== PHOTO DATES / PATHS ===" && \
find data/output/daily -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) \
-printf '%TY-%Tm-%Td %TH:%TM:%TS | %p\n' | sort | head -40
```

**Ничего пока не меняем в коде.**

Нам нужно увидеть, например, что-то вроде:

```text
20260816
20260817
20260818
```

или:

```text
2026-08-16
2026-08-17
...
```

Если дата действительно закодирована в структуре `daily`, тогда период можно сделать правильно и без изменения PostgreSQL:

```text
Период
  ↓
выбираем нужные daily-запуски
  ↓
адреса
  ↓
клиенты
  ↓
грид
```

А если окажется, что `daily` содержит только **последний запуск**, тогда следующим шагом найдём, где хранится история, и уже от неё построим фильтр.

---

### 👤 **User** — 2026-08-18 20:14:00

мы будем использовать данные шинпут - после сортировки и описания квен. в это же время собирать и данные о файлах в базу

---

### 🤖 **Assistant** — 2026-08-18 20:14:00

Да. **Это гораздо правильнее.** Тогда не надо пытаться восстановить дату из `daily` или использовать `imported_at`.

Фиксируем архитектуру:

```text
INPUT
  ↓
сортировка / распознавание
  ↓
фото
  ├── адрес
  ├── имя файла
  ├── дата/время файла
  ├── клиент
  ├── путь
  └── другие метаданные
        ↓
      БД
        ↓
       UI
```

То есть при обработке входящих фотографий мы **сразу создаём полноценную запись фотографии в БД**.

### Что стоит сохранять

Минимально:

```text
id
path
filename
address
client
file_created_at
file_modified_at
imported_at
```

И уже существующие:

```text
brand
category
description
confidence
qwen_status
qwen_time_sec
text_json
colors_json
objects_json
environment_json
...
```

Особенно важны:

**`file_created_at`** — дата создания файла, если она доступна.

**`file_modified_at`** — дата изменения файла.

И желательно ещё:

**`source_path`** — исходный путь из `input`.

**`output_path`** — куда файл был помещён после обработки.

Тогда период в интерфейсе будет настоящим:

```text
Дата фотографии
      ↓
2026-08
      ↓
адреса
      ↓
клиенты
      ↓
фото
```

### И это хорошо ложится на нашу будущую архитектуру

При следующей обработке:

```text
INPUT
 ↓
получили metadata файла
 ↓
DINO → адрес
 ↓
Qwen → описание / объекты / текст / цвета
 ↓
определили клиента
 ↓
одна запись → PostgreSQL
```

А UI уже **не сканирует файловую систему для определения характеристик фотографии**. Он работает с БД.

Это особенно важно для будущего:

- текстовый умный поиск;
- поиск по изображению;
- поиск по видео;
- фильтр периода;
- адреса;
- клиенты;
- подборки;
- комбинация всех фильтров через **И**.

### Поэтому сейчас меняем порядок работ

Не делаем пока фильтр периода на существующих 100 записях.

Сначала добавляем в схему БД метаданные файла и меняем **импорт/обработку фотографий**, чтобы новые фотографии сразу попадали в БД с датой.

После этого:

**Этап 1:** сбор metadata → БД  
**Этап 2:** единый `get_filtered_photos()`  
**Этап 3:** период + адреса + клиенты  
**Этап 4:** новая компоновка `Адреса | Клиенты | Фото`  
**Этап 5:** подборки  
**Этап 6:** сохранение состояния менеджера  
**Этап 7:** авторизация/cookie/цвета  
**Этап 8:** умный поиск.

И ещё я бы **не называл поле просто `date`**. Лучше сразу сделать `file_created_at` и `file_modified_at`, чтобы потом не было путаницы между датой файла, датой импорта и датой анализа.

---

### 👤 **User** — 2026-08-18 20:14:47

может сразу настроить первый этап - параллельной сортирвоки и описания. обновить базы и потом проверять

---

### 🤖 **Assistant** — 2026-08-18 20:14:47

Да. **Именно так и лучше сделать.** Не строить сейчас временный фильтр на старой БД, а сразу изменить производственный pipeline.

### Фиксируем новый первый этап

```text
                    INPUT
                      │
          ┌───────────┴───────────┐
          │                       │
     СОРТИРОВКА               ОПИСАНИЕ QWEN
     DINO/fingerprint         текст/объекты/цвета/...
          │                       │
          └───────────┬───────────┘
                      │
                ОБЩАЯ ЗАПИСЬ
                      │
                      ▼
                PostgreSQL
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
      ФАЙЛОВЫЕ                 WEB UI
      ДАННЫЕ                   ФИЛЬТРЫ
```

Но важная деталь: **параллельно — не обязательно одновременно писать в БД из двух процессов**.

Лучше:

1. Получили фото.
2. Один worker определяет адрес.
3. Другой worker/очередь выполняет Qwen.
4. Собираем результаты.
5. **Одна финальная операция записывает полную запись фото в PostgreSQL.**

Так мы не получим ситуацию:

```text
DINO записал строку
Qwen ещё не закончил
UI увидел полуготовую запись
```

### Что сразу добавляем в БД

Я бы добавил:

```text
file_created_at
file_modified_at
file_size
source_path
output_path
```

И оставил:

```text
imported_at
```

как дату попадания записи в БД.

Получится:

```text
file_created_at   → когда файл создан
file_modified_at  → когда изменён
imported_at       → когда мы его импортировали
```

Это потом даст нормальный периодический фильтр.

### И ещё важнее

При повторной обработке **не должны плодиться дубликаты**.

Нужно определить стабильный ключ фотографии, например:

```text
source_path
```

или, ещё лучше, комбинацию:

```text
source_path + file_size + modified_at
```

А в перспективе можно добавить hash файла.

Тогда pipeline сможет работать так:

```text
новое фото
   ↓
нет в БД → обработать → INSERT

уже есть
   ↓
не изменилось → пропустить

есть, но файл изменился
   ↓
обработать заново → UPDATE
```

Это очень пригодится, когда фотобаза станет большой.

---

## Поэтому сейчас предлагаю не трогать UI

Сначала делаем:

**Pipeline v1 → PostgreSQL**

и прогоняем небольшой тест:

```text
10–20 фотографий
        ↓
сортировка
+
Qwen
        ↓
БД
        ↓
проверка записей
```

Проверяем:

- адрес;
- клиента;
- дату файла;
- путь;
- описание Qwen;
- текст;
- объекты;
- цвета;
- отсутствие дублей.

**После этого уже подключаем новый UI-фильтр к правильной БД.**

Это даст нам гораздо более устойчивую основу для всей дальнейшей фотобазы.

---

### 👤 **User** — 2026-08-18 20:15:42

мда

---

### 🤖 **Assistant** — 2026-08-18 20:15:43

Да 🙂 Я слишком быстро ушёл в детали.

Суть гораздо проще:

**Да, сначала переделываем сам pipeline.**

```text
Фото из INPUT
      ↓
┌───────────────┐
│ Сортировка    │ → адрес
│ +             │
│ Qwen          │ → описание
└───────┬───────┘
        ↓
   одна запись
        ↓
   PostgreSQL
```

То есть при каждом фото одновременно собираем **всё, что уже умеем определять**, плюс **данные самого файла**.

После этого:

1. обновляем БД;
2. прогоняем небольшой тест;
3. проверяем, что данные корректные;
4. только потом переделываем UI под новую БД.

И **ничего сложного с hash, source/output и прочим сейчас не добавляем**, если это не требуется текущему pipeline.

Я бы сейчас просто нашёл **тот скрипт, который непосредственно запускает нынешнюю сортировку + Qwen**, и от него уже пошёл.

---

### 👤 **User** — 2026-08-18 20:15:57

ок

---

### 🤖 **Assistant** — 2026-08-18 20:15:57

Ок. Тогда идём от существующего pipeline, без лишней перестройки.

Следующий шаг — **найти фактическую точку запуска текущей сортировки и Qwen**. Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "=== SCRIPTS ===" && \
find scripts app -type f -name "*.py" | sort | \
grep -Ei 'photo|process|sort|qwen|daily|pipeline|import|analy'
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE 'qwen|qwen3|ollama|build_photo_record|INSERT INTO photos|UPDATE photos|photos \(' \
scripts app --include="*.py" 2>/dev/null | head -200
```

По этому выводу определим **один реальный pipeline**, который сейчас используется, и уже в него аккуратно добавим сбор данных файла → БД.

---

### 👤 **User** — 2026-08-18 20:16:33

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "=== SCRIPTS ===" && \
find scripts app -type f -name "*.py" | sort | \
grep -Ei 'photo|process|sort|qwen|daily|pipeline|import|analy'
=== SCRIPTS ===
app/core/scene_analyzer.py
app/ocr/ocr_pipeline.py
app/pipeline/__init__.py
app/pipeline/queue.py
app/pipeline/worker.py
app/web/components/photos_before_cache_20260816_145128.py
app/web/components/photos.py
app/web/components/technical_modules/photo_processing.py
app/web/components/technical_modules/qwen.py
app/web/photo_db.py
app/web_v01_backup_20260816_142053/components/photos.py
scripts/analyze_sequence_v38.py
scripts/analyze_subfingerprints.py
scripts/banner_qwen25vl_test_v01.py
scripts/banner_qwen4b_test_v01.py
scripts/import_qwen_to_db.py
scripts/qwen4b_output_v01_before_compact_prompt.py
scripts/qwen4b_output_v01.py
scripts/qwen_prompt_ablation.py
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

alexice@NEURO:~$ cd ~/projects/scene_fingerprint_mvp_v02 && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT column_name, data_type
 FROM information_schema.columns
 WHERE table_name = 'photos'
 ORDER BY ordinal_position;" \
| cat
      column_name      |          data_type          
-----------------------+-----------------------------
 id                    | integer
 address               | text
 filename              | text
 path                  | text
 client                | text
 brand                 | text
 category              | text
 description           | text
 confidence            | integer
 qwen_status           | text
 qwen_time_sec         | double precision
 text_json             | jsonb
 colors_json           | jsonb
 objects_json          | jsonb
 environment_json      | jsonb
 image_quality_json    | jsonb
 camera_view_json      | jsonb
 scene_objects_json    | jsonb
 analysis_quality_json | jsonb
 raw_json              | jsonb
 imported_at           | timestamp without time zone
(21 rows)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT
    MIN(imported_at) AS first_date,
    MAX(imported_at) AS last_date,
    COUNT(*) AS total,
    COUNT(DISTINCT DATE_TRUNC('month', imported_at)) AS months
 FROM photos;" \
| cat
     first_date      |      last_date      | total | months 
---------------------+---------------------+-------+--------
 2026-08-16 14:29:56 | 2026-08-16 14:29:56 |   100 |      1
(1 row)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
PGPASSWORD='' psql -h localhost -p 5432 -U lora -d photobase -c \
"SELECT
    DATE_TRUNC('month', imported_at) AS month,
    COUNT(*) AS photos
 FROM photos
 GROUP BY 1
 ORDER BY 1 DESC;" \
| cat
        month        | photos 
---------------------+--------
 2026-08-01 00:00:00 |    100
(1 row)

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "=== DAILY RUNS ===" && \
find data/output/daily -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort && \
echo && \
echo "=== PHOTO DATES / PATHS ===" && \
find data/output/daily -type f $ -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' $ \
-printf '%TY-%Tm-%Td %TH:%TM:%TS | %p\n' | sort | head -40
=== DAILY RUNS ===
20260816_224402
20260816_225139
20260816_225256
20260816_225554
20260816_225647
20260816_225712
20260816_225907
20260816_225941
20260816_230008
20260816_230013
20260816_230042
20260816_230330
20260816_231222
20260818_115048

=== PHOTO DATES / PATHS ===
2026-08-13 17:25:42.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (2).JPG
2026-08-13 17:25:44.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (3).JPG
2026-08-13 17:25:44.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (4).JPG
2026-08-13 17:25:46.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (5).JPG
2026-08-13 17:25:58.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (6).JPG
2026-08-13 17:26:10.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (7).JPG
2026-08-13 17:26:10.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (8).JPG
2026-08-13 17:26:10.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (9).JPG
2026-08-13 17:26:16.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (10).JPG
2026-08-13 17:26:20.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (11).JPG
2026-08-13 17:26:20.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (12).JPG
2026-08-13 17:26:30.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (13).JPG
2026-08-13 17:26:36.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (14).JPG
2026-08-13 17:26:38.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (15).JPG
2026-08-13 17:26:38.0000000000 | data/output/daily/20260818_115048/93_v33/Нагибина М. пр-кт  Нансена ул. 127 (в 50 м от моста), A (1).JPG
2026-08-13 17:31:48.0000000000 | data/output/daily/20260818_115048/85_v33/Ленина 52 (3).JPG
2026-08-13 17:31:48.0000000000 | data/output/daily/20260818_115048/85_v33/Ленина 52 (4).JPG
2026-08-13 17:31:48.0000000000 | data/output/daily/20260818_115048/85_v33/Ленина 52 (5).JPG
2026-08-13 17:31:50.0000000000 | data/output/daily/20260818_115048/85_v33/Ленина 52 (1).JPG
2026-08-13 17:31:50.0000000000 | data/output/daily/20260818_115048/85_v33/Ленина 52 (6).JPG
2026-08-13 17:31:52.0000000000 | data/output/daily/20260818_115048/85_v33/Ленина 52 (2).JPG
2026-08-13 17:35:08.0000000000 | data/output/daily/20260818_115048/84_v33/Ленина пр-кт 125–127, A(26).JPG
2026-08-13 17:35:08.0000000000 | data/output/daily/20260818_115048/84_v33/Ленина пр-кт 125–127, A(27).JPG
2026-08-13 17:35:10.0000000000 | data/output/daily/20260818_115048/84_v33/Ленина пр-кт 125–127, A(28).JPG
2026-08-13 17:35:12.0000000000 | data/output/daily/20260818_115048/84_v33/Ленина пр-кт 125–127, A(29).JPG
2026-08-13 17:36:36.0000000000 | data/output/daily/20260818_115048/84_v33/Ленина пр-кт 125–127, A(30).JPG
2026-08-13 17:36:44.0000000000 | data/output/daily/20260818_115048/84_v33/Ленина пр-кт 125–127, A(31).JPG
2026-08-13 17:36:46.0000000000 | data/output/daily/20260818_115048/84_v33/Ленина пр-кт 125–127, A(24).JPG
2026-08-13 17:36:46.0000000000 | data/output/daily/20260818_115048/84_v33/Ленина пр-кт 125–127, A(25).JPG
2026-08-14 12:27:56.0000000000 | data/output/daily/20260818_115048/94_v33/Шолохова 127 А (2).JPG
2026-08-14 12:27:56.0000000000 | data/output/daily/20260818_115048/94_v33/Шолохова 127 А (3).JPG
2026-08-14 12:27:56.0000000000 | data/output/daily/20260818_115048/94_v33/Шолохова 127 А (4).JPG
2026-08-14 12:27:58.0000000000 | data/output/daily/20260818_115048/94_v33/Шолохова 127 А (5).JPG
2026-08-14 12:28:00.0000000000 | data/output/daily/20260818_115048/94_v33/Шолохова 127 А (6).JPG
2026-08-14 12:28:22.0000000000 | data/output/daily/20260818_115048/94_v33/Шолохова 127 А (7).JPG
2026-08-14 12:28:24.0000000000 | data/output/daily/20260818_115048/94_v33/Шолохова 127 А (8).JPG
2026-08-14 12:28:26.0000000000 | data/output/daily/20260818_115048/94_v33/Шолохова 127 А (10).JPG
2026-08-14 12:28:26.0000000000 | data/output/daily/20260818_115048/94_v33/Шолохова 127 А (9).JPG
2026-08-14 12:28:28.0000000000 | data/output/daily/20260818_115048/94_v33/Шолохова 127 А (11).JPG
2026-08-14 12:28:32.0000000000 | data/output/daily/20260818_115048/94_v33/Шолохова 127 А (12).JPG
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "=== SCRIPTS ===" && \
find scripts app -type f -name "*.py" | sort | \
grep -Ei 'photo|process|sort|qwen|daily|pipeline|import|analy'
=== SCRIPTS ===
app/core/scene_analyzer.py
app/ocr/ocr_pipeline.py
app/pipeline/__init__.py
app/pipeline/queue.py
app/pipeline/worker.py
app/web/components/photos_before_cache_20260816_145128.py
app/web/components/photos.py
app/web/components/technical_modules/photo_processing.py
app/web/components/technical_modules/qwen.py
app/web/photo_db.py
app/web_v01_backup_20260816_142053/components/photos.py
scripts/analyze_sequence_v38.py
scripts/analyze_subfingerprints.py
scripts/banner_qwen25vl_test_v01.py
scripts/banner_qwen4b_test_v01.py
scripts/import_qwen_to_db.py
scripts/qwen4b_output_v01_before_compact_prompt.py
scripts/qwen4b_output_v01.py
scripts/qwen_prompt_ablation.py
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
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE 'qwen|qwen3|ollama|build_photo_record|INSERT INTO photos|UPDATE photos|photos \(' \
scripts app --include="*.py" 2>/dev/null | head -200
scripts/banner_model_compare_v04.py:19:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v04.py:20:    "qwen2.5vl:3b",
scripts/banner_model_compare_v04.py:23:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v04.py:135:        OLLAMA_URL,
scripts/banner_qwen25vl_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen25vl_test_v01")
scripts/banner_qwen25vl_test_v01.py:14:MODEL = "qwen2.5vl:3b"
scripts/banner_qwen25vl_test_v01.py:16:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_qwen25vl_test_v01.py:104:        OLLAMA_URL,
scripts/banner_qwen25vl_test_v01.py:159:    print("QWEN2.5-VL 3B TEST")
scripts/banner_model_compare_v05.py:16:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v05.py:17:    "qwen2.5vl:3b",
scripts/banner_model_compare_v05.py:20:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v05.py:113:        OLLAMA_URL,
scripts/banner_llm_full_v02.py:11:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_llm_full_v02.py:109:    print("Sending to Ollama...")
scripts/banner_llm_full_v02.py:141:    print("QWEN3-VL BANNER TEST")
scripts/import_qwen_to_db.py:10:QWEN_DIR = PROJECT / "data/metadata/qwen4b"
scripts/import_qwen_to_db.py:39:        CREATE TABLE IF NOT EXISTS photos (
scripts/import_qwen_to_db.py:53:            qwen_status TEXT,
scripts/import_qwen_to_db.py:54:            qwen_time_sec REAL,
scripts/import_qwen_to_db.py:90:        ON photos(qwen_status)
scripts/import_qwen_to_db.py:114:    relative = json_path.relative_to(QWEN_DIR)
scripts/import_qwen_to_db.py:166:        INSERT INTO photos (
scripts/import_qwen_to_db.py:178:            qwen_status,
scripts/import_qwen_to_db.py:179:            qwen_time_sec,
scripts/import_qwen_to_db.py:216:            qwen_status = excluded.qwen_status,
scripts/import_qwen_to_db.py:217:            qwen_time_sec = excluded.qwen_time_sec,
scripts/import_qwen_to_db.py:264:    QWEN_DIR.mkdir(
scripts/import_qwen_to_db.py:275:        QWEN_DIR.rglob("*.json")
scripts/import_qwen_to_db.py:279:    print("QWEN → SQLITE")
scripts/import_qwen_to_db.py:283:    print("QWEN DIR:", QWEN_DIR)
scripts/banner_qwen4b_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen4b_test_v01")
scripts/banner_qwen4b_test_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_qwen4b_test_v01.py:16:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_qwen4b_test_v01.py:104:        OLLAMA_URL,
scripts/banner_qwen4b_test_v01.py:159:    print("QWEN3-VL 4B TEST")
scripts/banner_llm_folder_search_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01_before_compact_prompt.py:15:OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"
scripts/qwen4b_output_v01_before_compact_prompt.py:17:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01_before_compact_prompt.py:18:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/qwen4b_output_v01_before_compact_prompt.py:351:        OLLAMA_URL,
scripts/qwen4b_output_v01_before_compact_prompt.py:363:    # Ollama performance diagnostics
scripts/qwen4b_output_v01_before_compact_prompt.py:386:        "[OLLAMA]",
scripts/qwen4b_output_v01_before_compact_prompt.py:649:    print("QWEN3-VL 4B — OUTPUT ANALYSIS")
scripts/qwen4b_output_v01.py:15:OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"
scripts/qwen4b_output_v01.py:17:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01.py:18:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/qwen4b_output_v01.py:167:            OLLAMA_URL,
scripts/qwen4b_output_v01.py:201:            "[OLLAMA]",
scripts/qwen4b_output_v01.py:228:                    "[QWEN RETRY]",
scripts/qwen4b_output_v01.py:242:                "[QWEN JSON ERROR]",
scripts/qwen4b_output_v01.py:525:        help="Output directory for Qwen metadata"
scripts/qwen4b_output_v01.py:536:    print("QWEN3-VL 4B — OUTPUT ANALYSIS")
scripts/banner_llm_full_v01.py:9:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_model_compare_v02.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v02.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v02.py:27:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v02.py:98:        OLLAMA_URL,
scripts/banner_model_compare_v01.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v01.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v01.py:28:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v01.py:103:        OLLAMA_URL,
scripts/banner_database_v02.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/migrate_sqlite_to_postgres.py:75:                qwen_status,
scripts/migrate_sqlite_to_postgres.py:76:                qwen_time_sec,
scripts/migrate_sqlite_to_postgres.py:111:                row["qwen_status"],
scripts/migrate_sqlite_to_postgres.py:112:                row["qwen_time_sec"],
scripts/migrate_sqlite_to_postgres.py:155:                INSERT INTO photos (
scripts/migrate_sqlite_to_postgres.py:165:                    qwen_status,
scripts/migrate_sqlite_to_postgres.py:166:                    qwen_time_sec,
scripts/banner_database_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/llm_resolver_v01.py:11:MODEL = "qwen3:4b"
scripts/llm_resolver_v01.py:168:            "ollama",
scripts/llm_resolver_v01.py:224:        print("--- QWEN3:4B ---")
scripts/qwen_prompt_ablation.py:15:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen_prompt_ablation.py:16:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/qwen_prompt_ablation.py:162:            OLLAMA_URL,
scripts/qwen_prompt_ablation.py:193:        print("OLLAMA TOTAL:    ", round(stats["total"], 2), "sec")
scripts/qwen_prompt_ablation.py:218:    print("QWEN3-VL 4B — PROMPT ABLATION TEST")
scripts/banner_model_compare_v03.py:19:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v03.py:20:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v03.py:23:OLLAMA_URL = "http://localhost:11434/api/chat"
scripts/banner_model_compare_v03.py:116:        OLLAMA_URL,
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:59:            qwen_status,
app/web/components/search.py:60:            qwen_time_sec,
app/web/components/technical_modules/photo_processing.py:191:            # QWEN3-VL 4B
app/web/components/technical_modules/photo_processing.py:194:            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"
app/web/components/technical_modules/photo_processing.py:196:            if not qwen_script.exists():
app/web/components/technical_modules/photo_processing.py:199:                    "✓ Hybrid завершён → Qwen script не найден"
app/web/components/technical_modules/photo_processing.py:203:                    f"Не найден Qwen script: {qwen_script}",
app/web/components/technical_modules/photo_processing.py:214:            qwen_output = (
app/web/components/technical_modules/photo_processing.py:218:                / "qwen4b"
app/web/components/technical_modules/photo_processing.py:222:            qwen_output.mkdir(
app/web/components/technical_modules/photo_processing.py:228:                "▶ Qwen3-VL 4B: выполняется..."
app/web/components/technical_modules/photo_processing.py:233:                "Запускается Qwen3-VL 4B.",
app/web/components/technical_modules/photo_processing.py:240:                qwen_process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:242:                    str(qwen_script),
app/web/components/technical_modules/photo_processing.py:246:                    str(qwen_output),
app/web/components/technical_modules/photo_processing.py:252:                qwen_lines = []
app/web/components/technical_modules/photo_processing.py:256:                    line = await qwen_process.stdout.readline()
app/web/components/technical_modules/photo_processing.py:266:                    qwen_lines.append(text)
app/web/components/technical_modules/photo_processing.py:271:                qwen_returncode = await qwen_process.wait()
app/web/components/technical_modules/photo_processing.py:273:                if qwen_returncode != 0:
app/web/components/technical_modules/photo_processing.py:277:                        "Qwen3-VL 4B: ошибка"
app/web/components/technical_modules/photo_processing.py:282:                        "но Qwen3-VL 4B завершился с ошибкой.",
app/web/components/technical_modules/photo_processing.py:290:                    "✓ Hybrid v12 + Qwen3-VL 4B: готово"
app/web/components/technical_modules/photo_processing.py:299:                    "Hybrid v12 + Qwen3-VL 4B.",
app/web/components/technical_modules/photo_processing.py:304:            except Exception as qwen_error:
app/web/components/technical_modules/photo_processing.py:308:                    "Qwen3-VL 4B: ошибка запуска"
app/web/components/technical_modules/photo_processing.py:312:                    f"Ошибка запуска Qwen: {qwen_error}",
app/web/components/technical_modules/photo_processing.py:384:            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
app/web/components/technical_modules/data.py:13:QWEN_ROOT = PROJECT / "data" / "metadata" / "qwen4b"
app/web/components/technical_modules/data.py:78:def qwen_stats():
app/web/components/technical_modules/data.py:80:    Статистика Qwen3-VL 4B.
app/web/components/technical_modules/data.py:90:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/data.py:95:    if QWEN_ROOT.exists():
app/web/components/technical_modules/data.py:98:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/data.py:243:    qwen = qwen_stats()
app/web/components/technical_modules/data.py:368:        # QWEN
app/web/components/technical_modules/data.py:378:                    "Qwen3-VL 4B"
app/web/components/technical_modules/data.py:389:            qwen_color = (
app/web/components/technical_modules/data.py:391:                if qwen["status"] == "ГОТОВ"
app/web/components/technical_modules/data.py:396:                qwen["status"],
app/web/components/technical_modules/data.py:397:                color=qwen_color,
app/web/components/technical_modules/data.py:405:                f"Обработано: {qwen['photos']}"
app/web/components/technical_modules/data.py:409:                f"OK: {qwen['ok']}"
app/web/components/technical_modules/data.py:413:                f"Ошибок: {qwen['errors']}"
app/web/components/technical_modules/data.py:417:                f"Адресов: {qwen['addresses']}"
app/web/components/technical_modules/data.py:421:                f"Среднее время: {qwen['avg_time']:.2f} сек"
app/web/components/technical_modules/data.py:425:                f"Средняя уверенность: {qwen['avg_confidence']:.1f}%"
app/web/components/technical_modules/qwen.py:10:QWEN_ROOT = (
app/web/components/technical_modules/qwen.py:14:    / "qwen4b"
app/web/components/technical_modules/qwen.py:24:QWEN_SCRIPT = (
app/web/components/technical_modules/qwen.py:27:    / "qwen4b_output_v01.py"
app/web/components/technical_modules/qwen.py:35:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/qwen.py:40:    if QWEN_ROOT.exists():
app/web/components/technical_modules/qwen.py:44:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/qwen.py:57:def _load_qwen_status():
app/web/components/technical_modules/qwen.py:72:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:156:                "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:173:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:200:def build_qwen():
app/web/components/technical_modules/qwen.py:205:            "QWEN3-VL 4B"
app/web/components/technical_modules/qwen.py:269:                "▶ Запустить Qwen",
app/web/components/technical_modules/qwen.py:275:                "■ Остановить Qwen",
app/web/components/technical_modules/qwen.py:294:    qwen_process = None
app/web/components/technical_modules/qwen.py:295:    qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:297:    async def stop_qwen():
app/web/components/technical_modules/qwen.py:298:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:299:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:301:        if qwen_process is None:
app/web/components/technical_modules/qwen.py:304:        qwen_stop_requested = True
app/web/components/technical_modules/qwen.py:307:            f"[QWEN MANUAL] STOP REQUESTED PID={qwen_process.pid}",
app/web/components/technical_modules/qwen.py:312:            qwen_process.terminate()
app/web/components/technical_modules/qwen.py:317:                f"[QWEN MANUAL] STOP FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:321:    async def run_qwen():
app/web/components/technical_modules/qwen.py:323:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:324:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:326:        print("[QWEN MANUAL] START", flush=True)
app/web/components/technical_modules/qwen.py:328:        qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:335:            if not QWEN_SCRIPT.exists():
app/web/components/technical_modules/qwen.py:338:                    f"[QWEN MANUAL] SCRIPT NOT FOUND: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:343:                    f"Не найден Qwen script: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:355:                    "[QWEN MANUAL] HYBRID RUN NOT FOUND",
app/web/components/technical_modules/qwen.py:382:                    f"[QWEN MANUAL] NO IMAGES: {result_dir}",
app/web/components/technical_modules/qwen.py:396:            qwen_output = QWEN_ROOT / run_name
app/web/components/technical_modules/qwen.py:397:            qwen_output.mkdir(
app/web/components/technical_modules/qwen.py:403:                f"[QWEN MANUAL] INPUT: {result_dir}",
app/web/components/technical_modules/qwen.py:408:                f"[QWEN MANUAL] OUTPUT: {qwen_output}",
app/web/components/technical_modules/qwen.py:413:                f"[QWEN MANUAL] IMAGES: {total_images}",
app/web/components/technical_modules/qwen.py:420:            model_label.text = "qwen3-vl:4b-instruct"
app/web/components/technical_modules/qwen.py:435:                f"Запуск Qwen3-VL 4B: {total_images} фото",
app/web/components/technical_modules/qwen.py:447:                str(QWEN_SCRIPT),
app/web/components/technical_modules/qwen.py:451:                str(qwen_output),
app/web/components/technical_modules/qwen.py:457:            qwen_process = process
app/web/components/technical_modules/qwen.py:460:                f"[QWEN MANUAL] PID: {process.pid}",
app/web/components/technical_modules/qwen.py:488:                    f"[QWEN] {text}",
app/web/components/technical_modules/qwen.py:530:                if "[QWEN] OK |" in text:
app/web/components/technical_modules/qwen.py:580:                    "[QWEN] ERROR" in text
app/web/components/technical_modules/qwen.py:581:                    or "[QWEN] FAILED" in text
app/web/components/technical_modules/qwen.py:617:                if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:627:                f"[QWEN MANUAL] FINISHED "
app/web/components/technical_modules/qwen.py:632:            if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:638:                    f"Qwen остановлен: "
app/web/components/technical_modules/qwen.py:650:                    "✓ Qwen3-VL 4B завершён",
app/web/components/technical_modules/qwen.py:660:                status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:663:                    f"Qwen завершился с ошибкой: {returncode}",
app/web/components/technical_modules/qwen.py:671:                f"[QWEN MANUAL] EXCEPTION: {exc!r}",
app/web/components/technical_modules/qwen.py:676:            status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:680:                    f"Ошибка запуска Qwen: {exc}",
app/web/components/technical_modules/qwen.py:689:            qwen_process = None
app/web/components/technical_modules/qwen.py:690:            qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:706:                    f"[QWEN MANUAL] UI REFRESH FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:712:        data = _load_qwen_status()
app/web/components/technical_modules/qwen.py:772:    run_button.on_click(run_qwen)
app/web/components/technical_modules/qwen.py:773:    stop_button.on_click(stop_qwen)
app/web/components/photos.py:91:from app.web.photo_db import build_photo_record_index
app/web/components/photos.py:118:            build_photo_record_index(PROJECT_ROOT)
app/web/components/photos.py:445:                        if value("qwen_status") != "—":
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:16:34

> **Inspecting Hybrid Sorting Implementation Files**
>
>
> **Inspected hybrid sorting implementation files**
>
> 
>
> Worked for a couple of seconds

Да. Теперь картина достаточно ясная — **делаем первый этап именно как единый pipeline**, а не как два независимых запуска.

### Что фиксируем

Поток будет такой:

```text
ВХОДНАЯ ПАПКА
     │
     ▼
DINO v33 / Hybrid
     │
     ├──► сортировка
     │       │
     │       └──► data/output/daily/<RUN>/<address_v33>/фото
     │
     └──► параллельно формируется реестр файлов
                         │
                         ▼
                  PostgreSQL photos
                         │
                         ▼
                    Qwen 3-VL 4B
                         │
                         ▼
                  обновление той же записи
                         │
                         ▼
                 ГОТОВАЯ ФОТОБАЗА
```

То есть **не надо сначала копировать фото → потом отдельно собирать базу → потом отдельно запускать Qwen**.

При сортировке мы уже знаем:

- исходный файл;
- итоговый путь;
- адрес / fingerprint;
- имя файла;
- размер/время файла;
- дату файла;
- клиента, если можем определить;
- `run_id`.

И это сразу пишем в PostgreSQL.

А когда Qwen закончил конкретное фото — **не создаём новую запись**, а обновляем существующую.

---

## Важный момент по текущей БД

Таблица `photos` уже подходит для этого:

```text
id
address
filename
path
client
brand
category
description
confidence
qwen_status
qwen_time_sec
text_json
colors_json
objects_json
environment_json
image_quality_json
camera_view_json
scene_objects_json
analysis_quality_json
raw_json
imported_at
```

Но для нормального нового pipeline я бы **сразу добавил несколько служебных полей**.

Например:

```text
source_path
source_filename
file_size
file_mtime
run_id
sort_status
sort_confidence
qwen_model
qwen_started_at
qwen_finished_at
```

И главное — уникальность по файлу/пути, чтобы повторный запуск не создавал дубли.

---

# Первый этап сейчас

Не трогаем UI и не трогаем прокрутку.

Сначала делаем backend:

### `scripts/daily_pipeline_v01.py`

Он будет запускаться примерно так:

```bash
uv run python scripts/daily_pipeline_v01.py \
    --input /путь/к/новым/фото
```

И внутри:

```text
1. создать RUN
2. найти фотографии
3. запустить существующий DINO/Hybrid sorter
4. каждое успешно отсортированное фото зарегистрировать в PostgreSQL
5. запустить Qwen для новых фото
6. результаты Qwen записать в ту же строку
7. сформировать итоговый report
```

При этом **старые скрипты сортировки не переписываем**. Мы сначала оборачиваем существующую рабочую логику.

---

## Но перед написанием pipeline нужно проверить интерфейс двух существующих скриптов

Дай сейчас только эти два вывода.

### 1. Как запускается текущая сортировка

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python scripts/sort_test_and_report_hybrid_v12.py --help
```

Если там нет `--help` или он запускает обработку — **не страшно, Ctrl+C**.

И ещё:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '1,120p' scripts/sort_test_and_report_hybrid_v12.py
```

### 2. Как запускается Qwen

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python scripts/qwen4b_output_v01.py --help
```

и:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '480,570p' scripts/qwen4b_output_v01.py
```

---

### Почему именно сейчас это важно

У нас уже есть рабочие части:

- `sort_test_and_report_hybrid_v12.py` — сортировка;
- `qwen4b_output_v01.py` — описание;
- `import_qwen_to_db.py` — старый импорт;
- PostgreSQL `photos` — целевая база;
- `data/output/daily/<RUN>` — фактический результат сортировки.

Поэтому **не будем писать ещё одну систему сортировки или ещё один импортёр**.

Сначала выясним точные входы/выходы этих двух рабочих модулей, а затем сделаем тонкий `daily_pipeline_v01`, который свяжет их.

И да — это как раз позволит потом сделать то, о чём мы говорили: **фото сразу появляются в базе/гриде после сортировки, а Qwen постепенно дополняет карточку**, без ожидания полного окончания обработки.

---

### 👤 **User** — 2026-08-18 20:17:28

по идее квен это гпу пролцесс, а дино - цпу, при параллельном запуске они не должны мешать друг другу

---

### 🤖 **Assistant** — 2026-08-18 20:17:28

Да, **в нашей конфигурации это как раз имеет смысл**. Но есть важная оговорка: DINO у нас тоже может использовать GPU, если текущий sorter запускается с CUDA. Поэтому сначала надо разделить **где фактически выполняется DINO**.

Если сделать так, как мы хотим:

```text
                 НОВЫЕ ФОТО
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
      DINO / SORT             QWEN 3-VL
       CPU-процесс            GPU-процесс
          │                     │
          ▼                     ▼
      адрес + путь          описание JSON
          │                     │
          └──────────┬──────────┘
                     ▼
                PostgreSQL
```

то это действительно хорошая архитектура.

### Но я бы сделал ещё лучше

Не запускать DINO и Qwen просто двумя независимыми процессами «на всякий случай», а сделать **конвейер с очередью**:

```text
Фото
 │
 ├── DINO → определил адрес
 │            │
 │            ├── запись в БД
 │            │
 │            └── очередь Qwen
 │                       │
 │                       ▼
 │                  Qwen GPU
 │                       │
 │                       ▼
 │                  UPDATE photos
 │
 └── следующие фото → DINO
```

То есть **DINO не ждёт Qwen**.

Получаем очень полезное свойство:

> Как только DINO определил и положил фото в адресную папку — оно уже появляется в базе. Qwen потом независимо дополняет его описанием.

### И это особенно хорошо для нашего железа

Если DINO действительно работает на CPU:

- Ryzen 5600 → занимается сортировкой;
- RTX 3060 12 GB → занимается Qwen;
- 32 GB RAM → общий буфер;
- процессы практически независимы.

При этом Qwen может обрабатывать уже отсортированные фотографии, пока DINO продолжает сортировать следующие.

---

### Единственное, что надо проверить

Не будем предполагать, что DINO CPU.

В текущем проекте у нас раньше была:

```text
Torch
CUDA = True
RTX 3060
```

Поэтому текущий DINO вполне может использовать GPU.

**Если он сейчас CUDA**, запускать одновременно Qwen 4B и DINO на одной RTX 3060 можно, но это уже будет конкуренция за VRAM и вычислительные ресурсы.

Поэтому я предлагаю первым делом проверить:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE 'cuda|device|torch.device|\.to\(' \
scripts/sort_test_and_report_hybrid_v12.py \
scripts/sort_neighbor_v12.py \
scripts/sort_neighbor_v36.py \
scripts/sort_sequence_v38.py \
app --include="*.py" 2>/dev/null | head -100
```

Если увидим, что DINO можно принудительно отправить на CPU, я бы для **первого фонового pipeline** сделал именно:

**DINO → CPU, Qwen → RTX 3060.**

Это даст нам настоящую параллельную обработку без борьбы двух моделей за одну видеокарту.

---

### 👤 **User** — 2026-08-18 20:18:16

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE 'cuda|device|torch.device|\.to\(' \
scripts/sort_test_and_report_hybrid_v12.py \
scripts/sort_neighbor_v12.py \
scripts/sort_neighbor_v36.py \
scripts/sort_sequence_v38.py \
app --include="*.py" 2>/dev/null | head -100
app/core/config.py:16:    device: str = os.getenv(
app/core/config.py:17:        "SCENE_DEVICE",
app/core/config.py:18:        "cuda" if torch.cuda.is_available() else "cpu"
app/core/embedder.py:20:        self.device = torch.device(settings.device)
app/core/embedder.py:22:        print(f"[SceneEmbedder] device={self.device}")
app/core/embedder.py:24:        if self.device.type == "cuda":
app/core/embedder.py:27:                f"{torch.cuda.get_device_name(0)}"
app/core/embedder.py:31:                f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
app/core/embedder.py:49:        self.model = self.model.to(self.device)
app/core/embedder.py:92:                key: value.to(
app/core/embedder.py:93:                    self.device,
app/ocr/ocr_pipeline.py:38:        print("[OCR] Ready. Device=CPU")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:18:17

Да — и здесь важный момент: **по текущему коду это не так**.

Мы нашли, что DINO сейчас по умолчанию тоже использует GPU:

```python
# app/core/config.py
"cuda" if torch.cuda.is_available() else "cpu"
```

и дальше:

```python
self.model = self.model.to(self.device)
```

То есть текущая схема фактически:

**DINO → GPU**  
**Qwen → GPU**

Поэтому параллельный запуск будет конкурировать за RTX 3060 12 GB VRAM и за вычислительные ресурсы GPU.

### Что предлагаю сделать

Раз мы хотим первый этап именно:

**фото → DINO сортировка → одновременно Qwen описание → обновление БД**

то логичнее разделить ресурсы:

```text
                         ┌── DINO → CPU
Новые фотографии ────────┤
                         └── Qwen → GPU
                              │
                              ▼
                         PostgreSQL
                              │
                              ▼
                         Web-фотобаза
```

То есть DINO принудительно:

```bash
SCENE_DEVICE=cpu
```

а Qwen оставить на GPU.

Тогда они действительно смогут работать параллельно, и главное — **Qwen не будет вытесняться из VRAM DINO-моделью**.

---

### Но есть ещё один нюанс

DINO на CPU — это не обязательно медленно настолько, чтобы отказаться от идеи.

У нас Ryzen 5 5600, 12 потоков. Можно выделить DINO, например, **6 CPU workers**, как мы уже закладывали для тяжёлых задач.

Получится:

```text
CPU
├── DINO worker 1
├── DINO worker 2
├── DINO worker 3
├── DINO worker 4
├── DINO worker 5
└── DINO worker 6

GPU
└── Qwen3-VL 4B
```

При этом PostgreSQL будет получать информацию **не после полного завершения этапов**, а по мере обработки.

### И вот это я бы сейчас сделал правильно

Не переделывать старые `sort_*` и `qwen_*` скрипты хаотично.

Сделать единый первый pipeline:

```text
INPUT
  ↓
DINO распознал
  ↓
создал/скопировал фото в address_v33
  │
  ├──────────────→ запись файла в PostgreSQL
  │
  └──────────────→ очередь Qwen
                         ↓
                    Qwen GPU
                         ↓
                    JSON metadata
                         ↓
                  UPDATE photos
```

То есть **БД начинает заполняться сразу**, а не импортируется огромным пакетом в конце.

И тогда в UI можно будет видеть:

```text
Фото: 1248
DINO: 1248 / 1248
Qwen: 817 / 1248
```

и постепенно:

```text
Qwen
██████████████░░░░░░ 65%
```

Причём фотографии уже будут отображаться в гриде, даже если Qwen ещё не успел их описать.

---

**Следующий шаг я бы сделал очень конкретный:** сначала посмотрим код `sort_test_and_report_hybrid_v12.py` и `qwen4b_output_v01.py`, чтобы понять, как именно сейчас передаётся список/папка фотографий. После этого соберём `pipeline_daily.py`, не ломая рабочие алгоритмы DINO v33 и Qwen 4B.

---

### 👤 **User** — 2026-08-18 20:18:51

давай

---

### 🤖 **Assistant** — 2026-08-18 20:18:55

Да. Делаем аккуратно, **не меняя пока сами алгоритмы распознавания DINO v33 и Qwen3-VL 4B**.

Сначала посмотрим два рабочих скрипта и их точки входа. Выполни одним блоком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \

echo "================ DINO HYBRID ================" && \
sed -n '1,260p' scripts/sort_test_and_report_hybrid_v12.py && \

echo && echo "================ QWEN ================" && \
sed -n '1,300p' scripts/qwen4b_output_v01.py
```

Если вывод слишком большой, лучше так — вытащим только архитектурно важные места:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \

echo "=== DINO: imports / config / main ===" && \
grep -nE '^import |^from |INPUT|OUTPUT|FINGER|DEVICE|device|def |if __name__|argparse|ArgumentParser' \
scripts/sort_test_and_report_hybrid_v12.py | head -200 && \

echo && echo "=== QWEN: imports / config / main ===" && \
grep -nE '^import |^from |INPUT|OUTPUT|MODEL|OLLAMA|def |if __name__|argparse|ArgumentParser' \
scripts/qwen4b_output_v01.py | head -250 && \

echo && echo "=== DINO calls ===" && \
grep -nE 'sort|recogn|finger|copy|shutil|Path|json|csv' \
scripts/sort_test_and_report_hybrid_v12.py | head -200 && \

echo && echo "=== QWEN calls ===" && \
grep -nE 'ollama|requests|POST|json|image|glob|rglob|Path|output' \
scripts/qwen4b_output_v01.py | head -250
```

### Что именно сейчас выясняем

Нам нужны четыре вещи:

1. **Откуда DINO получает входные фотографии.**
2. **Куда он складывает результат `*_v33`.**
3. **Как Qwen получает список фотографий после сортировки.**
4. **Как формируется JSON, который сейчас импортируется через `import_qwen_to_db.py`.**

После этого сделаем не новую систему с нуля, а обвязку вокруг уже рабочих компонентов:

```text
                    НОВЫЙ DAILY PIPELINE
                           │
                           ▼
                    новые фотографии
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
       DINO v33 / CPU             регистрация файла
              │                         │
              ▼                         │
       address_v33/                    │
              │                         │
              └────────────┬────────────┘
                           ▼
                    PostgreSQL photos
                           │
                           ▼
                     очередь Qwen
                           │
                           ▼
                    Qwen3-VL 4B / GPU
                           │
                           ▼
                    UPDATE photos
```

И важный принцип: **DINO и Qwen будут независимыми процессами**. Если Qwen временно занят, DINO продолжает сортировать. Если Qwen упал — фотографии и результаты DINO всё равно остаются в базе.

А потом уже добавим в UI ту самую **боковую прокрутку**, подборку и автоматическое появление фотографий без ожидания кнопки.

---

### 👤 **User** — 2026-08-18 20:19:22

int_mvp_v02 && \

echo "================ DINO HYBRID ================" && \
sed -n '1,260p' scripts/sort_test_and_report_hybrid_v12.py && \

echo && echo "================ QWEN ================" && \
sed -n '1,300p' scripts/qwen4b_output_v01.py
================ DINO HYBRID ================
#!/usr/bin/env python3

import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from collections import Counter

import psutil

PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/test"
OUTPUT_DIR = PROJECT / "data/output/test_sorted_v2"

FINGERPRINTS = [
    f"{i}_v33"
    for i in range(78, 96)
]

RECOGNITION_JSON = OUTPUT_DIR / "recognition.json"
REPORT_CSV = OUTPUT_DIR / "report.csv"
REPORT_JSON = OUTPUT_DIR / "report.json"
STATISTICS_JSON = OUTPUT_DIR / "statistics.json"

def gpu_stats():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )

        line = result.stdout.strip().splitlines()[0]
        parts = [x.strip() for x in line.split(",")]

        return {
            "gpu_name": parts[0],
            "gpu_utilization_percent": float(parts[1]),
            "gpu_memory_used_mb": float(parts[2]),
            "gpu_memory_total_mb": float(parts[3]),
        }

    except Exception:
        return {
            "gpu_name": None,
            "gpu_utilization_percent": None,
            "gpu_memory_used_mb": None,
            "gpu_memory_total_mb": None,
        }

def find_json(text):
    """
    Find the actual JSON array, ignoring messages such as:
        [SceneEmbedder]
        [Recognizer]
    """

    decoder = json.JSONDecoder()

    for i, ch in enumerate(text):
        if ch != "[":
            continue

        candidate = text[i:]

        try:
            obj, end = decoder.raw_decode(candidate)

            if isinstance(obj, list):
                return obj

        except json.JSONDecodeError:
            pass

    raise RuntimeError("Не удалось найти JSON-массив в выводе recognition")

def run_recognition():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fp_arg = ",".join(FINGERPRINTS)

    cmd = [
        "uv",
        "run",
        "scene-fingerprint",
        "recognize",
        str(INPUT_DIR),
        "--top-k",
        "5",
        "--threshold",
        "0.0",
        "--fingerprints",
        fp_arg,
        "--json",
    ]

    print("=" * 80)
    print("RUNNING RECOGNITION")
    print("=" * 80)

    print("Input:", INPUT_DIR)
    print("Fingerprints:", ", ".join(FINGERPRINTS))
    print()

    start = time.perf_counter()

    process = subprocess.run(
        cmd,
        cwd=PROJECT,
        capture_output=True,
        text=True,
    )

    elapsed = time.perf_counter() - start

    if process.returncode != 0:
        print(process.stdout)
        print(process.stderr)
        raise RuntimeError(
            f"recognize завершился с кодом {process.returncode}"
        )

    combined = process.stdout + "\n" + process.stderr

    data = find_json(combined)

    RECOGNITION_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return data, elapsed

def copy_images(data):
    print()
    print("=" * 80)
    print("SORTING")
    print("=" * 80)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    counters = Counter()

    for item in data:
        source = Path(item["file"])

        # Главный принцип:
        # ВСЕГДА используем best_id = первый кандидат.
        assigned_id = item.get("best_id")

        if not assigned_id:
            continue

        destination_dir = OUTPUT_DIR / assigned_id
        destination_dir.mkdir(parents=True, exist_ok=True)

        destination = destination_dir / source.name

        shutil.copy2(source, destination)

        counters[assigned_id] += 1

        candidates = item.get("candidates", [])

        row = {
            "file": str(source),
            "filename": source.name,
            "assigned_id": assigned_id,
            "score": item.get("score"),
            "second_score": item.get("second_score"),
            "margin": item.get("margin"),
            "confidence": item.get("confidence"),
            "status": item.get("status"),
            "best_image": item.get("best_image"),
            "best_image_score": item.get("best_image_score"),
            "global": None,
            "environment": None,
            "color": None,
            "spatial": None,
            "candidate_2": None,
            "candidate_2_score": None,
            "candidate_3": None,
            "candidate_3_score": None,
            "candidate_4": None,
            "candidate_4_score": None,
            "candidate_5": None,
            "candidate_5_score": None,
        }

        if candidates:
            c = candidates[0]

            row["global"] = c.get("global")
            row["environment"] = c.get("environment")
            row["color"] = c.get("color")
            row["spatial"] = c.get("spatial")

        for n in range(1, min(5, len(candidates))):
            c = candidates[n]

            row[f"candidate_{n+1}"] = c.get("id")
            row[f"candidate_{n+1}_score"] = c.get("score")

        rows.append(row)

    print()

    for k in sorted(counters, key=lambda x: int(x.split("_")[0])):
        print(f"{k:10s} {counters[k]:4d}")

    return rows, counters

def write_reports(rows, counters, recognition_time):
    fields = [
        "file",
        "filename",
        "assigned_id",
        "score",
        "second_score",
        "margin",
        "confidence",
        "status",
        "best_image",
        "best_image_score",
        "global",
        "environment",
        "color",
        "spatial",
        "candidate_2",
        "candidate_2_score",
        "candidate_3",
        "candidate_3_score",
        "candidate_4",
        "candidate_4_score",
        "candidate_5",
        "candidate_5_score",
    ]

    with open(REPORT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

================ QWEN ================
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
Ты анализируешь фотографию с улицы для базы наружной рекламы.

Найди рекламный баннер и верни ТОЛЬКО JSON.
Не добавляй пояснений вне JSON.
Не повторяй информацию.
Не придумывай отсутствующую информацию.

Формат:

{
  "client": "",
  "brand": "",
  "category": "",
  "text": [],
  "colors": [],
  "objects": [],
  "description": "",
  "banner_type": "видеоэкран",

  "environment": {
    "weather": "",
    "precipitation": "",
    "lighting": ""
  },

  "image_quality": {
    "overall": "",
    "sharpness": "",
    "exposure": "",
    "visibility": "",
    "banner_visible": true,
    "banner_readability": "",
    "motion_blur": false,
    "occlusion": false
  },

  "camera_view": {
    "distance": "",
    "angle": ""
  },

  "analysis_quality": {
    "banner_analysis": "",
    "text_analysis": ""
  },

  "confidence": 0
}

БАННЕР:
client — компания, организация или заказчик.
brand — торговая марка, имя кандидата или рекламируемый бренд.
category — категория рекламы.
text — читаемые надписи на баннере.
colors — основные цвета самого баннера.
objects — основные изображения и предметы НА БАННЕРЕ.
description — краткое описание композиции баннера, максимум 300 символов.
banner_type — на данном этапе "видеоэкран".

ОКРУЖЕНИЕ:
Определи ТОЛЬКО:
weather — солнечно / пасмурно / облачно / туман / неизвестно.
precipitation — нет / дождь / снег / мокрый снег / неизвестно.
lighting — яркий день / дневной свет / сумерки / ночь / искусственное освещение / неизвестно.

Не описывай окружающую сцену.
Не описывай здания, дороги, автомобили, автобусы, людей,
дорожные знаки, провода или растительность.

КАЧЕСТВО:
Оцени только качество фотографии и видимость баннера.

overall — хорошее / удовлетворительное / плохое.
sharpness — резкое / слегка размыто / сильно размыто / неизвестно.
exposure — нормальная / пересвечено / недоэкспонировано / очень тёмное / неизвестно.
visibility — хорошо виден / частично виден / плохо виден / не виден.
banner_visible — true или false.
banner_readability — высокая / средняя / низкая / невозможно определить.
motion_blur — true или false.
occlusion — true или false.

КАМЕРА:
distance — далеко / средняя дистанция / близко / неизвестно.
angle — прямо / слева / справа / сверху / снизу / косой ракурс / неизвестно.

Если баннер не виден:
client = ""
brand = ""
category = ""
text = []
colors = []
objects = []
description = ""
banner_visible = false

Массивы должны содержать только действительно важные элементы.
Не более 10 элементов в каждом массиве.
Не повторяй элементы.

confidence — уверенность в анализе от 0 до 100.
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

    MAX_ATTEMPTS = 2

    for attempt in range(1, MAX_ATTEMPTS + 1):

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
                "num_predict": 800,
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

        stats = {
            "total_duration_sec": round(
                data.get("total_duration", 0) / 1e9, 2
            ),
            "load_duration_sec": round(
                data.get("load_duration", 0) / 1e9, 2
            ),
            "prompt_eval_duration_sec": round(
                data.get("prompt_eval_duration", 0) / 1e9, 2
            ),
            "eval_duration_sec": round(
                data.get("eval_duration", 0) / 1e9, 2
            ),
            "prompt_eval_count": data.get(
                "prompt_eval_count"
            ),
            "eval_count": data.get(
                "eval_count"
            ),
        }

        print(
            "[OLLAMA]",
            stats,
            flush=True,
        )

        answer = data["message"]["content"]

        cleaned = answer.strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.replace("```json", "", 1)
            cleaned = cleaned.replace("```", "").strip()

        try:
            result = json.loads(cleaned)

            # JSON есть, но описание пустое — пробуем ещё раз
            description = str(
                result.get("description") or ""
            ).strip()

            if description:
                result["_time_sec"] = round(elapsed, 2)
                return result

            if attempt < MAX_ATTEMPTS:
                print(
                    "[QWEN RETRY]",
                    "description empty",
                    "| attempt:",
                    attempt + 1,
                    flush=True,
                )
                continue

            result["_time_sec"] = round(elapsed, 2)
            return result

        except Exception as exc:

            print(
                "[QWEN JSON ERROR]",
                repr(exc),
                "| attempt:",
                attempt,
                flush=True,
            )

            if attempt < MAX_ATTEMPTS:
                continue

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

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-18 20:19:23

Да, теперь картина достаточно ясная. И я бы **не стал пока переписывать эти два скрипта**.

У нас уже есть готовые рабочие компоненты:

- `sort_test_and_report_hybrid_v12.py` — DINO → распознавание → сортировка в `address_v33`;
- `qwen4b_output_v01.py` — берёт уже отсортированные фотографии и делает Qwen JSON;
- `import_qwen_to_db.py` — отдельно импортирует Qwen-результаты;
- PostgreSQL `photos` уже содержит **21 поле**, включая практически всё необходимое для будущего поиска.

### Что меняем

Сейчас цепочка:

```text
DINO
 ↓
копирование
 ↓
Qwen
 ↓
JSON-файлы
 ↓
отдельный импорт
 ↓
PostgreSQL
```

Делаем:

```text
                 ┌──────────────→ запись файла → PostgreSQL
                 │
Входные фото → DINO сортировка
                 │
                 └──────────────→ Qwen → UPDATE PostgreSQL
```

То есть **данные о файле заносим в PostgreSQL сразу после сортировки**, а Qwen потом дополняет ту же запись.

---

### Но сначала важный момент

Текущий Qwen жёстко смотрит сюда:

```python
INPUT_DIR = PROJECT / "data" / "output" / "test_sorted_v2"
```

А твой реальный daily pipeline уже создаёт:

```text
data/output/daily/20260818_115048/
    93_v33/
    85_v33/
    84_v33/
    94_v33/
    ...
```

Поэтому новый pipeline должен **передавать конкретную папку запуска Qwen**, а не менять глобальный `INPUT_DIR`.

То же самое с DINO: его рабочую логику пока не трогаем.

---

## Первый этап

Предлагаю создать отдельный:

```text
scripts/daily_pipeline_v01.py
```

Он будет делать:

```text
1. создать RUN_ID
2. запустить DINO v33
3. получить результаты сортировки
4. зарегистрировать каждую скопированную фотографию в PostgreSQL
5. запустить Qwen на этой папке
6. по мере получения JSON обновлять PostgreSQL
7. в конце выдать статистику
```

И **Qwen не будет ждать окончания импорта всей базы**.

Например:

```text
[DINO]  001.jpg → 93_v33
[DB]    001.jpg registered

[DINO]  002.jpg → 85_v33
[DB]    002.jpg registered

...

[QWEN]  001.jpg → OK 91%
[DB]    001.jpg updated

[QWEN]  002.jpg → OK 87%
[DB]    002.jpg updated
```

---

## И ещё лучше

Поскольку у нас PostgreSQL уже содержит:

```text
address
filename
path
client
brand
category
description
confidence
qwen_status
qwen_time_sec
...
raw_json
imported_at
```

**не надо сейчас добавлять новые таблицы для каждой стадии.**

Можно добавить только несколько технических полей, если действительно понадобятся:

```text
source_path
run_id
file_mtime
file_size
dino_status
dino_score
```

Но это сначала надо проверить — возможно, часть уже выводится из существующих `path`, `address` и данных DINO.

---

### И главное про CPU/GPU

Мы уже нашли:

```python
app/core/config.py

"cuda" if torch.cuda.is_available() else "cpu"
```

Поэтому перед параллельным запуском **нужно сделать DINO CPU-режим отдельным параметром**, например:

```bash
SCENE_DEVICE=cpu
```

А Qwen оставить:

```text
RTX 3060 → Qwen3-VL 4B
```

Получим именно ту архитектуру, которую ты описал:

```text
CPU                         GPU
────────────────────        ─────────────────
DINO v33                    Qwen3-VL 4B
    │                           │
    ▼                           ▼
address_v33/                metadata JSON
    │                           │
    └──────────┬────────────────┘
               ▼
          PostgreSQL
```

**Следующий шаг:** давай сначала сделаем `daily_pipeline_v01.py` как оркестратор, не ломая существующие скрипты. Для этого мне ещё нужен остаток `qwen4b_output_v01.py` после строки `def process(files):` — примерно до конца файла.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -n '300,620p' scripts/qwen4b_output_v01.py
```

После этого уже дам **первую рабочую версию pipeline**, а не будем гадать по архитектуре.

---

### 👤 **User** — 2026-08-18 20:20:24

у нас сортировка идет после дино - это нужно учитывать. там отдельбный скрипьт

---

### 🤖 **Assistant** — 2026-08-18 20:20:24

Да. Это важное уточнение. **DINO не сортирует сам по себе** — у нас цепочка разделена:

```text
входные фото
    ↓
DINO recognize
    ↓
результаты распознавания
    ↓
ОТДЕЛЬНЫЙ sort-скрипт
    ↓
address_v33/
    ↓
Qwen
```

И это **нужно сохранить**, потому что рабочая логика сортировки у нас уже отлажена.

### Поэтому новый pipeline не должен заменять сортировку

Правильная архитектура:

```text
                 DAILY PIPELINE
                       │
                       ▼
                 новые фотографии
                       │
                       ▼
              ┌─────────────────┐
              │ DINO recognize   │
              │ CPU              │
              └────────┬────────┘
                       │
                recognition.json
                       │
                       ▼
              ┌─────────────────┐
              │ SORT SCRIPT     │
              │ v33 / hybrid    │
              └────────┬────────┘
                       │
              data/output/daily/
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
         PostgreSQL          Qwen GPU
         файл + адрес          │
              │                ▼
              │             JSON
              │                │
              └───────┬────────┘
                      ▼
                  PostgreSQL
```

### И вот здесь появляется хорошая возможность

**После сортировки не надо ждать Qwen.**

Как только sort-скрипт скопировал:

```text
93_v33/Нагибина...JPG
```

мы сразу можем создать запись:

```text
photos
────────────────────────────
address = 93_v33
filename = Нагибина...JPG
path = ...
qwen_status = pending
imported_at = ...
```

А Qwen уже потом независимо заполнит:

```text
client
brand
category
description
confidence
text_json
colors_json
objects_json
...
qwen_status = done
qwen_time_sec = ...
raw_json = ...
```

### То есть отдельные этапы сохраняем

Я бы вообще **не объединял DINO и sort в один скрипт**:

```text
recognize.py       ← существующий рабочий механизм
       ↓
sort_*.py          ← существующий рабочий алгоритм
       ↓
register_to_db.py  ← новый
       ↓
qwen4b_output.py   ← существующий Qwen
       ↓
update_db.py       ← новый/адаптированный
```

А сверху:

```text
daily_pipeline.py
```

только **оркестратор**, который запускает их в правильном порядке.

---

И ещё один момент: твой `sort_test_and_report_hybrid_v12.py` сейчас сам запускает `scene-fingerprint recognize`, то есть фактически там уже объединены **recognize + sort**.

Но у нас есть отдельные `sort_sequence_v38/v39` и другие версии. Поэтому прежде чем выбирать, какой именно скрипт ставить в production daily pipeline, **надо определить тот сортировщик, который мы зафиксировали как рабочий**.

Я бы сейчас **не писал pipeline**, пока не проверим это. Давай найдём точку, где сейчас запускается именно рабочая daily-сортировка:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -RniE 'sort_sequence_v39|sort_sequence_v38|sort_test_and_report_hybrid_v12|20260818|data/output/daily' \
scripts app --include="*.py" 2>/dev/null | head -200
```

По этому выводу сразу определим **какой сортировщик является нашим текущим production-вариантом**, и уже его подключим к параллельному Qwen.

---

### 👤 **User** — 2026-08-18 20:24:14

Хотя наверно, можно сделать так:
1) процесс стартует, дино определяет адрес 
2) присваивается имя в соответствии со слепком - файлу дописывается имя к его имени 
3) файлы виртуально сортируются
4) создаются превью в аутпут 
5) параллельно свою работу выполняет квен описание 
6) файлы остаются там где и были с изменнными названиями (хотя можно предусмотреть вdry run)
7) превью, логи, джейсоны, кеши и хеши в аутпуте.
8) грид работает уже сразу , хотя скорее вскго в момент обработки спользрваться проект не будет

---

