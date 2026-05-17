param(
    [switch]$SkipEngineCatalog
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Initializing git submodules..."
git submodule update --init --recursive

Write-Host "Installing registration service..."
python -m pip install -e ".[dev]"

Write-Host "Installing fuzzy-enigma engine..."
python -m pip install -e ".\third_party\fuzzy-enigma-card-recognition[ocr]"

if (-not $SkipEngineCatalog) {
    Write-Host "Building fuzzy-enigma local catalog..."
    Push-Location ".\third_party\fuzzy-enigma-card-recognition"
    try {
        python ".\scripts\build_catalog.py" `
            --db-path "..\..\data\card-engine\cards.sqlite3" `
            --source-json "data\catalog\default-cards.json" `
            --download
    }
    finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Local host setup is ready."
Write-Host "Start the app with: .\entrypoints\start-local-host.ps1"
