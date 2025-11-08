# Run migrations from inside Docker container (PowerShell)
# Usage: .\scripts\migrate-docker.ps1

$migrationsDir = Join-Path $PSScriptRoot "..\supabase\migrations"
$files = Get-ChildItem -Path $migrationsDir -Filter "*.sql" | Sort-Object Name

Write-Host "Found $($files.Count) migration files" -ForegroundColor Cyan

foreach ($file in $files) {
    Write-Host "Running migration: $($file.Name)" -ForegroundColor Yellow
    $sql = Get-Content $file.FullName -Raw
    $output = $sql | docker exec -i lola-postgres psql -U lola -d lola_db 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Successfully applied: $($file.Name)" -ForegroundColor Green
    } else {
        # Some errors are expected (like tables already existing or users table not existing)
        if ($output -match "ERROR.*does not exist.*users") {
            Write-Host "Skipped (users table dependency): $($file.Name)" -ForegroundColor Yellow
        } elseif ($output -match "already exists") {
            Write-Host "Already exists: $($file.Name)" -ForegroundColor Yellow
        } else {
            Write-Host "Error applying $($file.Name)" -ForegroundColor Red
            Write-Host $output
        }
    }
}

Write-Host ""
Write-Host "Migration complete!" -ForegroundColor Cyan
