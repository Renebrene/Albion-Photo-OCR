#!/usr/bin/env bash
#
# Start the whole PhotoBAse stack for local use:
#   * FastAPI backend   (python -m app.api.main)
#   * job worker        (app.jobs.worker --watch)
#   * Quasar dev server (bun dev), unless --no-frontend / --prod
#
# Ctrl+C stops everything this script started.
#
# Environment (defaults below; INGEST_DB_PASSWORD is required):
#   INGEST_DB_HOST/PORT/NAME/USER
#   SCENE_API_PORT            (default 8010)
#
# Usage:
#   INGEST_DB_PASSWORD=lora scripts/dev_up.sh
#   INGEST_DB_PASSWORD=lora scripts/dev_up.sh --no-frontend
#   INGEST_DB_PASSWORD=lora scripts/dev_up.sh --prod   # build SPA, serve from API

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

PY="${PY:-$ROOT/.venv/bin/python}"

# Locate bun: explicit $BUN, then PATH, then common install locations.
resolve_bun() {
    if [[ -n "${BUN:-}" ]]; then echo "$BUN"; return; fi
    if command -v bun >/dev/null 2>&1; then command -v bun; return; fi
    local candidate
    for candidate in \
        "$HOME/.bun/bin/bun" \
        "$HOME/.cherrystudio/bin/bun" \
        "/usr/local/bin/bun" \
        "/usr/bin/bun"; do
        if [[ -x "$candidate" ]]; then echo "$candidate"; return; fi
    done
}
BUN="$(resolve_bun || true)"

export INGEST_DB_HOST="${INGEST_DB_HOST:-127.0.0.1}"
export INGEST_DB_PORT="${INGEST_DB_PORT:-5432}"
export INGEST_DB_NAME="${INGEST_DB_NAME:-photobase_ingest_test}"
export INGEST_DB_USER="${INGEST_DB_USER:-lora_ingest}"
export SCENE_API_PORT="${SCENE_API_PORT:-8010}"

: "${INGEST_DB_PASSWORD:?set INGEST_DB_PASSWORD (e.g. INGEST_DB_PASSWORD=lora scripts/dev_up.sh)}"

WITH_FRONTEND=1
WITH_WORKER=1

for arg in "$@"; do
    case "$arg" in
        --no-frontend) WITH_FRONTEND=0 ;;
        --no-worker) WITH_WORKER=0 ;;
        --prod) WITH_FRONTEND=0 ;;  # prod serves the SPA from the backend
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

if [[ ! -x "$PY" ]]; then
    echo "python not found at $PY (set PY=...)" >&2
    exit 1
fi

API_BASE="http://127.0.0.1:${SCENE_API_PORT}"

pids=()
kill_tree() {
    local pid="$1" child
    for child in $(pgrep -P "$pid" 2>/dev/null || true); do
        kill_tree "$child"
    done
    kill "$pid" 2>/dev/null || true
}
cleanup() {
    echo
    echo "[dev_up] stopping..."
    for pid in "${pids[@]:-}"; do
        kill_tree "$pid"
    done
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[dev_up] backend  -> $API_BASE"
"$PY" -m app.api.main &
pids+=($!)

# Wait for the backend to answer /api/health.
for _ in $(seq 1 30); do
    if curl -fsS "$API_BASE/api/health" >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

if ! curl -fsS "$API_BASE/api/health" >/dev/null 2>&1; then
    echo "[dev_up] backend did not become healthy; check output above" >&2
fi

if [[ "$WITH_WORKER" = 1 ]]; then
    echo "[dev_up] worker   -> app.jobs.worker --watch"
    "$PY" -m app.jobs.worker --watch &
    pids+=($!)
fi

if [[ "$WITH_FRONTEND" = 1 ]]; then
    if [[ -z "$BUN" ]]; then
        echo "[dev_up] bun not found - frontend dev server disabled."
        echo "         install bun (https://bun.sh) or set BUN=/path/to/bun,"
        echo "         then run: cd frontend && bun dev   (backend stays on $API_BASE)"
        WITH_FRONTEND=0
    fi
fi

if [[ "$WITH_FRONTEND" = 1 ]]; then
    if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
        echo "[dev_up] installing frontend deps ($BUN install)"
        (cd "$ROOT/frontend" && "$BUN" install)
    fi

    echo "[dev_up] frontend -> http://localhost:5173  (proxy /api -> $API_BASE)"
    (cd "$ROOT/frontend" && exec env VITE_API_TARGET="$API_BASE" "$BUN" dev) &
    pids+=($!)
fi

echo
echo "[dev_up] running. Press Ctrl+C to stop."
wait
