CREATE TABLE dino_runs (
    run_id              BIGSERIAL PRIMARY KEY,

    photo_id            TEXT NOT NULL
                        REFERENCES photos(photo_id)
                        ON DELETE CASCADE,

    run_type            TEXT NOT NULL
                        CHECK (run_type IN ('NORMAL', 'FORCE_RERUN')),

    status              TEXT NOT NULL
                        CHECK (status IN (
                            'PENDING',
                            'RUNNING',
                            'DONE',
                            'FAILED'
                        )),

    dino_best_id        TEXT,

    dino_score          DOUBLE PRECISION,
    dino_second_score   DOUBLE PRECISION,
    dino_margin         DOUBLE PRECISION,
    dino_confidence     TEXT,
    dino_status         TEXT,

    started_at          TIMESTAMP,
    finished_at         TIMESTAMP,

    dino_time_sec       DOUBLE PRECISION,

    error_message       TEXT,

    created_at          TIMESTAMP NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX idx_dino_runs_photo
    ON dino_runs(photo_id);


CREATE INDEX idx_dino_runs_photo_done
    ON dino_runs(photo_id, finished_at DESC)
    WHERE status = 'DONE';


CREATE TABLE dino_candidates (
    run_id              BIGINT NOT NULL
                        REFERENCES dino_runs(run_id)
                        ON DELETE CASCADE,

    rank                INTEGER NOT NULL
                        CHECK (rank BETWEEN 1 AND 5),

    fingerprint_id      TEXT NOT NULL,

    score               DOUBLE PRECISION NOT NULL,

    global_score        DOUBLE PRECISION NOT NULL,
    environment_score   DOUBLE PRECISION NOT NULL,
    color_score         DOUBLE PRECISION NOT NULL,
    spatial_score       DOUBLE PRECISION NOT NULL,

    best_image          TEXT,
    best_image_score    DOUBLE PRECISION NOT NULL,

    PRIMARY KEY (run_id, rank)
);


CREATE INDEX idx_dino_candidates_fingerprint
    ON dino_candidates(fingerprint_id);
