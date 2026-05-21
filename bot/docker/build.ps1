# Build Docker image (run from bot/ or pass -Context)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

docker build -t hashtag-ideas-bot:latest .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "OK: hashtag-ideas-bot:latest"
Write-Host "Next: copy .env, put SSH key in secrets/, then:"
Write-Host "  docker compose run --rm -it bot python main.py --login"
Write-Host "  docker compose up -d"
