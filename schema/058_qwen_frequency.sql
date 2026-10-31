-- Aggregate popularity of client/brand/tag values in the QWEN base.
-- One photo = one vote per value, even when it has several billboards.
-- Rebuild with scripts/recompute_qwen_frequencies.py --apply.

CREATE TABLE IF NOT EXISTS public.qwen_value_frequencies (
    kind TEXT NOT NULL CHECK (kind IN ('client', 'brand', 'tag', 'any')),
    value_key TEXT NOT NULL,
    value TEXT NOT NULL,
    photo_count INTEGER NOT NULL CHECK (photo_count >= 0),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kind, value_key)
);

-- `any` is the union of client/brand/tag mentions and is what crop
-- aggregation uses: an advertiser mentioned as a tag is still popular.
CREATE INDEX IF NOT EXISTS ix_qwen_value_frequencies_rank
    ON public.qwen_value_frequencies (kind, photo_count DESC);

-- Rollback:
-- DROP TABLE IF EXISTS public.qwen_value_frequencies;
