-- Add phone and location columns to users_jobs table
ALTER TABLE users_jobs ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE users_jobs ADD COLUMN IF NOT EXISTS location TEXT;
