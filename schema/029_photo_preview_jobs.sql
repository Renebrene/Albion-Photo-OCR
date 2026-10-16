-- Dedicated early CPU queue for photo SMALL/MIDDLE previews.
-- Extends, rather than replaces, job support added by prior migrations.
-- Rollback only after disabling the preview enqueue/worker:
--   DROP INDEX IF EXISTS public.ix_photo_preview_active_dedup;
--   ALTER TABLE public.job_queue DROP CONSTRAINT IF EXISTS job_queue_job_type_check;
--   -- Recreate the current constraint without PHOTO_PREVIEW.

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
            'PHOTO_PREVIEW'
        )
    );

CREATE UNIQUE INDEX ix_photo_preview_active_dedup
    ON public.job_queue ((payload ->> 'photo_id'))
    WHERE job_type = 'PHOTO_PREVIEW' AND status IN ('PENDING', 'RUNNING');
