-- =============================================================================
-- Provisioning PostgreSQL dengan hak minimum (Nusantara Trans)
-- =============================================================================
-- Jalankan sebagai superuser cluster (postgres), SEKALI saat instalasi:
--
--   sudo -u postgres psql -v ON_ERROR_STOP=1 \
--     -v owner_password="$(openssl rand -base64 24)" \
--     -v app_password="$(openssl rand -base64 24)" \
--     -f deploy/db_setup.sql
--
-- Simpan kedua password di secret manager. Yang dipakai aplikasi sehari-hari
-- HANYA nt_app (runtime). nt_owner hanya dipakai saat `manage.py migrate`.
--
-- Prinsip:
--   * nt_app  : LOGIN, tanpa SUPERUSER/CREATEDB/CREATEROLE/BYPASSRLS/REPLICATION.
--   * nt_owner: pemilik skema/tabel, dipakai untuk migrasi.
--   * PUBLIC   : tidak boleh CREATE di schema public (default PG15+ memang
--                dicabut; tetap ditegaskan untuk cluster lama).
--   * Aplikasi tidak pernah memakai role superuser cluster.
-- =============================================================================

\set ON_ERROR_STOP on

-- Role migrasi (pemilik objek)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nt_owner') THEN
    EXECUTE format('CREATE ROLE nt_owner LOGIN PASSWORD %L', :'owner_password');
  ELSE
    EXECUTE format('ALTER ROLE nt_owner PASSWORD %L', :'owner_password');
  END IF;
END $$;

-- Role runtime aplikasi (hak minimum)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nt_app') THEN
    EXECUTE format('CREATE ROLE nt_app LOGIN PASSWORD %L', :'app_password');
  ELSE
    EXECUTE format('ALTER ROLE nt_app PASSWORD %L', :'app_password');
  END IF;
END $$;

ALTER ROLE nt_owner NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE nt_app   NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

-- Database dimiliki role migrasi (bukan superuser).
SELECT 'CREATE DATABASE nusantartrans OWNER nt_owner'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'nusantartrans')
\gexec

\connect nusantartrans

-- Jangan biarkan semua user membuat objek di schema public.
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO nt_owner, nt_app;
GRANT CREATE ON SCHEMA public TO nt_owner;

GRANT CONNECT ON DATABASE nusantartrans TO nt_app;

-- Tabel/sequence yang dibuat nt_owner otomatis bisa dibaca/ditulis nt_app.
ALTER DEFAULT PRIVILEGES FOR ROLE nt_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO nt_app;
ALTER DEFAULT PRIVILEGES FOR ROLE nt_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO nt_app;

-- Untuk objek yang SUDAH ada (jalankan ulang skrip setelah migrasi awal):
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nt_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nt_app;

-- Pastikan tidak ada hak berlebih dari masa lalu.
ALTER DEFAULT PRIVILEGES FOR ROLE nt_app IN SCHEMA public
  REVOKE ALL ON TABLES FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM nt_app;

\echo ''
\echo 'Selesai. Set di .env produksi:'
\echo '  POSTGRES_USER=nt_app        (runtime)'
\echo '  POSTGRES_PASSWORD=<app_password>'
\echo '  POSTGRES_SSLMODE=require'
\echo 'Migrasi: jalankan `manage.py migrate` dengan POSTGRES_USER=nt_owner.'
