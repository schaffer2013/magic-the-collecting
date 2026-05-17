param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path ".env.prod")) {
    Copy-Item ".env.prod.example" ".env.prod"
    Write-Host "Created .env.prod from .env.prod.example"
}

$composeArgs = @("--env-file", ".env.prod", "up", "-d")
if ($Build) {
    $composeArgs += "--build"
}

Write-Host "Starting local production-like stack..."
docker compose @composeArgs

Write-Host ""
Write-Host "Magic: The Collecting is starting."
Write-Host "UI:  http://localhost:8080"
Write-Host "API: http://localhost:8080/docs"
