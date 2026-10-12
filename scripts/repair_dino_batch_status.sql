-- One-off data repair for databases that ran the pre-2026-10-12 finish_batch.
--
-- That version marked a DINO batch as DONE whenever no run was active, even
-- when some runs had FAILED (see docs/dino.txt §18/§26). This script rewrites
-- such batches to FAILED and recomputes their counters. It also fixes any
-- drifted completed/failed counters.
--
-- Idempotent: safe to run multiple times; a clean database is left unchanged.
-- Run as the application role:
--     psql -h 127.0.0.1 -U lora_ingest -d photobase_ingest_test \
--          -v ON_ERROR_STOP=1 -f scripts/repair_dino_batch_status.sql

BEGIN;

-- A batch that is DONE but has at least one FAILED run must be FAILED.
UPDATE dino_batches AS b
SET status = 'FAILED',
    finished_at = COALESCE(b.finished_at, CURRENT_TIMESTAMP)
WHERE b.status = 'DONE'
  AND EXISTS (
      SELECT 1
      FROM dino_runs AS r
      WHERE r.batch_id = b.batch_id
        AND r.status = 'FAILED'
  );

-- Recompute counters from the runs for every batch.
UPDATE dino_batches AS b
SET completed_count = agg.done_count,
    failed_count    = agg.failed_count
FROM (
    SELECT batch_id,
           COUNT(*) FILTER (WHERE status = 'DONE')   AS done_count,
           COUNT(*) FILTER (WHERE status = 'FAILED') AS failed_count
    FROM dino_runs
    GROUP BY batch_id
) AS agg
WHERE agg.batch_id = b.batch_id
  AND (b.completed_count <> agg.done_count
       OR b.failed_count <> agg.failed_count);

COMMIT;
