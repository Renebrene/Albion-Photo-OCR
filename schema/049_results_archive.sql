-- Архив результатов распознавания (нулевое состояние без потери истории).
--
-- Результаты DINO, HYBRID, QWEN и регионов-кропов переносятся в таблицы
-- `*_archive`, а рабочие таблицы очищаются: интерфейс и счётчики начинают с
-- нуля, но старая история распознавания остаётся доступной для разбора.
-- Переносит rows scripts/archive_results.py; сама миграция создаёт только
-- приёмники.
--
-- Архивные таблицы — копии по составу колонок (LIKE ... INCLUDING DEFAULTS
-- INCLUDING GENERATED), но БЕЗ внешних ключей и без индексов источника: иначе
-- очистка рабочей таблицы упёрлась бы в ссылку из архива. Дополнительно
-- добавляется `archived_at` (когда запись ушла в архив) и индекс по
-- натуральному ключу — по нему архив сверяют и выгружают.
--
-- Откат (архив нужен, пока данные лежат в нём):
--   INSERT INTO public.<таблица> SELECT <колонки без archived_at>
--       FROM public.<таблица>_archive;
--   DROP TABLE public.<таблица>_archive;

CREATE TABLE IF NOT EXISTS public.dino_batches_archive (
    LIKE public.dino_batches INCLUDING DEFAULTS INCLUDING GENERATED
);
ALTER TABLE public.dino_batches_archive
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS ix_dino_batches_archive_batch
    ON public.dino_batches_archive (batch_id);

CREATE TABLE IF NOT EXISTS public.dino_runs_archive (
    LIKE public.dino_runs INCLUDING DEFAULTS INCLUDING GENERATED
);
ALTER TABLE public.dino_runs_archive
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS ix_dino_runs_archive_photo
    ON public.dino_runs_archive (photo_id);
CREATE INDEX IF NOT EXISTS ix_dino_runs_archive_run
    ON public.dino_runs_archive (run_id);

CREATE TABLE IF NOT EXISTS public.dino_candidates_archive (
    LIKE public.dino_candidates INCLUDING DEFAULTS INCLUDING GENERATED
);
ALTER TABLE public.dino_candidates_archive
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS ix_dino_candidates_archive_run
    ON public.dino_candidates_archive (run_id);

CREATE TABLE IF NOT EXISTS public.hybrid_runs_archive (
    LIKE public.hybrid_runs INCLUDING DEFAULTS INCLUDING GENERATED
);
ALTER TABLE public.hybrid_runs_archive
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS ix_hybrid_runs_archive_run
    ON public.hybrid_runs_archive (hybrid_run_id);

CREATE TABLE IF NOT EXISTS public.hybrid_results_archive (
    LIKE public.hybrid_results INCLUDING DEFAULTS INCLUDING GENERATED
);
ALTER TABLE public.hybrid_results_archive
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS ix_hybrid_results_archive_photo
    ON public.hybrid_results_archive (photo_id);

CREATE TABLE IF NOT EXISTS public.photo_qwen_archive (
    LIKE public.photo_qwen INCLUDING DEFAULTS INCLUDING GENERATED
);
ALTER TABLE public.photo_qwen_archive
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS ix_photo_qwen_archive_photo
    ON public.photo_qwen_archive (photo_id);

CREATE TABLE IF NOT EXISTS public.photo_qwen_history_archive (
    LIKE public.photo_qwen_history INCLUDING DEFAULTS INCLUDING GENERATED
);
ALTER TABLE public.photo_qwen_history_archive
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS public.photo_regions_archive (
    LIKE public.photo_regions INCLUDING DEFAULTS INCLUDING GENERATED
);
ALTER TABLE public.photo_regions_archive
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS ix_photo_regions_archive_photo
    ON public.photo_regions_archive (photo_id);
