param(
    [ValidateRange(30, 86400)]
    [int]$CheckIntervalSeconds = 600,

    [ValidateRange(2, 300)]
    [int]$HealthCheckIntervalSeconds = 10,

    [string]$Branch = "main",

    [ValidateRange(1, 65535)]
    [int]$Port = 8000,

    [string]$TaskName = "PrintSmith Report Server Watchdog",

    [switch]$ScheduledTaskMode,
    [switch]$ReinstallScheduledTask
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile = Join-Path $RepoRoot "server_auto_update.log"
$UpdateRequestFile = Join-Path $RepoRoot ".server_update_requested"
$ServerProcess = $null
$RunningRevision = $null

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
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $($Command -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Ensure-Venv {
    $PythonExe = Join-Path $RepoRoot "venv\Scripts\python.exe"
    if (-not (Test-Path $PythonExe)) {
        Write-Log "Creating virtual environment"
        Invoke-RepoCommand @("python", "-m", "venv", "venv")
    }
    return $PythonExe
}

function Install-Dependencies {
    $PythonExe = Ensure-Venv
    Write-Log "Installing dependencies"
    Invoke-RepoCommand @($PythonExe, "-m", "pip", "install", "-r", "requirements.txt")
}

function Get-RepositoryRevision {
    $Revision = (& git -C $RepoRoot rev-parse HEAD)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read the local Git revision"
    }
    return $Revision.Trim()
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

function Start-ReportServer {
    $ExistingProcess = Get-ListeningProcess
    if ($ExistingProcess) {
        $script:ServerProcess = $ExistingProcess
        Write-Log "Adopted existing process $($ExistingProcess.Id) listening on port $Port"
        return
    }

    $PythonExe = Ensure-Venv
    Write-Log "Starting server on 0.0.0.0:$Port"
    $script:ServerProcess = Start-Process `
        -FilePath $PythonExe `
        -ArgumentList @("-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$Port") `
        -WorkingDirectory $RepoRoot `
        -PassThru `
        -NoNewWindow

    Start-Sleep -Seconds 2
    $script:ServerProcess.Refresh()
    if ($script:ServerProcess.HasExited) {
        throw "Server exited immediately with code $($script:ServerProcess.ExitCode)"
    }
    Write-Log "Server process started with ID $($script:ServerProcess.Id)"
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

function Update-RepositoryIfAvailable {
    Write-Log "Checking origin/$Branch for updates"
    Invoke-RepoCommand @("git", "fetch", "origin", $Branch)

    $RemoteHead = (& git -C $RepoRoot rev-parse "origin/$Branch").Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read origin/$Branch"
    }

    if ($RemoteHead -eq $script:RunningRevision) {
        Write-Log "No update found"
        return
    }

    Write-Log "Preparing update: $($script:RunningRevision) -> $RemoteHead"

    # Keep the working server alive while Git and dependency preparation run.
    Invoke-RepoCommand @("git", "reset", "--hard", "origin/$Branch")
    Install-Dependencies

    # Only stop the working server after every preparation step succeeds.
    Stop-ReportServer
    Start-ReportServer
    $script:RunningRevision = $RemoteHead
    Write-Log "Update completed successfully at $RemoteHead"
}

if (Install-OrStartScheduledTask) {
    exit 0
}

try {
    Write-Log "Scheduled watchdog started from $RepoRoot"

    Ensure-Venv | Out-Null
    $script:RunningRevision = Get-RepositoryRevision
    try {
        Start-ReportServer
    }
    catch {
        Write-Log "Initial server start failed; repairing dependencies: $($_.Exception.Message)"
        Install-Dependencies
        Start-ReportServer
    }

    $NextUpdateCheck = Get-Date

    while ($true) {
        if (-not (Test-ServerRunning)) {
            Write-Log "Server is not running; restarting immediately"
            Start-ReportServer
            $script:RunningRevision = Get-RepositoryRevision
        }

        if (Test-Path $UpdateRequestFile) {
            Remove-Item $UpdateRequestFile -Force -ErrorAction SilentlyContinue
            Write-Log "Immediate update check requested"
            $NextUpdateCheck = Get-Date
        }

        if ((Get-Date) -ge $NextUpdateCheck) {
            try {
                Update-RepositoryIfAvailable
                $NextUpdateCheck = (Get-Date).AddSeconds($CheckIntervalSeconds)
            }
            catch {
                Write-Log "Update failed; keeping the current server online: $($_.Exception.Message)"
                $NextUpdateCheck = (Get-Date).AddMinutes(2)
            }
        }

        Start-Sleep -Seconds $HealthCheckIntervalSeconds
    }
}
catch {
    Write-Log "Watchdog failed: $($_.Exception.Message)"
    throw
}
finally {
    # Do not stop a healthy child here. If the watchdog itself is restarted,
    # the new instance adopts the existing listener and resumes monitoring it.
    Write-Log "Watchdog process stopped; Task Scheduler will restart it"
}
