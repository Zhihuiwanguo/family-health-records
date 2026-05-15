create table if not exists public.health_files (
  id uuid primary key,
  person_id uuid,
  file_name text,
  file_type text,
  storage_path text,
  ocr_text text,
  ocr_status text,
  ai_summary text,
  ai_json jsonb,
  ai_status text,
  confirmed boolean default false,
  confirmed_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.health_files add column if not exists person_id uuid;
alter table public.health_files add column if not exists file_name text;
alter table public.health_files add column if not exists file_type text;
alter table public.health_files add column if not exists storage_path text;
alter table public.health_files add column if not exists ocr_text text;
alter table public.health_files add column if not exists ocr_status text;
alter table public.health_files add column if not exists ai_summary text;
alter table public.health_files add column if not exists ai_json jsonb;
alter table public.health_files add column if not exists ai_status text;
alter table public.health_files add column if not exists confirmed boolean default false;
alter table public.health_files add column if not exists confirmed_at timestamptz;
alter table public.health_files add column if not exists created_at timestamptz default now();
alter table public.health_files add column if not exists updated_at timestamptz default now();

create table if not exists public.health_events (
  id uuid primary key,
  person_id uuid,
  file_id uuid,
  event_date date,
  event_type text,
  report_type text,
  title text,
  summary text,
  risk_level text,
  department text,
  ai_json jsonb,
  confirmed boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.health_events add column if not exists person_id uuid;
alter table public.health_events add column if not exists file_id uuid;
alter table public.health_events add column if not exists event_date date;
alter table public.health_events add column if not exists event_type text;
alter table public.health_events add column if not exists report_type text;
alter table public.health_events add column if not exists title text;
alter table public.health_events add column if not exists summary text;
alter table public.health_events add column if not exists risk_level text;
alter table public.health_events add column if not exists department text;
alter table public.health_events add column if not exists ai_json jsonb;
alter table public.health_events add column if not exists confirmed boolean default false;
alter table public.health_events add column if not exists created_at timestamptz default now();
alter table public.health_events add column if not exists updated_at timestamptz default now();

notify pgrst, 'reload schema';
