-- Background billboard branch: detection, crops and crop-level QWEN results.
-- Purely additive: INGEST/DINO/HYBRID tables are untouched; only the queue
-- whitelist gains two job types. A region row describes a bbox in ORIGINAL
-- image coordinates and points at a crop cut from the original (full size).
--
-- Rollback after disabling the BILLBOARD_DETECT/QWEN_CROP worker branches:
--   DROP INDEX IF EXISTS public.ix_billboard_active_dedup;
--   DROP INDEX IF EXISTS public.ix_qwen_crop_active_dedup;
--   ALTER TABLE public.job_queue DROP CONSTRAINT IF EXISTS job_queue_job_type_check;
--   -- Recreate the constraint without BILLBOARD_DETECT/QWEN_CROP.
--   DROP TABLE IF EXISTS public.photo_regions;

ALTER TABLE public.job_queue
    DROP CONSTRAINT IF EXISTS job_queue_job_type_check;

ALTER TABLE public.job_queue
    ADD CONSTRAINT job_queue_job_type_check
    CHECK (
        job_type IN (
            'DINO_BATCH',
            'HYBRID_RUN',
            'QWEN_PHOTO',
            'NL_SEARCH',
            'INGEST_DIR',
            'MEDIA_SEARCH',
            'FINGERPRINT_BUILD',
            'VIDEO_TRANSCODE',
            'PHOTO_PREVIEW',
            'VIDEO_TRIM',
            'VIDEO_STORYBOARD',
            'MEDIA_EXPORT',
            'BILLBOARD_DETECT',
            'QWEN_CROP'
        )
    );

-- One active detection per photo and one active crop analysis per region:
-- repeated enqueues while a job is pending/running collapse to one row.
CREATE UNIQUE INDEX IF NOT EXISTS ix_billboard_active_dedup
    ON public.job_queue ((payload ->> 'photo_id'))
    WHERE job_type = 'BILLBOARD_DETECT' AND status IN ('PENDING', 'RUNNING');

CREATE UNIQUE INDEX IF NOT EXISTS ix_qwen_crop_active_dedup
    ON public.job_queue ((payload ->> 'region_id'))
    WHERE job_type = 'QWEN_CROP' AND status IN ('PENDING', 'RUNNING');

CREATE TABLE IF NOT EXISTS public.photo_regions (
    region_id       BIGSERIAL PRIMARY KEY,
    photo_id        TEXT NOT NULL REFERENCES public.photos(photo_id)
                    ON DELETE CASCADE,

    kind            TEXT NOT NULL DEFAULT 'billboard',
    crop_index      INTEGER NOT NULL DEFAULT 0 CHECK (crop_index >= 0),

    -- Bbox in ORIGINAL image coordinates (not the downscaled detection copy).
    bbox_x          INTEGER NOT NULL CHECK (bbox_x >= 0),
    bbox_y          INTEGER NOT NULL CHECK (bbox_y >= 0),
    bbox_w          INTEGER NOT NULL CHECK (bbox_w > 0),
    bbox_h          INTEGER NOT NULL CHECK (bbox_h > 0),

    score           REAL NOT NULL,
    detector        TEXT NOT NULL,

    -- Crop cut from the original at full resolution.
    crop_path       TEXT NOT NULL,
    crop_width      INTEGER NOT NULL CHECK (crop_width > 0),
    crop_height     INTEGER NOT NULL CHECK (crop_height > 0),

    qwen_status     TEXT CHECK (
                        qwen_status IS NULL
                        OR qwen_status IN ('RUNNING', 'DONE', 'FAILED')
                    ),
    qwen_fields     JSONB,
    qwen_model      TEXT,
    qwen_time_sec   REAL,
    qwen_error      TEXT,
    qwen_finished_at TIMESTAMPTZ,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_photo_regions_photo
    ON public.photo_regions (photo_id);

-- Each detected billboard crop has one ordered region row per photo.
-- A unique crop index keeps a photo's crop-to-result mapping deterministic.
CREATE UNIQUE INDEX IF NOT EXISTS ux_photo_regions_photo_crop
    ON public.photo_regions (photo_id, kind, crop_index)
    WHERE kind = 'billboard';
