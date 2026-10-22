# Обслуживание: очистка job_queue и временных кропов

Дата: 2026-10-22

## Зачем

`public.job_queue` растёт быстрее доменных таблиц: на одно фото приходятся
несколько заданий (INSPECT/PREVIEW/DINO/HYBRID/QWEN/BILLBOARD). При 57 000
фото это сотни тысяч строк; без retention таблица и её индексы занимают
гигабайты, а история заданий дублирует `run_history`.

Кропы щитов — временные файлы. После успешного QWEN они удаляются сразу, но
при ошибках, отменённых прогонах и старых версиях могут накапливаться
десятки гигабайт.

## Политика job_queue

Активные строки (`PENDING`, `RUNNING`, `PAUSED`) **не удаляются никогда**.

| Статус | Возраст | Действие |
|---|---|---|
| `DONE` | старше `--done-days` (14) | архив + удаление |
| `CANCELLED` | старше `--done-days` (14) | архив + удаление |
| `FAILED` | старше `--failed-days` (30) | архив + удаление |
| `PENDING`/`RUNNING`/`PAUSED` | любой | не трогать |

Перед удалением строка попадает в компактный
`public.job_queue_archive` (миграция `schema/044_job_queue_archive.sql`):
`id`, тип, статус, попытки, `photo_id`, ошибка (до 2000 символов), даты.
Полные `payload`/`result` не архивируются — они самые тяжёлые, а
пользовательская история уже хранится в `run_history`/`run_history_jobs`.

Архив хранится `--archive-days` (365) и затем также очищается.

### Алгоритм

1. Посчитать кандидатов по статусу и возрасту (`COALESCE(finished_at, created_at)`).
2. Батчами по 5000 (`FOR UPDATE SKIP LOCKED`) выбрать строки.
3. В одной транзакции: `INSERT ... job_queue_archive ON CONFLICT DO NOTHING`,
   затем `DELETE ... job_queue ... RETURNING`.
4. Закоммитить батч; повторить, пока есть кандидаты или не достигнут
   `--max-delete`.
5. Применить retention к архиву.
6. `VACUUM (ANALYZE) public.job_queue` (если не `--dry-run` и не `--no-vacuum`).

Ограничения безопасности: только `DONE/FAILED/CANCELLED`, только старше
порогов, `--max-delete` по умолчанию 200 000, `--dry-run` ничего не пишет.
Удаление не затрагивает `run_history`, `run_history_jobs` и доменные
результаты (QWEN/DINO/HYBRID).

### Запуск

```bash
# Только посчитать, ничего не менять
.venv/bin/python scripts/cleanup_job_queue.py --dry-run

# Боевой запуск с настройками по умолчанию
.venv/bin/python scripts/cleanup_job_queue.py

# Только QWEN-задания, порог 7 дней
.venv/bin/python scripts/cleanup_job_queue.py --job-type QWEN_PHOTO --done-days 7

# JSON для мониторинга
.venv/bin/python scripts/cleanup_job_queue.py --json
```

Переменные окружения по умолчанию:
`SCENE_JOB_RETENTION_DAYS=14`, `SCENE_JOB_FAILED_RETENTION_DAYS=30`,
`SCENE_JOB_ARCHIVE_DAYS=365`.

Перед первым боевым запуском применить `schema/044_job_queue_archive.sql`
(или явно указать `--no-archive`, что не рекомендуется).

## Политика кропов

`scripts/cleanup_crops.py`:

1. **Все кропы удаляются только по возрасту** — `--older-than-days`
   (по умолчанию 7), независимо от статуса QWEN. Раньше кропы DONE-фото
   сносились сразу, но теперь после описания по ним идёт прогон серий
   (`docs/series_merge.md`), и они должны дожить до него. Не успел прогон за
   7 дней — кропы удаляются.
2. Фото с `FAILED` или без QWEN подчиняются тому же правилу: повторный запуск
   не детектирует щит заново в пределах срока.
3. Каталоги в `SCENE_CROPS_ROOT`, которых нет в `photo_regions`, — сироты;
   удаляются после того же порога.
4. Если по фото есть активное задание `QWEN_PHOTO`, `BILLBOARD_DETECT` или
   `QWEN_CROP` (`PENDING/RUNNING/PAUSED`) — фото пропускается целиком.
5. Удаляются только пути внутри управляемого `SCENE_CROPS_ROOT`; вместе с
   последним кропом удаляются маркер `.crops.json` и пустой каталог.

```bash
.venv/bin/python scripts/cleanup_crops.py --dry-run
.venv/bin/python scripts/cleanup_crops.py --older-than-days 7
.venv/bin/python scripts/cleanup_crops.py --max-delete 5000 --json
.venv/bin/python scripts/cleanup_crops.py --skip-orphans
```

`--max-delete` (по умолчанию 5000 файлов) не даёт одному запуску удалить
слишком много; `0` — без лимита. Код возврата `1`, если хотя бы один файл
не удалось удалить.

## Расписание

В репозитории есть systemd-таймеры:

```bash
# системный вариант (пользователь scene)
sudo cp deploy/systemd/scene-maintenance.service \
        deploy/systemd/scene-maintenance.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now scene-maintenance.timer

# или пользовательский вариант
cp deploy/systemd/user/scene-maintenance.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now scene-maintenance.timer
```

По умолчанию — ежедневно в 03:30 с разбросом до 15 минут. Проверка:

```bash
systemctl list-timers '*scene-maintenance*'
journalctl -u scene-maintenance -n 50
journalctl --user -u scene-maintenance -n 50
```

JSON-строка в журнале содержит `eligible`, `deleted`, `archive_pruned`,
`known_candidates`, `orphan_dirs`, `files`, `bytes`, `failed`, `limited`.
`failed > 0` или `limited=true` — повод разобраться; `limited` обычно значит,
что за один запуск обработана только часть и нужно повторить.

## Контроль и тревоги

Рекомендуемый минимум:

- раз в неделю смотреть `pg_total_relation_size('public.job_queue')` и
  `job_queue_archive`;
- `failed > 0` в JSON — алерт;
- `limited=true` несколько запусков подряд — увеличить `--max-delete` или
  запускать чаще;
- свободное место `SCENE_CROPS_ROOT` и `SCENE_DATA`;
- не запускать cleanup во время массового INSPECT/QWEN, если `--max-delete`
  большой: батчи короткие, но лучше ночное окно.

Пример SQL-контроля:

```sql
SELECT pg_size_pretty(pg_total_relation_size('public.job_queue')) AS queue,
       pg_size_pretty(pg_total_relation_size('public.job_queue_archive')) AS archive,
       (SELECT count(*) FROM public.job_queue WHERE status IN ('PENDING','RUNNING','PAUSED')) AS active;
```

## Откат

- Удалённые `job_queue`-строки восстановлению из архива не подлежат
  автоматически; архив содержит только метаданные. Это журнал выполнения, а
  не источник истины. При необходимости строку можно восстановить вручную
  из `job_queue_archive`, но `payload`/`result` в ней отсутствуют.
- Отключить таймер: `systemctl disable --now scene-maintenance.timer`.
- Откатить схему архива: SQL в шапке `schema/044_job_queue_archive.sql`.

## Тесты

`tests/test_cleanup_scripts.py` проверяет:
- предикат job_queue не трогает активные статусы;
- архивный batch содержит компактные поля и `DELETE`;
- кропы DONE удаляются сразу, остальные — по возрасту;
- `--dry-run` и `--max-delete` действительно ничего не удаляют сверх лимита.
