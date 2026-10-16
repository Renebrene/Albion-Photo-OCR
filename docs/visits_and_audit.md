# Посещения и аудит нормализации клиентов

**Статус:** реализовано в коде (schema/033, `app/visits.py`, правки
`app/api/repository.py` и маршрутов). Миграция `033` **пока не применена** к
рабочей БД; вкладка «Посещения» и журнал алиасов появятся после её применения
и перезапуска `scene-api`.

## Посещения

- Таблица `user_visits` (schema/033): `visit_id`, `user_id` (FK → `users`, при
  удалении пользователя → NULL), `user_name` (снимок имени, чтобы список
  пережил переименование/архивацию), `event` (`login`/`logout`), `created_at`.
- Запись делается в обработчике `POST /v1/auth/login` после успешной выдачи
  токена (`app/visits.py:record_visit`). Определение «посещения» — **каждый
  вход** (решение владельца). Ошибка записи не ломает вход.
- `GET /v1/visits?limit=` — журнал, scope **`users:manage`** (только
  Администратор: вкладка «Посещения» стоит рядом с «Пользователями»).
- UI: вкладка **«Посещения»** в техническом разделе между «Пользователями» и
  «Отображением» (`frontend/src/components/VisitsAdmin.vue`). Скрывается, пока
  маршрут недоступен.

## Аудит нормализации клиентов

- Таблица `client_alias_audit` (schema/033): `audit_id`, `actor`, `alias`,
  `canonical_old`, `canonical_new`, `action` (`create`/`update`/`delete`),
  `created_at`.
- Правки справочника алиасов пишут строку аудита с именем действующего
  пользователя: `repository.upsert_client_alias(alias, canonical, actor)` и
  `delete_client_alias(alias, actor)`; маршруты `PUT/DELETE /v1/client-aliases`
  передают имя из principal.
- `GET /v1/client-aliases/qwen-names` — все названия клиентов/брендов,
  распознанные QWEN, в алфавитном порядке с частотой (scope `collections:write`).
- `GET /v1/client-aliases/audit?limit=` — журнал правок (scope
  `collections:write`).
- UI (`ClientNormalization.vue`, вкладка «Отображение»): список имён QWEN —
  клик по названию подставляет его в поля «как распознал QWEN» и
  «каноническое имя» (второе — уже заведённое сопоставление, если есть); под
  таблицей алиасов добавлен журнал «кто/что/когда изменил».

Исходные строки `photo_qwen` не переписываются — как и раньше, нормализация
влияет только на группировку и фильтр клиентов.

## Rollout (не выполнено)

1. Проверить `033` на disposable PostgreSQL (или в изолированной схеме).
2. Backup, применить `033` через `scripts/migrate.py`.
3. Перезапустить `scene-api` — активируются `/v1/visits`,
   `/v1/client-aliases/qwen-names`, `/v1/client-aliases/audit`.
