"""Celery 任务 — Phase 0 逐个实现（队列路由见 celery_app.task_routes）"""
import asyncio
import json
from pathlib import Path

from app.db import SessionLocal
from app.models import Job
from app.services import cover, storage, subtitles

from .celery_app import celery


def _resolve_path(p: str) -> Path:
    """任务内路径相对 backend 根目录解析"""
    path = Path(p)
    return path if path.is_absolute() else storage.backend_root() / path


def _load_job(job_id: str) -> tuple[Job, str | None]:
    """加载任务并置 quick_processing；返回 (job, 视频绝对路径)"""

    async def _work() -> tuple[Job, str | None]:
        async with SessionLocal() as db:
            job = await db.get(Job, job_id)
            if job is None:
                raise ValueError(f"job {job_id} not found")
            job.status = "quick_processing"
            await db.commit()
            video = job.inputs[0].get("video") if job.inputs else None
            return job, str(_resolve_path(video)) if video else None

    return asyncio.run(_work())


def _update_job(job_id: str, outputs: dict, error: str | None = None) -> None:
    async def _work() -> None:
        async with SessionLocal() as db:
            job = await db.get(Job, job_id)
            if job is None:
                return
            if error:
                job.status = "failed"
                job.plan = {"error": error}
            else:
                job.status = "quick_review"
                job.outputs = [outputs]
            await db.commit()

    asyncio.run(_work())


@celery.task(name="workers.quick_finish")
def quick_finish_task(
    job_id: str,
    title: str = "",
    platform: str = "xiaohongshu",
    language: str | None = None,
) -> dict:
    """QT-4 口播一键成片：ASR → 字幕烧录 → 封面 → 导出包（Phase 0 本地存储）"""
    try:
        job, video = _load_job(job_id)
        if not video or not Path(video).exists():
            raise FileNotFoundError(f"输入视频不存在: {video}")

        out = storage.quick_job_dir(job_id) / "out"
        out.mkdir(parents=True, exist_ok=True)

        segs = subtitles.transcribe(video, language=language)
        (out / "transcript.json").write_text(
            json.dumps(segs, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out / "subtitles.srt").write_text(subtitles.export_srt(segs), encoding="utf-8")
        subtitles.burn_subtitles(video, segs, out / "finished.mp4")

        frame = out / "_frame.png"
        cover.extract_best_frame(video, frame)
        cover.make_cover(frame, title, out / "cover.png", platform=platform)
        frame.unlink()

        outputs = {
            "transcript": str((out / "transcript.json").relative_to(storage.backend_root())),
            "subtitles": str((out / "subtitles.srt").relative_to(storage.backend_root())),
            "video": str((out / "finished.mp4").relative_to(storage.backend_root())),
            "cover": str((out / "cover.png").relative_to(storage.backend_root())),
        }
        _update_job(job_id, outputs)
        return {"job_id": job_id, "status": "quick_review", "outputs": outputs}
    except Exception as e:
        _update_job(job_id, {}, error=str(e))
        return {"job_id": job_id, "status": "failed", "error": str(e)}
