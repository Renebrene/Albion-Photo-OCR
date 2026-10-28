-- Закладка кнопки верхней панели у адреса (задание, 28.10.2026).
--
-- Списки адресов меняются редко: их состав определяется каталогом XLS, а не
-- работой системы. Поэтому закладка («Видеоэкраны», «Р-н-Д 6х3», «Города
-- области», «Область и трассы 6х3», «Р-н-Д малые форматы» или «не разобрано»)
-- не пересчитывается на каждый запрос по городу и формату, а хранится здесь и
-- заполняется при разборе XLS (`directory.import_addresses`) и скриптом
-- `scripts/recompute_address_panel_groups.py`.
--
-- Зачем: до этого фильтр по закладке применялся в Python уже ПОСЛЕ `LIMIT 1000`
-- в панели, поэтому список по кнопке обрезался по алфавиту, а не по правилу:
-- у «Экранов» 34 адреса из 95 в панель вообще не доезжали (1567 активных
-- адресов при лимите 1000). С колонкой фильтр идёт в SQL до лимита.
--
-- `panel_group` допускает NULL для строк, созданных мимо этих путей: фильтр по
-- закладке такие строки не выбирает, поэтому после применения нужно заполнить
-- их скриптом (он же идемпотентен и для повторного прогона).
--
-- Аддитивно: только новая колонка и индекс, ничего не переименовывается.
--
-- Откат:
--   DROP INDEX IF EXISTS public.address_directory_panel_group_idx;
--   ALTER TABLE public.address_directory DROP COLUMN IF EXISTS panel_group;

ALTER TABLE public.address_directory
    ADD COLUMN IF NOT EXISTS panel_group TEXT;

ALTER TABLE public.address_directory
    DROP CONSTRAINT IF EXISTS address_directory_panel_group_check;

ALTER TABLE public.address_directory
    ADD CONSTRAINT address_directory_panel_group_check
    CHECK (
        panel_group IS NULL
        OR panel_group IN ('screens', 'small', 'rostov', 'roads', 'cities', 'unknown')
    );

-- Панель и грид спрашивают адреса одной закладки: частичный индекс по активным
-- строкам ровно под этот запрос.
CREATE INDEX IF NOT EXISTS address_directory_panel_group_idx
    ON public.address_directory (panel_group)
    WHERE active;
