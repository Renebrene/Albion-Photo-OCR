-- Metadata identity for photos (scheme "metadata-v1", docs/identity_shadow.md).
--
-- Existing rows keep their content-SHA photo_id and sha256. New rows under
-- SCENE_IDENTITY_SCHEME=metadata-v1 carry identity_hash and a NULL sha256.
-- Running the switch without this migration fails loudly in
-- app/ingest/metadata_register.py.
--
-- Backfill (optional before the switch, reads only EXIF):
--   python scripts/backfill_photo_identity.py --dry-run
--   python scripts/backfill_photo_identity.py
--
-- Rollback, only after switching back to SCENE_IDENTITY_SCHEME=sha256 and
-- checking that no sha256 IS NULL:
--   DROP INDEX IF EXISTS public.ux_photos_identity_hash;
--   ALTER TABLE public.photos DROP COLUMN IF EXISTS identity_scheme;
--   ALTER TABLE public.photos DROP COLUMN IF EXISTS identity_hash;
--   ALTER TABLE public.photos ALTER COLUMN sha256 SET NOT NULL;

ALTER TABLE public.photos
    ADD COLUMN identity_hash CHAR(64)
        CHECK (identity_hash IS NULL OR identity_hash ~ '^[0-9a-f]{64}$'),
    ADD COLUMN identity_scheme TEXT NOT NULL DEFAULT 'legacy-content-sha256'
        CHECK (identity_scheme IN ('legacy-content-sha256', 'metadata-v1')),
    ALTER COLUMN sha256 DROP NOT NULL;

CREATE UNIQUE INDEX ux_photos_identity_hash
    ON public.photos (identity_hash)
    WHERE identity_hash IS NOT NULL;
