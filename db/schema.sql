-- ============================================================
-- Swachh PU Abhiyaan — PostgreSQL schema (Neon or any Postgres 13+)
-- Consolidates supabase/schema.sql + migrations v2–v8 into one file.
-- Safe to run more than once.
-- ============================================================

-- updated_at helper
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ── Users & roles ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              VARCHAR(100) NOT NULL,
    email             VARCHAR(255) NOT NULL UNIQUE,
    phone             VARCHAR(20),
    password_hash     TEXT NOT NULL,
    role              VARCHAR(20) NOT NULL CHECK (role IN ('student', 'faculty', 'worker', 'admin')),
    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

CREATE TABLE IF NOT EXISTS profiles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),   -- equals users.id
    user_id     UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('student', 'faculty', 'worker', 'admin')),
    phone       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_profiles_role ON profiles(role);

CREATE TABLE IF NOT EXISTS master_workers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id       VARCHAR(50) NOT NULL UNIQUE,
    full_name       VARCHAR(100) NOT NULL,
    department      VARCHAR(100) NOT NULL,
    phone           VARCHAR(20),
    designation     VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    username        VARCHAR(50) UNIQUE,
    password        VARCHAR(255),
    email           VARCHAR(255) UNIQUE,
    address         TEXT,
    date_of_joining DATE DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS email_otps (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    otp        VARCHAR(6) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    is_used    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_email_otps_user_id ON email_otps(user_id);

CREATE TABLE IF NOT EXISTS student_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    roll_no             VARCHAR(50) NOT NULL UNIQUE,
    address             TEXT,
    hostel              TEXT,
    id_card_image       TEXT,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    verified_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_at         TIMESTAMPTZ,
    rejection_reason    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS faculty_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    faculty_id          VARCHAR(50) NOT NULL UNIQUE,
    faculty_type        VARCHAR(20) NOT NULL CHECK (faculty_type IN ('teaching', 'non_teaching')),
    id_card_image       TEXT,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    verified_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_at         TIMESTAMPTZ,
    rejection_reason    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS worker_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    master_worker_id    UUID NOT NULL REFERENCES master_workers(id) ON DELETE RESTRICT,
    employee_id         TEXT,
    zone                TEXT,
    id_card_image       TEXT,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'rejected')),
    verified_by         UUID REFERENCES users(id) ON DELETE SET NULL,
    verified_at         TIMESTAMPTZ,
    rejection_reason    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Campus location hierarchy ───────────────────────────────
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS blocks (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (location_id, name)
);
CREATE TABLE IF NOT EXISTS floors (
    id SERIAL PRIMARY KEY,
    block_id INTEGER NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (block_id, name)
);
CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    floor_id INTEGER NOT NULL REFERENCES floors(id) ON DELETE CASCADE,
    room_number TEXT NOT NULL DEFAULT 'N/A',
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (floor_id, room_number, name)
);

-- ── Tasks (complaints) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    photo_url               TEXT NOT NULL,
    latitude                FLOAT8 NOT NULL,
    longitude               FLOAT8 NOT NULL,
    audio_url               TEXT,
    description             TEXT NOT NULL,
    profile_id              UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    assigned_to             UUID REFERENCES profiles(id) ON DELETE SET NULL,
    status                  TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'assigned', 'pending_verification', 'completed', 'rework_required', 'rejected')),
    due_date                TIMESTAMPTZ,
    completion_photo_url    TEXT,
    completion_submitted_at TIMESTAMPTZ,
    rejection_reason        TEXT,
    location_id             INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    block_id                INTEGER REFERENCES blocks(id) ON DELETE SET NULL,
    floor_id                INTEGER REFERENCES floors(id) ON DELETE SET NULL,
    room_id                 INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tasks_profile_id ON tasks(profile_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status_assigned ON tasks(status, assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);

-- ── Uploaded media (replaces Supabase Storage buckets) ──────
CREATE TABLE IF NOT EXISTS media (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bucket       TEXT NOT NULL,
    path         TEXT NOT NULL,
    content_type TEXT NOT NULL,
    data         BYTEA NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (bucket, path)
);

-- ── updated_at triggers ─────────────────────────────────────
DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['users', 'student_profiles', 'faculty_profiles', 'worker_profiles', 'tasks'] LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_updated_at ON %I', t, t);
        EXECUTE format('CREATE TRIGGER trg_%s_updated_at BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION set_updated_at()', t, t);
    END LOOP;
END $$;
