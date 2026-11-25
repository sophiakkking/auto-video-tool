"""QT-4 一键成片管线回归测试

需要本地 Postgres 就绪（scripts/dev-db.cmd start），未启动自动跳过。
"""
import asyncio
import json
import shutil
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

TEST_VIDEO = BACKEND / "testdata" / "test_video.mp4"


def _db_ready() -> bool:
    from sqlalchemy import text

    from app.db import engine

    async def _check() -> bool:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    return asyncio.run(_check())


pytestmark = pytest.mark.skipif(not _db_ready(), reason="本地 Postgres 未启动")


def _run(coro):
    return asyncio.run(coro)


def test_quick_finish_pipeline():
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Job, Workspace
    from app.services import storage
    from app.services.quick_pipeline import run_quick_tool_sync

    async def _get_demo_workspace() -> str:
        async with SessionLocal() as db:
            ws = (
                await db.execute(select(Workspace).where(Workspace.name == "demo"))
            ).scalar_one_or_none()
            if ws is None:
                ws = Workspace(name="demo", plan="free")
                db.add(ws)
                await db.commit()
            return ws.id

    ws_id = _run(_get_demo_workspace())

    async def _create_job() -> str:
        async with SessionLocal() as db:
            job = Job(
                workspace_id=ws_id,
                kind="quick",
                inputs=[],
                outputs=[],
                style_platforms=["xiaohongshu"],
                quick_tool="finish",
                status="quick_created",
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
            return job.id

    job_id = _run(_create_job())
    try:
        job_dir = storage.quick_job_dir(job_id)
        shutil.copy(TEST_VIDEO, job_dir / "input.mp4")

        async def _set_input() -> None:
            async with SessionLocal() as db:
                job = await db.get(Job, job_id)
                job.inputs = [
                    {"video": str((job_dir / "input.mp4").relative_to(storage.backend_root()))}
                ]
                await db.commit()

        _run(_set_input())

        result = run_quick_tool_sync(job_id, title="测试标题", platform="xiaohongshu")
        assert result["status"] == "quick_review", result

        out = job_dir / "out"
        for name in ("transcript.json", "subtitles.srt", "finished.mp4", "cover.png"):
            assert (out / name).exists(), f"缺少产物: {name}"

        transcript = json.loads((out / "transcript.json").read_text(encoding="utf-8"))
        assert len(transcript) == 3
        assert "保温杯" in transcript[0]["text"]

        async def _check_db() -> None:
            from app.services._media import has_audio

            async with SessionLocal() as db:
                job = await db.get(Job, job_id)
                assert job.status == "quick_review"
                assert len(job.outputs) == 1
                assert "video" in job.outputs[0]
                assert job.outputs[0].get("bgm"), "finish 应包含 BGM (QT-4)"
            assert has_audio(out / "finished.mp4")

        _run(_check_db())
    finally:
        async def _cleanup() -> None:
            async with SessionLocal() as db:
                job = await db.get(Job, job_id)
                if job is not None:
                    await db.delete(job)
                    await db.commit()

        _run(_cleanup())
        shutil.rmtree(job_dir, ignore_errors=True)


def test_quick_cover_tool():
    """cover 工具：无需 ASR，只验证封面生成 + 分发正确"""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Job, Workspace
    from app.services import storage
    from app.services.quick_pipeline import run_quick_tool_sync

    async def _setup() -> str:
        async with SessionLocal() as db:
            ws = (
                await db.execute(select(Workspace).where(Workspace.name == "demo"))
            ).scalar_one_or_none()
            if ws is None:
                ws = Workspace(name="demo", plan="free")
                db.add(ws)
                await db.commit()
            job = Job(
                workspace_id=ws.id,
                kind="quick",
                inputs=[],
                outputs=[],
                style_platforms=["instagram"],
                quick_tool="cover",
                status="quick_created",
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
            job_dir = storage.quick_job_dir(job.id)
            shutil.copy(TEST_VIDEO, job_dir / "input.mp4")
            job.inputs = [
                {"video": str((job_dir / "input.mp4").relative_to(storage.backend_root()))}
            ]
            await db.commit()
            return job.id

    job_id = _run(_setup())
    try:
        result = run_quick_tool_sync(job_id, title="封面测试", platform="instagram")
        assert result["status"] == "quick_review", result
        assert "cover" in result["outputs"]
        cover_path = storage.quick_job_dir(job_id) / "out" / "cover.png"
        assert cover_path.exists()

        from PIL import Image

        img = Image.open(cover_path)
        assert img.size == (720, 720)  # instagram 1:1
    finally:
        async def _cleanup() -> None:
            async with SessionLocal() as db:
                job = await db.get(Job, job_id)
                if job is not None:
                    await db.delete(job)
                    await db.commit()

        _run(_cleanup())
        shutil.rmtree(storage.quick_job_dir(job_id), ignore_errors=True)


def test_quick_bgm_tool():
    """bgm 工具：免版税曲库选曲 + auto-duck 混音，无需 ASR"""
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Job, Workspace
    from app.services import storage
    from app.services._media import has_audio, media_duration
    from app.services.quick_pipeline import run_quick_tool_sync

    async def _setup() -> str:
        async with SessionLocal() as db:
            ws = (
                await db.execute(select(Workspace).where(Workspace.name == "demo"))
            ).scalar_one_or_none()
            if ws is None:
                ws = Workspace(name="demo", plan="free")
                db.add(ws)
                await db.commit()
            job = Job(
                workspace_id=ws.id,
                kind="quick",
                inputs=[],
                outputs=[],
                style_platforms=["xiaohongshu"],
                quick_tool="bgm",
                status="quick_created",
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
            job_dir = storage.quick_job_dir(job.id)
            shutil.copy(TEST_VIDEO, job_dir / "input.mp4")
            job.inputs = [
                {"video": str((job_dir / "input.mp4").relative_to(storage.backend_root()))}
            ]
            await db.commit()
            return job.id

    job_id = _run(_setup())
    try:
        result = run_quick_tool_sync(job_id, mood="tech")
        assert result["status"] == "quick_review", result
        assert "video" in result["outputs"]
        bgm = result["outputs"].get("bgm")
        assert bgm and bgm["id"] == "meditating-beat"  # mood=tech → 唯一命中曲目
        assert "file" not in bgm  # 不泄露本地路径

        out = storage.quick_job_dir(job_id) / "out" / "finished.mp4"
        assert out.exists()
        assert has_audio(out)
        assert abs(media_duration(out) - media_duration(TEST_VIDEO)) < 0.5
    finally:
        async def _cleanup() -> None:
            async with SessionLocal() as db:
                job = await db.get(Job, job_id)
                if job is not None:
                    await db.delete(job)
                    await db.commit()

        _run(_cleanup())
        shutil.rmtree(storage.quick_job_dir(job_id), ignore_errors=True)
