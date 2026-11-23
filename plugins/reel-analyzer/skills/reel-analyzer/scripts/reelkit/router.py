"""Normaliza el link, detecta la plataforma y el id del video."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .errors import unsupported_url

# Parámetros de rastreo que se quitan del link (no cambian el video).
_TRACKING = {
    "igsh", "igshid", "si", "feature", "is_from_webapp", "sender_device", "sender_web_id", "_r", "_t",
    "mibextid", "rdid", "s", "t", "ref", "ref_src", "share_id", "share_app_id", "lang", "checksum",
    "u_code", "preview_pb", "social_share_type", "timestamp", "user_id", "web_id", "_d", "tt_from",
}


@dataclass
class Source:
    platform: str     # instagram | youtube | tiktok | x | facebook
    url: str          # link limpio
    video_id: str     # id si se puede leer del link; si no, "" (se completa con la metadata)


_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("instagram", re.compile(r"(?:^|\.)instagram\.com/(?:[\w.]+/)?(?:reels?|p|tv)/([\w-]+)", re.I)),
    ("youtube", re.compile(r"(?:^|\.)youtube\.com/shorts/([\w-]{6,})", re.I)),
    ("youtube", re.compile(r"(?:^|\.)youtube\.com/watch\?(?:.*&)?v=([\w-]{6,})", re.I)),
    ("youtube", re.compile(r"(?:^|\.)youtu\.be/([\w-]{6,})", re.I)),
    ("tiktok", re.compile(r"(?:^|\.)tiktok\.com/@[\w.-]+/(?:video|photo)/(\d+)", re.I)),
    ("tiktok", re.compile(r"(?:^|\.)(?:vm|vt)\.tiktok\.com/([\w-]+)", re.I)),
    ("tiktok", re.compile(r"(?:^|\.)tiktok\.com/t/([\w-]+)", re.I)),
    ("x", re.compile(r"(?:^|\.)(?:x|twitter)\.com/[\w]+/status/(\d+)", re.I)),
    ("facebook", re.compile(r"(?:^|\.)facebook\.com/(?:reel|reels)/(\d+)", re.I)),
    ("facebook", re.compile(r"(?:^|\.)facebook\.com/share/[rv]/([\w-]+)", re.I)),
    ("facebook", re.compile(r"(?:^|\.)facebook\.com/watch/?\?(?:.*&)?v=(\d+)", re.I)),
    ("facebook", re.compile(r"(?:^|\.)facebook\.com/[\w.]+/videos/(?:[\w.-]+/)?(\d+)", re.I)),
    ("facebook", re.compile(r"(?:^|\.)fb\.watch/([\w-]+)", re.I)),
]


def _clean(url: str) -> str:
    url = url.strip().strip("<>\"'")
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    parts = urlsplit(url)
    host = parts.netloc.lower()
    for prefix in ("m.", "mobile.", "www."):
        if host.startswith(prefix):
            host = host[len(prefix):]
    if host == "twitter.com":
        host = "x.com"
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
             if k.lower() not in _TRACKING and not k.lower().startswith("utm_")]
    path = parts.path
    if "instagram.com" in host:
        path = re.sub(r"/reels/", "/reel/", path)
    return urlunsplit(("https", host, path, urlencode(query), ""))


def route(url: str) -> Source:
    """Devuelve la plataforma y el link limpio, o lanza UNSUPPORTED_URL."""
    clean = _clean(url)
    probe = clean.split("://", 1)[1]
    for platform, pattern in _PATTERNS:
        m = pattern.search(probe)
        if m:
            return Source(platform, clean, m.group(1))
    raise unsupported_url(url)


def safe_id(value: str) -> str:
    return re.sub(r"[^\w-]+", "_", value).strip("_")[:60] or "video"
