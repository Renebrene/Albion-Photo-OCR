-- Worker reliability helpers: job dedup support.
--
-- QWEN jobs are deduplicated by photo_id while active (PENDING/RUNNING): the
-- enqueue path checks for an existing active job in the same statement, and
-- this index keeps that check cheap. It is intentionally NOT unique, so an
-- already-populated queue is never rejected by this migration.
--
-- Idempotent: safe to re-apply.

CREATE INDEX IF NOT EXISTS idx_job_queue_qwen_active_photo
    ON job_queue ((payload ->> 'photo_id'))
    WHERE job_type = 'QWEN_PHOTO' AND status IN ('PENDING', 'RUNNING');
