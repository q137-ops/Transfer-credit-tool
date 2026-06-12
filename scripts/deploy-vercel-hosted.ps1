param(
    [string]$SupabaseUrl = "https://pqgakcbzazunbdtfpkox.supabase.co",

    [string]$SupabaseAnonKey = "sb_publishable_ogfsGZKcfi-_JOD3kdXndQ_ujWAEdxQ"
)

npx vercel@latest --cwd web --prod --yes `
    --build-env NEXT_PUBLIC_SUPABASE_URL=$SupabaseUrl `
    --build-env NEXT_PUBLIC_SUPABASE_ANON_KEY=$SupabaseAnonKey `
    --env NEXT_PUBLIC_SUPABASE_URL=$SupabaseUrl `
    --env NEXT_PUBLIC_SUPABASE_ANON_KEY=$SupabaseAnonKey
