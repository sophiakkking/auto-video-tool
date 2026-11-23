"""全局配置（pydantic-settings，读取 backend/.env）"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = "dev"
    database_url: str = "postgresql+asyncpg://postpilot:postpilot@localhost:5432/postpilot"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    # Phase 0 本地磁盘存储（相对 backend 根目录）；生产换 MinIO/S3（技术设计 §2）
    storage_dir: str = "storage"
    # 开发期无 Redis 时同步执行 Celery 任务（task_always_eager）
    celery_eager: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
