create table if not exists public.health_observations (
  id uuid primary key default gen_random_uuid(),
  person_id uuid references public.persons(id) on delete set null,
  file_id uuid references public.health_files(id) on delete cascade,
  report_date date,
  report_type text,
  section_name text,
  item_name text not null,
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

alter table public.health_observations add column if not exists person_id uuid references public.persons(id) on delete set null;
alter table public.health_observations add column if not exists file_id uuid references public.health_files(id) on delete cascade;
alter table public.health_observations add column if not exists report_date date;
alter table public.health_observations add column if not exists report_type text;
alter table public.health_observations add column if not exists section_name text;
alter table public.health_observations add column if not exists item_name text;
alter table public.health_observations add column if not exists item_key text;
alter table public.health_observations add column if not exists item_alias text;
alter table public.health_observations add column if not exists result_text text;
alter table public.health_observations add column if not exists result_value numeric;
alter table public.health_observations add column if not exists result_unit text;
alter table public.health_observations add column if not exists reference_range text;
alter table public.health_observations add column if not exists reference_low numeric;
alter table public.health_observations add column if not exists reference_high numeric;
alter table public.health_observations add column if not exists abnormal_flag text;
alter table public.health_observations add column if not exists abnormal_direction text;
alter table public.health_observations add column if not exists risk_level text;
alter table public.health_observations add column if not exists interpretation text;
alter table public.health_observations add column if not exists suggested_action text;
alter table public.health_observations add column if not exists source_text text;
alter table public.health_observations add column if not exists confidence numeric;
alter table public.health_observations add column if not exists created_at timestamptz default now();
alter table public.health_observations add column if not exists updated_at timestamptz default now();

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

alter table public.health_findings add column if not exists person_id uuid references public.persons(id) on delete set null;
alter table public.health_findings add column if not exists file_id uuid references public.health_files(id) on delete cascade;
alter table public.health_findings add column if not exists report_date date;
alter table public.health_findings add column if not exists report_type text;
alter table public.health_findings add column if not exists body_part text;
alter table public.health_findings add column if not exists finding_name text;
alter table public.health_findings add column if not exists finding_description text;
alter table public.health_findings add column if not exists measurement_text text;
alter table public.health_findings add column if not exists size_value numeric;
alter table public.health_findings add column if not exists size_unit text;
alter table public.health_findings add column if not exists risk_level text;
alter table public.health_findings add column if not exists suggested_department text;
alter table public.health_findings add column if not exists suggested_action text;
alter table public.health_findings add column if not exists source_text text;
alter table public.health_findings add column if not exists confidence numeric;
alter table public.health_findings add column if not exists created_at timestamptz default now();
alter table public.health_findings add column if not exists updated_at timestamptz default now();

notify pgrst, 'reload schema';
