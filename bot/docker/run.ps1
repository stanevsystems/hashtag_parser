param(
    [ValidateSet("up", "down", "logs", "login", "test", "restart")]
    [string]$Action = "up"
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

switch ($Action) {
    "up"      { docker compose up -d; docker compose logs -f --tail 50 }
    "down"    { docker compose down }
    "logs"    { docker compose logs -f --tail 100 }
    "restart" { docker compose restart; docker compose logs -f --tail 50 }
    "login"   { docker compose run --rm -it bot python main.py --login }
    "test"    { docker compose run --rm bot python main.py --test }
    default   { Write-Host "Usage: .\docker\run.ps1 [up|down|logs|login|test|restart]" }
}
