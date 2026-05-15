create extension if not exists "pgcrypto";

create table if not exists public.persons (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  relation text,
  dob date,
  notes text,
  full_name text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.persons add column if not exists name text;
alter table public.persons add column if not exists relation text;
alter table public.persons add column if not exists dob date;
alter table public.persons add column if not exists notes text;
alter table public.persons add column if not exists full_name text;
alter table public.persons add column if not exists created_at timestamptz default now();
alter table public.persons add column if not exists updated_at timestamptz default now();

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

alter table public.health_files add column if not exists person_id uuid references public.persons(id);
alter table public.health_files add column if not exists file_name text;
alter table public.health_files add column if not exists file_type text;
alter table public.health_files add column if not exists storage_path text;
alter table public.health_files add column if not exists upload_time timestamptz default now();
alter table public.health_files add column if not exists ocr_text text;
alter table public.health_files add column if not exists ocr_status text default 'pending';
alter table public.health_files add column if not exists ai_summary text;
alter table public.health_files add column if not exists ai_json jsonb default '{}'::jsonb;
alter table public.health_files add column if not exists ai_status text default 'pending';
alter table public.health_files add column if not exists confirmed boolean default false;
alter table public.health_files add column if not exists confirmed_at timestamptz;
alter table public.health_files add column if not exists created_at timestamptz default now();
alter table public.health_files add column if not exists updated_at timestamptz default now();

create table if not exists public.health_events (
  id uuid primary key default gen_random_uuid(),
  person_id uuid references public.persons(id),
  file_id uuid references public.health_files(id),
  event_date date,
  event_type text,
  title text,
  summary text,
  risk_level text,
  department text,
  confirmed boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.health_events add column if not exists person_id uuid references public.persons(id);
alter table public.health_events add column if not exists file_id uuid references public.health_files(id);
alter table public.health_events add column if not exists event_date date;
alter table public.health_events add column if not exists event_type text;
alter table public.health_events add column if not exists title text;
alter table public.health_events add column if not exists summary text;
alter table public.health_events add column if not exists risk_level text;
alter table public.health_events add column if not exists department text;
alter table public.health_events add column if not exists confirmed boolean default true;
alter table public.health_events add column if not exists created_at timestamptz default now();
alter table public.health_events add column if not exists updated_at timestamptz default now();

notify pgrst, 'reload schema';
