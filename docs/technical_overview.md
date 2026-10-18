# PhotoBAse / Scene Fingerprint — техническое описание

**Актуально на 2026-10-18.** Документ описывает текущую реализацию в рабочей ветке и фактически используемую локальную конфигурацию. Это не SLA и не формальная сертификация безопасности. Целевые идеи из `docs/api_target.yaml`, `docs/architecture_target.mmd` и backlog не считаются реализованными, если ниже или в коде это не подтверждено.

## 1. Назначение

PhotoBAse — локальная веб-система для каталога фото и видео с распознаванием сцен/адресов и управлением обработкой. Она позволяет:

- регистрировать фотографии и видео из выбранных каталогов, не изменяя исходники;
- показывать фото и видео в браузере, искать и фильтровать их, открывать оригиналы при наличии прав;
- создавать и хранить эталонные fingerprint-слепки адресов;
- запускать отдельные задания PREVIEW, DINO, HYBRID и QWEN;
- просматривать состояния очереди, историю запусков и системные настройки;
- выполнять ограниченные video transcode/trim-операции с сохранением оригинала;
- при конфигурации Albion создавать временные облачные ссылки на выбранные медиа.

Основной сценарий — один сервер/рабочая станция в локальной сети; фотографии могут находиться на отдельном диске или сетевом хранилище. Приложение включает браузерный интерфейс, REST API, PostgreSQL и worker-процессы. Для внешнего доступа необходимы защищённая сеть или HTTPS reverse proxy, включённая аутентификация и корректные CORS origins.

## 2. Высокоуровневая архитектура

```text
Браузер: Vue 3 + Quasar SPA
             │ HTTP / JSON, bearer/session credentials
             ▼
FastAPI (API + раздача frontend/dist)
             │ параметры и задания, не тяжёлый inference
             ├────────────── PostgreSQL
             │               каталог, настройки, users/sessions,
             │               job_queue, DINO/HYBRID/QWEN, история
             ├────────────── Файловые каталоги
             │               originals (read-only), preview,
             │               fingerprints, derivatives, inbox
             ▼
Worker-процессы
  ├─ общий worker: INGEST, DINO/HYBRID, поиск и прочие jobs
  ├─ preview worker: фото SMALL/MIDDLE
  ├─ QWEN worker: локальный Ollama или облачный OpenAI-compatible API
  ├─ video worker: poster/storyboard/transcode/trim
  ├─ builder worker: fingerprint jobs
  └─ pipeline supervisor: координация стадий, не выполняет inference сам
```

API-обработчики создают задания, а тяжёлая работа выполняется worker’ами; inference не запускается синхронно в HTTP-handler. На Linux для постоянной работы применяются systemd user units из `deploy/systemd/user/`. У FastAPI отдельного frontend-сервиса нет: он отдаёт собранный `frontend/dist`.

## 3. Фото: идентичность и обработка

### 3.1 INGEST

1. Worker рекурсивно обнаруживает `.jpg`/`.jpeg` в выбранном каталоге.
2. Для нового фото файл проверяется Pillow: формат JPEG/MPO, размеры, число кадров, `verify()` и декодирование первого кадра. Исходник не изменяется.
3. `photo_id` строится как `PH_` + первые 24 hex SHA-256 всего физического файла. Полный digest хранится в `photos.sha256`; имя, каталог и EXIF не являются идентичностью фотографии.
4. Регистрация идемпотентно классифицирует фото как `NEW`, `EXISTING` или `CONFLICT`. В обычном folder ingest возможен быстрый пропуск известной пары `(filename, size)`; это ускоритель, не подтверждение идентичности содержимого.
5. Новая запись ставит задачу PREVIEW. Переносы/изменения реестра — транзакционные; оригиналы read-only.

Схема потока: `DISCOVER → INTEGRITY → IDENTITY → REGISTER → RESULT`.

### 3.2 PREVIEW

Для каждой зарегистрированной фотографии отдельный preview worker создаёт производные JPEG:

- SMALL: максимальная сторона по умолчанию 320 px;
- MIDDLE: максимальная сторона по умолчанию 1280 px;
- исходное соотношение сторон сохраняется, маленькие изображения не увеличиваются;
- файлы хранятся вне каталога originals, публикуются через временный файл, проверку и атомарное перемещение.

Preview нужен UI и локальному QWEN. Он не изменяет фото-ID и не является источником для DINO embedding, если другая операция явно не указала это.

### 3.3 DINO и HYBRID

- DINO batch фиксирует свой состав; добавление новых фотографий не меняет уже созданный batch.
- DINOv2 строит эмбеддинги и сохраняет кандидатов/оценки в PostgreSQL. Текущий runner в `app/dino/runner.py` выполняет DINO inference на **CPU**.
- HYBRID использует сохранённые DINO результаты и последовательный контекст. Он не должен молча повторно запускать DINO или изменять originals; запуск ограничивается documented readiness-условиями batch.
- Эталонные fingerprint-слепки хранятся как FAISS/NumPy/metadata файловые артефакты отдельно от реестра photo/video и PostgreSQL queue.

Не смешивать этот путь с созданием эталонного слепка. В runtime создание fingerprint — job `FINGERPRINT_BUILD` в PostgreSQL job queue и отдельный builder worker; в CLI/исторических компонентах имеется также SQLite queue (`app/pipeline/queue.py`), это другой механизм.

## 4. Видео

### 4.1 Регистрация и просмотр

Поддерживаются `.mp4`, `.m4v`, `.mov`, `.mpeg`, `.mpg`. Видео хранятся отдельно от фото и не поступают в DINO, HYBRID, QWEN или фото-fingerprint pipeline.

Для новых строк `video_id` — `VI_` + первые 24 hex SHA-256 **метаданных**, а не файла: канонически сериализованные basename, UTC-день и размер в байтах. Дата берётся из `creation_time`; при отсутствии — UTC-день mtime. Legacy video IDs/content-SHA значения сохраняются. Metadata ID не доказывает совпадение bytes: два разных файла с одинаковыми basename, датой и размером могут иметь один ID.

Video INGEST использует stat и ffprobe, не хеширует и не декодирует весь оригинал. Проверка stat до/после probe обнаруживает изменение размера/mtime во время чтения метаданных, но не замену bytes при сохранении тех же метаданных. Для новых видео нет общего лимита размера или длительности при регистрации и отображении.

Poster JPEG создаётся отдельно в `SCENE_VIDEO_PREVIEW_ROOT`. Исходники выдаются только в пределах `SCENE_ORIGINALS_ROOTS`; клиенту возвращается безопасное имя/каталог, но не абсолютный путь. Playback и скачивание используют короткоживущий HttpOnly cookie-ticket. Видео передаётся потоково с поддержкой HTTP byte ranges, а не целиком читается в память API или браузера.

### 4.2 Редактирование

- Только операции edit ограничены **1,5 GiB (1 610 612 736 байт) и 10 минутами**. Равенство лимиту допускается; превышение любого лимита блокирует edit, но не просмотр, listing, download или cloud link.
- Доступны профили H.264/MP4 transcode и ограниченный trim/storyboard. Это не полноценный видеоредактор с дорожками, эффектами или произвольным crop.
- Оригинал не перезаписывается. Готовый результат сохраняется под managed derivatives root, регистрируется как отдельный `video_assets`, получает poster и становится обычной карточкой для скачивания/ссылки. Имя основывается на исходном filename + `_копия`; при конфликте добавляется уникальный суффикс.
- Workers используют probe/stat/проверки формата, кодека, разрешения, FPS, длительности и размера. Полный content-SHA не считается; поэтому замена содержимого с теми же именем, размером, capture date и проверяемыми метаданными не может быть криптографически обнаружена.

Текущие каталоги задаются `SCENE_VIDEO_PREVIEW_ROOT`, `SCENE_VIDEO_STORYBOARD_ROOT` и `SCENE_VIDEO_DERIVATIVES_ROOT`; они не должны пересекаться с originals/source roots, кроме явно разрешённых originals для чтения. Для video jobs используется отдельный `scene-video-worker`.

## 5. QWEN и облачная обработка

QWEN — отдельный queued job для описаний/атрибутов фотографии, независимый от DINO/HYBRID.

- Локальный путь: Ollama; для поддерживаемого рабочего конфигурационного профиля используется instruct-VLM (например, `qwen3-vl:4b-instruct`). GPU в этом варианте нужен только если модель планируется запускать локально и требуется приемлемая скорость.
- Облачный путь: OpenAI-compatible API, явно настроенные provider/base URL/model/API key. Облаку передаётся изображение: фото кодируется в JPEG, уменьшается максимум до 1280 px по длинной стороне и отправляется с JSON-запросом. Перед выбором провайдера необходимо согласовать передачу изображений и политику хранения у поставщика.
- Базовый QWEN prompt явно перечисляет выходные поля `description`, `address`, `client`, `brand`, `category` и `tags`; при отсутствии значения модель должна вернуть `null`, а не выдумывать его. `client` и `brand` также выводятся в фото-гриде и доступны для ручного исправления в форме редактирования описания фото.
- QWEN исполняется worker’ом; API не загружает модель и не делает inference в request handler.

#### Опциональный billboard crop для QWEN

Детекция рекламного щита — отключаемая дополнительная ветка, управляемая переключателем **«Использовать crop рекламного щита для QWEN»** во вкладке **«Технический раздел → Распознавание»** (настройка `billboard_detect`, fallback env `SCENE_BILLBOARD_DETECT`). Переключатель доступен Администратору и сохраняется сразу. При выключении QWEN идёт по обычному полнокадровому пути; даже ранее сохранённый crop игнорируется, но не удаляется. При включённой опции worker ищет щит через YOLO-World; по умолчанию детекция использует копию с длинной стороной до 1920 px, score threshold 0.4, затем выбирается крупнейший bbox с padding 2%. Crop вырезается из оригинала в полном разрешении, атомарно публикуется в `SCENE_CROPS_ROOT` (default `data/crops`) и передаётся QWEN с максимальной стороной до 2048 px.

Для crop используется отдельный prompt, который явно просит `description`, `client`, `brand`, `category` и `tags`; поле `address` не запрашивается, потому что мелкий юридический адрес на рекламе может быть адресом рекламодателя, а не местом съёмки. После успешного QWEN crop удаляется; при отсутствии щита, выключенной опции или ошибке детекции обработка fallback-ится на полный кадр. Модуль детекции — отдельное optional расширение `ultralytics` с YOLO-World checkpoint и migration/table `photo_regions`; оно не является обязательной зависимостью базового режима и должно устанавливаться/включаться отдельно. В текущей рабочей конфигурации toggle включён; на сервере deployment state определяется его `app_settings`/environment значением. Код billboard-ветки и migration 040 находятся в незакоммиченном WIP, отдельно от commit видео/UI; для нового deployment эту ветку нужно включать только вместе со всеми её модулями, схемой, optional dependency и checkpoint.

Облачный QWEN снимает потребность в локальном GPU для этой конкретной модели, но **не** переносит туда DINO/HYBRID, сборку fingerprint, preview/INGEST, PostgreSQL или video transcode. Если billboard crop включён, внешнему QWEN provider передаётся crop; при fallback — подготовленный полный кадр. Albion cloud links — отдельная опциональная интеграция, не вычислительная платформа; для неё нужны отдельные endpoint/API credentials.

**Массовое пересканирование QWEN.** В «Распознавании» доступна деструктивная операция за явно выбранный период (по дате загрузки или съёмки): текущие строки `photo_qwen` выбранных фото сначала копируются в `photo_qwen_history`, затем удаляются, после чего ставится новое распознавание с зафиксированной текущей моделью. Пока есть активные QWEN jobs, операция отклоняется. Ответ API и история запуска содержат число архивных записей и поставленных jobs. Текстовый журнал последних версий доступен через `GET /v1/qwen/history`, третьей колонкой в настройках распознавания и внизу per-photo истории описаний.

## 6. Компоненты и службы

Linux user-unit профиль содержит:

| Unit | Роль |
|---|---|
| `scene-api` | FastAPI + раздача SPA |
| `scene-worker` | Общая очередь заданий, включая INGEST/DINO/HYBRID и операционные задачи |
| `scene-preview-worker` | Фото SMALL/MIDDLE preview queue |
| `scene-qwen-worker` | QWEN queue, чтобы модель/внешние запросы были изолированы |
| `scene-video-worker` | VIDEO_TRANSCODE, VIDEO_TRIM, VIDEO_STORYBOARD |
| `scene-builder` | Параллельная сборка fingerprint jobs; на текущем GPU-профиле настроен parallel=3 |
| `scene-pipeline-worker` | Supervisor последовательности стадий; сам не забирает тяжёлые jobs |

Образ Windows Docker Compose — демонстрационный стек PostgreSQL/API/general worker/QWEN/pipeline. В его текущем compose-файле нет выделенного video-worker, поэтому не следует считать, что Windows demo имеет полный parity с Linux video runtime.

## 7. Технические требования

### 7.1 Обязательное ПО

- **Python 3.12** (`>=3.12,<3.13`), зависимости проекта установлены из `pyproject.toml`/lockfile.
- **PostgreSQL**; в Windows Compose указан PostgreSQL 16. Постоянная установка должна использовать versioned SQL migrations через `scripts/migrate.py`.
- **Linux/systemd** — рекомендуемый production-like хост по текущим unit-файлам. Для Windows есть demo Compose; GPU/worker parity и производительность необходимо проверять отдельно.
- **FFprobe** для чтения metadata при video INGEST и проверки результата; **FFmpeg** с H.264 decode/encode компонентами для storyboard, trim и transcode. Постер создаётся через OpenCV VideoCapture. NVENC необязателен: использовать его только после успешного runtime smoke в контексте того же worker service; CPU `libx264` остаётся fallback.
- **Собранный SPA**: Node-compatible package manager Bun для `bun install --frozen-lockfile` и `bun run build`; в runtime браузерные assets обслуживает `scene-api`.
- **Ollama или облачный QWEN provider** — только если используется QWEN. Для локального inference нужен подходящий instruct vision-language model; облачный вариант требует исходящего HTTPS и настроенных credentials.
- Доступ к PostgreSQL, configured originals/source roots, writable `SCENE_DATA`, preview/storyboard/derivative/inbox roots и место для резервных копий.

### 7.2 Рекомендуемое железо

Это стартовые рекомендации, а не кодом проверенный формальный минимум; multi-user и крупные архивы необходимо профилировать.

| Профиль | CPU | RAM | Диск/сеть | GPU |
|---|---:|---:|---|---|
| Небольшая CPU-only установка | 4 vCPU | 16 ГБ | SSD от 500 ГБ плюс оригиналы | не нужен |
| Удобный локальный сервер | 6–8 физических ядер / 12–16 потоков | 32 ГБ | NVMe 1 ТБ или больше; оригиналы на отдельном диске/NAS | опционально NVIDIA 8–12 ГБ |
| Запас для нескольких workers/локального QWEN | 8–12 ядер | 64 ГБ | NVMe под ОС/БД/cache + рассчитанный объём для media/preview/derivatives | NVIDIA 12 ГБ — проверенный класс для текущего local profile, не минимальный requirement |

Оригиналы, неучаствующие в обработке, можно держать на NAS. Для интенсивного INGEST/preview желателен стабильный 1 Gbit/s LAN; медленная сеть увеличивает время чтения файлов. SSD рекомендуется прежде всего для PostgreSQL, job queue, preview/fingerprint metadata и temp-файлов. Ёмкость оригинального хранилища считать отдельно от system/database disk; предусмотреть рост preview, derivatives и резервных копий.

**Без GPU:** основной сайт, PostgreSQL, фото/видео каталог, QWEN через облачный provider, CPU DINO/HYBRID и CPU video transcode остаются возможными. Тяжёлые локальные этапы будут медленнее. Облако для QWEN не делает всё приложение «облачным».

**С GPU:** DINO batch в текущем runner остаётся CPU-only. GPU ускоряет сборку fingerprint; локальный QWEN тоже может использовать GPU через Ollama. Эти задачи делят VRAM, если выполняются одновременно.

### 7.3 Измеренные ориентиры текущей машины

На AMD Ryzen 5 5600 (6C/12T), 31 ГБ RAM, RTX 3060 12 ГБ для сборки fingerprint по 25 фото измерено: GPU пик около **1120 сборок/ч при parallel=3**, CPU пик около **628 сборок/ч при parallel=6**. Это throughput конкретного synthetic/local workload, не скорость DINO на каждом фото и не гарантия SLA. Другая метрика с текущего корпуса: DINO batch из 254 фото исполнялся примерно за 92 секунды на CPU; она также не является универсальной гарантией.

## 8. Размещение, конфигурация и сеть

- Постоянные оригиналы хранить в отдельных mount roots; задать `SCENE_ORIGINALS_ROOTS` и `SCENE_SOURCE_ROOTS`. Пустой originals allowlist означает fail-closed выдачу originals.
- Writable данные размещать отдельно: PostgreSQL volume, `SCENE_DATA`, preview roots, video storyboard/derivative roots, inbox и backups. DB backups и originals backups — разные задачи.
- Секреты (DB password, service tokens, user passwords, QWEN API key, Albion key) не класть в git или логи. Для systemd использовать защищённый env file; единицы запуска должны иметь доступ к оригиналам для чтения и к служебным roots для записи.
- Для LAN разместить API за внутренним reverse proxy или ограничить доступ firewall. Для Internet использовать HTTPS, bearer/session auth, scopes least privilege и конкретные `SCENE_CORS_ORIGINS`; PostgreSQL наружу не публиковать.
- Если checkout содержит пробелы в пути, systemd `WorkingDirectory` в локальной user-unit конфигурации указывать через symlink вроде `~/scene-fingerprint`. User units для автозапуска до login требуют systemd lingering.
- Schema migration применить к целевой БД до запуска кода, зависящего от новых колонок. `scripts/migrate.py` применяет все pending файлы; перед запуском проверять `--status`, backup и незнакомые/пользовательские migration-файлы. Не выполнять рабочие миграции автоматически при каждом старте без явно настроенного безопасного runbook.

## 9. Эксплуатационные ограничения и нецели

- Система не является SaaS/PaaS multi-tenant кластером; горизонтальное масштабирование и HA PostgreSQL отдельно не спроектированы этим документом.
- Нельзя смешивать durable video registry с transient video-файлом, используемым для поиска по кадрам.
- Video metadata identity — hash basename/date/size, не content fingerprint. Она не обнаруживает различные bytes при совпадении этих метаданных.
- Редактирование видео — только trim/transcode с сохранением оригинала; это не монтажный workstation.
- QWEN cloud передаёт изображение внешнему провайдеру. Не включать без политики приватности, подходящего договора и явного решения о data residency.
- Albion-провайдер/link upload требует внешней настройки и не считается готовым без предоставленных и проверенных credentials/endpoint.
- Billboard detection присутствует как отдельный экспериментальный WIP и не включён в основной описанный pipeline/обязательные runtime требования.

## 10. Файлы для первичной настройки

- `deploy/systemd/README.md` — основной server/user-systemd runbook.
- `deploy/systemd/user/scene.env.example` — пример env-переменных; значения с путями специфичны для workstation и должны быть заменены.
- `docs/db_setup.md` — PostgreSQL, migration runner, baseline/backup notes.
- `docs/auth_roles.md` — роли/scopes.
- `docs/ingest.md`, `docs/preview.txt`, `docs/dino.txt`, `docs/hybrid.txt`, `docs/video.md`, `docs/qwen_process.md` — component contracts.
- `frontend/package.json` и `pyproject.toml` — зависимости и команды build/test.
