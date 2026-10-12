-- Application settings (key/value). Used, for example, to choose the QWEN
-- model at runtime instead of only via the environment.
--
-- Idempotent: safe to re-apply.

CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT PRIMARY KEY,
    value      JSONB NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
