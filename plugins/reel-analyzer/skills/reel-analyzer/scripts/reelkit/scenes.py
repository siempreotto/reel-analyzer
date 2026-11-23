"""Detección de escenas con PySceneDetect (AdaptiveDetector).

Se ejecuta en un subproceso: OpenCV y PyAV (que trae faster-whisper) cargan cada uno
su propia libavdevice y en macOS chocan si viven en el mismo proceso.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import proc


def detect_scenes(video: Path, duration: float) -> list[tuple[float, float]]:
    r = proc.run([*proc.python_module("reelkit.scenes"), str(video)], timeout=900,
                 cwd=str(Path(__file__).resolve().parent.parent))
    scenes: list[tuple[float, float]] = []
    if r.returncode == 0:
        try:
            scenes = [(float(a), float(b)) for a, b in json.loads(r.stdout.strip().splitlines()[-1])]
        except (ValueError, IndexError):
            scenes = []
    else:
        print(f"[reelkit] detección de escenas falló, uso una sola escena: {r.stderr[-300:]}", file=sys.stderr)
    return normalize(scenes, duration)


def normalize(scenes: list[tuple[float, float]], duration: float, min_len: float = 0.3) -> list[tuple[float, float]]:
    """Ordena, cubre [0, duración] sin huecos y une escenas demasiado cortas."""
    if duration <= 0:
        return []
    cuts = sorted({round(s, 3) for s, _ in scenes if 0 < s < duration})
    bounds = [0.0, *cuts, round(duration, 3)]
    out: list[list[float]] = []
    for a, b in zip(bounds, bounds[1:]):
        if out and b - a < min_len:
            out[-1][1] = b
        else:
            out.append([a, b])
    if len(out) > 1 and out[0][1] - out[0][0] < min_len:
        out[1][0] = 0.0
        out.pop(0)
    return [(round(a, 2), round(b, 2)) for a, b in out]


def _main(path: str) -> None:
    from scenedetect import AdaptiveDetector, detect

    result = detect(path, AdaptiveDetector(min_scene_len=8))
    print(json.dumps([[s.seconds, e.seconds] for s, e in result]))


if __name__ == "__main__":
    _main(sys.argv[1])
