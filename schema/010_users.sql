-- Users, roles and server-side sessions (mirrors the legacy users_db/session).
--
-- Passwords are stored as a scrypt hash (never plaintext; the legacy compared
-- plaintext, which must not be repeated).
--
-- Idempotent: safe to re-apply.

CREATE TABLE IF NOT EXISTS users (
    user_id       BIGSERIAL PRIMARY KEY,

    name          TEXT NOT NULL UNIQUE,

    color         TEXT,

    role          TEXT NOT NULL DEFAULT 'Менеджер'
                  CHECK (role IN ('Администратор', 'Менеджер', 'Гость')),

    active        BOOLEAN NOT NULL DEFAULT TRUE,

    -- scrypt$<salt_hex>$<hash_hex>; NULL means "no password set"
    password_hash TEXT,

    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,

    user_id    BIGINT NOT NULL
               REFERENCES users(user_id)
               ON DELETE CASCADE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);


CREATE INDEX IF NOT EXISTS idx_sessions_user
    ON sessions(user_id);


-- Default roster (no password -> open until an admin sets one).
INSERT INTO users (name, role)
VALUES ('Администратор', 'Администратор'), ('Гость', 'Гость')
ON CONFLICT (name) DO NOTHING;
