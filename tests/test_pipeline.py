import json
from pathlib import Path

import pytest

import analyze
from conftest import needs_ffmpeg
from reelkit import download as dl
from reelkit.build import validate
from reelkit.frames import plan_times
from reelkit.scenes import normalize
from reelkit.transcribe import parse_vtt


def _run(tmp_path, *args):
    code = analyze.main([*args, "--out", str(tmp_path), "--sin-transcripcion"])
    return code


def test_plan_hook_has_seven_frames():
    plan = plan_times([(0.0, 4.0), (4.0, 8.0)], 8.0, "completo")
    hook = [p for p in plan if p[1] == "hook"]
    assert [p[0] for p in hook] == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]


def test_normalize_merges_tiny_scenes():
    assert normalize([(0, 2.0), (2.0, 2.1), (2.1, 6.0)], 6.0) == [(0.0, 2.1), (2.1, 6.0)]
    assert normalize([], 5.0) == [(0.0, 5.0)]


@needs_ffmpeg
def test_two_scenes_detects_cut(two_scene_video, tmp_path):
    assert _run(tmp_path, "--file", str(two_scene_video)) == 0
    out = tmp_path / "archivo_dos_escenas"
    data = json.loads((out / "analysis.json").read_text())
    validate(data)
    assert data["ritmo"]["cortes"] == 1
    assert len(data["escenas"]) == 2
    assert abs(data["escenas"][1]["t_inicio"] - 4.0) < 0.15
    assert len(data["hook"]["frames"]) == 7
    for rel in data["cuadros"]["lista"]:
        assert (out / rel).exists()
    for e in data["escenas"]:
        assert e["frames"], "cada escena debe tener al menos un cuadro"
    assert data["audio_global"]["lufs_integrado"] is not None
    assert (out / "timeline.md").read_text().startswith("# Línea de tiempo")
    assert two_scene_video.exists(), "nunca se borra el archivo del usuario"
    assert not (out / "_descarga").exists()


@needs_ffmpeg
def test_single_scene_uses_uniform_sampling_and_finds_silence(single_scene_video, tmp_path):
    assert _run(tmp_path, "--file", str(single_scene_video)) == 0
    data = json.loads((tmp_path / "archivo_una_escena" / "analysis.json").read_text())
    assert data["ritmo"]["cortes"] == 0
    assert data["ritmo"]["tipo_probable"].startswith("toma continua")
    assert data["cuadros"]["total"] > 7  # hook + muestreo uniforme
    sil = data["audio_global"]["silencios"]
    assert any(4.5 <= s["inicio"] <= 5.6 and s["dur"] >= 1.5 for s in sil)


@needs_ffmpeg
def test_rapido_is_smaller(two_scene_video, tmp_path):
    analyze.main(["--file", str(two_scene_video), "--out", str(tmp_path), "--sin-transcripcion", "--modo", "rapido"])
    data = json.loads((tmp_path / "archivo_dos_escenas" / "analysis.json").read_text())
    assert data["modo"] == "rapido"
    assert data["cuadros"]["lado_largo_px"] == 512


@needs_ffmpeg
def test_silent_video(silent_video, tmp_path):
    assert _run(tmp_path, "--file", str(silent_video)) == 0
    data = json.loads((tmp_path / "archivo_mudo" / "analysis.json").read_text())
    assert data["audio_global"]["tiene_audio"] is False
    assert data["transcripcion"] is None
    assert any("no tiene audio" in a for a in data["avisos"])


def test_network_blocked_exit_code(monkeypatch, tmp_path, capsys):
    def fake_ytdlp(src, workdir, auth):
        return None, {}, "ERROR: Unable to download webpage: <urlopen error [Errno 8] nodename nor servname provided>"
    monkeypatch.setattr(dl, "_ytdlp", fake_ytdlp)
    monkeypatch.setattr(analyze, "require_ffmpeg", lambda: None)
    code = analyze.main(["https://www.instagram.com/reel/DAbc123xyz/", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 3
    assert "NETWORK_BLOCKED" in out
    last = json.loads(out.strip().splitlines()[-1])
    assert last["resultados"][0]["error"] == "NETWORK_BLOCKED"


def test_instagram_html_retries_without_cookies(monkeypatch, tmp_path):
    calls = []

    def fake_ytdlp(src, workdir, auth):
        calls.append(list(auth))
        if auth:
            return None, {}, "ERROR: [Instagram] x: Failed to parse JSON (caused by JSONDecodeError('Expecting value'))"
        v = workdir / "video.mp4"
        v.write_bytes(b"x")
        return v, {"id": "x"}, ""
    monkeypatch.setattr(dl, "_ytdlp", fake_ytdlp)
    from reelkit.router import route
    video, info = dl.download(route("https://instagram.com/reel/abc"), tmp_path / "w", cookies_from_browser="chrome")
    assert video.name == "video.mp4"
    assert calls == [["--cookies-from-browser", "chrome"], []]


def test_generic_failure_retried_once(monkeypatch, tmp_path):
    calls = []

    def fake_ytdlp(src, workdir, auth):
        calls.append(1)
        if len(calls) == 1:
            return None, {}, "ERROR: unable to download video data: HTTP Error 403: Forbidden"
        v = workdir / "video.mp4"
        v.write_bytes(b"x")
        return v, {"id": "x"}, ""
    monkeypatch.setattr(dl, "_ytdlp", fake_ytdlp)
    monkeypatch.setattr(dl, "RETRY_DELAY_S", 0)
    from reelkit.router import route
    video, _ = dl.download(route("https://youtube.com/shorts/aBcDeFgHiJk"), tmp_path / "w")
    assert video.name == "video.mp4" and len(calls) == 2


def test_parse_vtt_rolling_captions(tmp_path):
    vtt = tmp_path / "subs.es.vtt"
    vtt.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:01.500\nEsto es\n\n"
        "00:00:01.500 --> 00:00:03.000\nEsto es un hook\n\n"
        "00:00:03.000 --> 00:00:04.000\n<c>que funciona</c>\n", encoding="utf-8")
    segs = parse_vtt(vtt)
    assert [s["text"] for s in segs] == ["Esto es", "un hook", "que funciona"]
    assert segs[0]["start"] == 0.0 and segs[-1]["end"] == 4.0
