$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Tokens = $null
$ParseErrors = $null
$Ast = [Management.Automation.Language.Parser]::ParseFile(
    (Join-Path $Root "run_server_auto_update.ps1"), [ref]$Tokens, [ref]$ParseErrors
)
if ($ParseErrors.Count) { throw ($ParseErrors | Out-String) }
# Load functions without running task registration, processes, or the watchdog loop.
foreach ($Definition in $Ast.FindAll({ param($Node) $Node -is [Management.Automation.Language.FunctionDefinitionAst] }, $false)) {
    . ([scriptblock]::Create($Definition.Extent.Text))
}
$ActualSwitch = ${function:Invoke-ReleaseSwitch}
$ActualComplete = ${function:Complete-ReleasePreparation}
$ActualTick = ${function:Invoke-WatchdogTick}
$ActualRestore = ${function:Restore-ServingRelease}
$ActualStart = ${function:Start-ReportServer}
$ActualSave = ${function:Save-ReleaseState}
$ActualPrepare = ${function:Prepare-Release}
$TemporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("printsmith-release-test-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $TemporaryRoot | Out-Null
$RepoRoot = $TemporaryRoot
$ReleaseStateFile = Join-Path $TemporaryRoot "state.json"
$BaselineFile = Join-Path $TemporaryRoot "baseline.json"
$ReleasesRoot = Join-Path $TemporaryRoot "releases"
$RollbackRequestFile = Join-Path $TemporaryRoot "rollback-request"
$UpdateRequestFile = Join-Path $TemporaryRoot "update-request"
$CheckIntervalSeconds = 600
$Port = 8000
$Branch = "main"
$Old = [pscustomobject]@{ revision = "old"; release_path = "old-code"; python_exe = "old-python" }
$New = [pscustomobject]@{ revision = "new"; release_path = "new-code"; python_exe = "new-python" }

function Assert-True {
    param($Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}
function Assert-Throws {
    param([scriptblock]$Action, [string]$Message)
    $Threw = $false
    try { & $Action } catch { $Threw = $true }
    Assert-True $Threw $Message
}
function Reset-Test {
    $script:Events = New-Object 'Collections.Generic.List[string]'
    $script:ActiveRelease = $Old
    $script:PreviousRelease = $null
    $script:BlockedRevision = ""
    $script:FailStart = ""
    $script:FailHealth = ""
    $script:FailGate = $false
    $script:IsRunning = $true
    $script:ServerProcess = $null
    $script:PreparationProcess = $null
    $script:PreparationOutput = Join-Path $TemporaryRoot "result.json"
    $script:PreparationStartedAt = Get-Date
    $script:NextUpdateCheck = (Get-Date).AddMinutes(10)
    $script:Listener = $null
    $script:ProcessDetails = $null
    $script:Health = @{ status = "ok"; revision = "new" }
    $script:UseExistingCandidate = $false
    $script:PendingBlockedRevision = ""
    $script:PersistState = $false
    Remove-Item $ReleaseStateFile -Force -ErrorAction SilentlyContinue
}
function New-FakeProcess {
    param([bool]$Exited, [int]$ExitCode = 0)
    $Process = [pscustomobject]@{ Id = 123; HasExited = $Exited; ExitCode = $ExitCode }
    $Process | Add-Member ScriptMethod Refresh {}
    $Process | Add-Member ScriptMethod Dispose {}
    return $Process
}
function Write-Log { param($Message) }
function Start-ReportServer {
    param($Release)
    $script:Events.Add("start:$($Release.revision)")
    if ($script:UseExistingCandidate -and $Release.revision -in @("new", "legacy-unverified")) {
        & $ActualStart $Release
        return
    }
    if ($script:UseExistingCandidate -and $script:Listener) { throw "port still occupied" }
    if ($Release.revision -eq $script:FailStart) { throw "simulated startup failure" }
    $script:IsRunning = $true
}
function Wait-ReleaseHealth {
    param($Release)
    $script:Events.Add("health:$($Release.revision)")
    if ($Release.revision -eq $script:FailHealth) { throw "simulated wrong revision" }
}
function Stop-ReportServer {
    $script:Events.Add("stop")
    if ($script:ServerProcess -and $script:Listener -and $script:ServerProcess.Id -eq $script:Listener.Id) {
        $script:Listener = $null
    }
    $script:ServerProcess = $null
}
function Test-ServerRunning { return $script:IsRunning }
function Save-ReleaseState {
    param($Release, $Previous, [string]$State = "active")
    if ($State -eq "pending") { $script:PendingBlockedRevision = $script:BlockedRevision }
    $script:Events.Add("save:${State}:$($Release.revision)")
    if ($script:PersistState) { & $ActualSave $Release $Previous $State }
}
function Complete-ReleasePreparation { & $ActualComplete }
function Start-ReleasePreparation { $script:Events.Add("prepare") }
function Stop-ReleasePreparation { $script:Events.Add("cancel-preparation"); $script:PreparationProcess = $null }
function Get-ListeningProcess { return $script:Listener }
function Get-CimInstance { param($ClassName, $Filter) return $script:ProcessDetails }
function Invoke-RestMethod { param($Uri, $TimeoutSec) return $script:Health }

try {
    Reset-Test
    & $ActualSwitch $New
    Assert-True (($Events -join ",") -eq "save:pending:new,stop,start:new,health:new,save:active:new") "Switch must record pending state and validate before acceptance"
    Assert-True ($ActiveRelease.revision -eq "new" -and $PreviousRelease.revision -eq "old") "Successful switch must retain rollback release"

    Reset-Test
    $FailStart = "new"
    Assert-Throws { & $ActualSwitch $New } "Startup failure must fail deployment"
    Assert-True ($ActiveRelease.revision -eq "old" -and $BlockedRevision -eq "new") "Startup failure must restore old and block rejected revision"
    Assert-True ($Events.Contains("start:old") -and $Events.Contains("health:old")) "Rollback must restart and validate old release"

    Reset-Test
    $FailHealth = "new"
    Assert-Throws { & $ActualSwitch $New } "Wrong health revision must fail deployment"
    Assert-True ($ActiveRelease.revision -eq "old" -and $Events.Contains("save:active:old")) "Wrong health revision must restore saved old release"

    Reset-Test
    & $ActualSwitch $New -ManualRollback
    Assert-True ($BlockedRevision -eq "old") "Explicit rollback must not automatically redeploy the rejected current version"
    Assert-True ($PendingBlockedRevision -eq "old") "Manual rollback must persist the rejected revision before stopping the current app"

    Reset-Test
    $PreparationProcess = New-FakeProcess $true 1
    Assert-Throws { & $ActualComplete } "Failed regression gate must reject candidate"
    Assert-True (-not $Events.Contains("stop")) "Failed preparation must never stop the serving app"

    Reset-Test
    $PreparationProcess = New-FakeProcess $true 0
    $New | ConvertTo-Json | Set-Content $PreparationOutput
    & $ActualComplete
    Assert-True ($ActiveRelease.revision -eq "new" -and $Events.Contains("stop")) "Only completed successful preparation may switch the app"

    Reset-Test
    $PreparationProcess = New-FakeProcess $false
    $IsRunning = $false
    & $ActualTick
    Assert-True ($Events.Contains("start:old") -and $PreparationProcess) "Serving crash must recover while preparation is still running"
    Assert-True (-not $Events.Contains("stop") -and -not $Events.Contains("prepare")) "Slow preparation must not switch releases or start another preparation"

    Reset-Test
    $PreparationProcess = New-FakeProcess $false
    $PreparationStartedAt = (Get-Date).AddMinutes(-31)
    Assert-Throws { & $ActualComplete } "Stalled preparation must time out"
    Assert-True ($Events.Contains("cancel-preparation") -and -not $Events.Contains("stop")) "Preparation timeout must preserve serving app"

    Reset-Test
    $Listener = New-FakeProcess $false
    $ProcessDetails = @{ ExecutablePath = "some-other-python"; CommandLine = "python -m uvicorn main:app" }
    Assert-Throws { & $ActualStart $New } "Unrelated listener must not be adopted"
    Assert-True (-not $ServerProcess) "Rejected listener must not become a process the watchdog can stop"
    $ProcessDetails = @{ ExecutablePath = "new-python"; CommandLine = 'python -m uvicorn --app-dir "new-code" othermain:app' }
    Assert-Throws { & $ActualStart $New } "Similarly named ASGI app must not be adopted"
    $ProcessDetails.CommandLine = 'python -m uvicorn --app-dir "new-code-extra" main:app'
    Assert-Throws { & $ActualStart $New } "App directory prefix must not identify the release"
    $ProcessDetails.CommandLine = 'python -m uvicorn --app-dir "new-code" main:app'
    $Health.revision = "other"
    Assert-Throws { & $ActualStart $New } "Wrong running revision must not be adopted"

    Reset-Test
    @{ revision = "new"; release_path = "new-code"; python_exe = "new-python"; previous = $Old; state = "pending" } |
        ConvertTo-Json -Depth 4 | Set-Content $ReleaseStateFile
    $FailHealth = "new"
    & $ActualRestore
    Assert-True ($ActiveRelease.revision -eq "old" -and $BlockedRevision -eq "new") "Interrupted unhealthy switch must recover previous release after watchdog restart"

    Reset-Test
    @{ revision = "old"; release_path = "old-code"; python_exe = "old-python"; previous = $New; state = "pending"; blocked_revision = "new" } |
        ConvertTo-Json -Depth 4 | Set-Content $ReleaseStateFile
    & $ActualRestore
    Assert-True ($ActiveRelease.revision -eq "old" -and $BlockedRevision -eq "new") "Interrupted manual rollback must keep the newer rejected revision blocked"
    Assert-True ($Events.Contains("save:active:old")) "Recovered manual rollback must finalize the older release"

    Reset-Test
    @{ revision = "new"; release_path = "new-code"; python_exe = "new-python"; previous = $Old; state = "pending" } |
        ConvertTo-Json -Depth 4 | Set-Content $ReleaseStateFile
    $UseExistingCandidate = $true
    $Listener = New-FakeProcess $false
    $ProcessDetails = @{ ExecutablePath = "new-python"; CommandLine = 'python -m uvicorn --app-dir "new-code" main:app' }
    $Health.revision = "wrong"
    & $ActualRestore
    Assert-True ($ActiveRelease.revision -eq "old" -and -not $Listener) "An interrupted failed candidate must be tracked and stopped before rollback"

    Reset-Test
    @{ revision = "new"; release_path = "new-code"; python_exe = "new-python"; previous = $Old; state = "pending" } |
        ConvertTo-Json -Depth 4 | Set-Content $ReleaseStateFile
    $UseExistingCandidate = $true
    $Listener = New-FakeProcess $false
    $ProcessDetails = @{ ExecutablePath = "unrelated-python"; CommandLine = 'python -m uvicorn --app-dir "new-code" main:app' }
    Assert-Throws { & $ActualRestore } "Rollback must refuse to kill an unrelated listener"
    Assert-True ($Listener -and -not $ServerProcess) "Unknown listener must remain untouched during rollback recovery"

    Reset-Test
    @{ revision = "legacy-unverified"; release_path = $RepoRoot; python_exe = "legacy-python"; previous = $null; state = "legacy"; blocked_revision = "new" } |
        ConvertTo-Json -Depth 4 | Set-Content $ReleaseStateFile
    & $ActualRestore
    Assert-True ($ActiveRelease.revision -eq "legacy-unverified" -and $Events.Contains("start:legacy-unverified")) "A previously serving legacy rollback must restart after reboot"
    Assert-True ($BlockedRevision -eq "new") "Restarting a legacy rollback must preserve rejected-revision protection"

    Reset-Test
    $PersistState = $true
    $UseExistingCandidate = $true
    $Listener = New-FakeProcess $false
    $ProcessDetails = @{
        ExecutablePath = Join-Path $RepoRoot "venv\Scripts\python.exe"
        CommandLine = "python -m uvicorn main:app --host 0.0.0.0 --port 8000"
    }
    & $ActualRestore
    $Adopted = Get-Content $ReleaseStateFile -Raw | ConvertFrom-Json
    Assert-True ($Adopted.state -eq "legacy" -and $Adopted.release_path -eq $RepoRoot) "First verified legacy adoption must be persisted before any update succeeds"
    $Listener = $null
    $ServerProcess = $null
    $UseExistingCandidate = $false
    $Events.Clear()
    & $ActualRestore
    Assert-True ($ActiveRelease.revision -eq "legacy-unverified" -and $Events.Contains("start:legacy-unverified")) "Adopted legacy app must restart after reboot even without a baseline or accepted candidate"

    Reset-Test
    $BlockedRevision = "rejected"
    & $ActualSave $Old $null
    & $ActualSave $New $Old
    $Saved = Get-Content $ReleaseStateFile -Raw | ConvertFrom-Json
    Assert-True ($Saved.revision -eq "new" -and $Saved.previous.revision -eq "old" -and $Saved.blocked_revision -eq "rejected") "Atomic manifest replacement must preserve version and rollback identity"

    # Mock only external build commands; exercise the actual candidate gate sequence.
    function git { $global:LASTEXITCODE = 0; return ("b" * 40) }
    function Invoke-RepoCommand {
        param([string[]]$Command)
        if ($Command[1] -eq "archive") { Set-Content -Path $Command[4] -Value "archive" }
        if ($Command -contains "pip") { $script:Events.Add("dependencies") }
        if ($Command[1] -like "*release_check.py") {
            $script:Events.Add("regression-gate")
            if ($script:FailGate) { throw "simulated accounting mismatch" }
        }
    }
    function Expand-Archive { param($Path, $DestinationPath, [switch]$Force) New-Item -ItemType Directory -Path $DestinationPath | Out-Null }
    New-Item -ItemType Directory -Path $ReleasesRoot -Force | Out-Null
    Set-Content -Path $BaselineFile -Value "approved baseline"
    Reset-Test
    $ExpectedRunningRevision = "old"
    $FailGate = $true
    Assert-Throws { & $ActualPrepare } "Accounting mismatch must prevent returning a candidate"
    Assert-True (($Events -join ",") -eq "dependencies,regression-gate") "Gate failure must not stop the app"
    $FailGate = $false
    $Candidate = & $ActualPrepare
    Assert-True ($Candidate.revision -eq ("b" * 40) -and $Candidate.release_path.StartsWith($ReleasesRoot)) "Only a checked isolated candidate may be returned"
    Write-Host "Windows release control-flow checks passed. No services, network calls, or real releases were changed."
}
finally {
    Remove-Item $TemporaryRoot -Recurse -Force
}
