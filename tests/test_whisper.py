"""Transcripción real con faster-whisper. Lenta (baja el modelo la primera vez):
solo corre con REEL_TEST_WHISPER=1 y en macOS (usa `say` para generar voz)."""
import json
import os
import shutil
import subprocess

import pytest

import analyze

pytestmark = pytest.mark.skipif(
    os.environ.get("REEL_TEST_WHISPER") != "1" or not shutil.which("say") or not shutil.which("ffmpeg"),
    reason="poner REEL_TEST_WHISPER=1 (macOS) para probar Whisper",
)


def test_whisper_spanish(tmp_path):
    aiff = tmp_path / "voz.aiff"
    subprocess.run(["say", "-v", "Paulina", "Tres errores que cometes al grabar tus reels. Sígueme para más.",
                    "-o", str(aiff)], check=True)
    mp4 = tmp_path / "voz.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=360x640:rate=25:duration=6",
                    "-i", str(aiff), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(mp4)],
                   check=True)
    assert analyze.main(["--file", str(mp4), "--out", str(tmp_path / "out")]) == 0
    data = json.loads((tmp_path / "out" / "archivo_voz" / "analysis.json").read_text())
    tr = data["transcripcion"]
    assert tr and tr["fuente"] == "whisper" and tr["idioma"] == "es"
    texto = " ".join(s["text"] for s in tr["segmentos"]).lower()
    assert "errores" in texto and "reels" in texto
    assert "errores" in data["hook"]["voz"].lower()
