param(
    [string]$Branch = "main",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Push-Location $RepoRoot
try {
    Write-Host "Stopping any server currently using port $Port..."
    $Connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($Connection in $Connections) {
        if ($Connection.OwningProcess) {
            Stop-Process -Id $Connection.OwningProcess -Force
        }
    }

    Write-Host "Updating from origin/$Branch..."
    git fetch origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }

    git reset --hard "origin/$Branch"
    if ($LASTEXITCODE -ne 0) { throw "git reset failed" }

    if (-not (Test-Path "venv\Scripts\python.exe")) {
        Write-Host "Creating virtual environment..."
        python -m venv venv
        if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
    }

    Write-Host "Installing dependencies..."
    .\venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

    Write-Host "Starting server on http://localhost:$Port ..."
    .\venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port $Port
}
finally {
    Pop-Location
}
