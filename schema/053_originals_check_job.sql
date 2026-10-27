-- Полная проверка доступности оригиналов — отдельный тип задания.
--
-- Сводка /v1/originals/health отвечает, подключён ли том, но не говорит, все
-- ли файлы на месте. Полный обход — это 57 тыс. stat по диску (а на сетевом
-- томе — по сети), поэтому он идёт заданием воркера, а не в обработчике HTTP.
-- Отдельный тип нужен, чтобы проверка была видна в истории очереди рядом с
-- остальными заданиями и её можно было отменить.
--
-- Миграция только расширяет список допустимых значений: существующие строки
-- проходят проверку без изменений, данные не переписываются.
--
-- Откат: удалить задания этого типа (в норме их нет в активных) и вернуть
-- прежний CHECK из schema/051_backup_jobs.sql.

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
            'REFINE',
            'BACKUP',
            'RESTORE',
            'ORIGINALS_CHECK'
        )
    );
