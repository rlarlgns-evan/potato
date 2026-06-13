-- VoyageAI · Supabase schema (SQL Editor에 붙여넣기)
-- Authentication → Providers → Google 활성화 후 실행

create table if not exists public.saved_trips (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  query text not null default '',
  meta jsonb not null default '{}'::jsonb,
  steps jsonb not null default '[]'::jsonb,
  focus_order int not null default 1,
  stop_names text not null default '',
  saved_at timestamptz not null default now()
);

create index if not exists saved_trips_user_saved_at
  on public.saved_trips (user_id, saved_at desc);

alter table public.saved_trips enable row level security;

create policy "saved_trips_select_own"
  on public.saved_trips for select
  using (auth.uid() = user_id);

create policy "saved_trips_insert_own"
  on public.saved_trips for insert
  with check (auth.uid() = user_id);

create policy "saved_trips_delete_own"
  on public.saved_trips for delete
  using (auth.uid() = user_id);
