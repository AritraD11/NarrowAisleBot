<#
.SYNOPSIS
    Incremental download of NarrowAisleBot bench telemetry CSVs from the Pi.

.DESCRIPTION
    Lists *.csv in ~/aislebot_logs on the Pi, compares against what's
    already in the local destination folder, and scp's down only the
    files that are missing. Safe to run repeatedly — already-downloaded
    files are never re-copied.

    Requires the Windows OpenSSH client (ssh.exe / scp.exe) — already
    confirmed working if `scp aritra@10.42.0.1:...` has worked for you
    before. No rsync, no extra install.

.PARAMETER LocalDir
    Where new CSVs land. Defaults to the calibration working folder.

.PARAMETER Remote
    SSH target for the Pi. Defaults to the fixed AisleBot-Pi AP address.

.PARAMETER RemoteDir
    Remote folder to sync from (relative to the Pi's home directory).

.EXAMPLE
    .\sync_bench_logs.ps1
        Sync everything new into the default folder.

.EXAMPLE
    .\sync_bench_logs.ps1 -LocalDir "D:\backup\aislebot_logs"
        Sync into a different local folder.
#>

param(
    [string]$LocalDir = "C:\Users\aritradas\Documents\mecanum robot ROS2\Encoder readings\Reading\Ground Test",
    [string]$Remote   = "aritra@10.42.0.1",
    [string]$RemoteDir = "aislebot_logs"
)

if (-not (Test-Path $LocalDir)) {
    New-Item -ItemType Directory -Path $LocalDir -Force | Out-Null
    Write-Host "Created $LocalDir"
}

Write-Host "Listing remote files on $Remote..."
$remoteListing = ssh $Remote "ls -1 $RemoteDir/*.csv 2>/dev/null"
if ($LASTEXITCODE -ne 0 -or -not $remoteListing) {
    Write-Host "Could not list remote files. Is the Pi reachable at $Remote right now?" -ForegroundColor Red
    exit 1
}

$remoteFiles = $remoteListing | ForEach-Object { Split-Path $_ -Leaf } | Where-Object { $_ -match '\.csv$' }
$localFiles  = Get-ChildItem -Path $LocalDir -Filter *.csv -ErrorAction SilentlyContinue |
               Select-Object -ExpandProperty Name

$missing = $remoteFiles | Where-Object { $_ -notin $localFiles }

if (-not $missing -or $missing.Count -eq 0) {
    Write-Host "Already up to date — nothing new on the Pi." -ForegroundColor Green
    exit 0
}

Write-Host "$($missing.Count) new file(s) to download:"
$missing | ForEach-Object { Write-Host "  $_" }
Write-Host ""

$ok = 0
foreach ($f in $missing) {
    Write-Host "Downloading $f ..." -NoNewline
    scp "${Remote}:${RemoteDir}/$f" "$LocalDir\" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " done" -ForegroundColor Green
        $ok++
    } else {
        Write-Host " FAILED" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Downloaded $ok / $($missing.Count) file(s) into $LocalDir"
