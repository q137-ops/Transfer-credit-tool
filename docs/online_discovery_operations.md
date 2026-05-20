# Online Discovery Operations

This note describes how the school-level online course discovery workflow is intended to run.

## Goal

For a target school, discover whether it offers online, academic-credit, non-degree-accessible courses. When available, extract:

- direct program/catalog pages
- course code and title
- credits
- price per course or per credit
- registration/enrollment URL
- evidence and missing review tasks

The default path does not require a large-model API. Search providers are used only to find candidate official pages; local rules, fuzzy scoring, and official catalog parsers do the verification work.

## Backend Endpoint

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8010
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/health
```

Discover a school without writing to Supabase:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8010/online-courses/discover-school `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"school_name":"Columbus State Community College","use_ai":false,"persist":false,"max_pages":40,"max_depth":2}'
```

Persist discovery output:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8010/online-courses/discover-school `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"school_name":"Columbus State Community College","use_ai":false,"persist":true,"max_pages":40,"max_depth":2}'
```

## Batch Discovery

Run one school:

```powershell
.\.venv\Scripts\python.exe scripts\run_online_discovery_batch.py --school "Columbus State Community College" --max-pages 40 --max-depth 2
```

Run the largest transfer schools:

```powershell
.\.venv\Scripts\python.exe scripts\run_online_discovery_batch.py --limit 10 --max-pages 40 --max-depth 2
```

## Official Catalog Imports

Some schools are better handled through official catalogs or APIs instead of general crawling:

```powershell
.\.venv\Scripts\python.exe scripts\import_official_online_catalogs.py --school asu
.\.venv\Scripts\python.exe scripts\import_official_online_catalogs.py --school byu
.\.venv\Scripts\python.exe scripts\import_official_online_catalogs.py --school cscc
.\.venv\Scripts\python.exe scripts\import_official_online_catalogs.py --school keiser
```

Current behavior:

- ASU imports Universal Learner Courses from official ASU pages.
- BYU imports Independent Study university courses from the official catalog API.
- CSCC imports current Web distance-learning sections and estimates Ohio resident course price from per-credit tuition.
- Keiser records a manual review task because no official open-enrollment non-degree individual online credit catalog was confirmed.

## Recommended Search Strategy

Do not search per transfer row. Search per school.

Suggested query families:

- `{school} online non-degree credit courses`
- `{school} guest student online credit courses`
- `{school} transient student online courses`
- `{school} non-matriculated student credit courses`
- `{school} course schedule online tuition`

The crawler should then stay mostly on official domains and follow high-value links such as:

- course catalog
- class schedule
- online learning
- guest/transient/non-degree admission
- registration/enroll
- tuition/fees

## Supabase Tables

The primary discovery tables are:

- `schools`
- `online_discovery_runs`
- `online_program_pages`
- `online_courses`
- `course_facts`
- `crawl_tasks`

Frontend search uses:

- `transfer_course_search`
- `online_course_discovery_search`
- `search_online_course_discovery(q, max_results)`

See `supabase/schema.safe.sql` for a GitHub-safe reference schema.

## Data Safety

Do not commit production dumps, raw crawl output, or secrets. Keep `.env`, source spreadsheets, and full Supabase exports out of GitHub. Commit only schema, code, docs, and small redacted examples.
