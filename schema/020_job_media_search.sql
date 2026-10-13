-- Smart media-search job type (searching the base by an uploaded photo).
--
-- The QWEN vision model has to describe the uploaded image, so the work runs
-- in the worker (never in an HTTP request handler) like DINO/HYBRID/QWEN.
-- The uploaded image is transient: it is stored in the inbox only until the
-- job finishes, then the worker deletes it.
--
-- Rollback: drop the constraint addition and re-create it without
-- 'MEDIA_SEARCH' (the same ALTER as migration 019). No data is touched.

ALTER TABLE job_queue
    DROP CONSTRAINT IF EXISTS job_queue_job_type_check;

ALTER TABLE job_queue
    ADD CONSTRAINT job_queue_job_type_check
    CHECK (
        job_type IN (
            'DINO_BATCH',
            'HYBRID_RUN',
            'QWEN_PHOTO',
            'NL_SEARCH',
            'INGEST_DIR',
            'MEDIA_SEARCH'
        )
    );
