-- Update the users_jobs table to add avatar_url support
ALTER TABLE public.users_jobs ADD COLUMN avatar_url TEXT;
