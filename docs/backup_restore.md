# Backup, restore и очистка базы

Дата: 2026-10-22

## Что бэкапим

| Данные | Обязательность | Инструмент |
|---|---|---|
| PostgreSQL | обязательно | `pg_dump -Fc` |
| `data/fingerprints` | желательно (дорого пересобирать) | файловый backup/restic |
| `data/preview`, `data/crops`, derivatives | можно пересоздать | не обязательны |
| Оригиналы на NAS | отдельная задача NAS | RAID/snapshot/restic |
| `/etc/scene-fingerprint.env` | обязательно | защищённый secret backup |

`data/` целиком не входит в ежедневный DB-backup: 19 ГБ и больше растут за
счёт превью. Для fingerprint используйте отдельный weekly backup или
`restic` с исключением `preview/`, `crops/`, `video_derivatives/`.

## Ежедневный backup

```bash
.venv/bin/python scripts/backup_db.py --dry-run
.venv/bin/python scripts/backup_db.py --json
```

Что делает скрипт:

1. `pg_dump -Fc --no-owner --no-privileges` во временный файл.
2. Проверяет дамп через `pg_restore --list`.
3. Считает SHA-256 и публикует файл атомарно (`os.replace`).
4. Пишет `.sha256` и `.json` manifest.
5. Удаляет старые дампы по GFS-политике:
   - последние 14 дней (`--keep-daily`);
   - 8 недель (`--keep-weekly`);
   - 6 месяцев (`--keep-monthly`).

Имя: `<db>_YYYYMMDD_HHMMSS.dump` в `SCENE_BACKUP_DIR`
(по умолчанию `~/albion-photobase-backups`; systemd — `/var/backups/albion-photobase`).

Установка таймера:

```bash
sudo cp deploy/systemd/scene-backup.service deploy/systemd/scene-backup.timer \
        /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now scene-backup.timer

systemctl list-timers '*scene-backup*'
journalctl -u scene-backup -n 30
```

Ежедневно в 02:30 с разбросом до 10 минут.

## Restore drill

Восстановление всегда в **отдельную** базу. Создать её должен администратор
PostgreSQL (у роли приложения может не быть `CREATEDB`):

```bash
sudo -u postgres createdb -O lora_ingest photobase_restore_test

.venv/bin/python scripts/restore_db.py \
  --backup ~/albion-photobase-backups/photobase_ingest_test_20261022_023000.dump \
  --target-db photobase_restore_test --confirm --jobs 4
```

Скрипт:

- проверяет `.sha256`, если он есть;
- отказывается писать в текущую `INGEST_DB_NAME` без `--allow-production`;
- требует явный `--target-db` и `--confirm`;
- делает `pg_restore --clean --if-exists --no-owner --no-privileges`.

После restore проверить:

```bash
psql -h 127.0.0.1 -U lora_ingest -d photobase_restore_test \
  -c "select count(*) from public.photos" \
  -c "select count(*) from public.photo_qwen" \
  -c "select count(*) from public.job_queue"
.venv/bin/python scripts/migrate.py --status   # с env на restore-БД
```

Restore drill проводить раз в квартал и записывать дату/результат.

## Очистка БД

### Штатная retention-очистка

- `scripts/cleanup_job_queue.py` — архив и удаление завершённых jobs;
- `scripts/cleanup_crops.py` — временные кропы;
- `deploy/systemd/scene-maintenance.timer` — ежедневно в 03:30.

Подробно: `docs/maintenance.md`.

### Полная очистка перед пересканированием

Полная очистка — **отдельная destructive-операция**, не входит в автоматический
таймер. Порядок:

1. Остановить workers и QWEN (`systemctl --user stop scene-*worker*`).
2. Сделать и проверить backup БД.
3. Сохранить справочники, которые не нужно пересоздавать:
   `users`, `sessions` (можно очистить), `address_directory`,
   `address_fingerprints`, `fingerprints`, `client_aliases`,
   `app_settings`, `automation_settings`.
4. Удалить доменные результаты в FK-безопасном порядке:
   `photo_qwen_history`, `photo_qwen`, `hybrid_results`, `hybrid_runs`,
   `dino_candidates`, `dino_runs`, `dino_batches`, `photo_regions`,
   `photo_previews`, `photo_address_overrides`, `photos`, `video_*`,
   `job_queue`, `run_history*`, `collections`, `saved_searches`.
5. Удалить производные каталоги `preview/`, `crops/`, `video_derivatives/`,
   `video/` (не оригиналы).
6. Запустить INSPECT заново.

Для повторяемости используется `scripts/reset_photobase.py`:

```bash
# посмотреть, что будет удалено
.venv/bin/python scripts/reset_photobase.py --dry-run --json

# боевой запуск: откажется при активных jobs, сделает backup и потребует
# точное подтверждение
.venv/bin/python scripts/reset_photobase.py --confirm RESET
```

Он сохраняет справочники (`users`, `sessions`, адреса, слепки, алиасы,
настройки, аудит), очищает доменные таблицы и производные каталоги
(`preview`, `crops`, `video_derivatives`, `storyboard`). Оригиналы не
затрагиваются. Для чистого теста есть `--dry-run`, `--no-files`,
`--no-backup` (последний — только для одноразовой среды).

## Что не делать

- Не запускать restore в рабочую БД без `--allow-production` и backup.
- Не хранить дампы на том же диске, что и PostgreSQL.
- Не считать `data/preview` backup'ом оригиналов.
- Не удалять `photo_qwen_history`, если нужна история пересканирований.

## Учебное восстановление на одноразовой базе (2026-10-23)

Проверка «бэкап действительно восстанавливается» без суперпользователя и без
риска для рабочей базы: поднимается **отдельный временный кластер PostgreSQL**
в `/tmp`, в него восстанавливается дамп, затем он удаляется. Рабочий кластер не
затрагивается ни на шаг.

```bash
export PATH=/usr/lib/postgresql/16/bin:$PATH
DRILL=/tmp/photobase-drill
mkdir -p "$DRILL/sock"

# ВАЖНО: локаль как у рабочей базы. С locale=C функция lower() не сворачивает
# кириллицу, и тесты, которые ищут адреса без учёта регистра, падают «на
# ровном месте» — на проде такого не будет.
initdb -D "$DRILL/data" -U lora_ingest --auth=trust --encoding=UTF8 --locale=en_US.UTF-8
pg_ctl -D "$DRILL/data" -o "-p 55433 -k $DRILL/sock -c listen_addresses=127.0.0.1" \
       -l "$DRILL/server.log" start

psql -h 127.0.0.1 -p 55433 -U lora_ingest -d postgres \
     -c "CREATE DATABASE photobase_restore_drill OWNER lora_ingest"
pg_restore -h 127.0.0.1 -p 55433 -U lora_ingest -d photobase_restore_drill \
           --no-owner --exit-on-error ~/albion-photobase-backups/<дамп>

# Сверка содержимого с рабочей базой (фото, превью, вердикты, очередь, сессии)
# и прогон интеграционных тестов:
SCENE_TEST_DB=1 SCENE_TEST_DB_NAME=photobase_ci_test \
INGEST_DB_HOST=127.0.0.1 INGEST_DB_PORT=55433 \
INGEST_DB_NAME=photobase_ci_test INGEST_DB_USER=lora_ingest \
INGEST_DB_PASSWORD=drill .venv/bin/python -m pytest tests/ -q

# Уборка
pg_ctl -D "$DRILL/data" stop -m fast && rm -rf "$DRILL"
```

Одноразовой базе нужны миграции, если она не восстановлена из дампа:

```bash
INGEST_DB_HOST=127.0.0.1 INGEST_DB_PORT=55433 INGEST_DB_NAME=photobase_ci_test \
INGEST_DB_USER=lora_ingest INGEST_DB_PASSWORD=drill \
.venv/bin/python scripts/migrate.py
```

### Результат прогона 2026-10-23

- восстановление полного дампа (1518 фото, 5740 заданий, 74 сессии) прошло без
  ошибок; по таблицам расхождений нет, кроме `photo_qwen` — там разница
  объясняется тем, что QWEN-воркер писал в рабочую базу уже после снятия дампа;
- интеграционные тесты (раньше они не запускались вовсе) дали **831 passed**;
  два падения оказались устаревшими тестами: они ждали фото без вердикта HYBRID
  в гриде, а грид по решению владельца показывает только распознанные. Тесты
  исправлены — теперь они создают вердикт (`conftest.recognize_photo`);
- ложное падение на импорте адресов было моей ошибкой в кластере (`locale=C`),
  а не ошибкой кода.
