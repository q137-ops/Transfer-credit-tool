# One-Command Deployment

This deployment path uses the hosted read-only Supabase backend for Transfer Master. Users do not need to create Supabase tables, run SQL, import data, or run the Python crawler.

The deployed site is a read-only search UI. It can query the hosted course dataset, but it cannot modify data or run imports.

## Required Public Values

This hosted deployment uses these public frontend values:

```env
NEXT_PUBLIC_SUPABASE_URL=https://pqgakcbzazunbdtfpkox.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_ogfsGZKcfi-_JOD3kdXndQ_ujWAEdxQ
```

Do not request or use:

- `DATABASE_URL`
- Supabase `service_role` key
- Tavily, Google, or other crawler/search API keys
- private import spreadsheets or database dumps

## Prerequisites

Install or sign in to:

- Git
- Node.js 18 or newer
- A Vercel account

The first Vercel command may ask you to log in.

## Deploy to Vercel from PowerShell

Paste the whole block into PowerShell:

```powershell
$repo = "https://github.com/q137-ops/Transfer-credit-tool.git"
$supabaseUrl = "https://pqgakcbzazunbdtfpkox.supabase.co"
$supabaseAnonKey = "sb_publishable_ogfsGZKcfi-_JOD3kdXndQ_ujWAEdxQ"

git clone $repo
Set-Location Transfer-credit-tool

npx vercel@latest --cwd web --prod --yes `
  --build-env NEXT_PUBLIC_SUPABASE_URL=$supabaseUrl `
  --build-env NEXT_PUBLIC_SUPABASE_ANON_KEY=$supabaseAnonKey `
  --env NEXT_PUBLIC_SUPABASE_URL=$supabaseUrl `
  --env NEXT_PUBLIC_SUPABASE_ANON_KEY=$supabaseAnonKey
```

The command uses Vercel's documented `--cwd`, `--yes`, `--prod`, `--build-env`, and `--env` options.

If the repository is already cloned, run this from the repository root instead:

```powershell
.\scripts\deploy-vercel-hosted.ps1
```

## Run Locally from PowerShell

Paste the whole block into PowerShell:

```powershell
$repo = "https://github.com/q137-ops/Transfer-credit-tool.git"
$supabaseUrl = "https://pqgakcbzazunbdtfpkox.supabase.co"
$supabaseAnonKey = "sb_publishable_ogfsGZKcfi-_JOD3kdXndQ_ujWAEdxQ"

git clone $repo
Set-Location Transfer-credit-tool

@"
NEXT_PUBLIC_SUPABASE_URL=$supabaseUrl
NEXT_PUBLIC_SUPABASE_ANON_KEY=$supabaseAnonKey
"@ | Set-Content web\.env.local

Set-Location web
npm install
npm run dev
```

Open <http://localhost:3000>.

## Deploy from the Vercel Dashboard

1. Import `q137-ops/Transfer-credit-tool` into Vercel.
2. Set **Root Directory** to `web`.
3. Add the two public environment variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
4. Deploy.

## What This Deployment Can and Cannot Do

Can:

- Search OSU-verified transfer courses.
- Show matched online course price, credits, and course URLs.
- Use the hosted Supabase dataset without running SQL.

Cannot:

- Import new data.
- Run crawlers.
- Write to Supabase.
- Access private logs, raw crawl output, or backend credentials.

Maintainers update the hosted data separately using trusted server-side credentials.

## What the Hosted Backend Exposes

The hosted backend is limited to read-only access for:

- `public.transfer_course_search`
- `public.online_course_discovery_search`
- `public.search_online_course_discovery(q, max_results)`
- supporting read tables needed by the search RPC: `schools`, `online_courses`, and `online_program_pages`

It does not expose write access to crawl tasks, raw imports, AI judgments, logs, or private credentials.

Maintainers can still change the hosted data through trusted backend credentials. The read-only deployment setup only limits what browser users can do with the public Supabase key.

## Local Setup for Maintainers

This section is for maintainers who need to run the crawler, imports, backend API, or local checks. Users who only want the public read-only search site should use the one-command deployment above.

### Environment Files

Copy the example env files and fill in private maintainer values:

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
NEXT_PUBLIC_SUPABASE_URL=https://pqgakcbzazunbdtfpkox.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_ogfsGZKcfi-_JOD3kdXndQ_ujWAEdxQ
```

Never commit real `.env` files. Keep `DATABASE_URL`, Supabase `service_role`, and search-provider keys server-side only.

### Frontend

```powershell
Set-Location web
npm install
npm run dev
```

Open <http://localhost:3000>.

Run frontend checks:

```powershell
Set-Location web
npm run lint
npm run build
```

### Backend API

Install backend dependencies:

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

### Data Maintenance Commands

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

### Independent Supabase Setup

The hosted dataset is the fastest path. To run with an independent database instead, create a Supabase project, apply `supabase/schema.safe.sql`, optionally load `supabase/seed.example.sql`, and set the frontend to that project's publishable or anon key.
