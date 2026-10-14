-- Building a fingerprint from the UI.
--
-- Two additions:
--
--   * job_queue accepts the FINGERPRINT_BUILD type. Building reads the source
--     folder, runs DINOv2 and writes the vectors, so it belongs in the worker
--     (the same queue that already builds INGEST_DIR), not in a request
--     handler. The consumer is scene-worker, which is already running.
--
--   * fingerprint_versions.images_meta keeps, for every source photo used in
--     that version, its file name AND its capture date. The originals are not
--     needed afterwards: the fingerprint is the result, the names and dates are
--     the only trace worth keeping (they come from metadata.json, written by
--     the builder while it still had the folder at hand).
--
-- Additive; nothing is rewritten.
--
-- Rollback:
--   ALTER TABLE job_queue DROP CONSTRAINT job_queue_job_type_check;
--   ... re-create it without 'FINGERPRINT_BUILD' (as in schema/020);
--   ALTER TABLE fingerprint_versions DROP COLUMN IF EXISTS images_meta;

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
            'INGEST_DIR',
            'MEDIA_SEARCH',
            'FINGERPRINT_BUILD'
        )
    );

ALTER TABLE fingerprint_versions
    ADD COLUMN IF NOT EXISTS images_meta JSONB NOT NULL DEFAULT '[]'::jsonb;

-- Cheap dedup lookup: one active build per fingerprint.
CREATE INDEX IF NOT EXISTS idx_job_queue_fingerprint_active
    ON job_queue ((payload ->> 'fingerprint_id'))
    WHERE job_type = 'FINGERPRINT_BUILD' AND status IN ('PENDING', 'RUNNING');
