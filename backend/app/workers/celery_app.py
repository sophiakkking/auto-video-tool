"""Celery 应用 — 三级队列（技术设计 §3.3）"""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery = Celery(
    "postpilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    # 开发期（无 Redis）：同步执行，请求内跑完管线；生产设 CELERY_EAGER=0
    task_always_eager=settings.celery_eager,
    # eager 模式下任务异常必须上抛（本机 celery 版本默认 False 会静默吞错）
    task_eager_propagates=True,
    task_routes={
        "workers.content_generation": {"queue": "light"},
        "workers.material_understanding": {"queue": "media"},
        "workers.quick_finish": {"queue": "media"},
        "workers.render": {"queue": "heavy"},
    },
)
