ALTER TABLE public.users_jobs 
ADD COLUMN dob TEXT,
ADD COLUMN aspirations TEXT[] DEFAULT '{}';
