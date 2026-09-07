$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

function Find-CompatiblePython {
    param([string]$Root)

    # 1. Check project-local bundled python runtime (e.g. on pendrive or release)
    $bundled = Join-Path $Root "runtime\python\python.exe"
    if (Test-Path -LiteralPath $bundled) {
        return @{ Path = $bundled; Type = "bundled" }
    }

    # 2. Check cached codex runtime if present on origin machine
    $codexPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path -LiteralPath $codexPython) {
        return @{ Path = $codexPython; Type = "codex" }
    }

    # 3. Check system 'python' command in PATH
    $sysPy = Get-Command "python.exe" -ErrorAction SilentlyContinue
    if ($sysPy) {
        try {
            $ver = (& $sysPy.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
            $major, $minor = $ver.Split('.') | ForEach-Object { [int]$_ }
            if ($major -eq 3 -and $minor -ge 10 -and $minor -le 13) {
                return @{ Path = $sysPy.Source; Type = "system" }
            }
        } catch {}
    }

    # 4. Check Windows 'py' launcher
    $pyLauncher = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        foreach ($v in @("-3.12", "-3.11", "-3.13", "-3.10", "-3")) {
            try {
                $out = (& py $v -c "import sys; print(sys.executable)").Trim()
                if ($out -and (Test-Path -LiteralPath $out)) {
                    return @{ Path = $out; Type = "py-launcher" }
                }
            } catch {}
        }
    }

    # 5. Check well-known Windows Python installation locations
    $knownPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Program Files\Python311\python.exe"
    )
    foreach ($p in $knownPaths) {
        if (Test-Path -LiteralPath $p) {
            return @{ Path = $p; Type = "known-path" }
        }
    }

    return $null
}

Write-Host "Locating compatible Python runtime..." -ForegroundColor Cyan
$detected = Find-CompatiblePython -Root $projectRoot
if ($null -eq $detected) {
    Write-Host "`n[ERROR] No compatible Python (3.10 - 3.13) installation found on this system." -ForegroundColor Red
    Write-Host "Please install Python (64-bit) from:" -ForegroundColor Yellow
    Write-Host "  https://www.python.org/downloads/windows/" -ForegroundColor White
    Write-Host "IMPORTANT: Make sure to check 'Add python.exe to PATH' during installation.`n" -ForegroundColor Yellow
    throw "Python is required to run TerraFly."
}

$basePython = $detected.Path
Write-Host "Using Python runtime: $basePython ($($detected.Type))" -ForegroundColor Green

$venvDir = Join-Path $projectRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$cfgPath = Join-Path $venvDir "pyvenv.cfg"

# Test if existing venv is functional
$venvWorking = $false
if (Test-Path -LiteralPath $venvPython) {
    try {
        & $venvPython -c "import sys; sys.exit(0)" 2>$null
        if ($LASTEXITCODE -eq 0) { $venvWorking = $true }
    } catch {
        $venvWorking = $false
    }
}

if (-not $venvWorking) {
    if (Test-Path -LiteralPath $venvDir) {
        Write-Host "Existing .venv is invalid or from another machine; recreating..." -ForegroundColor Yellow
        Remove-Item -LiteralPath $venvDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Creating Python virtual environment in .venv..." -ForegroundColor Cyan
    & $basePython -m venv $venvDir
    if (-not (Test-Path -LiteralPath $venvPython)) {
        throw "Failed to create virtual environment with $basePython."
    }
}

# Ensure pyvenv.cfg points to current base python location
if (Test-Path -LiteralPath $cfgPath) {
    $baseHome = Split-Path -Parent $basePython
    $newCfg = @"
home = $baseHome
include-system-site-packages = false
version = 3.12.14
executable = $basePython
command = $basePython -m venv $venvDir
"@
    Set-Content -LiteralPath $cfgPath -Value $newCfg -Encoding utf8
}

# Ensure site-packages points to project backend
$sitePackages = Join-Path $venvDir "Lib\site-packages"
if (Test-Path -LiteralPath $sitePackages) {
    $backendDir = Join-Path $projectRoot "backend"
    Set-Content -LiteralPath (Join-Path $sitePackages "terrafly.pth") -Value $backendDir -Encoding utf8
}

Write-Host "Upgrading pip..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip

Write-Host "Installing TerraFly core and dependencies..." -ForegroundColor Cyan
& $venvPython -m pip install -e "$projectRoot[test,ml]"

Write-Host "Checking PyTorch installation..." -ForegroundColor Cyan
$torchWorking = $false
try {
    & $venvPython -c "import torch, torchvision; sys.exit(0)" 2>$null
    if ($LASTEXITCODE -eq 0) { $torchWorking = $true }
} catch {
    $torchWorking = $false
}

if (-not $torchWorking) {
    Write-Host "Installing PyTorch..." -ForegroundColor Cyan
    $cu130Success = $false
    try {
        $reqCu130 = Join-Path $projectRoot "requirements-ml-cu130.txt"
        if (Test-Path -LiteralPath $reqCu130) {
            $p = Start-Process -FilePath $venvPython -ArgumentList @("-m", "pip", "install", "-r", $reqCu130) `
                -NoNewWindow -Wait -PassThru
            if ($p.ExitCode -eq 0) { $cu130Success = $true }
        }
    } catch {
        $cu130Success = $false
    }

    if (-not $cu130Success) {
        Write-Host "CUDA 13.0 package not applicable or unavailable; installing universal PyTorch..." -ForegroundColor Yellow
        & $venvPython -m pip install torch torchvision
    }
}

# Frontend setup
$frontendDist = Join-Path $projectRoot "frontend\dist\index.html"
$hasNpm = $null -ne (Get-Command "npm.cmd" -ErrorAction SilentlyContinue)
if (Test-Path -LiteralPath $frontendDist) {
    Write-Host "Prebuilt production web interface is ready (Node.js/npm not required)." -ForegroundColor Green
} else {
    if ($hasNpm) {
        Write-Host "Building frontend interface from source..." -ForegroundColor Cyan
        Push-Location (Join-Path $projectRoot "frontend")
        try {
            npm install
            npm run build
        } finally {
            Pop-Location
        }
    } else {
        Write-Warning "frontend\dist\index.html is missing and npm was not found."
        Write-Warning "To build the frontend from source, install Node.js from https://nodejs.org/"
    }
}

New-Item -ItemType Directory -Path (Join-Path $projectRoot "runtime\logs") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $projectRoot "runtime\tmp") -Force | Out-Null

Write-Host "`nTerraFly setup completed successfully!" -ForegroundColor Green
Write-Host "You can now launch TerraFly anytime by running Start-TerraFly.cmd." -ForegroundColor Green
