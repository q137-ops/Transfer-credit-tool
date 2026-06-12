# Transfer Master

Transfer Master is a local-first course discovery and transfer-equivalency tool. It combines OSU-verified transfer course records with crawled online credit-course catalogs so users can find courses that are both transferable and available online.

The project currently includes:

- A Next.js front end for searching verified transfer courses and matched online offerings.
- A FastAPI backend for school-level online course discovery.
- A rule-based crawler and fuzzy matcher that can run without large-model APIs.
- Supabase SQL for schema, search RPCs, RLS, and example seed data.
- Official-catalog import scripts for sources such as ASU ULC, BYU Independent Study, and Columbus State Community College.

## Fastest Deployment

Most users do not need to create a Supabase project, run SQL, import data, or run the Python crawler. They can deploy the read-only search site against the hosted Supabase dataset maintained for this project.

Required public values:

```env
NEXT_PUBLIC_SUPABASE_URL=https://pqgakcbzazunbdtfpkox.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_ogfsGZKcfi-_JOD3kdXndQ_ujWAEdxQ
```

Copy/paste deployment commands are in [DEPLOY.md](DEPLOY.md).

These two `NEXT_PUBLIC_` values are browser-visible by design and must be read-only at the database policy level. Do not give deployment users `DATABASE_URL`, Supabase `service_role` keys, Tavily/Google search keys, or production data dumps.

## Repository Layout

```text
backend/              FastAPI app and online discovery services
web/                  Next.js search UI
scripts/              Import and batch discovery scripts
supabase/             GitHub-safe schema, hardening SQL, and example seed
data/examples/        Small public demo CSVs
docs/                 Operational notes
```

## What the App Does

1. Stores OSU transfer-equivalency rows in Supabase.
2. Discovers whether a school offers online, academic-credit, non-degree-accessible courses.
3. Crawls or imports official course lists, credits, prices, and enrollment links.
4. Normalizes course numbers so variants such as `HST 109`, `HST-109`, and `HST109` can match.
5. Shows one combined course list:
   - `verified_by_osu_equivalency` when only OSU equivalency is known.
   - `verified_by_osu_equivalency_and_online` when the verified course also matches a discovered online course.

## Tech Stack

- Front end: Next.js, React, Tailwind CSS, Supabase JS
- Backend: FastAPI, httpx, BeautifulSoup, psycopg2
- Database: Supabase Postgres, RLS, `pg_trgm`, `unaccent`
- Search providers: Tavily or Google Programmable Search support in code; Brave Search is a recommended future provider for larger batches.

## Local Setup for Maintainers

This section is for maintainers who need to run the crawler, imports, or backend scripts. If you only want to deploy the public search UI, use [DEPLOY.md](DEPLOY.md) instead.

### 1. Environment Files

Copy the example env files and fill in your own values:

```powershell
Copy-Item .env.example .env
Copy-Item web\.env.local.example web\.env.local
```

Root `.env`:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=tvly-your-key-here
GOOGLE_SEARCH_API_KEY=
GOOGLE_SEARCH_CX=
```

Web `.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-publishable-or-anon-key
```

Never commit real `.env` files.

## Deploy With the Hosted Read-Only Supabase Backend

For the simplest deployment path, use [DEPLOY.md](DEPLOY.md). It gives a PowerShell block that clones this repository, sets the two public Supabase variables, and deploys the `web` app to Vercel.

This mode supports the public search UI only. It does not let deployed users run crawlers, import spreadsheets, modify data, or access private backend credentials.

### Vercel Deployment

1. Fork or clone this repository.
2. In Vercel, create a new project from the GitHub repository.
3. Set **Root Directory** to `web`.
4. Keep the default commands:
   - Install Command: `npm install`
   - Build Command: `npm run build`
   - Output Directory: leave unset for standard Next.js hosting
5. Add these environment variables using the hosted read-only values supplied by the project maintainer:

```env
NEXT_PUBLIC_SUPABASE_URL=https://pqgakcbzazunbdtfpkox.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_ogfsGZKcfi-_JOD3kdXndQ_ujWAEdxQ
```

6. Deploy.

The `NEXT_PUBLIC_` variables are intentionally browser-visible. Security comes from Supabase RLS and read-only grants, not from hiding these values.

### What the Hosted Backend Exposes

The hosted backend is limited to read-only access for:

- `public.transfer_course_search`
- `public.online_course_discovery_search`
- `public.search_online_course_discovery(q, max_results)`
- supporting read tables needed by the search RPC: `schools`, `online_courses`, and `online_program_pages`

It does not expose write access to crawl tasks, raw imports, AI judgments, logs, or private credentials.

Maintainers can still change the hosted data through trusted backend credentials. The read-only deployment setup only limits what browser users can do with the public Supabase key.

### If No Hosted Supabase Values Are Provided

The frontend needs Supabase environment variables to show real search results. Without them, the project can still build, but the search UI cannot query the hosted dataset. To run with an independent database, create a Supabase project and apply the SQL in `supabase/schema.safe.sql`, then optionally load `supabase/seed.example.sql`.

### 2. Install Frontend Dependencies

```powershell
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### 3. Install Backend Dependencies

```powershell
.\.venv\Scripts\pip.exe install -r backend\requirements.txt
```

Run the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8010
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8010/health
```

## Supabase

GitHub-safe SQL lives in [supabase/](supabase/):

- [schema.safe.sql](supabase/schema.safe.sql): reference schema, view, RPC, indexes, and read-only RLS policies.
- [security_hardening.sql](supabase/security_hardening.sql): optional permission tightening for public projects.
- [seed.example.sql](supabase/seed.example.sql): tiny demo seed with public course examples.

Do not commit production dumps or secrets. See [supabase/README.md](supabase/README.md) for details.

## Data Policy

This repository intentionally excludes raw production data, including:

- Full OSU transfer-equivalency exports.
- Supabase production dumps.
- Crawled HTML/text, raw model outputs, and crawl logs.
- Local source spreadsheets such as `data/courses.xlsx`.

Small example files in `data/examples/` are included only to demonstrate expected shapes. Verify third-party data licensing before redistributing any real dataset.

## Useful Commands

Import official online catalogs:

```powershell
.\.venv\Scripts\python.exe scripts\import_official_online_catalogs.py --school asu
.\.venv\Scripts\python.exe scripts\import_official_online_catalogs.py --school byu
.\.venv\Scripts\python.exe scripts\import_official_online_catalogs.py --school cscc
```

Run discovery for one school:

```powershell
.\.venv\Scripts\python.exe scripts\run_online_discovery_batch.py --school "Columbus State Community College" --max-pages 40 --max-depth 2
```

Run frontend checks:

```powershell
cd web
npm run lint
npm run build
```

## Security Notes

- Browser code must use only a Supabase publishable or anon key.
- Keep `DATABASE_URL` and search-provider keys on the server side.
- Do not expose Supabase `service_role` keys.
- Frontend-readable tables should have RLS enabled and read-only policies.
- Backend scripts should perform writes through trusted server credentials.

## License

Code in this repository is licensed under the MIT License. Data files, third-party course catalogs, and OSU transfer-equivalency records are not covered by the MIT License unless explicitly stated. See [LICENSE](LICENSE).
