#!/usr/bin/env bash
# Publica los pesos de faster-whisper como assets del release "whisper-models" del repo,
# para entornos donde Hugging Face está bloqueado pero GitHub no (p. ej. el sandbox de claude.ai).
#
# Uso:  bash scripts/publish_whisper_models.sh <usuario>/reel-analyzer [base small]
# Requiere: gh autenticado con permiso de escritura en el repo, y el venv de setup.sh.
set -euo pipefail
REPO="${1:?uso: publish_whisper_models.sh <usuario>/reel-analyzer [tamaños…]}"
shift || true
SIZES=("${@:-base small}")
[ $# -eq 0 ] && SIZES=(base small)
PY="${PY:-$HOME/.reel-analyzer/venv/bin/python}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

for SIZE in "${SIZES[@]}"; do
  echo "Bajando faster-whisper-$SIZE de Hugging Face…"
  SRC=$("$PY" -c "from faster_whisper.utils import download_model; print(download_model('$SIZE'))")
  mkdir -p "$WORK/faster-whisper-$SIZE"
  cp -L "$SRC"/* "$WORK/faster-whisper-$SIZE/"
  tar -C "$WORK" -czf "$WORK/faster-whisper-$SIZE.tar.gz" "faster-whisper-$SIZE"
  ls -lh "$WORK/faster-whisper-$SIZE.tar.gz"
done

gh release view whisper-models --repo "$REPO" >/dev/null 2>&1 || \
  gh release create whisper-models --repo "$REPO" --title "Modelos de Whisper (respaldo)" \
    --notes "Pesos de faster-whisper (modelos de Systran, licencia MIT) para entornos sin acceso a Hugging Face."
gh release upload whisper-models --repo "$REPO" --clobber "$WORK"/faster-whisper-*.tar.gz
echo "Listo. reelkit los baja de https://github.com/$REPO/releases/download/whisper-models/"
