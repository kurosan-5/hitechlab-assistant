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
  start_time time,  -- 出勤開始時刻を記録
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint attendance_unique unique(user_id, year, month, day)
);

-- チャンネルメモ機能用テーブル
create table if not exists public.channel_memos (
  id uuid primary key default gen_random_uuid(),
  channel_id text not null,
  channel_name text,
  user_id text not null,
  user_name text,
  message text not null,
  message_ts text not null,
  thread_ts text,
  permalink text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- インデックス作成
create index if not exists idx_channel_memos_channel_id on public.channel_memos(channel_id);
create index if not exists idx_channel_memos_created_at on public.channel_memos(created_at desc);
create index if not exists idx_channel_memos_user_id on public.channel_memos(user_id);

-- タスク管理機能用テーブル
create table if not exists public.channel_tasks (
  id uuid primary key default gen_random_uuid(),
  channel_id text not null,
  channel_name text,
  user_id text not null,
  user_name text,
  task_name text not null,
  description text,
  status text not null default 'pending',  -- pending, completed, cancelled
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);

-- タスク管理用インデックス
create index if not exists idx_channel_tasks_channel_id on public.channel_tasks(channel_id);
create index if not exists idx_channel_tasks_status on public.channel_tasks(status);
create index if not exists idx_channel_tasks_user_id on public.channel_tasks(user_id);
create index if not exists idx_channel_tasks_created_at on public.channel_tasks(created_at desc);
