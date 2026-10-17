# Тестирование

## Unit/backend и frontend

```bash
.venv/bin/python -m pytest -q
cd frontend && bun x vitest run tests
```

Backend-тесты по умолчанию не получают `INGEST_DB_PASSWORD`; DB-backed tests
пропускаются. Это сделано потому, что база `photobase_ingest_test` в локальном
развёртывании является рабочими данными, несмотря на суффикс `_test`.

## DB integration tests

Интеграционные тесты выполняют INSERT/UPDATE/DELETE и запускаются только на
отдельной disposable базе, заранее созданной и мигрированной под тесты. Имя
задаётся явно, пароль передаётся обычным `INGEST_DB_PASSWORD` из защищённого
окружения:

```bash
SCENE_TEST_DB=1 \
SCENE_TEST_DB_NAME=scene_fingerprint_ci \
INGEST_DB_PASSWORD='...' \
.venv/bin/python -m pytest tests/test_dino_batch_integration.py -q
```

`tests/conftest.py` откажется выполнять DB integration tests с базой
`photobase_ingest_test`. Не запускайте тесты с `SCENE_TEST_DB=1` против рабочей
БД. Тесты обязаны удалять созданные ими строки в `finally`/fixture teardown;
когда тест обращается к воркерам, он должен использовать отдельную очередь и
не допускать, чтобы сервисные воркеры забрали тестовые задания.

## Read-only диагностика orphan HYBRID

Чтобы пересчитать связи без изменения строк, запустите отчёт:

```bash
set -a && . ~/.config/scene-fingerprint.env && set +a
.venv/bin/python scripts/audit_orphan_hybrid.py --format csv
```

Скрипт делает только SELECT и показывает HYBRID ID, DINO batch, фактическое
число DINO runs/candidates, queue jobs и run-history links. Не используйте
ручные DELETE/UPDATE для operational rows без отдельного решения владельца.

## UI smoke tests

Vitest монтирует Vue/Quasar в `happy-dom` и подменяет `fetch`; это не проверяет
реальные браузерные загрузки, cookie/session профили и layout на физическом
viewport. Для ручного smoke-test нужны авторизованные сессии каждой роли:
Администратор, Менеджер, Гость.
