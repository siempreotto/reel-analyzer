"""Arma analysis.json (valida contra schema.json) y timeline.md."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import __version__
from .audio import is_silent_between, loudness_between, music_probable
from .frames import HOOK_END, Frame, estimate_tokens, frames_for_scene

SCHEMA_PATH = Path(__file__).with_name("schema.json")


def _int(v):
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def meta_from_info(info: dict, platform: str, url: str | None, probe: dict) -> dict:
    fecha = info.get("upload_date")
    if fecha and len(fecha) == 8:
        fecha = f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:]}"
    # Instagram da en uploader_id un número interno; el @usuario viene en channel.
    handles = [info.get(k) for k in ("uploader_id", "channel")]
    handles = [str(h) for h in handles if h and not str(h).lstrip("@").isdigit()]
    cuenta = handles[0] if handles else info.get("uploader")
    if cuenta and platform in ("instagram", "tiktok", "x") and not str(cuenta).startswith("@"):
        cuenta = "@" + str(cuenta)
    return {
        "plataforma": platform,
        "id": str(info.get("id") or ""),
        "cuenta": cuenta,
        "url": url or info.get("webpage_url"),
        "titulo": info.get("title") or info.get("fulltitle"),
        "fecha": fecha,
        "duracion_s": probe["duracion_s"],
        "vistas": _int(info.get("view_count")),
        "likes": _int(info.get("like_count")),
        "comentarios": _int(info.get("comment_count")),
        "caption": info.get("description") or "",
        "resolucion": f"{probe['ancho']}x{probe['alto']}",
        "orientacion": probe["orientacion"],
    }


def _voice_between(segs: list[dict], a: float, b: float) -> str:
    """Lo que se dice en [a, b).

    Con tiempos por palabra (Whisper) se reparte palabra por palabra, así una frase que
    cruza varios cortes queda partida donde corresponde. Sin ellos (subtítulos), cada
    segmento va a la escena donde empieza.
    """
    out = []
    for s in segs:
        words = s.get("palabras")
        if words:
            picked = [w[2] for w in words if a <= (w[0] + w[1]) / 2 < b]
            if picked:
                out.append("".join(picked).strip())
        elif a <= s["start"] < b:
            out.append(s["text"])
    return " ".join(x for x in out if x).strip()


def assemble(meta: dict, scenes: list[tuple[float, float]], frames: list[Frame], audio: dict,
             transcript: dict | None, mode: str, long_side: int, avisos: list[str]) -> dict:
    duration = meta["duracion_s"]
    segs = (transcript or {}).get("segmentos", [])
    speech = [(s["start"], s["end"]) for s in segs]
    energia = audio.get("energia_db_por_segundo", [])
    momentary = audio.get("momentary", [])
    silencios = audio.get("silencios", [])

    escenas = []
    for n, (a, b) in enumerate(scenes, start=1):
        e_slice = energia[int(a):max(int(a) + 1, int(b + 0.999))]
        escenas.append({
            "n": n, "t_inicio": a, "t_fin": b, "dur_s": round(b - a, 2),
            "frames": frames_for_scene(frames, a, b, n),
            "voz": _voice_between(segs, a, b),
            "texto_pantalla": None,
            "audio": {
                "loudness_lufs": loudness_between(momentary, a, b),
                "silencio": is_silent_between(silencios, a, b) if audio.get("tiene_audio") else True,
                "energia_db": round(sum(e_slice) / len(e_slice), 1) if e_slice else None,
            },
        })

    hook_end = min(HOOK_END, duration)
    hook_frames = [f.rel for f in frames if f.kind == "hook"] or [f.rel for f in frames[:1]]
    cortes = max(0, len(scenes) - 1)
    durs = [b - a for a, b in scenes] or [duration]
    palabras = sum(len(s["text"].split()) for s in segs)
    habla_s = sum(e - s for s, e in speech)
    ritmo = {
        "cortes": cortes,
        "cortes_por_min": round(cortes / duration * 60, 1) if duration else 0.0,
        "toma_promedio_s": round(sum(durs) / len(durs), 2),
        "toma_mas_corta_s": round(min(durs), 2),
        "toma_mas_larga_s": round(max(durs), 2),
        "palabras_por_min": round(palabras / habla_s * 60) if habla_s > 3 else None,
        "tipo_probable": _tipo(cortes, duration, bool(segs)),
    }
    audio_global = {
        "tiene_audio": audio.get("tiene_audio", False),
        "lufs_integrado": audio.get("lufs_integrado"),
        "rango_lra": audio.get("rango_lra"),
        "silencios": silencios,
        "musica_probable": music_probable(energia, speech, silencios, duration) if audio.get("tiene_audio") else None,
        "energia_db_por_segundo": energia,
    }
    if audio_global["tiene_audio"] and audio_global["musica_probable"] is None:
        avisos.append("No se pudo estimar si hay música (la voz cubre casi todo el audio): decide por el contexto.")
    elif audio_global["musica_probable"] is not None:
        avisos.append("'musica_probable' es una estimación por energía de audio, no un detector de música: "
                      "confírmalo con lo que ves y oyes en el contexto.")
    return {
        "version": __version__,
        "modo": mode,
        "generado": datetime.now().isoformat(timespec="seconds"),
        "meta": meta,
        "hook": {
            "t_fin": round(hook_end, 2),
            "frames": hook_frames,
            "voz": _voice_between(segs, 0, hook_end),
            "texto_pantalla": None,
            "loudness_lufs": loudness_between(momentary, 0, hook_end),
            "cortes_en_hook": sum(1 for a, _ in scenes[1:] if a < hook_end),
        },
        "escenas": escenas,
        "ritmo": ritmo,
        "audio_global": audio_global,
        "transcripcion": transcript,
        "cuadros": {
            "total": len(frames),
            "lado_largo_px": long_side,
            "tokens_estimados": estimate_tokens(frames),
            "lista": [f.rel for f in frames],
        },
        "avisos": avisos,
    }


def _tipo(cortes: int, duration: float, has_voice: bool) -> str:
    if duration <= 0:
        return "desconocido"
    cpm = cortes / duration * 60
    if cortes <= 1:
        return "toma continua (talking head o plano único)" if has_voice else "toma continua sin voz"
    if cpm >= 30:
        return "montaje rápido"
    if cpm >= 12:
        return "montaje medio"
    return "montaje pausado"


def validate(data: dict) -> None:
    try:
        import jsonschema
    except ImportError:
        return
    jsonschema.validate(data, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def write(data: dict, outdir: Path) -> tuple[Path, Path]:
    validate(data)
    a = outdir / "analysis.json"
    a.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    t = outdir / "timeline.md"
    t.write_text(timeline_md(data), encoding="utf-8")
    return a, t


def _fmt(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:05.2f}"


def _n(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, int) and v >= 1000:
        return f"{v:,}".replace(",", ".")
    return str(v)


def timeline_md(d: dict) -> str:
    m, r, ag, h = d["meta"], d["ritmo"], d["audio_global"], d["hook"]
    tr = d["transcripcion"]
    lines = [
        f"# Línea de tiempo: {m.get('cuenta') or ''} ({m['plataforma']})",
        "",
        f"- Link: {m.get('url') or '(archivo local)'}",
        f"- Duración: {m['duracion_s']} s · {m['orientacion']} {m['resolucion']} · "
        f"vistas {_n(m.get('vistas'))} · likes {_n(m.get('likes'))} · comentarios {_n(m.get('comentarios'))}",
        f"- Ritmo: {r['cortes']} cortes · {r['cortes_por_min']} cortes/min · toma promedio {r['toma_promedio_s']} s "
        f"· {r['tipo_probable']}" + (f" · {r['palabras_por_min']} palabras/min" if r.get("palabras_por_min") else ""),
        f"- Audio: {ag['lufs_integrado']} LUFS integrados · música probable: "
        f"{ {True: 'sí', False: 'no', None: '—'}[ag['musica_probable']] } · "
        f"{len(ag['silencios'])} silencios",
        f"- Transcripción: {tr['fuente'] + ' (' + str(tr.get('idioma')) + ')' if tr else 'no disponible'}",
        f"- Cuadros: {d['cuadros']['total']} (~{d['cuadros']['tokens_estimados']} tokens de imagen)",
        "",
        "## Caption",
        "",
        (m.get("caption") or "(sin caption)").strip()[:800],
        "",
        f"## Hook (0–{h['t_fin']} s)",
        "",
        f"- Cuadros: {', '.join(h['frames'])}",
        f"- Voz: {h['voz'] or '(sin voz)'}",
        f"- Cortes dentro del hook: {h['cortes_en_hook']} · loudness {h['loudness_lufs']} LUFS",
        "",
        "## Escenas",
        "",
        "| # | tiempo | dur | cuadros | voz | audio |",
        "|---|---|---|---|---|---|",
    ]
    for e in d["escenas"]:
        au = e["audio"]
        audio_txt = "silencio" if au["silencio"] else f"{au['loudness_lufs']} LUFS"
        voz = (e["voz"] or "—").replace("|", "/")
        lines.append(f"| {e['n']} | {_fmt(e['t_inicio'])}–{_fmt(e['t_fin'])} | {e['dur_s']} s | "
                     f"{', '.join(x.replace('frames/', '') for x in e['frames'])} | {voz} | {audio_txt} |")
    if ag["silencios"]:
        lines += ["", "## Silencios", ""]
        lines += [f"- {_fmt(s['inicio'])}–{_fmt(s['fin'])} ({s['dur']} s)" for s in ag["silencios"]]
    if tr and tr.get("segmentos"):
        lines += ["", "## Transcripción con tiempos", ""]
        lines += [f"- [{_fmt(s['start'])}] {s['text']}" for s in tr["segmentos"]]
    if d["avisos"]:
        lines += ["", "## Avisos", ""] + [f"- {a}" for a in d["avisos"]]
    return "\n".join(lines) + "\n"
