# Transfer Master

Transfer Master is a local-first course discovery and transfer-equivalency tool. It combines OSU-verified transfer course records with crawled online credit-course catalogs so users can find courses that are both transferable and available online.

The project currently includes:

- A Next.js front end for searching verified transfer courses and matched online offerings.
- A FastAPI backend for school-level online course discovery.
- A rule-based crawler and fuzzy matcher that can run without large-model APIs.
- Supabase SQL for schema, search RPCs, RLS, and example seed data.
- Official-catalog import scripts for sources such as ASU ULC, BYU Independent Study, and Columbus State Community College.

## Quick Deploy

Most users do not need to create a Supabase project, run SQL, import data, or run the Python crawler. This deploys the read-only search site against the hosted Supabase dataset maintained for this project.

Prerequisites:

- Git
- Node.js 18 or newer
- A Vercel account

Paste this whole block into PowerShell:

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

If the repository is already cloned, run this from the repository root:

```powershell
.\scripts\deploy-vercel-hosted.ps1
```

The deployed site uses these public read-only frontend values:

```env
NEXT_PUBLIC_SUPABASE_URL=https://pqgakcbzazunbdtfpkox.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_ogfsGZKcfi-_JOD3kdXndQ_ujWAEdxQ
```

These two `NEXT_PUBLIC_` values are browser-visible by design and must be read-only at the database policy level. Do not put `DATABASE_URL`, Supabase `service_role` keys, Tavily/Google search keys, or production data dumps in frontend deployment settings.

For local preview, Vercel Dashboard deployment, and maintainer setup, see [DEPLOY.md](DEPLOY.md).

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

## Security Notes

- Browser code must use only a Supabase publishable or anon key.
- Keep `DATABASE_URL` and search-provider keys on the server side.
- Do not expose Supabase `service_role` keys.
- Frontend-readable tables should have RLS enabled and read-only policies.
- Backend scripts should perform writes through trusted server credentials.

## License

Code in this repository is licensed under the MIT License. Data files, third-party course catalogs, and OSU transfer-equivalency records are not covered by the MIT License unless explicitly stated. See [LICENSE](LICENSE).
