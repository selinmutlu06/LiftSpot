-- ============================================================
-- 002 — Mark which buildings are real
-- Run in the Supabase SQL Editor (after 001).
--
-- An OpenStreetMap audit (scripts/verify_buildings.py) checked all 559
-- seed buildings. Only the 108 below could be confirmed as a real feature
-- of the stated type at roughly the stated location. The rest could not be
-- verified — many are fabricated, some are real buildings the geocoder
-- simply couldn't match by name. Nothing is deleted; everything unverified
-- is just flagged so the UI stops presenting its specs as fact.
--
-- `verified` means "this building exists where we say it does." It does NOT
-- certify floor or elevator counts — those stay community estimates until a
-- real visit confirms them.
-- ============================================================

alter table buildings add column if not exists verified boolean not null default false;

-- Reset, then mark the 108 OSM-confirmed buildings as verified.
update buildings set verified = false;
update buildings set verified = true where id in (
  3, 4, 8, 10, 13, 14, 15, 18, 19, 20, 21, 22, 28, 33, 35,
  42, 43, 46, 51, 53, 62, 63, 67, 70, 72, 74, 77, 88, 101, 102,
  109, 112, 124, 127, 131, 141, 149, 150, 151, 154, 155, 159, 162, 166, 167,
  168, 169, 171, 172, 177, 178, 197, 203, 207, 208, 219, 220, 224, 234, 244,
  253, 255, 256, 264, 269, 302, 313, 314, 317, 321, 325, 329, 330, 335, 361,
  362, 384, 432, 436, 437, 439, 442, 447, 448, 450, 452, 454, 455, 456, 460,
  462, 542, 561, 570, 571, 572, 573, 574, 575, 581, 584, 587, 590, 591, 592,
  599, 601, 602
);

-- Sanity check.
select
  count(*) filter (where verified)     as verified,
  count(*) filter (where not verified) as unverified,
  count(*)                             as total
from buildings;
