"""PostPilot API 入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .api import jobs, kb, quick, styles, workspace
from .config import get_settings
from .db import SessionLocal, engine
from .models import Base, Workspace

settings = get_settings()


async def _ensure_demo_workspace() -> None:
    """MVP 单工作区：启动时确保 demo 工作区存在"""
    async with SessionLocal() as session:
        exists = (
            await session.execute(select(Workspace).where(Workspace.name == "demo"))
        ).scalar_one_or_none()
        if exists is None:
            session.add(Workspace(name="demo", plan="free"))
            await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await _ensure_demo_workspace()
    except Exception as e:  # 数据库未就绪时仍可启动（/health 与风格库可用）
        print(f"[warn] 数据库未就绪，跳过建表：{e}")
    yield


app = FastAPI(title="PostPilot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(quick.router)
app.include_router(kb.router)
app.include_router(styles.router)
app.include_router(workspace.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}
