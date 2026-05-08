-- Migration to create the material_folders table and link it to interview_materials

CREATE TABLE IF NOT EXISTS public.material_folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Add folder_id to interview_materials
ALTER TABLE public.interview_materials ADD COLUMN IF NOT EXISTS folder_id UUID REFERENCES public.material_folders(id) ON DELETE SET NULL;

-- Enable RLS for material_folders
ALTER TABLE public.material_folders ENABLE ROW LEVEL SECURITY;

-- Policies for material_folders
CREATE POLICY "Allow authenticated read access for folders" 
ON public.material_folders 
FOR SELECT 
TO authenticated 
USING (true);

CREATE POLICY "Allow service role full access for folders" 
ON public.material_folders 
FOR ALL 
TO service_role 
USING (true) WITH CHECK (true);
