-- Сессионные токены хранятся хэшем, а не открытым текстом.
--
-- Bearer-токен И ЕСТЬ идентификатор сессии, поэтому дамп базы (бэкап, реплика,
-- лог запроса) отдавал рабочие учётные данные всех вошедших пользователей.
-- После миграции в таблице остаётся только SHA-256; сам токен живёт в браузере
-- пользователя и больше нигде.
--
-- Существующие входы сохраняются: хэш считается из уже лежащего в базе
-- значения, пока колонка ещё на месте. Но API нужно перезапустить сразу после
-- миграции — работающий процесс всё ещё ищет сессию по session_id.
--
-- Откат: открытые токены восстановить нельзя (в этом и смысл). Откат означает
-- вернуть таблицу без хэша и всем войти заново:
--   ALTER TABLE public.sessions ADD COLUMN session_id TEXT;
--   ALTER TABLE public.sessions DROP CONSTRAINT sessions_pkey;
--   ALTER TABLE public.sessions DROP COLUMN token_hash;
--   ALTER TABLE public.sessions ADD PRIMARY KEY (session_id);
-- После отката все текущие сессии недействительны.

ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS token_hash TEXT;

UPDATE public.sessions
   SET token_hash = encode(sha256(session_id::bytea), 'hex')
 WHERE token_hash IS NULL;

ALTER TABLE public.sessions ALTER COLUMN token_hash SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_sessions_token_hash
    ON public.sessions (token_hash);

ALTER TABLE public.sessions DROP CONSTRAINT IF EXISTS sessions_pkey;
ALTER TABLE public.sessions DROP COLUMN IF EXISTS session_id;
ALTER TABLE public.sessions ADD PRIMARY KEY (token_hash);
