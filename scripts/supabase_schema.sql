-- VoyageAI · Supabase schema (SQL Editor에 한 번 실행)
-- 프로젝트: ocmykswlbeaaicyrmskl
-- Redirect: https://rlarlgns-evan.github.io/potato/
-- Auth: Google / Kakao 활성화 후 실행

-- Edge Function (카카오 길찾기 CORS 프록시):
--   supabase secrets set KAKAO_REST_KEY=...
--   supabase functions deploy kakao-directions --no-verify-jwt
-- 브라우저는 {SUPABASE_URL}/functions/v1/kakao-directions 호출

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

drop policy if exists "saved_trips_select_own" on public.saved_trips;
drop policy if exists "saved_trips_insert_own" on public.saved_trips;
drop policy if exists "saved_trips_delete_own" on public.saved_trips;

create policy "saved_trips_select_own"
  on public.saved_trips for select
  to authenticated
  using (auth.uid() = user_id);

create policy "saved_trips_insert_own"
  on public.saved_trips for insert
  to authenticated
  with check (auth.uid() = user_id);

create policy "saved_trips_delete_own"
  on public.saved_trips for delete
  to authenticated
  using (auth.uid() = user_id);

-- 확인: Table Editor → saved_trips 테이블이 보이면 OK
