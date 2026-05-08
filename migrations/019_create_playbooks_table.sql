CREATE TABLE IF NOT EXISTS public.playbooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    industry TEXT,
    logo TEXT,
    hq TEXT,
    locations TEXT[] DEFAULT '{}',
    category TEXT,
    hiring_zone TEXT DEFAULT 'on-campus',
    hiring_seasons TEXT,
    hiring_type TEXT,
    roles TEXT[] DEFAULT '{}',
    difficulty TEXT DEFAULT 'Medium',
    difficulty_level INTEGER DEFAULT 3,
    rounds_count INTEGER DEFAULT 3,
    eligibility JSONB DEFAULT '{}',
    selection_process JSONB DEFAULT '[]',
    test_pattern JSONB DEFAULT '[]',
    syllabus JSONB DEFAULT '[]',
    registration_process TEXT[] DEFAULT '{}',
    compensation JSONB DEFAULT '{}',
    prep_focus TEXT,
    insider_scoop TEXT,
    jobs_link TEXT,
    cover_image TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.playbooks ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Public playbooks are viewable by everyone" ON public.playbooks
    FOR SELECT USING (true);

CREATE POLICY "Admins can insert playbooks" ON public.playbooks
    FOR INSERT WITH CHECK (auth.jwt() ->> 'role' = 'admin');

CREATE POLICY "Admins can update playbooks" ON public.playbooks
    FOR UPDATE USING (auth.jwt() ->> 'role' = 'admin');

CREATE POLICY "Admins can delete playbooks" ON public.playbooks
    FOR DELETE USING (auth.jwt() ->> 'role' = 'admin');

-- Indexing
CREATE INDEX idx_playbooks_slug ON public.playbooks(slug);
CREATE INDEX idx_playbooks_hiring_zone ON public.playbooks(hiring_zone);
