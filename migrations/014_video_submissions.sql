-- ============================================================
-- 014 — "Filmed it?" video submissions
-- Visitors on an unfilmed building can paste their YouTube link.
-- Nothing shows on the site until a human approves it:
-- scripts/review_submissions.py serves the review page and turns
-- approvals into the next migration. Run in the Supabase SQL Editor.
-- ============================================================

create table if not exists submissions (
  id          bigserial primary key,
  building_id bigint not null references buildings(id) on delete cascade,
  url         text not null,
  status      text not null default 'pending'
              check (status in ('pending', 'approved', 'rejected')),
  created_at  timestamptz not null default now(),
  -- Only real YouTube watch links; anything else is rejected at the door.
  constraint youtube_url check (
    url ~* '^https://((www|m)\.)?(youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]{6,}'
  ),
  -- The same video can't be submitted twice for the same building.
  unique (building_id, url)
);

alter table submissions enable row level security;

-- Anyone may submit (pending only) and see what's been submitted; nobody
-- anonymous may approve, edit, or delete — that happens in the SQL editor
-- via the migration the review tool generates.
create policy "Public insert pending submissions" on submissions
  for insert with check (status = 'pending');
create policy "Public read submissions" on submissions
  for select using (true);
revoke update, delete on table submissions from anon, authenticated;

-- Sanity check:
select count(*) as submissions from submissions;
