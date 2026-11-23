---
name: reel-analyzer
description: Desglosa un video corto (Instagram Reels, YouTube Shorts, TikTok, X o Facebook) escena por escena — visual, texto en pantalla, voz y audio no verbal — y escribe un guion original para replicar el formato con la marca del usuario, en español. Úsala cuando el usuario pegue un link de instagram.com/reel, instagram.com/p, youtube.com/shorts, youtu.be, tiktok.com, vm.tiktok.com, x.com, twitter.com, facebook.com/reel o fb.watch, o adjunte un MP4, y diga cosas como "analiza este reel", "desglosa este video", "replica este formato", "por qué se hizo viral", "hazme un guion como este" o "qué tiene este reel". También para comparar varios reels y sacar patrones.
license: MIT
allowed-tools: Bash, Read, Write
---

# reel-analyzer

Convierte un reel en evidencia (escenas, cuadros, transcripción y audio medido) y la usa para
explicar por qué funciona y escribir un guion **original** con el mismo formato.

`SKILL_DIR` es la carpeta de este archivo; los scripts están en `$SKILL_DIR/scripts/`.

## Reglas

- Se replica el **formato**, nunca el contenido: no reutilices frases, chistes, ejemplos ni la voz
  del creador. Nunca re-subas ni redistribuyas el video.
- Afirma solo lo que respalda la evidencia: cuadros que abriste, `analysis.json`, `timeline.md`.
  Si no hay transcripción, la voz se deduce de los cuadros y lo dices.
- La primera vez que `analyze.py` imprime `AVISO DE USO RESPONSABLE`, muéstraselo al usuario en
  una línea. No lo repitas después.
- No narres la instalación paso a paso: una línea de estado basta.

## 1. Preparar el entorno (una vez)

```bash
bash "$SKILL_DIR/scripts/setup.sh" --check || bash "$SKILL_DIR/scripts/setup.sh"
PY="$HOME/.reel-analyzer/venv/bin/python"
```

- Windows: `powershell -ExecutionPolicy Bypass -File "$SKILL_DIR/scripts/setup.ps1"` y
  `PY="$HOME/.reel-analyzer/venv/Scripts/python.exe"`.
- Instala sin preguntar (la primera vez tarda unos minutos; avisa en una línea).
- Si `setup.sh` no puede crear el venv (p. ej. un sandbox), instala directo y usa `python3`:
  `pip install -q --break-system-packages -r "$SKILL_DIR/scripts/requirements.txt"` → `PY=python3`.
  Verifica `ffmpeg -version`; si falta y eres root: `apt-get install -y ffmpeg`.
- Si falta ffmpeg y no se puede instalar, dile al usuario el comando exacto que imprimió el setup.

## 2. Pedir la marca (solo si hace falta)

Lee `~/.reel-analyzer/marcas.md`. Si existe, usa la marca guardada (o la que el usuario nombre).
Si no existe y el modo incluye guion, pregunta **una vez**: marca, qué vende, a quién le habla,
tono y CTA habitual. Guárdalo en `~/.reel-analyzer/marcas.md` (crea la carpeta si falta) para la
próxima. Puedes correr el análisis mientras esperas la respuesta.

## 3. Analizar

```bash
"$PY" "$SKILL_DIR/scripts/analyze.py" "<URL>" --out ./reels --modo completo
"$PY" "$SKILL_DIR/scripts/analyze.py" --file "<ruta.mp4>" --out ./reels      # archivo adjunto
"$PY" "$SKILL_DIR/scripts/analyze.py" "<URL1>" "<URL2>" "<URL3>" --out ./reels --modo rapido   # varios
```

- `--modo rapido` cuando el usuario pida algo rápido o pase 3+ links; `completo` por defecto.
- `--keep` solo si el usuario quiere conservar el video. `--sin-transcripcion` si tiene prisa.
- Corre el comando con timeout amplio (la primera transcripción baja el modelo de Whisper, ~500 MB).

### Si falla

`analyze.py` imprime `ERROR <CÓDIGO>: …` y `→ <acción>`. Actúa así:

| Código | Qué hacer |
|---|---|
| `NETWORK_BLOCKED` (exit 3) | Di exactamente: "En esta versión de Claude no puedo descargar desde el link; descarga el reel y adjúntalo aquí." Cuando lo adjunte, corre con `--file`. |
| `IG_LOGIN_REQUIRED`, `COOKIES_REQUIRED` | Pregunta qué navegador usa (con sesión iniciada en esa plataforma) y reintenta con `--cookies-from-browser <chrome\|safari\|firefox\|edge\|brave>`. Recomienda una cuenta secundaria. En macOS, Safari/Chrome pueden pedir permiso del llavero: avísale. |
| `IG_HTML_RESPONSE`, `EXTRACTOR_BROKEN` | Ya se reintentó con yt-dlp actualizado y con gallery-dl. Ofrece adjuntar el MP4. |
| `PRIVATE_OR_DELETED`, `UNSUPPORTED_URL` | Relaya el mensaje y pide otro link o el MP4. |

En claude.ai los archivos adjuntos suelen estar en `/mnt/user-data/uploads/`.

## 4. Ver el video

Por cada video, en `./reels/<plataforma>_<id>/`:

1. Lee `timeline.md` completo (resumen, transcripción con tiempos, audio por escena).
2. Abre con Read **todos** los cuadros del hook (`hook.frames`, 7 cuadros de 0 a 3 s).
3. Abre 1–2 cuadros por escena (`escenas[].frames`). En modo rápido, uno por escena basta.
4. Consulta `analysis.json` para números exactos (`ritmo`, `audio_global`, `escenas[].audio`).
5. Lee el texto en pantalla directo de los cuadros (no hay OCR). Si un texto no se lee bien,
   dilo en vez de adivinarlo.

`cuadros.tokens_estimados` dice cuánto cuesta ver todo; no abras cuadros que no aportan.

## 5. Entregar

Sigue `references/plantilla.md` (léela antes de escribir):

1. Ficha · 2. Hook (0–3 s) y por qué detiene el scroll · 3. Tabla escena por escena
(tiempo | visual/encuadre/movimiento | texto en pantalla | voz | audio no verbal | función) ·
4. Ritmo y audio · 5. Por qué funciona (3–5) · 6. ADN del formato · 7. Guion de réplica para la
marca (shot list, 3 hooks alternativos, caption, CTA, lista de producción).

- **Modo rápido:** Ficha + Hook + ADN + guion corto.
- **Varios links:** un desglose por video y cierra con el comparativo de patrones de la plantilla.
- Avisos de `analysis.json` que importen (sin transcripción, nombres propios dudosos, música
  estimada): menciónalos en una línea al final, no al principio.
- Al terminar, el video ya se borró (salvo `--keep`). Los cuadros quedan en `./reels/`; dilo si el
  usuario quiere borrarlos.
