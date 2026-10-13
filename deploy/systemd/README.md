# systemd deployment (scene-api + scene-worker)

Two long-running services cover the web app:

| Unit | Runs | Maps to legacy |
|---|---|---|
| `scene-api.service` | FastAPI app + built Quasar SPA (`app.api.main:app`) | `dashboard.service` |
| `scene-worker.service` | deferred job worker (`app.jobs.worker`) | `lora.service` (worker) |

Inference (DINO/HYBRID) and QWEN run **only** in the worker — never inside the
API process. The API serves `frontend/dist` statically, so there is no separate
frontend unit.

## Prerequisites

1. A checkout at `/opt/scene-fingerprint` with a virtualenv at
   `.venv/` (paths in the units assume these — edit the units otherwise).
2. A dedicated service user (the units use `scene`):
   ```bash
   sudo useradd --system --home /opt/scene-fingerprint --shell /usr/sbin/nologin scene
   sudo chown -R scene:scene /opt/scene-fingerprint
   ```
3. PostgreSQL reachable and the schema applied (`scripts/db_bootstrap.sh`).
4. Ollama running with the QWEN model (worker only).
5. Build the SPA once so the API can serve it:
   ```bash
   cd frontend && bun install --frozen-lockfile && bun run build
   ```

## Install

```bash
# 1. Environment file (never commit the filled-in copy — it has the DB password)
sudo install -m 0640 -o root -g scene deploy/systemd/scene.env.example /etc/scene-fingerprint.env
sudo "${EDITOR:-vi}" /etc/scene-fingerprint.env

# 2. Units
sudo cp deploy/systemd/scene-api.service deploy/systemd/scene-worker.service /etc/systemd/system/
sudo systemctl daemon-reload

# 3. Enable and start
sudo systemctl enable --now scene-api scene-worker

# 4. Check
systemctl status scene-api scene-worker
journalctl -u scene-worker -f
curl -fsS http://127.0.0.1:8010/api/health
```

## First login

Authentication is **fail-closed** (`SCENE_AUTH_REQUIRED=1`): every `/api/v1/*`
route needs a credential, and seeded users have **no password**, so login is
refused until one is set. Set the first password once, on the server:

```bash
cd /opt/scene-fingerprint
sudo -u scene INGEST_DB_PASSWORD=... \
    .venv/bin/python scripts/set_password.py Администратор
```

Then log in through the web UI. Changing a password invalidates its sessions.

`SCENE_ORIGINALS_ROOTS` must point at the mounted photo volume (comma-separated
roots); with it empty the original-file endpoint is refused entirely.

## Operating notes

- **Secrets**: `SCENE_API_TOKENS` and `INGEST_DB_PASSWORD` live only in
  `/etc/scene-fingerprint.env` (mode `0640`), never in the repo. There is a
  historical password in `docs/db_setup.md` kept by owner decision — do not
  reuse it in production.
- **CORS**: set `SCENE_CORS_ORIGINS` to the real origin(s); never `*`.
- **Automation**: to let the scheduler enqueue work, add `--automation` to the
  worker `ExecStart` (off by default; see `docs/frontend_quasar.md`, Slice 15).
- **Recovery**: `--requeue-stale 30` returns jobs stuck in `RUNNING` for more
  than 30 minutes to `PENDING` at worker start-up.
- **Hardening**: the units enable `NoNewPrivileges`, `PrivateTmp`,
  `ProtectSystem=full`, `ProtectHome` and only expose `data/` writable. If the
  source photo folders live outside the checkout, add them to `ReadWritePaths`.
- **Uploads** land in `SCENE_INBOX` (`data/inbox`); ensure it is on the same
  filesystem as the process user can write.
