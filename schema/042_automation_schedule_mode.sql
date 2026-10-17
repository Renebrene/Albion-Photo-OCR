-- Scheduler: interval mode (existing) or one fixed time per day.
--
-- Additive and idempotent. Rollback:
--   ALTER TABLE public.automation_settings DROP COLUMN IF EXISTS daily_time;
--   ALTER TABLE public.automation_settings DROP COLUMN IF EXISTS mode;

ALTER TABLE public.automation_settings
    ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'interval'
    CHECK (mode IN ('interval', 'daily'));

ALTER TABLE public.automation_settings
    ADD COLUMN IF NOT EXISTS daily_time TIME;

-- The watcher-based auto-DINO is not implemented; make sure it stays off.
UPDATE public.automation_settings
SET auto_dino = FALSE
WHERE id = 1;
