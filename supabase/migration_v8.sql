-- ============================================================
-- Swachh PU Abhiyaan — Migration v8: Location Hierarchy
-- Creates locations, blocks, floors, and rooms tables.
-- Integrates location fields into tasks table.
-- Sets up public read policies (RLS).
-- ============================================================

-- 1. Create locations table
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Create blocks table
CREATE TABLE IF NOT EXISTS blocks (
    id SERIAL PRIMARY KEY,
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (location_id, name)
);

-- 3. Create floors table
CREATE TABLE IF NOT EXISTS floors (
    id SERIAL PRIMARY KEY,
    block_id INTEGER NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (block_id, name)
);

-- 4. Create rooms table
CREATE TABLE IF NOT EXISTS rooms (
    id SERIAL PRIMARY KEY,
    floor_id INTEGER NOT NULL REFERENCES floors(id) ON DELETE CASCADE,
    room_number TEXT NOT NULL DEFAULT 'N/A',
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (floor_id, room_number, name)
);

-- 5. Add hierarchy columns to tasks table
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS block_id INTEGER REFERENCES blocks(id) ON DELETE SET NULL;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS floor_id INTEGER REFERENCES floors(id) ON DELETE SET NULL;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL;

-- 6. Enable Row Level Security (RLS)
ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE floors ENABLE ROW LEVEL SECURITY;
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;

-- 7. Create Read (SELECT) Policies for anyone
CREATE POLICY "Anyone can read locations" ON locations FOR SELECT USING (true);
CREATE POLICY "Anyone can read blocks" ON blocks FOR SELECT USING (true);
CREATE POLICY "Anyone can read floors" ON floors FOR SELECT USING (true);
CREATE POLICY "Anyone can read rooms" ON rooms FOR SELECT USING (true);

-- 8. Service role bypasses RLS automatically, so no write policies are needed for seeding or backend updates.
-- This keeps the tables read-only for public anon/authenticated users.

