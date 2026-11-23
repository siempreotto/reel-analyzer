import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/reel-analyzer/skills/reel-analyzer/scripts"
sys.path.insert(0, str(SCRIPTS))

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="requiere ffmpeg")


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


@pytest.fixture(scope="session")
def two_scene_video(tmp_path_factory) -> Path:
    """8 s vertical: 4 s de testsrc + 4 s de color rojo (un corte en t=4), con un tono de 440 Hz."""
    out = tmp_path_factory.mktemp("vid") / "dos_escenas.mp4"
    _ffmpeg(
        "-f", "lavfi", "-i", "testsrc=size=360x640:rate=25:duration=4",
        "-f", "lavfi", "-i", "color=c=red:size=360x640:rate=25:duration=4",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=8",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
        "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out),
    )
    return out


@pytest.fixture(scope="session")
def single_scene_video(tmp_path_factory) -> Path:
    """12 s sin cortes (tipo talking head) y con 2 s de silencio en el medio."""
    out = tmp_path_factory.mktemp("vid") / "una_escena.mp4"
    _ffmpeg(
        "-f", "lavfi", "-i", "testsrc2=size=360x640:rate=25:duration=12",
        "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=44100:duration=12",
        "-af", "volume=enable='between(t,5,7)':volume=0",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(out),
    )
    return out


@pytest.fixture(scope="session")
def silent_video(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("vid") / "mudo.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc=size=320x320:rate=25:duration=3",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out))
    return out
