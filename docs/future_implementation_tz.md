# Техническое задание: PhotoBAse Web API и интерфейс

**Тип документа:** проектное ТЗ, не описание существующей функциональности. Выполнение реализации не входит в текущий этап анализа. API-контракт — `api_target.yaml`; схема процессов — `architecture_target.mmd`.

## 1. Цель

Добавить безопасный и поддерживаемый web-слой для текущих алгоритмов Scene Fingerprint: FastAPI REST backend, Vue 3 + Quasar интерфейс и PostgreSQL для идентичности/состояния. Запускать вычислительные операции как управляемые jobs/workers, сохраняя существующие Python core компоненты и неизменяемую историю batch/run. Не переписывать признанный алгоритм в UI и не менять originals.

## 2. Границы первого релиза

Входит:

1. Безопасная загрузка JPEG/MPO и полный INSPECT lifecycle с DB identity check/insert.
2. Получение photo metadata и двух preview размеров.
3. Создание/статус неизменяемого DINO batch и запуск HYBRID строго для успешного batch.
4. Поиск/GRID с cursor pagination и базовыми фильтрами.
5. Vue/Quasar UI для GRID и процессов обработки с loading/empty/error состояния.
6. Authn/authz scopes, аудит, структурированные ошибки, тесты и disposable test PostgreSQL.

Не входит в релиз 1: OCR, Qwen как authority, автоматическое редактирование originals, массовое удаление, рекурсивная импортная библиотека без квот, физическая сортировка/копирование фотографий, автономное изменение алгоритмов по LLM. Qwen и сохранённые подборки — последующие опциональные этапы.

## 3. Пользовательские сценарии

- **Оператор загружает фото:** отправляет файлы, видит job id и статус, для каждого файла получает VALID/INVALID и NEW/EXISTING/CONFLICT без утечки локальных путей или внутренних исключений.
- **Пользователь просматривает GRID:** задаёт фильтры (address, client, collection, date, text), вручную запускает/обновляет выдачу, получает максимум 100 записей за запрос; видит preview и результатный статус.
- **Пользователь смотрит original:** открывает конкретное фото только после проверки права; endpoint выдаёт содержимое зарегистрированного source, не принимает клиентский путь.
- **Оператор запускает DINO:** создаёт NORMAL или FORCE_RERUN batch; состав фиксирован, видны total/completed/failed и состояние.
- **Оператор запускает HYBRID:** разрешено только для полностью успешно завершённого DINO batch; система создаёт отдельный новый HYBRID run и показывает его историю.
- **Пользователь анализирует результат:** видит TOP-5/score/margin/confidence/status и финальный HYBRID verdict, не предполагая, что низкая уверенность равна подтверждённому адресу.

## 4. Архитектурные требования

### 4.1 Backend

- FastAPI с app factory, versioned router (`/api/v1`), Pydantic DTOs, OpenAPI generation и сервисным слоем. Текущие dataclass results конвертировать на границе; не менять без необходимости pure algorithms.
- Отдельные adapters/repositories для PostgreSQL; драйвер psycopg поддерживать единообразные pool/transactions. Запросы параметризовать.
- HTTP request не должен держать долгую inference работу. Использовать durable queue/worker и сохранять job/batch state в PostgreSQL или согласованной устойчивой очереди; API отвечает `202` с status URL.
- Dependency injection для DB/session, auth principal и core services; не инициализировать GPU/model при импорте web module.
- Ошибки переводить в стабильный envelope с кодом и request_id; raw exception, SQL, token и stack trace не отдавать клиенту.
- Health/readiness отделить: liveness не обращаться к модели/БД; readiness описывает недоступные зависимости без секретов.

### 4.2 INSPECT / обработка изображения

- Разрешённые физические форматы и Pillow проверка должны соответствовать `docs/ingest.md`; декодировать ограниченно, учитывать decompression bomb, invalid frame и чрезмерные размеры.
- Максимальный размер файла, число файлов, job quota и timeout конфигурируются.
- Загрузка — в приватный quarantine, уникальное серверное имя; никакого доверия MIME/filename/path клиента. Исходник никогда не перезаписывать.
- Сначала полная проверка и SHA-256, затем transaction с unique constraint по полному sha256/photo_id. Повтор того же digest должен дать EXISTING идемпотентно; недопустимое различие атрибутов/коллизия — CONFLICT и audit event.
- Удаление quarantine/orphans — отдельная политика retention, не часть синхронного инспектирования.

### 4.3 DINO / HYBRID / PostgreSQL

- Изменения схем — последовательные, проверяемые, reversible где возможно; миграция существующей таблицы должна включать backfill до `NOT NULL`.
- Batch membership immutable после создания. Инварианты фиксировать constraint/transaction: DONE iff all expected work completed successfully, `failed_count=0`, нет PENDING/RUNNING; иначе FAILED. HYBRID start — атомарная проверка этих условий.
- Каждый rerun создаёт новую запись и сохраняет историю; применяемая версия модели/алгоритма/порогов входит в run metadata.
- Worker recovery: heartbeat/lease, ограниченные retry с backoff, terminal state и ручной rerun; stale RUNNING нельзя молча считать DONE.
- Поиск верхних кандидатов сохраняет ranking, scores и margin; pHash не подменяет SHA physical identity. Настроить benchmark точности/полноты на размеченном dataset.

### 4.4 Frontend: Vue + Quasar

- Экран **Фото**: фильтры и явная кнопка «Показать фотографии»/применить фильтры; GRID lazy loads cursor pages до 100 элементов; карточки используют SMALL preview, viewer — MIDDLE, original загружается отдельно.
- В карточке доступны filename, адрес/клиент/дата (если имеются), DINO/HYBRID статус и score с пояснением; пустые/ошибочные значения не должны вводить в заблуждение.
- Экран **Обработка**: действия INSPECT, NORMAL/FORCE_RERUN DINO, HYBRID; подтверждать дорогие/широкие операции; показывать запуск, batch id, прогресс и per-item ошибки. UI отражает server state и не хранит альтернативный журнал.
- Навигация/фильтры доступны клавиатуре; скринридер labels, контраст, responsive layout, clear loading/error/empty states. Подтверждённые сообщения на русском языке.
- Collection/saved search можно добавить отдельным этапом. Saved search хранит выражение условий, collection — набор photo_id; не копировать изображения.

## 5. Безопасность и приватность

1. OIDC/OAuth2/JWT либо инфраструктурный identity provider; scopes минимум `photos:read`, `ingest:write`, `jobs:read`, `jobs:write`, `admin`.
2. Разграничить просмотр результатов, загрузку и запуск повторной обработки. Проверять права также на preview и original media endpoints (IDOR protection).
3. CORS allowlist, TLS termination, безопасные cookie/CSRF если cookie auth, Content-Security-Policy и security headers.
4. Request/file quotas, rate limits, bounded worker concurrency, timeouts, decompression limits и backpressure.
5. SQL secrets через secret store; credentials отсутствуют в repo/log/API. Ротация ключей и DB role с минимальными правами.
6. Логи структурированные; redacted source path, EXIF, пользовательские metadata и tokens. Записывать actor, action, timestamp, resource/run id.
7. Не отдавать произвольные disk paths; file resolver строит доступ только по DB ID и проверенным root directories. Защита от path traversal/symlink escape.
8. Сроки хранения исходников/previews и права удаления определить до production; backup encrypted и проверять restore.

## 6. Предлагаемые API операции

См. `api_target.yaml`, включая примеры:

- `POST /api/v1/ingest` multipart → `202 job_id`;
- `GET /api/v1/jobs/{job_id}` → прогресс и результат per-file;
- `GET /api/v1/photos/{photo_id}` → metadata;
- `GET /api/v1/photos/{photo_id}/previews/{small|middle}` → JPEG;
- `GET /api/v1/search` → filters + cursor, limit ≤ 100;
- `POST /api/v1/batches/dino` → fixed batch;
- `GET /api/v1/batches/{batch_id}` → status/counts;
- `POST /api/v1/batches/{batch_id}/hybrid` → new HYBRID run только при DONE.

Публичный endpoint для original download, если нужен, следует добавить отдельным решением после определения scope/retention; он не должен принимать filesystem path.

## 7. Данные и миграции

Опираться на таблицы `photos`, `photo_previews`, DINO batches/runs/candidates, HYBRID runs/results из `schema/001_ingest.sql` – `005_hybrid.sql`; сначала провести migration review и утвердить единый migration runner. До выполнения `004_dino_batches.sql` проверить наличие строк; добавить безопасный backfill и детерминированную стратегию историческим run назначить batch либо остановить миграцию с понятной диагностикой.

Целевая схема должна дополнительно хранить/уточнить: `created_by`/tenant при multi-user, job idempotency key, request/run algorithm version, error code (без raw exception), updated_at/heartbeat, оптимизированные индексы поиска и cursor keys. Не добавлять поля адреса/клиента, пока их типы, источник и lifecycle не утверждены.

## 8. Нефункциональные требования / приемочные показатели

Точные SLO и объёмы определить нагрузочным профилем владельца; предложенные стартовые критерии:

- API metadata/search p95 ≤ 500 ms на staging dataset (без image inference), preview download p95 ≤ 1 s при локально доступных storage; зафиксировать dataset, infra и методику.
- Максимум 100 grid items на страницу; использование cursor pagination без полного сканирования таблицы.
- Веб-процесс не блокируется DINO; число одновременных inference ограничено конфигурацией.
- Повторная отправка idempotency key не создаёт повторные записи/jobs.
- Ошибка одного изображения не теряет исход остальных элементов batch.
- Восстановление после рестарта не переводит незавершённый/с ошибками batch в DONE.
- UI не загружает все full-resolution originals при открытии GRID.
- Ни один отрицательный тест безопасности не может читать unauthorized media/metadata или раскрывать секрет/абсолютный путь.

## 9. План реализации

1. **Стабилизация:** исправить/протестировать batch state, threshold semantics, timers, preview exception isolation/metrics; зафиксировать чистый Python service contract.
2. **Backend foundation:** app factory, config, auth, error schema, repositories, migration baseline, health/readiness и disposable PG integration fixtures.
3. **INSPECT vertical slice:** quarantine upload → validate/hash → identity check/register → job/result → тесты duplicate/corrupt/oversize.
4. **UI GRID:** API search/preview → Vue/Quasar grid, filters, pagination, viewer; usability/accessibility review.
5. **Batch control:** DINO job + progress/history; HYBRID gated start; recovery and retry.
6. **Hardening:** load/security tests, logs/metrics, backup/restore, staging rollout, operational docs; production rollout только после approve.
7. **Later:** collections/saved queries; LLM-assisted natural language search after role/access restrictions; no OCR unless отдельное бизнес-решение.

## 10. Definition of Done

- OpenAPI generation совпадает с вручную поддерживаемым контрактом; все ответы имеют DTO/пример и коды ошибок.
- Успешные и негативные unit/integration tests покрывают image, identity, duplicate/conflict, state transitions, authorization и media access.
- Migration tests проверяют чистую и populated test DB; миграция не запускается на production без backup/approval.
- Frontend E2E: upload, poll job, apply filters, page forward/back, image authorization, batch lifecycle; UI не инициирует скрытые повторные inference.
- Security review: auth scopes, IDOR, upload limits, path traversal, CORS, SQL parameters, secrets/logs.
- Документация запуска dev/staging, конфигурации, backup/restore и rollback; тесты проходят в CI.
- Existing NiceGUI flow не удаляется до проверенного parity и согласованного cutover.
