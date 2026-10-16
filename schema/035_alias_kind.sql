-- Нормализация не только клиентов, но и брендов QWEN.
--
-- До этой миграции справочник `client_aliases` умел только клиентов: одна
-- таблица, PK по `alias`. Бренд QWEN — такая же «изобретённая» строка, её нужно
-- приводить к канонической тем же способом, поэтому справочник получает
-- колонку `kind` ('client' | 'brand'), а PK становится составным
-- (kind, alias): одно и то же написание теоретически может быть и клиентом, и
-- брендом.
--
-- Журнал правок `client_alias_audit` получает ту же колонку, чтобы в истории
-- было видно, что именно правили.
--
-- ВАЖНО: код, который читает `kind`, требует применённой 035 — миграцию надо
-- применить до перезапуска scene-api. Существующие строки становятся
-- 'client' (backfill), поэтому поведение прежнего справочника не меняется.
--
-- Идемпотентно: повторное применение не меняет данные.
--
-- Откат (теряет бренд-строки, поэтому только если их нет):
--   DELETE FROM public.client_alias_audit WHERE kind = 'brand';
--   DELETE FROM public.client_aliases WHERE kind = 'brand';
--   ALTER TABLE public.client_aliases DROP CONSTRAINT IF EXISTS client_aliases_pkey;
--   ALTER TABLE public.client_aliases DROP CONSTRAINT IF EXISTS client_aliases_kind_check;
--   ALTER TABLE public.client_aliases DROP COLUMN IF EXISTS kind;
--   ALTER TABLE public.client_aliases ADD PRIMARY KEY (alias);
--   ALTER TABLE public.client_alias_audit DROP COLUMN IF EXISTS kind;

ALTER TABLE public.client_aliases
    ADD COLUMN IF NOT EXISTS kind TEXT;

UPDATE public.client_aliases SET kind = 'client' WHERE kind IS NULL;

ALTER TABLE public.client_aliases
    ALTER COLUMN kind SET DEFAULT 'client';

ALTER TABLE public.client_aliases
    ALTER COLUMN kind SET NOT NULL;

ALTER TABLE public.client_alias_audit
    ADD COLUMN IF NOT EXISTS kind TEXT;

UPDATE public.client_alias_audit SET kind = 'client' WHERE kind IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'client_aliases_kind_check'
          AND conrelid = 'public.client_aliases'::regclass
    ) THEN
        ALTER TABLE public.client_aliases
            ADD CONSTRAINT client_aliases_kind_check
            CHECK (kind IN ('client', 'brand'));
    END IF;
END $$;

-- PK меняется на составной (kind, alias): сначала снять старый, потом поставить
-- новый. IF EXISTS/IF NOT EXISTS делают шаг повторяемым.
ALTER TABLE public.client_aliases
    DROP CONSTRAINT IF EXISTS client_aliases_pkey;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'client_aliases_pkey'
          AND conrelid = 'public.client_aliases'::regclass
    ) THEN
        ALTER TABLE public.client_aliases
            ADD CONSTRAINT client_aliases_pkey PRIMARY KEY (kind, alias);
    END IF;
END $$;
