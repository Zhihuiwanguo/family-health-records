-- Ensure documents schema matches fields used by current app code.

create extension if not exists pgcrypto;

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now()
);

alter table public.documents add column if not exists person_id uuid;
alter table public.documents add column if not exists exam_date date;
alter table public.documents add column if not exists hospital text;
alter table public.documents add column if not exists department text;
alter table public.documents add column if not exists report_type text;
alter table public.documents add column if not exists body_part text;
alter table public.documents add column if not exists drive_url text;
alter table public.documents add column if not exists file_name text;
alter table public.documents add column if not exists notes text;
alter table public.documents add column if not exists is_critical boolean default false;

notify pgrst, 'reload schema';
