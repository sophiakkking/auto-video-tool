"""ORM 实体 — 对应技术设计 §4 数据模型"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return uuid4().hex


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    plan: Mapped[str] = mapped_column(String(32), default="free")


class BrandKit(Base, TimestampMixin):
    """品牌套件 (IN-4) — MVP 每工作区一套"""

    __tablename__ = "brand_kits"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), unique=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    colors: Mapped[dict] = mapped_column(JSONB, default=dict)
    fonts: Mapped[dict] = mapped_column(JSONB, default=dict)
    tone_of_voice: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_images: Mapped[list] = mapped_column(JSONB, default=list)


class StyleProfile(Base, TimestampMixin):
    """平台风格档案 (PS-6) — 配置化，改风格不改代码"""

    __tablename__ = "style_profiles"

    platform: Mapped[str] = mapped_column(String(32), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    text_spec: Mapped[dict] = mapped_column(JSONB, default=dict)
    image_spec: Mapped[dict] = mapped_column(JSONB, default=dict)
    video_spec: Mapped[dict] = mapped_column(JSONB, default=dict)
    limits: Mapped[dict] = mapped_column(JSONB, default=dict)


class KbDocument(Base, TimestampMixin):
    """知识库文档 (KB-1)"""

    __tablename__ = "kb_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    doc_type: Mapped[str] = mapped_column(String(32), default="file")
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # pending | indexing | ready | failed
    status: Mapped[str] = mapped_column(String(32), default="pending")
    chunks: Mapped[list[KbChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class KbChunk(Base, TimestampMixin):
    """知识库切块 + 向量 (KB-2/7)"""

    __tablename__ = "kb_chunks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("kb_documents.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)  # 来源页码/位置
    freshness: Mapped[float] = mapped_column(Float, default=1.0)
    document: Mapped[KbDocument] = relationship(back_populates="chunks")


class Material(Base, TimestampMixin):
    """素材与其理解结果 (MI-1..8)；saved_to_kb 默认 False (KB-9)"""

    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    job_id: Mapped[str | None] = mapped_column(
        ForeignKey("jobs.id"), nullable=True, index=True
    )
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    # text | image | video | audio | link
    material_type: Mapped[str] = mapped_column(String(32))
    file_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    extracted: Mapped[dict] = mapped_column(JSONB, default=dict)
    saved_to_kb: Mapped[bool] = mapped_column(Boolean, default=False)


class Job(Base, TimestampMixin):
    """生成任务 (OP-1) — kind: full(完整流水线) | quick(快速工具)"""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="full")
    inputs: Mapped[list] = mapped_column(JSONB, default=list)
    outputs: Mapped[list] = mapped_column(JSONB, default=list)  # ["text","image","video"]
    style_platforms: Mapped[list] = mapped_column(JSONB, default=list)
    language: Mapped[str] = mapped_column(String(16), default="zh-CN")
    # 完整流水线: created→understanding→plan_draft→plan_confirmed→generating
    #            →storyboard_pending→storyboard_approved→rendering→review→exported
    # 快速工具:   quick_created→quick_processing→quick_review→quick_exported
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    plan: Mapped[dict] = mapped_column(JSONB, default=dict)
    # 快速工具: subtitles | cover | bgm | finish | copy
    quick_tool: Mapped[str | None] = mapped_column(String(32), nullable=True)
    storyboard: Mapped[Storyboard | None] = relationship(
        back_populates="job", uselist=False
    )
    packages: Mapped[list[Package]] = relationship(back_populates="job")


class Storyboard(Base, TimestampMixin):
    """分镜审批门 (ST-4)"""

    __tablename__ = "storyboards"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True)
    # draft | pending_approval | approved
    status: Mapped[str] = mapped_column(String(32), default="draft")
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    job: Mapped[Job] = relationship(back_populates="storyboard")
    shots: Mapped[list[Shot]] = relationship(
        back_populates="storyboard",
        cascade="all, delete-orphan",
        order_by="Shot.order",
    )


class Shot(Base, TimestampMixin):
    """镜头 (ST-1/2/5) — source: ai 生成 | user 素材"""

    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    storyboard_id: Mapped[str] = mapped_column(ForeignKey("storyboards.id"), index=True)
    order: Mapped[int] = mapped_column(Integer)
    duration_s: Mapped[float] = mapped_column(Float, default=3.0)
    scene_desc: Mapped[str] = mapped_column(Text)
    camera: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)
    vo_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    keyframe_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="ai")
    storyboard: Mapped[Storyboard] = relationship(back_populates="shots")


class Package(Base, TimestampMixin):
    """按平台产出的成品包"""

    __tablename__ = "packages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    platform: Mapped[str] = mapped_column(String(32))
    variant: Mapped[int] = mapped_column(Integer, default=1)
    assets: Mapped[list] = mapped_column(JSONB, default=list)  # [{asset_id, type}]
    job: Mapped[Job] = relationship(back_populates="packages")


class Asset(Base, TimestampMixin):
    """单件产物，支持单元素重生成 (RV-2)"""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    # text | image | video | audio | srt
    asset_type: Mapped[str] = mapped_column(String(16))
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    spec: Mapped[dict] = mapped_column(JSONB, default=dict)  # 尺寸/时长/编码
    status: Mapped[str] = mapped_column(String(32), default="pending")


class MusicTrack(Base, TimestampMixin):
    """免版税曲库 (QT-3)"""

    __tablename__ = "music_tracks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(200))
    mood: Mapped[str] = mapped_column(String(32))
    tempo: Mapped[str] = mapped_column(String(32))
    duration_s: Mapped[float] = mapped_column(Float)
    license: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(1000))


class GenerationRun(Base, TimestampMixin):
    """每步成本/耗时日志 — 成本模型数据源（技术设计 §9.3）"""

    __tablename__ = "generation_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    step: Mapped[str] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
