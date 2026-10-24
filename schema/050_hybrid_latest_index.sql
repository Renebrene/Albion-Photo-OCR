-- «Последний вердикт HYBRID по фото» — самый частый подзапрос чтения.
--
-- `_address_sql` и `_latest_confidence_sql` берут последнюю строку
-- hybrid_results по photo_id с сортировкой finished_at DESC, hybrid_run_id DESC.
-- На 57 тысячах фото и 57 тысячах вердиктов каждый такой подзапрос давал
-- Index Scan + Sort. Составной индекс отдаёт строку уже в нужном порядке:
-- счётчики подвала и панель адресов перестают быть узким местом.
--
-- Откат: DROP INDEX IF EXISTS public.idx_hybrid_results_photo_latest;

CREATE INDEX IF NOT EXISTS idx_hybrid_results_photo_latest
    ON public.hybrid_results (photo_id, finished_at DESC NULLS LAST, hybrid_run_id DESC);
