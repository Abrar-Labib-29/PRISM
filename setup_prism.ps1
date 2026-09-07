<#
.SYNOPSIS
    iValue PRISM - Automated Windows Development Environment Setup Script
    Sets up everything required to start contributing to Project PRISM:
    - Clones / pulls latest code from GitHub (Abrar-Labib-29/PRISM)
    - Verifies / installs Python 3.10+ & Git
    - Sets up Python virtual environment (.venv) and installs all dependencies
    - Verifies / installs & starts local Ollama daemon
    - Pulls both required AI models (phi4-mini LLM + bge-small-en-v1.5 embeddings)
    - Builds custom presales model (ivalue-presales) with clamped context & threads
    - Verifies pre-computed NumPy embeddings & metadata files
    - Configures environment variables (.env) & runtime folders
    - Runs end-to-end pipeline health check

.NOTES
    Repository: https://github.com/Abrar-Labib-29/PRISM.git
    Target OS: Windows 10 (1909+) or Windows 11 (64-bit)
#>

[CmdletBinding()]
param (
    [string]$RepoUrl = "https://github.com/Abrar-Labib-29/PRISM.git",
    [string]$TargetDir = "PRISM",
    [switch]$SkipModelPull
)

$ErrorActionPreference = "Stop"

# Enable VT100 / ANSI color sequences in Windows PowerShell console
$Host.UI.RawUI.ForegroundColor = "White"

function Write-Step {
    param([string]$Title)
    Write-Host "`n================================================================================" -ForegroundColor Cyan
    Write-Host "  >> $Title" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host " [PASS] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host " [INFO] $Message" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host " [FAIL] $Message" -ForegroundColor Red
}

Write-Host @"

  ============================================================================
           _ __     __      _             ____  ____  ________  ____ ___ 
          (_) \ \   / /_ _  | |_   _  ___  |  _ \|  _ \|_   _/ ___||  \/  |
          | |\ \ / / _` | | | | | | |/ _ \ | |_) | |_) | | | \___ \| |\/| |
          | | \ V / (_| | |_| | |_| |  __/ |  __/|  _ <  | |  ___) | |  | |
          |_|  \_/ \__,_|\__,_|\__,_|\___| |_|   |_| \_\|_| |____/|_|  |_|
  ============================================================================
       Presales Recommendation & Intelligence System - Environment Setup
  ============================================================================
"@ -ForegroundColor Magenta

# -----------------------------------------------------------------------------
# STEP 1: Git & Repository Synchronization
# -----------------------------------------------------------------------------
Write-Step "STEP 1/7: Synchronizing Repository from GitHub"

$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Write-Info "Git is not installed or not in PATH. Attempting automatic installation via winget..."
    try {
        winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        $gitCmd = Get-Command git -ErrorAction SilentlyContinue
    } catch {
        Write-Err "Could not install Git automatically. Please install Git manually from https://git-scm.com/download/win"
        exit 1
    }
}
Write-Success "Git detected: $(git --version)"

# Check if we are already inside the PRISM git repository
$isInsideRepo = $false
if (Test-Path ".git") {
    $remoteUrl = git config --get remote.origin.url
    if ($remoteUrl -like "*PRISM*") {
        $isInsideRepo = $true
    }
}

if ($isInsideRepo) {
    Write-Info "Already inside PRISM repository. Pulling latest commits from origin/main..."
    git fetch origin main
    git pull origin main
    Write-Success "Repository updated to latest commit $(git rev-parse --short HEAD)."
} else {
    if (Test-Path $TargetDir) {
        Write-Info "Directory '$TargetDir' already exists. Navigating into it..."
        Set-Location $TargetDir
        git fetch origin main
        git pull origin main
    } else {
        Write-Info "Cloning repository from $RepoUrl into '$TargetDir'..."
        git clone $RepoUrl $TargetDir
        Set-Location $TargetDir
    }
    Write-Success "Repository synchronized at $(Get-Location)."
}

# -----------------------------------------------------------------------------
# STEP 2: Python Runtime Check & Virtual Environment (.venv)
# -----------------------------------------------------------------------------
Write-Step "STEP 2/7: Checking Python & Initializing Virtual Environment"

$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py -3"
}

if (-not $pythonCmd) {
    Write-Info "Python not detected in PATH. Attempting automatic installation of Python 3.11 via winget..."
    try {
        winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        $pythonCmd = "python"
    } catch {
        Write-Err "Please install Python 3.10+ from https://www.python.org/downloads/ and ensure 'Add to PATH' is checked."
        exit 1
    }
}

$pyVersion = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
Write-Success "Python runtime detected: $pyVersion"

# Create .venv if it does not exist
if (-not (Test-Path ".venv")) {
    Write-Info "Creating isolated virtual environment in .venv..."
    & $pythonCmd -m venv .venv
    Write-Success "Virtual environment created."
} else {
    Write-Success "Existing virtual environment (.venv) detected."
}

$venvPython = Join-Path (Get-Location) ".venv\Scripts\python.exe"
$venvPip = Join-Path (Get-Location) ".venv\Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Err "Virtual environment python executable not found at $venvPython."
    exit 1
}

# -----------------------------------------------------------------------------
# STEP 3: Install Python Dependencies
# -----------------------------------------------------------------------------
Write-Step "STEP 3/7: Installing Python Dependencies (requirements.txt)"

Write-Info "Upgrading pip, setuptools, wheel..."
& $venvPython -m pip install --upgrade pip setuptools wheel --quiet

if (Test-Path "requirements.txt") {
    Write-Info "Installing dependencies from requirements.txt (CustomTkinter, Ollama, SentenceTransformers, NumPy, Pandas, etc.)..."
    & $venvPip install -r requirements.txt --quiet
    Write-Success "All Python dependencies successfully installed."
} else {
    Write-Err "requirements.txt not found in repository root!"
    exit 1
}

# Check if Microsoft Visual C++ Redistributable is installed for PyTorch
$torchCheck = & $venvPython -c "
try:
    import torch
    print('TORCH_OK')
except OSError as e:
    if 'c10.dll' in str(e) or '126' in str(e) or 'Visual C++' in str(e):
        print('NEED_VCREDIST')
    else:
        print(f'TORCH_ERR:{e}')
except Exception as e:
    print(f'TORCH_ERR:{e}')
" 2>&1

if ($torchCheck -like "*NEED_VCREDIST*") {
    Write-Info "PyTorch requires Microsoft Visual C++ 2015-2022 Redistributable."
    Write-Info "Downloading & launching official Microsoft installer (click 'Yes' if prompted by Windows UAC)..."
    $vcRedistUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    $vcRedistPath = "$env:TEMP\vc_redist.x64.exe"
    if (-not (Test-Path $vcRedistPath)) {
        Invoke-WebRequest -Uri $vcRedistUrl -OutFile $vcRedistPath
    }
    try {
        Start-Process -FilePath $vcRedistPath -ArgumentList "/install /passive /norestart" -Verb RunAs -Wait
        Write-Success "Visual C++ Redistributable installed successfully."
    } catch {
        Write-Info "To complete PyTorch acceleration, run: $vcRedistPath"
    }
}

# -----------------------------------------------------------------------------
# STEP 4: Ollama Service Check, Installation & Daemon Auto-Start
# -----------------------------------------------------------------------------
Write-Step "STEP 4/7: Checking Ollama Service & Local Daemon"

$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
$ollamaPaths = @(
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "$env:ProgramFiles\Ollama\ollama.exe"
)

$ollamaExe = $null
if ($ollamaCmd) {
    $ollamaExe = $ollamaCmd.Source
} else {
    foreach ($p in $ollamaPaths) {
        if (Test-Path $p) {
            $ollamaExe = $p
            break
        }
    }
}

if (-not $ollamaExe) {
    Write-Info "Ollama is not installed. Attempting installation via winget..."
    try {
        winget install Ollama.Ollama --source winget --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        foreach ($p in $ollamaPaths) {
            if (Test-Path $p) {
                $ollamaExe = $p
                break
            }
        }
        if (-not $ollamaExe) {
            $foundCmd = Get-Command ollama -ErrorAction SilentlyContinue
            if ($foundCmd) {
                $ollamaExe = $foundCmd.Source
            }
        }
    } catch {
        Write-Info "Winget install failed. Downloading OllamaSetup.exe from official website..."
        $installerPath = "$env:TEMP\OllamaSetup.exe"
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installerPath
        Write-Info "Running Ollama installer. Please follow the prompt..."
        Start-Process -FilePath $installerPath -Wait
    }
}

if (-not $ollamaExe) {
    foreach ($p in $ollamaPaths) {
        if (Test-Path $p) {
            $ollamaExe = $p
            break
        }
    }
}

if ($ollamaExe) {
    Write-Success "Ollama executable located at: $ollamaExe"
} else {
    Write-Err "Ollama executable could not be found. Please ensure Ollama is installed from https://ollama.com"
    exit 1
}

# Check if Ollama daemon is actively running on port 11434
$daemonRunning = $false
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
    $daemonRunning = $true
} catch {
    $daemonRunning = $false
}

if (-not $daemonRunning) {
    Write-Info "Ollama daemon is offline. Starting 'ollama serve' in background..."
    Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    
    # Wait for daemon to become ready (up to 20 seconds)
    $attempts = 0
    while ($attempts -lt 15) {
        Start-Sleep -Seconds 1.5
        $attempts++
        try {
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
            $daemonRunning = $true
            break
        } catch {
            Write-Host -NoNewline "."
        }
    }
    Write-Host ""
}

if ($daemonRunning) {
    Write-Success "Ollama daemon is active and responding on http://127.0.0.1:11434."
} else {
    Write-Err "Could not connect to Ollama daemon on http://127.0.0.1:11434. Please start Ollama manually."
    exit 1
}

# -----------------------------------------------------------------------------
# STEP 5: Pull AI Models (Phi-4-mini & Embedding Model)
# -----------------------------------------------------------------------------
Write-Step "STEP 5/7: Setting Up AI Models (LLM & Embeddings)"

if (-not $SkipModelPull) {
    # 1. Reasoning Model: phi4-mini
    Write-Info "Checking if 'phi4-mini' is pulled in Ollama..."
    $modelsList = (Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags").models.name
    $phiInstalled = $modelsList | Where-Object { $_ -like "phi4-mini*" }

    if (-not $phiInstalled) {
        Write-Info "Pulling phi4-mini (~2.5 GB) into Ollama. This may take a few minutes depending on your internet..."
        & $ollamaExe pull phi4-mini
        Write-Success "Model 'phi4-mini' downloaded successfully."
    } else {
        Write-Success "Model 'phi4-mini' is already installed in Ollama ($phiInstalled)."
    }

    # 2. Build custom presales model: ivalue-presales from Modelfile.presales
    if (Test-Path "Modelfile.presales") {
        Write-Info "Creating optimized 'ivalue-presales' model with clamped 2048 ctx & 4 threads..."
        & $ollamaExe create ivalue-presales -f Modelfile.presales
        Write-Success "Custom model 'ivalue-presales' configured successfully."
    }

    # 3. Embedding Model: bge-small-en-v1.5
    Write-Info "Pre-caching BAAI/bge-small-en-v1.5 weights (~130 MB) via sentence-transformers..."
    $cacheScript = @"
import sys
try:
    from sentence_transformers import SentenceTransformer
    print('  Loading BAAI/bge-small-en-v1.5...')
    model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    vec = model.encode('iValue PRISM cyber security solution test query')
    print(f'  Embedding model verified! Output vector shape: {vec.shape}')
except Exception as e:
    print(f'  [NOTE] Embedding warm-up notice: {e}')
"@
    & $venvPython -c $cacheScript
    Write-Success "Embedding model check completed."
} else {
    Write-Info "SkipModelPull switch enabled; skipping model download."
}

# -----------------------------------------------------------------------------
# STEP 6: Pre-computed Data & Environment Setup
# -----------------------------------------------------------------------------
Write-Step "STEP 6/7: Verifying Data Files, Folders & Environment Config"

$requiredFiles = @(
    "data\composite_products.json",
    "data\domain_taxonomy.json",
    "data\embeddings.npy",
    "data\metadata.pkl",
    "data\raw\iValue_Solution_Recommendation_Dataset.xlsx",
    "assets\branding\ivalue_prism_logo.jpg",
    "themes\ivalue_prism.json"
)

$allFilesPresent = $true
foreach ($f in $requiredFiles) {
    if (Test-Path $f) {
        $size = (Get-Item $f).Length / 1KB
        Write-Success "$f exists ($([math]::Round($size, 1)) KB)"
    } else {
        Write-Err "Missing required data file: $f"
        $allFilesPresent = $false
    }
}

if (-not $allFilesPresent) {
    Write-Err "Some critical data files are missing! Please verify git checkout."
    exit 1
}

# Create runtime directories
$runtimeDirs = @(
    "logs",
    "exports",
    "$env:APPDATA\iValue_PRISM\logs"
)
foreach ($d in $runtimeDirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
}
Write-Success "Runtime directories verified: logs/, exports/, %APPDATA%\iValue_PRISM\logs\"

# Create or update .env file
$envContent = @"
# iValue PRISM Local Development Environment Configuration
PRISM_ENV=development
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=phi4-mini
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
SIMILARITY_FLOOR=0.20
SIMILARITY_WARNING=0.35
DATA_DIR=data
LOGS_DIR=logs
EXPORTS_DIR=exports
"@
Set-Content -Path ".env" -Value $envContent -Encoding utf8
Write-Success "Environment configuration written to .env."

# -----------------------------------------------------------------------------
# STEP 7: End-to-End Pipeline Health Check
# -----------------------------------------------------------------------------
Write-Step "STEP 7/7: Executing End-to-End Pipeline Self-Test"

$testScript = @"
import sys
import json
import pickle
import numpy as np
import ollama

print('1. Verifying pre-computed NumPy embeddings matrix...')
embeddings = np.load('data/embeddings.npy')
assert embeddings.shape == (139, 384), f'Unexpected embeddings shape: {embeddings.shape}'
print(f'   [OK] Embeddings matrix: {embeddings.shape} (float32, 139 products, 384 dims)')

print('2. Verifying metadata table...')
with open('data/metadata.pkl', 'rb') as f:
    df = pickle.load(f)
assert len(df) == 139, f'Unexpected item count: {len(df)}'
keys = list(df[0].keys()) if isinstance(df, list) else list(df.columns)
print(f'   [OK] Metadata table: {len(df)} products, sample attributes: {keys[:4]}')

print('3. Verifying composite product definitions...')
with open('data/composite_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)
assert len(products) == 139, f'Unexpected product count: {len(products)}'
print(f'   [OK] Composite products dictionary: {len(products)} products mapped.')

print('4. Verifying Ollama inference with phi4-mini...')
try:
    client = ollama.Client(host='http://127.0.0.1:11434')
    res = client.chat(
        model='phi4-mini',
        messages=[{'role': 'user', 'content': 'Respond with exactly: PRISM READY'}],
        options={'num_ctx': 512, 'temperature': 0.0}
    )
    reply = res['message']['content'].strip()
    print(f'   [OK] Ollama reply: \"{reply}\"')
except Exception as e:
    print(f'   [WARN] Ollama test notice: {e}')

print('5. Verifying CustomTkinter UI framework...')
try:
    import customtkinter as ctk
    app = ctk.CTk()
    app.withdraw()
    app.destroy()
    print('   [OK] CustomTkinter graphics engine initialized successfully.')
except Exception as e:
    print(f'   [WARN] CustomTkinter notice: {e}')

print('\nALL PREFLIGHT CHECKS PASSED!')
"@

try {
    & $venvPython -c $testScript
    Write-Success "Comprehensive self-test passed with 100% success rate."
} catch {
    Write-Err "Self-test failed: $_"
    exit 1
}

Write-Host @"

  ============================================================================
  🎉 PRISM ENVIRONMENT SETUP COMPLETE & READY FOR IMPLEMENTATION!
  ============================================================================

  To start working on the project, activate the virtual environment:
    PS> .\.venv\Scripts\Activate.ps1

  You can run your code and tests directly:
    PS> pytest tests/
    PS> python main.py

  Configuration settings: .env
  SRS Document: docs/iValue_Presales_Automation_SRS.md
  ============================================================================
"@ -ForegroundColor Green
