-- Migration 001: widen submission score columns from integer to float
--
-- Context: ai_score / trainer_score / final_score were INTEGER, truncating
-- fractional quiz partial-credit and percentage results (e.g. 66.67 -> 66).
-- The columns are now Float (double precision). SQLAlchemy create_all does not
-- ALTER existing columns, so run this ONCE against each existing PostgreSQL
-- database. Fresh databases created after this change already use float.
--
-- Usage:
--   psql "postgresql://<user>:<pass>@<host>:<port>/<db>" -f 001_float_scores.sql
-- or via docker compose:
--   docker compose exec -T postgres \
--     psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f - < 001_float_scores.sql

ALTER TABLE test_submissions
    ALTER COLUMN ai_score      TYPE double precision USING ai_score::double precision,
    ALTER COLUMN trainer_score TYPE double precision USING trainer_score::double precision,
    ALTER COLUMN final_score   TYPE double precision USING final_score::double precision;
