-- ============================================================
-- 006 — Reset verified to the corrected 106-building set
-- Run in the Supabase SQL Editor. Safe to re-run.
--
-- Use THIS file (not an old 002/003 tab) — it is the source of truth
-- for which buildings are OSM name-verified. Supersedes the verified
-- flag set by 002 (108) and the first 003 (202).
-- ============================================================
update buildings set verified = false;
update buildings set verified = true where id in (
  3, 4, 6, 7, 8, 13, 14, 15, 16, 20, 21, 22, 23, 25, 28,
  31, 32, 33, 34, 35, 38, 39, 42, 43, 46, 59, 61, 63, 74, 75,
  76, 77, 88, 90, 95, 96, 97, 99, 100, 101, 109, 112, 120, 124, 127,
  128, 131, 141, 150, 196, 197, 203, 207, 208, 209, 210, 212, 214, 216, 218,
  219, 220, 224, 234, 244, 247, 249, 250, 251, 253, 254, 256, 262, 302, 309,
  319, 328, 360, 372, 375, 377, 388, 404, 432, 436, 437, 438, 439, 442, 448,
  512, 541, 542, 574, 575, 581, 583, 584, 585, 587, 590, 592, 593, 594, 599,
  663
);

select count(*) filter (where verified) as verified,
       count(*) filter (where not verified) as unverified,
       count(*) as total
from buildings;
