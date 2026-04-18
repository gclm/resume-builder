# author: jf
[CmdletBinding()]
param(
    [int]$Port = 8999
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir "python-ai-backend"
$pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $backendDir)) {
    throw "python-ai-backend directory not found: $backendDir"
}

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Virtual environment not found: $pythonExe"
}

$listeners = @(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Sort-Object OwningProcess -Unique
)

if ($listeners.Count -gt 0) {
    Write-Host "[ERROR] Port $Port is already in use." -ForegroundColor Red
    foreach ($listener in $listeners) {
        Write-Host ("  PID={0} CreatedAt={1}" -f $listener.OwningProcess, $listener.CreationTime)
    }
    Write-Host "[HINT] Run .\stop-python-backend.ps1 -Port $Port first." -ForegroundColor Yellow
    exit 1
}

$env:PYTHONUNBUFFERED = "1"

Push-Location $backendDir
try {
    Write-Host "Starting python-ai-backend on http://127.0.0.1:$Port" -ForegroundColor Green
    & $pythonExe -m uvicorn app.main:app --host 127.0.0.1 --port $Port --app-dir $backendDir
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
