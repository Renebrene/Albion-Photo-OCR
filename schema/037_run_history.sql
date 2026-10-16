-- Unified run history for user-visible operations (pipeline, ingest, sort, qwen, scheduler).
--
-- Each user-triggered batch/tick is one row. `run_history_jobs` links queue jobs
-- to that run (one QWEN batch can contain many per-photo jobs, and pipeline jobs
-- can be shared with/duplicate a standalone operation). `log_path` is a relative
-- path under SCENE_RUN_LOG_ROOT (default data/logs); clients never supply or see
-- a filesystem path — logs are read by run_id via the API.
--
-- Additive; no backfill is required. Existing pipeline_runs and job_queue remain
-- the execution sources of truth; this table is the cross-operation index.
--
-- Rollback:
--   DROP TABLE IF EXISTS public.run_history_jobs;
--   DROP TABLE IF EXISTS public.run_history;

CREATE TABLE IF NOT EXISTS public.run_history (
    run_id          BIGSERIAL PRIMARY KEY,
    kind            TEXT NOT NULL
                    CHECK (kind IN ('pipeline', 'ingest', 'sort', 'qwen', 'scheduler')),
    mode            TEXT NOT NULL DEFAULT 'manual'
                    CHECK (mode IN ('manual', 'schedule', 'outofqueue')),
    status          TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN (
                        'PENDING', 'RUNNING', 'DONE', 'FAILED', 'PARTIAL',
                        'STOPPED', 'CANCELLED'
                    )),
    source_id       TEXT,
    parent_run_id   BIGINT REFERENCES public.run_history(run_id) ON DELETE SET NULL,
    title           TEXT NOT NULL DEFAULT '',
    counts          JSONB NOT NULL DEFAULT '{}'::jsonb,
    stages          JSONB NOT NULL DEFAULT '[]'::jsonb,
    error_count     INTEGER NOT NULL DEFAULT 0 CHECK (error_count >= 0),
    enqueue_complete BOOLEAN NOT NULL DEFAULT FALSE,
    message         TEXT,
    log_path        TEXT,
    created_by      TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_run_history_kind_started
    ON public.run_history (kind, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_run_history_status
    ON public.run_history (status, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_run_history_parent
    ON public.run_history (parent_run_id);

CREATE TABLE IF NOT EXISTS public.run_history_jobs (
    run_id      BIGINT NOT NULL
                REFERENCES public.run_history(run_id) ON DELETE CASCADE,
    job_id      BIGINT NOT NULL,
    linked_at   TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_id, job_id)
);

CREATE INDEX IF NOT EXISTS ix_run_history_jobs_job
    ON public.run_history_jobs (job_id);
