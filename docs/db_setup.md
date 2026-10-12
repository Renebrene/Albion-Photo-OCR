# Развёртывание PostgreSQL для Scene Fingerprint / PhotoBAse

Краткая инструкция, как создать БД проекта. Схема таблиц — в [`database_schema.md`](database_schema.md).

## 1. Имена и подключение

Проект использует один набор переменных окружения во всех PostgreSQL-модулях
(`app/ingest/database.py`, `app/preview/database.py`, `app/dino/database.py`, `app/hybrid/database.py`):

| Переменная | Значение по умолчанию |
|---|---|
| `INGEST_DB_HOST` | `localhost` |
| `INGEST_DB_PORT` | `5432` |
| `INGEST_DB_NAME` | `photobase_ingest_test` |
| `INGEST_DB_USER` | `lora_ingest` |
| `INGEST_DB_PASSWORD` | обязательна |

`docs/ingest.md` §5 фиксирует, что эти же имя БД и роль (`photobase_ingest_test` / `lora_ingest`)
ранее были проверены на реальном PostgreSQL. В локальном кластере на 2026-10-12 их нет.

## 2. Быстрый путь: один скрипт

Требуется суперпользователь PostgreSQL только для шага 1 (создание роли и БД).

```bash
export INGEST_DB_PASSWORD='<пароль-для-роли-lora_ingest>'
export PGSUPERUSER=postgres                       # если отличается
# доступ суперпользователя: ~/.pgpass или PGPASSWORD (TCP),
# либо peer через сокет: PGSUPERUSER_SOCKET=1 (например, через sudo -u postgres)

scripts/db_bootstrap.sh
```

Скрипт:
1. создаёт роль `lora_ingest` и БД `photobase_ingest_test` (`schema/000_bootstrap.sql`);
   шаг **автоматически пропускается**, если роль приложения уже подключается к целевой БД;
2. применяет `schema/001_ingest.sql` … `005_hybrid.sql` от имени роли приложения;
3. **пропускает** шаг 2, если `public.photos` уже существует (файлы схем не идемпотентны).

Если у локального `postgres` включена peer-аутентификация (пароля нет), шаг 1 выполняется
через unix-сокет, например:

```bash
sudo -u postgres env PGSUPERUSER_SOCKET=1 INGEST_DB_PASSWORD='...' \
    "/path/to/scripts/db_bootstrap.sh"
```

## 3. Ручной путь

Шаг 1 — от суперпользователя:

```bash
psql -h 127.0.0.1 -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v app_user=lora_ingest -v app_db=photobase_ingest_test \
     -v db_password="$INGEST_DB_PASSWORD" \
     -f schema/000_bootstrap.sql
```

Шаг 2 — от роли приложения, строго по порядку:

```bash
export PGPASSWORD="$INGEST_DB_PASSWORD"
for f in 001_ingest 002_preview 003_dino 004_dino_batches 005_hybrid 006_job_queue 007_qwen 008_settings 009_collections; do
    psql -h 127.0.0.1 -U lora_ingest -d photobase_ingest_test \
         -v ON_ERROR_STOP=1 -f "schema/$f.sql"
done
```

## 4. Важные предупреждения

- **Не применять `schema/*.sql` повторно на непустой БД.** Файлы используют
  `CREATE TABLE` без `IF NOT EXISTS`; повторный прогон упадёт. Миграционного
  раннера в проекте нет.
- **`004_dino_batches.sql` теперь backfill-safe и идемпотентен**: создаёт
  `dino_batches` при отсутствии, добавляет nullable `batch_id`, бэкфиллит orphan-runs
  (по одному legacy-batch на run), затем `SET NOT NULL`; повторный прогон — no-op.
  Для БД, где ранее работал старый `finish_batch` (batch мог получить `DONE` при
  `FAILED` runs), примените `scripts/repair_dino_batch_status.sql`.
- **Не запускать `psql -1`/в одной транзакции** шаг 1: `CREATE DATABASE` не
  выполняется внутри транзакции.
- **Пароль:** в `scripts/db_bootstrap.sh` пароль роли приложения передаётся через
  env `PGPASSWORD` (не виден в списке процессов). На шаге 1 пароль передаётся как
  psql-переменная — он попадает в историю команд/`ps` хоста; для локального
  bootstrap это принято, для общих сред — используйте `~/.pgpass`.
- Существующая локальная БД `albion` (роль `albion_app`) относится к **другому
  приложению** и не затрагивается.

## 5. Проверка после развёртывания

```bash
PGPASSWORD="$INGEST_DB_PASSWORD" psql -h 127.0.0.1 -U lora_ingest -d photobase_ingest_test \
    -c '\dt' \
    -c "select count(*) from public.photos"
```

Ожидаемые таблицы: `photos`, `photo_previews`, `dino_runs`, `dino_candidates`,
`dino_batches`, `hybrid_runs`, `hybrid_results`.

Проверка на реальной БД (integration-тесты) выполняется отдельно и требует
`INGEST_DB_PASSWORD`.

Статус на 2026-10-12 (эта машина): БД `photobase_ingest_test` и роль `lora_ingest`
созданы, применены `schema/001–005` (7 таблиц), `app.ingest.database.check_identity_batch()`
успешно классифицирует запись как `NEW` (read-only). Таблицы пусты.

> Замечание по безопасности: пароль роли приложения — `lora` (задан владельцем, для
> локальной разработки). Это слабый пароль: для любого сетевого/общего окружения
> задайте стойкий (`ALTER ROLE lora_ingest PASSWORD '...'`) и храните его только
> в env/секрет-хранилище, а не в файлах репозитория.
