"""素材理解（PRD 5.1）— Phase 0 实现

- 视频: 多语言 ASR 转写（词级时间轴）+ 场景检测 + 关键帧提取 (MI-3)
- 图片: OCR（中文友好）+ 视觉描述 (MI-4)
- 音频: 转写 (MI-5)
- 文本/链接: 关键词与关键信息提取 (MI-6)
- 提取结果写回 Material.extracted；仅用户勾选时写入知识库 (KB-9)
"""


def understand(material_type: str, file_url: str | None, text: str | None = None) -> dict:
    """返回 extracted 结构：{transcript, scenes, ocr, description, claims}"""
    raise NotImplementedError(
        "Phase 0: 接入 faster-whisper / PaddleOCR / 场景检测 / 视觉理解后实现"
    )
