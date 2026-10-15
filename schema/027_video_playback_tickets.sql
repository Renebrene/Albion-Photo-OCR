-- Short-lived HttpOnly-cookie capabilities let native <video> playback and
-- browser downloads use authenticated source files without bearer tokens in
-- URLs/access logs. Only a SHA-256 of the random capability is persisted.
--
-- Additive. Rollback after disabling video playback/download endpoints:
--   DROP TABLE IF EXISTS public.video_playback_tickets;

CREATE TABLE public.video_playback_tickets (
    ticket_sha256 CHAR(64) PRIMARY KEY
                  CHECK (ticket_sha256 ~ '^[0-9a-f]{64}$'),
    video_id      TEXT NOT NULL REFERENCES public.video_assets(video_id) ON DELETE CASCADE,
    action        TEXT NOT NULL CHECK (action IN ('inline', 'attachment')),
    expires_at    TIMESTAMPTZ NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_video_playback_tickets_expiry
    ON public.video_playback_tickets (expires_at);
