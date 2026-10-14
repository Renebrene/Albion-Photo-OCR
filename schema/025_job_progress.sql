-- Progress and pause for long jobs (fingerprint building).
--
--   progress - what the running job has done so far, written by the worker
--              while it works: {done, total, stage, percent, updated_at}. The
--              window polls the job row and draws a progress bar from it.
--   PAUSED   - a new status. A PENDING job set to PAUSED is simply not claimed;
--              a RUNNING job notices between batches, waits and continues when
--              it is resumed (the wait is bounded by the worker, see
--              SCENE_PAUSE_MAX_SECONDS).
--
-- Additive; existing rows keep NULL progress and their status.
--
-- Rollback:
--   ALTER TABLE job_queue DROP COLUMN IF EXISTS progress;
--   ALTER TABLE job_queue DROP CONSTRAINT job_queue_status_check;
--   ... re-create it without 'PAUSED' (as in schema/021);

ALTER TABLE job_queue
    ADD COLUMN IF NOT EXISTS progress JSONB;

ALTER TABLE job_queue
    DROP CONSTRAINT IF EXISTS job_queue_status_check;

ALTER TABLE job_queue
    ADD CONSTRAINT job_queue_status_check
    CHECK (
        status IN (
            'PENDING',
            'RUNNING',
            'PAUSED',
            'DONE',
            'FAILED',
            'CANCELLED'
        )
    );
