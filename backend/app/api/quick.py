"""快速工具路由 — 轻量通道（PRD 5.9）"""
import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_db
from ..models import Job
from ..schemas import JobOut
from ..services import storage
from ..services.quick_pipeline import run_quick_finish_sync
from ..workers.tasks import quick_finish_task
from .jobs import _demo_workspace_id

router = APIRouter(prefix="/v1/quick", tags=["quick"])

_TOOLS = {"subtitles", "cover", "bgm", "finish", "copy"}
_MAX_UPLOAD_MB = 500


async def _save_upload(file: UploadFile, dest: Path) -> None:
    """流式落盘，避免大文件占内存"""
    size = 0
    with dest.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > _MAX_UPLOAD_MB * 1024 * 1024:
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"文件超过 {_MAX_UPLOAD_MB}MB 限制")
            f.write(chunk)


@router.post("/{tool}", status_code=201)
async def run_quick_tool(
    tool: str,
    file: UploadFile = File(...),
    title: str = Form(""),
    platform: str = Form("xiaohongshu"),
    language: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    """口播加字幕 / 做封面 / 配音乐 / 一键成片 / 视频转文案

    已实现: finish（QT-4 一键成片：ASR → 字幕烧录 → 封面 → 导出包）
    其余工具 Phase 0 逐个接入。
    """
    if tool not in _TOOLS:
        raise HTTPException(400, f"unknown tool '{tool}', expected one of {sorted(_TOOLS)}")
    if tool != "finish":
        raise HTTPException(501, f"quick tool '{tool}' 尚未接入管线（Phase 0）")

    job = Job(
        workspace_id=await _demo_workspace_id(db),
        kind="quick",
        inputs=[],
        outputs=[],
        style_platforms=[platform],
        language=language or "zh-CN",
        quick_tool=tool,
        status="quick_created",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 素材默认不入库（KB-9）：只落本地工作区，不建 Material
    suffix = Path(file.filename or "video.mp4").suffix.lower()
    if not suffix or len(suffix) > 8 or not all(c.isalnum() or c == "." for c in suffix):
        suffix = ".mp4"
    dest = storage.quick_job_dir(job.id) / f"input{suffix}"
    try:
        await _save_upload(file, dest)
    except HTTPException:
        raise
    except Exception:
        await db.delete(job)  # 上传失败不留孤儿任务
        await db.commit()
        raise HTTPException(500, "上传保存失败")

    job.inputs = [{"video": str(dest.relative_to(storage.backend_root()))}]
    job.status = "quick_processing"
    await db.commit()

    if get_settings().celery_eager:
        # 开发期（无 Redis）：请求内同步跑管线；重活放线程，不阻塞事件循环
        result = await asyncio.to_thread(
            run_quick_finish_sync, job.id, title, platform, language or None
        )
        if result.get("status") == "failed":
            raise HTTPException(500, f"管线执行失败: {result.get('error')}")
        await db.refresh(job)
        return JobOut.model_validate(job)

    try:
        # 生产：Redis + worker 异步执行
        quick_finish_task.delay(job.id, title=title, platform=platform, language=language or None)
    except Exception as e:  # broker 不可达
        job.status = "failed"
        job.plan = {"error": f"任务入队失败: {e}"}
        await db.commit()
        raise HTTPException(503, "任务队列不可用（Redis 未就绪？）")

    await db.refresh(job)
    return JobOut.model_validate(job)


@router.get("/jobs/{job_id}")
async def get_quick_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """快速任务状态"""
    job = await db.get(Job, job_id)
    if job is None or job.kind != "quick":
        raise HTTPException(404, "quick job not found")
    return JobOut.model_validate(job)


# 产物白名单：防止路径穿越，只能取这四个固定文件
_FILES = {"transcript.json", "subtitles.srt", "finished.mp4", "cover.png"}


@router.get("/jobs/{job_id}/files/{name}")
async def get_quick_job_file(job_id: str, name: str, db: AsyncSession = Depends(get_db)):
    """下载快速任务产物（白名单文件名）"""
    if name not in _FILES:
        raise HTTPException(404, "file not found")
    job = await db.get(Job, job_id)
    if job is None or job.kind != "quick":
        raise HTTPException(404, "quick job not found")
    path = storage.quick_job_dir(job_id) / "out" / name
    if not path.is_file():
        raise HTTPException(404, "file not found")
    return FileResponse(path)
