"""媒体工具共享函数（ffmpeg/ffprobe 定位 + 通用查询）"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def ffmpeg() -> str:
    p = shutil.which("ffmpeg")
    if p:
        return p
    local = Path.home() / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
    if local.exists():
        return str(local)
    return "ffmpeg"


def ffprobe() -> str:
    p = shutil.which("ffprobe")
    if p:
        return p
    local = Path.home() / "tools" / "ffmpeg" / "bin" / "ffprobe.exe"
    if local.exists():
        return str(local)
    return "ffprobe"


def video_size(path: str | Path) -> tuple[int, int]:
    """返回 (width, height)；探测失败回退 720x1280"""
    r = subprocess.run(
        [
            ffprobe(), "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    parts = [int(x) for x in r.stdout.split()]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return 720, 1280


def video_height(path: str | Path) -> int:
    return video_size(path)[1]


def media_duration(path: str | Path) -> float:
    """媒体时长（秒）；探测失败返回 0"""
    r = subprocess.run(
        [
            ffprobe(), "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def has_audio(path: str | Path) -> bool:
    """是否存在音频流"""
    r = subprocess.run(
        [
            ffprobe(), "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return "audio" in r.stdout
