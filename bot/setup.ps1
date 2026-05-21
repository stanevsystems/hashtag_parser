# Quick setup (Windows). Messages in English to avoid encoding issues in PowerShell 5.1.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path venv)) {
    python -m venv venv
}
& .\venv\Scripts\pip.exe install -r requirements.txt
& .\venv\Scripts\python.exe -c "import python_socks; print('python-socks OK')"

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env - edit API_ID, CHAT_IDS, TELEGRAM_ADMIN_IDS"
}

Write-Host "Done. Run: .\run.ps1 --test"
