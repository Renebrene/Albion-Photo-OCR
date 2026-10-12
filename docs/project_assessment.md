# Scene Fingerprint / PhotoBAse — анализ и план развития

**Статус:** read-only анализ существующей реализации и проектные рекомендации. Прототип FastAPI/Vue/Quasar в этой работе **не создавался**; API-контракт в `api_target.yaml` — целевой проект, не существующий API.

## 1. Краткое резюме

Репозиторий содержит Python-систему распознавания сцен по визуальным fingerprint с текущим UI на NiceGUI, CLI, набором компонентов INGEST/PREVIEW и отдельными DINO/HYBRID pipeline. PostgreSQL используется для сохранения исходной идентичности, preview, результатов DINO и HYBRID. Основные оригиналы обрабатываются как read-only.

Ключевой архитектурный принцип — отделить **физическую идентичность фото** от вычислительных выводов: SHA-256 определяет неизменную идентичность `photo_id`; DINO формирует первичных кандидатов; HYBRID оценивает последовательность/соседство по сохранённым результатам; PREVIEW отвечает только за производные изображения интерфейса. PostgreSQL должен быть контрольной точкой между этапами.

Главный gap: указанная целевая архитектура FastAPI + Vue/Quasar ещё не является фактической архитектурой checkout. В `app/main.py` находится NiceGUI и только веб-страница `/`; в основной рабочей копии не обнаружено опубликованных REST endpoints, аутентификации/авторизации или Pydantic схем `IngestFileResult`/`IngestResult`. Поэтому будущий UI и API надо проектировать отдельным тонким слоем поверх проверенных сервисов, не заявляя уже реализованный функционал.

## 2. Область и уверенность

Исследованы исходники `app/core`, `app/ingest`, `app/preview`, `app/dino`, `app/hybrid`, `app/pipeline`, SQL `schema/001`–`005`, `docs/` и архивные обсуждения `111/chatgpt_md/`. Архивные разговоры — источник UX идей и истории решений, но не актуальный контракт: в них есть старые версии, повторы и предложения, часть которых расходится с кодом.

На момент анализа рабочее дерево имело пользовательские untracked компоненты/данные в `111/`, `app/dino/`, `app/hybrid/`, `test/`, `.claude/`, `docs/dino.txt`, `docs/hybrid.txt`, `schema/003`–`005`. Их содержимое не изменялось. Каталог `test/` содержит фотографии, а не подтверждённый Python test suite. Проверки, способные запускать обработчики, писать в PostgreSQL или менять файлы, не выполнялись.

## 3. Компоненты и фактическое состояние

| Компонент | Назначение | Источник / состояние |
|---|---|---|
| NiceGUI UI | Создание fingerprint, распознавание папки, просмотр базы fingerprint | `app/main.py`; тяжелые `SceneEmbedder`, `FingerprintManager`, `SceneRecognizer` создаются при импорте модуля |
| CLI | Операции с fingerprint, очередью, анализом и распознаванием | `app/cli.py`; команды INGEST/PREVIEW/DINO/HYBRID как полноценное orchestration API не обнаружены |
| Core | DINOv2 embeddings, fingerprint storage, compact descriptors, recognition | `app/core/embedder.py`, `fingerprint.py`, `scene_analyzer.py`, `recognizer.py` |
| INGEST | Обнаружить JPG/JPEG, проверить, вычислить SHA-256, сформировать идентичность и результат | `app/ingest/*`, подробная спецификация `docs/ingest.md` |
| PostgreSQL INGEST | Проверка `NEW`/`EXISTING`/`CONFLICT`, регистрация | `app/ingest/database.py`, `schema/001_ingest.sql`; отдельно от `pipeline.run()` |
| PREVIEW | SMALL/MIDDLE JPEG, валидатор, DB upsert | `app/preview/*`, `docs/preview.txt`, `schema/002_preview.sql` |
| DINO | Неизменяемый batch, inference, TOP-5 и per-image results | `app/dino/*`, `docs/dino.txt`, схемы `003`–`004` |
| HYBRID | Финальный выбор по DINO результатам и последовательному контексту | `app/hybrid/*`, `docs/hybrid.txt`, `schema/005_hybrid.sql` |
| REST API | Целевая интеграция UI/сервисов | В основной копии endpoints не подтверждены; целевой контракт в `api_target.yaml` |
| Vue/Quasar UI | Целевой интерфейс к API | В checkout не обнаружено; UI рекомендации основаны на требованиях и архивных обсуждениях |

Зависимости зафиксированы в `pyproject.toml`: Python `>=3.12,<3.13`, NiceGUI, Torch/Torchvision, Pillow, NumPy, FAISS CPU, OpenCV, Transformers, PostgreSQL `psycopg` и другие. Указаны одновременно `opencv-python-headless` и `opencv-python`; оправданность/совместимость этих двух дистрибутивов следует проверить при стандартизации окружения.

## 4. Алгоритмы и потоки данных

### 4.1 INGEST: идентичность и целостность

Документированный поток: `DISCOVER → INTEGRITY → IDENTITY → REGISTER → RESULT` (`docs/ingest.md`). В коде обнаружение ограничено непосредственными файлами выбранной папки, расширениями `.jpg`/`.jpeg`; сортировка детерминирована, рекурсивного поиска нет. Для каждого файла вычисляется SHA-256 всего физического файла чтением блоками 1 MiB; Pillow определяет контейнер/размеры/число кадров, делает `verify()`, затем файл открывается повторно и frame 0 фактически декодируется. Допустимые контейнеры — JPEG и MPO; оригинал read-only.

`photo_id = PH_<первые 24 hex-символа SHA-256>`. Полный digest сохраняется. Имя/путь/EXIF/размеры не влияют на ID; perceptual hashes не применяются. Для MPO физическая идентичность относится ко всему контейнеру, хотя визуальный кадр — frame 0.

`PhotoRecord`, `IngestFileResult` и `IngestResult` — frozen dataclasses, не Pydantic models (`app/ingest/register.py`, `result.py`). `IngestFileResult` имеет `source_path`, `filename`, `status`, optional `record`, optional `error`; `IngestResult` имеет `discovered`, `results`, `counters`. Статусы — `VALID`/`INVALID`. Ошибка конкретного файла представляется как INVALID, остальные результаты сохраняются.

Важный разрыв: `app/ingest/pipeline.py` не делает автоматически DB identity check/INSERT. Этот слой реализован отдельно в `app/ingest/database.py`; docs прямо фиксирует разделение. Нужен явно идемпотентный application service, который координирует pipeline и транзакционную регистрацию, а не смешивание ответственности с декодером файла.

### 4.2 PREVIEW

`PREVIEW` принимает зарегистрированный `PhotoRecord`, не создаёт `photo_id` и не сканирует filesystem как источник регистрации. JPEG использует исходное изображение, MPO — frame 0. Генерируются JPEG SMALL и MIDDLE в отдельном каталоге по именам `photo_id`, конфигурация в окружении; defaults 320/1280 px по большей стороне, без upscale. Для каждого результата — проверка файла, JPEG, Pillow `verify()`, повторное чтение и `load()`. Действия `CREATE`/`SKIP`/`REGENERATE` независимы для малой и средней версии; DB upsert допустим только если обе валидны. Исторические тестовые метрики в `docs/preview.txt` (256/256 READY) документированы, но в ходе этого анализа не повторялись.

Проверено на корпусе 256 фото: READY 256/256, errors 0; `SKIP` при существующих файлах, `REGENERATE` при порче, upsert в БД и чтение обратно работают. Уточнение по изоляции ошибок: ошибки уровня **изображения** изолированы — `_create_one` превращает их в `ERROR`-результат, и прогон продолжается (проверено записью с несуществующим `source_path`). Весь прогон останавливает только ошибка уровня **валидации** до чтения изображения (например, пустой `photo_id`) — тогда `pipeline.run` бросает `RuntimeError`. Ранее `database_skipped` всегда был `0` (upsert делался даже когда строка не менялась). **Исправлено (2026-10-12):** upsert выполняется только если строки в БД нет или она отличается, иначе результат учитывается как `database_skipped`. На корпусе из 256 записей повторный прогон даёт `db_updated=0, db_skipped=256`; покрыто интеграционными тестами. Осталось: публиковать preview атомарно (временный файл → валидация → публикация) — отдельный пункт.

### 4.3 DINO и HYBRID

Fingerprint v3.3 использует `facebook/dinov2-base` через Transformers, CLS embedding 768D, нормализацию. В `app/core/fingerprint.py` векторный поиск/ранжирование использует FAISS `IndexFlatIP(768)` по нормализованным векторам, поэтому inner product соответствует cosine similarity. Хранятся `faiss.index`, `embeddings.npy`, centroid, representatives, compact descriptors и metadata с версией. `imagehash` объявлен зависимостью, но фактическое использование в основном коде не найдено.

Компактный descriptor: environment (640 значений), HSV color histogram (48), spatial grayscale grid (32), изображение нормализуется до 128×128 в `app/core/scene_analyzer.py`. Recognition возвращает TOP-K, scores и margin между первым/вторым кандидатом. Классы confidence (`HIGH`, `PROBABLE`, `AMBIGUOUS`, `NO_MATCH`) зависят от абсолютного score и margin. В коде `recognizer.py` есть противоречие между комментарием «threshold no longer rejection gate» и фактической логикой: при `best_score < threshold` выбирается `best_id=None`/`NO_MATCH`. Это требует тестируемого решения контракта до UI/API.

По `docs/dino.txt`, PostgreSQL фиксирует состав DINO batch; новые фото не меняют уже созданный batch, результаты записываются на элемент и сохраняют историю rerun. HYBRID должен читать только сохранённые DINO результаты, не читать original, не выполнять повторный DINO и принимать только полностью успешный batch. Ранее `finish_batch` переводил batch в `DONE` при отсутствии активных задач даже при `failed_count > 0`, что противоречило `docs/dino.txt` §18/§26 и позволяло HYBRID запуск на неполном наборе. **Исправлено**: batch становится `FAILED` при любом провале, а `hybrid.create_run` дополнительно требует `failed_count == 0` и `completed_count == total_count`; покрыто интеграционными тестами на PostgreSQL.

В HYBRID runner зафиксирована эвристика: TOP-5 DINO candidates, соседская корректировка; конкретные веса — DINO score ×10 и neighbor bonus 3, switch gain 1.5. Это эвристика, а не вероятностно откалиброванная confidence; требуется benchmark на размеченных последовательностях и версия алгоритма в истории запуска.

## 5. API, модели, доступ и ошибки

### 5.1 Текущее состояние

`app/main.py` поднимает NiceGUI с UI; обнаружен только `@ui.page('/')`. Ни HTTP API routes, ни документированного access control/RBAC/Bearer auth в главной копии не подтверждено. Поэтому сервис нельзя безопасно выставлять в сеть только на основании текущего UI. Незавершенный FastAPI-каркас, встречающийся в локальном worktree, не считается частью текущего продукта/контракта.

Целевые API для будущей разработки определены в `api_target.yaml`: `/health`, `/v1/ingest`, `/v1/photos/{photo_id}`, `/v1/search`, `/v1/batches/dino`, `/v1/batches/{batch_id}`, `/v1/batches/{batch_id}/hybrid`, `/v1/previews/{photo_id}/{size}`. Это proposal, endpoints не реализованы.

### 5.2 Контракты

Текущие `IngestFileResult` и `IngestResult` описаны выше; любой сериализуемый HTTP response следует определить отдельными Pydantic DTO и версионировать. Не сериализовать произвольные исключения/локальные пути без явной политики. Рекомендуемая ошибка — стабильный envelope (`code`, `message`, `request_id`, optional field errors), с HTTP статусом и без stack trace/секретов.

Целевые статусы: 400 malformed parameters; 401 unauthenticated; 403 scope denied; 404 unknown photo/batch; 409 duplicate/identity conflict/not-ready state; 413 upload too large; 415 unsupported media; 422 corrupt image/invalid fields; 429 rate limit; 500 opaque server error; 503 dependency unavailable. Конкретные детали — в OpenAPI.

### 5.3 Авторизация и безопасность (требуется спроектировать)

- private-network deployments: OIDC/OAuth2 bearer tokens; scopes разделить на `photos:read`, `ingest:write`, `jobs:write`, `jobs:read`, `admin`; принцип минимальных прав.
- не доверять `source_path` от клиента. Upload должен идти в quarantine с лимитом размера, allowlist MIME/формата, Pillow decode/verify и запретом архивов/path traversal; оригинал не перезаписывать.
- секреты PostgreSQL только из secret store/env для локальной разработки; не логировать пароли, токены, исходный абсолютный путь или EXIF по умолчанию.
- ограничить размер/число файлов, concurrent jobs, timeout, rate limit; запуск тяжёлых inference jobs через durable worker, не event loop.
- закрыть CORS по известным UI origins; TLS/reverse proxy, security headers, CSRF если cookie auth; SQL только параметризованный; preview отдавать только для разрешённых фото и безопасным content type.
- аудит actor/request/job/run_id, но не сохранять содержимое изображения в логи; изоляция tenant/owner если мультипользовательский сценарий.

## 6. Визуальное решение и UX

Архив `111/chatgpt_md/` содержит исторические обсуждения, не единый утверждённый UX контракт. Согласующиеся предложения: GRID — только после действия пользователя или готового фильтра; preview вместо загрузки originals в карточки; ленивое получение, ограниченная выдача порядка ~100 элементов, пагинация/cursor; клик по карточке — просмотр original только при праве доступа. Фильтры: address, client, date, collection/search; подборки хранят идентификаторы/условия, saved search хранит запрос, а не копию выдачи. UI должен показывать статусы/время последнего фактического запуска, а не поддерживать ложный отдельный журнал.

Путь данных: оригиналы → DINO/HYBRID worker → DB/index → WEB GRID; UI не сортирует/копирует исходники и не пересчитывает распознавание. Для просмотра использовать SMALL/MIDDLE preview из `docs/preview.txt`, конкретный размер настраивать на этапе UX; original выдавать отдельным endpoint с авторизацией. Qwen/Qwen-VL может быть будущим вспомогательным языковым/описательным интерфейсом, но не блокировать базовый цикл. OCR в исторических заметках экспериментален и не включён в обязательный roadmap ядра.

## 7. Выявленные пробелы и приоритет улучшений

### P0 — корректность и безопасная эксплуатация

1. ~~Исправить согласование статусов DINO batch~~ **— исправлено (2026-10-12)**: `finish_batch` теперь `FAILED` при наличии провалов, `hybrid.create_run` требует `failed_count == 0` и `completed_count == total_count`. Подтверждено на реальном `run_batch` и интеграционными тестами. Осталось: покрыть гонки/повторные вызовы `finish_batch` отдельным тестом.
2. Проверить/сделать миграцию `004_dino_batches.sql` безопасной при существующих строках: `ADD batch_id` с `NOT NULL` без backfill может провалиться. Стратегия expand → backfill → validate → not-null с rollback и backup.
3. Однозначно определить threshold semantics в `SceneRecognizer`; убрать противоречивый комментарий и покрыть границы score/margin тестами.
4. Не выставлять текущую систему наружу как API без authn/authz, лимитов и безопасной выдачи файлов.
5. Изолировать тестовые данные/БД; проверить runbook на тестовой БД, прежде чем запускать текущие workers или SQL.

### P1 — устойчивость, производительность, эксплуатация

1. Сделать pipeline coordinator, который объединяет ingest validation и DB registration, при этом сохраняет чистые unit-компоненты; уникальный `sha256`/`photo_id` должен быть idempotent, конфликты явно классифицировать.
2. Добавить транзакционный batch workflow, retry policy, cancellation, lease/heartbeat и recovery незавершенных `PENDING/RUNNING`; фиксированные snapshots должны сохранять порядок/версию.
3. Измерить DINO inference и CPU postprocessing; текущая потенциальная проблема — модель/shared embedder в ThreadPool, не считать `workers` ускорением без измерений. Контролировать oversubscription BLAS/OpenMP/Torch.
4. Кэшировать query embeddings/compact descriptors в течение одного recognition request; исторические записи упоминают лишнее повторение DINO inference при сравнении кандидатов. Отдельно профилировать disk IO и загрузку fingerprint.
5. ~~Атомарная публикация артефактов~~ **частично исправлено (2026-10-12)**: `FingerprintManager.create()` строит слепок во временном каталоге и публикует через `os.replace`; при сбое частичный слепок не остаётся и повторный запуск не блокируется. Осталось: то же для PREVIEW (запись JPEG через временный файл → валидация → публикация).
6. Индексы/пагинация для поиска; проверить размер и рост FAISS index, версионирование embeddings/model/preprocessing; benchmark exact `IndexFlatIP` vs допустимые ANN решения без утраты нужной recall.
7. ~~Исправить метрики `database_skipped` и лишний upsert в PREVIEW~~ **— исправлено (2026-10-12)**: upsert только при отсутствии/расхождении строки, иначе `database_skipped`. Таймер `dino_time_sec` при ошибке исправлен ранее. Осталось: сообщения об ошибках без утечки локального пути.
8. Сформировать CI: unit-тесты algorithms/DTO/state machine; integration tests только на disposable PostgreSQL; dependency lock/security scan; migration validation и coverage.

## 8. Roadmap

### Этап 0 — стабилизация и тестируемость

Зафиксировать текущие API/DTO и DB state machine; определить инварианты batch; закрыть P0 дефекты и миграционный сценарий; создать набор синтетических fixtures без персональных исходных фото; unit + disposable PostgreSQL integration tests.

### Этап 1 — backend вертикальный срез

FastAPI application factory, routers, Pydantic v2 request/response DTO, сервисный слой и PostgreSQL repository; отдельное тестовое окружение/схема; auth scopes; загрузка в quarantine, асинхронный job/batch status, cursor search, preview endpoint. Сохранить существующий Python core, не встраивать тяжелый inference в request loop. Все новые миграции backwards-compatible.

### Этап 2 — Vue 3 + Quasar GRID и рабочие процессы

Сначала фото GRID с preview, безопасным просмотром, фильтрами и серверной cursor pagination; далее экран batches/status/errors, создание normal/force rerun по правам. UX доступность клавиатуры, адаптивность, пустые/loading/error states, понятные подтверждения destructive/admin действий.

### Этап 3 — production hardening и rollout

Наблюдаемость (structured logs, metrics, tracing), нагрузочные тесты и ресурсные budgets GPU/CPU, backup/restore, RBAC review, staging runbook, shadow/limited rollout. Переключение с NiceGUI только после сравнения сценариев и возможности отката.

### Этап 4 — управляемые подборки и поиск

Saved searches, collections, multi-query AND/OR, фильтрация по адресам/клиентам/дате/категориям после нормализации метаданных. Любой Qwen/LLM подключать как помощник над DB/поиском с проверяемыми действиями, не как authority для регистрации идентичности.

## 9. Рекомендуемые решения и trade-offs

| Решение | Выгода | Цена/ограничение |
|---|---|---|
| PostgreSQL — источник состояния batch и истории | Надёжное восстановление после рестарта, auditability | Нужно дисциплинированное управление транзакциями/lock и DB migrations |
| Async job API + worker вместо синхронного HTTP inference | Масштабируемость, стабильные таймауты, наблюдаемость | Очередь/состояния/отмена усложняют MVP |
| SHA-256 full-file identity | Точная повторяемая физическая идентичность и integrity | Дубликаты после преобразования/пересохранения не распознаются как те же файлы; это отдельная perceptual lookup задача |
| Exact FAISS IndexFlatIP сначала | Простота и точный baseline | Поиск линейный по числу эталонных векторов; ANN выбирать только после профиля/recall target |
| Vue/Quasar отдельно от core | UI не привязан к Python runtime, пригоден к росту | Два toolchain и API DTO требуют поддержки |
| Отдельные SMALL/MIDDLE preview | Быстрые grid и viewer, оригинал не загружается всегда | Дополнительное дисковое место и consistency lifecycle |
| Версионированные immutable runs | Воспроизводимость сравнения алгоритмов | Рост таблиц, нужна retention/archive policy |

## 10. Ссылки на исходники

- `app/main.py`, `app/cli.py` — действующее приложение и CLI.
- `app/core/embedder.py`, `fingerprint.py`, `recognizer.py`, `scene_analyzer.py`, `image.py` — embeddings, storage, similarity и descriptors.
- `app/ingest/integrity.py`, `identity.py`, `register.py`, `result.py`, `pipeline.py`, `database.py` — INGEST.
- `app/preview/generator.py`, `validator.py`, `pipeline.py`, `database.py` — PREVIEW.
- `app/dino/runner.py`, `database.py`, `app/hybrid/runner.py`, `database.py` — DINO/HYBRID.
- `schema/001_ingest.sql` … `schema/005_hybrid.sql` — схема PostgreSQL; сначала проверить миграционный порядок и существующие данные.
- `docs/ingest.md`, `docs/preview.txt`, `docs/dino.txt`, `docs/hybrid.txt` — архитектурные решения/оговорки.
- `111/chatgpt_md/` — исторический контекст UX и экспериментов, не нормативная спецификация.

## 11. Связанные материалы

- Целевая схема: [`architecture_target.mmd`](architecture_target.mmd)
- Целевой REST/OpenAPI контракт: [`api_target.yaml`](api_target.yaml)
- ТЗ и критерии приёмки: [`future_implementation_tz.md`](future_implementation_tz.md)
