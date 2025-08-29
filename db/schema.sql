-- Supabase PostgreSQL schema for attendance bot
create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slack_user_id text unique,
  slack_display_name text,
  contact text,
  work_type text,
  transportation_cost numeric,
  hourly_wage numeric,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.works (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  start_time timestamptz not null,
  end_time timestamptz,
  break_time integer,
  comment text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.attendance (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  year integer not null,
  month integer not null,
  day integer not null,
  is_attend boolean not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint attendance_unique unique(user_id, year, month, day)
);
