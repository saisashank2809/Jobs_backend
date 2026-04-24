-- Create feedback table
CREATE TABLE IF NOT EXISTS feedbacks_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('job_platform', 'mock_interview')),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT NOT NULL,
    interview_id UUID REFERENCES mock_interviews(id) ON DELETE SET NULL,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    meta JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_feedbacks_user_id ON feedbacks_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_feedbacks_type ON feedbacks_jobs(type);
CREATE INDEX IF NOT EXISTS idx_feedbacks_created_at ON feedbacks_jobs(created_at DESC);

-- Enable RLS
ALTER TABLE feedbacks_jobs ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Seekers: Can insert their own feedback
CREATE POLICY "Users can insert their own feedback" 
ON feedbacks_jobs FOR INSERT 
WITH CHECK (auth.uid() = user_id);

-- Seekers: Can view their own feedback
CREATE POLICY "Users can view their own feedback" 
ON feedbacks_jobs FOR SELECT 
USING (auth.uid() = user_id);

-- Admins: Can view all feedback
CREATE POLICY "Admins can view all feedback" 
ON feedbacks_jobs FOR SELECT 
USING (
    EXISTS (
        SELECT 1 FROM users_jobs 
        WHERE users_jobs.id = auth.uid() 
        AND users_jobs.role = 'admin'
    )
);
