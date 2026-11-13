param(
    [ValidateRange(30, 86400)]
    [int]$CheckIntervalSeconds = 600,

    [ValidateRange(2, 300)]
    [int]$HealthCheckIntervalSeconds = 10,

    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._/-]*$')]
    [string]$Branch = "main",

    [ValidateRange(1, 65535)]
    [int]$Port = 8000,

    [string]$TaskName = "PrintSmith Report Server Watchdog",

    [switch]$ScheduledTaskMode,
    [switch]$ReinstallScheduledTask,
    [switch]$Rollback,

    # Internal worker arguments; preparation never runs in the health-check loop.
    [switch]$PrepareReleaseMode,
    [string]$ExpectedRunningRevision = "",
    [string]$BlockedRevision = "",
    [string]$PreparationResultFile
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile = Join-Path $RepoRoot "server_auto_update.log"
$UpdateRequestFile = Join-Path $RepoRoot ".server_update_requested"
$RollbackRequestFile = Join-Path $RepoRoot ".server_rollback_requested"
$ReleaseStateFile = Join-Path $RepoRoot ".server-release.json"
$BaselineFile = Join-Path $RepoRoot ".release-baseline.json"
$ReleasesRoot = Join-Path $RepoRoot ".releases"
$ServerProcess = $null
$ActiveRelease = $null
$PreviousRelease = $null
$PreparationProcess = $null
$PreparationStartedAt = $null
$PreparationOutput = $null
$NextUpdateCheck = Get-Date

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Line = "[$Timestamp] $Message"
    Write-Host $Line
    Add-Content -Path $LogFile -Value $Line
}

function Test-IsAdministrator {
    $Identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $Principal = New-Object Security.Principal.WindowsPrincipal($Identity)
    return $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Install-OrStartScheduledTask {
    if ($ScheduledTaskMode) {
        return $false
    }

    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($ExistingTask -and $ReinstallScheduledTask) {
        Write-Log "Removing existing scheduled task '$TaskName'"
        if ($ExistingTask.State -eq "Running") {
            Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        }
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        $ExistingTask = $null
    }

    if (-not $ExistingTask) {
        if (-not (Test-IsAdministrator)) {
            throw "One-time setup requires an Administrator PowerShell window. Right-click PowerShell, choose 'Run as administrator', open this folder, and run .\run_server_auto_update.ps1"
        }

        $CurrentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        Write-Host "One-time setup for Windows user: $CurrentUser"
        Write-Host "Enter that user's Windows account password. It is stored by Windows Task Scheduler, never in this repository."
        $Credential = Get-Credential -UserName $CurrentUser -Message "Windows credential for the PrintSmith server task"

        $PowerShellExe = Join-Path $PSHOME "powershell.exe"
        $ActionArguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" -ScheduledTaskMode -CheckIntervalSeconds {1} -HealthCheckIntervalSeconds {2} -Branch "{3}" -Port {4} -TaskName "{5}"' -f `
            $PSCommandPath, $CheckIntervalSeconds, $HealthCheckIntervalSeconds, $Branch, $Port, $TaskName

        $Action = New-ScheduledTaskAction `
            -Execute $PowerShellExe `
            -Argument $ActionArguments `
            -WorkingDirectory $RepoRoot

        $Triggers = @(
            New-ScheduledTaskTrigger -AtStartup
            New-ScheduledTaskTrigger -AtLogOn -User $Credential.UserName
        )

        $Settings = New-ScheduledTaskSettingsSet `
            -AllowStartIfOnBatteries `
            -DontStopIfGoingOnBatteries `
            -StartWhenAvailable `
            -RestartCount 999 `
            -RestartInterval (New-TimeSpan -Minutes 2) `
            -ExecutionTimeLimit ([TimeSpan]::Zero) `
            -MultipleInstances IgnoreNew

        $Password = $Credential.GetNetworkCredential().Password
        Register-ScheduledTask `
            -TaskName $TaskName `
            -Description "Keeps the PrintSmith report server running and updates it from GitHub." `
            -Action $Action `
            -Trigger $Triggers `
            -Settings $Settings `
            -User $Credential.UserName `
            -Password $Password `
            -RunLevel Highest `
            -Force | Out-Null
        Clear-Variable Password

        Write-Log "Installed scheduled task '$TaskName' for $($Credential.UserName)"
        $ExistingTask = Get-ScheduledTask -TaskName $TaskName
    }

    if ($ExistingTask.State -ne "Running") {
        Write-Log "Starting scheduled task '$TaskName'"
        Start-ScheduledTask -TaskName $TaskName
    }
    else {
        Write-Log "Scheduled task '$TaskName' is already running"
    }

    Write-Host "The watchdog is owned by Windows Task Scheduler and will start after reboot."
    Write-Host "This setup window can now close."
    return $true
}

function Invoke-RepoCommand {
    param([string[]]$Command)
    Push-Location $RepoRoot
    try {
        $Executable = $Command[0]
        $Arguments = @()
        if ($Command.Length -gt 1) {
            $Arguments = $Command[1..($Command.Length - 1)]
        }
        Get-Command $Executable -ErrorAction Stop | Out-Null
        $ErrorActionPreference = "Continue"
        & $Executable @Arguments | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $($Command -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Get-ListeningProcess {
    $Connection = Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue | Select-Object -First 1

    if (-not $Connection -or -not $Connection.OwningProcess) {
        return $null
    }

    $Process = Get-Process -Id $Connection.OwningProcess -ErrorAction SilentlyContinue
    return $Process
}

function Test-ProcessIdentity {
    param($Process, $Release)
    $Details = Get-CimInstance Win32_Process -Filter "ProcessId = $($Process.Id)"
    if (-not $Details -or $Details.ExecutablePath -ine $Release.python_exe) {
        return $false
    }
    if ($Details.CommandLine -notmatch '(?i)(?:^|[\s"])uvicorn(?:$|[\s"])' -or
        $Details.CommandLine -notmatch '(?i)(?:^|[\s"])main:app(?:$|[\s"])') {
        return $false
    }
    if ($Release.release_path -ine $RepoRoot -or $Details.CommandLine -match '(?:^|\s)--app-dir(?:\s|=)') {
        $AppDirPattern = '(?i)(?:^|\s)--app-dir(?:\s+|=)"?{0}"?(?:$|\s)' -f [regex]::Escape($Release.release_path)
        if ($Details.CommandLine -notmatch $AppDirPattern) { return $false }
    }
    return $true
}

function Test-ReleaseHealth {
    param($Release)
    try {
        $Health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2
        return $Health.status -eq "ok" -and $Health.revision -eq $Release.revision
    }
    catch {
        return $false
    }
}

function Wait-ReleaseHealth {
    param($Release)
    $Deadline = (Get-Date).AddSeconds(30)
    do {
        if (-not (Test-ServerRunning)) {
            throw "Release $($Release.revision) exited during startup"
        }
        if ($Release.revision -eq "legacy-unverified" -or (Test-ReleaseHealth $Release)) {
            return
        }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $Deadline)
    throw "Release $($Release.revision) did not report its expected healthy revision"
}

function Start-ReportServer {
    param($Release)
    $ExistingProcess = Get-ListeningProcess
    if ($ExistingProcess) {
        if (-not (Test-ProcessIdentity $ExistingProcess $Release)) {
            throw "Port $Port belongs to another process; refusing to adopt or stop it"
        }
        $script:ServerProcess = $ExistingProcess
        if ($Release.revision -ne "legacy-unverified" -and -not (Test-ReleaseHealth $Release)) {
            throw "The listener on port $Port does not identify as release $($Release.revision)"
        }
        Write-Log "Adopted verified app process $($ExistingProcess.Id), revision $($Release.revision)"
        return
    }

    if (-not (Test-Path $Release.python_exe) -or -not (Test-Path $Release.release_path)) {
        throw "Release files are missing for $($Release.revision)"
    }
    $OldRevision = $env:PRINTSMITH_RELEASE_REVISION
    try {
        $env:PRINTSMITH_RELEASE_REVISION = $Release.revision
        $Arguments = '-m uvicorn --app-dir "{0}" main:app --host 0.0.0.0 --port {1}' -f $Release.release_path, $Port
        Write-Log "Starting release $($Release.revision) on 0.0.0.0:$Port"
        $script:ServerProcess = Start-Process `
            -FilePath $Release.python_exe `
            -ArgumentList $Arguments `
            -WorkingDirectory $RepoRoot `
            -PassThru `
            -NoNewWindow
    }
    finally {
        $env:PRINTSMITH_RELEASE_REVISION = $OldRevision
    }
}

function Stop-ReportServer {
    if ($script:ServerProcess) {
        $script:ServerProcess.Refresh()
        if (-not $script:ServerProcess.HasExited) {
            Write-Log "Stopping server process $($script:ServerProcess.Id)"
            Stop-Process -Id $script:ServerProcess.Id -Force
            $script:ServerProcess.WaitForExit()
        }
    }
    $script:ServerProcess = $null
}

function Test-ServerRunning {
    if (-not $script:ServerProcess) {
        return $false
    }

    $script:ServerProcess.Refresh()
    return -not $script:ServerProcess.HasExited
}

function Save-ReleaseState {
    param($Release, $Previous, [string]$State = "active")
    $PreviousData = $null
    if ($Previous) {
        $PreviousData = @{
            revision = $Previous.revision
            release_path = $Previous.release_path
            python_exe = $Previous.python_exe
        }
    }
    $Data = @{
        revision = $Release.revision
        release_path = $Release.release_path
        python_exe = $Release.python_exe
        previous = $PreviousData
        state = $State
        blocked_revision = $script:BlockedRevision
    }
    $TemporaryFile = "$ReleaseStateFile.tmp"
    $Data | ConvertTo-Json -Depth 5 | Set-Content -Path $TemporaryFile -Encoding UTF8
    if (Test-Path $ReleaseStateFile) {
        [IO.File]::Replace($TemporaryFile, $ReleaseStateFile, [NullString]::Value)
    }
    else {
        [IO.File]::Move($TemporaryFile, $ReleaseStateFile)
    }
}

function Invoke-ReleaseSwitch {
    param($Candidate, [switch]$ManualRollback)
    $OldRelease = $script:ActiveRelease
    $OldPrevious = $script:PreviousRelease
    $script:BlockedRevision = ""
    if ($ManualRollback -and $OldRelease) {
        $script:BlockedRevision = $OldRelease.revision
    }
    # A pending record lets a restarted watchdog validate or roll back an interrupted switch.
    Save-ReleaseState $Candidate $OldRelease "pending"
    try {
        Stop-ReportServer
        Start-ReportServer $Candidate
        Wait-ReleaseHealth $Candidate
        $script:ActiveRelease = $Candidate
        $script:PreviousRelease = $OldRelease
        Save-ReleaseState $Candidate $OldRelease
        Write-Log "Release $($Candidate.revision) is healthy and active"
    }
    catch {
        $Failure = $_.Exception.Message
        Stop-ReportServer
        $script:BlockedRevision = $Candidate.revision
        $script:ActiveRelease = $OldRelease
        $script:PreviousRelease = $OldPrevious
        if ($OldRelease) {
            Start-ReportServer $OldRelease
            Wait-ReleaseHealth $OldRelease
            $State = "active"
            if ($OldRelease.revision -eq "legacy-unverified") { $State = "legacy" }
            Save-ReleaseState $OldRelease $OldPrevious $State
            Write-Log "Rolled back to $($OldRelease.revision); rejected $($Candidate.revision): $Failure"
        }
        else {
            Remove-Item $ReleaseStateFile -Force -ErrorAction SilentlyContinue
        }
        throw "Release validation failed: $Failure"
    }
}

function Prepare-Release {
    Write-Host "Checking origin/$Branch for a candidate release"
    Invoke-RepoCommand @("git", "fetch", "origin", $Branch)
    $RemoteHead = (& git -C $RepoRoot rev-parse "origin/$Branch").Trim()
    if ($LASTEXITCODE -ne 0 -or $RemoteHead -notmatch '^[0-9a-f]{40}$') {
        throw "Unable to read origin/$Branch"
    }
    if ($RemoteHead -eq $ExpectedRunningRevision -or $RemoteHead -eq $BlockedRevision) {
        return $null
    }
    if (-not (Test-Path $BaselineFile)) {
        throw "Approved baseline missing: $BaselineFile. Review and capture it before releasing; the working server stays online."
    }

    $BuildId = "$RemoteHead-$([guid]::NewGuid().ToString('N'))"
    $ReleasePath = Join-Path $ReleasesRoot $BuildId
    $Archive = Join-Path $ReleasesRoot "$BuildId.zip"
    Invoke-RepoCommand @("git", "archive", "--format=zip", "--output", $Archive, $RemoteHead)
    Expand-Archive -Path $Archive -DestinationPath $ReleasePath -Force
    Remove-Item $Archive -Force
    $PythonExe = Join-Path $ReleasePath "venv\Scripts\python.exe"
    if (-not (Test-Path $PythonExe)) {
        Invoke-RepoCommand @("python", "-m", "venv", (Join-Path $ReleasePath "venv"))
    }
    Invoke-RepoCommand @($PythonExe, "-m", "pip", "install", "-r", (Join-Path $ReleasePath "requirements.txt"))
    # The checker runs candidate code while runtime JSON stays in the original working directory.
    Invoke-RepoCommand @($PythonExe, (Join-Path $ReleasePath "release_check.py"), "--baseline", $BaselineFile)
    return [pscustomobject]@{ revision = $RemoteHead; release_path = $ReleasePath; python_exe = $PythonExe }
}

function Start-ReleasePreparation {
    New-Item -ItemType Directory -Path $ReleasesRoot -Force | Out-Null
    $RequestId = [guid]::NewGuid().ToString("N")
    $script:PreparationOutput = Join-Path $ReleasesRoot "prepared-$RequestId.json"
    $LogPrefix = Join-Path $ReleasesRoot "prepare-$RequestId"
    $Revision = ""
    if ($script:ActiveRelease) { $Revision = $script:ActiveRelease.revision }
    $Arguments = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" -PrepareReleaseMode -Branch "{1}" -PreparationResultFile "{2}"' -f `
        $PSCommandPath, $Branch, $script:PreparationOutput
    if ($Revision) { $Arguments += ' -ExpectedRunningRevision "{0}"' -f $Revision }
    if ($script:BlockedRevision) { $Arguments += ' -BlockedRevision "{0}"' -f $script:BlockedRevision }
    $script:PreparationProcess = Start-Process `
        -FilePath (Join-Path $PSHOME "powershell.exe") `
        -ArgumentList $Arguments `
        -WorkingDirectory $RepoRoot `
        -RedirectStandardOutput "$LogPrefix.stdout.log" `
        -RedirectStandardError "$LogPrefix.stderr.log" `
        -PassThru -WindowStyle Hidden
    $script:PreparationStartedAt = Get-Date
    Write-Log "Preparing release separately; health checks continue. Details: $LogPrefix.*.log"
}

function Stop-ReleasePreparation {
    if ($script:PreparationProcess) {
        $script:PreparationProcess.Refresh()
        if (-not $script:PreparationProcess.HasExited) {
            & taskkill.exe /PID $script:PreparationProcess.Id /T /F | Out-Host
            if ($LASTEXITCODE -ne 0) { throw "Could not stop the release preparation process tree" }
        }
        $script:PreparationProcess.Dispose()
        $script:PreparationProcess = $null
    }
}

function Complete-ReleasePreparation {
    if (-not $script:PreparationProcess) { return }
    $script:PreparationProcess.Refresh()
    if (-not $script:PreparationProcess.HasExited) {
        if ((Get-Date) -gt $script:PreparationStartedAt.AddMinutes(30)) {
            Stop-ReleasePreparation
            throw "Release preparation exceeded 30 minutes; keeping the current server online"
        }
        return
    }
    $ExitCode = $script:PreparationProcess.ExitCode
    $script:PreparationProcess.Dispose()
    $script:PreparationProcess = $null
    $script:NextUpdateCheck = (Get-Date).AddSeconds($CheckIntervalSeconds)
    if ($ExitCode -ne 0 -or -not (Test-Path $script:PreparationOutput)) {
        throw "Release preparation or regression checks failed; keeping the current server online. See .releases preparation logs."
    }
    $Candidate = Get-Content $script:PreparationOutput -Raw | ConvertFrom-Json
    Remove-Item $script:PreparationOutput -Force
    if ($Candidate) { Invoke-ReleaseSwitch $Candidate }
}

function Invoke-WatchdogTick {
    if ($script:ActiveRelease -and -not (Test-ServerRunning)) {
        Write-Log "Server is not running; restarting release $($script:ActiveRelease.revision) immediately"
        Start-ReportServer $script:ActiveRelease
        Wait-ReleaseHealth $script:ActiveRelease
    }
    if (Test-Path $RollbackRequestFile) {
        Remove-Item $RollbackRequestFile -Force
        Stop-ReleasePreparation
        if ($script:PreviousRelease) {
            Invoke-ReleaseSwitch $script:PreviousRelease -ManualRollback
        }
        else { Write-Log "Rollback requested, but no previous healthy release is recorded" }
        $script:NextUpdateCheck = (Get-Date).AddSeconds($CheckIntervalSeconds)
    }
    if (Test-Path $UpdateRequestFile) {
        Remove-Item $UpdateRequestFile -Force
        $script:BlockedRevision = ""
        $script:NextUpdateCheck = Get-Date
    }
    Complete-ReleasePreparation
    if (-not $script:PreparationProcess -and (Get-Date) -ge $script:NextUpdateCheck) {
        Start-ReleasePreparation
    }
}

function Restore-ServingRelease {
    if (-not (Test-Path $ReleaseStateFile)) {
        if (Get-ListeningProcess) {
            $Legacy = [pscustomobject]@{
                revision = "legacy-unverified"
                release_path = $RepoRoot
                python_exe = Join-Path $RepoRoot "venv\Scripts\python.exe"
            }
            Start-ReportServer $Legacy
            $script:ActiveRelease = $Legacy
            Save-ReleaseState $Legacy $null "legacy"
        }
        return
    }
    $Saved = Get-Content $ReleaseStateFile -Raw | ConvertFrom-Json
    $script:ActiveRelease = $Saved
    $script:PreviousRelease = $Saved.previous
    $script:BlockedRevision = $Saved.blocked_revision
    try {
        Start-ReportServer $Saved
        Wait-ReleaseHealth $Saved
        if ($Saved.state -eq "pending") { Save-ReleaseState $Saved $Saved.previous }
    }
    catch {
        if (-not $Saved.previous) { throw }
        Stop-ReportServer
        $script:BlockedRevision = $Saved.revision
        $script:ActiveRelease = $Saved.previous
        $script:PreviousRelease = $null
        Start-ReportServer $script:ActiveRelease
        Wait-ReleaseHealth $script:ActiveRelease
        $State = "active"
        if ($script:ActiveRelease.revision -eq "legacy-unverified") { $State = "legacy" }
        Save-ReleaseState $script:ActiveRelease $null $State
        Write-Log "Recovered previous healthy release $($script:ActiveRelease.revision)"
    }
}

if ($PrepareReleaseMode) {
    try {
        $Candidate = Prepare-Release
        ConvertTo-Json -InputObject $Candidate | Set-Content -Path $PreparationResultFile -Encoding UTF8
        exit 0
    }
    catch {
        Write-Error $_ -ErrorAction Continue
        exit 1
    }
}

if ($Rollback) {
    $Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $Task) { throw "Install the scheduled watchdog before requesting a rollback" }
    Set-Content -Path $RollbackRequestFile -Value (Get-Date -Format "o")
    if ($Task.State -ne "Running") { Start-ScheduledTask -TaskName $TaskName }
    Write-Host "Rollback requested; the watchdog will restore the previous healthy release."
    exit 0
}

if (Install-OrStartScheduledTask) { exit 0 }

try {
    Write-Log "Scheduled watchdog started from $RepoRoot"
    Restore-ServingRelease
    while ($true) {
        try {
            Invoke-WatchdogTick
        }
        catch {
            Write-Log "Watchdog action failed: $($_.Exception.Message)"
            $script:NextUpdateCheck = (Get-Date).AddMinutes(2)
        }
        Start-Sleep -Seconds $HealthCheckIntervalSeconds
    }
}
catch {
    Write-Log "Watchdog failed: $($_.Exception.Message)"
    throw
}
finally {
    Stop-ReleasePreparation
    # A restarted watchdog validates and adopts the healthy serving release.
    Write-Log "Watchdog process stopped; Task Scheduler will restart it"
}
