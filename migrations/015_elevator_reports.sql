-- ============================================================
-- 015 — Community elevator reports
-- Elevator counts have no public source anywhere (migrations/005,
-- 008), so buildings.elevators has been NULL since the purge. The
-- people who actually know — riders and enthusiasts — can now report
-- what's inside: count, brand, drive type, notes. Reports sit pending
-- until reviewed (scripts/review_submissions.py); an approved count
-- becomes buildings.elevators, and the UI labels it "reported",
-- never presenting it as a verified fact.
-- Run in the Supabase SQL Editor.
-- ============================================================

create table if not exists elevator_reports (
  id          bigserial primary key,
  building_id bigint not null references buildings(id) on delete cascade,
  elevators   int check (elevators between 1 and 100),
  brand       text check (char_length(brand) <= 40),
  kind        text check (kind in ('hydraulic', 'traction')),
  notes       text check (char_length(notes) <= 500),
  who         text not null default 'Anonymous' check (char_length(who) <= 40),
  status      text not null default 'pending'
              check (status in ('pending', 'approved', 'rejected')),
  created_at  timestamptz not null default now(),
  -- An empty report says nothing: at least one substantive field.
  constraint says_something check (
    elevators is not null or brand is not null or kind is not null
  )
);

alter table elevator_reports enable row level security;

-- Same shape as submissions (migrations/014): anyone may file a pending
-- report and read reports; only the SQL editor (via the generated review
-- migration) can approve, edit, or delete.
create policy "Public insert pending reports" on elevator_reports
  for insert with check (status = 'pending');
create policy "Public read reports" on elevator_reports
  for select using (true);
revoke update, delete on table elevator_reports from anon, authenticated;

-- Sanity check:
select count(*) as elevator_reports from elevator_reports;
