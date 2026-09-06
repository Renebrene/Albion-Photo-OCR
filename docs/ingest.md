# INGEST

## 1. Назначение

Модуль `INGEST` отвечает за первичную обработку исходных фотографий.

Основная задача INGEST — проверить физический исходный файл, определить его стабильную идентичность и сформировать структурированную запись фотографии.

INGEST работает с исходными файлами в режиме read-only.

Исходные фотографии не изменяются и не перезаписываются.

Для MPO-файлов физический исходный объект сохраняется целиком. Для визуальной проверки и декодирования используется frame 0.

## 2. Границы ответственности

INGEST отвечает за:

- обнаружение поддерживаемых исходных файлов;
- проверку существования и типа файла;
- проверку расширения;
- вычисление SHA-256 исходного физического файла;
- определение контейнерного формата;
- определение размеров изображения;
- определение количества кадров;
- проверку целостности через `Image.verify()`;
- фактическое декодирование frame 0;
- создание стабильного `photo_id`;
- формирование `PhotoRecord`;
- формирование структурированного результата обработки.

INGEST не отвечает за:

- распознавание содержимого фотографии;
- DINO / Hybrid;
- Qwen;
- OCR;
- описание изображения;
- определение адреса;
- определение клиента;
- сортировку фотографий;
- построение scene fingerprint;
- изменение исходных файлов.

Perceptual hash (`pHash`, `dHash`) не участвует в формировании `photo_id`.

## 3. Архитектура pipeline

Текущий pipeline INGEST выполняет:

DISCOVER → INTEGRITY → IDENTITY → REGISTER → PhotoRecord → RESULT

Где:

- `DISCOVER` — обнаружение поддерживаемых исходных файлов;
- `INTEGRITY` — проверка физического файла, SHA-256 и декодирования;
- `IDENTITY` — создание детерминированного `photo_id`;
- `REGISTER` — формирование неизменяемого `PhotoRecord`;
- `RESULT` — формирование `IngestFileResult` и итогового `IngestResult`.

Результат обработки файла:

- `VALID` — файл успешно прошел текущий pipeline INGEST;
- `INVALID` — обработка файла завершилась ошибкой.

DATABASE IDENTITY CHECK является отдельным слоем PostgreSQL:

PhotoRecord → DATABASE IDENTITY CHECK → NEW / EXISTING / CONFLICT → INSERT NEW

Текущий `pipeline.run()` не вызывает DATABASE IDENTITY CHECK автоматически.

## 4. Модули INGEST

### app/ingest/integrity.py

Модуль выполняет физическую проверку исходного файла.

Поддерживаемые расширения:

- `.jpg`
- `.jpeg`

Поддерживаемые контейнерные форматы:

- `JPEG`
- `MPO`

Для каждого файла выполняется:

1. проверка существования;
2. проверка, что объект является обычным файлом;
3. проверка расширения;
4. получение размера файла;
5. вычисление SHA-256 полного физического файла;
6. открытие изображения через Pillow;
7. определение контейнерного формата;
8. определение ширины и высоты;
9. определение количества кадров;
10. выполнение `Image.verify()`;
11. повторное открытие файла;
12. переход на frame 0 через `seek(0)`;
13. фактическое декодирование через `load()`.

Таким образом, `verify()` и фактическое декодирование выполняются отдельно.

Результат содержит:

- `filename`;
- `source_path`;
- `exists`;
- `is_file`;
- `extension_valid`;
- `size_bytes`;
- `sha256`;
- `container_format`;
- `width`;
- `height`;
- `frame_count`;
- `decoded`;
- `integrity_status`;
- `error`.

Модуль работает read-only.

Он не создает JPEG-копии, preview или другие производные файлы.

Для MPO визуальным источником является frame 0, но физический исходный MPO-файл не изменяется.

### app/ingest/identity.py

Модуль создает стабильную идентичность фотографии на основании SHA-256.

SHA-256 сначала нормализуется и проверяется как строка из 64 шестнадцатеричных символов.

`photo_id` формируется как:

    PH_<первые 24 символа SHA-256>

Например:

    SHA-256:
    c4a49077cb428c56ad682a36fcbd4c6d17e271a5af05fd990481bd33ce1520a6

    photo_id:
    PH_c4a49077cb428c56ad682a36

Идентичность зависит только от SHA-256 физического исходного файла.

Она не зависит от:

- имени файла;
- пути;
- EXIF;
- размеров изображения;
- frame 0;
- содержимого других кадров MPO.

Полный SHA-256 сохраняется в `PhotoIdentity`.

`pHash` и `dHash` в создании `photo_id` не участвуют.

Модуль не выполняет обращения к PostgreSQL.

### app/ingest/register.py

Модуль формирует неизменяемый `PhotoRecord`.

`PhotoRecord` содержит:

- `photo_id`;
- `source_path`;
- `filename`;
- `sha256`;
- `container_format`;
- `frame_count`;
- `width`;
- `height`.

Перед созданием записи проверяется:

- наличие `photo_id`;
- наличие `source_path`;
- наличие `filename`;
- наличие `sha256`;
- поддерживаемый формат `JPEG` или `MPO`;
- `frame_count >= 1`;
- `width >= 1`;
- `height >= 1`.

`PhotoRecord` является frozen dataclass.

Создание `PhotoRecord` не является записью в PostgreSQL.

Модуль не изменяет исходный файл.

### app/ingest/database.py

Модуль является отдельным PostgreSQL-слоем INGEST.

Параметры подключения читаются из переменных окружения:

- `INGEST_DB_HOST`, по умолчанию `localhost`;
- `INGEST_DB_PORT`, по умолчанию `5432`;
- `INGEST_DB_NAME`, по умолчанию `photobase_ingest_test`;
- `INGEST_DB_USER`, по умолчанию `lora_ingest`;
- `INGEST_DB_PASSWORD` — обязательная переменная.

Основная функция проверки:

`check_identity_batch()`

Она выполняет read-only проверку существующих записей в:

`public.photos`

Проверка выполняется одновременно по:

- `photo_id`;
- `sha256`.

Результат классифицируется на три состояния.

#### NEW

`NEW` означает, что в базе не найден:

- данный `photo_id`;
- данный `sha256`.

Такая запись считается новой.

#### EXISTING

`EXISTING` означает, что:

- найденный `photo_id` соответствует тому же SHA-256;
- найденный SHA-256 соответствует тому же `photo_id`.

То есть связь:

    photo_id ↔ sha256

полностью совпадает.

#### CONFLICT

`CONFLICT` возникает, если существующая идентичность не соответствует новой паре.

Например:

    существующий photo_id
    +
    другой SHA-256

или:

    существующий SHA-256
    +
    другой photo_id

`register_new_photos()`:

1. выполняет DATABASE IDENTITY CHECK;
2. прекращает операцию при наличии `CONFLICT`;
3. пропускает `EXISTING`;
4. вставляет только `NEW`.

Функция `insert_photos()` выполняет batch INSERT.

Функция `insert_photo()` выполняет одиночный INSERT.

В таблице `public.photos` поле `created_at` имеет значение по умолчанию `CURRENT_TIMESTAMP`, поэтому текущие INSERT-запросы его отдельно не передают.

Важно:

`database.py` является отдельным слоем и не вызывается автоматически из `pipeline.run()`.

### app/ingest/result.py

Модуль формирует структурированный результат INGEST.

`IngestFileResult` содержит:

- `source_path`;
- `filename`;
- `status`;
- `record`;
- `error`.

Для успешного результата:

    status = VALID
    record = PhotoRecord
    error = None

Для ошибочного результата:

    status = INVALID
    record = None
    error = описание ошибки

`IngestResult` содержит:

- `discovered`;
- `results`;
- `counters`.

`counters` содержит количество:

- `VALID`;
- `INVALID`.

Для каждого обнаруженного файла формируется один `IngestFileResult`.

Оба dataclass являются frozen.

### app/ingest/pipeline.py

`process_file()` выполняет последовательность:

    Path
     ↓
    check_file()
     ↓
    create_identity()
     ↓
    register_photo()
     ↓
    PhotoRecord

Если INTEGRITY завершается с ошибкой, конкретный файл преобразуется в ошибочный результат.

Параллельная обработка выполняется через:

    ProcessPoolExecutor

Количество workers по умолчанию определяется как:

    max(1, os.cpu_count() // 2)

То есть используется половина доступных логических CPU-потоков, но минимум один worker.

Значение можно передать явно через `workers`.

При:

    workers < 1

возникает `ValueError`.

`run(directory, workers)`:

- обнаруживает файлы через `discover_files()`;
- если файлов нет, возвращает пустой `IngestResult`;
- запускает `process_file()` для каждого обнаруженного файла;
- `VALID` результат формируется через `valid_result()`;
- исключение при обработке конкретного файла преобразуется в `INVALID` через `invalid_result()`;
- ошибка одного файла не останавливает обработку остальных файлов;
- возвращает итоговый `IngestResult`.

Порядок результатов:

- futures сопоставляются с исходным списком `files`;
- результат каждого файла добавляется в том же порядке, в котором файл был обнаружен;
- для каждого обнаруженного файла формируется ровно один `IngestFileResult`.

Read-only правило:

- `pipeline.py` не записывает ничего обратно в source-файлы;
- `process_file()` только читает исходный файл и формирует объекты данных;
- создание `PhotoRecord` не является изменением физического source-файла.

Важное архитектурное ограничение текущей реализации:

- `pipeline.py` НЕ вызывает `database.check_identity_batch()`;
- `pipeline.py` НЕ вызывает `database.register_new_photos()`;
- `pipeline.py` НЕ выполняет `NEW / EXISTING / CONFLICT` внутри `run()`;
- поэтому текущий `run()` завершается формированием `IngestResult`, а не регистрацией в PostgreSQL;
- PostgreSQL DATABASE IDENTITY CHECK является отдельным слоем `app/ingest/database.py`.

Итоговая фактическая архитектура текущего INGEST:

    DISCOVER
    → INTEGRITY
    → IDENTITY
    → REGISTER
    → RESULT

Отдельный слой:

    PhotoRecord
    → DATABASE IDENTITY CHECK
    → NEW / EXISTING / CONFLICT
    → INSERT NEW

## 5. Верификация INGEST

На тестовом наборе:

    /home/alexice/Desktop/test

pipeline INGEST успешно обработал 256 файлов.

Результат:

    VALID:   256
    INVALID: 0

Распределение контейнеров:

    MPO:  255
    JPEG: 1

Распределение кадров:

    2 frame(s): 255
    1 frame(s): 1

JPEG decode verification успешно пройдена для всех 256 файлов.

Повторный запуск pipeline дал:

    run1: {'VALID': 256, 'INVALID': 0}
    run2: {'VALID': 256, 'INVALID': 0}

    same_count: True
    same_ids: True

Это подтверждает детерминированность формирования `photo_id` и одинаковый результат повторной обработки.

На фактической машине:

    REAL CPU THREADS: 12
    INGEST DEFAULT WORKERS: 6

Это соответствует формуле:

    max(1, os.cpu_count() // 2)

### DATABASE IDENTITY CHECK

Подключение к PostgreSQL:

    photobase_ingest_test

через роль:

    lora_ingest

успешно проверено.

На реальном PostgreSQL подтверждены все три состояния.

#### NEW

Для искусственно созданной новой пары `photo_id + sha256`:

    NEW       = 1
    EXISTING  = 0
    CONFLICT  = 0

Результат:

    NEW: PH_TEST_NEW_20260906 | ingest_test_new.JPG

#### EXISTING

Для существующей фотографии:

    photo_id = PH_c4a49077cb428c56ad682a36
    filename = Ашхабадский_01.JPG

получен результат:

    NEW       = 0
    EXISTING  = 1
    CONFLICT  = 0

#### CONFLICT

Для существующего `photo_id` с другим SHA-256:

    NEW       = 0
    EXISTING  = 0
    CONFLICT  = 1

Результат:

    CONFLICT: PH_c4a49077cb428c56ad682a36 | ingest_test_conflict.JPG

Таким образом, логика:

    NEW / EXISTING / CONFLICT

в `app/ingest/database.py` подтверждена на реальном PostgreSQL.

Все проверки DATABASE IDENTITY CHECK выполнялись без `INSERT`.

## 6. Текущее состояние INGEST

Текущая реализация INGEST подтверждена по основным слоям:

    DISCOVER       ✓
    INTEGRITY      ✓
    IDENTITY       ✓
    REGISTER       ✓
    RESULT         ✓
    PIPELINE       ✓
    DATABASE       ✓
    NEW            ✓
    EXISTING       ✓
    CONFLICT       ✓

Физические исходные фотографии при выполнении INGEST не изменяются.

Текущий pipeline не выполняет автоматическую запись в PostgreSQL.

DATABASE IDENTITY CHECK и последующая регистрация новых объектов являются отдельным слоем.
