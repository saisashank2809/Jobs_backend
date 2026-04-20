-- Migration 014: align mock interview persistence with admin review workflow.

ALTER TABLE IF EXISTS mock_interviews_jobs
    ALTER COLUMN job_id DROP NOT NULL;

ALTER TABLE IF EXISTS mock_interviews_jobs
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS viewed_at TIMESTAMPTZ NULL;

ALTER TABLE IF EXISTS mock_interviews_jobs
    ALTER COLUMN transcript SET DEFAULT '[]'::jsonb;

ALTER TABLE IF EXISTS mock_interviews_jobs
    ALTER COLUMN status SET DEFAULT 'in_progress';

UPDATE mock_interviews_jobs
SET status = 'pending_review'
WHERE status = 'completed';

CREATE INDEX IF NOT EXISTS idx_mock_interviews_jobs_status_created_at
    ON mock_interviews_jobs (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mock_interviews_jobs_user_id
    ON mock_interviews_jobs (user_id);
