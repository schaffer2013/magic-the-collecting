param(
    [switch]$Seed
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if ($Seed) {
    python -m registration_service.seed
}

Write-Host "Starting local host-run worker..."
$worker = Start-Process `
    -FilePath "python" `
    -ArgumentList "-m", "registration_service.worker" `
    -PassThru `
    -WindowStyle Hidden

Write-Host "Starting local host-run web app..."
Write-Host "UI:  http://localhost:8080"
Write-Host "API: http://localhost:8080/docs"
Write-Host "Press Ctrl+C to stop both the web app and worker."
try {
    python -m uvicorn registration_service.main:app --host 0.0.0.0 --port 8080
}
finally {
    if (-not $worker.HasExited) {
        Stop-Process -Id $worker.Id
    }
}
