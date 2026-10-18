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
9a. чтение даты съёмки из EXIF (кадр 0): `DateTimeOriginal` из Exif sub-IFD (`ExifOffset 0x8769`), fallback `DateTimeDigitized` из того же IFD, затем `DateTime` (`0x0132`) из 0-го IFD — порядок важен, потому что камерные JPEG обычно держат `DateTimeOriginal` именно в под-IFD, а не в 0-м; best-effort: отсутствие или поломка EXIF не влияет на `integrity_status`;
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
- `taken_at` (ISO-строка или `NULL`);
- `decoded`;
- `integrity_status`;
- `error`.

Модуль работает read-only.

Он не создает JPEG-копии, preview или другие производные файлы.

Для MPO визуальным источником является frame 0, но физический исходный MPO-файл не изменяется.

`discover_files()` обходит папку **рекурсивно по умолчанию** (`recursive=False` — только верхний уровень), отбирает `.jpg`/`.jpeg`, результат отсортирован. `scan_directory()` считает фото и суммарный объём без чтения содержимого — это то, что вызывает окно выбора папки.

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

`run(directory, workers, *, recursive=True, skip_known=None)`:

- обнаруживает файлы через `discover_files()`;
- если файлов нет, возвращает пустой `IngestResult`;
- при `skip_known` — вызывающая сторона передаёт функцию, которая по списку пар `(имя, размер)` возвращает уже зарегистрированные; такие файлы помечаются `SKIPPED` и **не читаются и не хешируются** (сам доступ к БД в `pipeline.py` не встроен — это сохраняет модуль независимым от PostgreSQL);
- запускает `process_file()` для каждого оставшегося файла;
- `VALID` результат формируется через `valid_result()`;
- исключение при обработке конкретного файла преобразуется в `INVALID` через `invalid_result()`;
- ошибка одного файла не останавливает обработку остальных файлов;
- возвращает итоговый `IngestResult` со счётчиками `VALID`/`INVALID`/`SKIPPED`.

### app/ingest/runner.py

Обход папки целиком — общий путь для CLI и для задания воркера:

    папка → pipeline.run (пропуск известных)
          → check_identity_batch → INSERT только NEW

`ingest_directory(directory, *, workers, skip_known=True, recursive=True)` возвращает JSON-совместимую сводку: `discovered`, `counters`, `registered`, `existing`, `conflicts`, `errors`. Конфликты **не прерывают** обход (в отличие от `register_new_photos()`, который используется на пути загрузки) — они возвращаются списком `photo_id`.

Команда CLI:

    scene-fingerprint ingest <папка> [--workers N] [--no-skip] [--no-recursive]

Через API то же самое делает `POST /v1/ingest/run` (задание `INGEST_DIR`, выполняется воркером). **Пропуск по паре (имя, размер) — только ускорение:** решение о записи по-прежнему принимает проверка `sha256` (NEW/EXISTING/CONFLICT). Компромисс: другой файл с тем же именем и ровно тем же размером будет пропущен; отключается флагом `--no-skip`.

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

После регистрации `NEW` записей общий `ingest_directory()` ставит отдельный `PHOTO_PREVIEW` job на каждый `photo_id`. Он использует уже зарегистрированную строку, а CPU-генерация выполняется выделенным `scene-preview-worker` через существующий `app/preview/pipeline.py`; `INGEST_DIR` не ждёт генерацию, и PREVIEW не ждёт DINO/HYBRID/QWEN. Синхронный upload также ставит PREVIEW job после успешной регистрации. Ошибка постановки задания возвращается в ingest summary/upload result, но не отменяет уже подтверждённую регистрацию. Смотрите `docs/preview.txt` и `deploy/systemd/README.md` для настройки воркера и ограниченного backfill.

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

Текущий photo pipeline не выполняет автоматическую запись в PostgreSQL.

DATABASE IDENTITY CHECK и последующая регистрация новых объектов являются отдельным слоем.

## 7. INGEST видео (новый отдельный домен)

Папочный `INGEST_DIR` теперь дополнительно находит video-файлы и обрабатывает их отдельной веткой; JPEG/MPO pipeline и таблица `public.photos` остаются без изменений.

Поддерживаемые расширения: `.mp4`, `.m4v`, `.mov`, `.mpeg`, `.mpg` (регистр не важен). Расширение служит только предварительным фильтром: содержимое и metadata проверяются `ffprobe`; INGEST использует только stat, не вычисляет hash содержимого и не читает видео целиком. Новые ID — `VI_` + первые 24 hex SHA-256 от однозначно сериализованных `[basename, UTC-дата YYYY-MM-DD, size_bytes]`; дата берётся из embedded `creation_time`, при отсутствии — UTC-день mtime. Поэтому одинаковые имя/дата/размер имеют одинаковый ID даже при разных bytes. Зарегистрированные до migration 041 строки и их старые content-SHA ID сохраняются без rewrite.

Регистрация и отображение не ограничены размером/длительностью. Для metadata probe задаётся `SCENE_INGEST_PROBE_TIMEOUT` (по умолчанию 60 секунд); бинарники — `SCENE_FFPROBE_BIN=/usr/bin/ffprobe`, `SCENE_FFMPEG_BIN=/usr/bin/ffmpeg`. Лимиты ingest `SCENE_INGEST_MAX_VIDEO_BYTES` и `SCENE_INGEST_MAX_VIDEO_SECONDS` больше не применяются. Отдельные пределы операций редактирования описаны в `docs/video.md`.

`video_assets` (`schema/026_video_assets.sql` + additive `schema/041_video_registered_derivatives.sql`) хранит отдельную video identity, контейнер/кодек, разрешение, длительность, fps, число кадров (NULL, если источник не сообщает), размер файла, best-effort `taken_at` из creation_time и `created_at` как время регистрации. Metadata identity hash и identity date хранятся отдельно от `sha256`; в новых rows `sha256` остаётся NULL, legacy content-SHA значения не переписываются. При отсутствии creation_time `taken_at` остаётся NULL (mtime используется только как fallback для identity date); файл не получает выдуманную дату съёмки.

Сводка `ingest_directory()` сохраняет прежние photo-поля и добавляет `videos` со счётчиками `discovered/valid/invalid/registered/existing`, конфликтами и ограниченным списком ошибок. Повторное сканирование новых видео использует metadata identity; legacy assets по возможности повторно сопоставляются по исходному пути и зарегистрированным метаданным без изменения старого ID. Ни `VIDEO` записи, ни derivatives не вставляются в `photos`; DINO, HYBRID, QWEN, photo-preview и fingerprint-build jobs для видео не создаются.

Для запуска нужен установленный runtime `ffmpeg`/`ffprobe`, видимый сервисам systemd. Если бинарь отсутствует, видео попадёт в INVALID с понятной ошибкой, фото-ingest продолжится. Для зарегистрированного видео INGEST best-effort создаёт poster JPEG по `video_id` в `SCENE_VIDEO_PREVIEW_ROOT` (по умолчанию `<SCENE_PREVIEW_ROOT>/videos`); это производный файл, оригинал не меняется. Ошибка poster не отменяет регистрацию видео.

### 7.1 Предварительная проверка папки

Кнопка «Проверить» вызывает `POST /v1/ingest/scan`; синхронный обход считает
поддержанные фото **и видео**, но не декодирует файлы и не пишет в БД. Ответ
содержит:

- `photos`, `videos`, `media_files`; `files` сохранён как прежнее photo-only
  поле для совместимости;
- `bytes`, `photo_bytes`, `video_bytes`;
- `extensions` — количество по каждому поддержанному расширению;
- `problem_count` и `problems` — до 20 примеров пустых/нечитаемых файлов
  (только имя и причина, без абсолютного пути);
- `preliminary=true` и `truncated`/`timed_out`.

Обход ограничен `SCENE_SOURCE_SCAN_LIMIT` (файлов) и
`SCENE_SOURCE_SCAN_TIMEOUT` (секунд, по умолчанию 10). Если лимит достигнут,
UI показывает предупреждение и не выдаёт частичный результат за полный. Полная
проверка целостности фото (`Pillow.verify` + decode) и видео (`ffprobe` +
`ffmpeg -xerror`) выполняется только в фоновом `INGEST_DIR`; её ошибки попадают
в результат задания и общий лог запуска.

Миграции `026`–`030` (video assets, playback tickets, derivatives, transcode/trim)
применены к рабочей БД; см. фактический rollout в `docs/video.md`.

## Параллельный INGEST и идентичность

Два обхода одной папки (например, ручной «Сканировать» во время «Обновления
базы») могут одновременно увидеть файл как новый. Вставка выполняется с
`INSERT ... ON CONFLICT DO NOTHING RETURNING photo_id`: проигравший в гонке не
получает `UniqueViolation`, его запись переклассифицируется в `EXISTING`, и
повторное задание PREVIEW для неё не ставится. Раньше в этом случае падала вся
транзакция и стадия INGEST помечала прогон ошибкой.

## Вкладка «Загрузка» в техническом разделе

Дата: 2026-10-17

- **Выбор папки** — два способа: «Выбрать на сервере» (встроенный браузер
  каталогов, `GET /v1/fingerprints/browse`) и «Системное окно» (zenity на
  машине сервера, включается `SCENE_NATIVE_PICKER=1`). Путь можно ввести
  вручную. Для папки на личном ПК указывается её сетевой/смонтированный путь
  на сервере.
- **Кнопки** «Проверить» и «Сканировать» активны сразу после выбора пути.
  «Проверить» — предварительная оценка (состав/размеры без декодирования);
  «Сканировать» ставит задание `INGEST_DIR`.
- **Блок статистики справа**: фото, видео, суммарный вес, число файлов с
  ошибками, количество по расширениям.
- **Итог проверки**:
  - без ошибок — зелёный баннер «Всё ОК» и «Переходите к этапу „Сортировка"»;
  - с ошибками — оранжевый баннер «ОК, но есть ошибки: N» с кнопками
    «Лог ошибок» (диалог с файлом и причиной), «Пересканировать» и
    «Пропустить и сканировать».
- Лимиты предпросмотра (`truncated`/`timed_out`) показываются отдельными
  предупреждениями; полную проверку целостности выполняет фоновый INGEST.
