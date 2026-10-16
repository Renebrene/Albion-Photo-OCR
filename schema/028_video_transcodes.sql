-- Asynchronous MP4/H.264 derivatives for durable video assets.
-- This migration does not touch source files or existing photo rows.
--
-- Rollback after disabling transcode workers/routes and preserving derivatives:
--   ALTER TABLE public.video_playback_tickets DROP COLUMN IF EXISTS derivative_id;
--   ALTER TABLE public.video_playback_tickets DROP CONSTRAINT IF EXISTS video_playback_tickets_action_check;
--   ALTER TABLE public.video_playback_tickets ADD CONSTRAINT video_playback_tickets_action_check
--       CHECK (action IN ('inline', 'attachment'));
--   DROP TABLE IF EXISTS public.video_derivatives;
--   ALTER TABLE public.job_queue DROP CONSTRAINT IF EXISTS job_queue_job_type_check;
--   ... recreate without VIDEO_TRANSCODE.

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
            'VIDEO_TRANSCODE'
        )
    );

CREATE TABLE public.video_derivatives (
    derivative_id       BIGSERIAL PRIMARY KEY,
    video_id            TEXT NOT NULL REFERENCES public.video_assets(video_id) ON DELETE CASCADE,
    profile             TEXT NOT NULL CHECK (profile IN ('strong_720p', 'standard_1080p', 'light_1440p')),
    source_sha256       CHAR(64) NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    status              TEXT NOT NULL DEFAULT 'PENDING'
                        CHECK (status IN ('PENDING', 'RUNNING', 'DONE', 'FAILED', 'CANCELLED')),
    job_id              BIGINT REFERENCES public.job_queue(id) ON DELETE SET NULL,
    output_path         TEXT,
    output_sha256       CHAR(64) CHECK (output_sha256 IS NULL OR output_sha256 ~ '^[0-9a-f]{64}$'),
    output_size_bytes   BIGINT CHECK (output_size_bytes IS NULL OR output_size_bytes > 0),
    width               INTEGER CHECK (width IS NULL OR width > 0),
    height              INTEGER CHECK (height IS NULL OR height > 0),
    duration_seconds    DOUBLE PRECISION CHECK (duration_seconds IS NULL OR duration_seconds > 0),
    fps                 DOUBLE PRECISION CHECK (fps IS NULL OR fps > 0),
    video_codec         TEXT,
    encoder             TEXT,
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    UNIQUE (video_id, profile, source_sha256),
    CHECK (status <> 'DONE' OR (output_path IS NOT NULL AND output_sha256 IS NOT NULL))
);

CREATE INDEX ix_video_derivatives_video_created
    ON public.video_derivatives (video_id, created_at DESC);

CREATE UNIQUE INDEX ix_video_transcode_active_dedup
    ON public.job_queue ((payload ->> 'video_id'), (payload ->> 'profile'), (payload ->> 'source_sha256'))
    WHERE job_type = 'VIDEO_TRANSCODE' AND status IN ('PENDING', 'RUNNING', 'PAUSED');

ALTER TABLE public.video_playback_tickets
    ADD COLUMN derivative_id BIGINT REFERENCES public.video_derivatives(derivative_id) ON DELETE CASCADE;

ALTER TABLE public.video_playback_tickets
    DROP CONSTRAINT IF EXISTS video_playback_tickets_action_check;

ALTER TABLE public.video_playback_tickets
    ADD CONSTRAINT video_playback_tickets_action_check
    CHECK (action IN ('inline', 'attachment', 'derivative_attachment'));
