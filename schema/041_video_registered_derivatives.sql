-- Add metadata-based identities for new videos and link completed derivatives
-- as independent assets. Existing content-derived IDs and hashes are retained.
-- Rollback after disabling video routes/workers and retaining asset history:
--   ALTER TABLE public.video_derivatives DROP CONSTRAINT IF EXISTS video_derivatives_done_output_check;
--   ALTER TABLE public.video_derivatives ADD CONSTRAINT video_derivatives_check
--       CHECK (status <> 'DONE' OR (output_path IS NOT NULL AND output_sha256 IS NOT NULL));
--   ALTER TABLE public.video_derivatives DROP COLUMN IF EXISTS output_identity_date;
--   ALTER TABLE public.video_derivatives DROP COLUMN IF EXISTS source_identity_scheme;
--   ALTER TABLE public.video_derivatives DROP COLUMN IF EXISTS asset_video_id;
--   ALTER TABLE public.video_assets DROP COLUMN IF EXISTS parent_video_id;
--   ALTER TABLE public.video_assets DROP COLUMN IF EXISTS source_derivative_id;
--   DROP INDEX IF EXISTS public.ux_video_assets_identity_hash;
--   ALTER TABLE public.video_assets DROP COLUMN IF EXISTS identity_hash;
--   ALTER TABLE public.video_assets DROP COLUMN IF EXISTS identity_date;
--   ALTER TABLE public.video_assets DROP COLUMN IF EXISTS identity_scheme;
--   ALTER TABLE public.video_assets ALTER COLUMN sha256 SET NOT NULL;
-- Existing derivative files and video rows are intentionally not deleted.

ALTER TABLE public.video_assets
    ADD COLUMN identity_hash CHAR(64)
        CHECK (identity_hash IS NULL OR identity_hash ~ '^[0-9a-f]{64}$'),
    ADD COLUMN identity_date DATE,
    ADD COLUMN identity_scheme TEXT NOT NULL DEFAULT 'legacy-content-sha256'
        CHECK (identity_scheme IN ('legacy-content-sha256', 'metadata-v1')),
    ALTER COLUMN sha256 DROP NOT NULL,
    ADD COLUMN parent_video_id TEXT REFERENCES public.video_assets(video_id) ON DELETE SET NULL,
    ADD COLUMN source_derivative_id BIGINT UNIQUE REFERENCES public.video_derivatives(derivative_id) ON DELETE SET NULL;

CREATE UNIQUE INDEX ux_video_assets_identity_hash
    ON public.video_assets (identity_hash)
    WHERE identity_hash IS NOT NULL;

ALTER TABLE public.video_derivatives
    DROP CONSTRAINT IF EXISTS video_derivatives_check;

ALTER TABLE public.video_derivatives
    ADD CONSTRAINT video_derivatives_done_output_check
        CHECK (status <> 'DONE' OR (output_path IS NOT NULL AND (output_sha256 IS NOT NULL OR output_size_bytes IS NOT NULL))),
    ADD COLUMN source_identity_scheme TEXT NOT NULL DEFAULT 'legacy-content-sha256'
        CHECK (source_identity_scheme IN ('legacy-content-sha256', 'metadata-v1')),
    ADD COLUMN asset_video_id TEXT UNIQUE REFERENCES public.video_assets(video_id) ON DELETE SET NULL,
    ADD COLUMN output_identity_date DATE;
