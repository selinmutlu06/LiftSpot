-- ============================================================
-- LiftSpot schema — run this in Supabase SQL Editor
-- ============================================================

create table if not exists buildings (
  id         bigint primary key,
  name       text not null,
  type       text not null,
  town       text not null,
  addr       text not null,
  lat        double precision not null,
  lng        double precision not null,
  stories    int not null,
  elevators  int not null,
  rating     numeric(3,1) not null default 0,
  verified   boolean not null default false,  -- OSM-confirmed real building (see migrations/003)
  stories_verified boolean not null default false  -- floor count confirmed by OSM building:levels (migrations/005); else it's an estimate
);

create table if not exists reviews (
  id          bigserial primary key,
  building_id bigint references buildings(id) on delete cascade not null,
  who         text not null default 'Anonymous',
  stars       int not null check (stars between 1 and 5),
  body        text not null default '',
  created_at  timestamptz not null default now()
);

-- Row Level Security
alter table buildings enable row level security;
alter table reviews   enable row level security;

create policy "Public read buildings"   on buildings for select using (true);
create policy "Public read reviews"     on reviews   for select using (true);
create policy "Public insert reviews"   on reviews   for insert with check (true);

-- The public may update buildings, but ONLY the rating column (recomputed from
-- real reviews by the app). Column-level grants enforce this — RLS gates rows,
-- not columns — so no anonymous visitor can touch verified, coordinates, or
-- specs. See migrations/004 for the rationale.
revoke update on table buildings from anon, authenticated;
grant  update (rating) on table buildings to anon, authenticated;
create policy "Public update building rating"
  on buildings for update using (true) with check (true);

-- ============================================================
-- Seed buildings
-- ============================================================
insert into buildings (id, name, type, town, addr, lat, lng, stories, elevators, rating) values
(  1, 'Winthrop / NYU Langone Hospital',                             'Medical',   'Mineola',            '259 1st St, Mineola, NY',                        40.7479, -73.6407, 11, 8, 4.6),
(  2, 'RXR Plaza',                                                   'Office',    'Uniondale',          '625 RXR Plaza, Uniondale, NY',                   40.7257, -73.5876, 15, 12, 4.8),
(  3, 'Roosevelt Field Mall',                                        'Mall',      'Garden City',        '630 Old Country Rd, Garden City, NY',            40.7407, -73.6107, 2, 6, 4.2),
(  4, 'Stony Brook University Hospital',                             'Medical',   'Stony Brook',        '101 Nicolls Rd, Stony Brook, NY',                40.9089, -73.1148, 19, 20, 4.7),
(  5, 'EAB Plaza (West Tower)',                                      'Office',    'Uniondale',          '100 Quentin Roosevelt Blvd, Uniondale, NY',      40.73002, -73.6039, 14, 10, 4.5),
(  6, 'Walt Whitman Shops',                                          'Mall',      'Huntington Station', '160 Walt Whitman Rd, Huntington Station, NY',    40.82247, -73.40943, 2, 5, 4.0),
(  7, 'Nassau University Medical Center',                            'Medical',   'East Meadow',        '2201 Hempstead Tpke, East Meadow, NY',           40.7203, -73.5532, 19, 16, 4.3),
(  8, 'Long Island Marriott',                                        'Hotel',     'Uniondale',          '101 James Doolittle Blvd, Uniondale, NY',        40.7234, -73.5905, 11, 6, 4.4),
(  9, 'Hofstra University — Axinn Library',                          'Education', 'Hempstead',          '123 Hofstra University, Hempstead, NY',          40.7146, -73.6003, 10, 4, 4.1),
( 10, 'Garden City Hotel',                                           'Hotel',     'Garden City',        '45 7th St, Garden City, NY',                     40.7268, -73.6398, 7, 5, 4.5),
( 11, 'Tanger Outlets Deer Park',                                    'Mall',      'Deer Park',          '152 The Arches Cir, Deer Park, NY',              40.76494, -73.30413, 2, 4, 3.9),
( 12, 'South Nassau / Mount Sinai South Nassau',                     'Medical',   'Oceanside',          '1 Healthy Way, Oceanside, NY',                   40.6388, -73.6334, 8, 9, 4.4),
( 13, 'North Shore University Hospital',                             'Medical',   'Manhasset',          '300 Community Dr, Manhasset, NY 11030',          40.7779, -73.7017, 10, 12, 4.7),
( 14, 'Long Island Jewish Valley Stream (Northwell Health)',         'Medical',   'Valley Stream',      '900 Franklin Ave, Valley Stream, NY 11580',      40.6811, -73.6864, 7, 6, 4.2),
( 15, 'Green Acres Mall',                                            'Mall',      'Valley Stream',      '2034 Green Acres Rd S, Valley Stream, NY 11581', 40.6630, -73.7219, 2, 4, 4.0),
( 16, 'Adelphi University — Post Hall',                              'Education', 'Garden City',        '1 South Ave, Garden City, NY 11530',             40.7202, -73.6517, 9, 4, 4.1),
( 17, '1 Jericho Plaza',                                             'Office',    'Jericho',            '1 Jericho Plaza, Jericho, NY 11753',             40.7920, -73.5398, 6, 6, 4.3),
( 18, 'Sunrise Mall',                                                'Mall',      'Massapequa',         '600 Sunrise Mall, Massapequa, NY 11758',         40.6829, -73.4346, 2, 4, 3.9),
( 19, 'One Hollow Lane',                                             'Office',    'Lake Success',       '1 Hollow Ln, Lake Success, NY 11020',            40.76607, -73.69501, 7, 5, 4.3),
( 20, 'Huntington Hospital (Northwell Health)',                      'Medical',   'Huntington',         '270 Park Ave, Huntington, NY 11743',             40.8794, -73.4162, 7, 6, 4.4),
( 21, 'Hilton Long Island / Huntington',                             'Hotel',     'Melville',           '598 Broad Hollow Rd, Melville, NY 11747',        40.7611, -73.4227, 9, 5, 4.3),
( 22, 'Melville Marriott Long Island',                               'Hotel',     'Melville',           '1350 Walt Whitman Rd, Melville, NY 11747',       40.7834, -73.4216, 10, 6, 4.5),
( 23, 'Good Samaritan University Hospital',                          'Medical',   'West Islip',         '1000 Montauk Hwy, West Islip, NY 11795',         40.6941, -73.2943, 9, 8, 4.4),
( 24, 'Hauppauge Corporate Center',                                  'Office',    'Hauppauge',          '150 Motor Pkwy, Hauppauge, NY 11788',            40.8073, -73.25941, 8, 6, 4.2),
( 25, 'Smith Haven Mall',                                            'Mall',      'Lake Grove',         '313 Smith Haven Mall, Lake Grove, NY 11755',     40.8590, -73.1247, 2, 5, 4.1),
( 26, 'Frank Melville Jr. Memorial Library, Stony Brook University', 'Education', 'Stony Brook',        'Circle Rd, Stony Brook, NY 11794',               40.9156, -73.1227, 6, 4, 4.2),
( 27, 'Peconic Bay Medical Center',                                  'Medical',   'Riverhead',          '1 Heroes Way, Riverhead, NY 11901',              40.9192, -72.6631, 6, 5, 4.3)

on conflict (id) do nothing;

-- Reviews are real submissions only — no seed data.
