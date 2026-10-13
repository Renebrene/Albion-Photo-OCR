-- Client aliases: map near-duplicate QWEN client names to one canonical value.
--
-- QWEN invents client strings ("Яндекс @Еда", "Яндекс Еда"), so the same real
-- client shows up several times. This table maps a raw value to a canonical
-- one; the source rows in photo_qwen are never modified (legacy kept the same
-- "normalize separately, don't rewrite" principle).
--
-- Idempotent: safe to re-apply.

CREATE TABLE IF NOT EXISTS client_aliases (
    alias      TEXT PRIMARY KEY,
    canonical  TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
