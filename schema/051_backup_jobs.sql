-- Бэкапы и восстановление из технического раздела — отдельные типы заданий.
--
-- Бэкап занимает диск и идёт минутами, восстановление перезаписывает базу
-- или файлы: это не работа фото-пайплайна, и выполняет её отдельный воркер
-- (scene-backup-worker, --only BACKUP,RESTORE). Отдельные типы нужны, чтобы
-- задания были видны в истории очереди и не путались с MEDIA_EXPORT —
-- иначе «отменить выгрузку» и «отменить бэкап» стали бы одним действием.
--
-- Миграция только расширяет список допустимых значений: существующие строки
-- проходят проверку без изменений, данные не переписываются.
--
-- Откат: удалить задания этих типов (в норме их нет в активных) и вернуть
-- прежний CHECK из schema/047_refine_job.sql.

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
            'RESTORE'
        )
    );
