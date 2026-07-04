-- ============================================================
-- Swachh PU Abhiyaan — Migration v7: Worker Email-Based Login
-- Workers login directly with email + password (no signup needed).
-- Replaces username-based login with email-based login.
-- ============================================================

-- 1. Add email column to master_workers (if not exists)
ALTER TABLE master_workers 
    ADD COLUMN IF NOT EXISTS email VARCHAR(255) UNIQUE;

-- 2. Update existing seeded master workers with email and strong passwords
-- Password rules: min 8 chars, starts with uppercase, has special character

UPDATE master_workers 
SET 
    email = 'ramesh.kumar@swachh.pu',
    password = 'Ramesh@101'
WHERE worker_id = 'EMP101';

UPDATE master_workers 
SET 
    email = 'suresh.singh@swachh.pu',
    password = 'Suresh@102'
WHERE worker_id = 'EMP102';

UPDATE master_workers 
SET 
    email = 'anita.devi@swachh.pu',
    password = 'Anita@103'
WHERE worker_id = 'EMP103';

-- 3. Create index on email for fast lookups
CREATE INDEX IF NOT EXISTS idx_master_workers_email ON master_workers(email);
