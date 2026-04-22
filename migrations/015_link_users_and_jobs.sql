-- ============================================================
-- MIGRATION: Link users and users_jobs
-- ============================================================
-- Run this in your Supabase SQL Editor.
-- This ensures that both tables stay in sync and new signups
-- (including Google Auth) automatically create a profile.
-- ============================================================

-- 1. Add Foreign Key to users_jobs (link to shared users)
ALTER TABLE public.users_jobs
DROP CONSTRAINT IF EXISTS fk_users_jobs_user_id;

ALTER TABLE public.users_jobs
ADD CONSTRAINT fk_users_jobs_user_id
FOREIGN KEY (id) REFERENCES public.users(user_id)
ON DELETE CASCADE;

-- 2. Trigger Function: Sync changes from 'users' -> 'users_jobs'
-- This ensures that if a name or email changes in the shared table,
-- it is updated in your project table too.
CREATE OR REPLACE FUNCTION public.sync_user_to_jobs()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE public.users_jobs
  SET 
    email = NEW.email,
    full_name = NEW.full_name,
    phone = NEW.phone,
    role = NEW.role,
    password = NEW.password_hash
  WHERE id = NEW.user_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_user_updated_sync ON public.users;
CREATE TRIGGER on_user_updated_sync
  AFTER UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION public.sync_user_to_jobs();

-- 3. Trigger Function: Auto-create 'users_jobs' row on new signup
-- This is critical for Google Auth. When a new user logs in via Google,
-- Supabase creates a row in 'users', and this trigger will create 
-- the corresponding entry in 'users_jobs'.
CREATE OR REPLACE FUNCTION public.handle_new_user_jobs()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users_jobs (id, email, full_name, phone, role, password)
  VALUES (
    NEW.user_id, 
    NEW.email, 
    COALESCE(NEW.full_name, split_part(NEW.email, '@', 1)), 
    NEW.phone, 
    NEW.role, 
    COALESCE(NEW.password_hash, '$2b$12$00000000000000000000000000000000000000000000000000000')
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_user_created_jobs ON public.users;
CREATE TRIGGER on_user_created_jobs
  AFTER INSERT ON public.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_jobs();
