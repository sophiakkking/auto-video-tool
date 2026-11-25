"""快速工具管线 — Celery 任务与 eager 模式共用的执行体

finish:     ASR → 字幕烧录 → 封面 → BGM 混音 (QT-4)
subtitles:  ASR → 字幕烧录 (QT-1)
cover:      最佳帧 + 标题大字封面 (QT-2)
copy:       ASR 转写 → 文案 (QT-6，平台适配文案 Phase 2)
bgm:        免版税曲库 mood 匹配 + auto-duck 混音 (QT-3)
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ..db import SessionLocal
from ..models import Job
from . import cover, music, storage, subtitles


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


def _add_bgm(video: str, out: Path, mood: str, track: str) -> dict:
    """选曲 + 混音到 finished.mp4（temp 混音后原子替换，可原地覆盖输入）。

    返回 {id, title, moods, tempo, license}（不含本地 file 路径，避免泄露）。
    """
    from ._media import media_duration

    dur = media_duration(video)
    picked = music.match_bgm(dur, mood or None, track or None)
    tmp = out / "_mixed.mp4"
    music.mix_with_video(video, picked, tmp)
    tmp.replace(out / "finished.mp4")
    return {k: v for k, v in picked.items() if k != "file"}


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
    mood: str = "",
    track: str = "",
) -> dict:
    """按 job.quick_tool 分发执行。异常内部消化，不向上抛。

    mood/track: BGM 选曲参数（QT-3）— mood 留空 = 自动（默认曲），track 可精确换曲。
    """
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
        elif tool == "bgm":
            bgm = _add_bgm(video, out, mood, track)
            outputs = {
                "video": _rel(out, "finished.mp4"),
                "bgm": bgm,
            }
        elif tool == "finish":
            segs = _transcribe(video, out, language)
            subtitles.burn_subtitles(video, segs, out / "finished.mp4")
            frame = out / "_frame.png"
            cover.extract_best_frame(video, frame)
            cover.make_cover(frame, title, out / "cover.png", platform=platform)
            frame.unlink()
            bgm = _add_bgm(out / "finished.mp4", out, mood, track)
            outputs = {
                "video": _rel(out, "finished.mp4"),
                "cover": _rel(out, "cover.png"),
                "transcript": _rel(out, "transcript.json"),
                "subtitles": _rel(out, "subtitles.srt"),
                "bgm": bgm,
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
    mood: str = "",
    track: str = "",
) -> dict:
    """同步包装：worker 进程（无运行中 loop）或 asyncio.to_thread 里调用"""
    return asyncio.run(run_quick_tool(job_id, title, platform, language, mood, track))
