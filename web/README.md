# Transfer Master Web

This is the Next.js frontend for Transfer Master.

For full project setup, Supabase schema notes, data policy, and licensing, see the root [README.md](../README.md).

## Quick Deploy

Most users can deploy this frontend without creating Supabase tables or running SQL. Use the copy/paste commands in [../DEPLOY.md](../DEPLOY.md) with these public read-only values:

```env
NEXT_PUBLIC_SUPABASE_URL=https://pqgakcbzazunbdtfpkox.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_ogfsGZKcfi-_JOD3kdXndQ_ujWAEdxQ
```

Do not put `DATABASE_URL`, Supabase `service_role`, Tavily, Google, or crawler keys in this frontend.

## Development

```powershell
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Required Environment

Create `web/.env.local` from `web/.env.local.example`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://pqgakcbzazunbdtfpkox.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_ogfsGZKcfi-_JOD3kdXndQ_ujWAEdxQ
```

Only public Supabase keys belong in this file. Never put `service_role` keys in frontend code.

## Deploying the Web App

When deploying from GitHub on Vercel, set the project root directory to `web`. The one-command path in [../DEPLOY.md](../DEPLOY.md) passes the same values through the Vercel CLI.

Use the hosted read-only Supabase values supplied by the project maintainer:

```env
NEXT_PUBLIC_SUPABASE_URL=https://pqgakcbzazunbdtfpkox.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_ogfsGZKcfi-_JOD3kdXndQ_ujWAEdxQ
```

These browser-visible values only provide read access to the public search dataset. Crawling, importing, and database writes require private server-side credentials and are not available from the deployed frontend.
