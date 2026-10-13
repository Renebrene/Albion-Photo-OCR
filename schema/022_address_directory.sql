-- Address directory: the human-readable names behind a fingerprint id.
--
-- The recognition pipeline stores a technical id (photos.address, e.g.
-- '83_v33'); people work with an address instead. Two names are kept, as in
-- the legacy MVP:
--   legal_address  - the full official name (reports, contracts, file names);
--   simple_address - the short one shown in checkbox lists and the grid.
--
-- address_fingerprints maps one fingerprint id to one address. Unlike the
-- legacy table it has a primary key: an id belongs to a single address, so a
-- typo cannot silently create two competing rows.
--
-- Additive: no existing table is altered and no photo row is touched. Photos
-- without a mapping simply read back with NULL legal/simple address.
--
-- Rollback:
--   DROP TABLE IF EXISTS public.address_fingerprints;
--   DROP TABLE IF EXISTS public.address_directory;

CREATE TABLE IF NOT EXISTS public.address_directory (
    address_id     SERIAL PRIMARY KEY,
    legal_address  TEXT NOT NULL DEFAULT '',
    simple_address TEXT NOT NULL DEFAULT '',
    active         BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order     INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- An address with no name at all is useless: at least one must be filled.
    CONSTRAINT address_directory_named
        CHECK (btrim(legal_address) <> '' OR btrim(simple_address) <> '')
);

-- The legal name is the identity of an address: two rows may not share it
-- (case- and whitespace-insensitive, empty values exempt).
CREATE UNIQUE INDEX IF NOT EXISTS uq_address_directory_legal
    ON public.address_directory (lower(btrim(legal_address)))
    WHERE btrim(legal_address) <> '';

CREATE INDEX IF NOT EXISTS idx_address_directory_simple
    ON public.address_directory (lower(btrim(simple_address)));

CREATE TABLE IF NOT EXISTS public.address_fingerprints (
    fingerprint_id TEXT PRIMARY KEY,
    address_id     INTEGER NOT NULL
        REFERENCES public.address_directory (address_id) ON DELETE CASCADE,
    active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_address_fingerprints_address
    ON public.address_fingerprints (address_id);
