-- ============================================================
-- 017b: the tallest towers OSM tagged as offices are apartments.
-- These head the default "tallest first" list, so they matter.
-- Queens Plaza Park, The Brooklyner, The Paxton: rental towers.
-- Oro Condominium, One Clinton: condos (One Clinton has the
-- Brooklyn Heights library on its ground floor).
-- Run in the Supabase SQL Editor. Safe to re-run.
-- ============================================================
update buildings set type = 'Residential' where id in (2403, 2219, 2081, 2223, 2396);

select id, name, type from buildings where id in (2403, 2219, 2081, 2223, 2396) order by id;
