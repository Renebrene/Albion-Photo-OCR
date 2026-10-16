-- Trim-only video derivatives. Existing fixed-profile transcodes remain valid.
-- Do not change or delete source video_assets; each trim is a separate derivative.
-- Rollback after disabling trim endpoints/workers (preserve generated files/history):
--   DROP INDEX IF EXISTS public.ix_video_trim_active_dedup;
--   ALTER TABLE public.video_playback_tickets DROP CONSTRAINT IF EXISTS video_playback_tickets_action_check;
--   ALTER TABLE public.video_playback_tickets ADD CONSTRAINT video_playback_tickets_action_check
--     CHECK (action IN ('inline', 'attachment', 'derivative_attachment'));
--   ALTER TABLE public.video_derivatives DROP CONSTRAINT IF EXISTS video_derivatives_profile_check;
--   ALTER TABLE public.video_derivatives ADD CONSTRAINT video_derivatives_profile_check
--     CHECK (profile IN ('strong_720p', 'standard_1080p', 'light_1440p'));
--   ALTER TABLE public.video_derivatives ADD CONSTRAINT video_derivatives_video_id_profile_source_sha256_key
--     UNIQUE (video_id, profile, source_sha256);
--   ALTER TABLE public.job_queue DROP CONSTRAINT IF EXISTS job_queue_job_type_check;
--   -- Recreate the current constraint without VIDEO_TRIM/VIDEO_STORYBOARD.
--   ALTER TABLE public.video_derivatives DROP COLUMN IF EXISTS operation_key;
--   ALTER TABLE public.video_derivatives DROP COLUMN IF EXISTS start_seconds;
--   ALTER TABLE public.video_derivatives DROP COLUMN IF EXISTS end_seconds;
--   ALTER TABLE public.video_derivatives DROP COLUMN IF EXISTS operation_kind;

ALTER TABLE public.job_queue
    DROP CONSTRAINT IF EXISTS job_queue_job_type_check;

ALTER TABLE public.job_queue
    ADD CONSTRAINT job_queue_job_type_check
    CHECK (
        job_type IN (
            'DINO_BATCH',
            'HYBRID_RUN',
            'QWEN_PHOTO',
            'NL_SEARCH',
            'INGEST_DIR',
            'MEDIA_SEARCH',
            'FINGERPRINT_BUILD',
            'VIDEO_TRANSCODE',
            'PHOTO_PREVIEW',
            'VIDEO_TRIM',
            'VIDEO_STORYBOARD'
        )
    );

ALTER TABLE public.video_derivatives
    DROP CONSTRAINT IF EXISTS video_derivatives_video_id_profile_source_sha256_key;

ALTER TABLE public.video_derivatives
    DROP CONSTRAINT IF EXISTS video_derivatives_profile_check;

ALTER TABLE public.video_derivatives
    ADD CONSTRAINT video_derivatives_profile_check
    CHECK (profile IN ('strong_720p', 'standard_1080p', 'light_1440p', 'trim'));

ALTER TABLE public.video_derivatives
    ADD COLUMN operation_kind TEXT NOT NULL DEFAULT 'TRANSCODE'
        CHECK (operation_kind IN ('TRANSCODE', 'TRIM')),
    ADD COLUMN start_seconds DOUBLE PRECISION,
    ADD COLUMN end_seconds DOUBLE PRECISION,
    ADD COLUMN operation_key TEXT NOT NULL DEFAULT '';

UPDATE public.video_derivatives
SET operation_key = profile || ':' || source_sha256
WHERE operation_key = '';

ALTER TABLE public.video_derivatives
    ADD CONSTRAINT video_derivatives_trim_range_check
        CHECK (
            (operation_kind = 'TRANSCODE' AND start_seconds IS NULL AND end_seconds IS NULL)
            OR
            (operation_kind = 'TRIM' AND profile = 'trim'
             AND start_seconds IS NOT NULL AND start_seconds >= 0
             AND end_seconds IS NOT NULL AND end_seconds > start_seconds)
        );

CREATE UNIQUE INDEX ix_video_derivatives_operation
    ON public.video_derivatives (video_id, source_sha256, operation_key);

CREATE UNIQUE INDEX ix_video_trim_active_dedup
    ON public.job_queue ((payload ->> 'video_id'), (payload ->> 'source_sha256'), (payload ->> 'operation_key'))
    WHERE job_type = 'VIDEO_TRIM' AND status IN ('PENDING', 'RUNNING', 'PAUSED');

CREATE UNIQUE INDEX ix_video_storyboard_active_dedup
    ON public.job_queue ((payload ->> 'video_id'), (payload ->> 'source_sha256'))
    WHERE job_type = 'VIDEO_STORYBOARD' AND status IN ('PENDING', 'RUNNING', 'PAUSED');

ALTER TABLE public.video_playback_tickets
    DROP CONSTRAINT IF EXISTS video_playback_tickets_action_check;

ALTER TABLE public.video_playback_tickets
    ADD CONSTRAINT video_playback_tickets_action_check
    CHECK (action IN ('inline', 'attachment', 'derivative_attachment'));
