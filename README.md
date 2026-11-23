# reel-analyzer

Pega el link de un **reel de Instagram, YouTube Short, TikTok, video de X o reel de Facebook** (o
adjunta un MP4) y Claude te entrega:

1. **Desglose escena por escena:** qué se ve, el texto en pantalla, lo que se dice y el audio no verbal (música, silencios, volumen).
2. **Por qué funciona** el hook y la estructura.
3. **ADN del formato:** la estructura abstracta, sin el contenido original.
4. **Guion original para tu marca:** shot list, 3 hooks alternativos, caption, CTA y lista de producción.

Todo en español. El video se procesa en tu computadora y se borra al terminar.

---

## Instalación

### Opción A: Claude Code (recomendada; funciona con links)

En una terminal:

```bash
claude plugin marketplace add siempreotto/reel-analyzer
claude plugin install reel-analyzer@reel-analyzer
```

O dentro de Claude Code: `/plugin marketplace add siempreotto/reel-analyzer` y después `/plugin`
para instalar **reel-analyzer** desde el panel.

La primera vez que lo uses, la skill instala sola lo que necesita en `~/.reel-analyzer/`. Tarda
unos minutos. Instala:
- Python 3.11 o superior, si no lo tienes (en macOS, con Homebrew);
- ffmpeg;
- yt-dlp, gallery-dl, PySceneDetect y faster-whisper;
- Deno.

### Opción B: Claude en la web o la app (sin instalar nada técnico)

1. Descarga [`reel-analyzer-skill.zip`](https://github.com/siempreotto/reel-analyzer/releases/latest)
   desde los Releases.
2. En claude.ai, ve a **Configuración → Capacidades → Skills**, presiona **Subir skill** y elige
   el zip. Necesitas la ejecución de código activada.
3. Descarga el reel en tu teléfono o computadora y **adjúntalo** al chat con "analiza este reel".

> En la web de Claude **no se puede descargar desde el link**. El entorno de Claude no tiene acceso
> libre a internet, así que la skill te pide el MP4. La transcripción allí depende de que el entorno
> pueda bajar el modelo de Whisper. Si no puede, el análisis sigue con los cuadros y el audio
> medido, y te avisa.

---

## Uso

```
analiza este reel https://www.instagram.com/reel/XXXX/
/reel https://youtube.com/shorts/XXXX
/reel https://www.tiktok.com/@cuenta/video/123 rápido
replica este formato para mi marca de café: <link>
compara estos tres: <link1> <link2> <link3>
```

- **Modo completo** (por defecto): ficha, hook, tabla escena por escena, ritmo y audio, por qué funciona, ADN y guion completo.
- **Modo rápido:** ficha, hook, ADN y guion corto. Se activa con "rápido" o cuando pasas varios links.
- **Tu marca:** la primera vez te la pregunta y la guarda en `~/.reel-analyzer/marcas.md`.

### Ejemplo de salida (resumido)

| # | Tiempo | Visual | Texto en pantalla | Voz | Audio | Función |
|---|---|---|---|---|---|---|
| 1 | 0:00–0:02 | Primer plano, entra caminando hacia la cámara | "3 errores al grabar reels" | "Tres errores que cometes…" | Golpe + música baja | Hook |
| 2 | 0:02–0:05 | Plano medio, corte en salto | "1. Hablas lento" | "Primero, hablas demasiado lento" | Música sigue, −16 LUFS | Paso 1 |

**ADN:** `[0–2 s] lista numerada prometida + texto grande → [2–12 s] un paso por corte (2–3 s c/u) → [final] CTA de seguir`

### Uso directo (sin Claude)

```bash
~/.reel-analyzer/venv/bin/python plugins/reel-analyzer/skills/reel-analyzer/scripts/analyze.py "<link>" --out ./reels
~/.reel-analyzer/venv/bin/python plugins/reel-analyzer/skills/reel-analyzer/scripts/analyze.py --file video.mp4 --modo rapido
```

Genera `./reels/<plataforma>_<id>/` con:
- `analysis.json`: escenas, hook, ritmo, audio y transcripción;
- `timeline.md`;
- `frames/t_SS.ss.jpg`.

Opciones: `--cookies-from-browser chrome`, `--keep` (conserva el video), `--sin-transcripcion`.

---

## Solución de problemas

| Mensaje | Qué hacer |
|---|---|
| `IG_LOGIN_REQUIRED` | Instagram solo deja descargar con una sesión iniciada. Entra a instagram.com en tu navegador, de preferencia con una **cuenta secundaria**, y pide: "reintenta con mi sesión de Chrome". Por debajo usa `--cookies-from-browser chrome`. En macOS puede aparecer un aviso del llavero: acéptalo. |
| `IG_HTML_RESPONSE` | Instagram cambió algo. Actualiza: `~/.reel-analyzer/venv/bin/pip install -U yt-dlp gallery-dl`. Si sigue fallando, adjunta el MP4. |
| `EXTRACTOR_BROKEN` | La skill ya intentó actualizar yt-dlp sola. Si persiste, espera unos días (yt-dlp se arregla rápido) o adjunta el MP4. |
| `COOKIES_REQUIRED` | YouTube o TikTok pide verificación (edad o "no eres un bot"). Usa tu sesión del navegador como en Instagram. |
| `PRIVATE_OR_DELETED` | El video es privado, se borró o no está disponible en tu país. |
| `NETWORK_BLOCKED` | No hay internet en ese entorno, por ejemplo en claude.ai. Adjunta el MP4. |
| `FFMPEG_MISSING` | Corre `bash plugins/reel-analyzer/skills/reel-analyzer/scripts/setup.sh`. En Windows, `setup.ps1`. |

Para reinstalar desde cero, borra `~/.reel-analyzer/venv` y `~/.reel-analyzer/.ok`.

## Limitaciones

- **Instagram es frágil:** en 2026 solo funciona con cookies y se rompe cada tanto. yt-dlp y gallery-dl lo arreglan en días; aquí una GitHub Action semanal actualiza yt-dlp y corre los tests.
- **Sin OCR:** Claude lee el texto en pantalla directamente de los cuadros. Los textos muy pequeños o muy rápidos pueden escapársele, y lo dice.
- **Música estimada:** `musica_probable` es una heurística por energía de audio, no un detector de música.
- **Nombres propios:** Whisper a veces los escribe mal.
- **Costo:** cada cuadro es una imagen. El modo completo manda como máximo 40 cuadros, unos 15 000 tokens en un reel vertical.

## Aviso legal y de uso responsable

Esta herramienta es para **estudiar el formato** de un video y escribir un **guion original**. No
re-publiques ni redistribuyas videos de otros, ni copies su texto, su voz o sus ejemplos.

Los términos de servicio de las plataformas limitan la descarga automatizada:
- **YouTube** prohíbe descargar contenido sin autorización y acceder por medios automatizados.
- **Meta (Instagram/Facebook)** prohíbe recolectar datos con medios automatizados sin permiso.
- **TikTok** prohíbe extraer contenido con sistemas automatizados sin aprobación escrita.

Descargar puede ir contra esos términos y llevar a la suspensión de la cuenta cuyas cookies uses.
Por eso conviene una cuenta secundaria. El riesgo y la decisión son tuyos. Esto no es asesoría
legal: consulta a un abogado de tu país si vas a usarlo comercialmente.

Para reducir riesgos:
- todo corre en tu computadora y con tu sesión;
- el video se borra al terminar;
- siempre puedes adjuntar un archivo propio en vez de un link.

## Desarrollo

```bash
bash plugins/reel-analyzer/skills/reel-analyzer/scripts/setup.sh
~/.reel-analyzer/venv/bin/pip install pytest
~/.reel-analyzer/venv/bin/python -m pytest -q
```

- `REEL_TEST_WHISPER=1` activa la prueba con Whisper real (macOS).
- `bash scripts/build_zip.sh` arma `dist/reel-analyzer-skill.zip` para claude.ai.
- `bash scripts/publish_whisper_models.sh siempreotto/reel-analyzer` publica los pesos de Whisper como assets de un release. Sirve de respaldo donde Hugging Face está bloqueado.

Para publicar una versión nueva: `claude plugin validate .`, `bash scripts/build_zip.sh` y un release con el zip adjunto.

Licencia MIT. Ver [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
