-- Resumable pipeline supervisor: one run over INGEST -> PREVIEW -> DINO ->
-- HYBRID -> QWEN. The supervisor only enqueues and observes the existing job
-- types (INGEST_DIR, PHOTO_PREVIEW, DINO_BATCH, HYBRID_RUN, QWEN_PHOTO); it
-- never runs inference itself and never rewrites the DINO/HYBRID/QWEN runners.
--
-- Rollback (after stopping the supervisor worker and disabling the endpoints;
-- history is preserved, no source media or child jobs are touched):
--   DROP TABLE IF EXISTS public.pipeline_run_stages;
--   DROP TABLE IF EXISTS public.pipeline_runs;

CREATE TABLE IF NOT EXISTS public.pipeline_runs (
    run_id         BIGSERIAL PRIMARY KEY,
    mode           TEXT NOT NULL DEFAULT 'manual'
                   CHECK (mode IN ('manual', 'schedule', 'outofqueue')),
    status         TEXT NOT NULL DEFAULT 'PENDING'
                   CHECK (status IN (
                       'PENDING', 'RUNNING', 'STOPPED', 'DONE', 'FAILED',
                       'SUPERSEDED'
                   )),
    stage          TEXT NOT NULL DEFAULT 'INGEST'
                   CHECK (stage IN ('INGEST', 'PREVIEW', 'DINO', 'HYBRID', 'QWEN')),
    stop_requested BOOLEAN NOT NULL DEFAULT FALSE,
    folder         TEXT,
    -- Immutable input snapshot: {"files": [...relative names...],
    -- "photo_cutoff": "<ISO timestamp>"}. Recorded once so a resumed run never
    -- picks up media that appeared while it was stopped.
    manifest       JSONB NOT NULL DEFAULT '{}'::jsonb,
    counts         JSONB NOT NULL DEFAULT '{}'::jsonb,
    message        TEXT,
    created_by     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at     TIMESTAMPTZ,
    finished_at    TIMESTAMPTZ,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.pipeline_run_stages (
    run_id       BIGINT NOT NULL
                 REFERENCES public.pipeline_runs(run_id) ON DELETE CASCADE,
    stage        TEXT NOT NULL
                 CHECK (stage IN ('INGEST', 'PREVIEW', 'DINO', 'HYBRID', 'QWEN')),
    position     INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'PENDING'
                 CHECK (status IN ('PENDING', 'RUNNING', 'DONE', 'FAILED', 'SKIPPED')),
    total_count  INTEGER NOT NULL DEFAULT 0,
    done_count   INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    ref          JSONB NOT NULL DEFAULT '{}'::jsonb,
    message      TEXT,
    started_at   TIMESTAMPTZ,
    finished_at  TIMESTAMPTZ,
    PRIMARY KEY (run_id, stage)
);

-- At most one active run at a time; a fresh run supersedes a stopped one.
CREATE UNIQUE INDEX IF NOT EXISTS ux_pipeline_runs_active
    ON public.pipeline_runs ((TRUE))
    WHERE status IN ('PENDING', 'RUNNING');

CREATE INDEX IF NOT EXISTS ix_pipeline_runs_created
    ON public.pipeline_runs (created_at DESC);

CREATE INDEX IF NOT EXISTS ix_pipeline_run_stages_run
    ON public.pipeline_run_stages (run_id);
