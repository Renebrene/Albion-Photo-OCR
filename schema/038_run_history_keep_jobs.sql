-- Preserve run history when completed queue rows are cleared.
-- schema/037 originally linked run_history_jobs.job_id to job_queue(id) with
-- ON DELETE CASCADE. Queue retention/cleanup must not erase user-visible history.
-- Rollback (only if queue rows will never be deleted): re-add the FK with
-- ON DELETE CASCADE after removing any orphaned history links.

ALTER TABLE public.run_history_jobs
    DROP CONSTRAINT IF EXISTS run_history_jobs_job_id_fkey;
