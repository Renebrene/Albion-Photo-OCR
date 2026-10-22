-- Кропы щитов как основа серий: хеш содержимого и время съёмки фото.
--
-- Серия — кадры одного экрана, снятые подряд. Чтобы связать их после QWEN,
-- нужны два признака, которых в таблице не было:
--
--   crop_phash     — 64-битный dHash кропа. Хеш всего кадра не годится: щит
--                    занимает ~18 % площади, и хеш описывает улицу. Замер:
--                    разница хешей кропов ≤ 6 → бренд совпадает в 82 %,
--                    ≥ 15 → в 14 % (docs/series_merge.md).
--   photo_taken_at — время съёмки самого фото (EXIF), отдельной записью у
--                    кропа: прогон по кропам не собирает его заново из
--                    photos и не зависит от join'а.
--
-- Кропы теперь живут после успешного QWEN (раньше удалялись сразу), поэтому
-- у записи есть признаки для группировки. Удаление — по возрасту
-- (scripts/cleanup_crops.py, по умолчанию 7 дней).
--
-- Откат:
--   DROP INDEX IF EXISTS ix_photo_regions_crop_phash;
--   DROP INDEX IF EXISTS ix_photo_regions_photo_taken_at;
--   ALTER TABLE public.photo_regions DROP COLUMN IF EXISTS crop_phash;
--   ALTER TABLE public.photo_regions DROP COLUMN IF EXISTS photo_taken_at;

ALTER TABLE public.photo_regions ADD COLUMN IF NOT EXISTS crop_phash BIGINT;

ALTER TABLE public.photo_regions ADD COLUMN IF NOT EXISTS photo_taken_at TIMESTAMP;

-- Заполняем время съёмки у уже существующих регионов из фото.
UPDATE public.photo_regions AS r
   SET photo_taken_at = p.taken_at
  FROM public.photos AS p
 WHERE p.photo_id = r.photo_id
   AND r.photo_taken_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_photo_regions_crop_phash
    ON public.photo_regions (crop_phash);

CREATE INDEX IF NOT EXISTS ix_photo_regions_photo_taken_at
    ON public.photo_regions (photo_taken_at);
