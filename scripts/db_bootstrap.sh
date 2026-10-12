#!/usr/bin/env bash
#
# Bootstrap the PhotoBAse / Scene Fingerprint PostgreSQL database.
#
# Step 1 (superuser) : create the application role + database (schema/000_bootstrap.sql).
# Step 2 (app role)  : apply schema/001_ingest.sql .. 005_hybrid.sql.
#
# Step 1 is SKIPPED automatically when the application role can already
# connect to the target database (nothing to create).
# Step 2 is SKIPPED when public.photos already exists, because the schema
# files are NOT idempotent (plain CREATE TABLE without IF NOT EXISTS).
#
# Environment:
#   INGEST_DB_PASSWORD   (required) password for the application role
#   INGEST_DB_HOST       (default 127.0.0.1)
#   INGEST_DB_PORT       (default 5432)
#   INGEST_DB_NAME       (default photobase_ingest_test)
#   INGEST_DB_USER       (default lora_ingest)
#   PGSUPERUSER          (default postgres) superuser used only for step 1
#   PGSUPERUSER_SOCKET   (default 0) set to 1 to reach the superuser over the
#                        unix socket (peer auth) instead of TCP+password
#
# Credentials:
#   * application role password -> PGPASSWORD env (not visible in `ps`)
#   * superuser password        -> configure ~/.pgpass or PGPASSWORD for the
#                                  step-1 connection yourself.
#     If the local server uses peer auth for `postgres`, run step 1 as that OS
#     user with the socket, e.g.:
#         sudo -u postgres env PGSUPERUSER_SOCKET=1 INGEST_DB_PASSWORD='...' \
#             ./scripts/db_bootstrap.sh

set -euo pipefail

HOST="${INGEST_DB_HOST:-127.0.0.1}"
PORT="${INGEST_DB_PORT:-5432}"
APP_DB="${INGEST_DB_NAME:-photobase_ingest_test}"
APP_USER="${INGEST_DB_USER:-lora_ingest}"
SUPERUSER="${PGSUPERUSER:-postgres}"

APP_PASSWORD="${INGEST_DB_PASSWORD:?INGEST_DB_PASSWORD must be set}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEMA_DIR="$SCRIPT_DIR/../schema"

if [[ ! -d "$SCHEMA_DIR" ]]; then
    echo "schema directory not found: $SCHEMA_DIR" >&2
    exit 1
fi

app_psql() {
    PGPASSWORD="$APP_PASSWORD" psql -h "$HOST" -p "$PORT" -U "$APP_USER" -d "$APP_DB" "$@"
}

if app_psql -tAc 'select 1' >/dev/null 2>&1; then
    echo "[1/2] role '$APP_USER' + database '$APP_DB' already usable -> skipping creation"
else
    super_args=(-U "$SUPERUSER" -d postgres)
    if [[ "${PGSUPERUSER_SOCKET:-0}" == "1" ]]; then
        echo "[1/2] creating role '$APP_USER' + database '$APP_DB' (as superuser '$SUPERUSER' via unix socket)"
    else
        super_args=(-h "$HOST" -p "$PORT" "${super_args[@]}")
        echo "[1/2] creating role '$APP_USER' + database '$APP_DB' (as superuser '$SUPERUSER' @ $HOST:$PORT)"
    fi
    psql "${super_args[@]}" \
        -v ON_ERROR_STOP=1 \
        -v app_user="$APP_USER" \
        -v app_db="$APP_DB" \
        -v db_password="$APP_PASSWORD" \
        -f "$SCHEMA_DIR/000_bootstrap.sql"
fi

echo "[2/2] application schema (as '$APP_USER' @ $APP_DB)"

existing="$(app_psql -tAc "select coalesce(to_regclass('public.photos')::text, '')")"

if [[ -n "$existing" ]]; then
    echo "  public.photos already exists -> skipping 001..005 (schema is not idempotent)"
else
    for name in 001_ingest 002_preview 003_dino 004_dino_batches 005_hybrid 006_job_queue 007_qwen; do
        echo "  applying schema/$name.sql"
        app_psql -v ON_ERROR_STOP=1 -f "$SCHEMA_DIR/$name.sql"
    done
fi

echo "Done. Export for the application:"
echo "  INGEST_DB_HOST=$HOST INGEST_DB_PORT=$PORT INGEST_DB_NAME=$APP_DB INGEST_DB_USER=$APP_USER INGEST_DB_PASSWORD=<set>"
