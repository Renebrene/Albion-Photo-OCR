# Что было в легаси (`scene_fingerprint_mvp_v02`) и чего нет сейчас

Источник: архив `111/` — это **выгрузка ChatGPT-логов**, код легаси вшит текстом в `chat_chunks/*.md` и `chatgpt_md/*`. Часть сниппетов — явные моки/заглушки. Легаси-стек: NiceGUI + FastAPI (внутри NiceGUI), PostgreSQL `photobase` (user `lora`), остаточный SQLite. Ссылки ниже — на файлы архива. Текущий статус сверен с `app/`, `schema/`, `frontend/src/`.

## 1. Уже реализовано (и часто лучше/иначе)

| Легаси | Текущий репозиторий |
|---|---|
| `photo_db.py` (чтение `photos`, статистика) | `app/api/repository.py` (photos, фасеты, фильтры) |
| `client_db.py` (клиенты с counts) | `GET /v1/clients` из `photo_qwen` |
| FastAPI `/api/photos`,`/api/clients`,`/api/addresses` | шире: `/v1/photos*`, `/v1/addresses`, `/v1/clients`, `/v1/batches/*`, `/v1/jobs*`, `/v1/qwen/*`, `/v1/photos/{id}/original` |
| `photo_ingest.py` | `app/ingest/` (integrity/identity/register/pipeline/database) |
| `dino_worker.py` / `qwen_worker.py` | `app/jobs/worker.py` + `app/dino/`, `app/qwen/` |
| `pipeline/queue.py` + `recovery.py` | `app/jobs/database.py` (`job_queue`, `FOR UPDATE SKIP LOCKED`) + наследие `app/pipeline/queue.py` (слепки) |
| Qwen-воркер, поля Qwen | `app/qwen/` + `schema/007_qwen.sql` (`photo_qwen`) |
| period/filters/GRID, базовые панели адрес/клиент | `frontend/src/pages/PhotosGrid.vue` (период, грид, одиночный выбор фасетов) |
| — | `app/api/auth.py` (bearer + scopes), `app/settings_store.py`, `schema/006..008`, `scripts/dev_up.sh`, CI-workflow |

## 2. Чего нет (пробелы) — по группам

### A. Пользователи, доступ, персонализация
- **`users_db.py`**: пользователи `Гость`/`Администратор`, `users`/`user_settings` (password_required, persist_state, active), вход по паролю, добавить/переименовать/архивировать/восстановить, палитра цветов. `session.py` — cookie-сессия (user_id), `get_current_user`.
- **Manager switcher** в шапке + **пер-менеджерский цвет** (`manager_colors`, `apply_user_color`).
- Сейчас: **Реализовано (2026-10-13)**: `schema/010_users.sql` (`users`, `user_sessions`), `app/users/` (scrypt-хэш пароля, CRUD), `app/api/auth.py` (login/logout/me, роли `Администратор/Менеджер/Гость` → scopes), UI-селектор менеджера + вход + вкладка «Пользователи». Остаётся bearer-режим как альтернатива. Пер-менеджерский цвет и `manager_selections` — нет.
- ⚠️ В легаси **пароль сравнивался в открытом виде** — копировать нельзя; делать нормально (хэш) или уходить в OIDC.

### B. Справочники адресов/клиентов
- **`directory_db.py`** + таблицы **`address_directory`**, **`address_fingerprints`** (PK `fingerprint_id` → `address_id`): маппинг **`78_v33 → 78`** (fingerprint → человекочитаемый адрес). `get_address_by_fingerprint()`.
- Нормализация клиентов: `client_db.py`, `client_aliases.py`, `client_dictionary.py`, `client_normalizer.py`, скрытые клиенты.
- Сейчас: адреса — **сырые fingerprint-id** (`78_v33`, `83_v33`); человекочитаемых адресов и справочника/алиасов клиентов нет.

### C. Подборки/закладки и сохранённые поиски (то, о чём вы спрашивали)
- **`collections.py` + БД**: таблицы **`collections`** (`user_id`, `name`, `kind ∈ {Моя, Клиентская}`, `scope ∈ {addresses, clients, photos}`), **`collection_members`** (`member_type ∈ {address, client, photo}`, unique), **`manager_selections`** (состояние чекбоксов менеджера). UI: `build_collections(scope)`, `add_collection()` (диалог Название/Тип/Клиент), синк с панелями адресов/клиентов. `chunk_207.md:708-786`, `chunk_176.md:269-462`.
- **Saved search / История поиска**: кнопка «Сохранить поиск» (bookmark), панель «История поиска» (в части ревизий — визуальные заглушки). `chunk_077.md:724`, `chunk_081.md:1994,2024`. — **Реализовано (2026-10-13)**: `schema/011_saved_searches.sql` + `/v1/searches` + карточка «История поиска» (сохранить/применить/удалить).
- Сейчас: подборки ✅ (кроме `manager_selections`), сохранённые поиски ✅.

### D. Выбор и массовые действия
- «Выбрать все»/«Снять выбор», **скачать выбранные** (`download_selected_files`), «Скачать все», **`download_selected_zip`**, «В подборку», «Сохранить поиск». `chunk_077.md:660-730`.
- Сейчас: нет (ни чекбоксов выбора фото, ни массовых операций).

### E. UI/UX (сверх реализованного)
- **Header**: логотип, подзаголовок, менеджер-селектор, **тёмная тема**, кнопка «Технический раздел». `chunk_079.md:2546-2620`. — **Реализовано** (тёмная тема, селектор менеджера/вход, вкладка «Технический»).
- **Глобальный поиск** по многим полям (client/brand/category/description/text/objects; планировался `tsvector`/GIN), «Найти», **загрузка фото** (`upload_photo`). `chunk_081.md:2262-2292`. — **Реализовано (2026-10-13)**: `q` ищет по filename/client/brand/category/description/address; загрузка — `POST /v1/upload` + кнопка/drag-and-drop. Нет: `tsvector`/GIN, разбора `raw`/objects.
- **Панели адрес/клиент**: **мультивыбор чекбоксами**, «Все/Снять», встроенный блок подборок. `chunk_175.md:195-224`. — **Реализовано (2026-10-13)**: чекбоксы-мультивыбор + «Все/Снять»; API принимает несколько `address`/`client` (OR).
- **GRID**: чекбокс выбора, **контекстное меню** (Открыть/Оригинал/Сохранить/В подборку), **drag-and-drop**, **режим список/плитка**, **сортировка**, кнопки фильтра. `chunk_077.md:487-730`, `chunk_078.md:302-333`. — **Реализовано (2026-10-13)**: чекбоксы, контекстное меню (ПКМ + меню в списке), режим плитка/список, сортировка, drag-and-drop файлов для загрузки.
- **Просмотрщик (rich)**: панель с Адрес/Клиент/**Бренд**/**Категория**/Confidence/Время Qwen/Статус/Описание + разобранные JSON: Текст/Цвета/Объекты/Окружение/Качество. `chunk_082.md:556-750`. — **Реализовано (2026-10-13)** по фактическим полям QWEN: Адрес/Клиент/Бренд/Категория/статус/модель/время/Описание/Теги (+ `GET /v1/photos/{id}/details`). Цвета/объекты/окружение/качество — у текущего QWEN-промпта таких полей нет.
- Сейчас: базовый грид + контекст/режимы/сортировка, одиночный выбор фасетов, rich-просмотрщик.

### F. Технический раздел
- Легаси — **модальный изменяемый диалог** с **8 вкладками**: `photo_processing, last_run, automation, qwen, data, system, fingerprints, users`. `chunk_103.md:1387-1515`.
- Сейчас: страница с **8 вкладками** (Обработка, Последний запуск, QWEN, Автоматизация, Система, Слепки, Пользователи, Данные); заглушки — `automation`, `data`.
- **`system/monitor.py`**: CPU/RAM/диск/сеть/температура/uptime. **Реализовано (2026-10-13, частично)**: `GET /v1/system` (psutil: CPU/RAM/диск/uptime/load) + UI-вкладка «Система». Нет сети/температуры.
- **`data.py`**: экспорт/импорт/обслуживание хранилища — **частично реализовано (2026-10-13)**: `GET /v1/data/export?format=json|csv` + `GET /v1/data/storage` + вкладка «Данные». **Импорт — нет** (заглушка; затрагивает INGEST). `fingerprints.py` (слепки) — **реализовано**: `GET /v1/fingerprints` + вкладка «Слепки». `last_run.py` (история) — **реализовано**: `GET /v1/runs/last` + вкладка «Последний запуск».

### G. Оркестрация и сервисы
- **`supervisor.py` / `controller.py` / `modes.py`**: режимы **manual / automatic (по времени) / watcher (слежение за папкой, polling)**, таблица **`pipeline_control`** (running/stop_requested/mode/watcher_path), `run_pipeline()` (DINO+Qwen), планировщик `seconds_until`. `chunk_234.md`, `chunk_145.md`, `chunk_142.md`. — **Частично реализовано (2026-10-13)**: расписание (`schema/012_automation.sql` + `/v1/automation` + `worker --automation`), авто-QWEN/авто-DINO. **Watcher папки/авто-INGEST — нет** (пишет новые данные).
- **`recovery.py`**: возврат «зависших» `processing → pending`. **Реализовано (2026-10-13)**: `app/jobs/database.py:requeue_stale()` (RUNNING старше N минут → PENDING), CLI-флаг `python -m app.jobs.worker --requeue-stale MINUTES` и `POST /v1/jobs/requeue-stale` (scope `jobs:write`). Проверено на реальном случае: 2 зависших QWEN-задания восстановлены и дообработаны.
- **systemd-юниты** (`scene-fingerprint.service`, `lora.service`, `dashboard.service`). `chunk_106.md:2469`.
- Сейчас: очередь + `python -m app.jobs.worker` (polling), `--automation` (расписание), `requeue-stale` (recovery), `scripts/dev_up.sh`. Нет: watcher папки/авто-INGEST и systemd-юнитов.

### H. OCR
- `app/ocr/{plate_detector,grid_ocr,ocr_pipeline}.py` — **перенесены**, но **не подключены** (ни пайплайн, ни API, ни UI). Задумывались как доп. корректор DINO только для спорных случаев; были «заморожены».

### I. Qwen — расширения
- **NL/поиск по Qwen-полям** в БД (`search.py`: `ILIKE` по client/brand/category/description/text/objects) и идея «Qwen — языковой интерфейс к БД».
- Флаг **«Автоматически запускать Qwen после DINO»**, «Повторно запустить Qwen», старт/стоп из UI.
- Нормализация клиентов Qwen (`smart_client_normalizer.py`, qwen3:4b).
- Сейчас: только извлечение (`QWEN_PHOTO`) + выбор модели; NL-поиска и авто-цепочки нет.

## 3. Что стоит добавить (рекомендация, по приоритету)

1. **Подборки + закладки** (C): таблицы `collections`/`collection_members` (+ `manager_selections`), API, UI (чекбоксы, «Добавить в подборку»). Это прямо запрошенная функциональность и относительно изолированная.
2. **Справочник адресов** (B): `address_directory` + `address_fingerprints` (маппинг `78_v33→78`), чтобы показывать человекочитаемый адрес вместо fingerprint-id. Влияет на все экраны.
3. **Выбор + массовые действия** (D): чекбоксы в GRID, «Выбрать все/Снять», скачивание выбранного (позже — zip).
4. **Пользователи/сессии** (A): лучше через **OIDC** или хэшированный пароль; ввести `users`/`roles` и серверную сессию/токен-логин. Пер-менеджерский цвет — приятный бонус.
5. **Единый поиск** (E): расширить `q` на client/brand/category/description; позже `tsvector`.
6. **Техраздел**: `system` (монитор), `fingerprints`, `last_run` (журнал запусков) — по образцу легаси.
7. **watcher/automation + recovery** (G): режимы и слежение за папкой — крупная работа; минимум — **recovery застрявших jobs** (недорого и полезно).
8. **OCR** (H): подключить к спорным случаям (после DINO/HYBRID), но это отдельный, необязательный этап.

## 4. Явные анти-паттерны легаси (не копировать)
- Пароль в открытом виде (`users_db.check_user_password`) → хэш/OIDC.
- Легаси-схема `photobase` с широкой `photos` (address/client/qwen_* в одной таблице) — у нас нормализовано (`photo_qwen` отдельно).
- Много визуальных заглушек (`ui.notify("... позже")`) — не выдавать за функциональность.
- Watcher-режимы в легаси фактически меняли только флаг в PG — делать реальный watcher, если нужно.

## 5. Источники (архив)
`chat_analysis`, `chat_chunks/chunk_{077,079,081,082,096,100,103,132,133,142,145,149,152,155,157,158,160,175,176,186,190,205,207,217,224,225,228,231,232,233,234}.md`, `chatgpt_md/ChatGPT-OCR для табличек-*.md`.
