-- INGEST metadata the UI needs but the original contract did not store.
--
--   taken_at   - capture date read from the source file's EXIF
--                (DateTimeOriginal, falling back to DateTimeDigitized); for
--                MPO this is frame 0. NULL when the file has no usable tag -
--                the grid then simply has no capture date for that photo.
--   size_bytes - size of the physical source file in bytes (stat()), so the
--                viewer can show MB and the ingest scan can skip a file
--                without hashing it (filename + size match).
--
-- Additive and idempotent: no existing row is touched. Rows registered before
-- this migration keep NULL until scripts/backfill_photo_metadata.py re-reads
-- their source file (originals are only read, never modified).
--
-- Rollback:
--   DROP INDEX IF EXISTS idx_photos_taken_at;
--   ALTER TABLE photos DROP COLUMN IF EXISTS size_bytes;
--   ALTER TABLE photos DROP COLUMN IF EXISTS taken_at;

ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS taken_at TIMESTAMP;

ALTER TABLE photos
    ADD COLUMN IF NOT EXISTS size_bytes BIGINT;

-- The grid filters and could sort by capture date.
CREATE INDEX IF NOT EXISTS idx_photos_taken_at
    ON photos (taken_at);
