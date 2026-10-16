-- Изоляция «закладок» (сохранённые поиски и подборки) по пользователю.
--
-- До этой миграции records были общими: колонка user_id существовала, но не
-- использовалась. Здесь наследие без владельца приписывается встроенному
-- «Администратору», чтобы оно не осталось видимым всем сразу после включения
-- фильтрации по владельцу.
--
-- Откат безопасен: колонки не удаляются, фильтрация в коде — единственное
-- изменение поведения.
--   DROP INDEX IF EXISTS public.idx_collections_user;

UPDATE public.saved_searches
SET user_id = (
        SELECT u.user_id::text
        FROM public.users AS u
        WHERE u.name = 'Администратор'
        LIMIT 1
    )
WHERE user_id IS NULL
  AND EXISTS (SELECT 1 FROM public.users WHERE name = 'Администратор');

UPDATE public.collections
SET user_id = (
        SELECT u.user_id::text
        FROM public.users AS u
        WHERE u.name = 'Администратор'
        LIMIT 1
    )
WHERE user_id IS NULL
  AND EXISTS (SELECT 1 FROM public.users WHERE name = 'Администратор');

CREATE INDEX IF NOT EXISTS idx_collections_user
    ON public.collections(user_id);
