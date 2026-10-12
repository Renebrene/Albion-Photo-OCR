-- Automation settings (scheduler) — single-row control table.
--
-- The scheduler only *enqueues* the operations that already exist elsewhere
-- (QWEN metadata for photos without it, a DINO batch for photos never run).
-- It never ingests new files and never deletes data. Disabled by default.
--
-- Idempotent: safe to re-apply.

CREATE TABLE IF NOT EXISTS automation_settings (
    id               INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),

    enabled          BOOLEAN NOT NULL DEFAULT FALSE,

    -- how often the scheduler may enqueue a tick
    interval_minutes INT NOT NULL DEFAULT 60
                     CHECK (interval_minutes BETWEEN 1 AND 10080),

    auto_dino        BOOLEAN NOT NULL DEFAULT FALSE,
    auto_qwen        BOOLEAN NOT NULL DEFAULT TRUE,

    last_tick        TIMESTAMP,
    updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


INSERT INTO automation_settings (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;
