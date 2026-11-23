# Avisos de terceros

## bradautomates/claude-video (MIT)

`reelkit/frames.py` adapta del archivo `skills/watch/scripts/frames.py` de
https://github.com/bradautomates/claude-video la técnica de deduplicación de cuadros
(miniatura RGB 16×16 vía ffmpeg, diferencia media por píxel contra el último cuadro
conservado, umbral 2.0). Su licencia:

```
MIT License

Copyright (c) 2026 Bradley Bonanno

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Dependencias que se instalan aparte (no se incluyen en este repo)

| Paquete | Licencia | Cómo se usa |
|---|---|---|
| yt-dlp | Unlicense | Se ejecuta como módulo (`python -m yt_dlp`) |
| gallery-dl | GPL-2.0 | Se ejecuta como programa aparte (subproceso), solo como respaldo para Instagram; no se importa ni se distribuye |
| PySceneDetect (`scenedetect`) | BSD-3-Clause | Detección de escenas, en un subproceso |
| faster-whisper | MIT | Transcripción local |
| jsonschema | MIT | Validación de `analysis.json` |
| FFmpeg | LGPL/GPL según la compilación | Programa externo del sistema |
| Deno | MIT | Runtime de JavaScript que yt-dlp necesita para YouTube |
