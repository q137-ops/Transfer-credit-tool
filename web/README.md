# Transfer Master Web

This is the Next.js frontend for Transfer Master.

For full project setup, Supabase schema notes, data policy, and licensing, see the root [README.md](../README.md).

## Development

```powershell
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Required Environment

Create `web/.env.local` from `web/.env.local.example`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-publishable-or-anon-key
```

Only public Supabase keys belong in this file. Never put `service_role` keys in frontend code.

## Deploying the Web App

When deploying from GitHub on Vercel, set the project root directory to `web`.

Use the hosted read-only Supabase values supplied by the project maintainer:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-hosted-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-hosted-read-only-anon-or-publishable-key
```

These browser-visible values only provide read access to the public search dataset. Crawling, importing, and database writes require private server-side credentials and are not available from the deployed frontend.
