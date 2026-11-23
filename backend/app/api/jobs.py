"""任务路由 — 完整流水线（PRD 5.1/5.2/5.7）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Job, Storyboard, Workspace
from ..schemas import JobCreate, JobOut

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


async def _demo_workspace_id(db: AsyncSession) -> str:
    ws = (
        await db.execute(select(Workspace).where(Workspace.name == "demo"))
    ).scalar_one_or_none()
    if ws is None:
        ws = Workspace(name="demo", plan="free")
        db.add(ws)
        await db.flush()
    return ws.id


@router.post("", status_code=201)
async def create_job(payload: JobCreate, db: AsyncSession = Depends(get_db)):
    """创建任务：任意素材 → 任意产出组合 (OP-1)"""
    job = Job(
        workspace_id=await _demo_workspace_id(db),
        kind="full",
        inputs=payload.inputs,
        outputs=list(payload.outputs),
        style_platforms=list(payload.style_platforms),
        language=payload.language,
        plan={},
        status="created",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    # TODO Phase 0: 入队素材理解 worker（workers.material_understanding）
    return JobOut.model_validate(job)


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """任务状态 + 生成方案"""
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return JobOut.model_validate(job)


# ---------- 以下接口 Phase 0 实现（当前返回 501 占位） ----------


@router.put("/{job_id}/plan", status_code=501)
async def confirm_plan(job_id: str):
    """确认/修改生成方案 (OP-2)"""
    raise HTTPException(501, "Phase 0 实现：方案生成后由用户确认并进入 generating 状态")


@router.get("/{job_id}/storyboard", status_code=501)
async def get_storyboard(job_id: str):
    """获取分镜脚本 + 定帧图 (ST-1/2)"""
    raise HTTPException(501, "Phase 0 实现：分镜脚本与关键帧生成后返回")


@router.put("/{job_id}/storyboard/shots", status_code=501)
async def update_shots(job_id: str):
    """编辑镜头：排序/增删/改时长改字 (ST-3)"""
    raise HTTPException(501, "Phase 0 实现")


@router.post("/{job_id}/storyboard/shots/{shot_id}/keyframe", status_code=501)
async def regenerate_keyframe(job_id: str, shot_id: str):
    """重生成某帧定帧图 (ST-3)"""
    raise HTTPException(501, "Phase 0 实现：文生图服务接入后可用")


@router.post("/{job_id}/storyboard/approve")
async def approve_storyboard(job_id: str, db: AsyncSession = Depends(get_db)):
    """批准分镜 → 触发渲染 (ST-4)"""
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    sb = (
        await db.execute(select(Storyboard).where(Storyboard.job_id == job_id))
    ).scalar_one_or_none()
    if sb is None:
        raise HTTPException(501, "Phase 0 实现：暂无分镜可审批")
    sb.status = "approved"
    job.status = "storyboard_approved"
    await db.commit()
    # TODO Phase 0: 入队渲染 worker（workers.render）
    return {"status": job.status}


@router.post("/{job_id}/render")
async def quick_render(job_id: str, db: AsyncSession = Depends(get_db)):
    """快速出片：跳过审批直接渲染 (ST-5)"""
    job = await db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    job.status = "rendering"
    await db.commit()
    # TODO Phase 0: 入队渲染 worker
    return {"status": job.status}


@router.post("/{job_id}/assets/{asset_id}/regenerate", status_code=501)
async def regenerate_asset(job_id: str, asset_id: str):
    """单元素重生成 (RV-2)"""
    raise HTTPException(501, "Phase 0 实现")


@router.post("/{job_id}/style-switch", status_code=501)
async def style_switch(job_id: str):
    """一键换平台风格 (PS-5/RV-3)"""
    raise HTTPException(501, "Phase 0 实现")


@router.post("/{job_id}/export", status_code=501)
async def export_package(job_id: str):
    """打包 ZIP → 下载链接 (RV-5)"""
    raise HTTPException(501, "Phase 0 实现")
