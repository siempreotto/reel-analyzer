"""Transcripción: subtítulos de la plataforma → faster-whisper (local) → None.

faster-whisper corre con vad_filter=True: sin VAD, Whisper "oye" frases en la música
o en el ruido (típicamente "Gracias" o "Suscríbete").

Pesos del modelo, en orden:
1. REEL_WHISPER_MODEL_DIR: carpeta con un modelo CTranslate2 ya descargado.
2. Hugging Face (lo normal en una computadora).
3. Respaldo por GitHub Release (REEL_WHISPER_MODEL_URL o el release del repo), para entornos
   donde Hugging Face está bloqueado pero GitHub no (p. ej. el sandbox de claude.ai).
"""
from __future__ import annotations

import os
import re
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

DEFAULT_MODEL = os.environ.get("REEL_WHISPER_MODEL", "small")
# Se completa al publicar el repo (Fase 4). Formato: tar.gz con la carpeta del modelo CT2.
RELEASE_URL = os.environ.get(
    "REEL_WHISPER_MODEL_URL",
    "https://github.com/{repo}/releases/download/whisper-models/faster-whisper-{size}.tar.gz",
)
def _default_repo() -> str:
    from . import REPO
    return "" if "<" in REPO else REPO


RELEASE_REPO = os.environ.get("REEL_ANALYZER_REPO") or _default_repo()

_TS = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})")
_TAG = re.compile(r"<[^>]+>")


def _secs(h, m, s, ms) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_vtt(path: Path) -> list[dict]:
    segs: list[dict] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    i = 0
    while i < len(lines):
        m = _TS.search(lines[i])
        if not m:
            i += 1
            continue
        start, end = _secs(*m.groups()[:4]), _secs(*m.groups()[4:])
        i += 1
        text = []
        while i < len(lines) and lines[i].strip():
            text.append(_TAG.sub("", lines[i]).strip())
            i += 1
        t = " ".join(x for x in text if x)
        if not t:
            continue
        # Los subtítulos automáticos repiten la línea anterior ("rolling"): quita el prefijo repetido.
        if segs and t.startswith(segs[-1]["text"]):
            t = t[len(segs[-1]["text"]):].strip()
            if not t:
                segs[-1]["end"] = round(end, 2)
                continue
        if segs and t == segs[-1]["text"]:
            segs[-1]["end"] = round(end, 2)
            continue
        segs.append({"start": round(start, 2), "end": round(end, 2), "text": t})
    return segs


def _models_dir() -> Path:
    return Path(os.environ.get("REEL_ANALYZER_HOME", Path.home() / ".reel-analyzer")) / "models"


def _ssl_context():
    """Python de python.org o de Homebrew a veces no ve los certificados del sistema
    (CERTIFICATE_VERIFY_FAILED); certifi viene con requests, que instala yt-dlp."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _from_release(size: str) -> str | None:
    if "{repo}" in RELEASE_URL and not RELEASE_REPO:
        return None
    url = RELEASE_URL.format(repo=RELEASE_REPO, size=size)
    dest = _models_dir() / f"faster-whisper-{size}"
    if (dest / "model.bin").exists():
        return str(dest)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            with urllib.request.urlopen(url, timeout=120, context=_ssl_context()) as resp:
                while chunk := resp.read(1 << 20):
                    tmp.write(chunk)
        with tarfile.open(tmp.name) as tar:
            tar.extractall(dest.parent, filter="data")
        os.unlink(tmp.name)
        return str(dest) if (dest / "model.bin").exists() else None
    except Exception as exc:  # noqa: BLE001
        print(f"[reelkit] no se pudo bajar el modelo desde GitHub: {exc}", file=sys.stderr)
        return None


def _load_model(size: str):
    from faster_whisper import WhisperModel

    local = os.environ.get("REEL_WHISPER_MODEL_DIR")
    if local and Path(local, "model.bin").exists():
        return WhisperModel(local, device="cpu", compute_type="int8")
    cached = _models_dir() / f"faster-whisper-{size}"
    if (cached / "model.bin").exists():
        return WhisperModel(str(cached), device="cpu", compute_type="int8")
    try:
        return WhisperModel(size, device="cpu", compute_type="int8")
    except Exception as exc:  # noqa: BLE001 — sin red hacia Hugging Face
        print(f"[reelkit] no se pudo bajar el modelo de Hugging Face ({type(exc).__name__}); "
              "pruebo el respaldo de GitHub…", file=sys.stderr)
        path = _from_release(size)
        if path:
            return WhisperModel(path, device="cpu", compute_type="int8")
        raise


def decode_audio(video: Path, sr: int = 16000):
    """Audio mono float32 a 16 kHz con ffmpeg. No se usa el decodificador de faster-whisper
    (PyAV): faster-whisper 1.2.1 llama a av.open(metadata_errors=…), que PyAV 19 ya no acepta."""
    import subprocess

    import numpy as np

    from . import proc
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", str(sr),
                        "-f", "f32le", "-"], capture_output=True, env=proc.env(), timeout=600)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[-300:])
    return np.frombuffer(r.stdout, dtype=np.float32)


def whisper(video: Path, prompt: str = "", size: str = DEFAULT_MODEL) -> dict:
    model = _load_model(size)
    segments, info = model.transcribe(
        decode_audio(video), vad_filter=True, vad_parameters={"min_silence_duration_ms": 400},
        beam_size=5, word_timestamps=True, initial_prompt=(prompt[:200] or None), condition_on_previous_text=False,
    )
    segs = []
    for s in segments:
        text = clean_text(s.text)
        if not text:
            continue
        seg = {"start": round(s.start, 2), "end": round(s.end, 2), "text": text}
        if s.words:
            words = [[round(w.start, 2), round(w.end, 2), clean_text(w.word)] for w in s.words]
            seg["palabras"] = [[a, b, " " + w] for a, b, w in words if w]
        segs.append(seg)
    return {"fuente": "whisper", "modelo": size, "idioma": info.language,
            "prob_idioma": round(info.language_probability, 2), "segmentos": segs}


_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u20E3\u200D]")
_STOP = {w.lower() for w in """a al ante como con de del el en es la las lo los mas más me mi mis no o para pero
por que qué se si sí su sus te tu tus un una uno y ya and are as at be but by for from how i if in is it its my
of on or so that the this to what when why with you your""".split()}


def vocab_prompt(cuenta: str | None, caption: str | None, limit: int = 25) -> str:
    """Prompt para Whisper con solo vocabulario (cuenta, marcas, nombres propios).

    Si se le pasa el caption tal cual, Whisper copia su estilo: emojis como «2️⃣» o el
    Title Case de un título. Una lista de términos sin frases no tiene nada que copiar.
    """
    text = _EMOJI.sub(" ", caption or "")
    terms: list[str] = []
    if cuenta:
        terms.append(cuenta.lstrip("@"))
    for tok in re.findall(r"[#@]?[\w][\w.\-+]*", text):
        word = tok.lstrip("#@").strip(".-")
        if len(word) < 2 or word.lower() in _STOP:
            continue
        if any(c.isupper() for c in word) or any(c.isdigit() for c in word) and any(c.isalpha() for c in word):
            if word not in terms:
                terms.append(word)
        if len(terms) >= limit:
            break
    return ", ".join(terms) + "." if terms else ""


def clean_text(text: str) -> str:
    return re.sub(r"\s{2,}", " ", _EMOJI.sub("", text)).strip()


def transcribe(video: Path, has_audio: bool, subtitle: Path | None = None, prompt: str = "",
               enabled: bool = True) -> tuple[dict | None, str | None]:
    """Devuelve (transcripción, aviso)."""
    if subtitle and subtitle.exists():
        segs = parse_vtt(subtitle)
        if segs:
            lang = subtitle.stem.split(".")[-1] if "." in subtitle.stem else None
            return {"fuente": "subtitulos", "idioma": lang, "segmentos": segs}, None
    if not has_audio:
        return None, "El video no tiene audio."
    if not enabled:
        return None, "Transcripción desactivada (--sin-transcripcion)."
    try:
        return whisper(video, prompt), None
    except ImportError:
        return None, "faster-whisper no está instalado; sigo sin transcripción (solo cuadros y audio)."
    except Exception as exc:  # noqa: BLE001
        return None, (f"No pude transcribir ({type(exc).__name__}). Sigo sin transcripción: "
                      "el análisis de voz se basa solo en lo que se ve.")
