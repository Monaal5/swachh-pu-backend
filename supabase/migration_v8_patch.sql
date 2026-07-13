-- Run this in the Supabase SQL Editor to secure the tables:

DROP POLICY IF EXISTS "Service role can modify locations" ON locations;
DROP POLICY IF EXISTS "Service role can modify blocks" ON blocks;
DROP POLICY IF EXISTS "Service role can modify floors" ON floors;
DROP POLICY IF EXISTS "Service role can modify rooms" ON rooms;

-- Clean up any test records
DELETE FROM locations WHERE name = 'Forbidden Location';
DELETE FROM locations WHERE name = 'Admin Test Location';
DELETE FROM locations WHERE name = 'Admin Test Location Updated';
