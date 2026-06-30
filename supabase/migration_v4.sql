-- ============================================================
-- Swachh PU Abhiyaan — Migration v4: Make ID Card Nullable
-- ============================================================
ALTER TABLE worker_profiles ALTER COLUMN id_card_image DROP NOT NULL;
ALTER TABLE faculty_profiles ALTER COLUMN id_card_image DROP NOT NULL;
