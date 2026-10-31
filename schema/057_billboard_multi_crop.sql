-- Persist one ordered photo_regions row per detected billboard crop.
-- Existing legacy billboard rows receive crop_index=0 and remain primary.
-- Test on a disposable populated database before any operational rollout.

ALTER TABLE public.photo_regions
    ADD COLUMN IF NOT EXISTS crop_index INTEGER NOT NULL DEFAULT 0
    CHECK (crop_index >= 0);

DROP INDEX IF EXISTS public.ux_photo_regions_one_billboard;

CREATE UNIQUE INDEX IF NOT EXISTS ux_photo_regions_photo_crop
    ON public.photo_regions (photo_id, kind, crop_index)
    WHERE kind = 'billboard';

CREATE INDEX IF NOT EXISTS ix_photo_regions_capture_crop
    ON public.photo_regions (photo_taken_at, crop_index)
    WHERE kind = 'billboard';

-- Rollback is only safe after removing secondary rows and verifying one
-- billboard row remains for each photo. Never execute that cleanup blindly.
-- DROP INDEX IF EXISTS public.ix_photo_regions_capture_crop;
-- DROP INDEX IF EXISTS public.ux_photo_regions_photo_crop;
-- ALTER TABLE public.photo_regions DROP COLUMN IF EXISTS crop_index;
-- CREATE UNIQUE INDEX public.ux_photo_regions_one_billboard
--     ON public.photo_regions (photo_id, kind) WHERE kind = 'billboard';
