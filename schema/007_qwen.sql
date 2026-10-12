-- QWEN metadata: a parallel, DINO-independent enrichment step.
--
-- One row per photo, written by app/qwen (via app.jobs.worker). It never
-- affects photo identity or the DINO/HYBRID pipeline; it only adds textual
-- metadata (description, address, client, brand, category, tags).
--
-- Idempotent: safe to re-apply.

CREATE TABLE IF NOT EXISTS photo_qwen (
    photo_id       TEXT PRIMARY KEY
                   REFERENCES photos(photo_id)
                   ON DELETE CASCADE,

    status         TEXT NOT NULL DEFAULT 'PENDING'
                   CHECK (status IN ('PENDING', 'RUNNING', 'DONE', 'FAILED')),

    description    TEXT,
    address        TEXT,
    client         TEXT,
    brand          TEXT,
    category       TEXT,

    tags           JSONB,
    raw            JSONB,

    qwen_model     TEXT,
    qwen_time_sec  DOUBLE PRECISION,
    error_message  TEXT,

    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at    TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_photo_qwen_status
    ON photo_qwen(status);

CREATE INDEX IF NOT EXISTS idx_photo_qwen_address
    ON photo_qwen(address);

CREATE INDEX IF NOT EXISTS idx_photo_qwen_client
    ON photo_qwen(client);


-- Allow the QWEN_PHOTO job type in the shared queue.
ALTER TABLE job_queue
    DROP CONSTRAINT IF EXISTS job_queue_job_type_check;

ALTER TABLE job_queue
    ADD CONSTRAINT job_queue_job_type_check
    CHECK (job_type IN ('DINO_BATCH', 'HYBRID_RUN', 'QWEN_PHOTO'));
