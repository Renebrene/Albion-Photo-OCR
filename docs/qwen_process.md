# QWEN — параллельный процесс метаданных (заметки)

**Статус:** заметки по историческим материалам `111/` (легаси-проект `scene_fingerprint_mvp_v02`). Это **не** текущий контракт репозитория и не реализовано в текущем checkout. Сохранено, чтобы вернуться к вопросу позже.

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

- В **текущем** репозитории QWEN-процесса нет: есть INGEST/PREVIEW/DINO/HYBRID и схема `001–005`. Колонок `qwen_*`/`*_json` в текущей схеме `photos` тоже нет — это легаси-модель.
- OCR в исторических обсуждениях **исключён** из обязательного roadmap; Qwen — опционален и не должен блокировать базовый цикл.
- Если интегрировать: отдельный процесс + свои статусные колонки/таблица, независимый от DINO, без влияния на `photo_id` и физическую идентичность.
- Нужно решить: где хранить (отдельная таблица `photo_qwen` vs колонки), как версионировать модель/промпт, как обрабатывать динамических клиентов и нормализацию.

## 6. Источники

- `111/chat_chunks/chunk_131.md` (~520–700: схема DINO/QWEN WORKER, `qwen3-vl:4b-instruct`, `localhost:11434`).
- `111/chat_chunks/chunk_234.md` (supervisor `run_pipeline`, Parallel Hybrid+Qwen).
- `111/chat_chunks/chunk_228.md` (`app/workers/qwen_worker.py`).
- `111/chat_chunks/chunk_205.md`, `chunk_087.md` (поля Qwen, клиенты, нормализация).
- `111/chat_chunks/chunk_072.md` (Ollama, варианты моделей).
