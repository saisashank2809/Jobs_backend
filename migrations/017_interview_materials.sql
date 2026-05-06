-- Migration to create the interview_materials table

CREATE TABLE IF NOT EXISTS public.interview_materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(200) NOT NULL,
    title VARCHAR(200) NOT NULL,
    file_url TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.interview_materials ENABLE ROW LEVEL SECURITY;

-- Allow read access to authenticated users
CREATE POLICY "Allow authenticated read access" 
ON public.interview_materials 
FOR SELECT 
TO authenticated 
USING (true);

-- Allow all access to service role (backend API uses service key typically, or we can just allow it)
CREATE POLICY "Allow service role full access" 
ON public.interview_materials 
FOR ALL 
TO service_role 
USING (true) WITH CHECK (true);
