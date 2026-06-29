-- ============================================================
-- Swachh PU Abhiyaan — Migration v2: Authentication & Registration System
-- Implements USERS, EMAIL_OTPS, STUDENT_PROFILES, FACULTY_PROFILES,
-- WORKER_PROFILES, and MASTER_WORKERS tables based on diagram specs.
-- ============================================================

-- Drop old conflicting tables from v1 if they exist
DROP TABLE IF EXISTS student_profiles CASCADE;
DROP TABLE IF EXISTS worker_profiles CASCADE;
DROP TABLE IF EXISTS faculty_profiles CASCADE;
DROP TABLE IF EXISTS email_otps CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS master_workers CASCADE;

-- 1. MASTER WORKERS TABLE
CREATE TABLE master_workers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id   VARCHAR(50) NOT NULL UNIQUE,
    full_name   VARCHAR(100) NOT NULL,
    department  VARCHAR(100) NOT NULL,
    phone       VARCHAR(20),
    designation VARCHAR(100) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_master_workers_worker_id ON master_workers(worker_id);

-- 2. USERS TABLE
CREATE TABLE users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              VARCHAR(100) NOT NULL,
    email             VARCHAR(255) NOT NULL UNIQUE,
    password_hash     TEXT NOT NULL,
    role              VARCHAR(20) NOT NULL CHECK (role IN ('student', 'faculty', 'worker', 'admin')),
    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);

-- 3. EMAIL OTPS TABLE
CREATE TABLE email_otps (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    otp        VARCHAR(6) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_used    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_email_otps_user_id ON email_otps(user_id);

-- 4. STUDENT PROFILES TABLE
CREATE TABLE student_profiles (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    roll_no    VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_student_profiles_user_id ON student_profiles(user_id);

-- 5. FACULTY PROFILES TABLE
CREATE TABLE faculty_profiles (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    faculty_id   VARCHAR(50) NOT NULL UNIQUE,
    faculty_type VARCHAR(20) NOT NULL CHECK (faculty_type IN ('teaching', 'non_teaching')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_faculty_profiles_user_id ON faculty_profiles(user_id);

-- 6. WORKER PROFILES TABLE
CREATE TABLE worker_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    master_worker_id    UUID NOT NULL REFERENCES master_workers(id) ON DELETE RESTRICT,
    id_card_image       TEXT NOT NULL,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    verified_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_at         TIMESTAMPTZ,
    rejection_reason    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_worker_profiles_user_id ON worker_profiles(user_id);
CREATE INDEX idx_worker_profiles_verification_status ON worker_profiles(verification_status);

-- Seed Sample Master Workers for testing
INSERT INTO master_workers (worker_id, full_name, department, phone, designation, status)
VALUES 
    ('EMP101', 'Ramesh Kumar', 'Sanitation', '9876543210', 'Senior Sanitation Officer', 'active'),
    ('EMP102', 'Suresh Singh', 'Maintenance', '9876543211', 'Maintenance Technician', 'active'),
    ('EMP103', 'Anita Devi', 'Sanitation', '9876543212', 'Sanitation Worker', 'active')
ON CONFLICT (worker_id) DO NOTHING;
