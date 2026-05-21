# Always use project venv (avoids system Python + old Telethon mismatch)
$ErrorActionPreference = "Stop"
$py = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "venv missing. Run: PowerShell -ExecutionPolicy Bypass -File .\setup.ps1"
    exit 1
}
& $py -c "import python_socks" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing python-socks into venv..."
    & (Join-Path $PSScriptRoot "venv\Scripts\pip.exe") install "python-socks[asyncio]"
}
if ($args.Count -eq 0) {
    Write-Host "Starting bot (Ctrl+C to stop). Commands: --test, --login"
}
& $py (Join-Path $PSScriptRoot "main.py") @args
