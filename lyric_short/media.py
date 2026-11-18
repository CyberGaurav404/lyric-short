"""ffmpeg helpers: locate the binary, probe, extract audio, encode, mux.

The project never assumes `ffmpeg` is on PATH: it looks at $FFMPEG, then PATH,
then the binary shipped inside `imageio-ffmpeg`.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import List, Optional


def ffmpeg() -> str:
    env = os.environ.get("FFMPEG")
    if env and os.path.exists(env):
        return env
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise SystemExit(
            "ffmpeg not found. Install it (`apt install ffmpeg`, `brew install ffmpeg`) "
            "or `pip install imageio-ffmpeg`."
        )


def run(cmd: List[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, **kw)


def probe_duration(path: str) -> float:
    out = subprocess.run([ffmpeg(), "-hide_banner", "-i", path],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout.decode("utf8", "ignore")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", out)
    if not m:
        raise SystemExit(f"could not read duration of {path}")
    h, mnt, sec = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(sec)


def extract_audio(src: str, dst: str, sample_rate: int = 16000) -> str:
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", src,
         "-vn", "-ac", "1", "-ar", str(sample_rate), dst])
    return dst


def encode_video(frames, out_path: str, width: int, height: int, fps: int,
                 crf: int = 20, preset: str = "medium", audio: Optional[str] = None,
                 audio_delay: float = 0.0, pix_fmt_in: str = "rgb24") -> None:
    """Stream RGB frames from an iterator of Pillow images into an MP4.

    Threads are pinned to 1 on purpose: the encoder then fits in ~1 GB of RAM,
    which keeps the tool usable on small laptops and inside containers.
    """
    cmd = [ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", pix_fmt_in,
           "-s", f"{width}x{height}", "-r", str(fps), "-i", "-"]
    if audio:
        cmd += ["-i", audio, "-map", "0:v:0", "-map", "1:a:0",
                "-af", _audio_filter(audio_delay),
                "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-threads", "1", "-filter_threads", "1",
            "-movflags", "+faststart", out_path]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for frame in frames:
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
    except BrokenPipeError:
        pass
    finally:
        rc = proc.wait()
    if rc != 0 or not os.path.exists(out_path):
        raise RuntimeError("ffmpeg failed while encoding frames")


def encode_from_dir(frames_dir: str, out_path: str, fps: int, crf: int = 20,
                    preset: str = "medium", audio: Optional[str] = None,
                    audio_delay: float = 0.0, pattern: str = "%05d.png") -> None:
    """Fallback encoder: read a numbered PNG sequence instead of a pipe."""
    cmd = [ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(fps),
           "-i", os.path.join(frames_dir, pattern)]
    if audio:
        cmd += ["-i", audio, "-map", "0:v:0", "-map", "1:a:0",
                "-af", _audio_filter(audio_delay),
                "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-threads", "1", "-filter_threads", "1", "-movflags", "+faststart", out_path]
    run(cmd)


def _audio_filter(delay: float) -> str:
    """Push the song back by `delay` seconds so it lines up with the intro card,
    then pad the tail so `-shortest` ends on the video, not on the audio."""
    if delay > 0.001:
        return f"adelay={int(delay * 1000)}:all=1,apad"
    return "apad"


def mux(video: str, audio: str, out_path: str) -> None:
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", video, "-i", audio,
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", "-movflags", "+faststart", out_path])
