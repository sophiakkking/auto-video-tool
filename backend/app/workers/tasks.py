"""Celery 任务 — Phase 0 逐个实现（队列路由见 celery_app.task_routes）"""
from app.services.quick_pipeline import run_quick_finish_sync

from .celery_app import celery


@celery.task(name="workers.material_understanding")
def material_understanding_task(job_id: str) -> dict:
    """素材理解：ASR/OCR/场景检测/关键信息提取 (MI-3/4/6)"""
    raise NotImplementedError("Phase 0: 调用 services.material_understanding")


@celery.task(name="workers.content_generation")
def content_generation_task(job_id: str) -> dict:
    """文案/方案/分镜脚本生成 (TX / OP-2 / ST-1)"""
    raise NotImplementedError("Phase 0: 调用 services.content / storyboard")


@celery.task(name="workers.quick_finish")
def quick_finish_task(
    job_id: str,
    title: str = "",
    platform: str = "xiaohongshu",
    language: str | None = None,
) -> dict:
    """QT-4 口播一键成片（worker 进程：无运行中事件循环，直接 asyncio.run）"""
    return run_quick_finish_sync(job_id, title, platform, language)


@celery.task(name="workers.render")
def render_task(job_id: str) -> dict:
    """视频渲染：FFmpeg Mode A 合成 (VD-3)"""
    raise NotImplementedError("Phase 0: 调用 services.render")
