-- ============================================================
-- Swachh PU Abhiyaan — Migration v5: Link profiles to public users table
-- ============================================================

-- 1. Drop the foreign key constraint referencing auth.users(id)
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_user_id_fkey;

-- 1.5 Clean up legacy orphan records that do not exist in the new public.users table
DELETE FROM tasks WHERE profile_id NOT IN (SELECT id FROM users);
DELETE FROM tasks WHERE assigned_to IS NOT NULL AND assigned_to NOT IN (SELECT id FROM users);
DELETE FROM student_profiles WHERE user_id NOT IN (SELECT id FROM users);
DELETE FROM faculty_profiles WHERE user_id NOT IN (SELECT id FROM users);
DELETE FROM worker_profiles WHERE user_id NOT IN (SELECT id FROM users);
DELETE FROM profiles WHERE user_id NOT IN (SELECT id FROM users);

-- 2. Add foreign key constraint referencing public.users(id)
ALTER TABLE profiles 
    ADD CONSTRAINT profiles_user_id_fkey 
    FOREIGN KEY (user_id) 
    REFERENCES public.users(id) 
    ON DELETE CASCADE;

-- 3. Drop existing role constraint if it exists
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_role_check;

-- 4. Add updated check constraint to support the 'faculty' role
ALTER TABLE profiles 
    ADD CONSTRAINT profiles_role_check 
    CHECK (role IN ('student', 'faculty', 'worker', 'admin'));
