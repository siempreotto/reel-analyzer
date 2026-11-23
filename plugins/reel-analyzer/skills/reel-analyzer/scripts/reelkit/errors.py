"""Errores con mensaje en español y la acción concreta para el usuario."""
from __future__ import annotations

import re


class ReelError(Exception):
    def __init__(self, code: str, mensaje: str, accion: str, detalle: str = ""):
        super().__init__(f"{code}: {mensaje}")
        self.code = code
        self.mensaje = mensaje
        self.accion = accion
        self.detalle = detalle

    def to_dict(self) -> dict:
        return {"error": self.code, "mensaje": self.mensaje, "accion": self.accion,
                "detalle": self.detalle[-600:]}

    def human(self) -> str:
        return f"ERROR {self.code}: {self.mensaje}\n→ {self.accion}"


def network_blocked(detalle: str = "") -> ReelError:
    return ReelError(
        "NETWORK_BLOCKED",
        "No hay acceso a la red desde aquí (o el sitio está bloqueado en este entorno), así que no puedo descargar desde el link.",
        "Descarga el reel en tu teléfono o computadora y adjunta el MP4; lo analizo con --file.",
        detalle,
    )


def ig_login_required(detalle: str = "", used_cookies: bool = False) -> ReelError:
    if used_cookies:
        return ReelError(
            "IG_LOGIN_REQUIRED",
            "Instagram rechazó la sesión: las cookies parecen vencidas o la cuenta fue marcada.",
            "Abre instagram.com en ese navegador, inicia sesión de nuevo (mejor con una cuenta secundaria) y reintenta. "
            "Si sigue fallando, descarga el reel y adjunta el MP4.",
            detalle,
        )
    return ReelError(
        "IG_LOGIN_REQUIRED",
        "Instagram exige una sesión iniciada para descargar este reel.",
        "Reintenta con --cookies-from-browser chrome (o safari, firefox, edge, brave) después de iniciar sesión en "
        "instagram.com en ese navegador. Recomendado: usa una cuenta secundaria, no la principal.",
        detalle,
    )


def ig_html_response(detalle: str = "") -> ReelError:
    return ReelError(
        "IG_HTML_RESPONSE",
        "Instagram devolvió una página web en vez de los datos del video (cambio reciente en su API).",
        "Actualiza con: ~/.reel-analyzer/venv/bin/pip install -U yt-dlp gallery-dl, inicia sesión de nuevo en el "
        "navegador y reintenta. Si persiste, descarga el reel y adjunta el MP4.",
        detalle,
    )


def private_or_deleted(detalle: str = "") -> ReelError:
    return ReelError(
        "PRIVATE_OR_DELETED",
        "El video es privado, fue eliminado o no está disponible en tu país.",
        "Verifica que el link abra en una ventana de incógnito. Si es de una cuenta privada que sigues, usa "
        "--cookies-from-browser; si no, adjunta el MP4.",
        detalle,
    )


def needs_cookies(detalle: str = "") -> ReelError:
    return ReelError(
        "COOKIES_REQUIRED",
        "La plataforma pide iniciar sesión (verificación de edad o de que no eres un bot).",
        "Reintenta con --cookies-from-browser chrome (o tu navegador) con la sesión iniciada en esa plataforma.",
        detalle,
    )


def extractor_broken(detalle: str = "") -> ReelError:
    return ReelError(
        "EXTRACTOR_BROKEN",
        "El descargador (yt-dlp) no pudo leer esta plataforma; suele pasar cuando la plataforma cambia algo.",
        "Actualiza con: ~/.reel-analyzer/venv/bin/pip install -U yt-dlp y reintenta. Si sigue fallando, adjunta el MP4.",
        detalle,
    )


def unsupported_url(url: str) -> ReelError:
    return ReelError(
        "UNSUPPORTED_URL",
        f"No reconozco este link como un video de Instagram, YouTube, TikTok, X o Facebook: {url}",
        "Pega el link directo del video (por ejemplo instagram.com/reel/…, youtube.com/shorts/…, tiktok.com/@…/video/…) "
        "o adjunta el MP4.",
    )


def download_failed(detalle: str = "") -> ReelError:
    return ReelError(
        "DOWNLOAD_FAILED",
        "No se pudo descargar el video.",
        "Revisa que el link abra en el navegador y reintenta; si sigue fallando, adjunta el MP4.",
        detalle,
    )


_NETWORK = re.compile(
    r"Failed to resolve|Temporary failure in name resolution|nodename nor servname|Name or service not known|"
    r"Network is unreachable|getaddrinfo failed|No address associated|Connection refused|Tunnel connection failed|"
    r"ProxyError|not in allowlist|x-deny-reason|blocked-by-allowlist|Errno 8|Errno -2|Errno -3|Errno 101|Errno 111",
    re.I,
)
_IG_EMPTY = re.compile(
    r"empty media response|login required|rate-limit reached or login required|"
    r"Requested content is not available|use --cookies|Main webpage is locked behind the login page",
    re.I,
)
_IG_HTML = re.compile(r"Expecting value|JSONDecodeError|Failed to parse JSON|returned HTML|text/html|"
                      r"Unable to extract (shared data|additional data)", re.I)
_PRIVATE = re.compile(
    r"Private video|This video is private|Video unavailable|This post is unavailable|has been removed|"
    r"account is private|This content isn.t available|no longer available|HTTP Error 410|"
    r"Video not available|not available in your country|geo.?restrict",
    re.I,
)
_HTTP404 = re.compile(r"HTTP Error 404|404: Not Found", re.I)
_COOKIES = re.compile(r"Sign in to confirm|confirm you.re not a bot|age.?restrict|inappropriate for some users|"
                      r"--cookies-from-browser or --cookies", re.I)
_BROKEN = re.compile(r"Unable to extract|Please report this issue|Unable to download JSON metadata|"
                     r"Unable to download webpage|KeyError|IndexError|TypeError|nsig|challenge solving", re.I)


def classify_ytdlp_error(stderr: str, platform: str, used_cookies: bool) -> ReelError:
    """Traduce la salida de error de yt-dlp a un ReelError accionable."""
    text = stderr or ""
    if _NETWORK.search(text):
        return network_blocked(text)
    if platform == "instagram":
        if _IG_HTML.search(text):
            return ig_html_response(text)
        if _IG_EMPTY.search(text) or (_HTTP404.search(text) and used_cookies):
            return ig_login_required(text, used_cookies)
    if _COOKIES.search(text):
        return needs_cookies(text)
    if _PRIVATE.search(text) or _HTTP404.search(text):
        return private_or_deleted(text)
    if _BROKEN.search(text):
        return extractor_broken(text)
    return download_failed(text)
