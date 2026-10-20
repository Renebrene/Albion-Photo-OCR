# ТЗ №3 — внутреннее хранилище демо-сайта на Albion

**Исполнитель:** агент, работающий в
`/home/alexice/projects/albion_yandex_maps_presentation_demo (Copy)`.
**Зависимость:** ТЗ №1 (`01_albion_tokens.md`) реализовано; для сайта нужен
токен с правами `upload` (и `delete`), привязанный к папке.
**Статус:** реализовано 2026-10-20; эксплуатация и миграция —
`doc/albion-storage.md` в репозитории сайта.

## 1. Цель

Внутренние файлы сайта (медиатека админки: изображения, видео, документы)
должны уметь храниться на файлохранилище Albion. Переключение — в настройках
админки. Старое локальное хранилище продолжает работать, ничего не ломается:

- по умолчанию режим `local` — поведение не меняется;
- в режиме `albion` новые файлы **пишутся и локально, и в Albion**; публичный
  URL берётся из Albion, локальная копия остаётся для экспорта, бэкапа и
  отката;
- при ошибке Albion загрузка не теряется: файл остаётся локальным, в ответе и
  логе — предупреждение.

Это не «перенос всех старых файлов». Backfill существующих файлов — отдельная
задача (см. §12).

## 2. Что уже есть (факты, не ломать)

- `backend/services/media_service.py`:
  - `STORAGE_ROOT = PROJECT_DIR / "storage"`;
  - `save_image`, `save_video`, `save_document` валидируют и конвертируют файл,
    пишут его в `storage/media/`, затем вызывают `_insert_media` и
    `_insert_variant`;
  - `list_media` / `update_media` / `delete_media` работают с `storage_path`;
  - `delete_media` удаляет файлы по `STORAGE_ROOT / storage_path`.
- `backend/db/schema_cms.sql:152` — `media` (`storage_path TEXT UNIQUE`,
  `preview_path`), `:181` — `media_variants` (`storage_path TEXT UNIQUE`).
- `backend/main.py:223-230` — `app.mount("/storage", StaticFiles(...))`.
- Фронтенд строит URL как `/storage/${storage_path}` в:
  `frontend/src/services/adminMedia.js:25,41`,
  `frontend/src/pages/AdministrationMediaPage.vue:935`,
  `frontend/src/pages/AdministrationContactsPage.vue:969`,
  `frontend/src/pages/AdministrationSiteMenuPage.vue:319`,
  `frontend/src/components/admin/MediaPicker.vue:248`,
  `frontend/src/components/admin/MediaSourceButtons.vue:73`,
  `frontend/src/components/news/NewsMediaCarousel.vue:116,119,149`,
  `frontend/src/components/admin/NewsMediaField.vue:182`.
- `backend/services/settings_service.py` — только оформление (публичная схема
  `/api/settings`). **Секреты туда класть нельзя.**
- `backend/api/admin_settings.py` — `GET/PUT /api/admin/settings` (оформление).
- `backend/services/portfolio_export.py` и `backend/services/site_backup_service.py`
  читают файлы из `STORAGE_ROOT` по локальному пути.
- `backend/services/media_paths.py` — отдельная ветка импорта конструкций
  (`/storage/constructions/imports/...`).
- `backend/services/upload_limits.py` — лимиты чтения.

## 3. Архитектура

### 3.1. Режимы

| Режим | Запись | Публичный URL |
|---|---|---|
| `local` (default) | только локально | `/storage/...` |
| `albion` | локально **и** в Albion | `external_url` из Albion; при его отсутствии — `/storage/...` |

Локальная копия в режиме `albion` обязательна: `portfolio_export`, бэкап,
`construction_media` и старые записи продолжают читать её без изменений.

### 3.2. Разрешение URL

Добавить в сериализацию `media` и `media_variants` поле `url`:

```python
"url": external_url or f"/storage/{storage_path}"
```

Фронтенд использует `item.url`, если оно есть, иначе старое
`/storage/${storage_path}`. Это сохраняет совместимость со старыми записями и
не требует переписывать все страницы сразу.

### 3.3. Что загружать в Albion

Для каждого сохранения — все созданные объекты:

- изображение: основной файл + варианты `large`, `card`, `thumb`;
- GIF: основной файл (+ превью, если есть);
- видео: `mp4` + `preview.webp`;
- документ: один файл.

Ключ объекта в Albion: `site-media/<uuid>/<имя-файла>` (папка `site-media`
или подпапка, заданная токеном). Имя — как локальное (`<uuid>-card.jpg`).

## 4. Миграция БД

Новый идемпотентный файл
`backend/migrations/migrate_media_external_storage.py` в стиле существующих:

```sql
ALTER TABLE media
    ADD COLUMN IF NOT EXISTS storage_backend TEXT NOT NULL DEFAULT 'local',
    ADD COLUMN IF NOT EXISTS external_url TEXT,
    ADD COLUMN IF NOT EXISTS external_key TEXT;

ALTER TABLE media_variants
    ADD COLUMN IF NOT EXISTS storage_backend TEXT NOT NULL DEFAULT 'local',
    ADD COLUMN IF NOT EXISTS external_url TEXT,
    ADD COLUMN IF NOT EXISTS external_key TEXT;

ALTER TABLE media
    ADD CONSTRAINT media_storage_backend_check
    CHECK (storage_backend IN ('local', 'albion')) NOT VALID;
-- после проверки данных: VALIDATE CONSTRAINT
```

- `storage_path` остаётся локальным путём и `UNIQUE` — не менять.
- Backfill не нужен: все старые строки = `local`.
- Выдать права `albion_app` на новые колонки не требуется (они в тех же
  таблицах), но проверить `information_schema` после миграции.
- Откат: колонки аддитивные; удалять их отдельной миграцией только после
  полного отката режима.

## 5. Backend

### 5.1. Новый сервис `backend/services/albion_storage.py`

По образцу клиента Photobase:

- `resolve_config()` — `site_settings` (ключ `storage.albion`) поверх env:
  `ALBION_FILES_URL`, `ALBION_FILES_TOKEN`, `ALBION_FILES_FOLDER_ID`,
  `ALBION_FILES_MODE` (`local`/`albion`, default `local`),
  `ALBION_FILES_TTL_DAYS` (default 90);
- `public_config()` — без токена (`token_set`, `token_hint`, `mode`, `url`,
  `folder_id`);
- `update_config(...)` — `None` не менять, `""` очищать;
- `verify()` — `GET {url}/api/v1/integration/verify`;
- `upload_file(path, filename, *, subfolder=None)` —
  `POST {url}/api/v1/integration/upload`, multipart `file`,
  `folder_id`, `ttl_days`; заголовок `X-API-Key`;
- `delete_file(file_id)` — только если у токена есть `delete`; иначе вернуть
  `False` и не считать это ошибкой.

Требования: `httpx`, `follow_redirects=False`, таймаут 120 с, только
`http`/`https`, токен не логировать, ошибки — безопасным текстом.

### 5.2. Новый сервис `backend/services/storage_backend.py`

- `mode() -> str`;
- `should_store_remote() -> bool`;
- `public_url(record) -> str`;
- `upload_saved_objects(objects) -> list[dict]` — принимает список
  `(local_path, relative_path, kind)` и возвращает `external_url`/`external_key`
  для каждого; при ошибке возвращает `None` и пишет warning, **не бросает**.

### 5.3. `media_service.py`

1. В `save_image`, `save_video`, `save_document` после успешной вставки в БД:
   - если `should_store_remote()`, вызвать `upload_saved_objects` для всех
     созданных файлов;
   - обновить строки `media`/`media_variants` полями
     `storage_backend='albion'`, `external_url`, `external_key`;
   - при любой ошибке оставить `storage_backend='local'`, записать warning и
     вернуть успешный ответ (локальный файл уже сохранён).
2. В `_insert_media`/`_insert_variant` добавить необязательные параметры
   `storage_backend`, `external_url`, `external_key` (по умолчанию `local`).
3. В `list_media` и в выдаче одного медиа добавить `url` для медиа и каждого
   варианта (см. §3.2).
4. В `delete_media`: удалить локальные файлы как сейчас; если
   `storage_backend='albion'` — вызвать `delete_file(external_key/file_id)`;
   при отсутствии права `delete` — залогировать «объект остался в Albion» и не
   считать операцию неуспешной.
5. Не менять сигнатуры публичных функций, кроме новых необязательных
   параметров.

### 5.4. Настройки и API

Не добавлять секреты в `settings_service` (он публичный). Создать
`backend/api/admin_integration.py`:

| Метод | Путь | Доступ |
|---|---|---|
| `GET` | `/api/admin/integration/albion` | `require_admin` |
| `PUT` | `/api/admin/integration/albion` | `require_admin` |
| `POST` | `/api/admin/integration/albion/verify` | `require_admin` |

Зарегистрировать роутер в `backend/main.py` рядом с `admin_settings_router`.
Ответ `GET` — `public_config()`; `PUT` — сохранить и вернуть `public_config()`;
`verify` — результат проверки или `400/503` с безопасным текстом.

## 6. Frontend

1. `frontend/src/services/adminMedia.js`: добавить
   `mediaUrl(item)` и `variantUrl(variant)`, которые возвращают
   `item.url || '/storage/' + item.storage_path`.
2. Заменить прямые шаблоны `/storage/${path}` в перечисленных в §2 файлах на
   новые хелперы. Для мест, где есть только `storage_path` (например,
   `NewsMediaCarousel`), оставить fallback — но если приходит `url`, брать его.
3. `AdministrationSettingsPage.vue`: добавить секцию «Файлохранилище Albion»:
   - режим (`local` / `albion`), URL, папка, TTL, токен (password, пусто = не
     менять), подпись-маска;
   - кнопки «Сохранить», «Проверить связь», «Очистить токен»;
   - показывать результат `verify` и предупреждение, что в режиме `albion`
     файлы дублируются локально и удалённо.
4. Ничего не менять в публичных страницах, кроме источника URL.

## 7. Отказоустойчивость и откат

- Albion недоступен → загрузка не падает, файл остаётся локальным; в БД
  `local`; в UI/логе предупреждение.
- Переключение `albion → local` мгновенно возвращает старые локальные URL;
  файлы, уже ушедшие в Albion, остаются, но продолжают иметь локальную копию.
- Переключение `local → albion` не трогает старые записи: у них нет
  `external_url`, поэтому URL остаётся `/storage/...`.
- Массовый перенос старых файлов не выполняется.

## 8. Безопасность

- Токен — только в `site_settings`/env; не возвращать в API, не писать в логи.
- `base_url` — только http/https, без credentials.
- Ответы Albion не логировать целиком.
- Не ослаблять существующие проверки размера/типа файла: Albion получает уже
  провалидированный и сконвертированный файл.
- Не добавлять новые внешние хосты в CSP без необходимости: публичные URL
  открываются как изображения/ссылки, а не как fetches из JS. Если появятся
  `<img>` с внешним хостом — добавить его в CSP в `frontend/index.html` и
  `deploy/nginx.conf.example`.

## 9. Тесты

Backend (`backend/tests`):

1. Миграция идемпотентна (два запуска подряд).
2. `resolve_config`/`update_config`: `None` не меняет, `""` очищает, режим
   валидируется, токен маскируется.
3. `mediaUrl`-сериализация: старая запись → `/storage/...`; запись с
   `external_url` → внешний URL.
4. `save_image` в режиме `albion` с подменённым `albion_storage.upload_file`
   (monkeypatch, без сети): локальные файлы на месте, в БД `albion` и
   `external_url`.
5. Ошибка загрузки в Albion: запрос успешен, в БД `local`, warning в логе.
6. `delete_media`: локальные файлы удалены; при `delete_file=False` операция
   успешна.
7. `verify` с фейковым httpx: 200/401/таймаут.

Frontend:

1. `AdministrationSettingsPage` сохраняет и проверяет настройки (stub fetch).
2. `mediaUrl` выбирает `url` при наличии.
3. `bun run build`.

Команды:

```bash
.venv/bin/python -m pytest backend/tests
cd frontend && bun run build && bun run lint:check
```

## 10. Definition of Done

- [ ] Миграция добавлена и идемпотентна.
- [ ] Режим `local` не меняет поведение (регрессионные тесты медиатеки).
- [ ] В режиме `albion` новые изображения/видео/документы уходят в Albion,
      локальная копия остаётся, URL ведёт на Albion.
- [ ] Ошибка Albion не ломает загрузку.
- [ ] Переключение режима в админке работает без рестарта.
- [ ] `portfolio_export`, бэкап и импорт конструкций не сломаны (локальные
      файлы на месте).
- [ ] Тесты и сборка зелёные; `git diff --check`.

## 11. Ограничения и следующая фаза

В v1 **не** переводятся на Albion:

- `construction_media` и импорт конструкций (`media_paths.py`,
  `storage/constructions/imports/...`) — отдельный поток;
- `news_media`, вложения новостей;
- изображения контактов и geo-слайдов, если они хранят путь отдельно от
  `media`;
- `portfolio_export`/`site_backup`: они продолжают читать локальные копии —
  это осознанно;
- backfill существующих файлов и удаление локальных копий.

Их можно перевести следующими фазами, когда режим `albion` подтверждён на
практике.

## 12. Ограничения работы с репозиторием

- Следовать `AGENTS.md`: один логический коммит, прямо в `main`, `git push`,
  строка `Co-Authored-By: Claude Code <noreply@anthropic.com>`.
- Перед правкой проверить `git status`: в дереве бывают чужие незакоммиченные
  изменения — не трогать.
- Не коммитить `.env`, `frontend/.env.local`, секреты.
- Каталог содержит `(Copy)` в имени: перед началом убедиться, что это тот
  репозиторий и ветка, и не копировать сюда артефакты из основного проекта.
