-- Saved searches (bookmarked filters), mirroring the legacy "История поиска".
--
-- A saved search stores a named snapshot of the GRID filter state (query,
-- selected addresses/clients, date range, collection). It never affects the
-- INGEST/DINO/HYBRID pipelines; it only helps the UI restore a filter set.
--
-- Idempotent: safe to re-apply.

CREATE TABLE IF NOT EXISTS saved_searches (
    search_id  BIGSERIAL PRIMARY KEY,

    -- owner; NULL when authentication is disabled (legacy had user_id)
    user_id    TEXT,

    name       TEXT NOT NULL,

    -- free-form filter snapshot, e.g.
    -- {"q": "...", "addresses": ["78_v33"], "clients": ["..."],
    --  "date_from": "...", "date_to": "...", "collection_id": 3}
    filters    JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX IF NOT EXISTS idx_saved_searches_user
    ON saved_searches(user_id);
