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
(по умолчанию `~/scene-fingerprint-backups`; systemd — `/var/backups/scene-fingerprint`).

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
  --backup ~/scene-fingerprint-backups/photobase_ingest_test_20261022_023000.dump \
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
