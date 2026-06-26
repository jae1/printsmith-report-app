param(
    [int]$CheckIntervalSeconds = 600,
    [string]$Branch = "main",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogFile = Join-Path $RepoRoot "server_auto_update.log"
$ServerProcess = $null

function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $Line = "[$Timestamp] $Message"
    Write-Host $Line
    Add-Content -Path $LogFile -Value $Line
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

function Sync-Repository {
    Write-Log "Fetching origin/$Branch"
    Invoke-RepoCommand @("git", "fetch", "origin", $Branch)
    Invoke-RepoCommand @("git", "reset", "--hard", "origin/$Branch")
}

function Install-Dependencies {
    $PythonExe = Ensure-Venv
    Write-Log "Installing dependencies"
    Invoke-RepoCommand @($PythonExe, "-m", "pip", "install", "-r", "requirements.txt")
}

function Start-ReportServer {
    $PythonExe = Ensure-Venv
    Write-Log "Starting server on 0.0.0.0:$Port"
    $script:ServerProcess = Start-Process `
        -FilePath $PythonExe `
        -ArgumentList @("-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$Port") `
        -WorkingDirectory $RepoRoot `
        -PassThru `
        -NoNewWindow
}

function Stop-ReportServer {
    if ($script:ServerProcess -and -not $script:ServerProcess.HasExited) {
        Write-Log "Stopping server process $($script:ServerProcess.Id)"
        Stop-Process -Id $script:ServerProcess.Id -Force
        $script:ServerProcess.WaitForExit()
    }
}

function Restart-ReportServer {
    Stop-ReportServer
    Sync-Repository
    Install-Dependencies
    Start-ReportServer
}

try {
    Write-Log "Auto-update runner started from $RepoRoot"
    Restart-ReportServer

    while ($true) {
        Start-Sleep -Seconds $CheckIntervalSeconds

        Invoke-RepoCommand @("git", "fetch", "origin", $Branch)
        $LocalHead = (& git -C $RepoRoot rev-parse HEAD).Trim()
        $RemoteHead = (& git -C $RepoRoot rev-parse "origin/$Branch").Trim()

        if ($LocalHead -ne $RemoteHead) {
            Write-Log "Update found: $LocalHead -> $RemoteHead"
            Restart-ReportServer
        }
        elseif ($script:ServerProcess -and $script:ServerProcess.HasExited) {
            Write-Log "Server exited with code $($script:ServerProcess.ExitCode); restarting"
            Start-ReportServer
        }
        else {
            Write-Log "No update found"
        }
    }
}
finally {
    Stop-ReportServer
    Write-Log "Auto-update runner stopped"
}
