"""风格库路由 — 平台风格档案（PRD 5.3 / PS-6）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..data.style_profiles import SEED_STYLE_PROFILES
from ..db import get_db
from ..models import StyleProfile
from ..schemas import StyleProfileIn

router = APIRouter(prefix="/v1/styles", tags=["styles"])


def _to_dict(row: StyleProfile) -> dict:
    return {
        "platform": row.platform,
        "version": row.version,
        "text": row.text_spec,
        "image": row.image_spec,
        "video": row.video_spec,
        "limits": row.limits,
    }


@router.get("")
async def list_styles(db: AsyncSession = Depends(get_db)):
    """风格档案列表：优先读库，库不可用/为空时返回种子数据"""
    try:
        rows = (await db.execute(select(StyleProfile))).scalars().all()
        if rows:
            return [_to_dict(r) for r in rows]
    except Exception:
        pass  # 数据库未就绪 → 回退种子数据
    return [p for p in SEED_STYLE_PROFILES.values()]


@router.put("/{platform}")
async def upsert_style(
    platform: str, payload: StyleProfileIn, db: AsyncSession = Depends(get_db)
):
    """调整风格档案（PS-6 配置化）"""
    if platform not in SEED_STYLE_PROFILES:
        raise HTTPException(400, f"unknown platform '{platform}'")
    row = await db.get(StyleProfile, platform)
    if row is None:
        row = StyleProfile(platform=platform)
        db.add(row)
    row.text_spec = payload.text
    row.image_spec = payload.image
    row.video_spec = payload.video
    row.limits = payload.limits
    row.version += 1
    await db.commit()
    await db.refresh(row)
    return _to_dict(row)
