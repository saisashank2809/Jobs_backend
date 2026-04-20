-- Migration: Add structured role overview storage for jobs
ALTER TABLE jobs_jobs ADD COLUMN IF NOT EXISTS role_overview JSONB;
