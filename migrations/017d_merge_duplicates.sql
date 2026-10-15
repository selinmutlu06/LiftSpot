-- ============================================================
-- 017d: one pin per real building. A same-address scan found
-- three duplicates (campus halls that share an address, like
-- Adelphi and the Stony Brook dorms, are separate buildings
-- and stay).
--   Northport VA: three rows for one hospital at 79 Middleville
--     Rd (#1017 sat 15 ft from #41). Keep #41, which has the video.
--   Good Samaritan, 1000 Montauk Hwy: keep #23, which has the video.
--   Coney Island Hospital (#2009) is the old name of NYC Health +
--     Hospitals: South Brooklyn Health (#2045), 60 m apart. Keep
--     #2045. Its YouTube search only tried the new name, and most
--     footage would be filed under the old one, so its coverage
--     goes back to "not checked" instead of claiming none exists.
--   (The Ruth Bader Ginsburg Building is the new tower on that
--     campus, a real separate building, and stays.)
-- Run in the Supabase SQL Editor. Safe to re-run.
-- ============================================================
begin;

update reviews          set building_id = 41   where building_id in (1015, 1017);
update reviews          set building_id = 23   where building_id = 1050;
update reviews          set building_id = 2045 where building_id = 2009;
delete from submissions      where building_id in (1015, 1017, 1050, 2009);
delete from elevator_reports where building_id in (1015, 1017, 1050, 2009);
delete from buildings where id in (1015, 1017, 1050, 2009);

update buildings set yt_videos = null, yt_url = null where id = 2045;

commit;

select count(*) as total,
       count(*) filter (where id in (1015, 1017, 1050, 2009)) as dupes_left
from buildings;  -- expect total = 710, dupes_left = 0
