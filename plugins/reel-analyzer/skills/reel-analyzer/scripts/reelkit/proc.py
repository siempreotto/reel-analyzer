"""Subprocesos con el PATH del venv (yt-dlp, gallery-dl y deno viven ahí)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys


def env() -> dict:
    e = dict(os.environ)
    venv_bin = os.path.dirname(sys.executable)
    e["PATH"] = venv_bin + os.pathsep + e.get("PATH", "")
    e.setdefault("PYTHONIOENCODING", "utf-8")
    return e


def run(cmd: list[str], timeout: float | None = None, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env(), timeout=timeout, **kw)


def which(name: str) -> str | None:
    return shutil.which(name, path=env()["PATH"])


def python_module(module: str) -> list[str]:
    return [sys.executable, "-m", module]
