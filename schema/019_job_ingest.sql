-- Folder INGEST job type.
--
-- Scanning the working folder hashes and decodes every new file, so it runs
-- in the worker (never in an HTTP request handler) like DINO/HYBRID/QWEN.
-- An active job for the same folder is not duplicated.
--
-- Idempotent: safe to re-apply.

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
            'INGEST_DIR'
        )
    );

-- Cheap dedup lookup for active folder ingests.
CREATE INDEX IF NOT EXISTS idx_job_queue_ingest_active_dir
    ON job_queue ((payload ->> 'directory'))
    WHERE job_type = 'INGEST_DIR' AND status IN ('PENDING', 'RUNNING');
