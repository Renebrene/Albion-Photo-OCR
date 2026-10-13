-- Trigram (pg_trgm) GIN indexes for ILIKE search.
--
-- The `q` search uses `col ILIKE '%needle%'`, which a btree cannot serve.
-- Trigram GIN indexes make substring/ILIKE search index-assisted.
--
-- The extension must exist (created by 000_bootstrap as superuser). If it is
-- absent, this file only emits a NOTICE and creates nothing, so bootstrap
-- still succeeds on hosts without pg_trgm.
--
-- Indexed columns are the ones directly searched today:
--   photos.filename, photo_qwen.client/brand/category/description.
-- The `address` filter is applied to a computed column (COALESCE over
-- hybrid/dino results), so it cannot use an index in the current query shape.
--
-- Idempotent: safe to re-apply.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
    ) THEN
        RAISE NOTICE
            'pg_trgm not installed; skipping trigram search indexes (schema/014)';
        RETURN;
    END IF;

    CREATE INDEX IF NOT EXISTS idx_photos_filename_trgm
        ON public.photos USING gin (filename gin_trgm_ops);

    CREATE INDEX IF NOT EXISTS idx_photo_qwen_client_trgm
        ON public.photo_qwen USING gin (client gin_trgm_ops);

    CREATE INDEX IF NOT EXISTS idx_photo_qwen_brand_trgm
        ON public.photo_qwen USING gin (brand gin_trgm_ops);

    CREATE INDEX IF NOT EXISTS idx_photo_qwen_category_trgm
        ON public.photo_qwen USING gin (category gin_trgm_ops);

    CREATE INDEX IF NOT EXISTS idx_photo_qwen_description_trgm
        ON public.photo_qwen USING gin (description gin_trgm_ops);
END
$$;
