"""快速工具管线 — Celery 任务与 eager 模式共用的执行体

finish:     ASR → 字幕烧录 → 封面 → 打包 (QT-4)
subtitles:  ASR → 字幕烧录 (QT-1)
cover:      最佳帧 + 标题大字封面 (QT-2)
copy:       ASR 转写 → 文案 (QT-6，平台适配文案 Phase 2)
bgm:        曲库未接 (QT-3)，暂不支持
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ..db import SessionLocal
from ..models import Job
from . import cover, storage, subtitles


def _resolve_path(p: str) -> Path:
    """任务内路径相对 backend 根目录解析"""
    path = Path(p)
    return path if path.is_absolute() else storage.backend_root() / path


async def _load_job(job_id: str) -> tuple[Job, str]:
    """加载任务、置 quick_processing，返回 (job, 视频绝对路径)"""
    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        if job is None:
            raise ValueError(f"job {job_id} not found")
        job.status = "quick_processing"
        await db.commit()
        video = job.inputs[0].get("video") if job.inputs else None
    if not video:
        raise ValueError("任务没有输入视频")
    video_path = _resolve_path(video)
    if not video_path.exists():
        raise FileNotFoundError(f"输入视频不存在: {video_path}")
    return job, str(video_path)


async def _set_result(job_id: str, outputs: dict, error: str | None = None) -> None:
    """落终态：quick_review + outputs，或 failed + plan.error"""
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


def _rel(out: Path, name: str) -> str:
    return str((out / name).relative_to(storage.backend_root()))


def _transcribe(video: str, out: Path, language: str | None) -> list[dict]:
    """ASR 转写 + 落盘 transcript/srt（同步重活，调用方需在非主循环线程）"""
    segs = subtitles.transcribe(video, language=language)
    if not segs:
        raise RuntimeError("未转写出任何语音内容")
    (out / "transcript.json").write_text(
        json.dumps(segs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "subtitles.srt").write_text(subtitles.export_srt(segs), encoding="utf-8")
    return segs


async def run_quick_tool(
    job_id: str,
    title: str = "",
    platform: str = "xiaohongshu",
    language: str | None = None,
) -> dict:
    """按 job.quick_tool 分发执行。异常内部消化，不向上抛。"""
    try:
        job, video = await _load_job(job_id)
        tool = job.quick_tool or "finish"
        out = storage.quick_job_dir(job_id) / "out"
        out.mkdir(parents=True, exist_ok=True)

        if tool == "cover":
            frame = out / "_frame.png"
            cover.extract_best_frame(video, frame)
            cover.make_cover(frame, title, out / "cover.png", platform=platform)
            frame.unlink()
            outputs = {"cover": _rel(out, "cover.png")}
        elif tool == "copy":
            _transcribe(video, out, language)
            outputs = {
                "transcript": _rel(out, "transcript.json"),
                "subtitles": _rel(out, "subtitles.srt"),
            }
        elif tool == "subtitles":
            segs = _transcribe(video, out, language)
            subtitles.burn_subtitles(video, segs, out / "finished.mp4")
            outputs = {
                "video": _rel(out, "finished.mp4"),
                "transcript": _rel(out, "transcript.json"),
                "subtitles": _rel(out, "subtitles.srt"),
            }
        elif tool == "finish":
            segs = _transcribe(video, out, language)
            subtitles.burn_subtitles(video, segs, out / "finished.mp4")
            frame = out / "_frame.png"
            cover.extract_best_frame(video, frame)
            cover.make_cover(frame, title, out / "cover.png", platform=platform)
            frame.unlink()
            outputs = {
                "video": _rel(out, "finished.mp4"),
                "cover": _rel(out, "cover.png"),
                "transcript": _rel(out, "transcript.json"),
                "subtitles": _rel(out, "subtitles.srt"),
            }
        else:
            raise ValueError(f"未知快速工具: {tool}")

        await _set_result(job_id, outputs)
        return {"job_id": job_id, "status": "quick_review", "outputs": outputs}
    except Exception as e:
        await _set_result(job_id, {}, error=str(e))
        return {"job_id": job_id, "status": "failed", "error": str(e)}


def run_quick_tool_sync(
    job_id: str,
    title: str = "",
    platform: str = "xiaohongshu",
    language: str | None = None,
) -> dict:
    """同步包装：worker 进程（无运行中 loop）或 asyncio.to_thread 里调用"""
    return asyncio.run(run_quick_tool(job_id, title, platform, language))
