-- Add asset_url so we store the source URL and can skip re-downloading when file exists.
-- Safe to run on existing DBs (IF NOT EXISTS).
ALTER TABLE ads ADD COLUMN IF NOT EXISTS asset_url TEXT;
