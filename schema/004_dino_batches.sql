-- DINO batches: a fixed snapshot of photos processed together (docs/dino.txt).
--
-- This migration is idempotent and safe to apply both on a fresh database
-- and on an existing one (schema/003 already applied and possibly populated):
--   * creates dino_batches if missing;
--   * adds dino_runs.batch_id (nullable) if missing;
--   * backfills existing runs that have no batch (one legacy single-photo
--     batch per run) so that existing data is preserved;
--   * enforces NOT NULL only after the backfill leaves no NULL rows;
--   * creates the batch index idempotently.
--
-- Re-running this file is a no-op.
--
-- Rollback (see docs/database_schema.md):
--   ALTER TABLE dino_runs DROP COLUMN batch_id;
--   DROP TABLE dino_batches;

CREATE TABLE IF NOT EXISTS dino_batches (
    batch_id         BIGSERIAL PRIMARY KEY,

    run_type         TEXT NOT NULL
                     CHECK (run_type IN ('NORMAL', 'FORCE_RERUN')),

    status           TEXT NOT NULL
                     CHECK (status IN ('PENDING', 'RUNNING', 'DONE', 'FAILED')),

    total_count      INTEGER NOT NULL
                     CHECK (total_count >= 0),

    completed_count  INTEGER NOT NULL DEFAULT 0
                     CHECK (completed_count >= 0),

    failed_count     INTEGER NOT NULL DEFAULT 0
                     CHECK (failed_count >= 0),

    created_at       TIMESTAMP NOT NULL
                     DEFAULT CURRENT_TIMESTAMP,

    started_at       TIMESTAMP,

    finished_at      TIMESTAMP
);


ALTER TABLE dino_runs
    ADD COLUMN IF NOT EXISTS batch_id BIGINT
    REFERENCES dino_batches(batch_id)
    ON DELETE CASCADE;


-- Backfill: assign every run without a batch to its own legacy batch.
-- A run is a single-photo unit, so a per-run batch (total_count = 1) is the
-- most faithful reconstruction of pre-batch history.
DO $$
DECLARE
    orphan       RECORD;
    new_batch_id BIGINT;
BEGIN
    FOR orphan IN
        SELECT run_id, run_type, status
        FROM dino_runs
        WHERE batch_id IS NULL
        ORDER BY run_id
    LOOP
        INSERT INTO dino_batches (
            run_type,
            status,
            total_count,
            completed_count,
            failed_count
        )
        VALUES (
            orphan.run_type,
            orphan.status,
            1,
            CASE WHEN orphan.status = 'DONE'   THEN 1 ELSE 0 END,
            CASE WHEN orphan.status = 'FAILED' THEN 1 ELSE 0 END
        )
        RETURNING batch_id INTO new_batch_id;

        UPDATE dino_runs
        SET batch_id = new_batch_id
        WHERE run_id = orphan.run_id;
    END LOOP;
END
$$;


-- Enforce NOT NULL only when no orphan row remains.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM dino_runs WHERE batch_id IS NULL) THEN
        RAISE EXCEPTION
            'dino_runs.batch_id still contains NULL values after backfill';
    END IF;

    ALTER TABLE dino_runs ALTER COLUMN batch_id SET NOT NULL;
END
$$;


CREATE INDEX IF NOT EXISTS idx_dino_runs_batch
    ON dino_runs(batch_id);
