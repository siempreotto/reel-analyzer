"""Audio no verbal medido con ffmpeg: loudness EBU R128, silencios y energía por segundo.

"musica_probable" es una ESTIMACIÓN heurística (energía sostenida donde nadie habla),
no un clasificador de música.
"""
from __future__ import annotations

import math
import re
import struct
import subprocess
from pathlib import Path

from . import proc

SR = 8000  # suficiente para energía por segundo

_M = re.compile(r"t:\s*([\d.]+)\s+TARGET:.*?M:\s*(-?[\d.]+|-inf)", re.I)
_I = re.compile(r"I:\s*(-?[\d.]+)\s*LUFS")
_LRA = re.compile(r"LRA:\s*([\d.]+)\s*LU")
_SIL_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SIL_END = re.compile(r"silence_end:\s*([\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)")


def analyze(video: Path, duration: float, has_audio: bool) -> dict:
    if not has_audio:
        return {"tiene_audio": False, "lufs_integrado": None, "rango_lra": None, "silencios": [],
                "energia_db_por_segundo": [], "momentary": [], "musica_probable": None}
    # -v verbose: ffmpeg ≥ 7 solo imprime el registro por cuadro de ebur128 a nivel verbose.
    r = proc.run(["ffmpeg", "-hide_banner", "-nostats", "-v", "verbose", "-i", str(video), "-vn",
                  "-af", "ebur128=framelog=verbose,silencedetect=noise=-35dB:d=0.4", "-f", "null", "-"],
                 timeout=600)
    log = r.stderr or ""
    momentary = []
    for t, m in _M.findall(log):
        momentary.append((float(t), None if m == "-inf" else float(m)))
    summary = log[log.rfind("Summary:"):] if "Summary:" in log else log
    i_m = _I.search(summary)
    lra = _LRA.search(summary)
    silencios = _silences(log, duration)
    energia = rms_per_second(video, duration)
    return {
        "tiene_audio": True,
        "lufs_integrado": float(i_m.group(1)) if i_m else None,
        "rango_lra": float(lra.group(1)) if lra else None,
        "silencios": silencios,
        "energia_db_por_segundo": energia,
        "momentary": momentary,
        "musica_probable": None,  # se calcula en build con la transcripción
    }


def _silences(log: str, duration: float) -> list[dict]:
    starts = [float(x) for x in _SIL_START.findall(log)]
    ends = [(float(e), float(d)) for e, d in _SIL_END.findall(log)]
    out = []
    for i, s in enumerate(starts):
        e = ends[i][0] if i < len(ends) else duration
        out.append({"inicio": round(max(0.0, s), 2), "fin": round(min(e, duration), 2),
                    "dur": round(min(e, duration) - max(0.0, s), 2)})
    return out


def rms_per_second(video: Path, duration: float) -> list[float]:
    """dBFS por segundo (mono, 8 kHz)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", str(SR),
                        "-f", "s16le", "-"], capture_output=True, env=proc.env(), timeout=600)
    if r.returncode != 0 or not r.stdout:
        return []
    data = r.stdout
    n = len(data) // 2
    samples = struct.unpack(f"<{n}h", data[: n * 2])
    out = []
    for i in range(0, n, SR):
        chunk = samples[i:i + SR]
        if len(chunk) < SR // 4:
            break
        ms = sum(s * s for s in chunk) / len(chunk)
        out.append(round(20 * math.log10(math.sqrt(ms) / 32768), 1) if ms > 0 else -96.0)
    return out


def loudness_between(momentary: list[tuple[float, float | None]], a: float, b: float) -> float | None:
    """Promedio energético de la loudness momentánea (ventana 400 ms) en [a, b)."""
    vals = [m for t, m in momentary if a <= t - 0.4 < b and m is not None and m > -70]
    if not vals:
        return None
    lin = sum(10 ** (v / 10) for v in vals) / len(vals)
    return round(10 * math.log10(lin), 1)


def is_silent_between(silencios: list[dict], a: float, b: float, frac: float = 0.6) -> bool:
    if b <= a:
        return False
    cov = sum(max(0.0, min(b, s["fin"]) - max(a, s["inicio"])) for s in silencios)
    return cov / (b - a) >= frac


def music_probable(energia: list[float], speech: list[tuple[float, float]], silencios: list[dict],
                   duration: float) -> bool | None:
    """Heurística: hay música si suena energía sostenida en los segundos sin voz,
    o si (sin transcripción) casi no hay silencios y la energía es pareja."""
    if not energia:
        return None
    def near_speech(sec: int) -> bool:
        # un segundo cuenta como "sin voz" solo si no toca ningún segmento (±0.3 s de margen)
        return any(s - 0.3 < sec + 1 and sec < e + 0.3 for s, e in speech)
    if speech:
        non_speech = [db for i, db in enumerate(energia) if not near_speech(i)]
        if len(non_speech) < 3:
            return None  # la voz cubre casi todo: la energía no distingue si hay música debajo
        loud = [db for db in non_speech if db > -40]
        return len(loud) / len(non_speech) >= 0.5
    silent = sum(s["dur"] for s in silencios)
    if duration <= 0:
        return None
    mean = sum(energia) / len(energia)
    var = sum((x - mean) ** 2 for x in energia) / len(energia)
    return silent / duration < 0.05 and math.sqrt(var) < 6 and mean > -35
