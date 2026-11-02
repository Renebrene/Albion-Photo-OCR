-- Second perceptual hash for billboard crops: pHash (DCT).
-- dHash (crop_phash) reacts to layout/brightness; pHash is more stable for
-- the same creative at a different scale. Search uses both.

ALTER TABLE public.photo_regions
    ADD COLUMN IF NOT EXISTS crop_phash_p BIGINT;

CREATE INDEX IF NOT EXISTS ix_photo_regions_crop_phash_p
    ON public.photo_regions (crop_phash_p)
    WHERE kind = 'billboard';

-- Rollback:
-- DROP INDEX IF EXISTS public.ix_photo_regions_crop_phash_p;
-- ALTER TABLE public.photo_regions DROP COLUMN IF EXISTS crop_phash_p;
