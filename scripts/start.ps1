$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$logRoot = Join-Path $projectRoot "runtime\logs"
$productionIndex = Join-Path $projectRoot "frontend\dist\index.html"
$productionMode = Test-Path -LiteralPath $productionIndex
$interfaceUrl = if ($productionMode) { "http://127.0.0.1:8000" } else { "http://127.0.0.1:5173" }

function Ensure-TerraFlyEnvironment {
    param([string]$ProjectDir)

    $bundledPythonDir = Join-Path $ProjectDir "runtime\python"
    $bundledPythonExe = Join-Path $bundledPythonDir "python.exe"
    $venvDir = Join-Path $ProjectDir ".venv"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"
    $cfgPath = Join-Path $venvDir "pyvenv.cfg"

    # If .venv exists, verify and repair it
    if (Test-Path -LiteralPath $venvPython) {
        # Check if pyvenv.cfg needs repairing (e.g. copied to a different folder/drive or machine)
        if (Test-Path -LiteralPath $cfgPath) {
            $cfgRaw = Get-Content -LiteralPath $cfgPath -Raw
            if (Test-Path -LiteralPath $bundledPythonExe) {
                if ($cfgRaw -notmatch [regex]::Escape($bundledPythonDir)) {
                    $newCfg = @"
home = $bundledPythonDir
include-system-site-packages = false
version = 3.12.14
executable = $bundledPythonExe
command = $bundledPythonExe -m venv $venvDir
"@
                    Set-Content -LiteralPath $cfgPath -Value $newCfg -Encoding utf8
                }
            }
        }

        # Fix __editable__.terrafly-*.pth and create terrafly.pth
        $sitePackages = Join-Path $venvDir "Lib\site-packages"
        if (Test-Path -LiteralPath $sitePackages) {
            $backendDir = Join-Path $ProjectDir "backend"
            Set-Content -LiteralPath (Join-Path $sitePackages "terrafly.pth") -Value $backendDir -Encoding utf8
            Get-ChildItem -Path $sitePackages -Filter "__editable__.terrafly*.pth" -ErrorAction SilentlyContinue | ForEach-Object {
                Set-Content -LiteralPath $_.FullName -Value $backendDir -Encoding utf8
            }
        }

        # Test if the venv python actually runs cleanly with core dependencies
        $venvWorks = $false
        try {
            & $venvPython -c "import sys, terrafly, uvicorn, fastapi; sys.exit(0)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $venvWorks = $true
            }
        } catch {
            $venvWorks = $false
        }

        if ($venvWorks) {
            return $venvPython
        }
    }

    # If environment is not working or missing, run setup automatically
    Write-Host "TerraFly environment requires setup or repair. Running initial setup..." -ForegroundColor Yellow
    $setupScript = Join-Path $ProjectDir "scripts\setup.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $setupScript
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
        throw "TerraFly setup did not complete successfully. Read the messages above, then retry."
    }
    return $venvPython
}

function Test-TerraFlyEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$ExpectedMarker
    )
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 1
        return $response.StatusCode -eq 200 -and $response.Content.Contains($ExpectedMarker)
    } catch {
        return $false
    }
}

function Assert-PortAvailable {
    param([Parameter(Mandatory = $true)][int]$Port)
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($listener) {
        $owners = ($listener | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
        throw "Port $Port is already used by another program (process $owners). Close it, then start TerraFly again."
    }
}

function Repair-DuplicateProcessPath {
    $variables = [Environment]::GetEnvironmentVariables()
    $pathKeys = @($variables.Keys | Where-Object { [string]$_ -ieq "PATH" })
    if ($pathKeys.Count -le 1) { return }

    $pathValue = [string]$env:PATH
    foreach ($key in $pathKeys) {
        [Environment]::SetEnvironmentVariable(
            [string]$key,
            $null,
            [EnvironmentVariableTarget]::Process
        )
    }
    [Environment]::SetEnvironmentVariable(
        "Path",
        $pathValue,
        [EnvironmentVariableTarget]::Process
    )
}

$python = Ensure-TerraFlyEnvironment -ProjectDir $projectRoot

New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $projectRoot "runtime\tmp") -Force | Out-Null
Repair-DuplicateProcessPath

$env:HF_HOME = Join-Path $projectRoot "runtime\model-cache"
$backendDir = Join-Path $projectRoot "backend"
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$backendDir;$env:PYTHONPATH" } else { $backendDir }

$backend = $null
$frontend = $null
$backendReady = Test-TerraFlyEndpoint "http://127.0.0.1:8000/api/health" '"service":"TerraFly"'
$frontendReady = Test-TerraFlyEndpoint $interfaceUrl "TerraFly"

if ($backendReady -and $productionMode -and -not $frontendReady) {
    throw "An older TerraFly backend is already using port 8000. Close its launcher window, then start this release again."
}

try {
    if (-not $backendReady) {
        Assert-PortAvailable 8000
        $backend = Start-Process -FilePath $python `
            -ArgumentList @("-m", "uvicorn", "terrafly.main:app", "--host", "127.0.0.1", "--port", "8000") `
            -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $logRoot "backend-output.log") `
            -RedirectStandardError (Join-Path $logRoot "backend-error.log")
    } else {
        Write-Host "Using the TerraFly backend that is already running." -ForegroundColor DarkGray
    }

    if (-not $productionMode) {
        if (-not $frontendReady) {
            Assert-PortAvailable 5173
            $frontend = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev") `
                -WorkingDirectory (Join-Path $projectRoot "frontend") -WindowStyle Hidden -PassThru `
                -RedirectStandardOutput (Join-Path $logRoot "frontend-output.log") `
                -RedirectStandardError (Join-Path $logRoot "frontend-error.log")
        } else {
            Write-Host "Using the TerraFly interface that is already running." -ForegroundColor DarkGray
        }
    }

    if ($productionMode) {
        Write-Host "Using the prebuilt release interface (no development server required)." -ForegroundColor DarkGray
    }
    Write-Host "TerraFly is starting at $interfaceUrl" -ForegroundColor Green
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if (($backend -and $backend.HasExited) -or ($frontend -and $frontend.HasExited)) { break }
        $backendReady = Test-TerraFlyEndpoint "http://127.0.0.1:8000/api/health" '"service":"TerraFly"'
        $frontendReady = Test-TerraFlyEndpoint $interfaceUrl "TerraFly"
        if ($backendReady -and $frontendReady) { break }
        Start-Sleep -Milliseconds 500
    }

    if (-not ($backendReady -and $frontendReady)) {
        $errLog = Join-Path $logRoot "backend-error.log"
        if (Test-Path -LiteralPath $errLog) {
            $errLines = Get-Content -LiteralPath $errLog -Tail 20 -ErrorAction SilentlyContinue
            if ($errLines) {
                Write-Host "`nBackend error log output:" -ForegroundColor Red
                Write-Host ($errLines -join "`n") -ForegroundColor Red
            }
        }
        throw "TerraFly did not become ready. Review the readable logs in runtime\logs, then run this launcher again."
    }

    try {
        Start-Process -FilePath $interfaceUrl -ErrorAction Stop
        Write-Host "TerraFly is ready. Your browser should open automatically." -ForegroundColor Green
    } catch {
        Write-Warning "TerraFly is running, but Windows could not open the browser automatically."
        Write-Host "Open this address manually: $interfaceUrl" -ForegroundColor Yellow
    }
    Write-Host "Keep this window open. Press Ctrl+C here to stop services started by this launcher."
    while (($null -eq $backend -or -not $backend.HasExited) -and ($null -eq $frontend -or -not $frontend.HasExited)) {
        Start-Sleep -Seconds 1
    }
} finally {
    if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id }
    if ($frontend -and -not $frontend.HasExited) { Stop-Process -Id $frontend.Id }
}
