-- GitHub-safe reference schema for Transfer Master.
-- This file intentionally excludes secrets and production data.
-- Apply to a fresh Supabase project only after reviewing names and policies.

create extension if not exists pg_trgm with schema extensions;
create extension if not exists unaccent with schema extensions;
create extension if not exists pgcrypto with schema extensions;

create table if not exists public.schools (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  normalized_name text,
  primary_domain text,
  state text,
  country text default 'US',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.online_discovery_runs (
  id uuid primary key default gen_random_uuid(),
  school_name text not null,
  status text not null default 'running',
  use_ai boolean not null default false,
  max_pages integer not null default 40,
  max_depth integer not null default 2,
  program_page_count integer not null default 0,
  course_count integer not null default 0,
  missing_task_count integer not null default 0,
  error_message text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists public.online_program_pages (
  id uuid primary key default gen_random_uuid(),
  school_id uuid references public.schools(id) on delete cascade,
  discovery_run_id uuid references public.online_discovery_runs(id) on delete set null,
  program_name text,
  program_type text,
  url text not null,
  page_title text,
  page_type text,
  is_official boolean,
  is_online boolean,
  is_credit_bearing boolean,
  is_non_degree_accessible boolean,
  requires_degree_admission boolean,
  confidence numeric,
  source_snippet text,
  evidence text,
  discovered_by text,
  raw_judgment jsonb,
  last_checked_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists public.online_courses (
  id uuid primary key default gen_random_uuid(),
  school_id uuid references public.schools(id) on delete cascade,
  program_page_id uuid references public.online_program_pages(id) on delete set null,
  discovery_run_id uuid references public.online_discovery_runs(id) on delete set null,
  course_code text,
  course_title text,
  credits numeric,
  canonical_course_url text,
  delivery_mode text,
  enrollment_status text,
  final_status text,
  confidence numeric,
  raw_extraction jsonb,
  is_online boolean,
  is_academic_credit boolean,
  is_non_degree_accessible boolean,
  price_per_credit numeric,
  price_per_course numeric,
  registration_url text,
  facts_summary jsonb not null default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique (school_id, course_code, canonical_course_url)
);

create table if not exists public.course_facts (
  id uuid primary key default gen_random_uuid(),
  course_id uuid references public.online_courses(id) on delete cascade,
  discovery_run_id uuid references public.online_discovery_runs(id) on delete set null,
  fact_type text not null,
  value_text text,
  value_number numeric,
  value_json jsonb,
  source_url text not null,
  source_title text,
  source_snippet text,
  confidence numeric,
  extracted_at timestamptz default now()
);

create table if not exists public.crawl_tasks (
  id uuid primary key default gen_random_uuid(),
  school_id uuid references public.schools(id) on delete cascade,
  course_id uuid references public.online_courses(id) on delete cascade,
  discovery_run_id uuid references public.online_discovery_runs(id) on delete set null,
  task_type text not null,
  query text,
  status text default 'pending',
  priority integer default 5,
  result_json jsonb,
  error_message text,
  created_at timestamptz default now(),
  completed_at timestamptz
);

create table if not exists public.transfer_course_search (
  id uuid primary key default gen_random_uuid(),
  school_name text not null,
  source_course_code text,
  source_course_title text,
  target_course_code text,
  target_course_title text,
  effective_date text,
  is_active boolean default true,
  school_url text,
  catalog_url text,
  registration_url text,
  tuition_url text,
  is_online boolean,
  format text,
  estimated_price numeric,
  price_per_credit numeric,
  fees numeric,
  term text,
  duration_weeks integer,
  difficulty_level text,
  confidence_level text default 'verified_by_osu_equivalency',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists schools_name_trgm_idx
  on public.schools using gin (name extensions.gin_trgm_ops);

create index if not exists online_courses_school_code_idx
  on public.online_courses (school_id, course_code);

create index if not exists online_courses_title_trgm_idx
  on public.online_courses using gin (course_title extensions.gin_trgm_ops);

create index if not exists online_program_pages_school_idx
  on public.online_program_pages (school_id);

create index if not exists transfer_course_search_school_idx
  on public.transfer_course_search (school_name);

create index if not exists transfer_course_search_course_idx
  on public.transfer_course_search (source_course_code);

create or replace view public.online_course_discovery_search
with (security_invoker = true) as
select
  oc.id,
  oc.discovery_run_id,
  s.name as school_name,
  s.normalized_name,
  s.primary_domain,
  opp.url as program_url,
  opp.page_title as program_title,
  opp.page_type,
  opp.is_official,
  oc.course_code,
  oc.course_title,
  oc.credits,
  oc.canonical_course_url,
  oc.delivery_mode,
  oc.is_online,
  oc.is_academic_credit,
  oc.is_non_degree_accessible,
  oc.price_per_credit,
  oc.price_per_course,
  oc.registration_url,
  oc.final_status,
  oc.confidence,
  oc.facts_summary,
  oc.updated_at,
  concat_ws(' ', s.name, oc.course_code, oc.course_title, opp.page_title) as search_text
from public.online_courses oc
left join public.schools s on s.id = oc.school_id
left join public.online_program_pages opp on opp.id = oc.program_page_id;

create or replace function public.search_online_course_discovery(
  q text default '',
  max_results integer default 50
)
returns table (
  id uuid,
  school_name text,
  course_code text,
  course_title text,
  credits numeric,
  canonical_course_url text,
  delivery_mode text,
  is_online boolean,
  is_academic_credit boolean,
  is_non_degree_accessible boolean,
  price_per_credit numeric,
  price_per_course numeric,
  registration_url text,
  final_status text,
  confidence numeric,
  program_url text,
  rank_score real
)
language sql
stable
set search_path = public, extensions
as $$
  select
    v.id,
    v.school_name,
    v.course_code,
    v.course_title,
    v.credits,
    v.canonical_course_url,
    v.delivery_mode,
    v.is_online,
    v.is_academic_credit,
    v.is_non_degree_accessible,
    v.price_per_credit,
    v.price_per_course,
    v.registration_url,
    v.final_status,
    v.confidence,
    v.program_url,
    case
      when coalesce(q, '') = '' then 0::real
      else extensions.similarity(v.search_text, q)
    end as rank_score
  from public.online_course_discovery_search v
  where coalesce(q, '') = ''
     or v.search_text ilike '%' || q || '%'
     or extensions.similarity(v.search_text, q) > 0.12
  order by rank_score desc, v.confidence desc nulls last, v.updated_at desc nulls last
  limit greatest(1, least(max_results, 200));
$$;

alter table public.schools enable row level security;
alter table public.online_courses enable row level security;
alter table public.online_program_pages enable row level security;
alter table public.online_discovery_runs enable row level security;
alter table public.transfer_course_search enable row level security;

create policy public_read_schools
  on public.schools for select to anon, authenticated using (true);

create policy public_read_online_courses
  on public.online_courses for select to anon, authenticated using (true);

create policy public_read_online_program_pages
  on public.online_program_pages for select to anon, authenticated using (true);

create policy public_read_online_discovery_runs
  on public.online_discovery_runs for select to anon, authenticated using (true);

create policy public_read_transfer_course_search
  on public.transfer_course_search for select to anon, authenticated using (true);

grant usage on schema public to anon, authenticated;
grant select on
  public.schools,
  public.online_courses,
  public.online_program_pages,
  public.online_discovery_runs,
  public.transfer_course_search,
  public.online_course_discovery_search
to anon, authenticated;

grant execute on function public.search_online_course_discovery(text, integer)
to anon, authenticated;

-- Do not grant anon/authenticated insert, update, delete, truncate, references, or trigger privileges.
