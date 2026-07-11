-- ============================================================
-- 009 — Restore the Foursquare-verified batch deleted by 008
-- Run in the Supabase SQL Editor (after 008). Safe to re-run.
--
-- 008's purge ran against a database still carrying 007's PRE-Foursquare
-- verified flags (141 ids), so it deleted 34 buildings the final audit HAD
-- confirmed (repo migration 007 lists 175). This re-inserts those 34 from
-- the seed data with 007's pin relocations and 008's rules already applied:
-- canonical names, stories NULL unless OSM polygons back them, elevators
-- NULL, verified = true. Their reviews were cascade-deleted and cannot be
-- recovered, so rating starts at 0 ("no reviews yet").
-- ============================================================

insert into buildings (id, name, type, town, addr, lat, lng, stories, elevators, rating, verified, stories_verified) values
(11, 'Tanger Outlets Deer Park', 'Mall', 'Deer Park', '152 The Arches Cir, Deer Park, NY', 40.76494, -73.30413, null, null, 0, true, false),
(48, '333 Earle Ovington Blvd', 'Office', 'Uniondale', '333 Earle Ovington Blvd, Uniondale, NY 11553', 40.72491, -73.593687, null, null, 0, true, false),  -- pin from 007: 333 Earle Ovington Blvd -> 333 Earle Ovington Blvd. (355m)
(50, '900 Stewart Ave', 'Office', 'Garden City', '900 Stewart Ave, Garden City, NY 11530', 40.7337, -73.59849, null, null, 0, true, false),
(52, '175 Broadhollow Rd', 'Office', 'Melville', '175 Broadhollow Rd, Melville, NY 11747', 40.78693, -73.41472, null, null, 0, true, false),
(53, '1010 Northern Blvd', 'Office', 'Great Neck', '1010 Northern Blvd, Great Neck, NY 11021', 40.78492, -73.70744, null, null, 0, true, false),
(55, 'Henry Schein HQ', 'Office', 'Melville', '135 Duryea Rd, Melville, NY 11747', 40.768675, -73.415633, null, null, 0, true, false),  -- pin from 007: Henry Schein HQ -> Henry Schein (332m)
(58, 'Broadridge Financial Solutions HQ', 'Office', 'Lake Success', '5 Dakota Dr, Lake Success, NY 11042', 40.762, -73.69073, null, null, 0, true, false),
(62, '1111 Marcus Ave', 'Office', 'Lake Success', '1111 Marcus Ave, Lake Success, NY 11042', 40.75638, -73.69966, null, null, 0, true, false),
(67, '445 Broadhollow Rd', 'Office', 'Melville', '445 Broadhollow Rd, Melville, NY 11747', 40.77522, -73.41982, null, null, 0, true, false),
(70, '1000 Woodbury Rd', 'Office', 'Woodbury', '1000 Woodbury Rd, Woodbury, NY 11797', 40.80253, -73.47992, null, null, 0, true, false),
(150, '3000 Marcus Ave', 'Office', 'Lake Success', '3000 Marcus Ave, Lake Success, NY 11042', 40.75884, -73.69562, null, null, 0, true, false),
(152, '1000 Franklin Ave', 'Office', 'Garden City', '1000 Franklin Ave, Garden City, NY 11530', 40.729828, -73.63617, null, null, 0, true, false),  -- pin from 007: 1000 Franklin Ave -> 1000 Franklin Ave (400m)
(158, '900 Merchants Concourse', 'Office', 'Westbury', '900 Merchants Concourse, Westbury, NY 11590', 40.74466, -73.59162, null, null, 0, true, false),
(159, '290 Broadhollow Rd', 'Office', 'Melville', '290 Broadhollow Rd, Melville, NY 11747', 40.78374, -73.41876, null, null, 0, true, false),
(167, '100 Motor Pkwy', 'Office', 'Hauppauge', '100 Motor Pkwy, Hauppauge, NY 11788', 40.80719, -73.26808, null, null, 0, true, false),
(168, '534 Broadhollow Rd', 'Office', 'Melville', '534 Broadhollow Rd, Melville, NY 11747', 40.77411, -73.42236, null, null, 0, true, false),
(174, '990 Stewart Ave', 'Office', 'Garden City', '990 Stewart Ave, Garden City, NY 11530', 40.73403, -73.59663, 2, null, 0, true, false),  -- stories est (008): 990 Stewart Ave (osm levels, 96m)
(180, 'Meltzer Lippe Goldstein & Breitstone LLP', 'Legal', 'Mineola', '190 Willis Ave, Mineola, NY 11501', 40.745942, -73.638865, null, null, 0, true, false),  -- pin from 007: Meltzer Lippe Goldstein & Breitstone LLP -> Meltzer, Lippe, Goldstein & Breitstone, LLP (207m)
(182, 'Bond Schoeneck & King PLLC', 'Legal', 'Garden City', '1010 Franklin Ave, Garden City, NY 11530', 40.730202, -73.636313, 5, null, 0, true, false),  -- pin from 007: Bond Schoeneck & King PLLC -> Bond, Schoeneck & King (391m); stories est (008): Bond Schoeneck & King PLLC (osm levels, 72m)
(185, 'Campolo Middleton & McCormick LLP', 'Legal', 'Ronkonkoma', '4175 Veterans Memorial Hwy, Ronkonkoma, NY 11779', 40.78299, -73.09865, null, null, 0, true, false),
(186, 'Hamburger Maxson Yaffe & McNally LLP', 'Legal', 'Melville', '225 Broadhollow Rd, Melville, NY 11747', 40.78539, -73.41547, null, null, 0, true, false),
(187, 'Farrell Fritz PC', 'Legal', 'Uniondale', '400 RXR Plaza, Uniondale, NY 11553', 40.720161, -73.584366, null, null, 0, true, false),  -- pin from 007: Farrell Fritz PC -> Farrell Fritz, PC (708m)
(189, 'Ruskin Moscou Faltischek PC', 'Legal', 'Uniondale', '1425 RXR Plaza, Uniondale, NY 11553', 40.720241, -73.583639, null, null, 0, true, false),  -- pin from 007: Ruskin Moscou Faltischek PC -> Ruskin Moscou Faltischek (697m)
(194, 'Gurney''s Star Island Resort', 'Hotel', 'Montauk', '32 Star Island Rd, Montauk, NY 11954', 41.06906, -71.93233, null, null, 0, true, false),
(295, 'Baron''s Cove Hotel', 'Hotel', 'Sag Harbor', '31 W Water St, Sag Harbor, NY 11963', 41.0012, -72.2999, null, null, 0, true, false),
(331, '700 Old Country Rd', 'Office', 'Plainview', '700 Old Country Rd, Plainview, NY 11803', 40.77323, -73.48757, null, null, 0, true, false),
(385, 'Suffolk County Vanderbilt Museum', 'Entertainment', 'Centerport', '180 Little Neck Rd, Centerport, NY 11721', 40.906475, -73.368774, null, null, 0, true, false),  -- name from 008; pin from 007: Vanderbilt Museum — Hall of Fishes -> Suffolk County Vanderbilt Museum (646m)
(389, 'Patchogue Theatre for the Performing Arts', 'Entertainment', 'Patchogue', '71 E Main St, Patchogue, NY 11772', 40.766025, -73.013459, null, null, 0, true, false),  -- pin from 007: Patchogue Theatre for the Performing Arts -> Patchogue Theatre for the Performing Arts (190m)
(462, '2 Huntington Quadrangle', 'Office', 'Melville', '2 Huntington Quadrangle, Melville, NY 11747', 40.77169, -73.41654, null, null, 0, true, false),
(491, 'Memorial Sloan Kettering Commack', 'Medical', 'Commack', '650 Commack Rd, Commack, NY 11725', 40.80964, -73.29329, null, null, 0, true, false),
(559, '500 Old Country Rd', 'Office', 'Garden City', '500 Old Country Rd, Garden City, NY 11530', 40.74245, -73.61864, null, null, 0, true, false),
(576, 'Nassau County Traffic & Parking Agency', 'Government', 'Hempstead', '16 Cooper St, Hempstead, NY 11550', 40.707528, -73.623225, null, null, 0, true, false),  -- pin from 007: Nassau County Traffic & Parking Agency -> Nassau County Traffic & Parking Violations Agency (483m)
(592, 'Planting Fields — Coe Hall', 'Entertainment', 'Oyster Bay', '1395 Planting Fields Rd, Oyster Bay, NY 11771', 40.864964, -73.55736, null, null, 0, true, false),  -- pin from 007: Planting Fields — Coe Hall -> Coe Hall (Planting Fields Arboretum) (322m)
(615, 'Jericho Terrace Plaza', 'Mall', 'Mineola', '500 Jericho Tpke, Mineola, NY 11501', 40.754393, -73.626078, null, null, 0, true, false)  -- pin from 007: Jericho Terrace Plaza -> Jericho terrace (772m)
on conflict (id) do nothing;

-- Sanity check: expect 175 buildings, 0 non-null elevators.
select count(*)                                 as buildings,
       count(*) filter (where stories_verified) as floors_fact,
       count(stories)                           as floors_any,
       count(elevators)                         as elevators_nonnull
from buildings;
