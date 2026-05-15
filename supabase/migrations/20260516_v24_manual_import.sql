create extension if not exists "pgcrypto";

create table if not exists public.health_files (
  id uuid primary key default gen_random_uuid(),
  person_id uuid references public.persons(id),
  file_name text,
  file_type text,
  storage_path text,
  upload_time timestamptz default now(),
  ocr_text text,
  ocr_status text default 'pending',
  ai_summary text,
  ai_json jsonb default '{}'::jsonb,
  ai_status text default 'pending',
  confirmed boolean default false,
  confirmed_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.health_events (
  id uuid primary key default gen_random_uuid(),
  person_id uuid references public.persons(id),
  file_id uuid references public.health_files(id),
  event_date date,
  event_type text,
  report_type text,
  title text,
  summary text,
  risk_level text,
  department text,
  ai_json jsonb default '{}'::jsonb,
  confirmed boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.health_events add column if not exists report_type text;
alter table public.health_events add column if not exists ai_json jsonb default '{}'::jsonb;

create table if not exists public.health_observations (
  id uuid primary key default gen_random_uuid(),
  person_id uuid references public.persons(id) on delete set null,
  file_id uuid references public.health_files(id) on delete cascade,
  report_date date,
  report_type text,
  section_name text,
  item_name text,
  item_key text,
  item_alias text,
  result_text text,
  result_value numeric,
  result_unit text,
  reference_range text,
  reference_low numeric,
  reference_high numeric,
  abnormal_flag text,
  abnormal_direction text,
  risk_level text,
  interpretation text,
  suggested_action text,
  source_text text,
  confidence numeric,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.health_findings (
  id uuid primary key default gen_random_uuid(),
  person_id uuid references public.persons(id) on delete set null,
  file_id uuid references public.health_files(id) on delete cascade,
  report_date date,
  report_type text,
  body_part text,
  finding_name text,
  finding_description text,
  measurement_text text,
  size_value numeric,
  size_unit text,
  risk_level text,
  suggested_department text,
  suggested_action text,
  source_text text,
  confidence numeric,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

notify pgrst, 'reload schema';
