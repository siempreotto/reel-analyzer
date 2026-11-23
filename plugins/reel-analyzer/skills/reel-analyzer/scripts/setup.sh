#!/usr/bin/env bash
# Instala (una sola vez) lo que necesita reel-analyzer en ~/.reel-analyzer/venv.
# Idempotente: si el marcador coincide con el hash de requirements.txt, no hace nada.
#
#   setup.sh           instala o verifica
#   setup.sh --check   solo verifica (exit 0 = listo, 2 = falta algo); no instala
set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="${REEL_ANALYZER_HOME:-$HOME/.reel-analyzer}"
VENV="$HOME_DIR/venv"
MARKER="$HOME_DIR/.ok"
REQ="$SCRIPTS_DIR/requirements.txt"

hash_req() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$REQ" | cut -d' ' -f1
  else sha256sum "$REQ" | cut -d' ' -f1; fi
}

ready() {
  [ -x "$VENV/bin/python" ] && [ -f "$MARKER" ] && [ "$(cat "$MARKER")" = "$(hash_req)" ] \
    && command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1
}

if [ "${1:-}" = "--check" ]; then
  if ready; then echo "reel-analyzer: listo"; exit 0; fi
  echo "reel-analyzer: falta instalar (corre setup.sh)"; exit 2
fi

if ready; then echo "reel-analyzer: todo instalado ($VENV)"; exit 0; fi

# 1. Python >= 3.11 (yt-dlp 2026.10.26 ya no soporta 3.10)
PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    PY="$(command -v "$c")"; break
  fi
done
if [ -z "$PY" ]; then
  echo "ERROR: hace falta Python 3.11 o superior."
  echo "  macOS:  brew install python@3.12"
  echo "  Ubuntu: sudo apt install python3.12 python3.12-venv"
  exit 1
fi
echo "Python: $PY ($("$PY" --version))"

# 2. ffmpeg + ffprobe
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "Instalando ffmpeg con Homebrew…"; brew install ffmpeg
  elif command -v apt-get >/dev/null 2>&1 && [ "$(id -u)" = "0" ]; then
    apt-get update -qq && apt-get install -y -qq ffmpeg
  else
    echo "ERROR: falta ffmpeg. Instálalo y vuelve a correr este script:"
    echo "  macOS:   brew install ffmpeg"
    echo "  Ubuntu:  sudo apt install ffmpeg"
    echo "  Windows: winget install Gyan.FFmpeg"
    exit 1
  fi
fi
echo "ffmpeg: $(command -v ffmpeg)"

# 3. venv + dependencias fijadas (Deno para YouTube llega como paquete de pip, extra [deno] de yt-dlp)
mkdir -p "$HOME_DIR"
if [ ! -x "$VENV/bin/python" ]; then
  echo "Creando venv en $VENV…"
  "$PY" -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install -q --upgrade pip
echo "Instalando dependencias (la primera vez tarda 1–3 min)…"
"$VENV/bin/python" -m pip install -q -r "$REQ"

# 4. Verificación rápida
"$VENV/bin/python" - <<'PYCHECK'
import importlib, shutil, sys, os
for mod in ("yt_dlp", "scenedetect", "faster_whisper", "jsonschema", "cv2"):
    importlib.import_module(mod)
venv_bin = os.path.dirname(sys.executable)
if not (shutil.which("deno") or os.path.exists(os.path.join(venv_bin, "deno"))):
    print("AVISO: no se encontró Deno; YouTube podría fallar.")
print("Módulos OK")
PYCHECK

hash_req > "$MARKER"
echo "reel-analyzer: instalación completa ($VENV)"
