# Entrypoint script to stop the Docker stack for Magic: The Collecting

Write-Host "Stopping Docker containers for Magic: The Collecting..."

# Stop the production-like stack
& docker compose down

Write-Host "All containers stopped."
