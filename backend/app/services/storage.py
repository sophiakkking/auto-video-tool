"""本地磁盘存储（Phase 0；生产换 MinIO/S3 — 技术设计 §2）

布局:
    storage/quick/{job_id}/input.mp4
    storage/quick/{job_id}/out/{transcript.json, subtitles.srt, finished.mp4, cover.png}

素材默认不入知识库（KB-9），本地文件仅作为任务工作区。
"""
from __future__ import annotations

from pathlib import Path

from ..config import get_settings

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def backend_root() -> Path:
    """backend/ 根目录（路径解析基准）"""
    return _BACKEND_ROOT


def storage_root() -> Path:
    s = Path(get_settings().storage_dir)
    return s if s.is_absolute() else _BACKEND_ROOT / s


def quick_job_dir(job_id: str) -> Path:
    d = storage_root() / "quick" / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d
