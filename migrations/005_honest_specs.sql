-- ============================================================
-- 005 — Honest specs: stop presenting unsourced numbers as facts
-- Run in the Supabase SQL Editor (after 003 and 004).
--
-- Verification (003) confirms a building EXISTS where we say it does. It never
-- confirmed floor or elevator counts — yet the UI was showing both as hard facts
-- for verified buildings. Those numbers came from the original (fabricated) seed.
--
-- New rule, matching "don't present a guess as a fact":
--   • Elevator counts have no authoritative public source anywhere, so the app now
--     always shows them as a community estimate ("~N · est") — never as fact.
--     (No schema change needed; this is handled in js/drawer.js + js/ui.js.)
--   • Floor counts are a fact ONLY where OpenStreetMap's building:levels confirms
--     them. This adds a `stories_verified` flag for exactly those, so every other
--     floor count renders as "· est", even on otherwise-verified buildings.
-- ============================================================

alter table buildings add column if not exists stories_verified boolean not null default false;

-- Reset, then flag the buildings whose floor count OSM building:levels confirms.
-- These are the only two the Overpass audit found a real building:levels for
-- (scripts/verify_overpass.py); the values were already set in migration 003.
update buildings set stories_verified = false;
update buildings set stories = 2, stories_verified = true where id = 51;   -- 585 Stewart Ave  (OSM building:levels = 2)
update buildings set stories = 6, stories_verified = true where id = 102;  -- Nassau County Courthouse (OSM building:levels = 6)

-- Sanity check.
select
  count(*) filter (where stories_verified)     as floors_confirmed,
  count(*) filter (where not stories_verified) as floors_estimated,
  count(*)                                      as total
from buildings;
