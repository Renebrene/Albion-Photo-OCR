# Фронтенд: старый NiceGUI → целевой Quasar

**Статус:** описание исторического фронтенда (по `111/`) и план переноса на Vue 3 + Quasar. Текущий репозиторий фронтенда на Quasar не содержит. Контракт API — [`api_target.yaml`](api_target.yaml), ТЗ — [`future_implementation_tz.md`](future_implementation_tz.md).

## 1. Что есть сейчас в репозитории

Текущий UI — минимальный NiceGUI в `app/main.py`: одна страница с тремя вкладками (`Создать слепок`, `Распознавание`, `База слепков`), синхронные вызовы `SceneEmbedder`/`FingerprintManager`/`SceneRecognizer`, создание моделей при импорте модуля. Это демонстрационный UI для fingerprint-слепков, а не фото-грид.

## 2. Исторический фронтенд (легаси NiceGUI, `app/web/`)

Более развитый фронтенд существовал в легаси-проекте `scene_fingerprint_mvp_v02` под `app/web/`. Заголовок окна — «АЛЬБИОН: Фотобаза. Офис».

Модульная структура:

- `app/web/main.py` — сборка страницы.
- `app/web/state.py`, `session.py` — состояние/сессия (в т.ч. `STATE.refresh_photos`).
- `app/web/config.py` — пути/конфиг.
- `app/web/frontend_v01.py`, `frontend_v02.py` — ранние версии.
- `app/web/components/`:
  - `header.py`, `filters.py`,
  - `photos.py` — грид фотографий (самый крупный модуль),
  - `addresses.py`, `clients.py` — панели-списки,
  - `collections.py` — подборки,
  - `search.py` — поиск (в легаси — только по данным Qwen, без DINO),
  - `technical.py`.
- `app/web/components/technical_modules/`: `photo_processing.py`, `qwen.py`, `automation.py`, `users.py`, `data.py`.
- `app/web/*_db.py`: `photo_db.py`, `client_db.py`, `directory_db.py`, `users_db.py` — доступ к PostgreSQL через `psycopg2` с `PG_CONFIG = {host: localhost, port: 5432, dbname: "photobase", user: "lora"}` (легаси-схема).

Типовая раскладка (из `111/chat_chunks/chunk_178.md`, `app/web/main.py`):

```python
ui.run(host=HOST, port=PORT, reload=False, title="АЛЬБИОН: Фотобаза. Офис")
```

```text
+----------------------+-------------------------------+
|  ПЕРИОД (card)       |                               |
|  [radio][select]     |                               |
+----------+-----------+                               |
| АДРЕСА   | КЛИЕНТЫ   |          ФОТО / GRID          |
| ↕ scroll | ↕ scroll  |                               |
+----------+-----------+-------------------------------+
```

Левая фиксированная колонка (~580px): карточка «Период» (`ui.radio` «Дата съёмки/Дата загрузки», `ui.select` «Текущий месяц/Предыдущий месяц/Все даты/Выбрать период»), ниже — две равные прокручиваемые панели «Адреса» и «Клиенты». Правая часть — грид фотографий (`build_photos()`), обновляемый через колбэк `STATE.refresh_photos`.

Виджеты NiceGUI, которые использовались: `ui.page`, `ui.row/column/card/label`, `ui.tabs/ui.tab_panel`, `ui.radio`, `ui.select`, `ui.input`, `ui.scroll_area`, `ui.dialog`, всплывающие окна («Показать фотографии»). Стилизация — Tailwind-классы через `.classes(...)` + `.style(...)`.

Легаси-грид грузил превью, показывал адрес/клиента/статус Qwen, поиск и подборки; оригиналы — по клику. Технический раздел (обработка, qwen, automaton, users, data) — отдельные модули.

## 3. Целевой фронтенд: Vue 3 + Quasar

Полностью отдельный SPA, работающий с FastAPI по [`api_target.yaml`](api_target.yaml). Никакого прямого доступа к PostgreSQL из фронтенда.

Принципы:

- данные только через REST API; оригиналы и previews — через API с проверкой прав;
- грид показывает **preview**, оригинал не грузится по умолчанию;
- серверная **cursor pagination** (≤100 элементов), ленивая подгрузка (`q-infinite-scroll`);
- UI не сортирует/не копирует исходники и не пересчитывает распознавание;
- статусы обработки — из API (реальные job/batch), а не отдельный журнал.

### 3.1 Соответствие виджетов NiceGUI → Quasar

| NiceGUI | Quasar |
|---|---|
| `ui.tabs` / `ui.tab_panel` | `q-tabs` / `q-tab-panels` / `q-route-tab` (Vue Router) |
| `ui.card` | `q-card` / `q-card-section` |
| `ui.row` / `ui.column` | `q-...` + flex-классы |
| `ui.select` | `q-select` |
| `ui.radio` | `q-option-group` / `q-radio` |
| `ui.input` | `q-input` |
| `ui.scroll_area` | `q-scroll-area` / `q-infinite-scroll` |
| `ui.dialog` | `q-dialog` |
| грид фото | `q-card` в `q-page` + `q-infinite-scroll`, либо `q-table` в grid-режиме |
| состояние (`STATE`) | Pinia store |
| HTTP | `axios`/`fetch` к FastAPI |

### 3.2 Экраны (v1)

1. **Фото (GRID)** — фильтры (адрес, клиент, дата, подборка, поиск), кнопка «Показать фотографии», сетка карточек на SMALL-preview, lazy-load, клик → просмотр (MIDDLE, далее original при наличии прав), отображение результата распознавания и score.
2. **Обработка (технический раздел)** — запуск/статус INGEST, DINO batch (NORMAL/FORCE_RERUN), HYBRID, прогресс и per-item ошибки; подтверждение дорогих операций; отображение реального состояния из API.
3. **Подборки/поиск** — saved searches (условия, не копия выдачи), collections (набор `photo_id`); мультизапрос AND/OR — следующий этап.
4. **Администрирование** — пользователи/роли (по правам), аудит.

### 3.3 Данные и безопасность

- авторизация OIDC/OAuth2, scopes (`photos:read`, `ingest:write`, `jobs:read`, `jobs:write`, `admin`);
- previews/оригиналы — только через авторизованный endpoint; фронтенд не принимает произвольные пути;
- CORS — allowlist UI origin; no secrets/EXIF в UI без необходимости.

### 3.4 Технологический стек

`Vue 3` + `Vue Router` + `Pinia` + `Quasar` (+ Vite). Сборка отдельным артефактом; раздача статики — reverse proxy или FastAPI static.

## 4. Что переиспользовать из легаси-фронтенда

- **Раскладку** «Период + Адреса/Клиенты + GRID» — как основу экрана «Фото».
- **Модульность** (header/filters/photos/addresses/clients/collections/search/technical) — перенести как Vue-компоненты.
- **Семантику фильтров** (период: дата съёмки/загрузки; месяцы; адрес/клиент/подборка; поиск) — в фильтры грида.
- **Смысл технических модулей** (обработка, qwen, automation, users, data) — как отдельные разделы SPA.

Не переиспользовать: прямой `psycopg2` из UI, легаси-схему `photos` (`address/client/qwen_*`), Qwen-специфичный поиск как единственный источник.

## 5. Что нужно решить до реализации

- Нормализованные сущности адресов/клиентов (или фильтры по строкам) — влияет на фильтры и API.
- Источник адреса/клиента: HYBRID-вердикт (fingerprint-id) vs Qwen-метаданные vs отдельный реестр (см. [`qwen_process.md`](qwen_process.md)).
- Единый контракт DTO (Pydantic) для грида/поиска/статусов.
- Аутентификация и права на просмотр previews/originals.

## 6. Реализованный срез 1 (2026-10-13)

Первый вертикальный срез: read-only API + Quasar GRID на реальной БД. Аутентификации **нет** — только локальная разработка.

### Backend — `app/api/` (FastAPI)

- `GET /api/health` → `{"status":"ok","version":...}`
- `GET /api/v1/photos?limit=&cursor=&q=` → страница зарегистрированных фото (cursor-пагинация по `photo_id`, `limit` 1..100, `q` — подстрока в `filename`); ответ `{items, next_cursor}`.
- `GET /api/v1/photos/{photo_id}` → сводка фото.
- `GET /api/v1/photos/{photo_id}/previews/{small|middle}` → JPEG-превью.

Особенности: `photo_id` валидируется по `^PH_[0-9a-f]{24}$` (иначе 404); путь превью строится из `photo_id` и `SCENE_PREVIEW_ROOT`, а не из пользовательского ввода; подключение к БД — через `INGEST_DB_*`. Конфиг API не тянет torch (`app/api/config.py`). CORS — по `SCENE_CORS_ORIGINS` (по умолчанию localhost:5173).

Тесты: `tests/test_api.py` (health, валидация, 404; list/cursor — с БД).

### Срез 2 — статусы обработки (read-only)

- `GET /api/v1/batches/dino?limit=&cursor=` — список DINO batch-ей (тип, статус, счётчики, тайминги).
- `GET /api/v1/batches/dino/{batch_id}` — детали batch (`404`, если нет).
- `GET /api/v1/batches/dino/{batch_id}/runs?limit=&cursor=` — runs batch-а.
- `GET /api/v1/hybrid/runs?limit=&cursor=` — список HYBRID-запусков.
- Экран «Обработка» в SPA: вкладки DINO batches / HYBRID runs, статус-бейджи, клик по batch → диалог со списком runs.

Запуск обработки (INGEST/DINO/HYBRID) в этом срезе **не реализован** — отдельный этап (enqueue + фоновый worker, без inference в request handler).

### Срез 3 — auth + originals

- `app/api/auth.py`: **опциональные** bearer-токены через `SCENE_API_TOKENS`
  (формат `token:scope1|scope2`, повторяющиеся через запятую, `*` = все scope).
  Если переменная не задана — API открыт (локальная разработка).
- Read-эндпоинты требуют scope `read`; `GET /api/v1/photos/{photo_id}/original`
  требует scope `originals` и отдаёт зарегистрированный исходник (путь берётся
  из БД, не из клиента). `GET /api/health` всегда открыт.
- SPA в этом срезе работает без токенов (если включить `SCENE_API_TOKENS`,
  фронтенду понадобится поле токена — следующий этап).
- OIDC/OAuth2 — будущая замена этого слоя без изменения эндпоинтов.

### Срез 4 — запуск обработки (очередь + worker)

- Очередь: таблица `job_queue` (`schema/006_job_queue.sql`). API только ставит задание, inference выполняет отдельный процесс.
- `POST /api/v1/jobs/dino-batch` (scope `jobs:write`) — создаёт DINO batch (`NORMAL`/`FORCE_RERUN`) и ставит задание → `202 {job_id, batch_id}`.
- `POST /api/v1/jobs/hybrid` (scope `jobs:write`) — создаёт HYBRID run для `DONE` batch и ставит задание → `202 {job_id, hybrid_run_id}`; неготовый batch → `409`.
- `GET /api/v1/jobs` и `GET /api/v1/jobs/{job_id}` (scope `jobs:read`) — статусы.
- **Worker:** `python -m app.jobs.worker` (один проход) или `--watch`. Забирает задание атомарно (`FOR UPDATE SKIP LOCKED`) и вызывает `app.dino.runner.run_batch` / `app.hybrid.runner.run`. Inference **никогда** не идёт в HTTP-хендлере.
- UI: кнопка «Запустить DINO (NORMAL)», действие «HYBRID» у `DONE`-batch и вкладка «Задания».
- Тесты: `tests/test_jobs_queue.py`, `tests/test_api_jobs.py`.

### Срез 5 — QWEN (текстовые метаданные)

- Параллельный процесс, независимый от DINO/HYBRID: `app/qwen/` + очередь (`job_type = QWEN_PHOTO`). Схема: `schema/007_qwen.sql` (таблица `photo_qwen`).
- Модель — через локальный **Ollama**; имя конфигурируемо (`QWEN_MODEL`, по умолчанию `qwen3-vl:8b`), `OLLAMA_URL`. Изображение (MPO → frame 0) ужимается и отправляется в `/api/chat` с `format=json`, `think=false`.
- Извлекаются поля: `description`, `address`, `client`, `brand`, `category`, `tags`.
- `POST /api/v1/jobs/qwen` (scope `jobs:write`) — ставит задания на указанные `photo_ids` или на все фото; выполняет тот же `app.jobs.worker`.
- `GET /api/v1/photos` расширен полями `address`/`client` и фильтрами `address`/`client`.
  **Источник адреса — распознавание** (последний `hybrid_results.hybrid_final_id`, fallback `dino_runs.dino_best_id`), **клиент — из QWEN** (`photo_qwen.client`).
- UI: в карточках GRID — адрес/клиент и описание; фильтры «Адрес (QWEN)»/«Клиент (QWEN)»; на экране «Обработка» — кнопка «Запустить QWEN».
- Тесты: `tests/test_qwen.py` (парсинг — всегда; БД — с базой; живой прогон — `QWEN_LIVE_TEST=1`).

### Срез 6 — выбор модели QWEN и авто-выгрузка

- Модель выбирается в рантайме и хранится в `app_settings` (`schema/008_settings.sql`, ключ `qwen_model`); при отсутствии значения используется env `QWEN_MODEL`. `app/settings_store.py`.
- `GET /api/v1/qwen/models` — список моделей Ollama + текущая; `PUT /api/v1/qwen/model` (scope `jobs:write`) — выбрать; `POST /api/v1/qwen/unload` (scope `jobs:write`) — выгрузить из памяти.
- **Авто-выгрузка:** каждый запрос к Ollama идёт с `keep_alive: 0`, поэтому модель выгружается сразу после обработки фото (проверено: после прогона `ollama ps` пуст).
- UI: экран «Настройки» — выбор модели из списка, кнопки «Сохранить»/«Выгрузить из памяти».
- Рекомендация для 12 ГБ VRAM: `qwen3-vl:8b` (точность/размер); быстрее — `qwen3-vl:4b-instruct`.

### Срез 7 — prod-раздача SPA

- FastAPI отдаёт собранный `frontend/dist` (если каталог существует): `/assets/*` — статика, остальные пути → `index.html` (SPA-fallback для клиентского роутинга).
- Маршруты `/api/*` регистрируются раньше и не затмеваются. Если `frontend/dist` нет — API работает как раньше (только `/api`).
- Один процесс для продакшена: собрать фронт (`bun run build`) и запустить `uvicorn app.api.main:app`. Проверено: `/` и `/processing` → HTML, `/api/health` → JSON, `/assets/*.js` → JS.
- Тесты: `tests/test_api_spa.py` (скипаются без сборки).

### Frontend — `frontend/` (Vue 3 + Quasar + Vite + Pinia + Router)

- Экран GRID: карточки на SMALL-превью, `q-infinite-scroll`, поиск по имени файла, клик → просмотр MIDDLE, состояния loading/empty/error.
- Dev-прокси `/api` → `http://127.0.0.1:8000` (см. `frontend/vite.config.js`).
- Quasar подключён готовым CSS (`quasar/dist/quasar.css`), без sass.

### Запуск

Backend (из корня репозитория):

```bash
export INGEST_DB_HOST=127.0.0.1 INGEST_DB_PORT=5432 \
       INGEST_DB_NAME=photobase_ingest_test INGEST_DB_USER=lora_ingest INGEST_DB_PASSWORD=lora
python -m app.api.main            # слушает http://127.0.0.1:8010

# альтернатива (порт задавайте явно; uvicorn по умолчанию использует 8000):
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8010
```

Frontend dev (порт 5173, прокси `/api` → backend):

```bash
cd frontend
bun install
VITE_API_TARGET=http://127.0.0.1:8010 bun dev   # http://localhost:5173
```

Порт API по умолчанию — `8010` (`SCENE_API_PORT`), dev-прокси по умолчанию нацелен на `http://127.0.0.1:8010` (`VITE_API_TARGET`). 8000 выбран не был, чтобы не конфликтовать с другими локальными сервисами; при необходимости порт переопределяется обеими переменными.

Prod — один процесс:

```bash
cd frontend && bun run build          # собирает frontend/dist
cd .. && python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8010
# SPA и API на одном порту: http://127.0.0.1:8010
```

Worker обработки (отдельный процесс):

```bash
python -m app.jobs.worker            # один проход
python -m app.jobs.worker --watch    # постоянно
```

### Ограничения среза

- Нет аутентификации/прав; нет выдачи originals.
- Фильтры — только по имени файла: в текущей схеме нет `address`/`client` (в легаси их давал QWEN, см. [`qwen_process.md`](qwen_process.md)).
- Нет экранов обработки (INGEST/DINO/HYBRID) и подборок — следующие этапы.
- Prod-раздача: собрать `frontend/dist` и отдать статику (reverse proxy или FastAPI static).

## 7. Источники

- `111/chat_chunks/chunk_178.md` — раскладка `app/web/main.py`, `ui.run(...)`.
- `111/chat_chunks/chunk_201.md` — NiceGUI/FastAPI mount, запуск.
- `111/chat_chunks/chunk_205.md`, `chunk_087.md` — `search.py`, `photo_db.py`, поля.
- Инвентарь модулей — grep по `app/web/...` в `111/`.
