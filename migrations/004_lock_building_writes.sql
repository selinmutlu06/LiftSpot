-- ============================================================
-- 004 — Lock down what the public can write to buildings
-- Run in the Supabase SQL Editor.
--
-- The original schema granted an open UPDATE policy:
--     create policy "Public update buildings" on buildings for update using (true);
-- Combined with Supabase's default table grants, that let ANY anonymous visitor
-- rewrite ANY column of ANY building — including `verified`, `lat`/`lng`, and the
-- floor/elevator counts. For an app whose entire premise is data honesty, an
-- anonymous user being able to flip `verified = true` or move a pin is the whole
-- ballgame.
--
-- The app only ever writes one thing: the recomputed `rating` after a review
-- (see js/drawer.js). So we restrict the public to exactly that — a single
-- column — at the privilege level, which RLS alone cannot do.
-- ============================================================

-- 1) Take back the blanket table-level UPDATE the API role got by default.
revoke update on table buildings from anon, authenticated;

-- 2) Hand back ONLY the rating column. Any attempt to update name, type, town,
--    addr, lat, lng, stories, elevators, or verified now fails with a privilege
--    error — regardless of the RLS policy.
grant update (rating) on table buildings to anon, authenticated;

-- 3) The row-level policy can stay permissive (it gates rows, not columns); the
--    column grant above is what actually constrains the write. Recreate it with a
--    name that reflects reality.
drop policy if exists "Public update buildings" on buildings;
create policy "Public update building rating"
  on buildings for update
  using (true)
  with check (true);

-- Sanity check: confirm rating is the only column anon may update.
select column_name
from information_schema.column_privileges
where grantee = 'anon' and table_name = 'buildings' and privilege_type = 'UPDATE';
