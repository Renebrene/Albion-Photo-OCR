-- Case-insensitive uniqueness for client/brand aliases.
--
-- The facet queries join aliases with LOWER(alias) = LOWER(client), while the
-- old PK (kind, alias) is case-sensitive. Two rows "Сбер" and "сбер" were
-- therefore both valid and doubled the facet count. The application now
-- upserts case-insensitively; this index makes the invariant a DB guarantee.
--
-- Apply with the normal migration runner on the next maintenance run. If
-- legacy case-duplicates exist, the index creation fails: resolve them first
-- (keep the row with the intended spelling, point the other spelling's
-- canonical at the same client).
--
-- Rollback:
--   DROP INDEX IF EXISTS public.ux_client_aliases_kind_lower_alias;

CREATE UNIQUE INDEX IF NOT EXISTS ux_client_aliases_kind_lower_alias
    ON public.client_aliases (kind, lower(alias));
