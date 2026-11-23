"""Selección y extracción de cuadros.

- Hook denso: 0, 0.5, 1 … 3 s (7 cuadros), sin dedup: el hook se mira entero.
- 1 cuadro por escena (2 si dura más de 4 s). Las escenas que caen dentro del hook
  reutilizan el cuadro del hook más cercano.
- Sin cortes ("talking head"): muestreo uniforme después del hook.
- Dedup contra el último cuadro conservado y tope de cuadros por modo.

La idea del dedup (miniatura RGB 16×16, diferencia media por píxel contra el último
cuadro conservado, umbral 2.0) viene de bradautomates/claude-video (MIT);
ver THIRD_PARTY_NOTICES.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import proc

HOOK_END = 3.0
HOOK_STEP = 0.5
DEDUP_THUMB = 16
DEDUP_THRESHOLD = 2.0

MODES = {
    # lado largo en px, tope total de cuadros, cuadros extra por escena larga
    "completo": {"long_side": 720, "max_frames": 40, "two_per_long_scene": True},
    "rapido": {"long_side": 512, "max_frames": 20, "two_per_long_scene": False},
}


@dataclass
class Frame:
    t: float
    path: Path
    kind: str                       # hook | escena | uniforme
    escenas: list[int] = field(default_factory=list)

    @property
    def rel(self) -> str:
        return f"frames/{self.path.name}"


def frame_name(t: float) -> str:
    return f"t_{t:06.2f}.jpg"


def _scale(long_side: int, w: int, h: int) -> str:
    if h >= w:
        return f"scale=-2:{min(long_side, h or long_side)}"
    return f"scale={min(long_side, w or long_side)}:-2"


def extract_at(video: Path, t: float, out: Path, long_side: int, w: int, h: int) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
           "-vf", _scale(long_side, w, h), "-q:v", "3", str(out)]
    r = proc.run(cmd, timeout=60)
    return r.returncode == 0 and out.exists() and out.stat().st_size > 0


def thumb(path: Path) -> bytes:
    """Miniatura RGB 16×16 en bytes crudos (salida binaria, por eso sin proc.run)."""
    import subprocess
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf",
                        f"scale={DEDUP_THUMB}:{DEDUP_THUMB},format=rgb24", "-f", "rawvideo", "-"],
                       capture_output=True, env=proc.env(), timeout=30)
    return r.stdout if r.returncode == 0 else b""


def delta(a: bytes, b: bytes) -> float:
    if not a or len(a) != len(b):
        return float("inf")
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def plan_times(scenes: list[tuple[float, float]], duration: float, mode: str) -> list[tuple[float, str, int | None]]:
    """Devuelve [(t, tipo, n_escena)] ordenado, antes de dedup y tope."""
    cfg = MODES[mode]
    end_cap = max(0.0, duration - 0.05)
    plan: list[tuple[float, str, int | None]] = []
    t = 0.0
    while t <= HOOK_END + 1e-9:
        plan.append((round(min(t, end_cap), 2), "hook", None))
        t += HOOK_STEP
    for i, (a, b) in enumerate(scenes, start=1):
        length = b - a
        if b <= HOOK_END + 0.25:
            continue  # cubierta por el hook
        lo = max(a, HOOK_END)
        if cfg["two_per_long_scene"] and length > 4.0:
            pts = [lo + (b - lo) / 3, lo + 2 * (b - lo) / 3]
        else:
            pts = [(lo + b) / 2]
        for p in pts:
            plan.append((round(min(p, end_cap), 2), "escena", i))
    # Tomas largas ("talking head" o plano único): muestreo uniforme dentro de la toma,
    # porque ahí lo que cambia es el gesto, el texto en pantalla o el encuadre, no el corte.
    for i, (a, b) in enumerate(scenes, start=1):
        lo = max(a, HOOK_END)
        if b - lo <= 6.0:
            continue
        step = max(2.5, (b - lo) / 10)
        t = lo + step
        while t < b - 0.5:
            plan.append((round(min(t, end_cap), 2), "uniforme", i))
            t += step
    plan.sort(key=lambda x: (x[0], x[1] != "hook"))
    dedup: list[tuple[float, str, int | None]] = []
    for item in plan:
        if dedup and abs(dedup[-1][0] - item[0]) < 0.75 and item[1] != "hook":
            continue
        if dedup and abs(dedup[-1][0] - item[0]) < 0.01:
            continue
        dedup.append(item)
    return dedup


def scene_of(t: float, scenes: list[tuple[float, float]]) -> int:
    for i, (a, b) in enumerate(scenes, start=1):
        if a <= t < b:
            return i
    return len(scenes)


def extract(video: Path, outdir: Path, scenes: list[tuple[float, float]], duration: float,
            w: int, h: int, mode: str = "completo") -> list[Frame]:
    cfg = MODES[mode]
    frames_dir = outdir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    plan = plan_times(scenes, duration, mode)

    hook = [p for p in plan if p[1] == "hook"]
    rest = [p for p in plan if p[1] != "hook"]
    budget = max(0, cfg["max_frames"] - len(hook))
    if len(rest) > budget:
        # Prioriza 1 cuadro por escena; luego reparte uniforme.
        firsts, seen = [], set()
        for p in rest:
            if p[1] == "escena" and p[2] not in seen:
                firsts.append(p)
                seen.add(p[2])
        pool = firsts if len(firsts) >= budget else firsts + [p for p in rest if p not in firsts]
        if len(pool) > budget:
            idx = [round(i * (len(pool) - 1) / max(1, budget - 1)) for i in range(budget)] if budget > 1 else [0]
            pool = [pool[i] for i in sorted(set(idx))][:budget]
        rest = sorted(pool[:budget], key=lambda x: x[0])

    out: list[Frame] = []
    last_thumb = b""
    for t, kind, _n in hook + rest:
        path = frames_dir / frame_name(t)
        if not extract_at(video, t, path, cfg["long_side"], w, h):
            continue
        if kind != "hook":
            th = thumb(path)
            if last_thumb and delta(th, last_thumb) <= DEDUP_THRESHOLD:
                path.unlink(missing_ok=True)
                continue
            last_thumb = th
        else:
            last_thumb = thumb(path)
        out.append(Frame(t, path, kind))
    out.sort(key=lambda f: f.t)
    for f in out:
        f.escenas = [scene_of(f.t, scenes)]
    return out


def frames_for_scene(frames: list[Frame], a: float, b: float, n: int) -> list[str]:
    inside = [f.rel for f in frames if a <= f.t < b]
    if inside:
        return inside
    # escena sin cuadro propio (dedup o tope): el cuadro más cercano
    if not frames:
        return []
    mid = (a + b) / 2
    return [min(frames, key=lambda f: abs(f.t - mid)).rel]


def estimate_tokens(frames: list[Frame]) -> int:
    total = 0
    for f in frames:
        try:
            w, h = _jpeg_size(f.path)
        except Exception:  # noqa: BLE001
            w, h = 405, 720
        total += round(w * h / 750)
    return total


def _jpeg_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            h = int.from_bytes(data[i + 5:i + 7], "big")
            w = int.from_bytes(data[i + 7:i + 9], "big")
            return w, h
        seg = int.from_bytes(data[i + 2:i + 4], "big")
        i += 2 + seg
    raise ValueError("sin SOF")
