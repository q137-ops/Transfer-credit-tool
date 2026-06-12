param(
    [Parameter(Mandatory = $true)]
    [string]$SupabaseUrl,

    [Parameter(Mandatory = $true)]
    [string]$SupabaseAnonKey
)

npx vercel@latest --cwd web --prod --yes `
    --build-env NEXT_PUBLIC_SUPABASE_URL=$SupabaseUrl `
    --build-env NEXT_PUBLIC_SUPABASE_ANON_KEY=$SupabaseAnonKey `
    --env NEXT_PUBLIC_SUPABASE_URL=$SupabaseUrl `
    --env NEXT_PUBLIC_SUPABASE_ANON_KEY=$SupabaseAnonKey
