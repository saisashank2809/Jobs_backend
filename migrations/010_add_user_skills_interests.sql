-- Add skills (text array) and interests (text) to user profile
ALTER TABLE users_jobs ADD COLUMN IF NOT EXISTS skills TEXT[] DEFAULT '{}';
ALTER TABLE users_jobs ADD COLUMN IF NOT EXISTS interests TEXT;
