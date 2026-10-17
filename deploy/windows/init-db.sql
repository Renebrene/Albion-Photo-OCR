-- Runs once, on an empty PostgreSQL volume (docker-entrypoint-initdb.d).
-- Search suggestions and trigram indexes require pg_trgm.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
