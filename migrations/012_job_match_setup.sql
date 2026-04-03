-- Migration: 012_job_match_setup.sql
-- Goal: Prepare tables for deterministic job matching (Skills & Interests)

-- 1. users_jobs: Modify interests from TEXT to TEXT[]
DO $$
BEGIN
    -- Check if column is already an array to avoid error on re-run
    IF (SELECT data_type FROM information_schema.columns 
        WHERE table_name = 'users_jobs' AND column_name = 'interests') = 'text' THEN
        
        -- Migrate data: Wrap existing text in an array, or default to empty array
        ALTER TABLE users_jobs 
        ALTER COLUMN interests TYPE TEXT[] 
        USING CASE 
            WHEN interests IS NULL OR interests = '' THEN '{}'::TEXT[]
            ELSE ARRAY[TRIM(interests)]
        END;
    END IF;
END $$;

-- Set default value for interests if not already set
ALTER TABLE users_jobs ALTER COLUMN interests SET DEFAULT '{}';

-- 2. jobs_jobs: Ensure matching columns exist with correct types
-- required_skills (TEXT[])
-- optional_skills (TEXT[])
-- tags (TEXT[])
-- experience_required (TEXT)

ALTER TABLE jobs_jobs ADD COLUMN IF NOT EXISTS required_skills TEXT[] DEFAULT '{}';
ALTER TABLE jobs_jobs ADD COLUMN IF NOT EXISTS optional_skills TEXT[] DEFAULT '{}';
ALTER TABLE jobs_jobs ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';
ALTER TABLE jobs_jobs ADD COLUMN IF NOT EXISTS experience_required TEXT;

-- Indexing for fast matching (PostgreSQL GIN index for arrays)
CREATE INDEX IF NOT EXISTS idx_users_jobs_skills_gin ON users_jobs USING GIN (skills);
CREATE INDEX IF NOT EXISTS idx_users_jobs_interests_gin ON users_jobs USING GIN (interests);
CREATE INDEX IF NOT EXISTS idx_jobs_jobs_required_skills_gin ON jobs_jobs USING GIN (required_skills);
CREATE INDEX IF NOT EXISTS idx_jobs_jobs_tags_gin ON jobs_jobs USING GIN (tags);
