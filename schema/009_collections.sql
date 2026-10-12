-- Collections / bookmarks (mirrors the legacy collections.py data model).
--
-- A collection groups addresses, clients or photos. Members are stored by
-- value (address string, client string or photo_id) so they survive re-ingest.
--
-- Idempotent: safe to re-apply.

CREATE TABLE IF NOT EXISTS collections (
    collection_id BIGSERIAL PRIMARY KEY,

    -- owner; NULL until users/sessions exist (legacy had user_id)
    user_id       TEXT,

    name          TEXT NOT NULL,

    kind          TEXT NOT NULL DEFAULT 'Моя'
                  CHECK (kind IN ('Моя', 'Клиентская')),

    -- for kind='Клиентская'
    client        TEXT,

    scope         TEXT NOT NULL DEFAULT 'photos'
                  CHECK (scope IN ('addresses', 'clients', 'photos')),

    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS collection_members (
    collection_id BIGINT NOT NULL
                  REFERENCES collections(collection_id)
                  ON DELETE CASCADE,

    member_type   TEXT NOT NULL
                  CHECK (member_type IN ('address', 'client', 'photo')),

    member_value  TEXT NOT NULL,

    PRIMARY KEY (collection_id, member_type, member_value)
);


CREATE INDEX IF NOT EXISTS idx_collection_members_value
    ON collection_members(member_type, member_value);
