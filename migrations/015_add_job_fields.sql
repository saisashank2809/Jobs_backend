-- Migration: Add new job fields to jobs_jobs table
ALTER TABLE jobs_jobs ADD COLUMN IF NOT EXISTS company_name TEXT;
ALTER TABLE jobs_jobs ADD COLUMN IF NOT EXISTS external_apply_url TEXT;
ALTER TABLE jobs_jobs ADD COLUMN IF NOT EXISTS work_mode TEXT DEFAULT 'Onsite';
ALTER TABLE jobs_jobs ADD COLUMN IF NOT EXISTS location TEXT;
