"""分镜脚本与定帧（PRD 5.7）— Phase 0 实现

- 镜头脚本：镜头号/时长/画面描述/运镜/字幕/口播词 (ST-1)
- 每镜一张定帧图（文生图或素材图，ST-2/5）
- 镜头数与节奏按平台风格档案 (ST-6)
"""


def generate_storyboard(job_id: str, style_profile: dict) -> list[dict]:
    """返回 shots: [{order, duration_s, scene_desc, camera, subtitle, vo_line}]"""
    raise NotImplementedError("Phase 0: 接入 LLM 分镜脚本 + 文生图定帧")
