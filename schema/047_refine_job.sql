-- «Уточнение» — отдельный тип задания в общей очереди.
--
-- Этап идёт после QWEN и связывает кадры одной серии. Отдельный тип нужен,
-- чтобы его можно было запускать, останавливать и видеть в истории отдельно
-- от описаний, и чтобы общий worker не путал его с QWEN_PHOTO.
--
-- Откат: удалить строки REFINE из job_queue и вернуть прежний CHECK
-- (см. schema/040_billboard_detection.sql).

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
            'QWEN_CROP',
            'REFINE'
        )
    );
