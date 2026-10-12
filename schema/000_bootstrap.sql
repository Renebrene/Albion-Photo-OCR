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

\echo '[bootstrap] done. Apply schema/001..005 as the application role next.'
