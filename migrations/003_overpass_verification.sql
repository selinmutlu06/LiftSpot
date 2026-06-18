-- ============================================================
-- 003 — Re-verify against OpenStreetMap via Overpass
-- Run in the Supabase SQL Editor (after 001 and 002).
--
-- The original audit (002) could only reach Nominatim *name search*, which
-- left 360 real-or-fake buildings unverifiable for the wrong reason. Overpass
-- (true spatial lookup near each pin) is reachable now, so this re-audits every
-- building by asking 'is there a real feature of this type at this spot?'.
-- See scripts/verify_overpass.py and scripts/build_migration_003.py.
--
-- Result: 202 buildings verified (was 108), 39 pins
-- relocated to their real OSM position, 2 story counts corrected.
-- Precision-first: anything uncertain stays unverified (see scripts/overpass_review.csv).
-- `verified` still means existence + location only — never elevator counts.
-- ============================================================

-- 1) Reset and set the verified flag from the Overpass audit.
update buildings set verified = false;
update buildings set verified = true where id in (
  3, 4, 5, 6, 7, 8, 9, 11, 13, 14, 15, 16, 18, 19, 20,
  21, 22, 23, 24, 25, 28, 31, 32, 33, 34, 35, 36, 38, 39, 42,
  43, 44, 46, 47, 51, 53, 55, 59, 60, 61, 63, 64, 67, 70, 71,
  74, 75, 76, 77, 88, 90, 92, 95, 96, 97, 99, 100, 101, 102, 103,
  105, 109, 112, 114, 115, 116, 120, 122, 123, 124, 127, 128, 131, 141, 142,
  150, 152, 154, 156, 159, 160, 162, 164, 166, 167, 168, 171, 172, 193, 196,
  197, 203, 207, 208, 209, 210, 211, 212, 214, 216, 218, 219, 220, 224, 231,
  232, 233, 234, 237, 242, 244, 247, 249, 250, 251, 253, 254, 256, 258, 259,
  262, 264, 273, 275, 276, 277, 278, 279, 280, 283, 295, 302, 309, 313, 316,
  317, 318, 319, 320, 324, 327, 328, 329, 330, 331, 334, 338, 360, 364, 371,
  372, 374, 375, 377, 388, 396, 404, 428, 432, 436, 437, 438, 439, 442, 448,
  456, 461, 462, 463, 467, 468, 473, 482, 483, 487, 488, 489, 496, 512, 534,
  536, 541, 542, 557, 561, 563, 566, 574, 575, 581, 583, 584, 585, 587, 590,
  592, 593, 594, 599, 612, 614, 663
);

-- 2) Relocate pins whose seed coordinate was wrong, to the real OSM feature.
--    Each move is a trustworthy name match; the comment shows the jump + target.
update buildings set lat = 40.738048, lng = -73.612665 where id = 3;  -- Roosevelt Field Mall -> Roosevelt Field Mall (338m)
update buildings set lat = 40.727467, lng = -73.554106 where id = 7;  -- Nassau University Medical Center -> Nassau University Medical Center (801m)
update buildings set lat = 40.723593, lng = -73.587656 where id = 8;  -- Long Island Marriott -> Long Island Marriott (241m)
update buildings set lat = 40.775087, lng = -73.700525 where id = 13;  -- North Shore University Hospital -> North Shore University Hospital (328m)
update buildings set lat = 40.66241, lng = -73.719502 where id = 15;  -- Green Acres Mall -> Green Acres Mall (213m)
update buildings set lat = 40.763844, lng = -73.42508 where id = 21;  -- Hilton Long Island / Huntington -> Hilton Long Island/Huntington (365m)
update buildings set lat = 40.865058, lng = -73.130287 where id = 25;  -- Smith Haven Mall -> Smith Haven Mall (821m)
update buildings set lat = 41.110428, lng = -72.361332 where id = 31;  -- Eastern Long Island Hospital -> Stony Brook Eastern Long Island Hospital (806m)
update buildings set lat = 40.88505, lng = -72.380739 where id = 32;  -- Stony Brook Southampton Hospital -> Stony Brook Southampton Hospital (545m)
update buildings set lat = 40.755667, lng = -73.707712 where id = 38;  -- Long Island Jewish Medical Center -> Long Island Jewish Medical Center (176m)
update buildings set lat = 40.774571, lng = -73.408304 where id = 61;  -- Newsday Building -> Newsday (774m)
update buildings set lat = 40.5843, lng = -73.666412 where id = 75;  -- The Allegria Hotel -> Allegria Hotel (544m)
update buildings set lat = 41.015123, lng = -71.993171 where id = 76;  -- Gurney's Montauk Resort & Seawater Spa -> Gurney's Inn Resort and Spa (207m)
update buildings set lat = 41.101577, lng = -72.362572 where id = 88;  -- The Menhaden Hotel -> The Menhaden (291m)
update buildings set lat = 40.729597, lng = -73.596746 where id = 92;  -- Nassau Community College — Library -> M Nassau Hall (601m)
update buildings set lat = 40.707379, lng = -73.623207 where id = 109;  -- Nassau County District Court -> Nassau County District Court (403m)
update buildings set lat = 40.655849, lng = -73.638204 where id = 120;  -- The Sutton at Rockville Centre -> Sutton House (858m)
update buildings set lat = 40.938232, lng = -72.300259 where id = 196;  -- Topping Rose House -> Topping Rose House (888m)
update buildings set lat = 41.001173, lng = -72.295107 where id = 207;  -- American Hotel Sag Harbor -> American Hotel (255m)
update buildings set lat = 41.07044, lng = -71.933123 where id = 208;  -- Montauk Yacht Club -> Montauk Yacht Club (161m)
update buildings set lat = 40.912961, lng = -73.122085 where id = 216;  -- Stony Brook University — Javits Lecture Ctr -> Jacob K. Javits Lecture Center (207m)
update buildings set lat = 40.658762, lng = -73.673689 where id = 234;  -- Lynbrook Gardens -> Lynbrook Gardens (296m)
update buildings set lat = 40.808087, lng = -73.107138 where id = 249;  -- Ronkonkoma LIRR Station & Garage -> Ronkonkoma LIRR Station (361m)
update buildings set lat = 40.739853, lng = -73.641838 where id = 250;  -- Mineola LIRR Intermodal Center -> Mineola Intermodal Center (729m)
update buildings set lat = 40.773331, lng = -73.531651 where id = 251;  -- Broadway Commons -> Broadway Mall (264m)
update buildings set lat = 40.817279, lng = -73.597472 where id = 254;  -- Tilles Center for the Performing Arts -> Tilles Center For The Performing Arts (849m)
update buildings set lat = 40.885232, lng = -72.503064 where id = 309;  -- Canoe Place Inn -> Canoe Place (839m)
update buildings set lat = 40.76077, lng = -73.690468 where id = 328;  -- 4 Dakota Dr -> 3 Dakota Driv (216m)
update buildings set lat = 40.915748, lng = -73.125073 where id = 372;  -- Stony Brook University — Harriman Hall -> Harriman Hall (211m)
update buildings set lat = 40.758148, lng = -73.587467 where id = 388;  -- The Space at Westbury -> The Space at Westbury (528m)
update buildings set lat = 40.779463, lng = -73.467309 where id = 404;  -- JCC Mid-Island -> Mid-Island Y JCC (620m)
update buildings set lat = 40.713449, lng = -73.257745 where id = 438;  -- Bay Shore–Brightwaters Library -> Bay Shore - Brightwaters Public Library (353m)
update buildings set lat = 40.765563, lng = -73.013662 where id = 439;  -- Patchogue–Medford Library -> Patchogue - Medford Library (183m)
update buildings set lat = 40.761364, lng = -73.499121 where id = 512;  -- Bethpage Federal Credit Union HQ -> Bethpage Federal Credit Union (300m)
update buildings set lat = 40.958901, lng = -72.190355 where id = 541;  -- The 1770 House -> 1770 House Restaurant & Inn (613m)
update buildings set lat = 41.101677, lng = -72.364409 where id = 542;  -- Greenporter Hotel -> The Greenporter Hotel (314m)
update buildings set lat = 40.792687, lng = -73.639995 where id = 585;  -- Roslyn High School -> Roslyn High School (868m)
update buildings set lat = 40.862577, lng = -73.557906 where id = 592;  -- Planting Fields — Coe Hall -> Planting Fields Arboretum (406m)
update buildings set lat = 40.773694, lng = -73.595965 where id = 593;  -- Old Westbury Gardens — Westbury House -> Old Westbury Gardens (923m)

-- 3) Correct story counts from OSM building:levels (name-matched buildings only).
update buildings set stories = 2 where id = 51;  -- 585 Stewart Ave: 6 -> 2
update buildings set stories = 6 where id = 102;  -- Nassau County Courthouse: 7 -> 6

-- Sanity check.
select count(*) filter (where verified) as verified,
       count(*) filter (where not verified) as unverified,
       count(*) as total
from buildings;
