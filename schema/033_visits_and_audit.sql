-- Посещения (учёт входов) и аудит нормализации клиентов.
--
-- user_visits: одна строка на событие входа/выхода. Имя хранится снимком,
--   чтобы список посещений переживал переименование или архивацию пользователя.
-- client_alias_audit: журнал правок справочника алиасов «кто/что/когда».
--   Исходные строки photo_qwen, как и раньше, не переписываются.
--
-- Откат:
--   DROP TABLE IF EXISTS public.client_alias_audit;
--   DROP TABLE IF EXISTS public.user_visits;

CREATE TABLE IF NOT EXISTS public.user_visits (
    visit_id   BIGSERIAL PRIMARY KEY,
    user_id    BIGINT REFERENCES public.users(user_id) ON DELETE SET NULL,
    user_name  TEXT NOT NULL,
    event      TEXT NOT NULL DEFAULT 'login'
               CHECK (event IN ('login', 'logout')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_user_visits_created
    ON public.user_visits (created_at DESC);

CREATE INDEX IF NOT EXISTS ix_user_visits_user
    ON public.user_visits (user_id);

CREATE TABLE IF NOT EXISTS public.client_alias_audit (
    audit_id      BIGSERIAL PRIMARY KEY,
    actor         TEXT,
    alias         TEXT NOT NULL,
    canonical_old TEXT,
    canonical_new TEXT,
    action        TEXT NOT NULL
                  CHECK (action IN ('create', 'update', 'delete')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_client_alias_audit_created
    ON public.client_alias_audit (created_at DESC);
