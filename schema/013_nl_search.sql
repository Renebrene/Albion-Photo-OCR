-- Natural-language search job type.
--
-- The NL query is translated to structured filters by the local QWEN model
-- inside the worker (never in an HTTP request handler), then the normal photo
-- search runs. Only the shared queue's job_type CHECK is widened here.
--
-- Idempotent: safe to re-apply.

ALTER TABLE job_queue
    DROP CONSTRAINT IF EXISTS job_queue_job_type_check;

ALTER TABLE job_queue
    ADD CONSTRAINT job_queue_job_type_check
    CHECK (job_type IN ('DINO_BATCH', 'HYBRID_RUN', 'QWEN_PHOTO', 'NL_SEARCH'));
