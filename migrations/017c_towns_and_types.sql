-- ============================================================
-- 017c: Long Island towns checked against the US Census, plus
-- building types that contradicted the building's own name.
--
-- Towns: every Long Island pin was looked up in the Census
-- geocoder (incorporated places, CDPs, county subdivisions).
-- 258 of 268 already matched the Census place or the postal
-- town in the address. These are the ones that didn't.
-- Types: OSM "commercial" footprints were imported as Office,
-- so some hotels, stations and condos landed there.
-- Run in the Supabase SQL Editor. Safe to re-run.
-- ============================================================
begin;

-- Towns (Census place in parentheses where it differs)
update buildings set town = 'Bay Shore'      where id = 1013;  -- North District Lofts (Bay Shore CDP)
update buildings set town = 'New Hyde Park'  where id = 483;   -- Lake Success Shopping Center (North New Hyde Park CDP, postal New Hyde Park)
update buildings set town = 'Old Westbury'   where id = 1073;  -- Wisser Memorial Library, NYIT
update buildings set town = 'Glen Cove'      where id = 1084;  -- Harbor Landing at Garvies Point
update buildings set town = 'Stony Brook'    where id in (1076, 1077);  -- Health Sciences Center, Basic Sciences Tower (Stony Brook University CDP)
update buildings set town = 'North Bellport' where id = 1093;  -- Hagerman Burn Building
update buildings set town = 'Brightwaters'   where id = 438;   -- Bay Shore-Brightwaters Public Library

-- Types
update buildings set type = 'Hotel'       where id = 2425;                    -- Marriott Courtyard
update buildings set type = 'Transit'     where id in (2109, 2383, 2375);     -- Coney Island-Stillwell Avenue, LaGuardia Terminal B + its garage
update buildings set type = 'Residential' where id in (2031, 2091, 2066, 2067, 2064, 2084, 2228);  -- Gotham Point South, Fairfield Manor Apts, Park Lane Condo, North Shore Towers, Crown Condos, Sunset Park Loft Condo, J Condos
update buildings set type = 'Medical'     where id in (2427, 1017);           -- "Medical Center" Brighton Beach, Northport VA Bldg 200
update buildings set type = 'Library'     where id in (9, 26, 97, 1073);      -- campus libraries, so the Library filter finds them

-- Typo
update buildings set name = '595 Stewart Avenue' where id = 1065;

commit;

select id, name, type, town from buildings
where id in (1013, 483, 1073, 1084, 1076, 1077, 1093, 438, 2425, 2109, 2383, 2375, 2031, 2091, 2066, 2067, 2064, 2084, 2228, 2427, 1017, 9, 26, 97, 1065)
order by id;
