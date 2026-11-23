"""Pydantic 请求/响应模型"""
from typing import Literal

from pydantic import BaseModel, Field

OutputType = Literal["text", "image", "video"]
Platform = Literal["instagram", "xiaohongshu", "x", "douyin"]
QuickTool = Literal["subtitles", "cover", "bgm", "finish", "copy"]


class JobCreate(BaseModel):
    """创建完整流水线任务 (OP-1/PS-3/OP-6/ST-5)"""

    inputs: list[str] = Field(default_factory=list)  # 素材 id 或内联文本
    outputs: list[OutputType] = Field(min_length=1)
    style_platforms: list[Platform] = Field(default_factory=lambda: ["xiaohongshu"])
    language: str = "zh-CN"
    quick_render: bool = False  # 快速出片：跳过分镜审批 (ST-5)


class JobOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    kind: str
    outputs: list
    style_platforms: list
    language: str
    status: str
    plan: dict
    quick_tool: str | None = None


class StyleProfileIn(BaseModel):
    text: dict = Field(default_factory=dict)
    image: dict = Field(default_factory=dict)
    video: dict = Field(default_factory=dict)
    limits: dict = Field(default_factory=dict)


class BrandKitIn(BaseModel):
    logo_url: str | None = None
    colors: dict = Field(default_factory=dict)
    fonts: dict = Field(default_factory=dict)
    tone_of_voice: str | None = None
    product_images: list = Field(default_factory=list)
