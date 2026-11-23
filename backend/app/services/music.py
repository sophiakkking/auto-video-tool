"""背景音乐（QT-3）— Phase 0 实现

- 免版税曲库按 mood/tempo 自动匹配视频长度 (QT-3)
- 人声下自动闪避（auto-duck）
"""


def match_bgm(video_duration_s: float, mood: str | None = None) -> dict:
    """返回 {title, mood, tempo, duration_s, license, url}"""
    raise NotImplementedError("Phase 0: 接入免版税曲库与匹配逻辑")


def mix_with_video(video_url: str, track: dict) -> str:
    raise NotImplementedError("Phase 0: FFmpeg 混音 + auto-duck")
