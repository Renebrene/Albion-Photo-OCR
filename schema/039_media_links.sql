-- Cloud media links (Albion limited upload endpoint).
-- Additive: no existing media rows or originals are changed. Links are only
-- metadata; the uploaded object lives in Albion. Expired links are filtered
-- from the API and marked EXPIRED lazily.
--
-- Rollback after disabling the MEDIA_EXPORT worker and cloud endpoints:
--   ALTER TABLE public.job_queue DROP CONSTRAINT IF EXISTS job_queue_job_type_check;
--   -- Recreate the current constraint without MEDIA_EXPORT.
--   DROP TABLE IF EXISTS public.media_links;

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
            'VIDEO_STORYBOARD',
            'MEDIA_EXPORT'
        )
    );

CREATE TABLE IF NOT EXISTS public.media_links (
    link_id          BIGSERIAL PRIMARY KEY,
    owner_user_id    TEXT,
    owner_name       TEXT,
    media_kind       TEXT NOT NULL CHECK (media_kind IN ('photo', 'video')),
    media_id         TEXT NOT NULL,
    provider         TEXT NOT NULL DEFAULT 'albion',
    status           TEXT NOT NULL DEFAULT 'PENDING'
                     CHECK (status IN ('PENDING', 'READY', 'FAILED', 'EXPIRED')),
    url              TEXT,
    object_key       TEXT,
    error_message    TEXT,
    job_id           BIGINT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at      TIMESTAMPTZ,
    expires_at       TIMESTAMPTZ,
    CHECK (status <> 'READY' OR (url IS NOT NULL AND expires_at IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS ix_media_links_owner_created
    ON public.media_links (owner_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_media_links_media
    ON public.media_links (media_kind, media_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_media_links_expiry
    ON public.media_links (expires_at)
    WHERE status = 'READY';
CREATE INDEX IF NOT EXISTS ix_media_links_status
    ON public.media_links (status, created_at DESC);
