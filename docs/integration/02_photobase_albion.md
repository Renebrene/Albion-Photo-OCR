# ТЗ №2 — сопряжение Photobase с файлохранилищем Albion

**Исполнитель:** агент, работающий в текущем репозитории
`scene_fingerprint_RELEASE_v38_1_v33`.
**Зависимость:** ТЗ №1 (`01_albion_tokens.md`) уже реализовано: Albion принимает
`X-API-Key`, умеет `/verify`, `/upload` и `/files/<id>`; токен привязан к папке.
**Статус:** реализовано 2026-10-20; настройка и эксплуатация —
[`../albion_storage.md`](../albion_storage.md).

## 1. Цель

Photobase должен:

1. хранить адрес хранилища, токен, папку и TTL в настройках (UI + БД, env как
   fallback), а не только в переменных окружения;
2. проверять связь с Albion кнопкой «Проверить связь» до первой загрузки;
3. выгружать выбранные фото/видео в Albion по новому контракту и получать
   обычную публичную ссылку;
4. показывать «Ссылки Albion» на вкладке **«Настройки»** технического раздела
   (перенос из «Отображения»).

TTL остаётся как есть: `media_links.expires_at` обязателен для `READY`, схема
**не меняется**, миграция не нужна.

## 2. Что уже есть (не ломать)

- `app/cloud/albion.py` — клиент: `settings()`, `is_configured()`,
  `upload_file(path, filename, ttl_days)`; ждёт `{url, expires_at, object_key}`.
  Сейчас читает только `ALBION_UPLOAD_URL` и `ALBION_API_KEY`.
- `app/cloud/export.py` — `run_export(link_id)`, выполняется в воркере
  (`app/jobs/worker.py`, тип `MEDIA_EXPORT`).
- `app/cloud/repository.py` — `create_pending`, `mark_ready`, `mark_failed`,
  `list_links`, `media_source`.
- `app/api/routes.py:200` — `GET /v1/media-links`; `:235` —
  `POST /v1/media-links` (создаёт PENDING и ставит `MEDIA_EXPORT`).
- `schema/039_media_links.sql` — таблица и CHECK; менять не нужно.
- `app/settings_store.py` — `get(key, default)`, `set_value(key, value)`.
- Образец хранения секрета и маскировки — QWEN:
  `app/qwen/processor.py:195` (`resolve_settings`), `:233` (`mask_api_key`),
  `:245` (`public_settings`), `:268` (`update_settings`; `None` — не менять,
  `""` — очистить).
- `app/api/auth.py`: `settings:write` есть только у Администратора.
- UI: `MediaLinksPanel.vue` сейчас подключён в `DisplaySettings.vue:13,90`;
  `DisplaySettings` стоит на вкладке «Отображение»,
  `BaseSettings.vue` — на вкладке «Настройки» (`Technical.vue:88-90`).

## 3. Новый модуль настроек

Создать `app/cloud/config.py` по образцу QWEN:

```python
KEYS = {
    "base_url": "albion_base_url",
    "api_key": "albion_api_key",
    "folder_id": "albion_folder_id",
    "ttl_days": "albion_ttl_days",
}

def resolve_settings() -> dict:
    """DB (app_settings) поверх env-значений по умолчанию."""

def public_settings() -> dict:
    """Без токена: url, folder_id, ttl_days, configured, api_key_set,
    api_key_hint (mask_api_key)."""

def update_settings(*, base_url=None, api_key=None, folder_id=None,
                    ttl_days=None) -> dict:
    """None — не менять, "" — очистить (для токена)."""
```

Правила:

- Env fallback: `ALBION_BASE_URL`, `ALBION_API_KEY`, `ALBION_FOLDER_ID`,
  `ALBION_LINK_TTL_DAYS` (по умолчанию 90, 1…3650).
- `ALBION_UPLOAD_URL` считать устаревшим; в документации заменить на
  `ALBION_BASE_URL`. Если переменная ещё задана, брать из неё origin
  (`scheme://host[:port]`) и писать предупреждение в лог один раз.
- `base_url` валидировать: только `http`/`https`, без логина/пароля, без
  хвостового `/`.
- Токен не возвращать никогда; `public_settings()` отдаёт только маску.
- `is_configured()` = `base_url` и `api_key` непустые.

## 4. Клиент Albion (`app/cloud/albion.py`)

Переписать на контракт ТЗ №1, сохранив имя `upload_file` и форму возврата
`{url, expires_at, object_key}`:

### 4.1. `verify() -> dict`

`GET {base_url}/api/v1/integration/verify`, заголовок `X-API-Key`.
Возвращает `{ok, name, scopes, folder_id, base_url}`.
Ошибки — `CloudUploadError` с безопасным текстом:

- `401` → «Albion отклонил токен»;
- `403` → «у токена нет права upload/папки»;
- таймаут/сеть → «Albion не ответил/недоступен».

### 4.2. `upload_file(path, filename, *, ttl_days=None) -> dict`

`POST {base_url}/api/v1/integration/upload`, multipart:

- `file` — поток,
- `folder_id` — из настроек (если задан),
- `ttl_days` — `ttl_days` или настройка,
- заголовок `X-API-Key`.

Ответ разобрать как сейчас: допускается плоский объект или `links[0]`.
Вернуть `url` (только http/https, без credentials), `expires_at`
(ISO или now+ttl), `object_key` (поле `object_key` или `key`; допускается
`file_id`).

Коды ошибок дополнить:

- `404` → «папка Albion не найдена»;
- `507` → «на хранилище Albion нет места»;
- `429` — оставить текущий текст с `Retry-After`.

### 4.3. Совместимость

`app/cloud/export.py` не менять по смыслу: он по-прежнему вызывает
`upload_file` и `repository.mark_ready`. `settings()` заменить на
`config.resolve_settings()`; экспорт читает настройки в момент выполнения
задания (воркер), поэтому смена URL/токена в UI подхватывается без рестарта.

## 5. API Photobase

Создать `app/api/cloud.py` и зарегистрировать в `app/api/main.py` (явный
`include_router`, как остальные):

| Метод | Путь | Scope | Назначение |
|---|---|---|---|
| `GET` | `/v1/cloud/settings` | `read` | публичные настройки (токен замаскирован) |
| `PUT` | `/v1/cloud/settings` | `settings:write` | сохранить URL/токен/папку/TTL |
| `POST` | `/v1/cloud/verify` | `settings:write` | проверить связь |

`PUT` принимает `{base_url?, api_key?, folder_id?, ttl_days?}`:
пустая строка очищает, отсутствие поля — не меняет. Ответ — как у `GET`.
`POST /verify` при ошибке возвращает `422`/`503` с безопасным текстом
(без токена и без абсолютных путей).

Добавить схему `CloudSettingsUpdate` в `app/api/schemas.py`.

## 6. UI

1. Новый компонент `frontend/src/components/CloudSettings.vue`:
   - поля Base URL, Folder ID, TTL (дней), Token (`type=password`, пусто =
     не менять);
   - подпись «сохранён …последние 4 символа», кнопка «Очистить токен»;
   - кнопки «Сохранить» и «Проверить связь», показ результата проверки;
   - блокировка полей без `settings:write` (Администратор).
2. `frontend/src/api/client.js`: `fetchCloudSettings`, `saveCloudSettings`,
   `verifyCloud`.
3. Перенос ссылок:
   - убрать `MediaLinksPanel` из `DisplaySettings.vue` (импорт и разметку);
   - добавить `CloudSettings` и `MediaLinksPanel` в `BaseSettings.vue`;
   - из `Technical.vue` убрать проброс `:all-links` в `DisplaySettings`, если
     он больше не нужен (иначе оставить только для совместимости пропсов).
4. `MediaLinksPanel` оставить компонентом, но обновить текст баннера: настройка
   теперь в «Настройках», а не только в env.
5. Проверить `Help.vue`: если там описан старый путь настроек — обновить.

## 7. Безопасность

- Токен — только в `app_settings`/env, в ответах и логах его нет.
- `base_url` — только http/https, без credentials; исходящий запрос без
  редиректов на другие хосты (httpx `follow_redirects=False`).
- Ошибки Albion не должны содержать токен, заголовки или локальные пути.
- `X-API-Key` очищать в `finally`, как сейчас.
- Не логировать тело ответа Albion целиком на уровне INFO.
- Не добавлять токен в query string.

## 8. Тесты

Backend (`tests/`):

1. `public_settings()` не содержит `api_key`, содержит `api_key_set`/hint.
2. `update_settings(api_key=None)` не меняет токен; `api_key=""` очищает;
   `ttl_days` клампится 1…3650; `base_url` с `javascript:` отклоняется.
3. `verify()`: 200 → ok; 401/403/таймаут → понятные `CloudUploadError`.
4. `upload_file()`: контракт ТЗ №1, `folder_id` и `ttl_days` уходят в запрос;
   плоский ответ и `links[0]`; `expires_at` из ответа; небезопасный URL
   отклоняется.
5. `POST /v1/media-links` при неконфигурированном провайдере → 503 (как сейчас).
6. Токен не появляется в ответах API и в `caplog`.

Frontend:

1. `CloudSettings` сохраняет и проверяет связь (stub `fetch`).
2. `BaseSettings` содержит «Ссылки Albion» и настройки Albion.
3. `DisplaySettings` больше не содержит `MediaLinksPanel`.
4. Обновить `frontend/tests/cloud-links.spec.js` под новый путь.

Команды: `cd frontend && bun run test`, `bun run build`, `uv run pytest -q`.

## 9. Definition of Done

- [ ] Настройки Albion хранятся в БД, env — fallback, токен замаскирован.
- [ ] «Проверить связь» работает и показывает понятный результат.
- [ ] Загрузка идёт на `/api/v1/integration/upload`, TTL сохраняется.
- [ ] `MediaLinksPanel` и `CloudSettings` на вкладке «Настройки»;
      «Отображение» их не содержит.
- [ ] Тесты зелёные, SPA собирается.
- [ ] Обновлены `docs/` (настройка, env, откат) и `Help.vue` при необходимости.
- [ ] `git diff --check`; рабочее дерево чистое после проверок.

## 10. Чего не делать

- Не менять схему `media_links` и семантику TTL.
- Не делать backfill/повторную выгрузку старых ссылок.
- Не трогать DINO/HYBRID/QWEN и очередь, кроме чтения настроек в
  `MEDIA_EXPORT`.
- Не возвращать токен в UI/API даже Администратору.
