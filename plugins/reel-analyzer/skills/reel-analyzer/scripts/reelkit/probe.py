"""ffprobe: duración, tamaño y si hay audio."""
from __future__ import annotations

import json
from pathlib import Path

from . import proc
from .errors import ReelError


def require_ffmpeg() -> None:
    if not proc.which("ffmpeg") or not proc.which("ffprobe"):
        raise ReelError("FFMPEG_MISSING", "Falta ffmpeg en este equipo.",
                        "Corre scripts/setup.sh (o: brew install ffmpeg / sudo apt install ffmpeg / "
                        "winget install Gyan.FFmpeg).")


def probe(video: Path) -> dict:
    r = proc.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)],
                 timeout=60)
    if r.returncode != 0:
        raise ReelError("BAD_VIDEO", "El archivo no parece un video válido.",
                        "Prueba con otro MP4 o vuelve a descargarlo.", r.stderr)
    data = json.loads(r.stdout or "{}")
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if v is None:
        raise ReelError("BAD_VIDEO", "El archivo no tiene pista de video.", "Adjunta el video, no solo el audio.")
    dur = float(data.get("format", {}).get("duration") or v.get("duration") or 0)
    w, h = int(v.get("width") or 0), int(v.get("height") or 0)
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = abs(int(sd["rotation"]))
    if rot in (90, 270):
        w, h = h, w
    return {"duracion_s": round(dur, 2), "ancho": w, "alto": h, "tiene_audio": a is not None,
            "orientacion": "vertical" if h > w else ("horizontal" if w > h else "cuadrado")}
