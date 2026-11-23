"""视频渲染（PRD 5.8）— Phase 0 实现

- 只渲染已批准的分镜 (VD-1)；快速出片模式直接渲染 (ST-5)
- Mode A：关键帧 + 运镜 + 字幕烧录 + BGM（FFmpeg/Remotion，VD-3）
- Mode B：图生视频 API，Phase 2，限额使用 (VD-4)
"""


def render_from_storyboard(job_id: str, shots: list[dict], style_profile: dict) -> str:
    """返回成品视频 URL"""
    raise NotImplementedError("Phase 0: 接入 FFmpeg Mode A 渲染管线")
