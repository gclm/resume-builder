# author: jf
[CmdletBinding()]
param(
    [int]$Port = 8999
)

$ErrorActionPreference = "Stop"

function Get-ListeningPids {
    param(
        [int]$TargetPort
    )

    $matched = @(
        netstat -ano -p tcp |
            Select-String -Pattern "^\s*TCP\s+\S+:$TargetPort\s+\S+\s+LISTENING\s+\d+\s*$"
    )

    if ($matched.Count -eq 0) {
        return @()
    }

    return @(
        $matched |
            ForEach-Object {
                $columns = ($_ -split "\s+") | Where-Object { $_ -ne "" }
                [int]$columns[-1]
            } |
            Sort-Object -Unique
    )
}

Write-Host "Inspecting port $Port listeners..." -ForegroundColor Cyan
$listenerPids = @(Get-ListeningPids -TargetPort $Port)

if ($listenerPids.Count -eq 0) {
    Write-Host "No listener found on port $Port."
    exit 0
}

$missingProcess = $false

foreach ($targetPid in $listenerPids) {
    try {
        $process = Get-Process -Id $targetPid -ErrorAction Stop
        Write-Host ("Stopping PID {0} ({1})" -f $targetPid, $process.ProcessName) -ForegroundColor Yellow
        Stop-Process -Id $targetPid -Force -ErrorAction Stop
    }
    catch {
        $missingProcess = $true
        Write-Warning "PID $targetPid is not visible in the current process list. The port listener may be stale."
    }
}

Start-Sleep -Seconds 1

$remainingPids = @(Get-ListeningPids -TargetPort $Port)

if ($remainingPids.Count -gt 0) {
    Write-Warning "Port $Port is still busy."
    foreach ($remainingPid in $remainingPids) {
        $remainingProcess = Get-Process -Id $remainingPid -ErrorAction SilentlyContinue
        if ($null -ne $remainingProcess) {
            Write-Warning ("Remaining listener PID={0} Process={1}" -f $remainingPid, $remainingProcess.ProcessName)
        }
        else {
            Write-Warning ("Remaining listener PID={0}" -f $remainingPid)
        }
    }
    if ($missingProcess) {
        Write-Warning "The fastest cleanup is a Windows reboot before restarting the backend."
    }
    exit 1
}

Write-Host "Port $Port is free." -ForegroundColor Green
