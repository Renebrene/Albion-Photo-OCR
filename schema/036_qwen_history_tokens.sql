-- История описаний QWEN и учёт токенов облачного провайдера.
--
-- `photo_qwen` — одна строка на фото: успешный ответ перезаписывает прежние
-- поля. Владелец просил полную перезапись И историю версий (чтобы сменить
-- модель и сравнить/откатиться), поэтому прежний результат перед перезаписью
-- кладётся в `photo_qwen_history`.
--
-- Учёт токенов: облачный провайдер возвращает `usage` в ответе, но он нигде не
-- сохранялся. Здесь появляются колонки на самой строке и в истории — в карточке
-- «Распознавание» виден расход при облачном провайдере (локальная Ollama
-- токенов не отдаёт, там значения остаются NULL).
--
-- Аддитивно: существующие строки не меняются, backfill не требуется.
--
-- Откат:
--   ALTER TABLE public.photo_qwen DROP COLUMN IF EXISTS prompt_tokens;
--   ALTER TABLE public.photo_qwen DROP COLUMN IF EXISTS completion_tokens;
--   ALTER TABLE public.photo_qwen DROP COLUMN IF EXISTS total_tokens;
--   DROP TABLE IF EXISTS public.photo_qwen_history;

CREATE TABLE IF NOT EXISTS public.photo_qwen_history (
    history_id      BIGSERIAL PRIMARY KEY,

    photo_id        TEXT NOT NULL,

    status          TEXT NOT NULL,
    description     TEXT,
    address         TEXT,
    client          TEXT,
    brand           TEXT,
    category        TEXT,
    tags            JSONB,
    raw             JSONB,

    qwen_model      TEXT,
    qwen_time_sec   DOUBLE PRECISION,
    error_message   TEXT,

    prompt_tokens     INTEGER,
    completion_tokens INTEGER,
    total_tokens      INTEGER,

    -- Когда был получен этот результат и когда его вытеснил новый.
    finished_at     TIMESTAMP,
    replaced_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Модель, которая перезаписала запись (для сравнения моделей).
    replaced_by_model TEXT
);

CREATE INDEX IF NOT EXISTS idx_photo_qwen_history_photo
    ON public.photo_qwen_history (photo_id, history_id DESC);

ALTER TABLE public.photo_qwen
    ADD COLUMN IF NOT EXISTS prompt_tokens INTEGER;

ALTER TABLE public.photo_qwen
    ADD COLUMN IF NOT EXISTS completion_tokens INTEGER;

ALTER TABLE public.photo_qwen
    ADD COLUMN IF NOT EXISTS total_tokens INTEGER;
