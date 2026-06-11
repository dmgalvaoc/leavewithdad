-- ── LeaveWithDad: community_events table ─────────────────────────────────────
-- Run this once in Supabase → SQL Editor

create table if not exists community_events (
  id              uuid        default gen_random_uuid() primary key,
  title           text        not null,
  date            date        not null,
  time            text,
  city            text        not null,
  description     text,
  link            text,
  submitter_id    uuid        references auth.users(id),
  submitter_name  text,
  submitter_email text,
  status          text        not null default 'pending'
                              check (status in ('pending', 'approved', 'rejected')),
  created_at      timestamptz default now()
);

-- Row-level security
alter table community_events enable row level security;

-- Anyone (including anon) can read approved events
create policy "Public can read approved"
  on community_events for select
  using (status = 'approved');

-- Authenticated users can submit their own events
create policy "Authenticated can insert own"
  on community_events for insert
  to authenticated
  with check (auth.uid() = submitter_id);

-- Admin (Diego) can read all (pending + rejected too)
create policy "Admin can read all"
  on community_events for select
  to authenticated
  using (auth.uid() = 'ac64773e-392b-4350-871d-efba51c45574'::uuid);

-- Admin can update status (approve / reject)
create policy "Admin can update status"
  on community_events for update
  to authenticated
  using (auth.uid() = 'ac64773e-392b-4350-871d-efba51c45574'::uuid);
