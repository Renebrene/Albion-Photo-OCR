-- Город и закладка справочника адресов.
--
-- «Город» приходит из XLS «Рекламные возможности» и нужен закладкам слепков:
--   «Ростов 6х3», «Малые форматы РнД» — Ростов-на-Дону;
--   «Районы и трассы 6х3»            — город/район, определённый как район или
--                                      трасса по названию («…РАЙОН», «ТРАССА …»);
--   «Города области»                 — остальные города Ростовской области.
--
-- `scope` — закладка самого справочника адресов («Экраны» / «Остальное»):
-- у них свои таблицы и свои загрузки XLS (задание, п. 6а). Существующие
-- адреса — экраны, поэтому DEFAULT 'screens' оставляет их на месте без
-- переписывания данных.
--
-- Аддитивно: колонки добавляются, ничего не переименовывается и не удаляется.
--
-- Откат:
--   ALTER TABLE public.address_directory DROP CONSTRAINT IF EXISTS address_directory_scope_check;
--   ALTER TABLE public.address_directory DROP COLUMN IF EXISTS city, DROP COLUMN IF EXISTS scope;

ALTER TABLE public.address_directory
    ADD COLUMN IF NOT EXISTS city TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'screens';

ALTER TABLE public.address_directory
    DROP CONSTRAINT IF EXISTS address_directory_scope_check;

ALTER TABLE public.address_directory
    ADD CONSTRAINT address_directory_scope_check
    CHECK (scope IN ('screens', 'other'));
