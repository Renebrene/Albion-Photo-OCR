-- Compact archive for finished queue jobs before retention cleanup deletes them.
--
-- The full payload/result can be large (QWEN/DINO batch metadata), so the
-- archive keeps only the fields needed for audits and for resolving a
-- run_history_jobs.job_id: type, status, attempts, photo id, error and times.
-- The user-visible run_history rows themselves are never removed here.
--
-- Rollback:
--   DROP INDEX IF EXISTS public.ix_job_queue_archive_archived;
--   DROP TABLE IF EXISTS public.job_queue_archive;

CREATE TABLE IF NOT EXISTS public.job_queue_archive (
    id               BIGINT PRIMARY KEY,
    job_type         TEXT NOT NULL,
    status           TEXT NOT NULL,
    attempts         INTEGER NOT NULL DEFAULT 0,
    payload_photo_id TEXT,
    error_message    TEXT,
    created_at       TIMESTAMP,
    started_at       TIMESTAMP,
    finished_at      TIMESTAMP,
    archived_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_job_queue_archive_archived
    ON public.job_queue_archive (archived_at);

CREATE INDEX IF NOT EXISTS ix_job_queue_archive_type_status
    ON public.job_queue_archive (job_type, status);
