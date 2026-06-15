-- ============================================================
-- LiftSpot — Specialty Medical Buildings
-- Dermatology, Physical Therapy, Radiology (IDs 621–665)
-- ============================================================

insert into buildings (id, name, type, town, addr, lat, lng, stories, elevators, rating) values
(622, 'Schweiger Dermatology Group Commack',       'Dermatology',      'Commack',          '99 Veterans Memorial Hwy, Commack, NY 11725',    40.8425, -73.2860, 2, 1, 4.2),
(624, 'Island Dermatology Rockville Centre',       'Dermatology',      'Rockville Centre', '2 Lincoln Ave, Rockville Centre, NY 11570',      40.6588, -73.6399, 2, 1, 4.2),
(625, 'Advanced Dermatology Huntington',           'Dermatology',      'Huntington',       '180 E Pulaski Rd, Huntington Station, NY 11746', 40.85132, -73.40027, 2, 1, 4.1),
(626, 'Advanced Dermatology Hicksville',           'Dermatology',      'Hicksville',       '55 Broadway, Hicksville, NY 11801',              40.7682, -73.5251, 2, 1, 4.1),
(627, 'Advanced Dermatology Melville',             'Dermatology',      'Melville',         '535 Broadhollow Rd, Melville, NY 11747',         40.7623, -73.4147, 3, 2, 4.2),
(628, 'North Shore Dermatology Manhasset',         'Dermatology',      'Manhasset',        '1155 Northern Blvd, Manhasset, NY 11030',        40.7872, -73.6928, 2, 1, 4.3),
(632, 'Dermatology of Long Island East Hampton',   'Dermatology',      'East Hampton',     '66 Newtown Ln, East Hampton, NY 11937',          40.9623, -72.1841, 2, 1, 4.4),
(633, 'Northwell Health Dermatology Lake Success', 'Dermatology',      'Lake Success',     '1991 Marcus Ave, Lake Success, NY 11042',        40.7595, -73.7176, 4, 3, 4.2),
(635, 'Stony Brook Dermatology East Setauket',     'Dermatology',      'East Setauket',    '17 Research Way, East Setauket, NY 11733',       40.9211, -73.1104, 3, 2, 4.3),
(638, 'Northwell Health PT Huntington',            'Physical Therapy', 'Huntington',       '181 E Main St, Huntington, NY 11743',            40.88013, -73.40007, 2, 1, 4.3),
(649, 'Summit Physical Therapy Bay Shore',         'Physical Therapy', 'Bay Shore',        '1 East Main St, Bay Shore, NY 11706',            40.7280, -73.2510, 2, 1, 4.0),
(654, 'Zwanger-Pesiri Radiology Commack',          'Radiology',        'Commack',          '5 Vanderbilt Motor Pkwy, Commack, NY 11725',     40.8432, -73.2825, 2, 1, 4.2),
(663, 'Peconic Bay Radiology Riverhead',           'Radiology',        'Riverhead',        '1300 Roanoke Ave, Riverhead, NY 11901',          40.9343, -72.67392, 3, 2, 4.0)

on conflict (id) do nothing;
