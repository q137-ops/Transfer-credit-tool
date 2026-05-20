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
