-- Allow cancelling a job.
--
-- app.jobs.database.mark_cancelled() flips a PENDING or RUNNING job to
-- CANCELLED (backlog item 2: the СТОП button on a media search). The status
-- CHECK from schema/006 did not list it, so the update was rejected.
--
-- Additive: only widens an allowed-value list, no row is touched. Existing
-- statuses keep their meaning; a cancelled job never reaches the worker.
--
-- Rollback: re-create the constraint without 'CANCELLED' (the ALTER below
-- minus the last value); rows already CANCELLED would have to be set to
-- FAILED first.

ALTER TABLE job_queue
    DROP CONSTRAINT IF EXISTS job_queue_status_check;

ALTER TABLE job_queue
    ADD CONSTRAINT job_queue_status_check
    CHECK (
        status IN (
            'PENDING',
            'RUNNING',
            'DONE',
            'FAILED',
            'CANCELLED'
        )
    );
