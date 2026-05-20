# Supabase SQL Publication Guide

This directory contains GitHub-safe Supabase SQL and tiny example data for local development.

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
- The online discovery tables should be public read-only for `anon`/`authenticated`.
- Keep writes in trusted backend scripts using `DATABASE_URL`, not the browser.
- Existing MVP tables `courses` and `crawl_logs` have anon write policies in the live database. Do not copy those policies into public migrations unless you intentionally want anonymous writes.

## Recommended GitHub Layout

- Commit `schema.safe.sql` as a reference schema.
- Commit small files under `data/examples/`.
- Keep real imports in private data sources or Supabase.
- Recreate production-like data by running scripts against a private Supabase project with local `.env`.
