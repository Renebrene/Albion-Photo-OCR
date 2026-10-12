-- Job queue for deferred processing (DINO batches, HYBRID runs).
--
-- The web API only enqueues work here; a separate worker process
-- (app.jobs.worker) claims and executes jobs, so no heavy inference ever
-- runs inside an HTTP request handler.
--
-- Idempotent: safe to re-apply.

CREATE TABLE IF NOT EXISTS job_queue (
    id            BIGSERIAL PRIMARY KEY,

    job_type      TEXT NOT NULL
                  CHECK (job_type IN ('DINO_BATCH', 'HYBRID_RUN')),

    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,

    status        TEXT NOT NULL DEFAULT 'PENDING'
                  CHECK (status IN (
                      'PENDING',
                      'RUNNING',
                      'DONE',
                      'FAILED'
                  )),

    attempts      INTEGER NOT NULL DEFAULT 0
                  CHECK (attempts >= 0),

    result        JSONB,

    error_message TEXT,

    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at    TIMESTAMP,
    finished_at   TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_job_queue_status
    ON job_queue(status, id);
