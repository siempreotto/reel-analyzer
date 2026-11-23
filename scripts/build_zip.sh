#!/usr/bin/env bash
# Empaqueta la skill para subirla a claude.ai (Configuración → Capacidades → Skills).
# Resultado: dist/reel-analyzer-skill.zip con la carpeta reel-analyzer/ (SKILL.md en su raíz).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$ROOT/plugins/reel-analyzer/skills/reel-analyzer"
OUT="$ROOT/dist/reel-analyzer-skill.zip"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$ROOT/dist"
cp -R "$SKILL" "$STAGE/reel-analyzer"
find "$STAGE" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "$STAGE" -name ".DS_Store" -type f -exec rm -f {} +

# claude.ai limita la description a 200 caracteres (Claude Code admite más): en el zip va la corta.
SHORT="$(tr -d '\n' < "$ROOT/scripts/descripcion_corta.txt")"
[ "${#SHORT}" -le 200 ] || { echo "ERROR: descripcion_corta.txt pasa de 200 caracteres" >&2; exit 1; }
python3 - "$STAGE/reel-analyzer/SKILL.md" "$SHORT" <<'PY'
import re, sys
p, short = sys.argv[1], sys.argv[2]
t = open(p, encoding="utf-8").read()
t = re.sub(r"(?m)^description: .*$", "description: " + short.replace("\\", "\\\\"), t, count=1)
open(p, "w", encoding="utf-8").write(t)
PY
rm -f "$OUT"
(cd "$STAGE" && zip -qr -X "$OUT" reel-analyzer)

SIZE=$(wc -c < "$OUT" | tr -d ' ')
COUNT=$(unzip -Z1 "$OUT" | grep -vc '/$')
echo "dist/reel-analyzer-skill.zip: $COUNT archivos, $SIZE bytes"
# claude.ai no publica un límite de tamaño para el zip (nov-2026); 8 MB es un tope conservador propio.
MAX_BYTES="${MAX_SKILL_ZIP_BYTES:-8388608}"
if [ "$SIZE" -gt "$MAX_BYTES" ]; then
  echo "ERROR: el zip pasa el límite de $MAX_BYTES bytes" >&2
  exit 1
fi
unzip -Z1 "$OUT" | grep -q '^reel-analyzer/SKILL.md$' || { echo "ERROR: falta reel-analyzer/SKILL.md" >&2; exit 1; }
