param (
    [string]$FilePath = "data\courses.xlsx"
)

Write-Host "Importing Excel file: $FilePath"

.\.venv\Scripts\python.exe scripts\import_xlsx_to_supabase.py $FilePath

if ($LASTEXITCODE -ne 0) {
    Write-Host "Import failed."
    exit $LASTEXITCODE
}

Write-Host "Import completed successfully."