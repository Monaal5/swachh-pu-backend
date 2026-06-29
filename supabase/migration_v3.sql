-- ============================================================
-- Swachh PU Abhiyaan — Migration v3: Task Verification Flow
-- Adds completion photo, verification timestamp, rejection reason,
-- due date, and expands task status choices.
-- ============================================================

-- 1. ADD NEW COLUMNS TO TASKS TABLE
ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS completion_photo_url TEXT,
    ADD COLUMN IF NOT EXISTS completion_submitted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS rejection_reason TEXT,
    ADD COLUMN IF NOT EXISTS due_date TIMESTAMPTZ;

-- 2. UPDATE STATUS CHECK CONSTRAINT
-- Drop existing status check constraint if it exists (default name created by postgres or schema.sql)
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_status_check;

-- Add updated check constraint allowing new lifecycle statuses
ALTER TABLE tasks ADD CONSTRAINT tasks_status_check
    CHECK (status IN ('pending', 'assigned', 'pending_verification', 'completed', 'rework_required', 'rejected'));

-- 3. INDEX FOR FAST LOOKUP BY STATUS & ASSIGNEE
CREATE INDEX IF NOT EXISTS idx_tasks_status_assigned ON tasks(status, assigned_to);
