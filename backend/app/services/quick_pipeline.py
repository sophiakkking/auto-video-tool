"""快速工具管线 — Celery 任务与 eager 模式共用的执行体

QT-4 口播一键成片：ASR → 字幕烧录 → 封面 → 导出包。
异常内部消化（job.status=failed + plan.error），不向上抛。
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from ..db import SessionLocal
from ..models import Job
from . import cover, storage, subtitles


def _resolve_path(p: str) -> Path:
    """任务内路径相对 backend 根目录解析"""
    path = Path(p)
    return path if path.is_absolute() else storage.backend_root() / path


async def run_quick_finish(
    job_id: str,
    title: str = "",
    platform: str = "xiaohongshu",
    language: str | None = None,
) -> dict:
    """执行一键成片管线并更新任务状态。同步重活（ASR/ffmpeg）由调用方放到线程。"""
    try:
        async with SessionLocal() as db:
            job = await db.get(Job, job_id)
            if job is None:
                return {"job_id": job_id, "status": "failed", "error": f"job {job_id} not found"}
            job.status = "quick_processing"
            await db.commit()
            video = job.inputs[0].get("video") if job.inputs else None
        if not video:
            raise ValueError("任务没有输入视频")

        video_path = _resolve_path(video)
        if not video_path.exists():
            raise FileNotFoundError(f"输入视频不存在: {video_path}")

        out = storage.quick_job_dir(job_id) / "out"
        out.mkdir(parents=True, exist_ok=True)

        segs = subtitles.transcribe(video_path, language=language)
        (out / "transcript.json").write_text(
            json.dumps(segs, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out / "subtitles.srt").write_text(subtitles.export_srt(segs), encoding="utf-8")
        subtitles.burn_subtitles(video_path, segs, out / "finished.mp4")

        frame = out / "_frame.png"
        cover.extract_best_frame(video_path, frame)
        cover.make_cover(frame, title, out / "cover.png", platform=platform)
        frame.unlink()

        outputs = {
            "transcript": str((out / "transcript.json").relative_to(storage.backend_root())),
            "subtitles": str((out / "subtitles.srt").relative_to(storage.backend_root())),
            "video": str((out / "finished.mp4").relative_to(storage.backend_root())),
            "cover": str((out / "cover.png").relative_to(storage.backend_root())),
        }

        async with SessionLocal() as db:
            job = await db.get(Job, job_id)
            if job is not None:
                job.status = "quick_review"
                job.outputs = [outputs]
                await db.commit()
        return {"job_id": job_id, "status": "quick_review", "outputs": outputs}
    except Exception as e:
        try:
            async with SessionLocal() as db:
                job = await db.get(Job, job_id)
                if job is not None:
                    job.status = "failed"
                    job.plan = {"error": str(e)}
                    await db.commit()
        except Exception:
            pass  # 状态落库失败不掩盖原始错误
        return {"job_id": job_id, "status": "failed", "error": str(e)}


def run_quick_finish_sync(
    job_id: str,
    title: str = "",
    platform: str = "xiaohongshu",
    language: str | None = None,
) -> dict:
    """同步包装：worker 进程（无运行中 loop）或 asyncio.to_thread 里调用"""
    return asyncio.run(run_quick_finish(job_id, title, platform, language))
