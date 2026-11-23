# Instala (una sola vez) lo que necesita reel-analyzer en %USERPROFILE%\.reel-analyzer\venv.
# Idempotente. Uso:  powershell -ExecutionPolicy Bypass -File setup.ps1 [-Check]
param([switch]$Check)
$ErrorActionPreference = "Stop"

$ScriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HomeDir = if ($env:REEL_ANALYZER_HOME) { $env:REEL_ANALYZER_HOME } else { Join-Path $env:USERPROFILE ".reel-analyzer" }
$Venv = Join-Path $HomeDir "venv"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
$Marker = Join-Path $HomeDir ".ok"
$Req = Join-Path $ScriptsDir "requirements.txt"
$Hash = (Get-FileHash -Algorithm SHA256 $Req).Hash.ToLower()

function Test-Ready {
  (Test-Path $VenvPy) -and (Test-Path $Marker) -and ((Get-Content $Marker -Raw).Trim() -eq $Hash) `
    -and (Get-Command ffmpeg -ErrorAction SilentlyContinue) -and (Get-Command ffprobe -ErrorAction SilentlyContinue)
}

if ($Check) {
  if (Test-Ready) { "reel-analyzer: listo"; exit 0 } else { "reel-analyzer: falta instalar (corre setup.ps1)"; exit 2 }
}
if (Test-Ready) { "reel-analyzer: todo instalado ($Venv)"; exit 0 }

# 1. Python >= 3.11
$Py = $null
foreach ($cand in @(@("py", "-3.13"), @("py", "-3.12"), @("py", "-3.11"), @("python"))) {
  try {
    & $cand[0] $cand[1..9] -c "import sys; sys.exit(sys.version_info < (3, 11))" 2>$null
    if ($LASTEXITCODE -eq 0) { $Py = $cand; break }
  } catch {}
}
if (-not $Py) { "ERROR: hace falta Python 3.11+.  winget install Python.Python.3.12"; exit 1 }

# 2. ffmpeg
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    "Instalando ffmpeg con winget…"
    winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    "Cierra y vuelve a abrir la terminal para que ffmpeg quede en el PATH, y corre este script otra vez."
    exit 1
  }
  "ERROR: falta ffmpeg.  winget install Gyan.FFmpeg"; exit 1
}

# 3. venv + dependencias
New-Item -ItemType Directory -Force -Path $HomeDir | Out-Null
if (-not (Test-Path $VenvPy)) { & $Py[0] $Py[1..9] -m venv $Venv }
& $VenvPy -m pip install -q --upgrade pip
"Instalando dependencias (la primera vez tarda 1-3 min)…"
& $VenvPy -m pip install -q -r $Req
if ($LASTEXITCODE -ne 0) { "ERROR: falló pip install"; exit 1 }
& $VenvPy -c "import yt_dlp, scenedetect, faster_whisper, jsonschema, cv2; print('Modulos OK')"
Set-Content -Path $Marker -Value $Hash
"reel-analyzer: instalación completa ($Venv)"
