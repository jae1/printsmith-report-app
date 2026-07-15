param(
    [string]$TaskName = "PrintSmith Report Server Watchdog"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$UpdateRequestFile = Join-Path $RepoRoot ".server_update_requested"
$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if (-not $Task) {
    throw "Scheduled watchdog '$TaskName' is not installed. Run .\run_server_auto_update.ps1 once from an Administrator PowerShell window."
}

Set-Content -Path $UpdateRequestFile -Value (Get-Date -Format "o")
Write-Host "Requested an immediate safe update check from watchdog '$TaskName'."

if ($Task.State -ne "Running") {
    Start-ScheduledTask -TaskName $TaskName
}
Write-Host "The existing report server stays online while the watchdog checks and prepares the update."
Write-Host "Review server_auto_update.log for progress."
