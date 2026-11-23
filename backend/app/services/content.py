"""内容生成（PRD 5.5）— Phase 0 实现

- 按平台风格档案生成文案 3 变体 (TX-1/2/3/5/7)
- 视频转文案：从转写文本生成 (TX-6)
- 接地生成：先经 rag.retrieve 检索，知识库外的表述标注「AI 建议 — 需核实」(TX-8)
"""


def generate_caption(
    platform: str,
    language: str,
    facts: list[dict],
    brand_kit: dict | None = None,
) -> list[str]:
    raise NotImplementedError("Phase 0: 接入 LLM 文案生成（技术设计 §7.3 Prompt 骨架）")


def transcript_to_copy(transcript: str, platform: str, language: str) -> list[str]:
    raise NotImplementedError("Phase 0: TX-6 视频转文案")
