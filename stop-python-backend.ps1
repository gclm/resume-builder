# author: jf
[CmdletBinding()]
param(
    [int]$Port = 8999
)

$ErrorActionPreference = "Stop"
$listeners = @(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Sort-Object OwningProcess -Unique
)

if ($listeners.Count -eq 0) {
    Write-Host "No listener found on port $Port."
    exit 0
}

$missingProcess = $false

foreach ($listener in $listeners) {
    $pid = [int]$listener.OwningProcess
    try {
        $process = Get-Process -Id $pid -ErrorAction Stop
        Write-Host ("Stopping PID {0} ({1})" -f $pid, $process.ProcessName) -ForegroundColor Yellow
        Stop-Process -Id $pid -Force -ErrorAction Stop
    }
    catch {
        $missingProcess = $true
        Write-Warning "PID $pid is not visible in the current process list. The port listener may be stale."
    }
}

Start-Sleep -Seconds 1

$remaining = @(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Sort-Object OwningProcess -Unique
)

if ($remaining.Count -gt 0) {
    Write-Warning "Port $Port is still busy."
    foreach ($listener in $remaining) {
        Write-Warning ("Remaining listener PID={0} CreatedAt={1}" -f $listener.OwningProcess, $listener.CreationTime)
    }
    if ($missingProcess) {
        Write-Warning "The fastest cleanup is a Windows reboot before restarting the backend."
    }
    exit 1
}

Write-Host "Port $Port is free." -ForegroundColor Green
