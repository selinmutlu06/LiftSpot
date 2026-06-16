-- ============================================================
-- 001 — Stop faking ratings
-- Run in the Supabase SQL Editor.
--
-- The seed files baked a made-up `rating` (e.g. 4.0) into every
-- building, so buildings with zero reviews still displayed a score.
-- This recomputes every rating from REAL reviews only:
--   • buildings with reviews  -> average of their review stars
--   • buildings with none     -> 0  (UI shows "No reviews yet")
-- ============================================================

update buildings b
set rating = coalesce((
  select round(avg(r.stars)::numeric, 1)
  from reviews r
  where r.building_id = b.id
), 0);

-- Sanity check: how many buildings are now genuinely rated vs unrated.
select
  count(*) filter (where rating > 0) as rated,
  count(*) filter (where rating = 0) as unrated,
  count(*)                           as total
from buildings;
