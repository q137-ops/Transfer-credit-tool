-- Optional hardening migration for a public Supabase project.
-- Review before applying. This does not contain secrets or production data.

revoke insert, update, delete, truncate, references, trigger on all tables in schema public
from anon, authenticated;

grant select on
  public.schools,
  public.transfer_course_search,
  public.online_courses,
  public.online_program_pages,
  public.online_discovery_runs,
  public.online_course_discovery_search
to anon, authenticated;

grant execute on function public.search_online_course_discovery(text, integer)
to anon, authenticated;

alter table public.schools enable row level security;
alter table public.transfer_course_search enable row level security;
alter table public.online_courses enable row level security;
alter table public.online_program_pages enable row level security;
alter table public.online_discovery_runs enable row level security;
alter table public.course_facts enable row level security;
alter table public.crawl_tasks enable row level security;
alter table public.ai_judgments enable row level security;
alter table public.crawl_logs enable row level security;
alter table public.courses enable row level security;
alter table public.transfer_courses enable row level security;
alter table public.transfer_equivalencies_raw enable row level security;

drop policy if exists "mvp anon can insert courses" on public.courses;
drop policy if exists "mvp anon can update courses" on public.courses;
drop policy if exists "mvp anon can insert crawl logs" on public.crawl_logs;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'schools' and policyname = 'public_read_schools'
  ) then
    create policy public_read_schools
      on public.schools for select to anon, authenticated using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'transfer_course_search' and policyname = 'public_read_transfer_course_search'
  ) then
    create policy public_read_transfer_course_search
      on public.transfer_course_search for select to anon, authenticated using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'online_courses' and policyname = 'public_read_online_courses'
  ) then
    create policy public_read_online_courses
      on public.online_courses for select to anon, authenticated using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'online_program_pages' and policyname = 'public_read_online_program_pages'
  ) then
    create policy public_read_online_program_pages
      on public.online_program_pages for select to anon, authenticated using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'online_discovery_runs' and policyname = 'public_read_online_discovery_runs'
  ) then
    create policy public_read_online_discovery_runs
      on public.online_discovery_runs for select to anon, authenticated using (true);
  end if;
end $$;
