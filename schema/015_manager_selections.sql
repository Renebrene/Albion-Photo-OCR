-- Per-manager UI state (mirrors the legacy `manager_selections`).
--
-- Stores one JSONB blob per user: the current GRID state (selected photo ids,
-- filters, NL ids). It is personal convenience state, not part of INGEST/DINO/
-- HYBRID, and writes are always scoped to the authenticated user.
--
-- Idempotent: safe to re-apply.

CREATE TABLE IF NOT EXISTS manager_selections (
    user_id    TEXT PRIMARY KEY,
    state      JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
