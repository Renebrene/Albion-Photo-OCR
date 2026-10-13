-- Bootstrap role + database for PhotoBAse / Scene Fingerprint.
--
-- Run as a PostgreSQL SUPERUSER. Do NOT wrap in a single transaction:
-- CREATE DATABASE cannot run inside a transaction block.
--
-- Required psql variables:
--     :app_user     login role for the application      (default lora_ingest)
--     :app_db       application database name           (default photobase_ingest_test)
--     :db_password  password for that role              (no default)
--
-- Example:
--     psql -h 127.0.0.1 -U postgres -d postgres \
--          -v ON_ERROR_STOP=1 \
--          -v app_user=lora_ingest -v app_db=photobase_ingest_test \
--          -v db_password="$INGEST_DB_PASSWORD" \
--          -f schema/000_bootstrap.sql

\echo '[bootstrap] ensuring role...'

SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L',
    :'app_user', :'db_password'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = :'app_user'
)\gexec

-- Keep the password in sync when the role already exists.
SELECT format(
    'ALTER ROLE %I WITH LOGIN PASSWORD %L',
    :'app_user', :'db_password'
)\gexec

\echo '[bootstrap] ensuring database...'

SELECT format(
    'CREATE DATABASE %I OWNER %I',
    :'app_db', :'app_user'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_database WHERE datname = :'app_db'
)\gexec

\echo '[bootstrap] enabling pg_trgm in the application database...'

-- Trigram search indexes (schema/014) need the pg_trgm extension. Creating an
-- extension requires superuser, so it is done here, in the app database.
-- If the extension files are missing on this host, bootstrap still succeeds;
-- schema/014 then skips index creation with a NOTICE.
\connect :app_db

DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '[bootstrap] pg_trgm unavailable (%); search indexes will be skipped', SQLERRM;
END
$$;

\echo '[bootstrap] done. Apply schema/001..014 as the application role next.'
