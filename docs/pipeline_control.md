# Супервизор пайплайна (resumable pipeline run)

**Статус:** развёрнуто 2026-10-16. Миграция `031` применена к
`photobase_ingest_test` (после backup и проверки в изолированной схеме),
`scene-api` перезапущен (маршруты `/v1/pipeline/*` активны),
`scene-pipeline-worker.service` установлен и включён. Сквозной smoke без
реальной обработки прошёл.

## Зачем

Кнопка «Обновление базы» должна запускать один управляемый прогон
**INGEST → PREVIEW → DINO → HYBRID → QWEN**, показывать прогресс по стадиям,
уметь остановиться и продолжиться с того же места, не подхватывая новые файлы,
и сохранять историю запусков в БД в реальном времени.

Супервизор — тонкий оркестратор. Он **не** запускает inference и **не**
переписывает раннеры DINO/HYBRID/QWEN: на каждом тике он ставит в очередь те же
задачи, что и ручные сценарии (`INGEST_DIR`, `PHOTO_PREVIEW`, `DINO_BATCH`,
`HYBRID_RUN`, `QWEN_PHOTO`), и переходит к следующей стадии, когда работа
текущей завершена.

## Модель данных (schema/031)

- `pipeline_runs` — запуск: `mode` (`manual`/`schedule`/`outofqueue`), `status`
  (`PENDING`/`RUNNING`/`STOPPED`/`DONE`/`FAILED`/`SUPERSEDED`), текущая `stage`,
  `stop_requested`, `folder`, `manifest` (JSONB), `counts` (JSONB), `message`,
  `created_by`, метки времени. **Один активный запуск** гарантируется частичным
  уникальным индексом `ux_pipeline_runs_active` (PENDING/RUNNING).
- `pipeline_run_stages` — по строке на стадию: `status`
  (`PENDING`/`RUNNING`/`DONE`/`FAILED`/`SKIPPED`), `total_count`/`done_count`/
  `failed_count`, `ref` (JSONB: `job_id`, `batch_id`, `hybrid_run_id`), `message`,
  метки времени.

## Неизменяемый снимок входа (manifest)

- При старте стадии INGEST список файлов папки (`discover_files` +
  `discover_video_files`) замораживается в `manifest["files"]` (относительные
  имена). Задача INGEST_DIR получает этот список в payload (`only_files`), и
  `pipeline.run`/`_ingest_videos` фильтруют обход по нему.
- По завершении INGEST записывается `manifest["photo_cutoff"]` — момент времени
  (DB `CURRENT_TIMESTAMP::timestamp`). Стадии DINO/HYBRID/QWEN работают только с
  фото, у которых `created_at <= photo_cutoff`.

Следствие: если прогон остановлен и **продолжен**, файлы, появившиеся в папке за
время простоя, в текущий прогон **не попадут**. «Начать заново» создаёт **новый**
запуск со свежим снимком; уже сделанная работа пропускается существующей
идемпотентностью (зарегистрированные файлы, готовые превью, DONE-раны DINO,
существующие строки QWEN).

## Стадии

| Стадия | Что делает | Признак завершения |
|---|---|---|
| INGEST | `enqueue_ingest(folder, only_files=manifest.files)` | задача `INGEST_DIR` → DONE/FAILED |
| PREVIEW | `enqueue_missing_previews()` (батчами) | нет активных `PHOTO_PREVIEW` |
| DINO | `create_batch("NORMAL", photo_ids=фото без DINO ≤ cutoff)` + `enqueue DINO_BATCH` | batch `DONE`/`FAILED` |
| HYBRID | `create_run(batch_id)` + `enqueue HYBRID_RUN` | run `DONE`/`FAILED` |
| QWEN | `enqueue_qwen` для фото без QWEN ≤ cutoff | нет активных `QWEN_PHOTO` |

DINO/HYBRID, упавшие в `FAILED`, переводят весь запуск в `FAILED`. Стадия QWEN
завершается при отсутствии активных задач, даже если часть описаний упала —
счётчик `failed_count` сохраняется (нужно для статистики «сколько с ошибкой»).

Стадия, которой нечего делать (нет фото без DINO, нет папки), помечается
`SKIPPED` и прогон идёт дальше.

## Остановка / продолжение / перезапуск

- **Остановка** (`POST /v1/pipeline/{id}/stop`) кооперативная: ставится
  `stop_requested`, следующий тик переводит запуск в `STOPPED`. Уже запущенные
  дочерние задачи (DINO/QWEN) доигрывают сами — супервизор их не убивает.
- **Продолжить** (`POST /v1/pipeline/{id}/resume`) возвращает `STOPPED` →
  `RUNNING`; работа продолжается с текущей стадии и **того же manifest**.
- **Заново** (`POST /v1/pipeline/start`) создаёт новый запуск; прежний `STOPPED`
  помечается `SUPERSEDED`. Новый снимок учитывает новые файлы, уже обработанное
  не пересчитывается.

## API

| Метод | Путь | Scope | Назначение |
|---|---|---|---|
| POST | `/v1/pipeline/start` | `jobs:write` | новый запуск (папка по умолчанию — настроенная рабочая) |
| POST | `/v1/pipeline/{id}/stop` | `jobs:write` | попросить остановку |
| POST | `/v1/pipeline/{id}/resume` | `jobs:write` | продолжить остановленный запуск |
| GET | `/v1/pipeline/current` | `read` | активный запуск (иначе последний) со стадиями |
| GET | `/v1/pipeline` | `read` | список запусков |
| GET | `/v1/pipeline/{id}` | `read` | один запуск со стадиями |

## Worker

Тик супервизора выполняет выделенный процесс:

```
python -m app.jobs.worker --pipeline --interval 3
```

он **не** берёт задачи очереди — только двигает активный запуск. Юнит
`deploy/systemd/user/scene-pipeline-worker.service`. Реальные
INGEST/PREVIEW/DINO/HYBRID/QWEN выполняют обычные воркеры.

## Интерфейс

В шапке, слева от переключателя темы, стоит кнопка **«Обновление базы»**
(`frontend/src/components/PipelineUpdateButton.vue`). Она опрашивает
`GET /v1/pipeline/current` каждые 3 секунды и:

- **скрывается**, пока маршрут недоступен (API без применённой 031 отвечает
  404) — поэтому UI можно выкладывать раньше backend-rollout;
- показывает статус по стадии: INGEST — «Медиа в папке: N», PREVIEW —
  «Превью x/y», DINO — «Совпадений: x», HYBRID — «Сверка x/y», QWEN —
  «Описаний: x (ошибок: y)»; по завершении — «База обновлена <дата>»,
  при остановке — «Процесс прерван <дата>»;
- во время прогона показывает спокойную пульсирующую **точку** (не мигающий
  текст; при `prefers-reduced-motion` анимация выключена);
- по нажатию во время прогона открывает окно со статусом и кнопкой
  «Остановить», для остановленного — «Продолжить» / «Начать заново»;
- по завершении просит подвал обновить сводку (`@finished`).

Кнопку видит пользователь с `jobs:write` (Администратор/Менеджер); у Гостя
действие недоступно. Иконка темы отражает текущее состояние (солнце —
светлая, месяц — тёмная).

**Уточнение по «Обработано медиа x/y»**: INGEST-задача сейчас не публикует
живой прогресс (в `progress` пишут только сборки слепков), поэтому для стадии
INGEST показывается число медиа в снимке папки, а не «обработано из». Живой
прогресс INGEST — отдельная доработка.

## Rollout (выполнено 2026-10-16)

1. **Проверка 031.** Отдельную disposable PostgreSQL в этом окружении создать
   нельзя (роль без `CREATEDB`, нет sudo/docker), поэтому миграция проверена в
   **изолированной схеме** `scene_mig031_scratch` рабочей БД: свежее применение
   → повтор (идемпотентно) → инвариант «один активный запуск» (второй
   PENDING/RUNNING отклонён, новый после STOPPED разрешён) → каскадное удаление
   стадий → документированный откат DROP → удаление схемы. Всё прошло; схема
   удалена.
2. **Backup.** `photobase_ingest_test_before_031_20261016_160716.dump`
   (проверен `pg_restore -l`, 195 объектов).
3. **Применение.** `scripts/migrate.py` применил `031` (30→31 applied); повторный
   запуск — no-op. Таблицы `pipeline_runs`/`pipeline_run_stages` пусты, фото целы
   (326).
4. **Сервисы.** Установлен и включён `scene-pipeline-worker.service`;
   `scene-api` и `scene-worker` перезапущены. Все 6 сервисов активны; `/api/health`
   200, `/v1/pipeline/current` без токена 401 (fail-closed), маршруты
   `/v1/pipeline/*` присутствуют в OpenAPI.
5. **Сквозной smoke** (folder=None, реальной обработки нет): INGEST SKIPPED →
   PREVIEW DONE 326/326 → DINO SKIPPED (нет фото без DINO) → HYBRID SKIPPED →
   QWEN DONE 325/326 (1 известная ошибка) → run `DONE` «база обновлена». Тестовый
   запуск удалён.

Откат: остановить и отключить `scene-pipeline-worker.service`, перезапустить
`scene-api` без маршрутов pipeline (или оставить — они просто читают таблицы),
затем `DROP TABLE pipeline_run_stages, pipeline_runs` (см. комментарий в
`schema/031_pipeline_runs.sql`).
