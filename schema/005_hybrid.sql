-- HYBRID RUNS
-- One HYBRID run processes one completed DINO batch.
-- A DINO batch may have multiple HYBRID runs.

CREATE TABLE hybrid_runs (
    hybrid_run_id BIGSERIAL PRIMARY KEY,
    dino_batch_id BIGINT NOT NULL
        REFERENCES dino_batches(batch_id)
        ON DELETE CASCADE,

    status TEXT NOT NULL
        CHECK (status IN ('PENDING','RUNNING','DONE','FAILED')),

    total_count INTEGER NOT NULL
        CHECK (total_count >= 0),

    completed_count INTEGER NOT NULL DEFAULT 0
        CHECK (completed_count >= 0),

    failed_count INTEGER NOT NULL DEFAULT 0
        CHECK (failed_count >= 0),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE INDEX idx_hybrid_runs_dino_batch
    ON hybrid_runs(dino_batch_id);


-- HYBRID RESULTS
-- One result for one photo within one HYBRID run.

CREATE TABLE hybrid_results (
    hybrid_run_id BIGINT NOT NULL
        REFERENCES hybrid_runs(hybrid_run_id)
        ON DELETE CASCADE,

    photo_id TEXT NOT NULL
        REFERENCES photos(photo_id)
        ON DELETE CASCADE,

    dino_run_id BIGINT NOT NULL
        REFERENCES dino_runs(run_id)
        ON DELETE CASCADE,

    hybrid_original_id TEXT,
    hybrid_final_id TEXT,
    hybrid_changed BOOLEAN NOT NULL DEFAULT FALSE,

    hybrid_old_score DOUBLE PRECISION,
    hybrid_score DOUBLE PRECISION,
    hybrid_margin DOUBLE PRECISION,

    hybrid_neighbors TEXT,

    status TEXT NOT NULL
        CHECK (status IN ('DONE','FAILED')),

    error_message TEXT,

    hybrid_time_sec DOUBLE PRECISION,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,

    PRIMARY KEY (hybrid_run_id, photo_id)
);

CREATE INDEX idx_hybrid_results_photo
    ON hybrid_results(photo_id);

CREATE INDEX idx_hybrid_results_dino_run
    ON hybrid_results(dino_run_id);

CREATE INDEX idx_hybrid_results_final_id
    ON hybrid_results(hybrid_final_id);
