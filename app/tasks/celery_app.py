from __future__ import annotations

from celery import Celery

from app.config import settings


celery_app = Celery("context-engine", broker=settings.redis_url, backend=settings.redis_url)

