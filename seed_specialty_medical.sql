-- ============================================================
-- LiftSpot — Specialty Medical Buildings
-- Dermatology, Physical Therapy, Radiology (IDs 621–665)
-- ============================================================

insert into buildings (id, name, type, town, addr, lat, lng, stories, elevators, rating) values

-- ── DERMATOLOGY ───────────────────────────────────────────────
(621, 'Schweiger Dermatology Group Garden City',   'Dermatology', 'Garden City',      '1000 Franklin Ave, Garden City, NY 11530',              40.7260, -73.6355,  2,  1, 4.3),
(622, 'Schweiger Dermatology Group Commack',       'Dermatology', 'Commack',          '99 Veterans Memorial Hwy, Commack, NY 11725',           40.8425, -73.2860,  2,  1, 4.2),
(623, 'Schweiger Dermatology Group Great Neck',    'Dermatology', 'Great Neck',       '600 Northern Blvd, Great Neck, NY 11021',               40.7920, -73.7280,  3,  2, 4.3),
(624, 'Island Dermatology Rockville Centre',       'Dermatology', 'Rockville Centre', '2 Lincoln Ave, Rockville Centre, NY 11570',             40.6588, -73.6399,  2,  1, 4.2),
(625, 'Advanced Dermatology Huntington',           'Dermatology', 'Huntington',       '180 E Pulaski Rd, Huntington Station, NY 11746',        40.8322, -73.4162,  2,  1, 4.1),
(626, 'Advanced Dermatology Hicksville',           'Dermatology', 'Hicksville',       '55 Broadway, Hicksville, NY 11801',                     40.7682, -73.5251,  2,  1, 4.1),
(627, 'Advanced Dermatology Melville',             'Dermatology', 'Melville',         '535 Broadhollow Rd, Melville, NY 11747',                40.7623, -73.4147,  3,  2, 4.2),
(628, 'North Shore Dermatology Manhasset',         'Dermatology', 'Manhasset',        '1155 Northern Blvd, Manhasset, NY 11030',               40.7872, -73.6928,  2,  1, 4.3),
(629, 'Dermatology Associates of Long Island',     'Dermatology', 'Hauppauge',        '150 Motor Pkwy, Hauppauge, NY 11788',                   40.8188, -73.2093,  2,  1, 4.2),
(630, 'South Shore Skin Center Patchogue',         'Dermatology', 'Patchogue',        '285 Sills Rd, Patchogue, NY 11772',                     40.7740, -72.9988,  1,  0, 4.0),
(631, 'Bellmore Dermatology',                      'Dermatology', 'Bellmore',         '2600 Merrick Rd, Bellmore, NY 11710',                   40.6611, -73.5330,  1,  0, 4.0),
(632, 'Dermatology of Long Island East Hampton',   'Dermatology', 'East Hampton',     '66 Newtown Ln, East Hampton, NY 11937',                 40.9623, -72.1841,  2,  1, 4.4),
(633, 'Northwell Health Dermatology Lake Success', 'Dermatology', 'Lake Success',     '1991 Marcus Ave, Lake Success, NY 11042',               40.7595, -73.7176,  4,  3, 4.2),
(634, 'Great Neck Dermatology',                    'Dermatology', 'Great Neck',       '1010 Northern Blvd, Great Neck, NY 11021',              40.7889, -73.7271,  2,  1, 4.1),
(635, 'Stony Brook Dermatology East Setauket',     'Dermatology', 'East Setauket',    '17 Research Way, East Setauket, NY 11733',              40.9211, -73.1104,  3,  2, 4.3),

-- ── PHYSICAL THERAPY ─────────────────────────────────────────
(636, 'ProClinix Sports Physical Therapy Armonk',  'Physical Therapy', 'Uniondale',   '333 Hempstead Tpke, Uniondale, NY 11553',               40.7089, -73.5985,  1,  0, 4.3),
(637, 'Fyzical Therapy Garden City',               'Physical Therapy', 'Garden City', '600 Old Country Rd, Garden City, NY 11530',             40.7231, -73.6368,  4,  3, 4.2),
(638, 'Northwell Health PT Huntington',            'Physical Therapy', 'Huntington',  '181 E Main St, Huntington, NY 11743',                   40.8691, -73.4258,  2,  1, 4.3),
(639, 'Stony Brook Physical Therapy Commack',      'Physical Therapy', 'Commack',     '480 Commack Rd, Commack, NY 11725',                     40.8392, -73.2809,  2,  1, 4.1),
(640, 'Performance Physical Therapy Hauppauge',    'Physical Therapy', 'Hauppauge',   '1600 Motor Pkwy, Hauppauge, NY 11788',                  40.7817, -73.2184,  2,  1, 4.2),
(641, 'BenchMark Physical Therapy Massapequa',     'Physical Therapy', 'Massapequa',  '5301 Merrick Rd, Massapequa, NY 11758',                 40.6726, -73.4640,  1,  0, 4.1),
(642, 'Excel Physical Therapy Great Neck',         'Physical Therapy', 'Great Neck',  '1010 Northern Blvd, Great Neck, NY 11021',              40.7889, -73.7271,  2,  1, 4.2),
(643, 'Island Sports Physical Therapy Smithtown',  'Physical Therapy', 'Smithtown',   '778 Smithtown Bypass, Smithtown, NY 11787',             40.8604, -73.2171,  1,  0, 4.1),
(644, 'Northwell PT Manhasset',                    'Physical Therapy', 'Manhasset',   '430 Community Dr, Manhasset, NY 11030',                 40.7730, -73.7025,  4,  3, 4.3),
(645, 'ProClinix Pleasantville — Mineola',         'Physical Therapy', 'Mineola',     '200 Old Country Rd, Mineola, NY 11501',                 40.7462, -73.6416,  3,  2, 4.2),
(646, 'Rehab 2 Perform Melville',                  'Physical Therapy', 'Melville',    '301 Route 110, Melville, NY 11747',                     40.7765, -73.4075,  2,  1, 4.1),
(647, 'Island Physical Therapy Riverhead',         'Physical Therapy', 'Riverhead',   '740 E Main St, Riverhead, NY 11901',                    40.9175, -72.6529,  1,  0, 4.0),
(648, 'Advanced Physical Therapy Babylon',         'Physical Therapy', 'Babylon',     '34 Oak St, Babylon, NY 11702',                          40.7012, -73.3241,  2,  1, 4.1),
(649, 'Summit Physical Therapy Bay Shore',         'Physical Therapy', 'Bay Shore',   '1 East Main St, Bay Shore, NY 11706',                   40.7280, -73.2510,  2,  1, 4.0),
(650, 'PT Solutions Lynbrook',                     'Physical Therapy', 'Lynbrook',    '150 Merrick Rd, Lynbrook, NY 11563',                    40.6548, -73.6751,  1,  0, 4.1),

-- ── RADIOLOGY ─────────────────────────────────────────────────
(651, 'Zwanger-Pesiri Radiology Merrick',          'Radiology',   'Merrick',          '2200 Merrick Rd, Merrick, NY 11566',                    40.6568, -73.5543,  1,  0, 4.2),
(652, 'Zwanger-Pesiri Radiology Massapequa',       'Radiology',   'Massapequa',       '785 Hicksville Rd, Massapequa, NY 11758',               40.6922, -73.4717,  1,  0, 4.1),
(653, 'Zwanger-Pesiri Radiology Bay Shore',        'Radiology',   'Bay Shore',        '1550 Union Blvd, Bay Shore, NY 11706',                  40.7359, -73.2474,  1,  0, 4.1),
(654, 'Zwanger-Pesiri Radiology Commack',          'Radiology',   'Commack',          '5 Vanderbilt Motor Pkwy, Commack, NY 11725',            40.8432, -73.2825,  2,  1, 4.2),
(655, 'North Shore Radiology Manhasset',           'Radiology',   'Manhasset',        '1155 Northern Blvd, Manhasset, NY 11030',               40.7872, -73.6928,  2,  1, 4.3),
(656, 'Stony Brook Radiology East Setauket',       'Radiology',   'East Setauket',    '17 Research Way, East Setauket, NY 11733',              40.9211, -73.1104,  3,  2, 4.2),
(657, 'Northwell Imaging Lake Success',            'Radiology',   'Lake Success',     '1991 Marcus Ave, Lake Success, NY 11042',               40.7595, -73.7176,  4,  3, 4.3),
(658, 'Island MRI & Radiology Hauppauge',          'Radiology',   'Hauppauge',        '1600 Motor Pkwy, Hauppauge, NY 11788',                  40.7817, -73.2184,  2,  1, 4.1),
(659, 'Radiology Associates of Long Island',       'Radiology',   'Rockville Centre', '165 N Village Ave, Rockville Centre, NY 11570',         40.6643, -73.6376,  2,  1, 4.2),
(660, 'St. Francis Imaging Roslyn',                'Radiology',   'Roslyn',           '100 Port Washington Blvd, Roslyn, NY 11576',            40.7887, -73.6479,  8,  7, 4.4),
(661, 'Open MRI of Long Island Westbury',          'Radiology',   'Westbury',         '940 Old Country Rd, Westbury, NY 11590',                40.7567, -73.5791,  1,  0, 4.0),
(662, 'ProScan Imaging Melville',                  'Radiology',   'Melville',         '535 Broadhollow Rd, Melville, NY 11747',                40.7623, -73.4147,  3,  2, 4.1),
(663, 'Peconic Bay Radiology Riverhead',           'Radiology',   'Riverhead',        '1300 Roanoke Ave, Riverhead, NY 11901',                 40.9213, -72.6538,  3,  2, 4.0),
(664, 'Zwanger-Pesiri Radiology Great Neck',       'Radiology',   'Great Neck',       '600 Northern Blvd, Great Neck, NY 11021',               40.7920, -73.7280,  3,  2, 4.2),
(665, 'Southampton Radiology',                     'Radiology',   'Southampton',      '240 Meeting House Ln, Southampton, NY 11968',           40.8878, -72.3861,  5,  4, 4.1)

on conflict (id) do nothing;
