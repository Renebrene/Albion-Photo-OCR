-- Fingerprint registry: names, descriptions, versions and archiving.
--
-- The vectors stay on disk (data/fingerprints/<id>/): metadata.json remains the
-- source of truth for what a fingerprint contains. These two tables mirror it
-- into PostgreSQL so the UI can name a fingerprint, describe it, archive it and
-- keep a version journal, without the API having to re-read the disk for every
-- row. app/api/fingerprints.py:sync_from_disk() fills and refreshes them.
--
--   fingerprints          one row per fingerprint id (78_v33)
--   fingerprint_versions  one row per rebuild (photo count + saved file names)
--
-- Additive: no existing table is altered, no vector is touched. Dropping the
-- rows only loses the human metadata; it can be rebuilt from the disk.
--
-- Rollback:
--   DROP TABLE IF EXISTS public.fingerprint_versions;
--   DROP TABLE IF EXISTS public.fingerprints;

CREATE TABLE IF NOT EXISTS public.fingerprints (
    fingerprint_id     TEXT PRIMARY KEY,
    display_name       TEXT NOT NULL DEFAULT '',
    description        TEXT NOT NULL DEFAULT '',
    algorithm_version  TEXT,
    model              TEXT,
    dimension          INTEGER,
    images_count       INTEGER NOT NULL DEFAULT 0,
    source_folder      TEXT,
    active             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fingerprints_images_count_check CHECK (images_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_fingerprints_active
    ON public.fingerprints (active, fingerprint_id);

CREATE TABLE IF NOT EXISTS public.fingerprint_versions (
    version_id         SERIAL PRIMARY KEY,
    fingerprint_id     TEXT NOT NULL
        REFERENCES public.fingerprints (fingerprint_id) ON DELETE CASCADE,
    algorithm_version  TEXT,
    images_count       INTEGER NOT NULL DEFAULT 0,
    image_names        JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_folder      TEXT,
    is_current         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    recreated_at       TIMESTAMP,

    CONSTRAINT fingerprint_versions_images_count_check
        CHECK (images_count >= 0)
);

-- One current version per fingerprint, and a cheap history lookup.
CREATE UNIQUE INDEX IF NOT EXISTS uq_fingerprint_versions_current
    ON public.fingerprint_versions (fingerprint_id)
    WHERE is_current;

CREATE INDEX IF NOT EXISTS idx_fingerprint_versions_history
    ON public.fingerprint_versions (fingerprint_id, created_at DESC);
