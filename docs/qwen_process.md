# QWEN — параллельный процесс метаданных (заметки)

**Статус:** заметки по историческим материалам `111/` (легаси-проект `scene_fingerprint_mvp_v02`).
**Реализовано (2026-10-13) в минимальном виде:** `app/qwen/` + `schema/007_qwen.sql` (`photo_qwen`) + `job_type = QWEN_PHOTO`
в очереди; модель по умолчанию `qwen3-vl:8b` через Ollama; поля `description/address/client/brand/category/tags`.
Детали реализации — в [`frontend_quasar.md`](frontend_quasar.md) §6, «Срез 5». Ниже — исторический контекст.

**Коротко:** QWEN — отдельный процесс, который независимо от DINO обогащает фотографии текстовыми метаданными (описание, адрес, клиент, бренд, категория и структурные JSON-поля) через локальную VLM-модель в Ollama. Работает параллельно DINO по одним и тем же `photo_id`.

## 1. Место в архитектуре

Источник: `111/chat_chunks/chunk_131.md` (~520–700), `chunk_234.md`.

```text
                    PostgreSQL
                         │
              ┌──────────┴──────────┐
              │                     │
        dino_status=pending   qwen_status=pending
              │                     │
              ▼                     ▼
       DINO WORKER             QWEN WORKER
       1 процесс               1 процесс
       CPU                     GPU
              │                     │
              └──────────┬──────────┘
                         ▼
                       photos
```

Ключевой принцип: **DINO и Qwen независимы**. Для одного фото:

```text
PH_00000527
      ├──► DINO ──► dino_status=ok
      └──► QWEN ──► qwen_status=ok
```

а не последовательная цепочка `DINO → Qwen → следующая`.

Планировалось в супервизоре (`app/pipeline/supervisor.py`, `run_pipeline()`):

```text
                    ┌── Hybrid v12 ──► внутренний DINO 33
                    │                 └─► TOP1-5 + соседи + hybrid_final_id → PostgreSQL
daily ─> photo_id ──┤
                    └── Qwen ────────► описание → PostgreSQL
```

Позже планировалось убрать отдельный `DINO_WORKER` из супервизора и запускать DINO внутри Hybrid v12, оставив Qwen как параллельную ветку.

## 2. Как работает воркер

- Один постоянно живущий процесс; модель загружается один раз (для DINO — `SceneEmbedder`; для Qwen — Ollama сама держит модель).
- Забор задачи: `SELECT ... FOR UPDATE SKIP LOCKED` по статусу `pending`.
- Обработка одного фото → запись статуса и полей.
- Файлы (легаси): `app/workers/qwen_worker.py`, `app/pipeline/supervisor.py`.

## 3. Модель и транспорт

- Ollama: `http://localhost:11434/api/generate`, `http://localhost:11434/api/chat`.
- Основная модель: `qwen3-vl:4b-instruct`.
- В экспериментах упоминались также `qwen2.5-vl:3b` и `llama3.2-vision:11b`.
- Скрипты генерации/тестов: `scripts/qwen4b_output_v01.py`, `qwen4b_output_v01_before_compact_prompt.py`, `scripts/banner_qwen4b_test_v01.py`, `banner_qwen25vl_test_v01.py`, `banner_model_compare_v0x.py`.
- Роль Qwen: **визуальный помощник / описание / проверка**, не основной цикл распознавания. Ориентир по скорости — порядка нескольких секунд на фото (в обсуждениях фигурировало ~8.75 с/фото).

## 4. Поля вывода (легаси-таблица `photos`)

Из `app/web/photo_db.py`, `app/web/components/search.py`:

- скалярные: `address`, `client`, `brand`, `category`, `description`, `confidence`;
- статус/время: `qwen_status`, `qwen_time_sec`;
- структурные JSON: `text_json`, `colors_json`, `objects_json`, `environment_json`, `image_quality_json`, `camera_view_json`, `scene_objects_json`, `analysis_quality_json`, `raw_json`;
- служебное: `imported_at`.

Отмеченные особенности:
- клиенты «появляются динамически от Qwen» → отдельная сущность/таблица;
- идея «реестра нормализации сущностей» — не править исходные данные Qwen, а нормализовать отдельно (`chunk_087.md` ~2197);
- поиск по Qwen-данным в легаси был только по PostgreSQL (без DINO) — `search_database()`.

## 5. Что важно помнить при возврате

> Историческая заметка на момент анализа (см. §6 — статус изменился).

- В **текущем** репозитории QWEN-процесса нет: есть INGEST/PREVIEW/DINO/HYBRID и схема `001–005`. Колонок `qwen_*`/`*_json` в текущей схеме `photos` тоже нет — это легаси-модель.
- OCR в исторических обсуждениях **исключён** из обязательного roadmap; Qwen — опционален и не должен блокировать базовый цикл.
- Если интегрировать: отдельный процесс + свои статусные колонки/таблица, независимый от DINO, без влияния на `photo_id` и физическую идентичность.
- Нужно решить: где хранить (отдельная таблица `photo_qwen` vs колонки), как версионировать модель/промпт, как обрабатывать динамических клиентов и нормализацию.

## 6. Реализовано в текущем репозитории (2026-10-13)

- Отдельная таблица `photo_qwen` (`schema/007_qwen.sql`), независима от DINO/INGEST; job `QWEN_PHOTO` в `job_queue`.
- Поля: `description, address, client, brand, category, tags[]`. Легаси-JSON-поля (colors/objects/environment/quality) **не переносились** — в промпте их нет.
- **Стабильность парсинга (2026-10-13)**: ответ иногда обрывался по лимиту токенов (`done_reason: "length"`) → JSON не закрывался → `"no JSON object"`. Добавлены `options.num_predict = 512` и ограничение «tags не более 10»; ранее упавшие 2 фото + 1 без строки (MPO) обработаны. Итог: **256/256 DONE**.
- Диагностика/повтор: `GET /v1/qwen/stats` (counts + `failed_photo_ids`); `POST /v1/jobs/qwen {"only_failed": true}` — повторный прогон упавших; кнопка в UI «Настройки → Метаданные QWEN».
- NL-поиск: job `NL_SEARCH` (см. `docs/frontend_quasar.md`, Срез 17).

### 6.1 Провайдеры и keep-alive (2026-10-13)

- **Провайдер** выбирается на рантайме (таблица `app_settings`, поля в UI): `ollama` (локально, по умолчанию) или `openai` — OpenAI-совместимый облачный endpoint (`base_url` + `model` + `api_key`). Ключ хранится в настройках и **маскируется** в ответах (`public_settings`), наружу не отдаётся. Облако — осознанный opt-in: изображения уходят на внешний сервис (в UI есть предупреждение).
- API: `GET /v1/qwen/settings` (маскированный вид), `PUT /v1/qwen/settings` (provider/model/base_url/api_key/keep_alive/unload_on_idle), `GET /v1/qwen/models` (модели активного провайдера), `POST /v1/qwen/unload` (для облака — no-op).
- **Keep-alive**: `QWEN_KEEP_ALIVE` (по умолчанию `10m`) держит локальную модель резидентной между заданиями; `QWEN_UNLOAD_ON_IDLE` заставляет воркер выгружать её, когда очередь опустела. Ручная выгрузка остаётся.
- **Замер (2026-10-13, qwen3-vl:4b-instruct, RTX 3060)**: одно фото cold **9,35 с** vs warm **2,60 с** — ускорение **3,59×**; `ollama ps` подтверждает резидентность. Ожидаемый эффект на очередь ≈ вдвое меньше суммарного времени относительно прежнего `keep_alive: 0` (сохранённое среднее 5,3 с/фото).

## 7. Источники

- `111/chat_chunks/chunk_131.md` (~520–700: схема DINO/QWEN WORKER, `qwen3-vl:4b-instruct`, `localhost:11434`).
- `111/chat_chunks/chunk_234.md` (supervisor `run_pipeline`, Parallel Hybrid+Qwen).
- `111/chat_chunks/chunk_228.md` (`app/workers/qwen_worker.py`).
- `111/chat_chunks/chunk_205.md`, `chunk_087.md` (поля Qwen, клиенты, нормализация).
- `111/chat_chunks/chunk_072.md` (Ollama, варианты моделей).
