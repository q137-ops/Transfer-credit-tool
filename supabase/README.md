# Supabase SQL Publication Guide

This directory contains GitHub-safe Supabase SQL and tiny example data for local development.

Users who are deploying against the hosted read-only backend do not need to run any SQL from this directory. These files are for maintainers, security review, and independent self-hosted database setups.

## Safe to Commit

- Schema DDL: `create table`, `alter table`, `create index`, constraints, triggers.
- Read-only views and RPC functions without secrets.
- RLS enablement and least-privilege read policies.
- Extension setup for public search, such as `pg_trgm` and `unaccent`.
- Small synthetic or public example rows.

## Do Not Commit

- `.env`, `DATABASE_URL`, JWT secrets, API keys, or Supabase `service_role` keys.
- Production data dumps from `transfer_course_search`, `transfer_equivalencies_raw`, `online_courses`, `course_facts`, crawl logs, or AI judgments.
- `raw_extraction`, `raw_judgment`, `facts_summary`, full crawl HTML/text, or model outputs unless manually redacted.
- SQL that grants browser roles write access by default.
- Early MVP policies such as anon insert/update on app tables.

## Current Database Notes

- Public front-end reads currently rely on:
  - `public.transfer_course_search`
  - `public.online_course_discovery_search`
  - `public.search_online_course_discovery(q, max_results)`
- The public browser roles should be read-only and limited to the tables/view/RPC required by search.
- Keep writes in trusted backend scripts using `DATABASE_URL`, not the browser.
- Do not expose `DATABASE_URL`, `service_role`, crawl logs, raw import tables, or search provider keys to deployed users.

## Hosted Read-Only Backend

Deployments can point at an existing hosted Supabase backend by setting only:

```env
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

These values are public by design. Before sharing them with deployment users, apply or verify `security_hardening.sql` so `anon` and `authenticated` have no write privileges and only the search-facing objects are readable.

The hardening is reversible. It only changes grants and RLS policies for browser-facing roles (`anon` and `authenticated`). Maintainers can still update data through trusted server-side credentials such as `DATABASE_URL`.

If a future feature intentionally needs frontend writes, add a narrow policy for that specific table and action instead of restoring broad anonymous writes. For example:

```sql
grant insert on public.some_public_table to authenticated;

create policy authenticated_can_insert_some_public_table
  on public.some_public_table
  for insert
  to authenticated
  with check (true);
```

Do not grant broad write access to `anon` unless the table is explicitly designed for public anonymous submissions.

## Recommended GitHub Layout

- Commit `schema.safe.sql` as a reference schema.
- Commit small files under `data/examples/`.
- Keep real imports in private data sources or Supabase.
- Recreate production-like data by running scripts against a private Supabase project with local `.env`.
