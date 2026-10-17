-- Manual legal-address override for one photo.
--
-- DINO/HYBRID may recognise the wrong address; the owner can correct it in
-- the photo card. The override lives next to the recognition data, so the
-- originals and recognition runs are never modified.
--
-- Additive and idempotent. Rollback:
--   DROP TABLE IF EXISTS public.photo_address_overrides;

CREATE TABLE IF NOT EXISTS public.photo_address_overrides (
    photo_id    TEXT PRIMARY KEY
                REFERENCES public.photos(photo_id) ON DELETE CASCADE,
    address_id  INTEGER NOT NULL
                REFERENCES public.address_directory(address_id)
                ON DELETE CASCADE,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_photo_address_overrides_address
    ON public.photo_address_overrides (address_id);
