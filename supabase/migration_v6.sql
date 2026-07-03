-- ============================================================
-- Swachh PU Abhiyaan — Migration v6: Worker Login & Details
-- ============================================================

-- 1. Add columns to master_workers
ALTER TABLE master_workers 
    ADD COLUMN IF NOT EXISTS username VARCHAR(50) UNIQUE,
    ADD COLUMN IF NOT EXISTS password VARCHAR(255),
    ADD COLUMN IF NOT EXISTS address TEXT,
    ADD COLUMN IF NOT EXISTS date_of_joining DATE DEFAULT CURRENT_DATE;

-- 2. Update existing seeded master workers
UPDATE master_workers 
SET 
    username = 'ramesh101', 
    password = 'pass101', 
    address = '123, Green Street, City, State', 
    date_of_joining = '2022-06-01'::DATE
WHERE worker_id = 'EMP101';

UPDATE master_workers 
SET 
    username = 'suresh102', 
    password = 'pass102', 
    address = '456, Blue Avenue, City, State', 
    date_of_joining = '2023-01-15'::DATE
WHERE worker_id = 'EMP102';

UPDATE master_workers 
SET 
    username = 'anita103', 
    password = 'pass103', 
    address = '789, Red Lane, City, State', 
    date_of_joining = '2023-05-10'::DATE
WHERE worker_id = 'EMP103';
