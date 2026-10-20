# ТЗ №1 — механизм токенов и загрузки в Albion

**Исполнитель:** агент, работающий в `/home/alexice/projects/albion-files`.
**Зависимости:** нет. Это первый этап, от него зависят Photobase и демо-сайт.
**Статус:** реализовано 2026-10-20 (включая `DELETE /integration/files/<id>`);
`venv/bin/python -m unittest discover -s tests` — 54 OK.

## 1. Цель

Сделать файлохранилище Albion точкой выдачи машинных токенов и приёма файлов
от других проектов по сети (LAN или интернет), без браузерной сессии, CSRF и
ручного подтверждения. Токен выпускается владельцем хранилища, хранится только
в виде SHA-256, имеет права и привязку к папке.

Результат: любой доверенный сервис с токеном может проверить связь, загрузить
файл в разрешённую папку и получить обычную публичную ссылку Albion.

## 2. Что уже есть (не переделывать)

- `server.py:1937` — `check_api_key(provided)`: ищет SHA-256 ключа в
  `tokens.json`, возвращает `{'id', 'name'}`.
- `server.py:1948` — `_resolve_api_key()`: читает `X-API-Key` только из
  заголовка и кладёт имя/id в `g`.
- `server.py:1955` — CSRF применяется только при `session['logged_in']`;
  запросы с API-ключом его не требуют.
- `server.py:2406` — `/upload`: рабочая логика сохранения файла, проверки
  расширения, уникализации имени, записи в `files_db.json`, генерации `slug`.
- `server.py:2100` — `login_required`: только сессия. Для новых endpoint'ов
  его использовать **нельзя**.
- `manage_tokens.py` — выпуск/отзыв/список ключей.
- `upload_capacity_error(incoming_bytes, db=None)` — квоты и свободное место.
- `allowed_file`, `is_valid_filename`, `get_file_ext`, `make_short_slug`,
  `safe_upload_path`, `get_folder_physical_path`, `update_last_upload`,
  `save_db`, `load_db`, `load_folders`.
- `BASE_URL` (`ALBION_BASE_URL`) и публичные ссылки: `{BASE_URL}/{slug}` либо
  `{BASE_URL}/{url_path(physical_path)}`.

## 3. Модель токена

`tokens.json` остаётся словарём `{sha256(ключ): метаданные}`. Метаданные
расширяются, старые записи читаются как есть.

```json
{
  "<sha256>": {
    "name": "Photobase",
    "created": "20.10.2026 12:00",
    "scopes": ["upload", "download"],
    "folder_id": "3f0c...uuid",
    "expires_at": null
  }
}
```

Правила:

- Нет поля `scopes` → `["download"]` (полная обратная совместимость).
- `folder_id` обязателен для `upload`: без него токен не может писать.
- `expires_at` — необязательная дата ISO; просроченный токен отклоняется.
- `*` в `scopes` означает все права.
- Секрет хранится только как SHA-256; в открытом виде — один раз при выпуске.

`manage_tokens.py`:

```bash
python manage_tokens.py add "Photobase" --scopes upload,download --folder <uuid>
python manage_tokens.py add "Демо-сайт" --scopes upload,delete --folder <uuid>
python manage_tokens.py list
python manage_tokens.py revoke "Photobase"
```

`list` дополнительно печатает права и папку. `add` без `--scopes` сохраняет
прежнее поведение (`download`).

## 4. HTTP-контракт

Базовый URL — тот же, что у сайта (`ALBION_BASE_URL`). Аутентификация — только
заголовок `X-API-Key`. Тело и ответы — JSON, кроме multipart-загрузки.

### 4.1. `GET /api/v1/integration/verify`

Проверка токена и его прав. Ничего не меняет.

Успех `200`:

```json
{
  "ok": true,
  "name": "Photobase",
  "scopes": ["upload", "download"],
  "folder_id": "3f0c...",
  "base_url": "https://files.example.ru",
  "limits": {"max_upload_gb": 50}
}
```

Ошибки: `401` — токена нет/неверен; `403` — токен просрочен или у него нет
`upload`/`download`.

### 4.2. `POST /api/v1/integration/upload`

`multipart/form-data`:

| Поле | Обяз. | Смысл |
|---|---|---|
| `file` | да | один файл |
| `folder_id` | нет | если у токена нет привязки; иначе должен совпасть с токеном |
| `display_name` | нет | имя в интерфейсе; по умолчанию имя файла |
| `ttl_days` | нет | только для расчёта `expires_at`, файл не удаляется |

Успех `200`:

```json
{
  "file_id": "uuid",
  "url": "https://files.example.ru/korotkaya-ssylka",
  "short_url": "https://files.example.ru/korotkaya-ssylka",
  "object_key": "uploads/<folder>/<name>.jpg",
  "name": "photo.jpg",
  "folder_id": "3f0c...",
  "expires_at": "2027-01-18T12:00:00+00:00"
}
```

`expires_at` = сейчас + `ttl_days` (по умолчанию `ALBION_INTEGRATION_TTL_DAYS`,
90; максимум 3650). Это **метка для клиента**, а не удаление файла: у Albion нет
политики удаления по TTL. Явно указать это в ответе документации.

Ошибки:

| Код | Когда |
|---|---|
| `400` | нет файла, пустое имя, `count`/форма некорректны |
| `401` | токена нет или он неверен |
| `403` | нет права `upload`, токен не привязан к папке, чужая папка |
| `404` | папки нет |
| `413` | превышен размер запроса/файла |
| `429` | превышен лимит запросов токена |
| `507` | нет свободного места/квоты |

### 4.3. `DELETE /api/v1/integration/files/{file_id}` — необязательно

Право `delete`. Удаляет файл и запись, как кнопка в админке. Если в v1 не
делать — клиенты обязаны считать, что удаление на стороне Albion не поддержано,
и документировать это.

## 5. Изменения в коде

### 5.1. `manage_tokens.py`

1. Добавить аргументы `--scopes` (через запятую) и `--folder`.
2. Валидировать: `scopes ⊆ {download, upload, delete, *}`; для `upload`
   требовать `--folder`.
3. Сохранять новые поля; `list` печатает их.
4. Не менять формат старых записей.

### 5.2. `server.py`

1. Расширить `check_api_key`:

```python
def check_api_key(provided):
    if not provided:
        return None
    key_hash = hashlib.sha256(provided.encode('utf-8')).hexdigest()
    meta = load_tokens().get(key_hash)
    if not meta:
        return None
    scopes = meta.get('scopes') or ['download']
    expires = meta.get('expires_at')
    if expires:
        try:
            if datetime.fromisoformat(expires) < datetime.now():
                return {'id': key_hash, 'name': meta.get('name', '?'),
                        'scopes': scopes, 'folder_id': meta.get('folder_id'),
                        'expired': True}
        except ValueError:
            return None
    return {'id': key_hash, 'name': meta.get('name', 'без имени'),
            'scopes': scopes, 'folder_id': meta.get('folder_id'),
            'expired': False}
```

2. Добавить хелпер `require_api_scope(scope)` для новых роутов (возвращает
   `(meta, error_response)`); не использовать `login_required`.
3. Добавить `@app.route('/api/v1/integration/verify', methods=['GET'])` и
   `@app.route('/api/v1/integration/upload', methods=['POST'])`.
4. В upload:
   - проверить scope `upload` и `folder_id` токена;
   - `folders = load_folders()`, папка должна существовать;
   - `allowed_file(file.filename)`, `get_file_ext`, `original_name.replace('+','_')`;
   - уникализировать имя так же, как `/upload`;
   - **атомарная запись**: сохранить во временный файл рядом с целевым и
     `os.replace(tmp, save_path)`; при ошибке удалить tmp;
   - записать запись в `files_db.json` теми же полями, что `/upload`
     (`access_id`, `current_filename`, `physical_path`, `slug`, ...);
   - вернуть контракт §4.2.
5. Лимит частоты: использовать существующий `limiter`, ключ — `g.api_key_id`
   (fallback — IP). Значение — 60 загрузок в минуту на токен.
6. Логирование: имя токена, имя файла, размер, папка. **Никогда** не логировать
   сам ключ и `X-API-Key`.

### 5.3. Документация

Обновить `docs/API.md` разделом «Интеграция (машинные токены)»: токен, права,
папка, оба endpoint'а, коды ошибок, пример curl.

## 6. Безопасность (обязательные проверки)

- Ключ — только заголовок; query-параметр запрещён.
- Сравнение — через SHA-256 и словарь (как сейчас), без утечки длины/префикса.
- Токен не возвращается ни в одном ответе и не попадает в логи.
- Запись только в папку токена; `safe_upload_path` обязателен.
- Запрещены пустые имена, `..`, абсолютные пути, `\0`.
- Квоты и `ALBION_MIN_FREE_GB` — те же, что у веб-загрузки.
- Токен с `upload` не получает доступ к админским JSON-API.

## 7. Тесты

Добавить в `tests/test_server.py` (или отдельный `tests/test_integration.py`):

1. `verify` без ключа → 401; с неверным → 401.
2. `verify` с ключом `download` → 403; с `upload` → 200 и правильные scopes.
3. `upload` без права `upload` → 403.
4. `upload` с чужим `folder_id` → 403; с несуществующей папкой → 404.
5. Успешная загрузка: файл появился, запись в `files_db.json`, `url`
   начинается с `BASE_URL`, `object_key` внутри `uploads/`.
6. Дубликат имени получает суффикс, как в `/upload`.
7. Просроченный токен → 403.
8. Превышение размера → 413.
9. Ключ не появляется в логах (проверить перехватом логов).
10. Отзыв токена → 401.

Тесты не должны трогать рабочие `files_db.json`/`uploads`: подменять
`ALBION_DATA_DIR` на `tmp_path`.

## 8. Совместимость

- Старые токены без `scopes` продолжают работать на скачивание.
- Формат `files_db.json` не меняется.
- Существующие `/upload`, `/f/`, публичные ссылки не трогаются.
- Миграция данных не нужна.

## 9. Definition of Done

- [ ] `manage_tokens.py` умеет scopes и папку.
- [ ] `/verify` и `/upload` реализованы по контракту.
- [ ] Тесты из §7 зелёные.
- [ ] `docs/API.md` обновлён.
- [ ] `git diff --check`, рабочее дерево чистое после прогона тестов.
- [ ] Коммит по правилам репозитория, `git push`.

## 10. Чего не делать

- Не выдавать токену доступ к сессии/CSRF.
- Не удалять файлы по TTL.
- Не менять публичные ссылки и slug-логику.
- Не трогать `auth.json`, `settings.json`, браузерную админку.
