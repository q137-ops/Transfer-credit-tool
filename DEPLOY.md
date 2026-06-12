# One-Command Deployment

This deployment path uses the hosted read-only Supabase backend for Transfer Master. Users do not need to create Supabase tables, run SQL, import data, or run the Python crawler.

The deployed site is a read-only search UI. It can query the hosted course dataset, but it cannot modify data or run imports.

## Required Public Values

Ask the project maintainer for these two public frontend values:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-hosted-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-hosted-read-only-anon-or-publishable-key
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

Replace the two placeholder values, then paste the whole block into PowerShell:

```powershell
$repo = "https://github.com/q137-ops/Transfer-credit-tool.git"
$supabaseUrl = "PASTE_HOSTED_SUPABASE_URL"
$supabaseAnonKey = "PASTE_HOSTED_READ_ONLY_ANON_OR_PUBLISHABLE_KEY"

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
.\scripts\deploy-vercel-hosted.ps1 `
  -SupabaseUrl "PASTE_HOSTED_SUPABASE_URL" `
  -SupabaseAnonKey "PASTE_HOSTED_READ_ONLY_ANON_OR_PUBLISHABLE_KEY"
```

## Run Locally from PowerShell

Replace the two placeholder values, then paste the whole block into PowerShell:

```powershell
$repo = "https://github.com/q137-ops/Transfer-credit-tool.git"
$supabaseUrl = "PASTE_HOSTED_SUPABASE_URL"
$supabaseAnonKey = "PASTE_HOSTED_READ_ONLY_ANON_OR_PUBLISHABLE_KEY"

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
