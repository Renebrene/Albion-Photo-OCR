#!/usr/bin/env bash
set -euo pipefail

# Only the API container applies migrations (RUN_MIGRATIONS=1 in compose).
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    echo "[demo] applying database migrations"
    python scripts/migrate.py
fi

exec "$@"
