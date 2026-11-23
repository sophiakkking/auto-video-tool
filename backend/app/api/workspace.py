"""工作区与品牌套件路由（IN-4）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import BrandKit
from ..schemas import BrandKitIn
from .jobs import _demo_workspace_id

router = APIRouter(prefix="/v1/workspace", tags=["workspace"])


@router.get("/brand-kit")
async def get_brand_kit(db: AsyncSession = Depends(get_db)):
    ws_id = await _demo_workspace_id(db)
    kit = (
        await db.execute(select(BrandKit).where(BrandKit.workspace_id == ws_id))
    ).scalar_one_or_none()
    if kit is None:
        raise HTTPException(404, "brand kit not configured")
    return {
        "logo_url": kit.logo_url,
        "colors": kit.colors,
        "fonts": kit.fonts,
        "tone_of_voice": kit.tone_of_voice,
        "product_images": kit.product_images,
    }


@router.put("/brand-kit")
async def upsert_brand_kit(payload: BrandKitIn, db: AsyncSession = Depends(get_db)):
    ws_id = await _demo_workspace_id(db)
    kit = (
        await db.execute(select(BrandKit).where(BrandKit.workspace_id == ws_id))
    ).scalar_one_or_none()
    if kit is None:
        kit = BrandKit(workspace_id=ws_id)
        db.add(kit)
    kit.logo_url = payload.logo_url
    kit.colors = payload.colors
    kit.fonts = payload.fonts
    kit.tone_of_voice = payload.tone_of_voice
    kit.product_images = payload.product_images
    await db.commit()
    return {"status": "ok"}
