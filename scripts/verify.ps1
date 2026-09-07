param([switch]$Full)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$bundledPythonDir = Join-Path $projectRoot "runtime\python"
$bundledPythonExe = Join-Path $bundledPythonDir "python.exe"
$venvDir = Join-Path $projectRoot ".venv"
$python = Join-Path $venvDir "Scripts\python.exe"
$cfgPath = Join-Path $venvDir "pyvenv.cfg"
$frontend = Join-Path $projectRoot "frontend"

# Auto-repair venv if moved to another drive/folder
if (Test-Path -LiteralPath $python) {
    if ((Test-Path -LiteralPath $cfgPath) -and (Test-Path -LiteralPath $bundledPythonExe)) {
        $cfgRaw = Get-Content -LiteralPath $cfgPath -Raw
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
    $sitePackages = Join-Path $venvDir "Lib\site-packages"
    if (Test-Path -LiteralPath $sitePackages) {
        $backendDir = Join-Path $projectRoot "backend"
        Set-Content -LiteralPath (Join-Path $sitePackages "terrafly.pth") -Value $backendDir -Encoding utf8
    }
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "TerraFly is not set up. Run scripts\setup.ps1 once first."
}

$backendDir = Join-Path $projectRoot "backend"
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$backendDir;$env:PYTHONPATH" } else { $backendDir }
New-Item -ItemType Directory -Path (Join-Path $projectRoot "runtime\tmp") -Force | Out-Null

function Invoke-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )
    Write-Host "`n[CHECK] $Name" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE." }
    Write-Host "[PASS]  $Name" -ForegroundColor Green
}

$hasNodeModules = Test-Path -LiteralPath (Join-Path $frontend "node_modules")
$hasNpm = $null -ne (Get-Command "npm.cmd" -ErrorAction SilentlyContinue)
$hasProductionDist = Test-Path -LiteralPath (Join-Path $frontend "dist\index.html")

if (-not $hasNodeModules -and -not $hasProductionDist) {
    throw "Frontend packages or built interface are missing. Run scripts\setup.ps1 once first."
}

Push-Location $projectRoot
try {
    Invoke-Check "Python dependencies" { & $python -m pip check }
    Invoke-Check "Backend scientific and safety tests" { & $python -m pytest -q }
    Invoke-Check "Bundled measured-terrain workflow" { & $python scripts\smoke_terrain_workflow.py }

    if ($hasNodeModules -and $hasNpm) {
        Invoke-Check "Frontend interaction tests" { Push-Location $frontend; try { npm test } finally { Pop-Location } }
        Invoke-Check "Production interface build" { Push-Location $frontend; try { npm run build } finally { Pop-Location } }
    } else {
        Invoke-Check "Production interface verification" {
            if (-not $hasProductionDist) { throw "Missing frontend/dist/index.html" }
            Write-Host "Prebuilt production interface verified." -ForegroundColor DarkGray
        }
    }

    if ($Full) {
        $env:HF_HOME = Join-Path $projectRoot "runtime\model-cache"
        $device = (& $python -c "import torch; print('cuda' if torch.cuda.is_available() else 'cpu')").Trim()
        Invoke-Check "Complete real-model calibration workflow on $device" {
            & $python scripts\smoke_final_workflow.py --device $device
        }
    }

    $health = $null
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2
    } catch {
        Write-Host "`n[INFO]  App is not running; launch it with Start-TerraFly.cmd for the visual check." -ForegroundColor Yellow
    }
    if ($null -ne $health) {
        if ($health.service -ne "TerraFly" -or $health.version -ne "1.0.0") {
            throw "Running service identity/version does not match TerraFly 1.0.0."
        }
        Write-Host "`n[PASS]  Running app health: TerraFly $($health.version)" -ForegroundColor Green
    }

    Write-Host "`nALL REQUESTED TERRAFLY CHECKS PASSED." -ForegroundColor Green
    Write-Host "Automated checks prove software behavior; they do not replace independent height validation."
} finally {
    Pop-Location
}
