-- Планировщик: фоновый вотчер папки не реализуется, поэтому авто-DINO (он был
-- привязан к идее слежения за папкой) выключен, и авто-QWEN по умолчанию
-- выключен. Существующая строка настроек обновляется, чтобы уже запущенный
-- планировщик перестал автоматически ставить задачи QWEN.
--
-- Откат:
--   ALTER TABLE public.automation_settings ALTER COLUMN auto_dino SET DEFAULT FALSE;
--   ALTER TABLE public.automation_settings ALTER COLUMN auto_qwen SET DEFAULT TRUE;

ALTER TABLE public.automation_settings
    ALTER COLUMN auto_dino SET DEFAULT FALSE;

ALTER TABLE public.automation_settings
    ALTER COLUMN auto_qwen SET DEFAULT FALSE;

UPDATE public.automation_settings
SET auto_dino = FALSE,
    auto_qwen = FALSE
WHERE id = 1;
