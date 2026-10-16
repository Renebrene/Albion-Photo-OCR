# systemd deployment (scene-api + scene-worker)

Two long-running services cover the web app:

| Unit | Runs | Maps to legacy |
|---|---|---|
| `scene-api.service` | FastAPI app + built Quasar SPA (`app.api.main:app`) | `dashboard.service` |
| `scene-worker.service` | deferred job worker (`app.jobs.worker`) | `lora.service` (worker) |
| `scene-builder.service` (user unit) | parallel fingerprint builder (`app.jobs.worker --watch --only FINGERPRINT_BUILD --parallel 3`) | — |
| `scene-video-worker.service` (user unit) | isolated `VIDEO_TRANSCODE` / `VIDEO_TRIM` / `VIDEO_STORYBOARD` jobs; smoke-gated NVENC or CPU | — |
| `scene-preview-worker.service` (user unit) | isolated `PHOTO_PREVIEW` queue poller; parallel CPU work runs in `app.preview.pipeline` | — |

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
5. For video INGEST/transcode, install a trusted FFmpeg build that includes both `ffmpeg` and `ffprobe` and the H.264 encoder/decoder. Set `SCENE_FFMPEG_BIN` / `SCENE_FFPROBE_BIN` in the environment file. `scene-video-worker` is separate and must not be enabled before FFmpeg/FFprobe paths are readable from the user-service context, schema/030 is applied, output roots are writable/outside source roots, and the synthetic CPU smoke passes. NVENC is used only if its runtime test succeeds in that context; otherwise auto mode falls back to CPU.
6. Build the SPA once so the API can serve it:
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

## Local single-machine variant (user units, no root)

When the app runs on the same workstation as the data and root is not available,
install the same two services as **user** units instead of system ones:

```bash
mkdir -p ~/.config/systemd/user
# units (WorkingDirectory must have no spaces -> use a symlink):
ln -sfn "/path/to/scene_fingerprint_RELEASE_v38_1_v33 (2)" ~/scene-fingerprint
cp deploy/systemd/user/scene-api.service deploy/systemd/user/scene-worker.service deploy/systemd/user/scene-video-worker.service deploy/systemd/user/scene-preview-worker.service ~/.config/systemd/user/
install -m 600 deploy/systemd/user/scene.env.example ~/.config/scene-fingerprint.env
# edit ~/scene-fingerprint paths + DB password, then:
systemctl --user daemon-reload
systemctl --user enable --now scene-api scene-worker
# Enable only after FFmpeg/FFprobe service-context smoke passes and schema 030 is applied:
systemctl --user enable --now scene-video-worker
# Enable after schema 029 is applied; this worker is the only queue consumer of PHOTO_PREVIEW:
systemctl --user enable --now scene-preview-worker
```

Notes that matter:

- **No spaces in `WorkingDirectory`.** systemd does not unquote these paths, so
  a checkout under a name with spaces must be reached through a symlink
  (e.g. `~/scene-fingerprint`).
- **Autostart at boot** requires lingering: `sudo loginctl enable-linger <user>`
  (otherwise user services start at login only).
- The frontend is served by the API process (built `frontend/dist`), so there
  is **no separate frontend unit**.
- Inspect logs with `journalctl --user -u scene-api -f`.

## Early photo previews

Photo registration in directory INGEST and upload enqueues one `PHOTO_PREVIEW`
job per newly registered photo. The general worker excludes this type by default;
`scene-preview-worker.service` claims only it, so older DINO/QWEN work cannot hold
preview generation behind its FIFO position. Preview files remain independent
of DINO/HYBRID/QWEN results.
The photo preview pipeline itself uses a bounded process pool; configure
`SCENE_PREVIEW_WORKERS` (default: half of logical CPU cores). Keep only one
preview queue poller, since its one job invocation already parallelizes images.
The API and worker must share `SCENE_PREVIEW_ROOT`, which must be writable by
the worker and readable by the API.

After applying schema/029 to the intended database and deploying the code,
enable the unit. A bounded backfill can enqueue missing preview rows without
blocking the request or touching originals:

```bash
curl -X POST 'http://127.0.0.1:8010/api/v1/previews/backfill?limit=500' \
  -H 'Authorization: Bearer <token-with-jobs:write>'
```

The endpoint schedules at most 5000 photo jobs per call (default 500). Existing
active jobs are deduplicated by a PostgreSQL partial unique index. Failed jobs
remain visible in the queue; an explicit backfill can enqueue them again for
photos that still have no preview row. Valid SMALL/MIDDLE outputs are skipped
by the existing generator on retry. Do not enable the preview worker before
schema/029 has been applied.

## Parallel fingerprint building

Building a fingerprint is CPU-bound, so a batch of them is spread over several
processes of the same unit:

```bash
# in the unit: ExecStart=... app.jobs.worker --watch --only FINGERPRINT_BUILD --parallel 3
```

`--only` keeps these workers from taking QWEN/DINO jobs, and each of the N
processes claims its own job atomically (`claim_next` with a type filter), so a
batch of builds runs N at a time. Each process gets `cores / parallel` torch
threads. A **pause** is honoured between batches; the worker waits for the
resume at most `SCENE_PAUSE_MAX_SECONDS` (default 300) and then fails the job
rather than blocking the queue, because one worker handles one job at a time.

## Video runtime and trim editor

The video worker is user-only in the local setup and accepts `VIDEO_TRANSCODE`,
`VIDEO_TRIM`, and `VIDEO_STORYBOARD`; the general worker excludes these types.
The trim-only editor creates a new derivative under `SCENE_VIDEO_DERIVATIVES_ROOT`
and the storyboard uses `SCENE_VIDEO_STORYBOARD_ROOT`. Originals stay read-only.
Before enabling `scene-video-worker`, apply schema/030 through `scripts/migrate.py`,
verify the FFmpeg binaries are readable by the user systemd service, and run a
synthetic trim/storyboard smoke. Keep `SCENE_VIDEO_ENCODER=cpu` if NVENC has not
passed a runtime encode under the same service environment. The checked-in
Cherry-managed FFmpeg path in `scene.env.example` is specific to this workstation;
replace it with a trusted service-accessible path on other installations.

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
- **INGEST folder**: `SCENE_SOURCE_FOLDER` (default, overridable in the UI and
  stored in `app_settings`) is scanned by the worker when `POST /v1/ingest/run`
  or `scene-fingerprint ingest <folder>` is used. Set `SCENE_SOURCE_ROOTS` to
  restrict which folders may be picked; leave it empty only on a single-owner
  host. Files already registered under the same (name, size) are skipped
  without hashing.
- **Migrations**: after pulling a change that touches `schema/`, run
  `scripts/migrate.py` **before** restarting the units — the API/worker read
  columns added by the new migration (see `docs/db_setup.md`).
