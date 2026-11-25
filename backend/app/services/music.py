"""背景音乐（QT-3）— 内置 CC0 曲库 + mood 匹配 + FFmpeg 混音（人声下自动闪避）

曲库：FreePD.com（Kevin MacLeod，CC0 公有领域）经 archive.org 镜像收录 8 首，
存放于 backend/assets/music/（catalog.json 记录元数据，ATTRIBUTION.txt 记录出处）。
Phase 2 可换曲库 API，接口保持不变。

混音方案：
- 音乐 aloop 循环铺满整段视频 + 结尾 2s 渐弱（afade）
- 原声保留；音乐经 sidechaincompress 以原声为侧链 → 人声出现时自动压低（auto-duck）
- 视频流 -c:v copy 不重编码，只重编音频（aac）
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ._media import ffmpeg, has_audio, media_duration
from . import storage

_CATALOG: dict | None = None

_MUSIC_VOLUME = 0.32  # 有原声时的音乐音量（sidechain 前）
_MUSIC_VOLUME_NO_VOICE = 0.85  # 无原声时的音乐音量
_FADE_OUT_S = 2.0
_DUCK = "sidechaincompress=threshold=0.02:ratio=12:attack=150:release=800"


def _assets_dir() -> Path:
    return storage.backend_root() / "assets" / "music"


def _catalog() -> dict:
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = json.loads((_assets_dir() / "catalog.json").read_text(encoding="utf-8"))
    return _CATALOG


def list_tracks() -> list[dict]:
    """曲库清单（供前端选曲）：[{id, title, moods, tempo, duration_s, license}]"""
    cat = _catalog()
    return [
        {
            "id": t["id"],
            "title": t["title"],
            "moods": t["moods"],
            "tempo": t["tempo"],
            "duration_s": t["duration_s"],
            "license": cat["license"],
        }
        for t in cat["tracks"]
    ]


def match_bgm(
    video_duration_s: float, mood: str | None = None, track_id: str | None = None
) -> dict:
    """按指定曲目 / mood 选曲，返回 {id, title, moods, tempo, duration_s, license, file}

    - track_id 精确指定（用户换曲）
    - mood 匹配：命中该 mood 的曲目里，优先选时长 ≥ 视频长度的最短曲（免循环），
      否则取最长曲
    - 都未指定：默认曲（neutral）
    """
    cat = _catalog()
    tracks = cat["tracks"]
    if track_id:
        for t in tracks:
            if t["id"] == track_id:
                return _to_track_dict(t, cat)
        raise ValueError(f"未知曲目: {track_id}")

    picked = None
    if mood:
        candidates = [t for t in tracks if mood in t["moods"]]
        if candidates:
            longer = [t for t in candidates if t["duration_s"] >= video_duration_s]
            picked = min(longer, key=lambda t: t["duration_s"]) if longer else max(
                candidates, key=lambda t: t["duration_s"]
            )
    if picked is None:
        picked = next((t for t in tracks if t.get("default")), tracks[0])
    return _to_track_dict(picked, cat)


def _to_track_dict(t: dict, cat: dict) -> dict:
    return {
        "id": t["id"],
        "title": t["title"],
        "moods": t["moods"],
        "tempo": t["tempo"],
        "duration_s": t["duration_s"],
        "license": cat["license"],
        "file": str(_assets_dir() / t["file"]),
    }


def mix_with_video(video_path: str | Path, track: dict, out_path: str | Path) -> str:
    """把 BGM 混入视频（原声保留、人声下自动闪避），返回输出路径

    视频流 -c:v copy 不重编码；音频重编 aac。
    无原声的视频直接铺音乐（无闪避）。
    """
    video_path = Path(video_path).resolve()
    out_path = Path(out_path).resolve()
    music_file = Path(track["file"]).resolve()
    if not music_file.is_file():
        raise FileNotFoundError(f"曲库文件缺失: {music_file}")

    dur = media_duration(video_path)
    if dur <= 0:
        raise RuntimeError(f"无法探测视频时长: {video_path.name}")
    fade_st = max(0.0, dur - _FADE_OUT_S)

    # [1:a] 音乐：循环 → 截到视频长度 → 结尾渐弱
    bg = (
        f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{dur:.3f},"
        f"afade=t=out:st={fade_st:.3f}:d={_FADE_OUT_S}[bg]"
    )
    voice = has_audio(video_path)
    if voice:
        # 原声做侧链：人声出现时音乐自动压低（auto-duck），再与原声混合
        af = (
            f"{bg};"
            f"[0:a]asplit[voice][sc];"
            f"[bg]volume={_MUSIC_VOLUME}[bg0];"
            f"[bg0][sc]{_DUCK}[ducked];"
            f"[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
            f"alimiter=limit=0.95[aout]"
        )
    else:
        af = f"{bg};[bg]volume={_MUSIC_VOLUME_NO_VOICE}[aout]"

    cmd = [
        ffmpeg(), "-y",
        "-i", str(video_path),
        "-i", str(music_file),
        "-filter_complex", af,
        "-map", "0:v", "-c:v", "copy",
        "-map", "[aout]", "-c:a", "aac", "-b:a", "192k",
        str(out_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg 混音失败: {r.stderr[-400:]}")
    return str(out_path)
