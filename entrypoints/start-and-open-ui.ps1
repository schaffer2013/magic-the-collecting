# Entrypoint script to set up and launch the production-like Docker stack and open the web UI

# Copy environment templates if needed
if (-not (Test-Path ".env.prod")) {
    Copy-Item ".env.prod.example" ".env.prod"
}
if (-not (Test-Path ".env.test")) {
    Copy-Item ".env.test.example" ".env.test"
}


# Safe start: stop containers if running
Write-Host "Stopping any running Docker containers for Magic: The Collecting..."
& .\entrypoints\stop-local-host.ps1

# Build and start the Docker stack
Write-Host "Building and starting Docker containers..."
& .\entrypoints\start-local.ps1 -Build

# Wait for the web service to be available
$maxAttempts = 30
$attempt = 0
$serviceUp = $false
while ($attempt -lt $maxAttempts -and -not $serviceUp) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080" -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) {
            $serviceUp = $true
        }
    } catch {
        Start-Sleep -Seconds 2
        $attempt++
    }
}

if ($serviceUp) {
    Write-Host "Web UI is up! Opening in browser..."
    Start-Process "http://localhost:8080"
} else {
    Write-Host "Web UI did not become available in time. Please check Docker logs."
}
