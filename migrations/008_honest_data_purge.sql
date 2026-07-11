-- ============================================================
-- 008 — Honest data purge: delete phantoms, adopt real names, unfake the numbers
-- Run in the Supabase SQL Editor (after 007). Safe to re-run.
--
-- The multi-source audit (scripts/verify_sources.py) could confirm only 175 of
-- 572 buildings exist. This migration finishes the job the "est" badges started:
--   1. DELETE the 397 buildings no source could confirm (reviews cascade).
--   2. Adopt canonical names from the confirming source (curated: OSM names that
--      are stale/sloppier than ours were NOT adopted — list at bottom).
--   3. Stories: NULL unless OSM building polygons actually carry the data
--      (scripts/resource_floors.py). Name-matched polygon => verified fact;
--      unnamed polygon at the point => sourced estimate; nothing => NULL.
--   4. Elevators: NULL everywhere. No public source exists; the old numbers
--      were invented. Real counts must come from community reports.
-- ============================================================

alter table buildings alter column stories   drop not null;
alter table buildings alter column elevators drop not null;

-- 1. Remove every building the audit could not confirm exists.
delete from buildings where not verified;

-- 2. Canonical names from the confirming source.
update buildings set name = '585 Stewart Avenue' where id = 51;
update buildings set name = '400 Crossways Park Drive' where id = 63;
update buildings set name = 'Middle Country Public Library (Centereach)' where id = 127;
update buildings set name = '999 Stewart Avenue' where id = 169;
update buildings set name = 'The Smithtown Library — Main Branch' where id = 244;
update buildings set name = 'Great Neck Public Library — Main Branch' where id = 247;
update buildings set name = 'Broadway Mall' where id = 251;
update buildings set name = 'Long Island Aquarium and Exhibition Center' where id = 255;
update buildings set name = 'Nassau Veterans Memorial Coliseum' where id = 256;
update buildings set name = 'Gurwin Jewish Nursing & Rehabilitation Center' where id = 262;
update buildings set name = 'The Bristal Assisted Living at Westbury' where id = 264;
update buildings set name = 'Suffolk County Vanderbilt Museum' where id = 385;
update buildings set name = 'Mid-Island Y JCC' where id = 404;
update buildings set name = 'Bay Shore–Brightwaters Public Library' where id = 438;
update buildings set name = '1770 House Restaurant & Inn' where id = 541;
update buildings set name = 'The Greenporter Hotel' where id = 542;
update buildings set name = '350 Jericho Turnpike' where id = 561;
update buildings set name = 'Jericho Middle / High School' where id = 581;
update buildings set name = 'William A. Shine Great Neck South High School' where id = 583;
update buildings set name = 'Temple Beth-El of Great Neck' where id = 601;

-- 3. Floor counts: wipe the fabrications, keep only what OSM building data supports.
update buildings set stories = null, stories_verified = false;
-- Verified facts: name-matched building polygon carries building:levels.
update buildings set stories = 2, stories_verified = true  where id = 3;  -- Roosevelt Field Mall (osm way/328660194, 0m)
update buildings set stories = 2, stories_verified = true  where id = 51;  -- 585 Stewart Ave (osm way/328660183, 0m)
update buildings set stories = 3, stories_verified = true  where id = 91;  -- Farmingdale State College — Gleeson Hall (osm way/470064987, 0m)
update buildings set stories = 2, stories_verified = true  where id = 210;  -- Stony Brook University — Engineering Bldg (osm way/60911992, 105m)
update buildings set stories = 2, stories_verified = true  where id = 234;  -- Lynbrook Gardens (osm way/593522978, 141m)
update buildings set stories = 3, stories_verified = true  where id = 263;  -- Peconic Landing at Southold (osm way/460835108, 83m)
update buildings set stories = 1, stories_verified = true  where id = 384;  -- Parrish Art Museum (osm way/353079604, 12m)
update buildings set stories = 3, stories_verified = true  where id = 594;  -- Sagamore Hill — Roosevelt Home (osm way/450217987, 87m)
-- Sourced estimates: an OSM building polygon at the point has levels/height,
-- but we couldn't match it by name — kept as '· est', never as fact.
update buildings set stories = 18, stories_verified = false where id = 4;  -- Stony Brook University Hospital (osm levels, 59m)
update buildings set stories = 11, stories_verified = false where id = 38;  -- Long Island Jewish Medical Center (osm height 39.7m, 14m)
update buildings set stories = 9, stories_verified = false where id = 39;  -- Cohen Children's Medical Center (osm levels, 9m)
update buildings set stories = 4, stories_verified = false where id = 41;  -- Northport VA Medical Center (osm levels, 4m)
update buildings set stories = 6, stories_verified = false where id = 42;  -- St. Charles Hospital (osm height 20.0m, 96m)
update buildings set stories = 1, stories_verified = false where id = 88;  -- The Menhaden Hotel (osm levels, 83m)
update buildings set stories = 3, stories_verified = false where id = 90;  -- SUNY Old Westbury — Campus Center (osm levels, 46m)
update buildings set stories = 2, stories_verified = false where id = 99;  -- Stony Brook University — Administration (osm levels, 35m)
update buildings set stories = 2, stories_verified = false where id = 174;  -- 990 Stewart Ave (osm levels, 96m)
update buildings set stories = 5, stories_verified = false where id = 182;  -- Bond Schoeneck & King PLLC (osm levels, 72m)
update buildings set stories = 1, stories_verified = false where id = 248;  -- Babylon Public Library (osm levels, 34m)
update buildings set stories = 2, stories_verified = false where id = 257;  -- Long Island Children's Museum (osm levels, 99m)
update buildings set stories = 4, stories_verified = false where id = 601;  -- Temple Beth El Great Neck (osm levels, 127m)

-- 4. Elevator counts were invented; real ones must come from reviews.
update buildings set elevators = null;

-- Sanity check: expect 175 buildings, 0 non-null elevators.
select count(*)                                   as buildings,
       count(*) filter (where stories_verified)   as floors_fact,
       count(stories)                             as floors_any,
       count(elevators)                           as elevators_nonnull
from buildings;

-- OSM names reviewed but NOT adopted (seed name is better):
--   #8 kept 'Long Island Marriott' — OSM "Marriott Long Island" — seed matches official branding
--   #22 kept 'Melville Marriott Long Island' — same
--   #23 kept 'Good Samaritan University Hospital' — OSM stale: "University" added officially in 2021
--   #34 kept 'St. Francis Hospital The Heart Center' — OSM "Saint Francis Hospital" less official
--   #39 kept 'Cohen Children's Medical Center' — OSM has doubled possessive
--   #42 kept 'St. Charles Hospital' — official uses "St."
--   #76 kept 'Gurney's Montauk Resort & Seawater Spa' — OSM stale pre-2013 name
--   #95 kept 'Touro Law Center' — OSM "Touro Law School" not the official name
--   #112 kept 'Hempstead Town Hall' — OSM "Town of Hempstead" is the municipality, not the building
--   #113 kept 'Suffolk County Family Court' — OSM matched the District Court — different court, name kept
--   #130 kept 'MacArthur Airport Parking Garage' — OSM matched the whole airport, not the garage
--   #257 kept 'Long Island Children's Museum' — OSM dropped the possessive
--   #448 kept 'Mineola Village Hall' — OSM "Village of Mineola" is the municipality
--   #511 kept 'New York Community Bancorp HQ' — both names doubtful post-Flagstar rebrand; left as-is
--   #537 kept 'East Hampton Village Green' — OSM "Village of East Hampton" is the municipality
--   #574 kept 'Sag Harbor Village Hall' — OSM "Village of Sag Harbor" is the municipality
