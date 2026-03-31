from __future__ import annotations

from celery import Celery

from app.config import settings


celery_app = Celery("context-engine", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_track_started=True,
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_time_limit - 60,
    worker_prefetch_multiplier=1,
)
celery_app.autodiscover_tasks(["app.tasks"])

