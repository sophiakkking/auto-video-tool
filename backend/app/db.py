"""异步数据库引擎与会话（PostgreSQL + pgvector）

poolclass=NullPool：async 连接池绑定创建时的事件循环，跨 loop 复用会损坏连接。
NullPool 每次取用新建连接（跟随当前 loop），Phase 0 开销可忽略；生产走
worker 进程 + 连接池时再调回默认池。
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url, echo=False, pool_pre_ping=True, poolclass=NullPool
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI 依赖：每请求一个会话"""
    async with SessionLocal() as session:
        yield session
