#!/usr/bin/env python3
"""reel-analyzer: link o MP4 → analysis.json + timeline.md + cuadros.

Uso:
  analyze.py <URL> [<URL> ...] [--out ./reels] [--cookies-from-browser chrome] [--modo rapido|completo] [--keep]
  analyze.py --file video.mp4 [--out ./reels] [--modo rapido|completo]

Salida por video: <out>/<plataforma>_<id>/{analysis.json, timeline.md, frames/t_SS.ss.jpg}
Errores: una línea "ERROR <CODIGO>: …" y otra "→ acción", más un JSON en la última línea de stdout.
Códigos de salida: 0 ok · 2 error · 3 NETWORK_BLOCKED (pide el MP4).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reelkit import audio as audio_mod  # noqa: E402
from reelkit import build, frames as frames_mod, scenes as scenes_mod  # noqa: E402
from reelkit.download import _auth_args, download, fetch_subtitles, local_file  # noqa: E402
from reelkit.errors import ReelError  # noqa: E402
from reelkit.probe import probe, require_ffmpeg  # noqa: E402
from reelkit.router import Source, route, safe_id  # noqa: E402
from reelkit.transcribe import transcribe, vocab_prompt  # noqa: E402

HOME = Path(os.environ.get("REEL_ANALYZER_HOME", Path.home() / ".reel-analyzer"))
AVISO = ("AVISO DE USO RESPONSABLE: reel-analyzer sirve para estudiar el FORMATO de un video y escribir un guion "
         "original. No re-publiques el video ni copies su contenido; descargar puede ir contra los términos de la "
         "plataforma. El video se borra al terminar (salvo --keep).")


def _first_run_notice() -> None:
    marker = HOME / ".aviso_mostrado"
    if marker.exists():
        return
    print(AVISO)
    try:
        HOME.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        pass


def analyze_one(source: str, is_file: bool, out_root: Path, mode: str, keep: bool,
                cookies_from_browser: str | None, cookies_file: str | None, do_transcribe: bool) -> Path:
    t0 = time.time()
    require_ffmpeg()
    avisos: list[str] = []
    info: dict = {}
    subtitle = None
    if is_file:
        video = local_file(source)
        platform, url = "archivo", None
        outdir = out_root / f"archivo_{safe_id(video.stem)}"
        workdir = outdir / "_descarga"
        workdir.mkdir(parents=True, exist_ok=True)
        downloaded = False
    else:
        src: Source = route(source)
        platform, url = src.platform, src.url
        outdir = out_root / f"{platform}_{safe_id(src.video_id or 'video')}"
        workdir = outdir / "_descarga"
        if workdir.exists():
            shutil.rmtree(workdir)
        print(f"[reelkit] descargando {platform}: {url}", file=sys.stderr)
        video, info = download(src, workdir, cookies_from_browser, cookies_file)
        downloaded = True
        subtitle = fetch_subtitles(info, workdir, src, _auth_args(cookies_from_browser, cookies_file))
        if info.get("id") and not src.video_id:
            new = out_root / f"{platform}_{safe_id(str(info['id']))}"
            if not new.exists():
                outdir.rename(new)
                outdir, workdir = new, new / "_descarga"
                video = workdir / video.name
                subtitle = (workdir / subtitle.name) if subtitle else None

    if (outdir / "frames").exists():
        shutil.rmtree(outdir / "frames")
    pr = probe(video)
    meta = build.meta_from_info(info, platform, url, pr)
    dur = pr["duracion_s"]
    print(f"[reelkit] {dur:.1f} s, {pr['ancho']}x{pr['alto']}; detectando escenas…", file=sys.stderr)
    scenes = scenes_mod.detect_scenes(video, dur)
    print(f"[reelkit] {len(scenes)} escenas; extrayendo cuadros ({mode})…", file=sys.stderr)
    frames = frames_mod.extract(video, outdir, scenes, dur, pr["ancho"], pr["alto"], mode)
    print("[reelkit] midiendo audio…", file=sys.stderr)
    au = audio_mod.analyze(video, dur, pr["tiene_audio"])
    print("[reelkit] transcribiendo…", file=sys.stderr)
    prompt = vocab_prompt(meta.get("cuenta"), meta.get("caption"))
    tr, aviso_tr = transcribe(video, pr["tiene_audio"], subtitle, prompt, enabled=do_transcribe)
    if aviso_tr:
        avisos.append(aviso_tr)
    if tr and tr.get("fuente") == "whisper":
        avisos.append("Transcripción automática: los nombres propios y marcas pueden salir mal escritos.")

    long_side = frames_mod.MODES[mode]["long_side"]
    data = build.assemble(meta, scenes, frames, au, tr, mode, long_side, avisos)
    data["meta"]["procesado_en_s"] = round(time.time() - t0, 1)
    a_path, t_path = build.write(data, outdir)

    if downloaded and not keep:
        shutil.rmtree(workdir, ignore_errors=True)
    elif downloaded and keep:
        kept = outdir / f"video{video.suffix}"
        shutil.move(str(video), kept)
        shutil.rmtree(workdir, ignore_errors=True)
    else:
        shutil.rmtree(workdir, ignore_errors=True)  # nunca toca el archivo original del usuario

    print(f"OK {a_path}")
    print(f"   timeline: {t_path}")
    print(f"   {len(scenes)} escenas · {data['cuadros']['total']} cuadros (~{data['cuadros']['tokens_estimados']} tokens) "
          f"· transcripción: {tr['fuente'] if tr else 'no'} · {data['meta']['procesado_en_s']} s")
    return a_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="analyze.py", description="Desglosa un video corto para replicar su formato.")
    ap.add_argument("urls", nargs="*", help="Links de Instagram, YouTube Shorts, TikTok, X o Facebook")
    ap.add_argument("--file", action="append", default=[], help="Ruta a un MP4 local (se puede repetir)")
    ap.add_argument("--out", default="./reels", help="Carpeta de salida (default ./reels)")
    ap.add_argument("--modo", choices=["rapido", "completo"], default="completo")
    ap.add_argument("--cookies-from-browser", dest="cfb", default=None,
                    help="chrome | safari | firefox | edge | brave (usa la sesión de ese navegador)")
    ap.add_argument("--cookies", default=None, help="Archivo cookies.txt (formato Netscape)")
    ap.add_argument("--keep", action="store_true", help="Conserva el video descargado")
    ap.add_argument("--sin-transcripcion", action="store_true", help="No usa Whisper (más rápido)")
    args = ap.parse_args(argv)

    if not args.urls and not args.file:
        ap.print_help()
        return 2
    _first_run_notice()
    out_root = Path(args.out).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    jobs = [(u, False) for u in args.urls] + [(f, True) for f in args.file]
    results, worst = [], 0
    for source, is_file in jobs:
        try:
            p = analyze_one(source, is_file, out_root, args.modo, args.keep, args.cfb, args.cookies,
                            not args.sin_transcripcion)
            results.append({"fuente": source, "ok": True, "analysis": str(p)})
        except ReelError as e:
            print(e.human())
            results.append({"fuente": source, "ok": False, **e.to_dict()})
            worst = max(worst, 3 if e.code == "NETWORK_BLOCKED" else 2)
    print(json.dumps({"resultados": results}, ensure_ascii=False))
    return worst


if __name__ == "__main__":
    sys.exit(main())
