"""Descarga: yt-dlp → (solo Instagram) gallery-dl → error claro en español.

Nunca se escribe un extractor propio. gallery-dl (GPL-2.0) se invoca como programa
aparte, no se importa ni se copia.
"""
from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

from . import proc
from .errors import ReelError, classify_ytdlp_error, download_failed, network_blocked
from .router import Source

VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".mov", ".m4v")
_updated_once = False


def _auth_args(cookies_from_browser: str | None, cookies_file: str | None) -> list[str]:
    if cookies_from_browser:
        return ["--cookies-from-browser", cookies_from_browser]
    if cookies_file:
        return ["--cookies", str(Path(cookies_file).expanduser())]
    return []


def _find_video(directory: Path) -> Path | None:
    for ext in VIDEO_EXTS:
        hits = sorted(directory.glob(f"video*{ext}"))
        if hits:
            return hits[0]
    for ext in VIDEO_EXTS:
        hits = sorted(directory.rglob(f"*{ext}"))
        if hits:
            return hits[0]
    return None


def _ytdlp(src: Source, workdir: Path, auth: list[str]) -> tuple[Path | None, dict, str]:
    cmd = [*proc.python_module("yt_dlp"), "--no-playlist", "--no-progress", "--no-warnings",
           "-S", "res:1080", "--merge-output-format", "mp4", "--write-info-json",
           "--retries", "3", "--socket-timeout", "20",
           "-o", str(workdir / "video.%(ext)s"), *auth, "--", src.url]
    r = proc.run(cmd, timeout=600)
    video = _find_video(workdir)
    info = {}
    info_path = workdir / "video.info.json"
    if info_path.exists():
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            info = {}
    if r.returncode != 0 or video is None:
        return None, info, (r.stderr or "") + (r.stdout or "")
    return video, info, ""


def _self_update_ytdlp() -> bool:
    """Actualiza yt-dlp una sola vez por corrida, solo dentro de nuestro venv."""
    global _updated_once
    if _updated_once:
        return False
    _updated_once = True
    home = os.environ.get("REEL_ANALYZER_HOME", str(Path.home() / ".reel-analyzer"))
    if not str(Path(sys.prefix).resolve()).startswith(str(Path(home).resolve())):
        return False
    print("[reelkit] yt-dlp falló con un error de extractor; actualizando yt-dlp y reintentando una vez…",
          file=sys.stderr)
    r = proc.run([sys.executable, "-m", "pip", "install", "-q", "-U", "yt-dlp[default,curl-cffi,deno]"],
                 timeout=300)
    return r.returncode == 0


def _gallery_dl(src: Source, workdir: Path, auth: list[str]) -> tuple[Path | None, dict, str]:
    gdir = workdir / "gdl"
    gdir.mkdir(exist_ok=True)
    cmd = [*proc.python_module("gallery_dl"), "-D", str(gdir), "--filename", "video_{num}.{extension}",
           "--write-metadata", *auth, src.url]
    r = proc.run(cmd, timeout=600)
    video = _find_video(gdir)
    info: dict = {}
    for meta in glob.glob(str(gdir / "*.json")):
        try:
            info = json.loads(Path(meta).read_text(encoding="utf-8"))
            break
        except (OSError, ValueError):
            pass
    if video is None:
        return None, info, (r.stderr or "") + (r.stdout or "")
    return video, _gdl_to_ytdlp_info(info, src), ""


def _gdl_to_ytdlp_info(m: dict, src: Source) -> dict:
    return {
        "id": m.get("post_shortcode") or m.get("shortcode") or src.video_id,
        "uploader": m.get("fullname") or m.get("username"),
        "uploader_id": m.get("username"),
        "channel": m.get("username"),
        "description": m.get("description") or "",
        "like_count": m.get("likes"),
        "view_count": m.get("video_view_count") or m.get("view_count"),
        "duration": m.get("video_duration"),
        "timestamp": None,
        "extractor": "gallery-dl",
    }


def download(src: Source, workdir: Path, cookies_from_browser: str | None = None,
             cookies_file: str | None = None) -> tuple[Path, dict]:
    """Descarga el video a workdir/video.mp4 y devuelve (ruta, info de yt-dlp)."""
    workdir.mkdir(parents=True, exist_ok=True)
    auth = _auth_args(cookies_from_browser, cookies_file)
    used_cookies = bool(auth)

    video, info, err = _ytdlp(src, workdir, auth)
    if video:
        return video, info
    first = classify_ytdlp_error(err, src.platform, used_cookies)
    if first.code == "NETWORK_BLOCKED":
        raise first

    if first.code == "EXTRACTOR_BROKEN" and _self_update_ytdlp():
        video, info, err = _ytdlp(src, workdir, auth)
        if video:
            return video, info
        first = classify_ytdlp_error(err, src.platform, used_cookies)

    if src.platform == "instagram":
        # HTML en vez de JSON con sesión: Instagram a veces responde bien sin sesión.
        if first.code == "IG_HTML_RESPONSE" and used_cookies:
            video, info, err = _ytdlp(src, workdir, [])
            if video:
                return video, info
        # Respaldo: gallery-dl (se arregla casi cada semana para Instagram).
        if proc.which("gallery-dl") or _module_available("gallery_dl"):
            video, info, gerr = _gallery_dl(src, workdir, auth)
            if video:
                return video, info
            if "NameResolution" in gerr or "Failed to resolve" in gerr:
                raise network_blocked(gerr)
    raise first


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def fetch_subtitles(info: dict, workdir: Path, src: Source, auth: list[str]) -> Path | None:
    """Intenta bajar subtítulos de la plataforma (manuales primero). Nunca falla."""
    info_path = workdir / "video.info.json"
    if not info_path.exists():
        return None
    lang = (info.get("language") or "").split("-")[0]
    manual = {k for k, v in (info.get("subtitles") or {}).items() if v and k != "live_chat"}
    auto = {k for k, v in (info.get("automatic_captions") or {}).items() if v}
    choice, kind = _pick_track(manual, lang), "manual"
    if not choice:
        choice, kind = _pick_track(auto, lang, auto=True), "auto"
    if not choice:
        return None
    cmd = [*proc.python_module("yt_dlp"), "--load-info-json", str(info_path), "--skip-download",
           "--no-warnings", "--write-subs" if kind == "manual" else "--write-auto-subs",
           "--sub-langs", choice, "--sub-format", "vtt/best", "--convert-subs", "vtt",
           "-o", str(workdir / "subs.%(ext)s"), *auth]
    try:
        proc.run(cmd, timeout=120)
    except Exception:  # noqa: BLE001 — los subtítulos son opcionales
        return None
    hits = sorted(workdir.glob("subs*.vtt"))
    return hits[0] if hits else None


def _pick_track(keys: set[str], lang: str, auto: bool = False) -> str | None:
    if not keys:
        return None
    order = []
    if lang:
        order += [f"{lang}-orig", lang] if auto else [lang]
    order += ["es-orig", "es", "es-419", "es-ES", "en-orig", "en", "en-US", "pt", "pt-BR"]
    for k in order:
        if k in keys:
            return k
    if auto:
        origs = sorted(k for k in keys if k.endswith("-orig"))
        return origs[0] if origs else None
    return sorted(keys)[0]


def local_file(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise ReelError("FILE_NOT_FOUND", f"No encuentro el archivo: {p}",
                        "Revisa la ruta o adjunta el video otra vez.")
    return p


__all__ = ["download", "fetch_subtitles", "local_file", "download_failed"]
