-- ============================================================
-- 007 — Multi-source verification (OSM + Wikidata + Census + Yelp)
-- Run in the Supabase SQL Editor. Safe to re-run. Supersedes 006.
--
-- 175 buildings confirmed BY NAME by an authoritative source
--   OSM: 137   Wikidata: 5   Yelp: 0   Foursquare: 33
-- 71 pins relocated to the matched feature; 5 floor counts from OSM.
-- Precision-first: address-only matches do NOT verify (see scripts/sources_evidence.csv).
-- ============================================================

update buildings set verified = false;
update buildings set verified = true where id in (
  3, 4, 6, 8, 9, 11, 13, 14, 15, 16, 17, 20, 21, 22, 23,
  25, 26, 28, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 41, 42,
  43, 44, 46, 48, 50, 51, 52, 53, 55, 58, 59, 62, 63, 67, 70,
  74, 75, 76, 77, 78, 88, 90, 91, 95, 96, 97, 98, 99, 100, 101,
  102, 109, 112, 113, 124, 125, 127, 128, 129, 130, 131, 141, 150, 151, 152,
  158, 159, 167, 168, 169, 174, 177, 180, 182, 185, 186, 187, 189, 194, 196,
  197, 203, 207, 208, 209, 210, 211, 212, 214, 218, 219, 220, 224, 225, 228,
  234, 244, 247, 248, 251, 253, 254, 255, 256, 257, 259, 262, 263, 264, 269,
  295, 302, 305, 331, 360, 362, 372, 375, 377, 383, 384, 385, 389, 392, 404,
  409, 432, 436, 437, 438, 439, 442, 443, 444, 447, 448, 452, 455, 457, 462,
  483, 491, 511, 512, 537, 541, 542, 559, 561, 574, 575, 576, 581, 583, 584,
  587, 590, 591, 592, 594, 597, 599, 601, 602, 615
);

-- Relocate pins to the confirmed feature.
update buildings set lat = 40.738048, lng = -73.612665 where id = 3;  -- Roosevelt Field Mall -> Roosevelt Field Mall (338m)
update buildings set lat = 40.72404, lng = -73.588089 where id = 8;  -- Long Island Marriott -> Marriott Long Island (215m)
update buildings set lat = 40.66241, lng = -73.719502 where id = 15;  -- Green Acres Mall -> Green Acres Mall (213m)
update buildings set lat = 40.786142, lng = -73.546265 where id = 17;  -- 1 Jericho Plaza -> 1 Jericho Plaza (849m)
update buildings set lat = 40.763844, lng = -73.42508 where id = 21;  -- Hilton Long Island / Huntington -> Hilton Long Island/Huntington (365m)
update buildings set lat = 40.865058, lng = -73.130287 where id = 25;  -- Smith Haven Mall -> Smith Haven Mall (821m)
update buildings set lat = 40.725833, lng = -73.240833 where id = 29;  -- South Shore University Hospital -> South Shore University Hospital (943m)
update buildings set lat = 41.109956, lng = -72.360119 where id = 31;  -- Eastern Long Island Hospital -> Eastern Long Island Hospital Heliport (735m)
update buildings set lat = 40.88505, lng = -72.380739 where id = 32;  -- Stony Brook Southampton Hospital -> Stony Brook Southampton Hospital (545m)
update buildings set lat = 40.774941, lng = -73.478834 where id = 36;  -- Plainview Hospital -> Plainview Hospital (952m)
update buildings set lat = 40.810972, lng = -73.508088 where id = 37;  -- Syosset Hospital -> Syosset Hospital (632m)
update buildings set lat = 40.755667, lng = -73.707712 where id = 38;  -- Long Island Jewish Medical Center -> Long Island Jewish Medical Center (176m)
update buildings set lat = 40.893707, lng = -73.308785 where id = 41;  -- Northport VA Medical Center -> Northport VA Medical Center (556m)
update buildings set lat = 40.6853, lng = -73.4258 where id = 44;  -- South Oaks Hospital -> South Oaks Hospital (259m)
update buildings set lat = 40.72491, lng = -73.593687 where id = 48;  -- 333 Earle Ovington Blvd -> 333 Earle Ovington Blvd. (355m)
update buildings set lat = 40.768675, lng = -73.415633 where id = 55;  -- Henry Schein HQ -> Henry Schein (332m)
update buildings set lat = 40.5843, lng = -73.666412 where id = 75;  -- The Allegria Hotel -> Allegria Hotel (544m)
update buildings set lat = 41.015123, lng = -71.993171 where id = 76;  -- Gurney's Montauk Resort & Seawater Spa -> Gurney's Inn Resort and Spa (207m)
update buildings set lat = 40.808343, lng = -73.657415 where id = 78;  -- Hilton Garden Inn Roslyn -> Hilton Garden Inn - Roslyn (1135m)
update buildings set lat = 41.101577, lng = -72.362572 where id = 88;  -- The Menhaden Hotel -> The Menhaden (291m)
update buildings set lat = 40.75301, lng = -73.428617 where id = 91;  -- Farmingdale State College — Gleeson Hall -> Gleeson Hall (382m)
update buildings set lat = 40.91645, lng = -73.118244 where id = 98;  -- Stony Brook University — Wang Center -> Wang Center (547m)
update buildings set lat = 40.7388, lng = -73.634356 where id = 102;  -- Nassau County Courthouse -> Nassau County Courthouse (349m)
update buildings set lat = 40.707379, lng = -73.623207 where id = 109;  -- Nassau County District Court -> Nassau County District Court (403m)
update buildings set lat = 40.831941, lng = -73.696833 where id = 125;  -- Port Washington Public Library -> Port Washington Public Library (603m)
update buildings set lat = 40.795948, lng = -73.100303 where id = 129;  -- Long Island MacArthur Airport Terminal -> Long Island MacArthur Airport (185m)
update buildings set lat = 40.729828, lng = -73.63617 where id = 152;  -- 1000 Franklin Ave -> 1000 Franklin Ave (400m)
update buildings set lat = 40.745942, lng = -73.638865 where id = 180;  -- Meltzer Lippe Goldstein & Breitstone LLP -> Meltzer, Lippe, Goldstein & Breitstone, LLP (207m)
update buildings set lat = 40.730202, lng = -73.636313 where id = 182;  -- Bond Schoeneck & King PLLC -> Bond, Schoeneck & King (391m)
update buildings set lat = 40.720161, lng = -73.584366 where id = 187;  -- Farrell Fritz PC -> Farrell Fritz, PC (708m)
update buildings set lat = 40.720241, lng = -73.583639 where id = 189;  -- Ruskin Moscou Faltischek PC -> Ruskin Moscou Faltischek (697m)
update buildings set lat = 40.938232, lng = -72.300259 where id = 196;  -- Topping Rose House -> Topping Rose House (888m)
update buildings set lat = 41.001173, lng = -72.295107 where id = 207;  -- American Hotel Sag Harbor -> American Hotel (255m)
update buildings set lat = 41.07044, lng = -71.933123 where id = 208;  -- Montauk Yacht Club -> Montauk Yacht Club (161m)
update buildings set lat = 40.86236, lng = -73.468226 where id = 209;  -- Cold Spring Harbor Laboratory -> Cold Spring Harbor Laboratory (518m)
update buildings set lat = 40.911374, lng = -73.120758 where id = 211;  -- Stony Brook University — Life Sciences Bldg -> Life Sciences (396m)
update buildings set lat = 40.887364, lng = -72.385285 where id = 225;  -- Southampton Town Hall -> Southampton Town Hall (607m)
update buildings set lat = 40.7381, lng = -73.639296 where id = 228;  -- Theodore Roosevelt Exec & Legislative Bldg -> Theodore Roosevelt (774m)
update buildings set lat = 40.658762, lng = -73.673689 where id = 234;  -- Lynbrook Gardens -> Lynbrook Gardens (296m)
update buildings set lat = 40.695004, lng = -73.325992 where id = 248;  -- Babylon Public Library -> Babylon Public Library (846m)
update buildings set lat = 40.773331, lng = -73.531651 where id = 251;  -- Broadway Commons -> Broadway Mall (264m)
update buildings set lat = 40.817279, lng = -73.597472 where id = 254;  -- Tilles Center for the Performing Arts -> Tilles Center For The Performing Arts (849m)
update buildings set lat = 40.917919, lng = -72.656195 where id = 255;  -- Long Island Aquarium -> Long Island Aquarium and Exhibition Center (358m)
update buildings set lat = 40.72795, lng = -73.600355 where id = 257;  -- Long Island Children's Museum -> Long Island Children Museum (971m)
update buildings set lat = 40.917344, lng = -73.124727 where id = 259;  -- Stony Brook University Sports Complex -> Sports Complex (671m)
update buildings set lat = 41.068137, lng = -72.417179 where id = 305;  -- North Fork Table & Inn -> North Fork Table & Inn (1126m)
update buildings set lat = 40.918873, lng = -72.663984 where id = 362;  -- Riverhead Town Hall -> Riverhead Town Hall (286m)
update buildings set lat = 40.915748, lng = -73.125073 where id = 372;  -- Stony Brook University — Harriman Hall -> Harriman Hall (211m)
update buildings set lat = 40.728347, lng = -73.597478 where id = 383;  -- Cradle of Aviation Museum -> Cradle of Aviation Museum (786m)
update buildings set lat = 40.906475, lng = -73.368774 where id = 385;  -- Vanderbilt Museum — Hall of Fishes -> Suffolk County Vanderbilt Museum (646m)
update buildings set lat = 40.766025, lng = -73.013459 where id = 389;  -- Patchogue Theatre for the Performing Arts -> Patchogue Theatre for the Performing Arts (190m)
update buildings set lat = 40.874378, lng = -73.416159 where id = 392;  -- Huntington YMCA -> Huntington YMCA (1075m)
update buildings set lat = 40.779463, lng = -73.467309 where id = 404;  -- JCC Mid-Island -> Mid-Island Y JCC (620m)
update buildings set lat = 40.810509, lng = -73.640072 where id = 409;  -- Nassau County Museum of Art -> Nassau County Museum of Art (1092m)
update buildings set lat = 40.713449, lng = -73.257745 where id = 438;  -- Bay Shore–Brightwaters Library -> Bay Shore - Brightwaters Public Library (353m)
update buildings set lat = 40.765563, lng = -73.013662 where id = 439;  -- Patchogue–Medford Library -> Patchogue - Medford Library (183m)
update buildings set lat = 40.724722, lng = -73.322222 where id = 443;  -- North Babylon Public Library -> North Babylon Public Library (693m)
update buildings set lat = 40.707255, lng = -73.704603 where id = 444;  -- Elmont Public Library -> Elmont Public Library (1013m)
update buildings set lat = 40.657612, lng = -73.675287 where id = 447;  -- Lynbrook Village Hall -> Lynbrook Village Hall (408m)
update buildings set lat = 40.678722, lng = -73.418295 where id = 452;  -- Amityville Village Hall -> Amityville Village Hall (236m)
update buildings set lat = 40.731112, lng = -73.445143 where id = 455;  -- Farmingdale Village Hall -> Farmingdale Village Hall (164m)
update buildings set lat = 40.733089, lng = -73.680528 where id = 457;  -- New Hyde Park Village Hall -> New Hyde Park Village Hall (735m)
update buildings set lat = 40.766451, lng = -73.52842 where id = 511;  -- New York Community Bancorp HQ -> New York Community Bank Plaza (447m)
update buildings set lat = 40.761364, lng = -73.499121 where id = 512;  -- Bethpage Federal Credit Union HQ -> Bethpage Federal Credit Union (300m)
update buildings set lat = 40.958901, lng = -72.190355 where id = 541;  -- The 1770 House -> 1770 House Restaurant & Inn (613m)
update buildings set lat = 41.101677, lng = -72.364409 where id = 542;  -- Greenporter Hotel -> The Greenporter Hotel (314m)
update buildings set lat = 40.793418, lng = -73.538094 where id = 561;  -- 350 Jericho Tpke -> 350 Jericho Turnpike (283m)
update buildings set lat = 40.707528, lng = -73.623225 where id = 576;  -- Nassau County Traffic & Parking Agency -> Nassau County Traffic & Parking Violations Agency (483m)
update buildings set lat = 40.864964, lng = -73.55736 where id = 592;  -- Planting Fields — Coe Hall -> Coe Hall (Planting Fields Arboretum) (322m)
update buildings set lat = 40.798043, lng = -73.735599 where id = 601;  -- Temple Beth El Great Neck -> Temple Beth-El of Great Neck (242m)
update buildings set lat = 40.754393, lng = -73.626078 where id = 615;  -- Jericho Terrace Plaza -> Jericho terrace (772m)

-- Floor counts confirmed by OSM building:levels.
alter table buildings add column if not exists stories_verified boolean not null default false;
update buildings set stories_verified = false;
update buildings set stories = 2, stories_verified = true where id = 51;  -- 585 Stewart Ave: 6 -> 2
update buildings set stories = 3, stories_verified = true where id = 90;  -- SUNY Old Westbury — Campus Center: 5 -> 3
update buildings set stories = 3, stories_verified = true where id = 91;  -- Farmingdale State College — Gleeson Hall: 4 -> 3
update buildings set stories = 3, stories_verified = true where id = 263;  -- Peconic Landing at Southold: 4 -> 3
update buildings set stories = 1, stories_verified = true where id = 384;  -- Parrish Art Museum: 3 -> 1

select count(*) filter (where verified) as verified,
       count(*) filter (where not verified) as unverified,
       count(*) as total
from buildings;
