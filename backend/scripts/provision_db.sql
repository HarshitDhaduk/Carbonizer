-- Carbonizer — database provisioning (idempotent).
-- Creates the application role + database. Run once as the postgres superuser:
--
--   "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h 127.0.0.1 -U postgres -d postgres -f backend\scripts\provision_db.sql
--
-- (psql will prompt for the postgres password.)
-- The role password here ('carbonizer') matches the default DATABASE_URL in
-- app/core/config.py. Change both together if you want a different password.

-- 1) application login role
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'carbonizer') THEN
      CREATE ROLE carbonizer WITH LOGIN PASSWORD 'carbonizer';
      RAISE NOTICE 'created role carbonizer';
   ELSE
      RAISE NOTICE 'role carbonizer already exists — leaving as-is';
   END IF;
END
$$;

-- 2) database owned by that role (CREATE DATABASE can't run inside a DO block,
--    so generate + execute it conditionally with \gexec)
SELECT 'CREATE DATABASE carbonizer OWNER carbonizer'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'carbonizer')\gexec

-- 3) privileges
GRANT ALL PRIVILEGES ON DATABASE carbonizer TO carbonizer;

\echo 'Provisioning complete. Verify with: \l carbonizer  and  \du carbonizer'
