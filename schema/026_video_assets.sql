-- Durable source-video registry. Video metadata stays separate from the
-- photo-only `photos` table so DINO/HYBRID/QWEN cannot accidentally consume it.
-- This migration is additive; it does not modify or backfill photo rows.
--
-- Rollback (only after video routes/workers are disabled and the new data is
-- exported/retained as required):
--   DROP TABLE IF EXISTS public.video_assets;

CREATE TABLE public.video_assets (
    video_id          TEXT PRIMARY KEY
                      CHECK (video_id ~ '^VI_[0-9a-f]{24}$'),
    source_path       TEXT NOT NULL,
    filename          TEXT NOT NULL,
    sha256            CHAR(64) NOT NULL UNIQUE
                      CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    container_format  TEXT NOT NULL,
    video_codec       TEXT NOT NULL,
    width             INTEGER NOT NULL CHECK (width > 0),
    height            INTEGER NOT NULL CHECK (height > 0),
    duration_seconds  DOUBLE PRECISION NOT NULL CHECK (duration_seconds > 0),
    fps               DOUBLE PRECISION CHECK (fps IS NULL OR fps > 0),
    frame_count       BIGINT CHECK (frame_count IS NULL OR frame_count > 0),
    size_bytes        BIGINT NOT NULL CHECK (size_bytes > 0),
    taken_at          TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    display_title     TEXT NOT NULL DEFAULT ''
                      CHECK (length(display_title) <= 300)
);

CREATE INDEX ix_video_assets_created_at
    ON public.video_assets (created_at DESC, video_id);

CREATE INDEX ix_video_assets_taken_at
    ON public.video_assets (taken_at DESC, video_id)
    WHERE taken_at IS NOT NULL;

CREATE INDEX ix_video_assets_filename
    ON public.video_assets (lower(filename));
